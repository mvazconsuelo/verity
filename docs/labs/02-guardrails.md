# Lab 02 — Guardrails

**You learn:** how to recognize a greeting by meaning (not by words) without spending an extra model
call, and where this module's job intentionally stops.

## The problem it solves

If someone types "good afternoon", "what's up" or "hey", none of those share a single word with
"hi" — an `if "hi" in question` won't catch all of them. But the *meaning* is the same, and
embeddings already capture that.

## Semantic routing, not keyword matching

[`rag/build_index.py`](../../app/rag/build_index.py) defines a fixed list of references
(`GREETING_REFERENCES`: "hola", "buenos días", "qué tal"...) and embeds them **once**, when the
index gets built — stored in `index.db`'s `phrases` table.

[`gateway/guardrails.py`](../../app/gateway/guardrails.py), `is_greeting()`: compares the question's
vector (the same one already computed for RAG, zero extra calls) against those reference vectors. If
the maximum similarity clears `MIN_SIMILARITY_GREETING` (0.75 — stricter than RAG's threshold,
because a false positive here is harder to notice), it answers directly:

```python
GREETING_ANSWER = "¡Hola! ¿En qué te puedo ayudar?"
```

**Try it yourself:** ask "buenas tardes" and then "hola" — neither spends a call to the chat model
(watch the latency, or `docker compose logs ollama` while you ask: no `/api/chat` request should
show up for either one).

## Why the threshold is higher than RAG's

`MIN_SIMILARITY_GREETING = 0.75` versus `MIN_SIMILARITY = 0.5`. A greeting misdetected as a real
question only costs one extra LLM call (cheap). A real question misdetected as a greeting never
gets a real answer at all — the cost of being wrong is higher in that direction, so the threshold is
more conservative.

## The module's boundary, on purpose

> "Scope, on purpose: this module is for SMALL, deterministic decisions — not a place to represent
> business topics or actions."

`guardrails.py` decides exactly two things: is there enough confidence? is it a greeting? Nothing
like "if it asks about shipping, answer with the shipping template" — **that always goes through
real RAG**, never a fixed answer in this module. The boundary is deliberate: mixing "small,
deterministic decisions" with "business logic" in the same place is, over time, how a small module
becomes unmaintainable.

## Adding a new category

If you ever need to recognize another intent (say, "I want to talk to a human"), the pattern already
exists: `index_store.py`'s `phrases` table is generic by `category` — today only `"greeting"` is
populated, but `save_phrases()`/`read_phrases()` aren't greeting-specific. Before building it: is it
really needed, or is it enough for RAG to answer "I don't have that information" and have a human
review it later? Don't add the category until you have that answer.

---

**[Español](../es/labs/02-guardrails.md)**
