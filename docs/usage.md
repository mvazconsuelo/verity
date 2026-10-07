# Using the bot

Two ways to talk to it once it's up (`make local`, or `docker compose up` in `app/`): the interactive
script, or the raw API with `curl`. Both hit the same gateway — there's no difference in what you
can do, just how you do it.

## Option 1: `chat.sh`

```bash
make chat
# or directly: app/run/chat.sh
```

A plain read-eval-print loop around `/ask`: type a question, get an answer, repeat. Blank line or
Ctrl+D to exit. If the gateway was started with real API keys (not `AUTH_DISABLED=true`), pass yours:

```bash
API_KEY=your-key app/run/chat.sh
```

It's [~50 lines of bash](../app/run/chat.sh) — read it if you want to see the minimum needed to talk
to the API from a script, with no dependencies beyond `curl` and `python3`.

## Option 2: the raw API

Three endpoints. All of them (except `/health`) need the `x-api-key` header; none of them need
anything else **unless** you've set `ORIGIN_VERIFY_SECRET` yourself (empty by default — see
[`gateway/auth.py`](../app/gateway/auth.py)).

### `GET /health`

No API key needed — this is the one endpoint anything (a load balancer, a script, you) can call
without credentials, specifically so uptime checks don't need a secret.

```bash
curl http://localhost:8000/health
```
```json
{"status": "ok", "release": "local"}
```

### `GET /config`

Needs `x-api-key`. The bot's effective configuration — what the evaluator reads before running the
exam, and a quick way to check what you're actually talking to.

```bash
curl http://localhost:8000/config -H "x-api-key: your-key"
```
```json
{
  "release": "local",
  "prompt_hash": "a1b2c3d4",
  "temperature": 0,
  "model": "qwen2.5:1.5b",
  "rag": true,
  "embedding_model": "bge-m3",
  "top_k": 3,
  "min_similarity": 0.5,
  "min_similarity_saludo": 0.75,
  "index": {"embedding_model": "bge-m3", "n_documents": 4, "n_chunks": 13, "dimension": 1024, "...": "..."}
}
```

### `POST /ask`

Needs `x-api-key`. The only endpoint that costs a model call (unless a guardrail short-circuits it —
see [Lab 02](labs/02-guardrails.md)).

```bash
curl -X POST http://localhost:8000/ask \
  -H "content-type: application/json" \
  -H "x-api-key: your-key" \
  -d '{"question": "¿cuánto tarda el envío estándar?"}'
```
```json
{
  "answer": "El envío estándar tarda de 3 a 5 días hábiles.",
  "model": "qwen2.5:1.5b",
  "tokens": 14,
  "release": "local",
  "prompt_hash": "a1b2c3d4",
  "temperature": 0,
  "sources": ["envios.md#Plazos"]
}
```

`sources` tells you exactly which document and section backed the answer (empty if the question got
short-circuited by a guardrail — a greeting, or "I don't have that information"). `question` is
required, 1 to `MAX_QUESTION_CHARS` (2000 by default) — anything outside that range is a `422`
before the request ever reaches RAG.

### Errors you'll actually see

| Status | When | See |
| --- | --- | --- |
| `401` | Missing or wrong `x-api-key` | [`gateway/auth.py`](../app/gateway/auth.py) |
| `403` | `ORIGIN_VERIFY_SECRET` is set and the header doesn't match (doesn't apply by default) | [Break the Platform #7](break.md#7-origin_verify_secret-by-default-does-nothing) |
| `422` | Question empty or too long | Pydantic validation in [`gateway/endpoints.py`](../app/gateway/endpoints.py) |
| `429` | Rate limit hit | [Break the Platform #6](break.md#6-rate-limit-429-with-retry-after) |
| `502` | Ollama didn't respond | `gateway/endpoints.py`, catches `httpx.HTTPError` |

## What to put in `app/knowledge/`

This is what actually feeds the embeddings — get it right and search works; get it wrong and the
bot either can't find anything or returns noisy, unrelated chunks. Full mechanics in
[Lab 01](labs/01-rag.md); here's what to actually do when writing a document:

1. **One `.md` file per topic area is plenty** — you don't need one file per fact. The project's own
   `app/knowledge/envios.md` covers shipping times, costs and coverage in one file, split into
   sections.
2. **Structure with `## ` headings, one subtopic per section.** Each `##` section becomes its own
   chunk — a question matches a *section*, not a whole document. A document with no `##` at all
   gets chunked by raw character count instead, which is far less precise (it can cut a sentence
   wherever `CHUNK_MAX_CHARS` happens to land).
3. **Keep sections focused and reasonably short.** If a section runs past `CHUNK_MAX_CHARS` (1200
   characters by default), it gets split further with overlap — not wrong, but a sign the section
   is probably covering more than one topic and would search better split by hand into two `##`s.
4. **Don't bury the answer in a huge paragraph of unrelated facts.** Compare:

   ```markdown
   <!-- good: a question about cost only pulls in cost-relevant text -->
   ## Costos
   El envío estándar cuesta $4.99, gratis en pedidos desde $50.

   <!-- worse: shipping cost, return policy and store hours all in one section -->
   ## Información general
   El envío estándar cuesta $4.99... Las devoluciones se aceptan hasta 30 días...
   El local abre de 9 a 18...
   ```

   The first version means a search for "shipping cost" retrieves *only* shipping-cost text. The
   second drags in unrelated content as part of the same chunk, diluting the match.
5. **Validate before trusting it's picked up:**
   ```bash
   docker run --rm -v "$PWD/app":/work -w /work python:3.11-slim python3 -m rag.validate_knowledge knowledge
   ```
   Catches format issues, oversized files (`MAX_FILE_KB`), and unsupported extensions (only `.md`
   is read — anything else is silently ignored, with a warning).
6. **Rebuild after every change** — `knowledge/` is baked into the image at build time, not mounted
   live. See [Break the Platform #2](break.md#2-i-edited-a-document-and-the-bot-keeps-answering-the-old-one)
   if this bites you.
7. **Write 2-3 golden-set questions per document as you go** (see [Lab 05](labs/05-evaluation.md)) —
   it's much easier to write them while you remember what you just put in the document than to
   reconstruct it later.

---

**[Español](es/usage.md)**
