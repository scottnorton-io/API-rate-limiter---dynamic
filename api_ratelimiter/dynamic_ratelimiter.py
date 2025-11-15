import time
import threading
from typing import Optional


class DynamicRateLimiter:
    """
    Adaptive token-bucket rate limiter with AIMD-style tuning.

    - current_rate: requests per second (dynamic)
    - min_rate / max_rate: safety bounds for the dynamic rate
    - increase_step: additive increase on success
    - decrease_factor: multiplicative decrease on backoff (e.g. 429)

    Usage:
        limiter = DynamicRateLimiter(initial_rate=5.0, min_rate=0.2, max_rate=20.0)
        limiter.acquire()
        # make request...
        limiter.on_success()   # or limiter.on_backoff(retry_after)
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
        """
        Block until a token is available and we're out of cooldown.

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
            self.current_rate = min(
                self.max_rate,
                self.current_rate + self.increase_step,
            )

    def on_backoff(self, retry_after: Optional[float] = None) -> None:
        """Alias for :meth:`on_429` for more generic backoff semantics."""
        self.on_429(retry_after=retry_after)

    def on_429(self, retry_after: Optional[float] = None) -> None:
        """
        Call this when you receive a backoff-worthy response (429, 502, 503, etc.).

        - Scales rate down multiplicatively.
        - Applies cooldown based on Retry-After or a conservative guess.
        """
        with self._lock:
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
