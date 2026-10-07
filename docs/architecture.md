# Architecture

![Verity architecture](images/architecture.svg)

## The path of a question

1. **`user → gateway`** (`POST /ask`): the gateway checks the API key, the rate limit and the
   question's length before touching anything else (`gateway/auth.py`).
2. **`gateway → ollama`**: the question gets embedded with `bge-m3` (the same model that indexed
   the documents — `retrieval.py` refuses to start if they don't match, see below).
3. **Guardrails, before spending a call on the chat model** (`gateway/guardrails.py`):
   - Does the question's vector look more like a greeting than like any chunk? → answers fixed,
     no RAG, no LLM.
   - Is the best chunk found below the confidence threshold (`MIN_SIMILARITY`)? → answers "I don't
     have that information," no LLM.
4. If it passed the guardrails: the retrieved context gets assembled into the prompt, and only then
   does it call the chat model (`qwen2.5:1.5b`).

## What's NOT in the path of a question

- **`indexer`**: runs once at stack startup (`depends_on: service_completed_successfully` in
  `docker-compose.yml`) and exits. The gateway never re-indexes on the fly — if you change
  `knowledge/`, the image has to be rebuilt.
- **`evaluator`**: never starts with `docker compose up` (it has `profiles: ["evaluator"]`). It's
  invoked by hand, against a gateway that's already up.
- **`DVC` + `SeaweedFS`**: `"dvc"` profile, also doesn't start with `up`. Solves a different problem
  (versioning the source documents) that has nothing to do with answering questions.
- **`GitHub Actions`**: doesn't even run on your machine — and **never reaches the runtime**. There's
  no arrow from CI to any container in the diagram, on purpose: see
  [Lab 06](labs/06-github-actions-ci.md) for why.

## Why the index is read-only from the gateway

`rag/build_index.py` (the `indexer`) is the only thing that writes `index.db`. The gateway
(`retrieval.py`) opens it once (`@lru_cache`) and never writes to it again. This means the gateway
could have multiple replicas without coordinating with each other — none of them writes anything to
another. (Today a single replica runs; the property comes for free if more are ever needed.)

## Why `knowledge/` gets baked into the image instead of mounted live

The gateway's Dockerfile does `COPY knowledge ./knowledge` — it's part of the image, not a volume.
This means **the whole image is the unit of version**: an image tag fixes the code, the prompt and
the documents it's going to answer with, all at once. Changing a document without rebuilding the
image has no effect (see [Lab 03](labs/03-docker.md) for the detail, and
[Break the Platform #2](break.md#2-i-edited-a-document-and-the-bot-keeps-answering-the-old-one) to
watch it fail live).

---

**[Español](../es/architecture.md)**
