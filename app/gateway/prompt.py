"""Loads the prompt (system.md + template.md) and, if the template asks for {docs}, every
document in full (instead of just the chunks RAG brings back with {context})."""
import hashlib
import os
from pathlib import Path

from fastapi import HTTPException

PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", "/srv/prompts"))
DOCS_DIR = Path(os.getenv("DOCS_DIR", "/srv/knowledge"))


def read_docs() -> str:
    return "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(DOCS_DIR.glob("*.md")))


def load_prompt() -> tuple[str | None, str, str]:
    """Reads prompts/system.md and prompts/template.md and returns (system, template, text hash).

    There is a single prompt: its history lives in git, and every evaluation records its hash."""
    try:
        template = (PROMPTS_DIR / "template.md").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Missing template.md in {PROMPTS_DIR}")
    system_file = PROMPTS_DIR / "system.md"
    system = system_file.read_text(encoding="utf-8").strip() if system_file.exists() else None
    # The hash changes if the text changes, even if the version keeps the same name
    hash_ = hashlib.sha256(f"{system or ''}\n---\n{template}".encode()).hexdigest()[:8]
    return system, template, hash_
