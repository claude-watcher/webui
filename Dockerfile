FROM python:3.14-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev && \
    .venv/bin/opentelemetry-bootstrap -a requirements | uv pip install --requirement -

FROM python:3.14-slim-trixie

ARG BUILD_TIMESTAMP="1970-01-01T00:00:00+00:00"
ARG COMMIT_HASH="00000000-dirty"
ARG PROJECT_URL="claude-watcher-webui"
ARG VERSION="v0.0.0"

ENV BUILD_TIMESTAMP=${BUILD_TIMESTAMP}
ENV COMMIT_HASH=${COMMIT_HASH}
ENV PROJECT_URL=${PROJECT_URL}
ENV VERSION=${VERSION}

LABEL org.opencontainers.image.source=${PROJECT_URL}
LABEL org.opencontainers.image.created=${BUILD_TIMESTAMP}
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.revision=${COMMIT_HASH}

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY *.py run.sh ./
COPY static ./static

RUN useradd -ms /bin/bash -d /app app && chown -R app:app /app
USER app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
# Containers must listen on all interfaces for `-p` to reach the app; the loopback
# default would be unreachable.
ENV APP_HOST=0.0.0.0
# The container network namespace is the isolation boundary, and the real exposure
# is the operator's `-p` — which the host-run safety gate can't see. So allow the
# non-loopback bind here; rely on `-p` (and APP_AUTH_TOKEN when the published port
# isn't on a trusted network) instead. The gate stays strict for bare-host runs.
ENV APP_ALLOW_INSECURE_BIND=true
# NOTE: detection reads the HOST /proc, ~/.claude AND any custom CLAUDE_CONFIG_DIR
# profiles — the latter are absolute host paths in each session's env, so the host
# home must be visible at the SAME path. Run with the host uid + home (see README):
#   docker run --rm --pid=host -u $(id -u):$(id -g) -e HOME=$HOME \
#     -v $HOME:$HOME:ro -p 8000:8000 claude-watcher-webui:local
ENTRYPOINT ["./run.sh"]
