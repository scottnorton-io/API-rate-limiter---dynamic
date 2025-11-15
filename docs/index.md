# Dynamic API Rate Limiter

**Dynamic, 429-aware API rate limiter with self-tuning AIMD and per-API configs.**

This library helps you stay within API rate limits (Notion, Vanta, Fieldguide, and others)
while still pushing as much safe throughput as possible.

It:

- Learns optimal request rates using an **AIMD** algorithm.
- Honors **HTTP 429** and `Retry-After` headers.
- Centralizes per-API configuration in one registry.
- Exposes an HTTP client and a standalone rate limiter.
- Includes logging and metrics hooks for observability.

---

## Project Links

- **Source Code:** <https://github.com/scottnorton-io/dynamic-api-rate-limiter>
- **License:** MIT
- **Author:** Scott Norton

Use the navigation on the left to explore:

- **Getting Started** – installation, quick start
- **Usage** – practical, copy-pasteable examples
- **Design** – how the limiter works internally
- **Metrics & Observability** – logging, metrics patterns
- **Changelog** – version history
