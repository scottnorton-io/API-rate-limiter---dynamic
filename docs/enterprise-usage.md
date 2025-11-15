# Enterprise Usage

This document shows how to use the enterprise‑oriented wrapper that ships with
`dynamic-api-rate-limiter`. It builds on the core `DynamicRateLimiter` and
`DynamicAPIClient`, adding:

- Structured logging.
- A single **metrics event** per request.
- A simple, configurable **circuit breaker**.

You can adopt this wrapper in production services where you need more observability and
stronger protection around a critical upstream API.

---

## Concepts

### EnterpriseClient

`EnterpriseClient` wraps a `DynamicAPIClient` and exposes a familiar `request(...)` method.
It:

- Calls the underlying dynamic client for every HTTP request.
- Collects timing and limiter information.
- Emits a metrics event (if you provide a handler).
- Emits structured logs using a logger of your choice.
- Applies a **circuit breaker** around the call.

### CircuitBreakerConfig and CircuitOpenError

The circuit breaker is configured via `CircuitBreakerConfig` and, when open, will cause
`EnterpriseClient.request(...)` to raise `CircuitOpenError` *before* any HTTP request is
attempted.

At a high level, the breaker:

- Tracks failures (typically 5xx responses or exceptions).
- Opens after a configured `failure_threshold` is reached.
- Stays open for `open_interval` seconds.
- After the open interval, allows requests again and resets the failure count if they succeed.

The exact behaviour is implemented in `api_ratelimiter.enterprise` and is intentionally small
and easy to read.

### MetricsHandler

A `MetricsHandler` is a simple callable:

```python
from typing import Protocol, Dict, Any

class MetricsHandler(Protocol):
    def __call__(self, event: Dict[str, Any]) -> None: ...
```

`EnterpriseClient` will call this handler with a single event dictionary for each request.
The event includes things like:

- `integration`
- `tenant_id`
- `status_code`
- `elapsed_ms`
- `rate_snapshot` (from the underlying limiter)
- `context` (pass‑through context provided at construction)
- `error` (if an exception occurred)

You can route these events to whatever metrics/observability stack you use (Prometheus,
StatsD, Datadog, Honeycomb, OpenTelemetry, …).

---

## Basic example

```python
from api_ratelimiter.enterprise import (
    EnterpriseClient,
    CircuitBreakerConfig,
    CircuitOpenError,
)
from api_ratelimiter.api_rate_config import get_api_rate_config

def metrics_handler(event: dict) -> None:
    # Example: emit to logs or push to your metrics backend.
    print("METRICS EVENT:", event)

notion_cfg = get_api_rate_config("notion")

client = EnterpriseClient(
    integration="notion",
    tenant_id="tenant-123",
    base_url="https://api.notion.com",
    rate_config=notion_cfg,
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        open_interval=60.0,
    ),
    metrics_handler=metrics_handler,
)

try:
    resp = client.request(
        "GET",
        "/v1/databases",
        headers={
            "Authorization": "Bearer YOUR_TOKEN",
            "Notion-Version": "2022-06-28",
        },
        timeout=10.0,
    )
    resp.raise_for_status()
except CircuitOpenError:
    # The breaker is open; you might want to short‑circuit here.
    ...
```

---

## Backoff handling and `on_429`

Internally, the dynamic client uses `DynamicRateLimiter.on_429(...)` as its **generic backoff
handler** for all configured backoff status codes, not just HTTP 429.

- If the status code is 429 and a `Retry-After` header is present, that header is respected to
  set the cooldown window.
- For other configured backoff status codes, a conservative cooldown is derived from the current
  rate and a `cooldown_multiplier` on the limiter.

> ℹ️ The method name is kept as `on_429` for historical reasons, but it should be understood as
> “on backoff signal” in the current design.

---

## Timeouts and reliability

`EnterpriseClient` simply forwards any `timeout` you pass to the underlying `requests` call.
It does **not** pick a default for you.

We strongly recommend that you always set a timeout explicitly:

```python
response = client.request("GET", "/v1/resource", timeout=10.0)
```

Without timeouts, slow or unresponsive upstream APIs can tie up workers indefinitely, and the
rate limiter cannot help you recover.

---

## Exceptions

`EnterpriseClient.request(...)` may raise:

- Exceptions from `requests` (connection errors, timeouts, etc.).
- `RuntimeError` from the underlying dynamic client if it gives up after
  `max_retries_on_backoff` attempts.
- `CircuitOpenError` if the circuit breaker is currently open.

Downstream callers should handle these according to the criticality of the upstream API. A
common pattern is to treat `CircuitOpenError` as a “fail fast” signal and return a clear,
degraded‑mode response to your own callers.

---

## Concurrency notes

The underlying rate limiter is:

- **Thread‑safe** within a single process.
- **Not distributed** across processes or hosts.

For multi‑process or multi‑node architectures, you can:

- Use one limiter per process as a *local* protection mechanism.
- Combine this with upstream limits and, if needed, a distributed rate‑limiting solution for
  hard global caps.

The enterprise wrapper does not change these guarantees; it simply layers logging, metrics, and
a circuit breaker around the same single‑process limiter.
