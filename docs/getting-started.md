# Getting Started

This page walks through installation, basic setup, and a first request.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/scottnorton-io/dynamic-api-rate-limiter.git
cd dynamic-api-rate-limiter
```

Install dependencies (development):

```bash
pip install -e ".[dev]"
```

For library usage only:

```bash
pip install requests
```

(Once this project is published to PyPI, you will be able to run:)

```bash
pip install dynamic-api-rate-limiter
```

---

## Quick Start

Create a client for Notion:

```python
from api_ratelimiter import make_client_for

notion = make_client_for("notion")
```

Make a request (example: fetch a page):

```python
import os

headers = {
    "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
    "Notion-Version": "2022-06-28",
}

resp = notion.request("GET", f"/pages/{os.environ['NOTION_PAGE_ID']}", headers=headers)
resp.raise_for_status()
data = resp.json()
print(data)
```

The rate limiter will:

- Pace requests to avoid hitting rate limits.
- Gradually **increase** the allowed rate on successful responses.
- **Decrease** the rate and respect cooldowns when the API returns 429.

---

## Per-API Configurations

The mapping for known APIs (Notion, Vanta, Fieldguide, etc.) lives in:

```text
api_ratelimiter/api_rate_config.py
```

You can:

- Adjust existing configs.
- Add new entries for custom APIs.
- Keep all rate tuning in a single place.
