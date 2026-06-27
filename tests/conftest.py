from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

import detect


@pytest.fixture(autouse=True)
def _reset_scan_cache() -> Iterator[None]:
    # scan_sessions() caches results for ~1s; clear it between tests so a fast
    # suite doesn't serve one test's snapshot to the next.
    detect._scan_cache = None
    yield
    detect._scan_cache = None


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    import main

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
