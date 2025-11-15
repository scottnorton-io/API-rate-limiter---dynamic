"""Example: Using the dynamic rate limiter with the Airtable API.

This example assumes:

- You have an Airtable base with ID in AIRTABLE_BASE_ID
- You have a table name in AIRTABLE_TABLE_NAME
- You have an API key or personal access token in AIRTABLE_TOKEN

NOTE: This is a basic example and does not cover pagination or schema-specific logic.
"""

import os

from api_ratelimiter import make_client_for


def main() -> None:
    client = make_client_for("airtable")

    base_id = os.environ.get("AIRTABLE_BASE_ID")
    table_name = os.environ.get("AIRTABLE_TABLE_NAME")
    token = os.environ.get("AIRTABLE_TOKEN")

    if not base_id or not table_name or not token:
        raise SystemExit(
            "Please set AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, and AIRTABLE_TOKEN to use this example."
        )

    headers = {
        "Authorization": f"Bearer {token}",
    }

    # Simple list-records example
    path = f"/{base_id}/{table_name}"
    resp = client.request("GET", path, headers=headers)
    resp.raise_for_status()

    data = resp.json()
    print("Records:")
    for record in data.get("records", []):
        print(record.get("id"), record.get("fields"))


if __name__ == "__main__":
    main()
