ARG PYTHON_VERSION
ARG UV_VERSION

# uv comes from its official image (pinned version)
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim
COPY --from=uv /uv /uvx /bin/

# git: the exam's report records which commit it ran against (see git_info() in run_eval.py)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Only the "evaluator" group's dependencies, pinned in uv.lock
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --only-group evaluator

# The mounted repo belongs to a different user; without this git refuses to read it
RUN git config --system --add safe.directory /work

WORKDIR /work
CMD ["bash"]
