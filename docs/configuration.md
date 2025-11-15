# Configuration & Overrides

By default, `dynamic-api-rate-limiter` ships with a curated set of
integrations in :data:`API_RATE_CONFIGS` (Notion, Vanta, Fieldguide,
Airtable, Zapier, Slack, GitHub, OpenAI, etc.).

In real deployments you may want to:

- Add your own internal services.
- Override limits for specific APIs based on your workload.
- Keep those settings in configuration instead of hard-coding them.

This page shows how to do that.

---

## 1. Listing available integrations

At runtime you can introspect which integrations are built in:

```python
from api_ratelimiter import list_available_integrations

print(list_available_integrations())
# {'notion': 'https://api.notion.com/v1', 'github': 'https://api.github.com', ...}
```

This is useful for CLIs or admin UIs.

---

## 2. Loading overrides from JSON

You can define additional (or overriding) configurations in a JSON file,
for example `rate_overrides.json`:

```json
{
  "my-internal-api": {
    "base_url": "https://internal.example.com/api",
    "initial_rate": 5.0,
    "min_rate": 1.0,
    "max_rate": 20.0,
    "increase_step": 0.5,
    "decrease_factor": 0.5,
    "documented_limit_desc": "Internal service tuned for higher throughput."
  }
}
```

Then load and merge them:

```python
from api_ratelimiter import (
    load_api_rate_overrides_json,
    merged_api_rate_configs,
    make_client_from_config,
)

overrides = load_api_rate_overrides_json("rate_overrides.json")
all_configs = merged_api_rate_configs(overrides)

cfg = all_configs["my-internal-api"]
client = make_client_from_config(cfg)
```

You now have a fully dynamic client using the same AIMD algorithm and
backoff behavior as the built-in integrations.

---

## 3. Using environment variables + JSON

A common pattern is to:

- Store API URLs and numeric limits in a JSON file.
- Keep secrets (tokens) in Keychain or environment variables.
- Use the JSON purely for rate limiting and base URLs.

For example, with a Docker/Kubernetes deployment, you might:

- Bake `rate_overrides.json` into the image.
- Pass secrets via env vars (or a secret manager).
- Construct clients using `make_client_from_config` and your merged mapping.

---

## 4. When to use overrides vs. code changes

Use **overrides** when:

- Tuning limits per environment (dev vs. prod).
- Adjusting behavior without deploying new code.

Use **code changes** when:

- Adding widely useful integrations you plan to share.
- Changing the default behavior of the library itself.
