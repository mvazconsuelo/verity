"""Saves and searches the vector index in a single SQLite file (sqlite-vec extension).

Used by rag/build_index.py (creates the file, once, when indexing) and gateway/retrieval.py (opens
it and searches, on every question). It used to be three files (vectors.npy, chunks.json,
meta.json) and the search was a matrix multiplication with NumPy; now it's one file and a SQL
query. NumPy is still used to normalize the vectors (rag/build_index.py and gateway/retrieval.py),
not to save or search them.

sqlite-vec returns a cosine "distance" (0 = identical, 2 = opposite), not a similarity.
distance_metric=cosine is saved on purpose and converted with `1 - distance`, so the result is the
SAME cosine similarity as before (-1 to 1, higher = more similar) and MIN_SIMILARITY doesn't change
scale: it still means the same thing it did when it was calibrated (see README > Configuration).
"""
import json
import sqlite3
import struct
from pathlib import Path

import numpy as np
import sqlite_vec

FILE = "index.db"


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path, check_same_thread=False)
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con


def create(folder: Path, dimension: int, meta: dict) -> sqlite3.Connection:
    """Creates the file from scratch, with the vectors table and the metadata one. Called by build_index.py."""
    path = folder / FILE
    path.unlink(missing_ok=True)  # always rebuild from scratch, never mix with an old index
    con = _connect(path)
    con.execute(
        f"CREATE VIRTUAL TABLE chunks USING vec0("
        f"embedding float[{dimension}] distance_metric=cosine, +source TEXT, +section TEXT, +text TEXT)"
    )
    con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    con.executemany("INSERT INTO meta VALUES (?, ?)", [(k, json.dumps(v)) for k, v in meta.items()])
    con.commit()
    return con


def save(con: sqlite3.Connection, vectors: np.ndarray, chunks: list[dict]) -> None:
    """One chunk per row. Called by build_index.py, after create()."""
    dim = vectors.shape[1]
    con.executemany(
        "INSERT INTO chunks(embedding, source, section, text) VALUES (?, ?, ?, ?)",
        [
            (struct.pack(f"{dim}f", *vector), chunk["source"], chunk["section"], chunk["text"])
            for vector, chunk in zip(vectors, chunks)
        ],
    )
    con.commit()


def create_phrases(con: sqlite3.Connection, dimension: int) -> None:
    """Second table in the SAME index.db, next to `chunks`: reference phrases for semantic routing
    (gateway/guardrails.py) — kept in its own table so a reference phrase never surfaces as a
    document `source` in an answer. Generic by `category` on purpose: today the only category is
    "greeting" (see rag/build_index.py GREETING_REFERENCES), but adding a new one later (e.g.
    "complaint") is just new rows, no schema change. Called by build_index.py, on the same
    connection create() returns."""
    con.execute("CREATE VIRTUAL TABLE phrases USING vec0(" f"embedding float[{dimension}] distance_metric=cosine, +category TEXT, +phrase TEXT)")
    con.commit()


def save_phrases(con: sqlite3.Connection, vectors: np.ndarray, categories: list[str], phrases: list[str]) -> None:
    """One reference phrase per row. Called by build_index.py, after create_phrases()."""
    dim = vectors.shape[1]
    con.executemany(
        "INSERT INTO phrases(embedding, category, phrase) VALUES (?, ?, ?)",
        [(struct.pack(f"{dim}f", *vector), category, phrase) for vector, category, phrase in zip(vectors, categories, phrases)],
    )
    con.commit()


def read_phrases(con: sqlite3.Connection) -> dict[str, np.ndarray]:
    """All reference vectors, grouped by category — {"greeting": array of shape (n, dim), ...}.
    Called by gateway/guardrails.py, once (there are only a handful of rows per category, so no
    need for a MATCH search like chunks: load them all into memory and compare with a dot product)."""
    by_category: dict[str, list] = {}
    for blob, category in con.execute("SELECT embedding, category FROM phrases"):
        by_category.setdefault(category, []).append(struct.unpack(f"{len(blob) // 4}f", blob))
    return {category: np.array(vectors, dtype=np.float32) for category, vectors in by_category.items()}


def open_index(folder: Path) -> sqlite3.Connection:
    """Opens an already-built index. Called by gateway/retrieval.py, once (with @lru_cache)."""
    return _connect(folder / FILE)


def read_meta(con: sqlite3.Connection) -> dict:
    return {key: json.loads(value) for key, value in con.execute("SELECT key, value FROM meta")}


def search(con: sqlite3.Connection, question_vector: np.ndarray, top_k: int) -> list[tuple[float, dict]]:
    """The top_k chunks most similar to question_vector, as (cosine similarity, {source, section, text})."""
    dim = question_vector.shape[0]
    rows = con.execute(
        "SELECT source, section, text, distance FROM chunks WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
        (struct.pack(f"{dim}f", *question_vector), top_k),
    ).fetchall()
    return [(1 - distance, {"source": s, "section": sec, "text": t}) for s, sec, t, distance in rows]
