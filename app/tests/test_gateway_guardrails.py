"""gateway/guardrails.py's is_greeting(): deterministic, fake vectors — no Ollama, no index.db, no
network. Simple 2D unit vectors so the cosine similarity math is easy to verify by hand.
"""
import numpy as np
import pytest

from gateway import guardrails
from gateway.guardrails import is_greeting


@pytest.fixture(autouse=True)
def clean_greeting_vectors(monkeypatch):
    """Every test starts with nothing loaded — never the real module state."""
    monkeypatch.setattr(guardrails, "_greeting_vectors", None)
    yield


def test_greeting_above_threshold_is_true(monkeypatch):
    monkeypatch.setattr(guardrails, "_greeting_vectors", np.array([[1.0, 0.0]]))
    monkeypatch.setattr(guardrails, "MIN_SIMILARITY_GREETING", 0.5)
    assert is_greeting(np.array([1.0, 0.0])) is True


def test_below_threshold_is_false(monkeypatch):
    monkeypatch.setattr(guardrails, "_greeting_vectors", np.array([[1.0, 0.0]]))
    monkeypatch.setattr(guardrails, "MIN_SIMILARITY_GREETING", 0.9)
    # similarity here is 0.6 (the question's x-coordinate) — below the 0.9 threshold
    assert is_greeting(np.array([0.6, 0.8])) is False


def test_nothing_loaded_is_false():
    assert is_greeting(np.array([1.0, 0.0])) is False
