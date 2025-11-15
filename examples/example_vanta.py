"""
Minimal Vanta usage example.

Set VANTA_TOKEN before running this script.

The endpoint used here is illustrative; adjust path/fields to match your tenant and API version.
"""

import os

from api_ratelimiter.clients import make_client_for


def list_assets(token: str):
    vanta = make_client_for("vanta")

    headers = {
        "Authorization": f"Bearer {token}",
    }

    resp = vanta.request("GET", "/v1/assets", headers=headers)
    resp.raise_for_status()
    return resp.json()


def main():
    token = os.environ.get("VANTA_TOKEN", "").strip()
    if not token:
        raise SystemExit("Please set VANTA_TOKEN environment variable.")

    data = list_assets(token)
    print("Assets response keys:", list(data.keys()))


if __name__ == "__main__":
    main()
