from typing import Any, Dict, Optional, Iterable, List

import requests
from requests import Response

from api_ratelimiter.clients import DynamicAPIClient


class DummyLimiter:
    """Simple limiter used to verify DynamicAPIClient behaviour in tests."""

    def __init__(self) -> None:
        self.acquire_calls = 0
        self.success_calls = 0
        self.backoff_calls = 0
        self.last_retry_after: Optional[float] = None

    def acquire(self) -> None:
        self.acquire_calls += 1

    def on_success(self) -> None:
        self.success_calls += 1

    def on_429(self, retry_after: Optional[float] = None) -> None:
        self.backoff_calls += 1
        self.last_retry_after = retry_after


class DummySession(requests.Session):
    def __init__(self, responses: Iterable[Response]) -> None:
        super().__init__()
        self._responses: List[Response] = list(responses)
        self.requests: list[tuple[str, str, Dict[str, Any]]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> Response:  # type: ignore[override]
        self.requests.append((method, url, kwargs))
        if not self._responses:
            raise RuntimeError("DummySession ran out of prepared responses")
        return self._responses.pop(0)


def make_response(status: int, headers: Optional[Dict[str, str]] = None) -> Response:
    r = Response()
    r.status_code = status
    r._content = b"{}"
    if headers:
        r.headers.update(headers)
    return r


def test_client_success_path_calls_on_success() -> None:
    limiter = DummyLimiter()
    resp = make_response(200)
    session = DummySession([resp])

    client = DynamicAPIClient(
        base_url="https://example.com",
        limiter=limiter,
        session=session,
    )

    out = client.request("GET", "/foo")

    assert out is resp
    assert limiter.acquire_calls == 1
    assert limiter.success_calls == 1
    assert limiter.backoff_calls == 0


def test_client_429_triggers_backoff_and_retries() -> None:
    limiter = DummyLimiter()
    first = make_response(429, headers={"Retry-After": "3"})
    second = make_response(200)
    session = DummySession([first, second])

    client = DynamicAPIClient(
        base_url="https://example.com",
        limiter=limiter,
        session=session,
        max_retries_on_429=5,
    )

    out = client.request("GET", "/foo")

    assert out.status_code == 200
    # One backoff, one success, two acquires for two requests
    assert limiter.backoff_calls == 1
    assert limiter.last_retry_after == 3.0
    assert limiter.success_calls == 1
    assert limiter.acquire_calls >= 2


def test_client_503_triggers_backoff_when_configured() -> None:
    limiter = DummyLimiter()
    first = make_response(503)
    second = make_response(200)
    session = DummySession([first, second])

    client = DynamicAPIClient(
        base_url="https://example.com",
        limiter=limiter,
        session=session,
        max_retries_on_429=5,
        backoff_status_codes=(429, 502, 503),
    )

    out = client.request("GET", "/foo")

    assert out.status_code == 200
    assert limiter.backoff_calls == 1
    assert limiter.success_calls == 1
    assert limiter.acquire_calls >= 2
