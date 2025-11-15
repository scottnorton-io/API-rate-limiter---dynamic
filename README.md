🚀 README.md (complete)


# API Rate Limiter – Dynamic, Self-Tuning, 429-Aware Python Client  
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
- Backoffs safely on 429s  
- Learns the real allowable throughput of the API  

This is ideal for compliance automation, ETL, scripting, and backend services.

---

## 🔥 Features

### ✔️ Dynamic Rate Learning
The limiter uses **AIMD (Additive Increase / Multiplicative Decrease)**:

- Slowly increases speed on success  
- Quickly decreases speed on 429  
- Auto-pauses when API demands  
- Stabilizes at the optimal rate  

### ✔️ API Configuration Registry
Centralized config table for:

- Notion  
- Vanta  
- Fieldguide  
- Any API you add  

### ✔️ One-Line API Client Creation
```python

notion = make_client_for("notion")
vanta = make_client_for("vanta")
fg = make_client_for("fieldguide")

```

### ✔️ Fully Modular
- Swap rate config without touching code
- Add new APIs in seconds
- No duplication between scripts

### 📦 Installation
```bash

pip install requests

```

Clone the repo:
```bash

git clone https://github.com/scottnorton-io/api-limiter.git
cd api-limiter

```

### 📘 Quick Start Example (Notion)
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

### 📚 Architecture
```text

api-limiter/
    dynamic_ratelimiter.py   -> adaptive token bucket
    dynamic_api_client.py    -> request/response logic
    api_rate_config.py       -> centralized API config table
    clients.py               -> client factory
    examples/
        example_notion.py
        example_vanta.py
        example_fieldguide.py

```

### 🛠 Adding a New API

1. Edit `api_rate_config.py`
2. Add:
```python

API_RATE_CONFIGS["new_api"] = ApiRateConfig(
    name="new_api",
    base_url="https://api.example.com/v1",
    initial_rate=2.0,
    min_rate=0.3,
    max_rate=5.0,
    increase_step=0.1,
    decrease_factor=0.5,
    documented_limit_desc="Vendor says 5req/sec burst allowed",
)

```
3. Use:
```python

client = make_client_for("new_api")

```

Done.

### 📄 License
MIT License © Scott Norton

### 💬 Questions or contributions?
Open an issue or PR. Contributions welcome!
