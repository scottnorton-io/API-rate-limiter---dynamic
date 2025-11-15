"""HTTP client utilities built on top of DynamicRateLimiter."""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Dict, Any

import requests

from .dynamic_ratelimiter import DynamicRateLimiter
from .api_rate_config import get_api_rate_config, ApiRateConfig


class DynamicAPIClient:
    """HTTP client that uses a :class:`DynamicRateLimiter` and respects backoff.

    It will:

    - Call limiter.acquire() before each outbound request.
    - Treat selected HTTP status codes as backoff signals (default: 429).
    - Use Retry-After for 429 when present.
    - Call limiter.on_success() on non-backoff responses.
    - Call limiter.on_429(retry_after) on backoff responses.
    """

    def __init__(
        self,
        base_url: str,
        *,
        limiter: DynamicRateLimiter,
        max_retries_on_backoff: int = 20,
        backoff_status_codes: Iterable[int] = (429,),
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.max_retries_on_backoff = max_retries_on_backoff

        # Normalize backoff status codes to a tuple for fast "in" checks
        self.backoff_status_codes: Sequence[int] = tuple(backoff_status_codes)
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
        """Perform a single HTTP request with dynamic, backoff-aware rate limiting."""
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

            # If not a backoff status, treat as success and return
            if response.status_code not in self.backoff_status_codes:
                self.limiter.on_success()
                return response

            # Backoff-handling path
            retries += 1

            retry_after_seconds: Optional[float] = None

            if response.status_code == 429:
                retry_after_raw = response.headers.get("Retry-After")
                if retry_after_raw is not None:
                    try:
                        retry_after_seconds = float(retry_after_raw)
                    except ValueError:
                        retry_after_seconds = None

            # Use the limiter's backoff handler (named on_429 for historical reasons)
            self.limiter.on_429(retry_after_seconds)

            if retries > self.max_retries_on_backoff:
                raise RuntimeError(
                    f"Exceeded max_retries_on_backoff ({self.max_retries_on_backoff}) for {url}"
                )


def _build_limiter_from_config(cfg: ApiRateConfig) -> DynamicRateLimiter:
    """Internal helper: build a DynamicRateLimiter from an ApiRateConfig."""
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
    max_retries_on_backoff: int = 20,
    backoff_status_codes: Iterable[int] = (429,),
) -> DynamicAPIClient:
    """Factory: build a :class:`DynamicAPIClient` using the named API's rate config."""
    cfg = get_api_rate_config(api_name)
    limiter = _build_limiter_from_config(cfg)

    return DynamicAPIClient(
        base_url=cfg.base_url,
        limiter=limiter,
        max_retries_on_backoff=max_retries_on_backoff,
        backoff_status_codes=backoff_status_codes,
        session=session,
    )
