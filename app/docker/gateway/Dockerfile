ARG PYTHON_VERSION
ARG UV_VERSION

# uv se toma de su imagen oficial (versión fija)
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim
COPY --from=uv /uv /uvx /bin/

WORKDIR /srv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/srv/.venv/bin:$PATH"

# Capa de dependencias: solo se reconstruye si cambian pyproject.toml o uv.lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Capa de código y contenido. Todo va DENTRO de la imagen: el mismo tag fija código, prompt y
# documentos a la vez. knowledge/ se versiona con DVC (ver app/dvc-setup.sh): "dvc pull" la deja
# lista en el disco ANTES de este build — este Dockerfile solo la copia, tal cual esté.
COPY gateway ./gateway
COPY rag ./rag
COPY prompts ./prompts
COPY knowledge ./knowledge

EXPOSE 8000
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
