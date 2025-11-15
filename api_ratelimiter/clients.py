from typing import Optional, Dict, Any

import requests

from .dynamic_ratelimiter import DynamicRateLimiter
from .api_rate_config import get_api_rate_config, ApiRateConfig


class DynamicAPIClient:
    """
    Simple HTTP client that uses DynamicRateLimiter and respects 429 responses.

    - Call .request(method, path, ...) to perform a rate-limited request.
    - The client:
        - Calls limiter.acquire() before each outbound request
        - Calls limiter.on_success() on non-429 responses
        - Calls limiter.on_429(retry_after) on HTTP 429
    """

    def __init__(
        self,
        base_url: str,
        *,
        limiter: DynamicRateLimiter,
        max_retries_on_429: int = 20,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.max_retries_on_429 = max_retries_on_429
        self.limiter = limiter

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Perform a single HTTP request with dynamic, 429-aware rate limiting.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        retries = 0

        while True:
            # Wait until we're allowed to send the next request
            self.limiter.acquire()

            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                headers=headers,
                **kwargs,
            )

            # Non-429 responses are treated as successful samples
            if response.status_code != 429:
                self.limiter.on_success()
                return response

            # Handle HTTP 429 Too Many Requests
            retries += 1
            retry_after_raw = response.headers.get("Retry-After")
            retry_after_seconds: Optional[float] = None

            if retry_after_raw is not None:
                try:
                    retry_after_seconds = float(retry_after_raw)
                except ValueError:
                    # If 'Retry-After' is a date, ignore and use fallback
                    retry_after_seconds = None

            self.limiter.on_429(retry_after_seconds)

            if retries > self.max_retries_on_429:
                raise RuntimeError(
                    f"Exceeded max_retries_on_429 ({self.max_retries_on_429}) for {url}"
                )


def _build_limiter_from_config(cfg: ApiRateConfig) -> DynamicRateLimiter:
    """
    Internal helper: build a DynamicRateLimiter from an ApiRateConfig.
    """
    return DynamicRateLimiter(
        initial_rate=cfg.initial_rate,
        min_rate=cfg.min_rate,
        max_rate=cfg.max_rate,
        increase_step=cfg.increase_step,
        decrease_factor=cfg.decrease_factor,
    )


def make_client_for(
    api_name: str,
    *,
    session: Optional[requests.Session] = None,
    max_retries_on_429: int = 20,
) -> DynamicAPIClient:
    """
    Factory: build a DynamicAPIClient using the named API's rate config.

    Example:
        notion = make_client_for("notion")
        resp = notion.request("GET", "/pages/...")
    """
    cfg = get_api_rate_config(api_name)
    limiter = _build_limiter_from_config(cfg)

    return DynamicAPIClient(
        base_url=cfg.base_url,
        limiter=limiter,
        max_retries_on_429=max_retries_on_429,
        session=session,
    )
