"""The gateway's API surface: /health, /config, /ask. Each one just calls auth/prompt/retrieval/
guardrails and assembles the response — the actual logic lives in those modules. Named
"endpoints", not "routes"/"router": in an LLM project that word means something else (see
guardrails.py, the actual semantic router — greeting vs. real question, confident vs. not).
"""
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from gateway import auth, guardrails, prompt, retrieval

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("MODEL", "qwen2.5:1.5b")
RELEASE = os.getenv("APP_VERSION", "dev")  # the deployed image's own version (its tag)
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))  # 0 = repeatable answers
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "60"))  # how long to wait for Ollama

router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=auth.MAX_QUESTION_CHARS)


class AskResponse(BaseModel):
    answer: str
    model: str
    tokens: int
    release: str
    prompt_hash: str
    temperature: float
    sources: list[str] = []  # retrieved chunks, as "document.md#Section"


@router.get("/health")
async def health():
    return {"status": "ok", "release": RELEASE}


@router.get("/config", dependencies=[Depends(auth.rate_limit)])
async def config():
    """The bot's effective configuration; the evaluation script includes it in its report."""
    _, template, hash_ = prompt.load_prompt()
    uses_rag = "{context}" in template
    cfg = {"release": RELEASE, "prompt_hash": hash_, "temperature": TEMPERATURE, "model": MODEL, "rag": uses_rag}
    if uses_rag:
        cfg |= {
            "embedding_model": retrieval.EMBEDDING_MODEL,
            "top_k": retrieval.TOP_K,
            "min_similarity": guardrails.MIN_SIMILARITY,
            "min_similarity_saludo": guardrails.MIN_SIMILARITY_GREETING,
            "index": retrieval.load_index()[1],
        }
    return cfg


@router.post("/ask", response_model=AskResponse, dependencies=[Depends(auth.rate_limit)])
async def ask(req: AskRequest):
    system, template, hash_ = prompt.load_prompt()
    response = dict(model=MODEL, release=RELEASE, prompt_hash=hash_, temperature=TEMPERATURE)

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
            context, sources = "", []
            if "{context}" in template:
                q, results = await retrieval.retrieve(client, req.question)
                sources = [f"{c['source']}#{c['section']}" for _, c in results]
                if guardrails.is_greeting(q):
                    # "Semantic routing": looks more like a greeting than like any document. Answer
                    # directly, without spending a call on the LLM or showing sources (they don't
                    # come from any real document).
                    return AskResponse(answer=guardrails.GREETING_ANSWER, tokens=0, sources=[], **response)
                if not guardrails.is_confident(results):
                    # Nothing similar enough to the question: answer without spending a call on the LLM,
                    # and without sources (same reasoning as the greeting above — these chunks were
                    # never confident enough to actually back an answer, so citing them would be misleading)
                    return AskResponse(answer=guardrails.NO_INFO_ANSWER, tokens=0, sources=[], **response)
                context = "\n\n".join(c["text"] for _, c in results)

            docs = prompt.read_docs() if "{docs}" in template else ""
            content = (
                template.replace("{docs}", docs).replace("{context}", context).replace("{question}", req.question)
            )
            messages = ([{"role": "system", "content": system}] if system else []) + [
                {"role": "user", "content": content}
            ]
            r = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": TEMPERATURE},
                },
            )
            r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"LLM not available: {e}")

    data = r.json()
    return AskResponse(
        answer=data["message"]["content"], tokens=data["eval_count"], sources=sources, **response
    )
