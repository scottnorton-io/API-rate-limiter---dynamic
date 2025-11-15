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
