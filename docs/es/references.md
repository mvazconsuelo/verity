# Referencias

Documentación oficial de cada pieza del stack, para cuando quieras ir más allá de lo que explica
este repo.

## Aplicación

- [FastAPI](https://fastapi.tiangolo.com/) — el framework del gateway
- [Pydantic](https://docs.pydantic.dev/) — validación de `AskRequest`/`AskResponse`
- [Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md) — API de `/api/chat` y `/api/embed`
- [bge-m3 (Hugging Face)](https://huggingface.co/BAAI/bge-m3) — el modelo de embeddings
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) — cómo se compara `bge-m3` contra otros modelos de embeddings
- [sqlite-vec](https://github.com/asg017/sqlite-vec) — la extensión que usa `index.db`

## Datos

- [DVC — documentación](https://dvc.org/doc)
- [DVC — remotos S3-compatibles](https://dvc.org/doc/user-guide/data-management/remote-storage/amazon-s3)
- [SeaweedFS — wiki](https://github.com/seaweedfs/seaweedfs/wiki)

## Plataforma y CI

- [Docker Compose — referencia](https://docs.docker.com/reference/compose-file/)
- [GitHub Actions — documentación](https://docs.github.com/actions)
- [uv](https://docs.astral.sh/uv/) — el gestor de paquetes/entornos de Python que usa el proyecto

## Las herramientas que validan el propio CI

- [shellcheck](https://www.shellcheck.net/) — lint de scripts bash
- [hadolint](https://github.com/hadolint/hadolint) — lint de Dockerfiles
- [actionlint](https://github.com/rhysd/actionlint) — lint de workflows de GitHub Actions
- [gitleaks](https://github.com/gitleaks/gitleaks) — detección de secretos en el historial de git

## Testing

- [pytest](https://docs.pytest.org/)
- [Starlette TestClient](https://www.starlette.io/testclient/) — usado en `tests/test_gateway_auth.py`

---

**[English](../references.md)**
