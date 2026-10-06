"""Examines the bot against eval/golden.jsonl:

    python eval/run_eval.py

Runs locally only — see app/run/run.sh. Writes the result to TWO places, always in the same spot:

    eval-result.json   the full detail of THIS run, so any script can read it again later.
    eval-result.md      the same result, in readable Markdown. Also printed to the terminal (for
                        app/run/run.sh and for this run's own logs).

golden.jsonl is written by hand — there used to be an automatic candidate generator using
qwen2.5:1.5b (the "generar" command, removed on 2026-09-24) that got dropped: with such a small
model, the questions it invented needed so much manual review and fixing that it didn't save real
time over writing them directly. With few documents, writing 2-3 questions per document by hand is
little work.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
GOLDEN = Path(os.getenv("GOLDEN_PATH", "eval/golden.jsonl"))
JSON_PATH = Path(os.getenv("EVAL_JSON_PATH", "eval/report/eval-result.json"))
MD_PATH = JSON_PATH.with_suffix(".md")

# Quality gate: whoever adapts the bot sets the minimum acceptable value for each metric, in
# config.env. Empty ones aren't required; if none are set, the script is purely informational.
THRESHOLDS_ENV = {
    "accuracy": "EVAL_MIN_ACCURACY",
    "accuracy_answerable": "EVAL_MIN_ACCURACY_ANSWERABLE",
    "refusal_rate": "EVAL_MIN_REFUSAL_RATE",
    "retrieval_recall": "EVAL_MIN_RETRIEVAL_RECALL",
}

# Phrases (no accents) the bot uses to admit it doesn't know something. These match the bot's REAL
# answer text, which stays in Spanish on purpose (see prompts/system.md) — don't translate them.
REFUSAL_MARKERS = [
    "no tengo", "no cuento", "no dispongo", "no puedo", "no se ",
    "no conozco", "no encuentro", "no hay informacion", "lo siento",
]


def normalize(text: str) -> str:
    """Lowercase and without accents, so comparisons don't care about them."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def headers() -> dict:
    """Headers for accessing the gateway: the API key (API_KEY, or the first of API_KEYS) and, if set, the origin secret."""
    h = {"content-type": "application/json"}
    key = os.getenv("API_KEY") or next((k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()), "")
    if key:
        h["x-api-key"] = key
    if os.getenv("ORIGIN_VERIFY_SECRET"):
        h["x-origin-verify"] = os.environ["ORIGIN_VERIFY_SECRET"]
    return h


def ask_question(question: str) -> dict:
    req = urllib.request.Request(
        f"{GATEWAY_URL}/ask",
        data=json.dumps({"question": question}).encode(),
        headers=headers(),
    )
    start = time.perf_counter()
    waited = 0.0  # time spent waiting on the rate limit: not the bot's own latency
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            # The gateway rate-limits requests per minute and per key. With the model already warm,
            # the exam runs faster than that limit: wait what the gateway asks for and retry.
            if e.code == 429 and attempt < 3:
                wait = int(e.headers.get("Retry-After", "60"))
                print(f"   (gateway rate limit: waiting {wait}s)", flush=True)
                time.sleep(wait)
                waited += wait
                continue
            data = {"answer": "", "tokens": 0, "model": None, "error": str(e)}
            break
        except (urllib.error.URLError, TimeoutError) as e:
            data = {"answer": "", "tokens": 0, "model": None, "error": str(e)}
            break
    data["latency_s"] = time.perf_counter() - start - waited
    return data


def read_thresholds() -> dict[str, float]:
    """Reads the minimums from config.env (EVAL_MIN_* variables). Called at the start to fail fast if one is malformed."""
    thresholds = {}
    for metric, env_var in THRESHOLDS_ENV.items():
        value = os.getenv(env_var, "").strip()
        if not value:
            continue
        try:
            thresholds[metric] = float(value)
            if not 0 <= thresholds[metric] <= 1:
                raise ValueError
        except ValueError:
            sys.exit(
                f"{env_var} must be a number between 0 and 1, or be empty (it's {value!r}). "
                "Check config.env: comments go on their own line, not after an empty value."
            )
    return thresholds


def check_thresholds(metrics: dict, thresholds: dict) -> list[dict]:
    """One row per defined threshold: metric, value, min and status (PASS/FAIL/N_A)."""
    rows = []
    for name, minimum in thresholds.items():
        if name not in metrics:
            rows.append({"metric": name, "value": None, "min": minimum, "status": "N_A"})
        else:
            value = metrics[name]
            status = "PASS" if value + 1e-9 >= minimum else "FAIL"
            rows.append({"metric": name, "value": round(value, 4), "min": minimum, "status": status})
    return rows


def gateway_config() -> dict:
    """The bot's effective configuration (prompt, temperature, RAG parameters)."""
    try:
        req = urllib.request.Request(f"{GATEWAY_URL}/config", headers=headers())
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError):
        return {}


def score(case: dict, answer: str) -> bool:
    text = normalize(answer)
    if case["answerable"]:
        # Passes if ALL keywords show up
        return all(normalize(k) in text for k in case["keywords"])
    # No possible answer: passes if it admits it doesn't know
    return any(m in text for m in REFUSAL_MARKERS)


def git_info() -> dict:
    """The commit the evaluation ran against, and whether there were uncommitted changes.

    Computed OUTSIDE the container (GIT_COMMIT/GIT_DIRTY, set by app/run/run.sh from the full
    checkout) because in here only app/ is mounted, not the repo root with .git: a "git
    status" from inside app/ would see everything outside app/ as deleted. If those variables
    aren't set (e.g. running the script standalone with the full repo in front), it falls back to git.
    """
    if os.getenv("GIT_COMMIT"):
        return {"commit": os.environ["GIT_COMMIT"], "dirty": os.getenv("GIT_DIRTY", "") != ""}

    def git(*args):
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
    try:
        return {
            "commit": git("rev-parse", "--short", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        }
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"commit": None, "dirty": None}


# ── Report: a JSON with everything, and a readable Markdown built from it ───────────────────────

def emoji(ok: bool | None) -> str:
    return "➖" if ok is None else ("✅" if ok else "❌")


def build_report(*, results, metrics, gate_checks, thresholds, golden_md5, cfg, reject_reason=None) -> dict:
    prompt_hash = next((x["prompt_hash"] for x in results if x.get("prompt_hash")), None)
    release = next((x["release"] for x in results if x.get("release")), None)
    temperature = next((x["temperature"] for x in results if x.get("temperature") is not None), None)
    gate_passed = bool(thresholds) and all(f["status"] != "FAIL" for f in gate_checks)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "release": release,
        "git": git_info(),
        "model": {
            "chat": next((x["model"] for x in results if x.get("model")), None),
            "embedding": cfg.get("embedding_model"),
            "temperature": temperature,
            "prompt_hash": prompt_hash,
        },
        "rag": {
            "enabled": cfg.get("rag"),
            "top_k": cfg.get("top_k"),
            "min_similarity": cfg.get("min_similarity"),
            **{k: cfg.get("index", {}).get(k) for k in ("chunking", "n_chunks", "knowledge_hash")},
        },
        "golden": {
            "path": str(GOLDEN),
            "md5": golden_md5,
            "n_questions": len(results),
            "rejected_reason": reject_reason,  # only if it never got to examine (e.g. "empty")
        },
        "metrics": {k: round(v, 4) for k, v in metrics.items()},
        "gate": {
            "enabled": bool(thresholds),
            "passed": gate_passed if thresholds else None,
            "checks": gate_checks,
        },
        "questions": results,
    }


def cell(text) -> str:
    """One Markdown table cell: no pipes or line breaks, they'd break the table."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def md_table(rows: list[list], header: list[str]) -> str:
    sep = ["---"] * len(header)
    return "\n".join(
        "| " + " | ".join(cell(c) for c in row) + " |"
        for row in [header, sep, *rows]
    )


def report_markdown(report: dict) -> str:
    release = report["release"] or "unknown"
    parts = [f"## 🧪 Quality exam — release `{release}`", ""]

    gate = report["gate"]
    if gate["enabled"]:
        title = "✅ PASSED" if gate["passed"] else "❌ REJECTED"
        parts += [f"### {title}", ""]
        rows = [
            [emoji(c["status"] == "PASS"), f"`{c['metric']}`", f"{c['value']:.2f}", f"≥ {c['min']:.2f}"]
            if c["status"] != "N_A" else
            ["➖", f"`{c['metric']}`", "—", f"≥ {c['min']:.2f} (n/a)"]
            for c in gate["checks"]
        ]
        parts += [md_table(rows, ["", "Metric", "Value", "Minimum"]), ""]
    elif report["golden"]["rejected_reason"]:
        parts += ["### ❌ REJECTED", "", f"_{report['golden']['rejected_reason']}_", ""]
    else:
        parts += ["### ℹ️ No quality gate configured (informational only)", ""]

    m = report["metrics"]
    if m:
        summary = (
            f"**{report['golden']['n_questions']} questions** · "
            f"overall accuracy `{m.get('accuracy', 0):.2f}` · "
            f"average latency `{m.get('avg_latency_s', 0):.1f}s` · "
            f"`{m.get('total_tokens', 0):.0f}` total tokens"
        )
        parts += [summary, ""]

    model = report["model"]
    commit = f"commit `{report['git']['commit']}`" if report["git"]["commit"] else None
    dirty = "with uncommitted changes" if report["git"]["dirty"] else None
    if model["chat"]:
        detail = f"Model `{model['chat']}` · prompt `{model['prompt_hash']}` · temperature `{model['temperature']}`"
        if commit:
            detail += f" · {commit}" + (f" ({dirty})" if dirty else "")
        parts += [detail, ""]
    elif commit:
        parts += [commit + (f" ({dirty})" if dirty else ""), ""]

    if report["questions"]:
        parts += ["<details>", f"<summary>Detail by question ({len(report['questions'])})</summary>", ""]
        rows = [
            [emoji(q["ok"]), f"`{q['id']}`", q["question"], q.get("answer") or "_(no answer)_", emoji(q["retrieval_ok"]), f"{q['latency_s']:.1f}s"]
            for q in report["questions"]
        ]
        parts += [md_table(rows, ["", "id", "Question", "Bot's answer", "Retrieval", "Latency"]), "", "</details>"]

    return "\n".join(parts)


def write_report(report: dict) -> None:
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)  # eval/report/ doesn't exist until the first run
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = report_markdown(report)
    MD_PATH.write_text(md + "\n", encoding="utf-8")
    print("\n" + md)


def reject(reason: str) -> None:
    """Empty golden set or another reason the exam couldn't even run: a report is still written,
    so the history has no gaps."""
    report = build_report(
        results=[], metrics={}, gate_checks=[], thresholds={}, golden_md5=None, cfg={}, reject_reason=reason,
    )
    write_report(report)  # already prints "### ❌ REJECTED" + the reason: nothing to repeat here
    sys.exit(1)


def examine():
    thresholds = read_thresholds()  # before examining: if the config is wrong, fail now

    if not GOLDEN.exists() or not (cases := [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]):
        # Without questions there's nothing proving the bot answers well, so nothing gets published.
        # Not a bug in the exam, it's the quality gate doing its job.
        reject(f"{GOLDEN} has no questions: add at least 2-3 per document")

    golden_md5 = hashlib.md5(GOLDEN.read_bytes()).hexdigest()
    cfg = gateway_config()

    results = []
    for case in cases:
        r = ask_question(case["question"])
        ok = not r.get("error") and score(case, r["answer"])
        sources = r.get("sources") or []
        # Is the right document among the retrieved chunks? (only with RAG and an answerable question)
        retrieval_ok = (
            case["source"] in [s.split("#")[0] for s in sources] if sources and case["source"] else None
        )
        results.append({
            **case,
            "answer": r["answer"],
            "model": r["model"],
            "release": r.get("release"),
            "prompt_hash": r.get("prompt_hash"),
            "temperature": r.get("temperature"),
            "sources": sources,
            "retrieval_ok": retrieval_ok,
            "ok": ok,
            "tokens": r["tokens"],
            "latency_s": round(r["latency_s"], 2),
            "error": r.get("error"),
        })
        print(f"{'OK  ' if ok else 'FAIL'} {case['id']} ({r['latency_s']:.1f}s) {case['question']}")

    answerable_results = [x for x in results if x["answerable"]]
    unanswerable_results = [x for x in results if not x["answerable"]]
    metrics = {
        "accuracy": sum(x["ok"] for x in results) / len(results),
        "accuracy_answerable": sum(x["ok"] for x in answerable_results) / len(answerable_results) if answerable_results else 0.0,
        # How many of the unanswerable questions it admitted not knowing (the rest are made up)
        "refusal_rate": sum(x["ok"] for x in unanswerable_results) / len(unanswerable_results) if unanswerable_results else 0.0,
        "avg_latency_s": sum(x["latency_s"] for x in results) / len(results),
        "avg_tokens": sum(x["tokens"] for x in results) / len(results),
        "total_tokens": sum(x["tokens"] for x in results),
    }
    with_retrieval = [x for x in answerable_results if x["retrieval_ok"] is not None]
    if with_retrieval:
        # Beyond the answer: did the search bring back the right document?
        metrics["retrieval_recall"] = sum(x["retrieval_ok"] for x in with_retrieval) / len(with_retrieval)

    gate_checks = check_thresholds(metrics, thresholds)
    gate_passed = all(f["status"] != "FAIL" for f in gate_checks)

    report = build_report(
        results=results, metrics=metrics, gate_checks=gate_checks, thresholds=thresholds,
        golden_md5=golden_md5, cfg=cfg,
    )
    write_report(report)  # already prints the full report (table, gate, detail): nothing to repeat here

    if thresholds:
        sys.exit(0 if gate_passed else 1)


if __name__ == "__main__":
    examine()
