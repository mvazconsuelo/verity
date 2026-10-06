"""Assembles the app: middleware, lifespan, and the endpoints from endpoints.py. This file only
wires things together — the logic for each concern lives in its own module:

    auth.py         who gets in (origin, API key, rate limit)
    prompt.py       what gets told to the model (system.md, template.md, full documents)
    retrieval.py    RAG mechanics: embed the question, search the index, return chunks
    guardrails.py   policy: is there enough confidence to answer? is it a greeting?
    endpoints.py    the gateway's API surface, using all of the above
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gateway import auth, endpoints, guardrails, prompt

EXPOSE_DOCS = os.getenv("EXPOSE_DOCS", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    _, template, _ = prompt.load_prompt()
    if "{context}" in template:  # without RAG there's no question vector to compare a greeting against
        guardrails.load_phrases()  # reads index.db, no network call: safe to run synchronously here
    yield


app = FastAPI(
    title="Verity",
    lifespan=lifespan,
    # Interactive docs aren't published unless explicitly requested
    docs_url="/docs" if EXPOSE_DOCS else None,
    redoc_url=None,
    openapi_url="/openapi.json" if EXPOSE_DOCS else None,
)

app.middleware("http")(auth.verify_origin)

# Added AFTER the middleware above so it stays outside and handles the preflight requests (OPTIONS)
if auth.CORS_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=auth.CORS_ALLOWED_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type", "x-api-key"],
        max_age=600,
    )

app.include_router(endpoints.router)
