import time
from typing import List, Dict, Any

import pytest

from api_ratelimiter.api_rate_config import get_api_rate_config
from api_ratelimiter.enterprise import (
    EnterpriseClient,
    CircuitBreakerConfig,
    CircuitOpenError,
)


class DummyResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any] | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class DummySession:
    """A tiny stand-in for requests.Session used in tests.

    It always returns the configured response and records the calls so we can
    assert on them later.
    """

    def __init__(self, response: DummyResponse):
        self._response = response
        self.calls: List[Dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs):
        self.calls.append({"method": method, "url": url, "kwargs": kwargs})
        # Simulate a tiny delay so elapsed_ms is non-zero.
        time.sleep(0.001)
        return self._response


def test_enterprise_client_emits_metrics_on_success(monkeypatch):
    notion_cfg = get_api_rate_config("notion")
    metrics_events: List[Dict[str, Any]] = []

    def metrics_handler(event: Dict[str, Any]) -> None:
        metrics_events.append(event)

    # Make the underlying session always return a 200 OK.
    session = DummySession(DummyResponse(200, {"ok": True}))

    client = EnterpriseClient(
        integration="notion",
        tenant_id="tenant-123",
        base_url="https://api.notion.com",
        rate_config=notion_cfg,
        metrics_handler=metrics_handler,
    )

    # Swap in our dummy session so no real HTTP is performed.
    client._client.session = session  # type: ignore[attr-defined]

    resp = client.request("GET", "/v1/databases", timeout=5.0)

    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # One metrics event per request, with basic fields populated.
    assert len(metrics_events) == 1
    event = metrics_events[0]
    assert event["integration"] == "notion"
    assert event.get("tenant_id") == "tenant-123"
    assert event.get("status_code") == 200
    assert isinstance(event.get("elapsed_ms"), (int, float))
    assert "rate_snapshot" in event


def test_circuit_breaker_opens_after_failures():
    notion_cfg = get_api_rate_config("notion")
    metrics_events: List[Dict[str, Any]] = []

    def metrics_handler(event: Dict[str, Any]) -> None:
        metrics_events.append(event)

    # Underlying session will always return a 500.
    session = DummySession(DummyResponse(500))

    cb_cfg = CircuitBreakerConfig(
        failure_threshold=2,
        open_interval=60.0,
    )

    client = EnterpriseClient(
        integration="notion",
        tenant_id=None,
        base_url="https://api.notion.com",
        rate_config=notion_cfg,
        circuit_breaker_config=cb_cfg,
        metrics_handler=metrics_handler,
    )

    client._client.session = session  # type: ignore[attr-defined]

    # First two requests should be attempted and recorded as failures.
    resp1 = client.request("GET", "/v1/databases", timeout=5.0)
    resp2 = client.request("GET", "/v1/databases", timeout=5.0)

    assert resp1.status_code == 500
    assert resp2.status_code == 500
    assert len(metrics_events) == 2

    # After reaching the failure threshold, the circuit should open and
    # further calls should raise CircuitOpenError.
    with pytest.raises(CircuitOpenError):
        client.request("GET", "/v1/databases", timeout=5.0)
