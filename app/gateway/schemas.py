"""Request/response models for the gateway's API surface. Kept separate from endpoints.py per
FastAPI's own "Bigger Applications" guide — schemas and routers are different concerns, even when
(like here) there are only two of them.
"""
from pydantic import BaseModel, Field

from gateway import auth


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
