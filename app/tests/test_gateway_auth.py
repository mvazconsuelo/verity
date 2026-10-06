"""Gateway security barriers: origin, API key, CORS, rate limit and question size."""
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from gateway.main import app

ORIGIN = {"x-origin-verify": "origin-secret"}


def with_key(key: str = "key-one") -> dict:
    return {**ORIGIN, "x-api-key": key}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# ── Origin ────────────────────────────────────────────────────────────────────
def test_missing_origin_header_is_403(client):
    assert client.get("/health").status_code == 403


def test_wrong_origin_header_is_403(client):
    assert client.get("/health", headers={"x-origin-verify": "other"}).status_code == 403


def test_health_with_correct_origin_does_not_need_a_key(client):
    r = client.get("/health", headers=ORIGIN)
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "release": "test"}


# ── API key ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("route,method", [("/config", "get"), ("/ask", "post")])
def test_missing_key_is_401(client, route, method):
    r = getattr(client, method)(route, headers=ORIGIN, **({"json": {"question": "hola"}} if method == "post" else {}))
    assert r.status_code == 401


def test_invalid_key_is_401(client):
    assert client.get("/config", headers=with_key("bad")).status_code == 401


def test_valid_key_passes(client):
    assert client.get("/config", headers=with_key()).status_code == 200


def test_config_returns_release_and_prompt_hash(client):
    cfg = client.get("/config", headers=with_key()).json()
    assert cfg["release"] == "test"
    assert len(cfg["prompt_hash"]) == 8
    assert cfg["rag"] is False


# ── Question validation ────────────────────────────────────────────────────────
def test_empty_question_is_422(client):
    assert client.post("/ask", json={"question": ""}, headers=with_key()).status_code == 422


def test_question_too_long_is_422(client):
    assert client.post("/ask", json={"question": "x" * 51}, headers=with_key()).status_code == 422


# ── API docs stay closed ────────────────────────────────────────────────────────
@pytest.mark.parametrize("route", ["/docs", "/openapi.json"])
def test_docs_are_not_published(client, route):
    assert client.get(route, headers=ORIGIN).status_code == 404


# ── CORS ──────────────────────────────────────────────────────────────────────
def test_cors_allowed_origin(client):
    r = client.options(
        "/ask",
        headers={
            "origin": "https://front.example",
            "access-control-request-method": "POST",
            "access-control-request-headers": "x-api-key,content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "https://front.example"


def test_cors_disallowed_origin_gets_no_header(client):
    r = client.options(
        "/ask", headers={"origin": "https://intruder.example", "access-control-request-method": "POST"}
    )
    assert "access-control-allow-origin" not in r.headers


# ── Rate limit ────────────────────────────────────────────────────────────────
def test_rate_limit_per_minute_and_retry_after(client):
    codes = [client.get("/config", headers=with_key("key-two")).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    r = client.get("/config", headers=with_key("key-two"))
    assert r.headers["retry-after"] == "60"


def test_each_key_has_its_own_quota(client):
    for _ in range(4):
        client.get("/config", headers=with_key("key-two"))
    assert client.get("/config", headers=with_key("key-three")).status_code == 200


def test_invalid_requests_also_count(client):
    for _ in range(3):
        client.post("/ask", json={"question": ""}, headers=with_key("key-one"))
    assert client.get("/config", headers=with_key("key-one")).status_code == 429


# ── Closed by default at startup ─────────────────────────────────────────────
def test_gateway_does_not_start_without_api_keys():
    env = {k: v for k, v in os.environ.items() if k != "API_KEYS"}
    r = subprocess.run(
        [sys.executable, "-c", "import gateway.main"],
        env={**env, "PYTHONPATH": os.environ.get("PYTHONPATH", "") or "."},
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "API_KEYS" in r.stderr
