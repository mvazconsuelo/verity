# References

Official documentation for each piece of the stack, for when you want to go beyond what this repo
explains.

## Application

- [FastAPI](https://fastapi.tiangolo.com/) — the gateway's framework
- [Pydantic](https://docs.pydantic.dev/) — validates `AskRequest`/`AskResponse`
- [Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md) — the `/api/chat` and `/api/embed` API
- [bge-m3 (Hugging Face)](https://huggingface.co/BAAI/bge-m3) — the embedding model
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) — how `bge-m3` compares against other embedding models
- [sqlite-vec](https://github.com/asg017/sqlite-vec) — the extension behind `index.db`

## Data

- [DVC — documentation](https://dvc.org/doc)
- [DVC — S3-compatible remotes](https://dvc.org/doc/user-guide/data-management/remote-storage/amazon-s3)
- [SeaweedFS — wiki](https://github.com/seaweedfs/seaweedfs/wiki)

## Platform

- [Docker Compose — reference](https://docs.docker.com/reference/compose-file/)
- [uv](https://docs.astral.sh/uv/) — the Python package/environment manager the project uses

## Testing

- [pytest](https://docs.pytest.org/)
- [Starlette TestClient](https://www.starlette.io/testclient/) — used in `tests/test_gateway_auth.py`

---

**[Español](es/references.md)**
