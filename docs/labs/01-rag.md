# Lab 01 — RAG

**You learn:** section-based chunking, embeddings, similarity search, and why there's a confidence
threshold before answering.

## The example document

[`app/knowledge/envios.md`](../../app/knowledge/envios.md):

```markdown
# Envíos

## Plazos
El envío estándar tarda de 3 a 5 días hábiles. El envío express tarda de 24 a 48 horas.

## Costos
El envío estándar cuesta $4.99, gratis en pedidos desde $50...

## Cobertura
Enviamos a todo el territorio nacional...
```

(The bot's own documents and answers stay in Spanish on purpose — see `prompts/system.md`. The
mechanics below are language-agnostic.)

## How it gets chunked

[`rag/loaders.py`](../../app/rag/loaders.py), function `chunk_md()`: splits the text on every
`## ` (a `###` does NOT count as a split — it's a subheading inside the same section). The title
(`# Envíos`) gets prepended to every chunk, so each one is understandable without the rest of the
document. `envios.md` produces 3 chunks: one for `Plazos`, `Costos` and `Cobertura` each.

If a section is longer than `CHUNK_MAX_CHARS` (1200 by default), it gets split into several with
`CHUNK_OVERLAP_CHARS` (150) of overlap — so a sentence doesn't end up cut right at the boundary
between two chunks, out of context for both.

**Try it yourself:**
```bash
docker run --rm -v "$PWD/app":/work -w /work python:3.11-slim python3 -m rag.validate_knowledge knowledge
```

## How it gets embedded and indexed

[`rag/build_index.py`](../../app/rag/build_index.py) (the `indexer` service, runs once at startup):
asks Ollama for one vector per chunk (`bge-m3`), and saves them into `index.db`
([`rag/index_store.py`](../../app/rag/index_store.py), on top of `sqlite-vec`) along with metadata
(`embedding_model`, `n_chunks`, `knowledge_hash`).

## How it gets searched

[`gateway/retrieval.py`](../../app/gateway/retrieval.py), `retrieve()`: embeds the question with the
same model, and returns the `TOP_K` (3 by default) most similar chunks by cosine similarity.

## The confidence threshold

The most similar chunk has a *score* between 0 and 1. If it doesn't reach `MIN_SIMILARITY` (0.5 by
default), the bot **doesn't call the chat model at all** — it answers "I don't have that
information." directly (`gateway/guardrails.py`, `is_confident()`). This stops the model from
"making up" an answer, on a question that's off-topic, using whatever wrong context it happened to
find.

**Try it yourself:** ask something that has nothing to do with your business (`"what's the capital
of France?"`) and check that the answer doesn't spend a single LLM call — compare the latency
against a real question.

## See what got indexed

```bash
make local   # pick "View the index" from the menu
```

Shows you, chunk by chunk, exactly what the gateway has available to search — useful for debugging
"why didn't the bot find this?" without guessing.

---

**[Español](../es/labs/01-rag.md)**
