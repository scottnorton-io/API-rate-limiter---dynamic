# Dynamic API Rate Limiter

A small, focused Python library for *dynamic*, backoff‑aware rate limiting of third‑party APIs.

It is designed for integrations like Notion, Vanta, Fieldguide, Airtable, Zapier, Slack, GitHub, OpenAI, and similar
SaaS APIs where you:
- **Do not fully control** the upstream rate limits.
- Need to **react to 429 / backoff signals** (and sometimes 5xx bursts).
- Want a **simple, single‑process** library you can drop into workers or services.

At its core is an **AIMD (Additive‑Increase / Multiplicative‑Decrease)** token‑bucket rate limiter, wrapped in a
small HTTP client and (optionally) an enterprise‑oriented wrapper that adds logging, metrics, and a simple
circuit breaker.

---

## Features

- **Dynamic rate limiting** using AIMD + token bucket.
- **Backoff aware**: uses `Retry-After` and/or a conservative cooldown for 429 and other configured status codes.
- **Thread‑safe**, single‑process design.
- **Per‑API configuration** (Notion, Vanta, Fieldguide, Airtable, Zapier, Slack, GitHub, OpenAI, …).
- **Config overrides** via JSON for per‑tenant / per‑environment tuning.
- **Enterprise wrapper** with:
  - Structured logging.
  - Metrics callback (single event dict for each request).
  - A simple circuit breaker to protect upstream APIs.
- **Examples** for common APIs and patterns (including macOS Keychain usage).

For full documentation, see the published docs site or the `docs/` directory in this repository.

---

## Quick start

```bash
pip install dynamic-api-rate-limiter
```

Basic usage with the built‑in configuration for a known integration (for example Notion):

```python
from api_ratelimiter.clients import make_client_from_config

client = make_client_from_config("notion")

resp = client.request(
    "GET",
    "/v1/databases",
    headers={"Authorization": "Bearer YOUR_TOKEN", "Notion-Version": "2022-06-28"},
    timeout=10.0,  # strongly recommended: always set a timeout
)
resp.raise_for_status()
print(resp.json())
```

If you want full control over the configuration, you can create and wire everything yourself:

```python
from api_ratelimiter.dynamic_ratelimiter import DynamicRateLimiter
from api_ratelimiter.clients import DynamicAPIClient

limiter = DynamicRateLimiter(
    rate_limit_per_sec=3.0,
    burst_size=3.0,
    increase_factor=0.1,
    decrease_factor=0.5,
    min_rate=0.1,
    max_rate=10.0,
    cooldown_multiplier=1.5,
)

client = DynamicAPIClient(
    base_url="https://api.example.com",
    limiter=limiter,
    backoff_status_codes=(429, 503),
)

response = client.request("GET", "/v1/resource", timeout=10.0)
```

---

## Architecture overview

This repository is intentionally small and focused. The main pieces are:

```text
api_ratelimiter/
  __init__.py               # Public exports and package version.

  dynamic_ratelimiter.py    # Core AIMD + token bucket rate limiter.
                            # - Single-process, thread-safe.
                            # - Tracks current rate, tokens, cooldown window.
                            # - Exposes `acquire()`, `on_success()`, `on_429()`
                            #   (historical name: generic backoff handler),
                            #   and `snapshot()` for observability.

  api_rate_config.py        # ApiRateConfig dataclass and built-in API configs.
                            # - Central registry of per-API defaults.
                            # - `get_api_rate_config(name)` helper.

  clients.py                # HTTP client wrapper (requests-based).
                            # - `DynamicAPIClient` that:
                            #     * Calls `limiter.acquire()` before each request.
                            #     * Treats configured status codes as backoff signals.
                            #     * Uses `Retry-After` when present for 429s.
                            # - Factory helpers:
                            #     * `make_client_for(config)`
                            #     * `make_client_from_config(name)`

  config_overrides.py       # Runtime configuration overrides.
                            # - `load_api_rate_overrides_json(path)`:
                            #     Load validated overrides from JSON on disk.
                            # - `merged_api_rate_configs(overrides)`:
                            #     Merge overrides with built-in configs.
                            # - `list_available_integrations()`:
                            #     Introspection for CLIs / admin tools.

  enterprise.py             # Enterprise wrapper.
                            # - `EnterpriseClient` that wraps DynamicAPIClient and adds:
                            #     * Structured logging.
                            #     * Metrics handler callback.
                            #     * Circuit breaker (`CircuitBreakerConfig`). 
                            # - Raises `CircuitOpenError` when the breaker is open.

examples/
  example_notion.py         # Notion API example.
  example_vanta.py          # Vanta example (sample; requires customization).
  example_fieldguide.py     # Fieldguide example (sample; requires customization).
  example_airtable.py       # Airtable example.
  example_zapier.py         # Zapier example.
  example_slack.py          # Slack example.
  example_github.py         # GitHub example.
  example_openai.py         # OpenAI example.
  example_keyring_macos.py  # macOS keychain usage pattern.

docs/
  getting-started.md
  usage.md
  integrations.md
  configuration.md
  deployment.md
  metrics.md
  design.md
  security-macos.md
  changelog.md
```

---

## Enterprise usage (high level)

For more advanced cases, you can use the enterprise wrapper to get structured logging, metrics,
and a circuit breaker:

```python
from api_ratelimiter.enterprise import (
    EnterpriseClient,
    CircuitBreakerConfig,
    CircuitOpenError,
)

from api_ratelimiter.api_rate_config import get_api_rate_config

def metrics_handler(event: dict) -> None:
    # Example: push to your metrics system of choice.
    # `event` includes: integration, tenant_id, status_code, elapsed_ms,
    # limiter snapshot, context, and error details (if any).
    print("EVENT", event)

enterprise_client = EnterpriseClient(
    integration="notion",
    tenant_id="tenant-123",
    base_url="https://api.notion.com",
    rate_config=get_api_rate_config("notion"),
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        open_interval=60.0,
    ),
    metrics_handler=metrics_handler,
)

try:
    resp = enterprise_client.request(
        "GET", "/v1/databases", timeout=10.0
    )
except CircuitOpenError:
    # The circuit is open; you may want to short‑circuit or return a fast failure.
    ...
```

See `docs/usage.md` and `docs/metrics.md` for more detailed patterns and examples.

---

## Configuration overrides

By default, the library ships with conservative per‑API configs for several common SaaS APIs.
You can override or extend these at runtime using a JSON file and the helpers in
`api_ratelimiter.config_overrides`.

A minimal override file might look like:

```json
{
  "custom_api": {
    "rate_limit_per_sec": 2.0,
    "burst_size": 2.0,
    "increase_factor": 0.1,
    "decrease_factor": 0.5,
    "min_rate": 0.1,
    "max_rate": 5.0,
    "cooldown_multiplier": 1.5
  }
}
```

Then in Python:

```python
from api_ratelimiter.config_overrides import (
    load_api_rate_overrides_json,
    merged_api_rate_configs,
    list_available_integrations,
)

overrides = load_api_rate_overrides_json("overrides.json")
configs = merged_api_rate_configs(overrides)

print("Available integrations:", list_available_integrations(configs))
```

---

## Timeouts and reliability

This library **does not** force a default timeout on HTTP requests, but it **strongly recommends**
that you always pass an explicit `timeout` to `.request(...)` (on both `DynamicAPIClient` and
`EnterpriseClient`).

```python
response = client.request("GET", "/v1/resource", timeout=10.0)
```

Without a timeout, your code can hang indefinitely on a slow or unresponsive upstream API.

---

## Concurrency model

- The rate limiter is **thread‑safe** within a single process.
- It is **not distributed**: if you run multiple processes or nodes, each process will have its
  own limiter state.
- For multi‑process / multi‑node deployments, you can still use this library as a *local*
  protection mechanism at each worker while relying on upstream limits and/or a future
  distributed implementation for hard global limits.

---

## Exceptions

The library tries to keep exceptions simple and predictable:

- HTTP errors are surfaced via `requests` as usual (`response.raise_for_status()`).
- When the dynamic client gives up after the configured `max_retries_on_backoff`, it raises
  a **`RuntimeError`** with a short explanation.
- When the enterprise circuit breaker is open, `EnterpriseClient.request(...)` raises
  **`CircuitOpenError`** before any HTTP call is made.

See the docstrings and `docs/usage.md` for more detail.

---

## Development

- Formatting & linting: `ruff`
- Tests: `pytest`
- Docs: `mkdocs`

Typical commands during development:

```bash
pip install -e ".[dev]"
ruff check api_ratelimiter tests examples
pytest
mkdocs serve
```

CI runs the linter and test suite across supported Python versions on every push and pull
request. A separate workflow builds and publishes docs and tagged releases to PyPI.
