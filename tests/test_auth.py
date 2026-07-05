from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import Request

from auth import make_auth_dependency


@pytest.fixture
async def secured_client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    """A client whose app instance enforces a fixed token."""
    import importlib

    import main as main_mod

    monkeypatch.setenv("APP_AUTH_TOKEN", "s3cret")
    main = importlib.reload(main_mod)
    monkeypatch.setattr(main.detect, "scan_sessions", lambda *a, **k: [])

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    importlib.reload(main_mod)  # restore unguarded app for other tests


async def test_rejects_without_token(secured_client: httpx.AsyncClient) -> None:
    r = await secured_client.get("/api/sessions")
    assert r.status_code == 401


async def test_accepts_api_key_header(secured_client: httpx.AsyncClient) -> None:
    r = await secured_client.get("/api/sessions", headers={"X-API-Key": "s3cret"})
    assert r.status_code == 200


async def test_accepts_bearer(secured_client: httpx.AsyncClient) -> None:
    r = await secured_client.get("/api/sessions", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200


async def test_accepts_query_key(secured_client: httpx.AsyncClient) -> None:
    r = await secured_client.get("/api/sessions?key=s3cret")
    assert r.status_code == 200


async def test_meta_unauthenticated(secured_client: httpx.AsyncClient) -> None:
    # /api/meta is always open so the UI can decide whether to prompt.
    r = await secured_client.get("/api/meta")
    assert r.status_code == 200
    assert r.json() == {"auth_required": True}


async def test_wrong_token_rejected(secured_client: httpx.AsyncClient) -> None:
    r = await secured_client.get("/api/sessions", headers={"X-API-Key": "nope"})
    assert r.status_code == 401


async def test_open_dependency_is_noop() -> None:
    dep = make_auth_dependency(None)
    # No token, but an open gate must not raise.
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""}
    await dep(Request(scope))  # must not raise


def _req_with_query_key(token: str) -> Request:
    # Query params decode as UTF-8 (unlike HTTP headers, which are latin-1), so a
    # non-ASCII token survives this channel intact.
    from urllib.parse import quote

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/sessions",
            "headers": [],
            "query_string": ("key=" + quote(token)).encode(),
        }
    )


async def test_non_ascii_token_matches() -> None:
    # secrets.compare_digest on str raises TypeError for non-ASCII; we compare
    # bytes, so an accented token authenticates instead of 500-ing.
    dep = make_auth_dependency("clé-sücrée")
    await dep(_req_with_query_key("clé-sücrée"))  # must not raise


async def test_non_ascii_token_mismatch_is_401() -> None:
    from fastapi import HTTPException

    dep = make_auth_dependency("clé-sücrée")
    with pytest.raises(HTTPException) as exc:
        await dep(_req_with_query_key("wrong"))
    assert exc.value.status_code == 401
