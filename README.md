# API Rate Limiter – Dynamic, Self-Tuning, 429-Aware Python Client

[![CI](https://github.com/scottnorton-io/dynamic-api-rate-limiter/actions/workflows/ci.yml/badge.svg)](https://github.com/scottnorton-io/dynamic-api-rate-limiter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%20|%203.10%20|%203.11%20|%203.12-blue.svg)](https://github.com/scottnorton-io/dynamic-api-rate-limiter)


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
- Backs off safely on 429s
- Learns the real allowable throughput of the API

This is ideal for compliance automation, ETL, scripting, and backend services.

---

## 🔥 Features

### ✔️ Dynamic Rate Learning

The limiter uses **AIMD (Additive Increase / Multiplicative Decrease)**:

- Slowly increases speed on success
- Quickly decreases speed on 429
- Auto-pauses when the API tells you to wait
- Stabilizes at the optimal rate

### ✔️ API Configuration Registry

Centralized config table for:

- Notion
- Vanta
- Fieldguide
- Any API you add

### ✔️ One-Line API Client Creation

```python
from api_ratelimiter.clients import make_client_for

notion = make_client_for("notion")
vanta = make_client_for("vanta")
fg = make_client_for("fieldguide")
```

### ✔️ Fully Modular

- Swap rate config without touching calling code
- Add new APIs in seconds
- No duplication between scripts

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
        dynamic_ratelimiter.py
        api_rate_config.py
        clients.py
    examples/
        example_notion.py
        example_vanta.py
        example_fieldguide.py
    .github/
        workflows/ci.yml
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

## 📚 Background / Design Notes

For deeper context on the design, AIMD behavior, and how this fits into a broader compliance automation toolchain, see `background.md`.

---

## 🧪 Running the examples

From the repo root:

```bash
python examples/example_notion.py
python examples/example_vanta.py
python examples/example_fieldguide.py
```

(You’ll need to export the appropriate `*_TOKEN` and ID environment variables as described in each example file.)

---

## 📄 License

MIT License © 2025 Scott Norton

---

## 💬 Contributing

Issues and pull requests are welcome.

See `CONTRIBUTING.md` for details on setup, linting, and tests.
