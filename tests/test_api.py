import time

import httpx
import pytest

import detect
from main import insecure_bind_reason


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_bind_loopback_always_ok(host: str) -> None:
    # Loopback is safe even with no auth and no override.
    assert insecure_bind_reason(host, "", False) is None


def test_bind_nonloopback_no_auth_refused() -> None:
    assert insecure_bind_reason("0.0.0.0", "", False) is not None


def test_bind_nonloopback_with_auth_ok() -> None:
    assert insecure_bind_reason("0.0.0.0", "secret", False) is None


def test_bind_nonloopback_with_override_ok() -> None:
    assert insecure_bind_reason("0.0.0.0", "", True) is None


async def test_health(client: httpx.AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_meta_open(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/meta")
    assert r.status_code == 200
    assert r.json() == {"auth_required": False}


async def test_sessions_open(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(detect, "scan_sessions", lambda: [{"pid": 1, "state": "idle"}])
    r = await client.get("/api/sessions")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["sessions"][0]["pid"] == 1


def test_scan_sessions_no_procs(monkeypatch: pytest.MonkeyPatch) -> None:
    # No claude processes → empty list, never raises.
    monkeypatch.setattr(detect, "get_claude_processes", list)
    assert detect.scan_sessions() == []


def _one_proc(
    monkeypatch: pytest.MonkeyPatch,
    state_tuple: tuple[str, int | None, str | None, str | None, float | None],
) -> None:
    monkeypatch.setattr(
        detect,
        "get_claude_processes",
        lambda: [{"pid": 1, "elapsed": 10, "start_unix": 0.0, "starttime": 0}],
    )
    monkeypatch.setattr(detect, "get_cwd", lambda pid: "/tmp/proj")
    monkeypatch.setattr(detect, "get_env", lambda pid: {})
    monkeypatch.setattr(detect, "get_session_state", lambda *a, **k: state_tuple)


def test_idle_seconds_computed_server_side(monkeypatch: pytest.MonkeyPatch) -> None:
    # idle_seconds is derived from last_activity on the server (clock-skew proof),
    # clamped to >=0, and present (>= the elapsed since last_activity).
    _one_proc(monkeypatch, ("idle", 5, None, "topic", time.time() - 120))
    rows = detect.scan_sessions()
    assert len(rows) == 1
    assert rows[0]["idle_seconds"] is not None
    assert rows[0]["idle_seconds"] >= 119


def test_idle_seconds_none_without_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    _one_proc(monkeypatch, ("working", 5, "Bash", None, None))
    rows = detect.scan_sessions()
    assert rows[0]["idle_seconds"] is None


def test_idle_seconds_clamped_non_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    # last_activity slightly in the future (skewed statusUpdatedAt) → 0, never < 0.
    _one_proc(monkeypatch, ("idle", 5, None, None, time.time() + 30))
    rows = detect.scan_sessions()
    assert rows[0]["idle_seconds"] == 0


async def test_index_serves_filter_controls(client: httpx.AsyncClient) -> None:
    # Guards the filter-bar regressions: controls must be present and the
    # `.controls[hidden]` rule (which lets the ⚙ actually hide them) must exist.
    r = await client.get("/")
    assert r.status_code == 200
    html = r.text
    for needle in (
        'id="opt-sort"',
        'id="opt-idle"',
        'id="opt-topic"',
        'id="opt-cards"',
        'id="settings-btn"',
        ".controls[hidden]",
    ):
        assert needle in html, needle
