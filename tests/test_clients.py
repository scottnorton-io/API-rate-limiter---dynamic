from typing import Any, Dict, Optional, Iterable

import requests

from api_ratelimiter.clients import DynamicAPIClient
from api_ratelimiter.dynamic_ratelimiter import DynamicRateLimiter


class DummyLimiter(DynamicRateLimiter):
    """Test limiter that does not sleep."""

    def acquire(self) -> None:  # type: ignore[override]
        # No-op for tests; we don't throttle in unit tests.
        return


class DummyResponse:
    def __init__(self, status_code: int, headers: Optional[Dict[str, str]] = None, payload: Any = None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload or {}

    def json(self) -> Any:
        return self._payload


class DummySession:
    def __init__(self, responses: Iterable[DummyResponse]):
        self._responses = list(responses)
        self.requests_made = 0

    def request(self, method: str, url: str, **kwargs: Any) -> DummyResponse:  # type: ignore[override]
        self.requests_made += 1
        try:
            return self._responses.pop(0)
        except IndexError:
            raise AssertionError("No more dummy responses configured")


def test_dynamic_api_client_success_path():
    limiter = DummyLimiter(initial_rate=5.0)
    responses = [DummyResponse(200, payload={"ok": True})]
    session = DummySession(responses)

    client = DynamicAPIClient(
        base_url="https://api.example.com",
        limiter=limiter,
        max_retries_on_backoff=3,
        backoff_status_codes=(429,),
        session=session,  # type: ignore[arg-type]
    )

    resp = client.request("GET", "/test")
    assert isinstance(resp, requests.Response) or hasattr(resp, "status_code")
    assert resp.status_code == 200
    assert session.requests_made == 1


def test_dynamic_api_client_retries_on_429_then_succeeds():
    limiter = DummyLimiter(initial_rate=5.0)
    responses = [
        DummyResponse(429, headers={"Retry-After": "0"}),
        DummyResponse(200, payload={"ok": True}),
    ]
    session = DummySession(responses)

    client = DynamicAPIClient(
        base_url="https://api.example.com",
        limiter=limiter,
        max_retries_on_backoff=3,
        backoff_status_codes=(429,),
        session=session,  # type: ignore[arg-type]
    )

    resp = client.request("GET", "/test")
    assert isinstance(resp, requests.Response) or hasattr(resp, "status_code")
    assert resp.status_code == 200
    assert session.requests_made == 2
