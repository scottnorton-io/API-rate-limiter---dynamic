# Metrics & Observability

The library is designed to integrate easily with logging and metrics systems.

---

## Logging

`DynamicRateLimiter` uses the standard `logging` module:

- `DEBUG` logs when the rate increases.
- `WARNING` logs when backoff is triggered (`on_429`).

Enable simple logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

---

## snapshot() for Metrics

`DynamicRateLimiter.snapshot()` returns:

```python
snap = limiter.snapshot()
# {
#   "current_rate": 2.5,
#   "tokens": 1.7,
#   "cooldown_until": 1708000000.123
# }
```

Use this to:

- Feed Prometheus gauges.
- Emit log-based metrics (Datadog, Loki, CloudWatch, etc.).
- Build dashboards over time.

A simple pattern:

```python
import logging
from api_ratelimiter import make_client_for

logger = logging.getLogger("rate_limiter_metrics")

client = make_client_for("notion")
limiter = client.limiter

snap = limiter.snapshot()
logger.info(
    "limiter_snapshot",
    extra={
        "current_rate": snap["current_rate"],
        "tokens": snap["tokens"],
        "cooldown_until": snap["cooldown_until"],
    },
)
```

---

For more detailed examples (including Prometheus-style pseudo-code), see
`METRICS.md` in the repository.

---

## Enterprise Client Wrapper

For larger deployments you may want more than just the raw rate limiter.
The :class:`EnterpriseClient` adds:

- Structured logging for each request.
- A pluggable `metrics_handler` callback.
- Optional circuit-breaker behavior.
- Optional `tenant_id` to support multi-tenant usage.

```python
import logging
from api_ratelimiter import (
    EnterpriseClient,
    CircuitBreakerConfig,
    make_enterprise_client,
)

logger = logging.getLogger("api_ratelimiter_example")

def metrics_sink(event: dict) -> None:
    # Map this event into Prometheus / StatsD / OpenTelemetry as needed
    print("metrics event:", event)

cb_cfg = CircuitBreakerConfig(failure_threshold=5, open_interval=60.0)

client = make_enterprise_client(
    "notion",
    tenant_id="tenant-123",
    logger=logger,
    metrics_handler=metrics_sink,
    circuit_breaker=cb_cfg,
)

resp = client.request("GET", "/v1/search", json={"query": "example"})
```

The `event` dictionary handed to `metrics_handler` contains keys like:

- `integration`
- `tenant_id`
- `method`
- `path`
- `status_code` (if a response was received)
- `elapsed_ms`
- `rate_snapshot` (from the underlying limiter)
- `error` (if an exception occurred)
- `context` (any additional context you passed)
```)
