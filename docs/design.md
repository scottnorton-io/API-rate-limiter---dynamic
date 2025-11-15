# Design

This page summarizes the design from `background.md`.

---

## Token Bucket + AIMD

The core limiter, `DynamicRateLimiter`, combines:

1. **Token Bucket**

   - `current_rate` (requests per second)
   - `tokens` (available immediate requests)
   - `last_refill` (time of last refill)
   - `cooldown_until` (honors Retry-After and other cooldowns)

   Tokens refill at `current_rate` tokens/second and are capped to avoid large bursts.

2. **AIMD (Additive Increase / Multiplicative Decrease)**

   - On success, `current_rate` increases by a fixed `increase_step`.
   - On backoff (e.g. 429), `current_rate` is multiplied by `decrease_factor`.
   - This converges on a sustainable rate just below the real-world limit.

---

## Backoff Behavior

When a response has a status code in `backoff_status_codes` (default: `(429,)`):

- If status is 429 and `Retry-After` is present:
  - Parse `Retry-After` as seconds and use as cooldown.
- Otherwise:
  - Use a conservative cooldown based on `current_rate` (bounded).

In both cases, the limiter:

- Decreases `current_rate` using `decrease_factor`.
- Updates `cooldown_until`.
- Trims tokens to restart cautiously.

---

## Configuration Registry

`ApiRateConfig` instances live in `API_RATE_CONFIGS` and store:

- `base_url`
- `initial_rate`, `min_rate`, `max_rate`
- `increase_step`, `decrease_factor`
- Optional `documented_limit_desc`

This allows all rate tuning to remain centralized and documented.

---

For the full design narrative (including future ideas and limitations), see
`background.md` in the repository.
