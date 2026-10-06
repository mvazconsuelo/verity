"""Builds the RAG index: chunks knowledge/, computes one vector per chunk and saves it to
artifacts/index/index.db (SQLite + sqlite-vec: see rag/index_store.py).

    python -m rag.build_index

If the documents have errors, nothing gets built (the same checks as rag.validate_knowledge).
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np

from rag import index_store
from rag.loaders import MAX_CHARS, OVERLAP_CHARS, analyze, hash_documents

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
DOCS_DIR = Path(os.getenv("DOCS_DIR", "knowledge"))
INDEX_DIR = Path(os.getenv("INDEX_DIR", "artifacts/index"))
BATCH = 32  # texts per call to Ollama

# Reference phrases for semantic routing (gateway/guardrails.py). Embedded here and saved into
# index.db's `phrases` table (rag/index_store.py) — same Ollama call as the documents, so the
# gateway never needs to talk to Ollama just to load these at startup.
#
# NOT a catalog of business topics: it's for small, deterministic routing decisions only (like
# "is this a greeting?") — a question about the business always goes through RAG/knowledge/*.md,
# never a hardcoded entry here.
GREETING_REFERENCES = ["hola", "buenos días", "buenas tardes", "buenas noches", "qué tal", "cómo estás", "cómo andás", "hey"]


def embeddings(texts: list[str]) -> np.ndarray:
    """One vector per text, normalized (length 1): so the dot product is the cosine similarity."""
    batches = []
    for i in range(0, len(texts), BATCH):
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/embed",
            data=json.dumps({"model": EMBEDDING_MODEL, "input": texts[i : i + BATCH]}).encode(),
            headers={"content-type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            batches.append(np.array(json.load(r)["embeddings"], dtype=np.float32))
    m = np.vstack(batches)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def main() -> int:
    report = analyze(DOCS_DIR)
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    if report.errors:
        for error in report.errors:
            print(f"ERROR: {error}")
        print("Index not built: fix the documents.")
        return 1

    vectors = embeddings([c["text"] for c in report.chunks])

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "embedding_model": EMBEDDING_MODEL,
        "chunking": "md: sections",
        "chunk_max_chars": MAX_CHARS,
        "chunk_overlap_chars": OVERLAP_CHARS,
        "n_documents": len(report.documents),
        "n_chunks": len(report.chunks),
        "knowledge_hash": hash_documents(DOCS_DIR, report.documents),
        "dimension": int(vectors.shape[1]),
    }
    con = index_store.create(INDEX_DIR, dimension=meta["dimension"], meta=meta)
    index_store.save(con, vectors, report.chunks)

    categories = ["greeting"] * len(GREETING_REFERENCES)
    phrase_vectors = embeddings(GREETING_REFERENCES)
    index_store.create_phrases(con, dimension=meta["dimension"])
    index_store.save_phrases(con, phrase_vectors, categories, GREETING_REFERENCES)

    con.close()
    print(
        f"Index saved to {INDEX_DIR / index_store.FILE}: {len(report.documents)} documents, {len(report.chunks)} chunks, "
        f"{len(GREETING_REFERENCES)} reference phrases, vectors of {vectors.shape[1]} numbers"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
