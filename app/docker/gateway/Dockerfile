ARG PYTHON_VERSION
ARG UV_VERSION

# uv comes from its official image (pinned version)
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim
COPY --from=uv /uv /uvx /bin/

WORKDIR /srv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/srv/.venv/bin:$PATH"

# Dependency layer: only rebuilds if pyproject.toml or uv.lock change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Code and content layer. Everything goes INSIDE the image: the same tag fixes code, prompt and
# documents at once. knowledge/ is versioned with DVC (see app/dvc-setup.sh): "dvc pull" leaves it
# ready on disk BEFORE this build — this Dockerfile just copies it, as-is.
COPY gateway ./gateway
COPY rag ./rag
COPY prompts ./prompts
COPY knowledge ./knowledge

EXPOSE 8000
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
