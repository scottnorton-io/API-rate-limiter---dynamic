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

    limiter.on_success()
    assert limiter.current_rate == 2.0

    limiter.on_success()
    assert limiter.current_rate == 2.0


def test_on_429_reduces_rate_and_sets_cooldown(monkeypatch) -> None:
    fake_time = {"t": 0.0}

    def monotonic() -> float:
        return fake_time["t"]

    def sleep(seconds: float) -> None:
        fake_time["t"] += seconds

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

    limiter.on_429(retry_after=5.0)
    assert limiter.current_rate == 5.0
    assert limiter._cooldown_until > fake_time["t"]  # type: ignore[attr-defined]

    before = fake_time["t"]
    limiter.acquire()
    after = fake_time["t"]

    assert after - before >= 5.0


def test_on_backoff_alias_calls_on_429(monkeypatch) -> None:
    calls = {"on_429": 0, "last_retry_after": None}

    limiter = DynamicRateLimiter(
        initial_rate=5.0,
        min_rate=1.0,
        max_rate=10.0,
        increase_step=1.0,
        decrease_factor=0.5,
    )

    original_on_429 = limiter.on_429

    def wrapped_on_429(retry_after=None):
        calls["on_429"] += 1
        calls["last_retry_after"] = retry_after
        return original_on_429(retry_after=retry_after)

    monkeypatch.setattr(limiter, "on_429", wrapped_on_429)

    limiter.on_backoff(retry_after=7.5)

    assert calls["on_429"] == 1
    assert calls["last_retry_after"] == 7.5
