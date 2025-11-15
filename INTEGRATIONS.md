# Built-in Integrations

The library ships with conservative, documented defaults for a small set of common SaaS APIs.
These are defined in `api_ratelimiter.api_rate_config.API_RATE_CONFIGS` and can be inspected
or overridden at runtime.

> ⚠️ **Important**
>
> These defaults are intentionally conservative and may *not* match the absolute maximum
> throughput that the provider allows. Always verify against the vendor’s documentation and
> tune via overrides if you have strong requirements.

## Summary table

| Integration  | Description                             | Base URL                               | Example script                  | Notes                                                |
|--------------|-----------------------------------------|----------------------------------------|---------------------------------|------------------------------------------------------|
| `notion`     | Notion public API                       | `https://api.notion.com`               | `examples/example_notion.py`    | Tuned for typical workspace‑level integrations.      |
| `vanta`      | Vanta API                               | `https://api.vanta.com`                | `examples/example_vanta.py`     | **Sample** – requires endpoint & auth customization. |
| `fieldguide` | Fieldguide API                          | `https://api.fieldguide.io`            | `examples/example_fieldguide.py`| **Sample** – requires endpoint & auth customization. |
| `airtable`   | Airtable REST API                       | `https://api.airtable.com`             | `examples/example_airtable.py`  | General REST patterns with backoff behaviour.        |
| `zapier`     | Zapier Platform / REST hooks            | `https://nla.zapier.com` (or similar)  | `examples/example_zapier.py`    | Generic patterns for webhook / action usage.         |
| `slack`      | Slack Web / SCIM API                    | `https://slack.com/api`                | `examples/example_slack.py`     | Consider app‑level tokens and scopes.                |
| `github`     | GitHub REST API                         | `https://api.github.com`               | `examples/example_github.py`    | Works for GitHub.com and GHES with tuned base URL.   |
| `openai`     | OpenAI REST API                         | `https://api.openai.com`               | `examples/example_openai.py`    | Adjust for your expected tokens / rpm usage.         |

For some providers (notably Vanta and Fieldguide), we include **sample** examples that show
how to wire up the client and limiter, but we do **not** publish full, official integrations.
You must configure the exact endpoints, auth headers, and rate expectations for your specific
account and data volumes.

## Inspecting and overriding configs

```python
from api_ratelimiter.api_rate_config import get_api_rate_config
from api_ratelimiter.config_overrides import (
    load_api_rate_overrides_json,
    merged_api_rate_configs,
    list_available_integrations,
)

# Get the default config for a single integration.
notion_cfg = get_api_rate_config("notion")
print(notion_cfg)

# Load and merge JSON overrides.
overrides = load_api_rate_overrides_json("overrides.json")
all_configs = merged_api_rate_configs(overrides)

print("Available integrations:", list_available_integrations(all_configs))
```

See `docs/configuration.md` for a more detailed discussion of how the config objects are
structured and how to override them safely in production.
