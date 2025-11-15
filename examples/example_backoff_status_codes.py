"""Example: Backoff on multiple status codes (429 + 503).

This example shows how to configure the client so that it treats both
HTTP 429 (Too Many Requests) and HTTP 503 (Service Unavailable) as
backoff signals.

Replace the base URL and path with a real API you want to test against.
"""

import os

from api_ratelimiter.clients import make_client_for


def main() -> None:
    # In this example we use the "notion" API config, but any configured API
    # name from ApiRateConfig can be used here.
    client = make_client_for(
        "notion",
        backoff_status_codes=(429, 503),
    )

    token = os.environ.get("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID")
    if not token or not page_id:
        raise SystemExit(
            "Please set NOTION_TOKEN and NOTION_PAGE_ID env vars to run this example."
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }

    resp = client.request("GET", f"/pages/{page_id}", headers=headers)
    resp.raise_for_status()

    print("Request succeeded with status:", resp.status_code)


if __name__ == "__main__":
    main()
