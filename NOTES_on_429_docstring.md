# Suggested `on_429` docstring update

To clarify that `DynamicRateLimiter.on_429` is now the generic backoff handler
for all configured backoff status codes (not just 429), you can update its
docstring to something like the following:

```python
    def on_429(self, retry_after: float | None = None) -> None:
        """Handle a backoff signal from the upstream API.

        Historically this method was only used for HTTP 429 responses,
        hence the name. In the current design it is the generic backoff
        handler for *all* configured backoff status codes.

        Behaviour:

        - Applies a multiplicative decrease to the current rate
          (down to ``min_rate``), leaving the token bucket in a safe state.
        - Sets a cooldown window during which ``acquire()`` will block
          or raise immediately, depending on your calling pattern.
          * If ``retry_after`` is provided (for example from a 429
            ``Retry-After`` header), it is used directly.
          * Otherwise, a conservative cooldown is derived from the
            current rate and ``cooldown_multiplier``.
        - Ensures the rate stays within [``min_rate``, ``max_rate``].
        """
```

This is a documentation-only change and does not affect runtime behaviour.
