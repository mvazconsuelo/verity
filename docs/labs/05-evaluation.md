# Lab 05 — Evaluation

**You learn:** what a "prompt" and a "golden set" actually are, how to objectively measure whether
the bot answers well, what a quality gate is, and why every answer carries a `prompt_hash` pinned
to it.

## What's a "prompt", actually?

The **prompt** is the literal text sent to the model as instructions — in this project,
[`system.md`](../../app/prompts/system.md) (who the bot is, what it's allowed and not allowed to do)
combined with [`template.md`](../../app/prompts/template.md) (how the question and the retrieved
context from RAG get assembled into the final message the model sees). There's no separate "behavior
code" deciding tone, refusals, or how retrieved chunks get used — all of that comes from this text.
Change the wording and you change the bot's behavior, with zero code changes. That's exactly why it's
worth versioning and hashing (`prompt_hash`, below) with the same care as code: it effectively *is*
the behavior.

## What's a "golden set", and why evaluate at all?

A **golden set** is a fixed list of questions with known-correct expectations, used to measure
quality the same way, every time — the same idea as a test suite in regular software, adapted to a
system that answers in free-form text instead of returning a fixed value (you can't assert
`answer == "3 to 5 days"` on something an LLM phrases differently each time — hence `keywords`
matching, not exact text, below). Without a golden set, "did my prompt change make the bot better or
worse?" is just a feeling. With one, it's a number you can compare run over run — and a gate that can
block a bad change before it reaches anyone (see [the quality gate](#the-quality-gate) below).

## `golden.jsonl`, line by line

[`app/eval/golden.jsonl`](../../app/eval/golden.jsonl), one question per line. The real file is in
Spanish (matching the real documents — see [Lab 01](01-rag.md)); translated here for this guide:

```json
{"id": "q01", "question": "How long does standard shipping take?", "expected": "3 to 5 business days.", "keywords": ["3 to 5"], "source": "shipping.md", "answerable": true}
```

- `answerable: true` → passes if the answer contains **all** the `keywords` (not an exact text
  match — the model can phrase it differently, what matters is that the fact is in there).
- `answerable: false` → passes if the answer *admits it doesn't know* (a fixed list of phrases in
  [`run_eval.py`](../../app/eval/run_eval.py): "no tengo", "no dispongo"... — "I don't have", "I
  don't offer"). These are questions
  made up on purpose, with no answer in any document — they measure whether the bot makes things up
  when it doesn't know, which is the most expensive mistake a customer-support bot can make.

They're written by hand — there used to be an automatic generator using `qwen2.5:1.5b` that got
dropped: with such a small model, the questions it invented needed so much manual review that it
didn't actually save time.

## The metrics

`run_eval.py` computes, over the whole set:

| Metric | What it measures |
| --- | --- |
| `accuracy` | % of all questions that passed (answerable + unanswerable) |
| `accuracy_answerable` | % of the answerable ones that got answered correctly |
| `refusal_rate` | % of the unanswerable ones the bot correctly declined |
| `retrieval_recall` | Of the answerable ones, % where the right document showed up among the retrieved chunks (stricter than `accuracy`: you can't "get lucky" without this) |

## The quality gate

`config.env`:
```
EVAL_MIN_ACCURACY_ANSWERABLE=0.90
EVAL_MIN_REFUSAL_RATE=0.90
EVAL_MIN_RETRIEVAL_RECALL=0.90
```

Empty = not required (see `# EVAL_MIN_ACCURACY=0.90`, commented out: today the overall metric isn't
enforced, only the three specific ones). If any configured metric doesn't hit the minimum,
`run_eval.py` exits with code `1` — useful if you ever wire it back into something automated.

**Try it yourself — lower a threshold artificially and watch something pass that used to fail:**
```bash
EVAL_MIN_RETRIEVAL_RECALL=0.0 docker compose run --rm evaluator python eval/run_eval.py
```

## `prompt_hash` and `release`

Every `/ask` response (see [`gateway/endpoints.py`](../../app/gateway/endpoints.py)) includes:

- **`prompt_hash`**: an 8-character SHA-256 hash of `system.md` + `template.md`. Changes if the
  prompt's *text* changes, even if the filename stays the same — there's no way to touch the prompt
  without it showing up in every response.
- **`release`**: the tag of the image that's answering (`APP_VERSION`).

The exam's report (`eval/report/eval-result.json` + `.md`) stores both alongside the git commit —
so an old report always says exactly which code, which prompt and which documents it was using,
without having to reconstruct it from memory.

## Running the exam

```bash
make local   # pick "Examine" from the menu
```

The full report lands in `app/eval/report/eval-result.md` (readable) and `.json` (for scripts).
Check the `<details>` table with the per-question breakdown — it includes whether retrieval brought
back the right document (✅/❌/➖), not just whether the final answer passed.

---

**[Español](../es/labs/05-evaluation.md)**
