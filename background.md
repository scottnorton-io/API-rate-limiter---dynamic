# Background & Design Notes – dynamic-api-rate-limiter

This document explains the design of the `dynamic-api-rate-limiter` library:
what problem it solves, how it works internally, and how to tune it for your
APIs and workloads.

---

## 1. Problem the library solves

Many APIs enforce rate limits, returning HTTP `429 Too Many Requests` when
clients exceed their quotas. Naive clients either:

- Hard-code a fixed requests-per-second value (often too conservative), or
- Ignore limits, hammer the API, and rely on repeated 429s to slow them down.

Neither is ideal if you want:

- **Maximum safe throughput** without constantly hitting rate limits.
- A **generic mechanism** that works across many APIs (Notion, Vanta,
  Fieldguide, etc.).
- **Centralized configuration** instead of scattering magic numbers in
  scripts and services.

This library provides:

- A dynamic, self-tuning rate limiter (`DynamicRateLimiter`).
- A simple HTTP client (`DynamicAPIClient`) that uses the limiter and
  respects `429` and `Retry-After` headers.
- A per-API configuration registry (`ApiRateConfig`) that keeps limit tuning
  in one place.

---

## 2. Conceptual model

At a high level, the library combines three pieces:

1. **Token-bucket rate limiting** (continuous-time, requests-per-second model).
2. **AIMD (Additive Increase / Multiplicative Decrease)** to adjust the rate.
3. **Backoff-aware HTTP client** that reacts to server signals (429, Retry-After).

### 2.1 Token bucket

The limiter maintains:

- `current_rate` – allowed requests per second (dynamic).
- `tokens` – how many requests are currently allowed to proceed immediately.
- `last_refill` – last time the bucket was refilled.
- `cooldown_until` – time until which all requests should wait (e.g. Retry-After).

Conceptually:

- Tokens accumulate over time at `current_rate` tokens/second.
- Each request consumes 1 token.
- If there are no tokens, callers must wait until enough have accumulated.
- The bucket is capped at (currently) 2 seconds worth of tokens to prevent
  unbounded bursts.

### 2.2 AIMD (Additive Increase / Multiplicative Decrease)

To discover and track the real-world rate limit of an API, the limiter uses:

- **Additive Increase** on success:
  - After every non-backoff response (non-429 by default),
    `current_rate` increases by `increase_step`, up to `max_rate`.
  - This slowly pushes the rate higher, probing for available capacity.

- **Multiplicative Decrease** on backoff:
  - When a backoff signal arrives (e.g. HTTP 429),
    `current_rate` is multiplied by `decrease_factor`.
  - `decrease_factor` is in `(0, 1]` (e.g. `0.5` to cut rate in half).
  - This quickly backs off from a rate that was too aggressive.

Over time, AIMD tends to converge to a rate just below the true limit,
while still adapting if conditions change (e.g., vendor changes limits,
shared tenants become busier, etc.).

---

## 3. Backoff & Retry-After behavior

The `DynamicAPIClient` is built around a simple loop:

1. Call `limiter.acquire()` (respecting tokens and cooldown).
2. Perform the HTTP request (with `requests`).
3. If response status is **not** in `backoff_status_codes`:
   - Treat it as success and call `limiter.on_success()`.
   - Return the response to the caller.
4. Otherwise (backoff status, e.g. 429):
   - If 429, inspect the `Retry-After` header:
     - If numeric seconds, pass that to `limiter.on_429(retry_after)`.
     - If missing or non-numeric, pass `None`, and the limiter chooses a
       conservative default cooldown based on `current_rate`.
   - If status is a different backoff code (e.g. 503) without explicit
     retry-after, `on_429(None)` is used with the same conservative logic.
   - The client retries until `max_retries_on_backoff` is exceeded, then
     raises a `RuntimeError`.

### 3.1 `backoff_status_codes`

By default, the client treats only 429 as a backoff signal:

```python
client = make_client_for("notion")
```

You can extend this, for example to back off on 503 as well:

```python
client = make_client_for(
    "notion",
    backoff_status_codes=(429, 503),
)
```

This is useful when an API vendor explicitly recommends backing off on
transient 5xx errors.

---

## 4. API configuration registry

`ApiRateConfig` captures tuning per API:

```python
@dataclass(frozen=True)
class ApiRateConfig:
    name: str
    base_url: str

    initial_rate: float
    min_rate: float
    max_rate: float
    increase_step: float
    decrease_factor: float

    documented_limit_desc: Optional[str] = None
```

This allows you to define a central table such as:

```python
API_RATE_CONFIGS = {
    "notion": ApiRateConfig(
        name="notion",
        base_url="https://api.notion.com/v1",
        initial_rate=2.0,
        min_rate=0.3,
        max_rate=3.5,
        increase_step=0.1,
        decrease_factor=0.5,
        documented_limit_desc="Approx. 3 requests/second per integration on average.",
    ),
    "vanta": ApiRateConfig(...),
    "fieldguide": ApiRateConfig(...),
}
```

A client is then one line away:

```python
from api_ratelimiter.clients import make_client_for

notion = make_client_for("notion")
```

This centralization means:

- No magic rate-limit numbers in scripts.
- Easy updates when vendors change limits.
- Clear, documented behavior per API.

---

## 5. Tuning guidance

A few practical tips for choosing `initial_rate`, `min_rate`, `max_rate`,
`increase_step`, and `decrease_factor`:

### 5.1 initial_rate

- If the vendor documents a rough limit (e.g. "3 requests/sec"), choose an
  initial rate slightly below that (e.g. 2.0).
- If limits are unknown, start conservatively (e.g. 1–3 req/sec) and let
  AIMD push upward.

### 5.2 min_rate

- Avoid zero; something like `0.1` is usually fine.
- If you want stronger guarantees about minimum throughput, use a higher
  value, but note that this might be too aggressive in very tight limits.

### 5.3 max_rate

- Set to what you believe is the safe upper bound for bursts.
- If documented limits say "5 req/sec", you might set `max_rate=5.0` or a
  little above if the vendor tolerates short bursts.

### 5.4 increase_step

- Controls how quickly the limiter ramps up on success.
- Smaller values are gentler (e.g. 0.1–0.2).
- Larger values converge faster but risk overshooting more often.

### 5.5 decrease_factor

- A value of `0.5` (cut rate in half) is a good default.
- Lower values (e.g. 0.25) back off more aggressively.
- Values closer to 1.0 are milder but may lead to more repeated 429s.

In general:

- Start with: `initial_rate` slightly below expected limit,
  `min_rate=0.1`, `max_rate=~1–2x` expected limit,
  `increase_step=0.1–0.2`, `decrease_factor=0.5`.
- Observe behavior in logs/metrics and adjust if needed.

---

## 6. Logging & metrics

The limiter now supports basic logging and a `snapshot()` method for metrics.

### 6.1 Logging

`DynamicRateLimiter` emits:

- A `debug` log on initialization.
- A `debug` log when `on_success()` increases the rate.
- A `warning` log when `on_429()` triggers backoff (with previous/new rate
  and cooldown info).

To enable these logs in your application:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

In a production environment, you might use `INFO` or `WARNING` as a baseline
and enable `DEBUG` temporarily when tuning.

### 6.2 snapshot() for metrics

`snapshot()` returns a dictionary like:

```python
snap = limiter.snapshot()
# {
#   "current_rate": 2.5,
#   "tokens": 1.7,
#   "cooldown_until": 1_708_000_000.123  # monotonic-based timestamp
# }
```

You can feed these values into your metrics system (e.g. Prometheus gauges
or a logging-based metrics pipeline). A simple pattern:

```python
import logging
from api_ratelimiter.clients import make_client_for

logger = logging.getLogger(__name__)

notion = make_client_for("notion")
limiter = notion.limiter  # DynamicAPIClient exposes its limiter

def log_rate_metrics() -> None:
    snap = limiter.snapshot()
    logger.info(
        "rate_limiter_snapshot",
        extra={
            "current_rate": snap["current_rate"],
            "tokens": snap["tokens"],
            "cooldown_until": snap["cooldown_until"],
        },
    )
```

You can call `log_rate_metrics()` periodically (e.g. in a background thread,
cron-like task, or at the end of a batch).

---

## 7. Single-process vs. distributed deployments

The current limiter is **thread-safe within a single process**. It assumes:

- One process / worker controls a given limiter instance.
- Multiple threads may issue requests, but all go through the same limiter.

If you run **multiple processes or pods** sharing the same API quota (e.g. a
Notion integration token), each process will behave politely on its own, but
the *aggregate* traffic might still exceed the vendor’s limits.

A future enhancement could introduce a **distributed token bucket** backed
by Redis, Postgres, or another shared store, allowing all workers to share
one global view of tokens and cooldowns.

---

## 8. Limitations and future ideas

Current limitations:

- Single-process, in-memory limiter (no distributed coordination).
- HTTP-only (no async client yet).
- Focused on request rate; does not manage concurrency limits or payload
  size-based throttling.

Potential future work:

- Async client (e.g. `httpx`-based) with the same `DynamicRateLimiter` core.
- Distributed rate limiter backend.
- Per-endpoint overrides (e.g. stricter limits for bulk export routes).
- Built-in Prometheus integration helpers.

---

## 9. Summary

The `dynamic-api-rate-limiter` library is designed to:

- Be **safe by default** (respect 429 + Retry-After).
- **Adapt** to real-world limits without hardcoding brittle numbers.
- Provide a **central configuration registry** for all your APIs.
- Offer **observability hooks** (logging + snapshots) to help you tune.
- Fit naturally into Python scripting and service code without heavy
  dependencies.

If you’re integrating multiple systems (e.g. Notion, Vanta, Fieldguide, and
other evidence sources), this gives you one consistent, extensible pattern
for staying within limits while keeping throughput high.
