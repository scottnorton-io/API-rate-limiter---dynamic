"""Dynamic, AIMD-style API rate limiter.

This module provides :class:`DynamicRateLimiter`, an adaptive token-bucket
rate limiter that:

- Tracks a dynamic "current_rate" (requests per second).
- Uses Additive Increase / Multiplicative Decrease (AIMD) to tune the rate.
- Supports cooldown windows (e.g. Retry-After from upstream APIs).
- Exposes a lightweight snapshot() method for observability.

The limiter is thread-safe and designed for a single-process environment.
For multi-process or multi-node deployments, consider a distributed
token bucket implementation as a future enhancement.
"""

from __future__ import annotations

import logging
import time
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DynamicRateLimiter:
    """Adaptive token-bucket rate limiter with AIMD-style tuning.

    Parameters
    ----------
    initial_rate:
        Starting rate in requests per second.
    min_rate:
        Lower bound for the dynamic rate.
    max_rate:
        Upper bound for the dynamic rate.
    increase_step:
        Additive increment applied to the rate on successful requests.
    decrease_factor:
        Multiplicative factor applied to the rate when backoff is triggered
        (e.g. on HTTP 429). Must be in (0, 1].
    """

    def __init__(
        self,
        initial_rate: float,
        min_rate: float = 0.1,
        max_rate: float = 50.0,
        increase_step: float = 0.1,
        decrease_factor: float = 0.5,
    ) -> None:
        if initial_rate <= 0:
            raise ValueError("initial_rate must be > 0")
        if not (0 < decrease_factor <= 1):
            raise ValueError("decrease_factor must be in (0, 1]")

        self.current_rate = float(initial_rate)
        self.min_rate = float(min_rate)
        self.max_rate = float(max_rate)
        self.increase_step = float(increase_step)
        self.decrease_factor = float(decrease_factor)

        # Token bucket state
        self._tokens = self.current_rate  # start with one second worth of tokens
        self._last_refill = time.monotonic()

        # Cooldown window (e.g. Retry-After)
        self._cooldown_until: float = 0.0

        self._lock = threading.Lock()

        logger.debug(
            "DynamicRateLimiter initialized: %s",
            {
                "current_rate": self.current_rate,
                "min_rate": self.min_rate,
                "max_rate": self.max_rate,
                "increase_step": self.increase_step,
                "decrease_factor": self.decrease_factor,
            },
        )

    def _refill(self, now: float) -> None:
        """Refill tokens based on elapsed time and current_rate."""
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return

        # Add tokens proportional to elapsed time and current rate
        self._tokens += elapsed * self.current_rate

        # Cap burst size to 2 seconds worth of tokens
        max_tokens = 2.0 * self.current_rate
        if self._tokens > max_tokens:
            self._tokens = max_tokens

        self._last_refill = now

    def acquire(self) -> None:
        """Block until a token is available and we're out of cooldown.

        This should be called immediately before making an outbound request.
        """
        while True:
            with self._lock:
                now = time.monotonic()

                # Honor cooldown (e.g. Retry-After)
                if now < self._cooldown_until:
                    sleep_for = self._cooldown_until - now
                else:
                    self._refill(now)
                    if self._tokens >= 1.0:
                        self._tokens -= 1.0
                        return

                    # Time to next token at current_rate
                    if self.current_rate > 0:
                        missing = 1.0 - self._tokens
                        sleep_for = max(missing / self.current_rate, 0.01)
                    else:
                        # Extremely conservative fallback if rate hit 0
                        sleep_for = 0.5

            time.sleep(sleep_for)

    def on_success(self) -> None:
        """Call this after a successful request to gently increase rate."""
        with self._lock:
            prev_rate = self.current_rate
            self.current_rate = min(
                self.max_rate,
                self.current_rate + self.increase_step,
            )
            if self.current_rate != prev_rate:
                logger.debug(
                    "DynamicRateLimiter on_success: rate increased",
                    extra={
                        "previous_rate": prev_rate,
                        "new_rate": self.current_rate,
                    },
                )

    def on_429(self, retry_after: Optional[float] = None) -> None:
        """Call this when you receive a 429 or similar backoff signal.

        Parameters
        ----------
        retry_after:
            Optional retry-after interval in seconds. If not provided,
            a conservative default is calculated from the current rate.
        """
        with self._lock:
            prev_rate = self.current_rate
            # Multiplicative decrease
            self.current_rate = max(
                self.min_rate,
                self.current_rate * self.decrease_factor,
            )

            now = time.monotonic()

            if retry_after is not None and retry_after > 0:
                cooldown = retry_after
            else:
                # Fallback: one second per current_rate unit, capped
                cooldown = min(60.0, max(1.0, 1.0 / self.current_rate))

            self._cooldown_until = max(self._cooldown_until, now + cooldown)

            # Trim tokens so we restart cautiously
            self._tokens = min(self._tokens, self.current_rate)

            logger.warning(
                "DynamicRateLimiter backoff triggered",
                extra={
                    "previous_rate": prev_rate,
                    "new_rate": self.current_rate,
                    "retry_after": retry_after,
                    "cooldown_until": self._cooldown_until,
                },
            )

    def snapshot(self) -> Dict[str, float]:
        """Return a lightweight snapshot of limiter internals.

        The values are intended for metrics / logging and are not guaranteed
        to be perfectly synchronized with in-flight operations, but they are
        good enough for observability dashboards.

        Returns
        -------
        dict
            A dictionary with keys:
            - current_rate
            - tokens
            - cooldown_until
        """
        with self._lock:
            return {
                "current_rate": float(self.current_rate),
                "tokens": float(self._tokens),
                "cooldown_until": float(self._cooldown_until),
            }
