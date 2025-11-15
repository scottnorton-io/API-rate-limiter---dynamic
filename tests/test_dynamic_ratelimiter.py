import api_ratelimiter.dynamic_ratelimiter as dr
from api_ratelimiter.dynamic_ratelimiter import DynamicRateLimiter


def test_on_success_increases_rate_up_to_max() -> None:
    limiter = DynamicRateLimiter(
        initial_rate=1.0,
        min_rate=0.5,
        max_rate=2.0,
        increase_step=0.5,
        decrease_factor=0.5,
    )

    assert limiter.current_rate == 1.0

    limiter.on_success()
    assert limiter.current_rate == 1.5

    # Next increase would push to 2.0 (max)
    limiter.on_success()
    assert limiter.current_rate == 2.0

    # Further successes should not exceed max_rate
    limiter.on_success()
    assert limiter.current_rate == 2.0


def test_on_429_reduces_rate_and_sets_cooldown(monkeypatch) -> None:
    fake_time = {"t": 0.0}

    def monotonic() -> float:
        return fake_time["t"]

    def sleep(seconds: float) -> None:
        # Instead of actually sleeping, advance the fake clock.
        fake_time["t"] += seconds

    # Patch the time functions used inside DynamicRateLimiter
    monkeypatch.setattr(dr.time, "monotonic", monotonic)
    monkeypatch.setattr(dr.time, "sleep", sleep)

    limiter = DynamicRateLimiter(
        initial_rate=10.0,
        min_rate=1.0,
        max_rate=20.0,
        increase_step=1.0,
        decrease_factor=0.5,
    )

    assert limiter.current_rate == 10.0

    # Trigger a 429 with an explicit Retry-After of 5 seconds
    limiter.on_429(retry_after=5.0)
    assert limiter.current_rate == 5.0

    # Cooldown should be in the future from the fake clock
    assert limiter._cooldown_until > fake_time["t"]  # type: ignore[attr-defined]

    before = fake_time["t"]
    limiter.acquire()
    after = fake_time["t"]

    # acquire() should have "slept" at least until the cooldown expired
    assert after - before >= 5.0
