# 💥 Break the Platform

Real failures, provoked on purpose. The pattern for each one: **provoke → what you see → where to
look → cause → fix → lesson.** Nothing here is hypothetical — all of them were reproduced running
the project exactly as it sits in the repo.

---

## 1. The gateway won't start

**Provoke:**
```bash
cd app && unset API_KEYS && docker compose up gateway
```

**What you see:** the `gateway` container exits immediately, never sits in `Restarting`. In the logs:
```
RuntimeError: Set API_KEYS (export it yourself before bringing up the stack; or AUTH_DISABLED=true for testing only)
```

**Where to look:** [`gateway/auth.py`](../../app/gateway/auth.py) — the check runs when the module
is *imported*, not on the first request.

**Cause:** on purpose: closed by default. There's no version of the gateway that accepts traffic
without a key "by accident" — either you have it, or it simply doesn't start.

**Fix:** `export API_KEYS=whatever` (or `AUTH_DISABLED=true`, **testing only**) before
`docker compose up`.

**Lesson:** fail-fast at startup is cheaper than fail-open in production. You pay the cost once, when
bringing the stack up — not every time someone sends a request without a key.

---

## 2. I edited a document and the bot keeps answering the old one

**Provoke:** edit `app/knowledge/envios.md`, save, and ask the bot about it without rebuilding
anything.

**What you see:** the answer is still based on the previous content.

**Where to look:** [`app/docker/gateway/Dockerfile`](../../app/docker/gateway/Dockerfile) — it has
`COPY knowledge ./knowledge`.

**Cause:** `knowledge/` gets baked into the image at build time, it isn't mounted live from disk.
Editing the file on your filesystem doesn't change anything inside a container that's already running.

**Fix:** `docker compose build && docker compose up -d` (or, simpler, `make local` again — `run.sh`
already does the build).

**Lesson:** the whole image is the unit of version. One image *tag* fixes code + prompt + documents
at once — by design, not by accident (see [Architecture](architecture.md)).

---

## 3. The index was built with a different embedding model

**Provoke:** bring the stack up, then change `EMBEDDING_MODEL` in `config.env` to something else
(e.g. `nomic-embed-text`) and restart only the `gateway` without rebuilding the index.

**What you see:** `500` on any question that uses RAG:
```
The index was built with 'bge-m3' and the gateway uses 'nomic-embed-text': rebuild it with make up
```

**Where to look:** [`gateway/retrieval.py`](../../app/gateway/retrieval.py), `load_index()`.

**Cause:** vectors from two different models aren't comparable to each other — mixing them would
give meaningless search results, silently, with no visible error. This check exists to turn that
silence into a loud error.

**Fix:** rebuild the index with the same model the gateway uses (`docker compose up` — the `indexer`
reruns if the config changed).

**Lesson:** a mismatched model is worse than an error: it answers *something*, just wrong. Better to
break loud and early than to degrade silently.

---

## 4. The golden set is empty

**Provoke:**
```bash
cd app && mv eval/golden.jsonl /tmp/golden.bak && echo -n > eval/golden.jsonl
docker compose run --rm evaluator python eval/run_eval.py
```

**What you see:**
```
### ❌ REJECTED

_eval/golden.jsonl has no questions: add at least 2-3 per document_
```
and the process exits with code `1`.

**Where to look:** [`app/eval/run_eval.py`](../../app/eval/run_eval.py), `examine()`.

**Cause:** without questions there's nothing proving the bot answers well — rejecting is the quality
gate doing its job, not a bug.

**Fix:** `mv /tmp/golden.bak eval/golden.jsonl`. In real life: write 2-3 questions per document
before trusting an answer (see [Lab 05](labs/05-evaluation.md)).

**Lesson:** an empty evaluation set isn't "no opinion" — here it's an explicit rejection.

---

## 5. SeaweedFS: "the specified bucket does not exist"

**Provoke:** `docker compose --profile dvc up -d seaweedfs` (a clean SeaweedFS, no bucket) and then
`dvc push` straight away, skipping `app/dvc-setup.sh`.

**What you see:**
```
ERROR: unexpected error - The specified bucket does not exist: An error occurred (NoSuchBucket)
when calling the ListObjectsV2 operation: The specified bucket does not exist
```

**Where to look:** [`app/dvc-setup.sh`](../../app/dvc-setup.sh) — the step that runs
`s3.bucket.create -name knowledge` against `weed shell`.

**Cause:** unlike other self-hosted S3 options, SeaweedFS does **not** auto-create the bucket on the
first `PutObject`. It has to be created by hand (or by a script) before you can write to it.

**Fix:** run `make dvc-setup` — it's idempotent, run it as many times as you want.

**Lesson:** "S3-compatible" doesn't mean "identical to S3 in every detail" — bucket auto-creation is
exactly one of the places where it differs. It's worth testing the full path (create → upload →
download) before assuming it, instead of copying instructions from another project.

---

## 6. Rate limit: `429` with `Retry-After`

**Provoke:**
```bash
for i in 1 2 3 4; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/config -H "x-api-key: your-key"; done
```

**What you see:** the first `RATE_LIMIT_PER_MINUTE` (30 by default) return `200`; the next one
returns `429` with the `retry-after: 60` header.

**Where to look:** [`gateway/auth.py`](../../app/gateway/auth.py), `rate_limit()` — a sliding window
per API key, in memory (no Redis: for a single replica, it's enough).

**Cause:** the limit is **per key, not per IP**. An invalid request (say, an empty question that
returns `422`) counts too — on purpose, so it isn't free to send garbage faster than real questions.

**Fix:** wait for `Retry-After`, or use another key (`API_KEYS` accepts several, comma-separated).

**Lesson:** a "per IP" limit is easy to dodge (several IPs). Per key is harder to dodge and easier to
audit (you know exactly who asked for what).

---

## 7. `ORIGIN_VERIFY_SECRET`: by default, does nothing

**Provoke:** send a request with no special header, with the stack freshly up (`config.env`
untouched).

**What you see:** it works normally — no `x-origin-verify` header needed.

**Where to look:** [`gateway/auth.py`](../../app/gateway/auth.py), `verify_origin()`:
`if ORIGIN_VERIFY_SECRET:`.

**Cause:** in this fully local setup there's no proxy/CDN in front injecting a secret header —
requiring one anyway would break the normal use case. The check turns itself off when the variable
is empty (which is the default).

**Fix:** none needed — that's the expected behavior. If you ever put a tunnel or proxy in front, set
`ORIGIN_VERIFY_SECRET` to whatever that proxy injects, and the check starts being enforced.

**Lesson:** a security variable that's "optional by default, strict if you set it" is more secure in
practice than one that *always* requires something — because the latter tempts everyone into setting
a fixed, trivial value everywhere "to make it work," which is worse than having nothing at all.

---

Found a real failure that's not here? Add it in the same format — it's the most honest way to
document a system: by showing how it breaks, not just how it's supposed to work.

---

**[Español](../es/break.md)**
