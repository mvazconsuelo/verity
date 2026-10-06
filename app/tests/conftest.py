"""Shared test configuration.

The gateway reads its configuration at import time, so the variables are set here, before any
test imports gateway.main. The prompts are test-only (no RAG): Ollama isn't needed.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

_prompts_dir = Path(tempfile.mkdtemp(prefix="verity-prompts-"))
(_prompts_dir / "template.md").write_text("{question}", encoding="utf-8")

os.environ.update(
    API_KEYS="key-one,key-two,key-three",
    ORIGIN_VERIFY_SECRET="origin-secret",
    CORS_ALLOWED_ORIGINS="https://front.example",
    RATE_LIMIT_PER_MINUTE="3",
    MAX_QUESTION_CHARS="50",
    PROMPTS_DIR=str(_prompts_dir),
    DOCS_DIR=str(ROOT.parent / "knowledge"),
    APP_VERSION="test",
)
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def clean_rate_limits():
    """Every test starts with no requests counted."""
    from gateway import auth

    auth._windows.clear()
    yield
