# Usage Guide

This is a condensed version of the full `USAGE.md` in the repository and focuses
on the most common patterns.

For deeper, end-to-end examples, see the `USAGE.md` file in the project root.

---

## Basic Pattern

```python
from api_ratelimiter import make_client_for

client = make_client_for("notion")
response = client.request("GET", "/pages/...")
```

The client will:

- Call `limiter.acquire()` before each outbound request.
- Call `limiter.on_success()` on non-backoff responses.
- Call `limiter.on_429()` on configured backoff statuses (e.g. 429).

---

## Using Notion, Vanta, and Fieldguide

### Notion

```python
import os
from api_ratelimiter import make_client_for

notion = make_client_for("notion")

headers = {
    "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
    "Notion-Version": "2022-06-28",
}

resp = notion.request("GET", f"/pages/{os.environ['NOTION_PAGE_ID']}", headers=headers)
resp.raise_for_status()
print(resp.json())
```

### Vanta (placeholder example)

```python
import os
from api_ratelimiter import make_client_for

vanta = make_client_for("vanta")

resp = vanta.request(
    "GET",
    "/some-endpoint",
    headers={"Authorization": f"Bearer {os.environ['VANTA_TOKEN']}"},
)
resp.raise_for_status()
print(resp.json())
```

### Fieldguide (placeholder example)

```python
import os
from api_ratelimiter import make_client_for

fg = make_client_for("fieldguide")

resp = fg.request(
    "GET",
    "/some-endpoint",
    headers={"Authorization": f"Bearer {os.environ['FIELDGUIDE_TOKEN']}"},
)
resp.raise_for_status()
print(resp.json())
```

---

## Pagination Loop Example

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

    cursor = data.get("next_cursor")
```

The limiter ensures this pagination loop does not overwhelm the API.

---

## Backing Off on Multiple Status Codes

You can configure additional status codes (like 503) as backoff triggers:

```python
client = make_client_for(
    "notion",
    backoff_status_codes=(429, 503),
)
```

Any response with status code in that set will:

- Trigger `on_429()` with optional `Retry-After`.
- Decrease the rate and set cooldown as needed.
