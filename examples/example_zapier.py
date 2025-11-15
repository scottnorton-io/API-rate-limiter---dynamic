"""Example: Calling a Zapier catch hook with the dynamic rate limiter.

This pattern is useful when you have a Zapier Catch Hook URL that you want
to call from a script or backend service, but still want to avoid hammering
Zapier under heavy load.

Requirements:

- Set ZAPIER_HOOK_PATH to the path portion of your Zapier hook URL, e.g.
  if your URL is https://hooks.zapier.com/hooks/catch/123456/abcdef/ then
  ZAPIER_HOOK_PATH should be "hooks/catch/123456/abcdef/".
"""

import os

from api_ratelimiter import make_client_for


def main() -> None:
    client = make_client_for("zapier")

    hook_path = os.environ.get("ZAPIER_HOOK_PATH")
    if not hook_path:
        raise SystemExit(
            "Please set ZAPIER_HOOK_PATH to the path portion of your Zapier hook URL."
        )

    # Simple JSON payload to trigger the Zap
    payload = {"message": "Hello from dynamic-api-rate-limiter!"}

    resp = client.request("POST", f"/{hook_path.lstrip('/')}", json=payload)
    resp.raise_for_status()

    print("Zapier hook triggered successfully:", resp.status_code)


if __name__ == "__main__":
    main()
