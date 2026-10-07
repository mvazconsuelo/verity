# Lab 01 — RAG

**You learn:** what RAG actually is and why it exists, what a chunk and an embedding vector are,
section-based chunking, similarity search, and why there's a confidence threshold before answering.

## What is RAG, actually?

A plain LLM only knows what it saw during training — it has no idea what *your* shipping policy
says, because that text was never part of its training data. You could try pasting your entire
knowledge base into every prompt, but that doesn't scale: there's a limit to how much text a model
can take at once, it costs more the more you send, and the more irrelevant text you include, the
worse and slower the answer tends to get.

**R**etrieval-**A**ugmented **G**eneration splits the problem into two separate steps instead of one:

1. **Retrieval**: before asking the model anything, search your own documents for the few pieces
   that are actually relevant to this specific question.
2. **Generation**: hand the model *only* those relevant pieces, as context, along with the question.

The model never "knows" your documents ahead of time — every single request, you re-tell it the
relevant part, fresh. That's also why it's possible to answer honestly with "I don't have that
information": if retrieval doesn't find anything confident enough, there's no context to make up an
answer from in the first place (see [the confidence threshold](#the-confidence-threshold) below).

### Why split documents into chunks at all?

You can't usefully ask "is this relevant to the question?" about an entire document at once — a long
document might have one relevant paragraph and many irrelevant ones, and comparing the whole thing
as a single block would blur that one good match into noise. So documents get cut into smaller
pieces — **chunks** — small enough that each one is about roughly *one* thing, so a search can tell
"this piece is relevant" from "this piece isn't" with real precision.

### What's actually inside a vector?

An **embedding model** (`bge-m3` here) reads a piece of text and outputs a fixed-length list of
numbers — in this project, 1024 of them. That list is the **vector** (or "embedding"). It isn't
arbitrary: the model was trained so that texts with similar *meaning* end up with vectors that sit
close together in that 1024-dimensional space, and texts with different meaning end up far apart —
regardless of the exact words used. "How long does shipping take?" and "when will my order arrive?"
land close together even though they share almost no words in common.

"Close together" gets measured with **cosine similarity**: a number (0 to 1, for these normalized
vectors) that says how aligned two vectors are — 1 means essentially the same meaning, 0 means
unrelated. That's the `score` you'll see below, and the number `MIN_SIMILARITY` gets compared against.

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

In English: `# Shipping` / `## Timelines` (standard: 3-5 business days, express: 24-48h) /
`## Costs` ($4.99 standard, free over $50) / `## Coverage` (national only).

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
