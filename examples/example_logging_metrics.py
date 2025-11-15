"""Example showing logging and metrics with dynamic-api-rate-limiter.

This example demonstrates:

- Enabling logging for the rate limiter.
- Accessing the underlying DynamicRateLimiter from a DynamicAPIClient.
- Periodically logging a snapshot for metrics/observability.

NOTE: This script uses a generic "example" API endpoint; replace with
real API details for your environment.
"""

import logging
import os
import time

from api_ratelimiter.clients import make_client_for


def configure_logging() -> None:
    """Configure basic logging for demonstration purposes."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    configure_logging()

    # For this example, we'll pretend we have a generic API config named "notion"
    # configured in ApiRateConfig. Replace "notion" with another API name
    # if you prefer.
    client = make_client_for("notion")

    # The client exposes its limiter instance for observability.
    limiter = client.limiter

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

    for i in range(5):
        # Perform a rate-limited request
        resp = client.request("GET", f"/pages/{page_id}", headers=headers)
        resp.raise_for_status()

        # Log a snapshot for metrics
        snap = limiter.snapshot()
        logging.getLogger("rate_limiter_metrics").info(
            "limiter_snapshot",
            extra={
                "current_rate": snap["current_rate"],
                "tokens": snap["tokens"],
                "cooldown_until": snap["cooldown_until"],
            },
        )

        print(f"Iteration {i+1}: status={resp.status_code}, current_rate={snap['current_rate']}")

        # Just to slow down the demo loop a bit; in real code you may not sleep here.
        time.sleep(1)


if __name__ == "__main__":
    main()
