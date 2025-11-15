# Integration Registry

This project includes a growing set of **named integrations** that share:

- A base URL
- A conservative rate configuration
- Example usage scripts
- Typical environment variables

The goal is to make it easy to drop this library into automation and
compliance workflows without rethinking rate limiting for each API.

## Summary Table

| Integration | Key name    | Base URL                        | Typical Use                                           | Env Vars (examples)                                                                 | Example script                          |
|------------|-------------|----------------------------------|-------------------------------------------------------|-------------------------------------------------------------------------------------|----------------------------------------|
| Notion     | `notion`    | `https://api.notion.com/v1`      | Docs, workspaces, evidence notes                      | `NOTION_TOKEN`, `NOTION_PAGE_ID`, `NOTION_DATABASE_ID`                              | `examples/example_notion.py`           |
| Vanta      | `vanta`     | `https://api.vanta.com`          | Compliance automation / evidence                      | `VANTA_API_TOKEN`                                                                   | `examples/example_vanta.py` (future)   |
| Fieldguide | `fieldguide`| `https://api.fieldguide.io`      | Audit & engagement workflows                          | `FIELDGUIDE_TOKEN`                                                                  | `examples/example_fieldguide.py` (future) |
| Airtable   | `airtable`  | `https://api.airtable.com/v0`    | Light-weight data store, checklists, trackers         | `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME`, `AIRTABLE_TOKEN`                         | `examples/example_airtable.py`         |
| Zapier     | `zapier`    | `https://hooks.zapier.com`       | Event fan-out, glue between SaaS tools                | `ZAPIER_HOOK_PATH`                                                                  | `examples/example_zapier.py`           |
| Slack      | `slack`     | `https://slack.com/api`          | Notifications, chat-based automation                  | `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`                                               | `examples/example_slack.py`            |
| GitHub     | `github`    | `https://api.github.com`         | Repo metadata, evidence collection, code queries      | `GITHUB_TOKEN`, `GITHUB_ORG`                                                        | `examples/example_github.py`           |
| OpenAI     | `openai`    | `https://api.openai.com/v1`      | AI-assisted summarization, drafting, analysis         | `OPENAI_API_KEY`, `OPENAI_MODEL`                                                    | `examples/example_openai.py`           |

## Adding New Integrations

1. Add a new `ApiRateConfig` entry to `api_ratelimiter/api_rate_config.py`.
2. Optionally add an example under `examples/`.
3. Update this registry and the docs (`docs/integrations.md`) accordingly.

This keeps the library's ecosystem discoverable and predictable.
