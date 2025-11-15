from api_ratelimiter.dynamic_ratelimiter import DynamicRateLimiter


def test_dynamic_rate_limiter_on_success_increases_rate():
    limiter = DynamicRateLimiter(initial_rate=5.0, min_rate=0.1, max_rate=10.0, increase_step=0.5)
    snap_before = limiter.snapshot()
    limiter.on_success()
    snap_after = limiter.snapshot()

    assert snap_after["current_rate"] >= snap_before["current_rate"]
    assert snap_after["current_rate"] <= 10.0


def test_dynamic_rate_limiter_on_429_decreases_rate_and_sets_cooldown():
    limiter = DynamicRateLimiter(initial_rate=5.0, min_rate=0.1, max_rate=10.0, decrease_factor=0.5)
    snap_before = limiter.snapshot()
    limiter.on_429(retry_after=1.0)
    snap_after = limiter.snapshot()

    assert snap_after["current_rate"] <= snap_before["current_rate"]
    assert snap_after["current_rate"] >= 0.1
    assert snap_after["cooldown_until"] > 0.0


def test_dynamic_rate_limiter_snapshot_is_stable_dict():
    limiter = DynamicRateLimiter(initial_rate=3.0)
    snap = limiter.snapshot()

    assert set(snap.keys()) == {"current_rate", "tokens", "cooldown_until"}
    assert isinstance(snap["current_rate"], float)
    assert isinstance(snap["tokens"], float)
    assert isinstance(snap["cooldown_until"], float)
