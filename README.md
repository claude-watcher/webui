# Claude Code Watcher — Web UI

[![ci](https://github.com/claude-watcher/webui/actions/workflows/ci.yml/badge.svg)](https://github.com/claude-watcher/webui/actions/workflows/ci.yml)

A crude, **read-only** web view of the running Claude Code sessions on this
machine, served over HTTP with a single self-contained page. **Display only**: no
terminal focus, no actions, no signalling.

## Endpoints

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/` | open | the HTML page (polls `/api/sessions`) |
| GET | `/healthz` | open | `{"status":"ok"}` |
| GET | `/api/meta` | open | `{"auth_required": bool}` |
| GET | `/api/sessions` | gated | `{count, sessions[], auth_required, dev, instance}` |

`dev`/`instance` are livereload internals (`dev` true only under `APP_RELOAD`; the
page reloads itself when `instance` changes). Each entry in `sessions[]` carries
`project`, `state`, `context_pct`, `tool`, `topic`, `idle_seconds` and friends.

## Auth (optional)

Empty `APP_AUTH_TOKEN` → the API is open. Set it → `/api/sessions` requires the
token, accepted three ways:

- `X-API-Key: <token>`
- `Authorization: Bearer <token>`
- `?key=<token>` — used by the web page, stored in `localStorage`

The page probes `/api/meta` and only shows a key prompt when a token is required.

## Display options

The ⚙ button in the header reveals a filter bar (mirrors the TUI options). Each
choice is stored per-browser in `localStorage` and applied client-side; the API
is unchanged:

| Option | Values | Effect |
|---|---|---|
| sort | `default` / `idle` | `default` keeps the server order (waiting → working → idle, then project); `idle` floats the most-recently-idle sessions to the top of the idle group |
| idle | `none` / `loose` / `precise` | idle duration shown on idle rows: hidden, `[Nd ]HH:MM`, or `[Nd ]HH:MM:SS` |
| topic | on / off | show the AI title / last prompt under each session |
| cards | on / off | roomier spacing between rows |

The bar itself is hidden on every load (not persisted). Idle durations are
computed **server-side** (`idle_seconds` in each session) rather than from the
browser clock.

## Run

```bash
make install                      # uv sync
make run                          # → http://localhost:8000
APP_AUTH_TOKEN=hunter2 make run   # require a key
```

Config is via `APP_*` env vars / `.env` (see `.env.example`): `APP_HOST`,
`APP_PORT`, `APP_LOG_LEVEL`, `APP_JSON_LOGS`, `APP_AUTH_TOKEN`,
`APP_ALLOW_INSECURE_BIND`, `APP_RELOAD`.

### Bind safety

Binds **`127.0.0.1`** by default. Session data (cwd paths, AI topics, project
names) is **unauthenticated unless `APP_AUTH_TOKEN` is set**, so binding a
non-loopback `APP_HOST` (e.g. `0.0.0.0`) with no token is **refused at startup** —
set a token, or pass `APP_ALLOW_INSECURE_BIND=true` to opt in.

## Container

Detection reads the host `/proc` (so `--pid=host`) and resolves each session's
transcript from **absolute host paths** — `~/.claude`, plus any custom
`CLAUDE_CONFIG_DIR` profile (e.g. `~/.claude-work`) baked into the session's env.
To see every profile, expose the **host home at the same path**, run as the **host
uid** (the `~/.claude*` dirs are `0700`), and set `HOME` to the host home so the
default-profile lookup resolves there too:

```bash
make docker-build

# All profiles (default + every ~/.claude-*):
docker run --rm --pid=host -u $(id -u):$(id -g) -e HOME=$HOME \
  -v $HOME:$HOME:ro -p 8000:8000 \
  claude-watcher-webui:local        # == `make docker-run`

# Default ~/.claude profile only — narrower mount:
docker run --rm --pid=host -u $(id -u):$(id -g) -e HOME=$HOME \
  -v $HOME/.claude:$HOME/.claude:ro -p 8000:8000 \
  claude-watcher-webui:local
```

The image bakes `APP_HOST=0.0.0.0` (so `-p` works) and `APP_ALLOW_INSECURE_BIND=true`
(the netns is the boundary; `-p` is your exposure choice). **Auth is still off by
default** — once you publish the port off a trusted network, set `APP_AUTH_TOKEN`.

## Detection

`detect.py` is a self-contained copy of the watcher detection logic, trimmed to
read-only. It reads `/proc`, the session registry under `~/.claude/sessions/` and
the transcript `.jsonl` files to derive each session's state, context % and topic;
if the upstream heuristics change, align it by hand.

## Develop

```bash
make test     # uv run pytest
make lint     # pre-commit run --all-files
```
