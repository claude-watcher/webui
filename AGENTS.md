# AGENTS.md — claude-watcher-webui

## What this is

A crude, **read-only** web view of the Claude Code sessions running on this
machine. FastAPI serves a JSON endpoint and one self-contained HTML page that
polls it. **Display only** — no terminal focus, no actions, no signalling.

## Layout

| File | Role |
|---|---|
| `detect.py` | Session detection backend, trimmed to read-only (no X11/window/kitty/focus/kill). Reads `/proc`, `~/.claude/sessions/<pid>.json` (registry) and the transcript `.jsonl`. |
| `auth.py` | Optional shared-secret gate (`X-API-Key` / `Bearer` / `?key=`). Open when `APP_AUTH_TOKEN` is empty. |
| `main.py` | FastAPI app: `/healthz`, `/api/sessions` (guarded), `/api/meta` (open), `/` (the page). |
| `static/index.html` | Single polling page, no build step, no external deps. |

`detect.py` is a self-contained copy of the watcher detection logic — align it by
hand if the upstream heuristics change.

## Endpoints

- `GET /healthz` → `{"status": "ok"}`
- `GET /api/meta` → `{"auth_required": bool}` (always open; UI uses it to decide whether to prompt)
- `GET /api/sessions` → `{count, sessions[], auth_required, dev, instance}` (guarded when a token is set; `dev`/`instance` are livereload internals)

## Run

```bash
make install        # uv sync
make run            # uv run python main.py  → http://localhost:8000
APP_AUTH_TOKEN=hunter2 make run   # require a key
make test
make lint
```

Container: detection reads the **host** `/proc` and `~/.claude`, so run with
`--pid=host -v $HOME/.claude:/app/.claude:ro` (see `make docker-run`).

Binds **`127.0.0.1` by default**. Session data (cwd paths, topics, project names)
is unauthenticated unless `APP_AUTH_TOKEN` is set, so binding a non-loopback
`APP_HOST` with no token is **refused at startup** — set a token, or pass
`APP_ALLOW_INSECURE_BIND=true` to opt in (the container does, behind `-p`).

## Conventions

uv for deps; ruff (line length 110) + mypy strict, both enforced by pre-commit
(`make lint`). Modern type hints only (`list[str]`, `str | None`). Health endpoint
at `/healthz`. Structured logging via `fastapi-structured-logging`. Dockerfile is
multi-stage (build with uv, run the `.venv` binary).
