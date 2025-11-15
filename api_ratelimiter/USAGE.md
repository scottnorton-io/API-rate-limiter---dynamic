# USAGE.md — Dynamic API Rate Limiter

This guide provides **practical, real-world usage examples** for the
`dynamic-api-rate-limiter` package. It is designed as a companion to the
README, giving you concrete, copy‑paste‑ready patterns for:

- Making API requests with automatic rate limiting  
- Using Notion, Vanta, and Fieldguide with prebuilt configs  
- Logging and metrics patterns  
- Backoff handling  
- Building ETL‑style workflows  
- Creating your own API configuration  
- Advanced flows (batching, sync loops, retries, pagination)

---

# 1. Importing and Creating a Client

```python
from api_ratelimiter import make_client_for

client = make_client_for("notion")
```

You now have:

- A `DynamicAPIClient`
- A `DynamicRateLimiter` internally attached to it

Make requests using:

```python
response = client.request("GET", "/pages/...")
```

The limiter automatically:

- Sleeps when necessary  
- Adjusts its rate  
- Backs off on 429  
- Honors Retry‑After  
- Learns the optimal request speed  

---

# 2. Example: Basic Notion Request

```python
import os
from api_ratelimiter import make_client_for

client = make_client_for("notion")

def get_page(page_id):
    headers = {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Notion-Version": "2022-06-28",
    }
    resp = client.request("GET", f"/pages/{page_id}", headers=headers)
    resp.raise_for_status()
    return resp.json()

print(get_page(os.environ["NOTION_PAGE_ID"]))
```

**No rate tuning required** — the dynamic limiter handles it.

---

# 3. Example: Vanta API Request

```python
import os
from api_ratelimiter import make_client_for

vanta = make_client_for("vanta")

token = os.environ["VANTA_API_TOKEN"]

resp = vanta.request(
    "GET",
    "/entities",
    headers={"Authorization": f"Bearer {token}"}
)
print(resp.json())
```

Your library does:

- Request pacing  
- Dynamic increase / decrease  
- 429 retry logic  
- Cooldowns  

---

# 4. Example: Fieldguide API Request

```python
import os
from api_ratelimiter import make_client_for

fg = make_client_for("fieldguide")

resp = fg.request(
    "GET",
    "/v1/workflows",
    headers={"Authorization": f"Bearer {os.environ['FIELDGUIDE_TOKEN']}"},
)
print(resp.json())
```

---

# 5. Logging + Snapshots (Metrics)

Enable logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

Snapshot example:

```python
snap = client.limiter.snapshot()
print(snap)
```

Output:

```python
{
  "current_rate": 2.4,
  "tokens": 1.1,
  "cooldown_until": 1708012345.12
}
```

This is perfect for:

- Prometheus exporters  
- Datadog logs → metrics  
- CloudWatch embedded metrics  
- Grafana Loki → metrics extraction  

---

# 6. Backoff on Multiple Status Codes (429, 503, 408, etc.)

```python
client = make_client_for(
    "notion",
    backoff_status_codes=(429, 503, 408)
)
```

Now *all* of these trigger:

- Multiplicative decrease  
- Optional Retry‑After compliance  
- Cooldown intervals  

---

# 7. Example: ETL Loop That Avoids Rate Limits

```python
import time
from api_ratelimiter import make_client_for

client = make_client_for("notion")
limiter = client.limiter

def process_page(page_id):
    resp = client.request("GET", f"/pages/{page_id}")
    resp.raise_for_status()
    return resp.json()

while True:
    for pid in list_of_ids:
        data = process_page(pid)
        store_locally(data)

    print("Snapshot:", limiter.snapshot())
    time.sleep(5)
```

This loop **never melts the API**, no matter the list size.

---

# 8. Example: Pagination (Auto‑Safe)

```python
results = []

cursor = None
while True:
    params = {"start_cursor": cursor} if cursor else {}
    resp = client.request("GET", "/databases/xxx/query", params=params)
    data = resp.json()

    results.extend(data["results"])
    if not data.get("has_more"):
        break

    cursor = data["next_cursor"]
```

The rate limiter prevents pagination loops from over‑running an API.

---

# 9. Creating a Custom API Configuration

Add a custom API in your own code:

```python
from api_ratelimiter import ApiRateConfig, API_RATE_CONFIGS

API_RATE_CONFIGS["my_internal_api"] = ApiRateConfig(
    name="my_internal_api",
    base_url="https://internal.api.company/v2",
    initial_rate=3.0,
    min_rate=1.0,
    max_rate=10.0,
    increase_step=0.2,
    decrease_factor=0.6,
    documented_limit_desc="Internal SRE says soft limit ~8 rps.",
)
```

Then:

```python
client = make_client_for("my_internal_api")
```

---

# 10. Retrying Non‑429 Failures (Application Logic)

The library retries **only** backoff‑related failures.

If you want business‑logic retries:

```python
import requests
from api_ratelimiter import make_client_for

client = make_client_for("notion")

for attempt in range(5):
    try:
        resp = client.request("GET", "/pages/xxx")
        resp.raise_for_status()
        break
    except requests.RequestException:
        if attempt == 4:
            raise
        time.sleep(1)
```

---

# 11. Batch Processing Pattern (Ideal for Compliance Automation)

```python
def fetch_items(ids):
    for item_id in ids:
        resp = client.request("GET", f"/items/{item_id}")
        yield resp.json()
```

This pattern:

- Uses the limiter automatically  
- Avoids sudden traffic bursts  
- Scales linearly  

---

# 12. Long‑Running Worker Pattern

```python
while True:
    job = queue.get()
    resp = client.request("POST", "/process", json=job)
    persist(resp.json())
```

The worker **self-throttles** based on API feedback.

---

# 13. Integrating Into asyncio? (Reference)

Right now the library is synchronous.

BUT you can safely run it inside an executor:

```python
import asyncio
from functools import partial

loop = asyncio.get_event_loop()
client = make_client_for("notion")

async def async_get(path):
    return await loop.run_in_executor(
        None, partial(client.request, "GET", path)
    )
```

A fully async version can be added later if needed.

---

# 14. Safely Using With Multi‑Threading

Each thread needs its own client instance:

```python
def worker():
    client = make_client_for("notion")
    ...

for _ in range(5):
    Thread(target=worker).start()
```

Shared clients across threads **will** work but are less predictable.

---

# 15. How the Dynamic Limiter Learns

| Event | Effect on Rate |
|-------|----------------|
| Successful request | +increase_step |
| Backoff (429/503/etc.) | × decrease_factor |
| Retry‑After present | cooldown_until updated |
| Tokens depleted | sleeps automatically |

You don’t have to tune anything unless you want to.

---

# 16. Tuning Guidance

If you *must* tune:

- Increase `max_rate` if you have a lot of work and the API can take more.
- Lower `min_rate` if the API is fragile or slow.
- Increase `increase_step` for faster ramp‑up.
- Decrease `decrease_factor` (e.g., 0.4 → 0.2) for more aggressive backoff.

---

# 17. Adding Support for a New API in the Repo

Edit:

```
api_ratelimiter/api_rate_config.py
```

Add:

```python
API_RATE_CONFIGS["xyz"] = ApiRateConfig(...)
```

---

# 18. End-to-End Pattern (Full Workflow Example)

```python
from api_ratelimiter import make_client_for

client = make_client_for("notion")

def sync_database(db_id):
    cursor = None
    all_items = []

    while True:
        payload = {"start_cursor": cursor} if cursor else {}
        resp = client.request("POST", f"/databases/{db_id}/query", json=payload)
        data = resp.json()

        all_items.extend(data["results"])

        if not data.get("has_more"):
            break

        cursor = data["next_cursor"]

    return all_items
```

This is a **production‑safe** sync loop.

---

# 19. Philosophy of the Dynamic Limiter

- APIs change limits without warning  
- Documentation is vague or misleading  
- A static rate limit → brittle  
- A dynamic limiter → **self‑healing**

The goal is to **never break**, no matter:

- Bursts  
- Retrying  
- Changes in API vendor limits  

---

# 20. Roadmap (Optional Enhancements)

- async version using `anyio` / `httpx`  
- distributed / multi‑worker token pools  
- Prometheus exporter  
- CLI utility  
- Local caching layer  
- Debug dashboard  

---

# Final Notes

This `USAGE.md` is meant to be a **comprehensive operational guide**. It should live at the root of your repo next to:

- `README.md`
- `background.md`
- `METRICS.md`

And will continue to grow as we add features.

