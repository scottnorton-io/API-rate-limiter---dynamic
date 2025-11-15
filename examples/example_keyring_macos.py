"""Example: Using macOS Keychain via keyring for API secrets.

This example shows a pattern for storing and retrieving API tokens using
the `keyring` library, which on macOS will use the native Keychain.

It falls back to environment variables if a secret is not found in keyring.

Supported in this example:

- NOTION_TOKEN
- OPENAI_API_KEY

Setup steps (macOS):

1. Install keyring:

   pip install keyring

   (Or, if using extras: pip install "dynamic-api-rate-limiter[security]")

2. Store a secret:

   python -m keyring set dynamic-api-rate-limiter NOTION_TOKEN

   (You will be prompted to enter the value.)

3. Run this script.
"""

import os
from typing import Optional

import keyring

from api_ratelimiter import make_client_for


SERVICE_NAME = "dynamic-api-rate-limiter"


def get_secret(name: str) -> Optional[str]:
    """Retrieve a secret from keyring, falling back to env vars.

    This pattern keeps secrets out of source code and (ideally) out of
    your shell history, while still allowing environment-variable-based
    override for CI or containers.
    """
    value = keyring.get_password(SERVICE_NAME, name)
    if value:
        return value
    return os.environ.get(name)


def main() -> None:
    notion = make_client_for("notion")
    openai_client = make_client_for("openai")

    notion_token = get_secret("NOTION_TOKEN")
    openai_key = get_secret("OPENAI_API_KEY")

    if not notion_token:
        raise SystemExit(
            "Missing NOTION_TOKEN in keyring or environment. "
            "Set via: python -m keyring set dynamic-api-rate-limiter NOTION_TOKEN"
        )

    if not openai_key:
        raise SystemExit(
            "Missing OPENAI_API_KEY in keyring or environment. "
            "Set via: python -m keyring set dynamic-api-rate-limiter OPENAI_API_KEY"
        )

    print("Successfully retrieved secrets from keyring/env.")
    # You would now use `notion` and `openai_client` with these tokens in headers.


if __name__ == "__main__":
    main()
