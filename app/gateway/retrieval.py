"""Pure RAG mechanics: open the vector index (rag/index_store.py), embed the question, and return
the TOP_K most similar chunks with their score. No policy decisions here — that's guardrails.py.
"""
import os
from functools import lru_cache
from pathlib import Path

import httpx
import numpy as np
from fastapi import HTTPException

from rag import index_store

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
INDEX_DIR = Path(os.getenv("INDEX_DIR", "/srv/artifacts/index"))
TOP_K = int(os.getenv("TOP_K", "3"))


@lru_cache(maxsize=1)
def load_index() -> tuple:
    """Index built by rag/build_index.py: (SQLite connection, metadata). Opened only once."""
    if not (INDEX_DIR / index_store.FILE).exists():
        raise HTTPException(status_code=500, detail=f"Missing index in {INDEX_DIR}: the indexer hasn't built it (check: docker compose logs indexer)")
    con = index_store.open_index(INDEX_DIR)
    meta = index_store.read_meta(con)
    if meta.get("embedding_model") != EMBEDDING_MODEL:
        # Vectors from different models aren't comparable: without this check the bot would silently answer worse
        raise HTTPException(
            status_code=500,
            detail=f"The index was built with '{meta.get('embedding_model')}' and the gateway uses '{EMBEDDING_MODEL}': rebuild it with make up (the indexer reruns when the config changes)",
        )
    return con, meta


async def retrieve(client: httpx.AsyncClient, question: str) -> tuple[np.ndarray, list[tuple[float, dict]]]:
    """The question's vector (normalized, for guardrails.py) and the TOP_K most similar chunks,
    with their similarity."""
    con, _ = load_index()
    r = await client.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBEDDING_MODEL, "input": question})
    r.raise_for_status()
    q = np.array(r.json()["embeddings"][0], dtype=np.float32)
    q = q / np.linalg.norm(q)
    return q, index_store.search(con, q, TOP_K)
