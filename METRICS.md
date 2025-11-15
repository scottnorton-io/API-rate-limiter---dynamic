# Metrics & Observability Guide

This document shows a few patterns for exporting limiter metrics from
`dynamic-api-rate-limiter` into your observability stack.

The key primitive is:

```python
snap = limiter.snapshot()
# {
#   "current_rate": 2.5,
#   "tokens": 1.7,
#   "cooldown_until": 1708000000.123
# }
```

You can call this periodically and push the values to any metrics system.

---

## 1. Logging-based metrics

If you already use log-based metrics (e.g. Datadog log pipelines, Loki, etc.),
you can emit a structured log on a regular interval.

```python
import logging
import time

from api_ratelimiter.clients import make_client_for

logger = logging.getLogger("rate_limiter_metrics")

client = make_client_for("notion")
limiter = client.limiter

def log_metrics_loop() -> None:
    while True:
        snap = limiter.snapshot()
        logger.info(
            "limiter_snapshot",
            extra={
                "current_rate": snap["current_rate"],
                "tokens": snap["tokens"],
                "cooldown_until": snap["cooldown_until"],
            },
        )
        time.sleep(10)
```

Your logging pipeline can then aggregate these values as gauges over time.

---

## 2. Prometheus (conceptual example)

If you're using Prometheus in Python, you might do something like:

```python
from prometheus_client import Gauge, start_http_server

from api_ratelimiter.clients import make_client_for

client = make_client_for("notion")
limiter = client.limiter

g_current_rate = Gauge("api_limiter_current_rate", "Current requests/sec")
g_tokens = Gauge("api_limiter_tokens", "Available tokens")
g_cooldown_until = Gauge("api_limiter_cooldown_until", "Cooldown end (monotonic time)")

def collect_metrics() -> None:
    snap = limiter.snapshot()
    g_current_rate.set(snap["current_rate"])
    g_tokens.set(snap["tokens"])
    g_cooldown_until.set(snap["cooldown_until"])
```

Then hook `collect_metrics()` into whatever loop or scheduler you use, and
expose Prometheus metrics via `start_http_server(...)` or your existing exporter.

---

## 3. General recommendations

- Consider logging metrics on a **fixed interval** (e.g. every 10–30 seconds)
  rather than on every request, to reduce noise.
- Correlate limiter metrics with error rates and response latency from your
  APIs to see how rate changes impact performance.
- Start with simple dashboards:
  - `current_rate` over time
  - 429/backoff events over time
- Use these metrics to tune `max_rate`, `increase_step`, and `decrease_factor`
  for each API configuration.
