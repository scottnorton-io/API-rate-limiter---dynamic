[![CI](https://github.com/scottnorton-io/dynamic-api-rate-limiter/actions/workflows/ci.yml/badge.svg)](https://github.com/scottnorton-io/dynamic-api-rate-limiter/actions/workflows/ci.yml)
[![Docs](https://github.com/scottnorton-io/dynamic-api-rate-limiter/actions/workflows/docs.yml/badge.svg)](https://github.com/scottnorton-io/dynamic-api-rate-limiter/actions/workflows/docs.yml)
[![PyPI](https://img.shields.io/badge/PyPI-not--released-lightgrey.svg)](https://pypi.org/project/dynamic-api-rate-limiter/)

# Dynamic API Rate Limiter – Self-Tuning, 429-Aware Python Client

### Developed by Scott Norton • https://github.com/scottnorton-io/

This library provides a production-grade, dynamic rate limiter designed for:

- Notion API
- Vanta API
- Fieldguide API
- Any REST API (plug-and-play)

It automatically:

- Avoids hitting rate limits
- Adapts its speed dynamically
- Respects `Retry-After` headers
- Backs off safely on 429s (and optionally other status codes)
- Learns the real allowable throughput of the API

This is ideal for compliance automation, ETL, scripting, and backend services.

---

## 🔥 Features

### ✔️ Dynamic Rate Learning (AIMD)

The limiter uses **AIMD (Additive Increase / Multiplicative Decrease)**:

- Slowly increases speed on success
- Quickly decreases speed on backoff (e.g. 429)
- Auto-pauses when the API tells you to wait (`Retry-After`)
- Stabilizes near the optimal rate for that API

### ✔️ API Configuration Registry

Centralized config table for:

- Notion
- Vanta
- Fieldguide
- Any API you add

All rate-tuning parameters live in one place: `api_ratelimiter/api_rate_config.py`.

### ✔️ One-Line API Client Creation

```python
from api_ratelimiter.clients import make_client_for

notion = make_client_for("notion")
vanta = make_client_for("vanta")
fg = make_client_for("fieldguide")
```

### ✔️ Backoff-Aware HTTP Client

- Honors `Retry-After` on HTTP 429.
- Retries up to a configurable maximum.
- Can treat additional status codes (like 503) as backoff signals via
  `backoff_status_codes`.

```python
client = make_client_for(
    "notion",
    backoff_status_codes=(429, 503),
)
```

### ✔️ Logging & Metrics Ready

- Uses Python's `logging` module for debug + backoff logs.
- Exposes a `snapshot()` method for metrics (current rate, tokens, cooldown).
- Example: `examples/example_logging_metrics.py` shows how to log limiter state.

---

## 📦 Installation

Install dependencies:

```bash
pip install requests
```

Clone the repo:

```bash
git clone https://github.com/scottnorton-io/dynamic-api-rate-limiter.git
cd dynamic-api-rate-limiter
```

(Optional) install in editable mode:

```bash
pip install -e .
```

---

## 📘 Quick Start Example (Notion)

```python
from api_ratelimiter.clients import make_client_for

notion = make_client_for("notion")


def get_page(page_id: str, token: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }
    resp = notion.request("GET", f"/pages/{page_id}", headers=headers)
    resp.raise_for_status()
    return resp.json()


print(get_page("YOUR_PAGE_ID", "YOUR_INTEGRATION_TOKEN"))
```

---

## 🧠 Architecture

```text
dynamic-api-rate-limiter/
    api_ratelimiter/
        __init__.py
        dynamic_ratelimiter.py   # Adaptive token bucket (AIMD)
        api_rate_config.py       # Centralized API config table
        clients.py               # Dynamic API client + factory
    examples/
        example_notion.py
        example_vanta.py
        example_fieldguide.py
        example_logging_metrics.py
    .github/
        workflows/ci.yml
    tests/
        test_dynamic_ratelimiter.py
        test_clients.py
    README.md
    CONTRIBUTING.md
    LICENSE
    pyproject.toml
    background.md
```

---

## 🛠 Adding a New API

1. Edit `api_ratelimiter/api_rate_config.py`
2. Add:

```python
from api_ratelimiter.api_rate_config import ApiRateConfig, API_RATE_CONFIGS

API_RATE_CONFIGS["new_api"] = ApiRateConfig(
    name="new_api",
    base_url="https://api.example.com/v1",
    initial_rate=2.0,
    min_rate=0.3,
    max_rate=5.0,
    increase_step=0.1,
    decrease_factor=0.5,
    documented_limit_desc="Vendor says 5 req/sec allowed.",
)
```

3. Use it:

```python
from api_ratelimiter.clients import make_client_for

client = make_client_for("new_api")
resp = client.request("GET", "/some/endpoint")
```

---

## 📊 Logging & Metrics

The limiter integrates with the standard `logging` module and exposes
a `snapshot()` method for metrics.

### Enable logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

You will see:

- `DEBUG` logs when the rate increases.
- `WARNING` logs when backoff (`on_429`) is triggered.

### Emit metrics from snapshot()

```python
from api_ratelimiter.clients import make_client_for

client = make_client_for("notion")
limiter = client.limiter

snap = limiter.snapshot()
# {
#   "current_rate": 2.5,
#   "tokens": 1.7,
#   "cooldown_until": 1708000000.123
# }
```

You can push these values to Prometheus, CloudWatch, or any metrics backend
you use. The example script `examples/example_logging_metrics.py` shows how
to log them periodically.

---

## 🧪 Running the examples

From the repo root:

```bash
python examples/example_notion.py
python examples/example_vanta.py
python examples/example_fieldguide.py
python examples/example_logging_metrics.py
```

(You’ll need to export the appropriate `*_TOKEN` and ID environment variables
as described in each example file.)

---

## 📚 Background / Design Notes

For deeper context on:

- Token bucket implementation
- AIMD behavior
- Backoff + Retry-After flow
- Tuning guidance

see [`background.md`](./background.md).

---

## 📄 License

MIT License © 2025 Scott Norton

---

## 💬 Contributing

Issues and pull requests are welcome.

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for details on setup, linting, and tests.


## 📖 Documentation Site

Once GitHub Pages is enabled for this repository, the MkDocs documentation
will be available at:

- https://scottnorton-io.github.io/dynamic-api-rate-limiter/

You can also build and serve the docs locally:

```bash
pip install mkdocs
mkdocs serve
```

Then open http://127.0.0.1:8000/ in your browser.
## 🔐 Secure Secrets on macOS

For macOS users, you can store API tokens in the native Keychain using the
`keyring` library and avoid keeping secrets in plain environment variables.

See:

- `docs/security-macos.md` (or the "Security on macOS" page in the docs site)
- `examples/example_keyring_macos.py`

for a concrete pattern.

## 🌐 Integrations Registry

Supported integrations and their typical env vars/examples are documented in:

- `INTEGRATIONS.md`
- `docs/integrations.md` (also visible in the docs site under "Integrations")
