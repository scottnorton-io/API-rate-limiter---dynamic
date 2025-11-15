# Background & Design Notes

This document provides additional context on the goals, design choices, and
trade-offs behind `dynamic-api-rate-limiter`.

The short version:

- We want **maximum safe throughput** against third-party APIs.
- We want to **avoid hard-coding limits** whenever possible.
- We want to **treat the API as the source of truth** about when to slow down
  (via status codes and `Retry-After` headers).
- We want a small, composable tool that can be dropped into scripts or used
  as a library.

---

## Goals

1. **Stay under vendor rate limits without guessing blindly.**
   Hard-coding `60 requests/minute` works until:
   - The vendor changes limits.
   - Limits differ by endpoint or plan.
   - You run multiple workers and collectively exceed the limit.

2. **Adapt dynamically based on feedback from the API.**
   Instead of just capping at an arbitrary rate, we want to *learn* the
   effective ceiling by watching for overload signals like `429`, `502`,
   and `503`.

3. **Be easy to adopt.**
   - A single `make_client_for("notion")` call.
   - Centralized configuration for each API.
   - No heavy dependencies.

---

## Core Design

There are three main pieces:

1. `DynamicRateLimiter` – an adaptive token-bucket limiter using
   AIMD (Additive Increase / Multiplicative Decrease).
2. `DynamicAPIClient` – a small HTTP wrapper that applies the limiter and
   handles backoff on selected status codes.
3. `ApiRateConfig` – a registry of per-API defaults (Notion, Vanta,
   Fieldguide, etc.).

### 1. DynamicRateLimiter (AIMD + token bucket)

The limiter tracks a **current rate in requests per second** and exposes:

- `acquire()` – blocks until a request token is available.
- `on_success()` – called after successful (non-backoff) responses.
- `on_429(retry_after)` – called when the API signals overload or rate limit.

Internally it uses a token bucket:

- Tokens accumulate over time at `current_rate`.
- Each outgoing request consumes one token.
- The bucket is capped at roughly two seconds' worth of tokens to avoid
  unbounded bursts.

The rate evolves using AIMD:

- **Additive Increase** (on success):
  - `current_rate += increase_step` up to `max_rate`.
  - This slowly probes for additional capacity.

- **Multiplicative Decrease** (on backoff):
  - `current_rate = current_rate * decrease_factor`, bounded by `min_rate`.
  - This quickly backs away when the API complains.

Cooldowns are enforced via a wall-clock deadline:

- When `on_429(retry_after)` is called, we compute a `cooldown_until` time.
- `acquire()` will:
  - Immediately return if we're past the cooldown and have tokens.
  - Otherwise sleep until `cooldown_until` or until tokens become available.

### 2. DynamicAPIClient (HTTP wrapper)

The client is intentionally thin:

- Calls `limiter.acquire()` before each request.
- Dispatches HTTP calls through a `requests.Session`.
- Categorizes responses into:
  - **Normal**: status not in `backoff_status_codes`.
  - **Backoff**: status in `backoff_status_codes` (by default: 429, 502, 503).

Normal responses:

- Call `limiter.on_success()`.
- Return the response to the caller.

Backoff responses:

- Read the `Retry-After` header if present (seconds).
- Call `limiter.on_429(retry_after_seconds)`.
- Retry up to `max_retries_on_429` times.

The reasoning behind the default backoff set:

- **429 Too Many Requests** – explicit signal that you hit a rate limit.
- **502 Bad Gateway / 503 Service Unavailable** – often mean a transient
  overload or upstream issue. Backing off slightly is almost always
  the polite thing to do.

If you want stricter or looser behaviour, you can override
`backoff_status_codes` when constructing the client.

### 3. ApiRateConfig (per-API defaults)

Each API gets a small configuration record:

- `base_url`: where requests go.
- `initial_rate`: starting guess for requests per second.
- `min_rate` / `max_rate`: safe bounds for dynamic rate changes.
- `increase_step` / `decrease_factor`: tuning knobs for AIMD behaviour.
- `documented_limit_desc`: human-readable notes about vendor limits.

The config lives in `api_rate_config.py` and is used by `make_client_for()`
to construct a `DynamicAPIClient` with sensible defaults for each API.

---

## Error Handling & Trade-offs

### Why still call it `on_429` if it handles 502/503?

The name is historical: the method was originally introduced for handling
429 status codes specifically. It has since been generalized as the
"backoff hook" for all configured overload responses.

Renaming it to `on_backoff()` would be more semantically accurate, but
would also be a breaking change for existing users. For now, we keep the
name and treat 429, 502, 503 (and any other status codes you configure)
as triggers for the same backoff logic.

### Per-process vs global limits

The current implementation is **process-local**:

- Each process or worker has its own limiter.
- If you run many workers, they may collectively exceed a global rate
  limit that the vendor enforces across your account or IP.

For most single-script or modestly parallel use cases this is fine.
For highly concurrent workloads, a future evolution could add a
distributed backend (e.g. Redis) to coordinate tokens across workers.

---

## Testing Strategy

The `tests/` directory includes:

- Behavioural tests for `DynamicRateLimiter`:
  - Ensuring `on_success()` increases rate up to `max_rate`.
  - Ensuring `on_429()` reduces rate and enforces cooldown without
    relying on real wall-clock sleeps (we patch `time.sleep` and
    `time.monotonic` in tests).
- Behavioural tests for `DynamicAPIClient`:
  - Verifying that normal responses call `on_success()`.
  - Verifying that 429 responses use `Retry-After` and call the backoff hook.
  - Verifying that 503 responses trigger backoff when part of
    `backoff_status_codes`.

These tests are intentionally small and fast so they can run in CI on
every push and pull request.

---

## Extensibility

A few ways you can extend this library safely:

- **New APIs**: add entries to `API_RATE_CONFIGS` and optionally examples
  under `examples/`.
- **Custom backoff policy**: subclass `DynamicRateLimiter` or provide your
  own limiter object as long as it exposes the same three methods
  (`acquire`, `on_success`, `on_429`).
- **Telemetry / metrics**: wrap calls to `on_success` / `on_429` and
  `acquire` to emit tracing or metrics (e.g. Prometheus, logs).

---

If you have ideas for improving the algorithm, adding new presets for
popular APIs, or supporting a distributed limiter backend, contributions
are very welcome. See `CONTRIBUTING.md` for details.
