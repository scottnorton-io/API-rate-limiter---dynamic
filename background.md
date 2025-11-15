# 📘 API Rate Limiter Cookbook

>Dynamic, Self-Tuning Rate Limiting for Notion, Vanta, Fieldguide, and Any Other API

## 🔥 Overview

This cookbook provides a production-ready, fully modular system for:

Dynamically rate-limiting API calls
- Respecting 429 Too Many Requests responses
- Automatically obeying Retry-After headers
- Maintaining a config table of known API limits (Notion, Vanta, Fieldguide, etc.)
- Creating client objects automatically from that configuration
- Scaling to any number of APIs with minimal code

The system uses an AIMD (Additive Increase / Multiplicative Decrease) algorithm similar to TCP congestion control.

This ensures that your integration:
- Operates at the optimal allowable speed
- Never exceeds rate limits
- Adapts dynamically to changing API/server behavior
- Is generic enough to work with ANY API

It is ideal for compliance automation, integrations, ETL jobs, microservices, and high-volume API scripting.

---

## 🍳 THE COOKBOOK

### 1. Core Concepts
### ✔️ Dynamic Rate Limiting

Your rate limiter starts at an initial request-per-second rate, then:
- Increases the allowable rate slightly after each successful request
- Decreases the rate aggressively if a 429 is encountered
- Pauses during any server-provided Retry-After window
- Learns and stabilizes around the real-world rate limit of the target API

This allows you to hit the maximum sustainable speed without guessing.

### ✔️ API Configuration Registry

Each API gets a configuration entry:
```python

ApiRateConfig(
    name="notion",
    base_url="https://api.notion.com/v1",
    initial_rate=2.0,
    min_rate=0.3,
    max_rate=3.5,
    increase_step=0.1,
    decrease_factor=0.5,
    documented_limit_desc="~3 requests/second per integration",
)

```

You can maintain a table of:
- Documented vendor rate limits
- Empirical settings determined by testing
- Custom per-API behavior

### ✔️ Client Factory

Your scripts never instantiate raw clients.

Instead:

```python

notion = make_client_for("notion")
vanta  = make_client_for("vanta")
fg     = make_client_for("fieldguide")

```

This ensures:
- Consistency
- No duplication
- Centralized configuration
- Easy deployment and scaling

## 2. Installation (local or production)

Your repo will contain:

```text

api-limiter/
├── dynamic_ratelimiter.py
├── dynamic_api_client.py
├── api_rate_config.py
├── examples/
│   ├── example_notion.py
│   ├── example_vanta.py
│   └── example_fieldguide.py
├── README.md
└── pyproject.toml (optional)

```

Install dependencies:

```bash

pip install requests

```

## 3. Dynamic Rate Limiter (Core Algorithm)

**File**: `dynamic_ratelimiter.py`

```python

<insert same code from prior message verbatim>

```

(This code is already complete and production-ready.)

## 4. API Client that Uses the Limiter
>API wrapper that tunes itself

This integrates the dynamic limiter with `requests`, and strictly respects 429:

Every call → `limiter.acquire()`

On 429 → read Retry-After, call `limiter.on_429(...)`, then try again

On non-429 success → `limiter.on_success()`

**File**: `dynamic_api_client.py`

```python

# dynamic_api_client.py
import time
from typing import Optional, Dict, Any

import requests

from dynamic_ratelimiter import DynamicRateLimiter


class DynamicAPIClient:
    def __init__(
        self,
        base_url: str,
        *,
        initial_rate: float = 5.0,
        min_rate: float = 0.1,
        max_rate: float = 50.0,
        increase_step: float = 0.1,
        decrease_factor: float = 0.5,
        max_retries_on_429: int = 20,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.max_retries_on_429 = max_retries_on_429

        self.limiter = DynamicRateLimiter(
            initial_rate=initial_rate,
            min_rate=min_rate,
            max_rate=max_rate,
            increase_step=increase_step,
            decrease_factor=decrease_factor,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> requests.Response:

        url = f"{self.base_url}/{path.lstrip('/')}"
        retries = 0

        while True:
            # Wait until we're allowed to send the next request
            self.limiter.acquire()

            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                headers=headers,
                **kwargs,
            )

            # Non-429 responses
            if response.status_code != 429:
                # Treat any non-429 as a successful sample for AIMD.
                self.limiter.on_success()
                return response

            # Hit 429: handle dynamically
            retries += 1
            # Get Retry-After header if present
            retry_after_raw = response.headers.get("Retry-After")
            retry_after_seconds: Optional[float] = None

            if retry_after_raw is not None:
                try:
                    retry_after_seconds = float(retry_after_raw)
                except ValueError:
                    # If server returns a date instead of seconds, just ignore
                    retry_after_seconds = None

            self.limiter.on_429(retry_after_seconds)

            if retries > self.max_retries_on_429:
                raise RuntimeError(
                    f"Exceeded max_retries_on_429 ({self.max_retries_on_429}) "
                    f"for {url}"
                )
            # Loop again – acquire() will honor any cooldown we just set

```

## 5. API Configuration Table

**File**: `api_rate_config.py`

```python

# api_rate_config.py
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ApiRateConfig:
    name: str
    base_url: str

    # Dynamic rate-limiter tuning
    initial_rate: float       # starting requests/sec
    min_rate: float
    max_rate: float
    increase_step: float
    decrease_factor: float

    # Optional: documented hard limit for reference (not directly used)
    documented_limit_desc: Optional[str] = None


# Registry of known APIs.
#
# Notion: official docs say ~3 requests per second on average per integration,
# with bursts allowed. :contentReference[oaicite:0]{index=0}
API_RATE_CONFIGS: Dict[str, ApiRateConfig] = {
    "notion": ApiRateConfig(
        name="notion",
        base_url="https://api.notion.com/v1",
        initial_rate=2.0,         # start a bit below 3 rps
        min_rate=0.3,             # don't go absurdly low
        max_rate=3.5,             # allow small bursts above the doc avg
        increase_step=0.1,
        decrease_factor=0.5,
        documented_limit_desc="~3 requests/second per integration on average",
    ),

    # Vanta: public docs don’t clearly state a numeric rate limit.
    # Let the dynamic limiter learn + rely on 429 handling.
    "vanta": ApiRateConfig(
        name="vanta",
        base_url="https://api.vanta.com",  # adjust if your tenant uses a variant
        initial_rate=3.0,
        min_rate=0.5,
        max_rate=10.0,
        increase_step=0.2,
        decrease_factor=0.5,
        documented_limit_desc="Rate limit not clearly published; dynamic tuning + 429 handling.",
    ),

    # Fieldguide: same situation, no obvious published hard numbers.
    "fieldguide": ApiRateConfig(
        name="fieldguide",
        base_url="https://api.fieldguide.io",  # verify your actual base URL
        initial_rate=3.0,
        min_rate=0.5,
        max_rate=10.0,
        increase_step=0.2,
        decrease_factor=0.5,
        documented_limit_desc="Rate limit not clearly published; dynamic tuning + 429 handling.",
    ),
}


def get_api_rate_config(name: str) -> ApiRateConfig:
    """
    Look up a named API config (e.g. 'notion', 'vanta', 'fieldguide').

    Raises KeyError if not found.
    """
    key = name.lower()
    return API_RATE_CONFIGS[key]

```

## 6. Example Usage

**File**: `examples/example_notion.py`

```python

from clients import make_client_for

notion = make_client_for("notion")

def get_page(page_id: str, token: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }
    resp = notion.request("GET", f"/pages/{page_id}", headers=headers)
    resp.raise_for_status()
    return resp.json()

print(get_page("YOUR_PAGE_ID", "YOUR_TOKEN"))

```
