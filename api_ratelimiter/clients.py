from typing import Optional, Dict, Any, Iterable, Tuple

import requests

from .dynamic_ratelimiter import DynamicRateLimiter
from .api_rate_config import get_api_rate_config, ApiRateConfig


class DynamicAPIClient:
    """
    HTTP client that uses DynamicRateLimiter and backs off on selected status codes.

    Behaviour:

    - Calls limiter.acquire() before each outbound request.
    - On non-backoff status codes:
        - Calls limiter.on_success() and returns the response.
    - On backoff status codes (default: 429, 502, 503):
        - Reads `Retry-After` header if present (seconds).
        - Calls limiter.on_429(retry_after_seconds).
        - Retries up to `max_retries_on_429` times.
    """

    def __init__(
        self,
        base_url: str,
        *,
        limiter: DynamicRateLimiter,
        max_retries_on_429: int = 20,
        backoff_status_codes: Optional[Iterable[int]] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.max_retries_on_429 = max_retries_on_429
        self.limiter = limiter

        if backoff_status_codes is None:
            # 429 Too Many Requests, plus 502 / 503 for overload / transient failures.
            backoff_status_codes = (429, 502, 503)
        self.backoff_status_codes: Tuple[int, ...] = tuple(backoff_status_codes)

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
        Perform a single HTTP request with dynamic, backoff-aware rate limiting.
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

            status = response.status_code

            # Normal (non-backoff) path: treat as a successful sample.
            if status not in self.backoff_status_codes:
                self.limiter.on_success()
                return response

            # Backoff path for overloaded / rate-limited responses.
            retries += 1
            retry_after_raw = response.headers.get("Retry-After")
            retry_after_seconds: Optional[float] = None

            if retry_after_raw is not None:
                try:
                    retry_after_seconds = float(retry_after_raw)
                except ValueError:
                    # If 'Retry-After' is a date or malformed, ignore and use fallback.
                    retry_after_seconds = None

            # We reuse on_429 as the generic backoff hook.
            self.limiter.on_429(retry_after_seconds)

            if retries > self.max_retries_on_429:
                raise RuntimeError(
                    f"Exceeded max_retries_on_429 ({self.max_retries_on_429}) for {url} "
                    f"after backoff status {status}."
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
    max_retries_on_429: int = 20,
    backoff_status_codes: Optional[Iterable[int]] = None,
) -> DynamicAPIClient:
    """
    Factory: build a DynamicAPIClient using the named API's rate config.

    Example:
        notion = make_client_for("notion")
        resp = notion.request("GET", "/pages/..."
    """
    cfg = get_api_rate_config(api_name)
    limiter = _build_limiter_from_config(cfg)

    return DynamicAPIClient(
        base_url=cfg.base_url,
        limiter=limiter,
        max_retries_on_429=max_retries_on_429,
        backoff_status_codes=backoff_status_codes,
        session=session,
    )
