ARG PYTHON_VERSION
ARG UV_VERSION

# uv se toma de su imagen oficial (versión fija)
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim
COPY --from=uv /uv /uvx /bin/

# git: el reporte del examen registra con qué commit se ejecutó (ver git_info() en run_eval.py)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Solo las dependencias del grupo "evaluator", con las versiones fijadas en uv.lock
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --only-group evaluator

# El repo montado pertenece a otro usuario; sin esto git se niega a leerlo
RUN git config --system --add safe.directory /work

WORKDIR /work
CMD ["bash"]
