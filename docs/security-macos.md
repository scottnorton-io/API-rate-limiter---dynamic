# Secure Deployment on macOS

This project is designed to work well in **macOS environments** where you
want to keep API secrets out of source code and, where possible, out of
environment variables as well.

The recommended pattern is:

- Use the `keyring` library to talk to macOS Keychain.
- Use a consistent `SERVICE_NAME` (e.g. `dynamic-api-rate-limiter`).
- Store per-secret entries (e.g. `NOTION_TOKEN`, `OPENAI_API_KEY`).
- Fall back to environment variables for CI or non-interactive contexts.

---

## 1. Install security extras

From your project environment:

```bash
pip install "dynamic-api-rate-limiter[security]"
```

or, if working in this repo:

```bash
pip install -e ".[dev]"
```

This installs `keyring`, which uses macOS Keychain by default.

---

## 2. Storing secrets in Keychain

Use `keyring`'s CLI to set values:

```bash
python -m keyring set dynamic-api-rate-limiter NOTION_TOKEN
python -m keyring set dynamic-api-rate-limiter OPENAI_API_KEY
```

You will be prompted to enter the secret values, which will be stored in
macOS Keychain under the service name `dynamic-api-rate-limiter`.

---

## 3. Retrieving secrets in code

A recommended helper pattern:

```python
import os
import keyring

SERVICE_NAME = "dynamic-api-rate-limiter"

def get_secret(name: str) -> str | None:
    value = keyring.get_password(SERVICE_NAME, name)
    if value:
        return value
    return os.environ.get(name)
```

Then use it in your scripts:

```python
from api_ratelimiter import make_client_for

notion = make_client_for("notion")
token = get_secret("NOTION_TOKEN")
```

This lets you:

- Use Keychain in local/dev environments.
- Use environment variables in CI or containers.
- Avoid hard-coding secrets or committing them by accident.

---

## 4. Good Practices

- **Never** commit secrets to Git.
- Prefer **per-user** secrets in Keychain for local work.
- For CI, use the CI system's **secret management** instead of Keychain.
- Consider creating a separate user/project in each SaaS (Notion, Vanta,
  Fieldguide, etc.) for automation, with restricted permissions.
- Rotate keys periodically and when changing roles or tooling.

---

## 5. Example Script

See:

- `examples/example_keyring_macos.py`

for a concrete example that combines Keychain-backed secrets and the
dynamic rate limiter for Notion and OpenAI.
