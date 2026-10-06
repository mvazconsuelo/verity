"""The policy decisions applied to a retrieved result, before anything reaches the chat model:

    is_confident()                is the best chunk similar enough to trust an answer on it? If
                                   not, refuse without spending a call on the LLM.
    load_phrases()/is_greeting()   "semantic routing": recognizes a GREETING by meaning
                                   (embeddings), not by matching words — "good morning" or "how's
                                   it going" route the same as "hi" even though they share no word
                                   with GREETING_REFERENCES. Their vectors are computed once at
                                   startup (by the indexer, saved into index.db's `phrases` table)
                                   and compared against the same vector retrieval.py already
                                   computes for RAG: no extra call to the chat model.

Both is_confident() and is_greeting() take the same normalized question vector that
retrieval.retrieve() returns.

Scope, on purpose: this module is for SMALL, deterministic decisions (today: confidence, and is it
a greeting?) — not a place to represent business topics or actions. A question about the business
(shipping, warranty, anything in knowledge/*.md) always goes through RAG below, never a hardcoded
answer here.
"""
import os

import numpy as np

from gateway import retrieval
from rag import index_store

MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.5"))  # below this, the LLM is never called
NO_INFO_ANSWER = "No tengo esa información."

MIN_SIMILARITY_GREETING = float(os.getenv("MIN_SIMILARITY_GREETING", "0.75"))  # calibrated in the README, with real data
GREETING_ANSWER = "¡Hola! ¿En qué te puedo ayudar?"

_greeting_vectors: np.ndarray | None = None  # set by load_phrases(), once the indexer's phrases are read


def is_confident(results: list[tuple[float, dict]]) -> bool:
    """Is the best retrieved chunk similar enough to the question to trust an answer on it?"""
    return bool(results) and results[0][0] >= MIN_SIMILARITY


def load_phrases() -> None:
    """Reads index.db's `phrases` table (the greeting reference vectors, computed once by the
    indexer — see rag/build_index.py's GREETING_REFERENCES) into memory. Called once at startup
    (gateway/main.py lifespan) — reuses the same index.db connection retrieval.load_index()
    already opens, so this is a local read, not a network call."""
    global _greeting_vectors
    con, _ = retrieval.load_index()
    _greeting_vectors = index_store.read_phrases(con).get("greeting")


def is_greeting(q: np.ndarray) -> bool:
    """Does the question's vector look more like a greeting than like any document?"""
    return _greeting_vectors is not None and len(_greeting_vectors) > 0 and float(np.max(_greeting_vectors @ q)) >= MIN_SIMILARITY_GREETING
