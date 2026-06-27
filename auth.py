"""Optional shared-secret gate.

When `APP_AUTH_TOKEN` is unset/empty the API is fully open. When set, every
guarded request must present the token in one of three ways (crude on purpose,
display-only data):

  - ``X-API-Key: <token>``           (API clients)
  - ``Authorization: Bearer <token>`` (API clients)
  - ``?key=<token>``                  (the browser UI, stored in localStorage)

Comparison is constant-time to avoid leaking the token length/prefix via timing.
"""

import secrets
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status


def _present_token(request: Request) -> str | None:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.query_params.get("key")


def make_auth_dependency(expected: str | None) -> Callable[[Request], Awaitable[None]]:
    """Build a FastAPI dependency enforcing `expected` (no-op when falsy)."""

    # Compare on UTF-8 bytes: secrets.compare_digest on str raises TypeError for
    # any non-ASCII char, which would turn a valid (accented) token into a 500 and
    # silently break auth. Bytes compare is constant-time and accent-safe.
    expected_b = expected.encode() if expected else None

    async def dependency(request: Request) -> None:
        if not expected_b:
            return
        token = _present_token(request)
        if token is None or not secrets.compare_digest(token.encode(), expected_b):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return dependency
