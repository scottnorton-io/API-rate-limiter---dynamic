# Changelog

This is a rendered version of `CHANGELOG.md`. For full details, see the file
in the repository.

---

## [Unreleased]

- TBD

## [0.1.0] - Initial public release

### Added

- Dynamic AIMD-based `DynamicRateLimiter` with token-bucket implementation.
- `DynamicAPIClient` that respects 429 responses and `Retry-After` headers.
- Central `ApiRateConfig` registry with initial configs for Notion, Vanta, and Fieldguide.
- `make_client_for()` factory for one-line client creation.
- Logging integration and `snapshot()` for metrics/observability.
- Examples for Notion, Vanta, Fieldguide, logging/metrics, and multi-status backoff.
- CI workflow (lint + tests) and basic test suite.
- Documentation set: `README.md`, `USAGE.md`, `background.md`, `METRICS.md`, `CONTRIBUTING.md`.
- MIT license.
