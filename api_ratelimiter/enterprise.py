"""Enterprise-oriented helpers and wrappers.

This module provides higher-level constructs that are commonly needed in
larger or more complex deployments, such as:

- A thin `EnterpriseClient` wrapper that adds:
  - Structured logging for each request.
  - A pluggable metrics callback.
  - Optional circuit-breaker behavior.
  - Optional multi-tenant context fields (e.g., `tenant_id`).

These are intentionally light-weight abstractions that you can adapt to
your logging / observability stack (Prometheus, StatsD, OpenTelemetry,
vendor-specific APM, etc.).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional

import requests

from .clients import DynamicAPIClient, make_client_for


MetricsHandler = Callable[[Dict[str, Any]], None]


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Configuration for a simple circuit breaker.

    Parameters
    ----------
    failure_threshold:
        How many consecutive failures are allowed before the circuit opens.
    open_interval:
        How long (in seconds) the circuit remains open before allowing
        attempts again.
    """

    failure_threshold: int = 5
    open_interval: float = 30.0


class CircuitOpenError(RuntimeError):
    """Raised when a request is attempted while the circuit is open."""


@dataclass
class EnterpriseClient:
    """Wrapper around :class:`DynamicAPIClient` with enterprise features.

    This client is intended for use in larger systems where you want:

    - Consistent, structured logging for each outbound API call.
    - A central place to feed metrics into your monitoring system.
    - Optional circuit-breaking behavior to avoid hammering dependencies
      that are already failing.
    - Optional multi-tenant context (e.g. `tenant_id`).

    Parameters
    ----------
    name:
        Logical name of this integration (e.g. "notion", "github").
    client:
        The underlying :class:`DynamicAPIClient` instance.
    tenant_id:
        Optional tenant identifier if you multiplex API usage across tenants.
    logger:
        Optional :mod:`logging` logger. If provided, each request will emit
        a structured log record with an ``api_ratelimiter`` field.
    metrics_handler:
        Optional callback that will receive a dictionary describing each
        request outcome. Intended to be wired into Prometheus, StatsD,
        OpenTelemetry, etc.
    circuit_breaker:
        Optional :class:`CircuitBreakerConfig`. If provided, repeated
        failures will temporarily "open" the circuit and raise
        :class:`CircuitOpenError` immediately without hitting the upstream
        API.
    """

    name: str
    client: DynamicAPIClient
    tenant_id: Optional[str] = None
    logger: Optional[logging.Logger] = None
    metrics_handler: Optional[MetricsHandler] = None
    circuit_breaker: Optional[CircuitBreakerConfig] = None

    _failure_count: int = field(default=0, init=False)
    _opened_until: float = field(default=0.0, init=False)

    def request(
        self,
        method: str,
        path: str,
        *,
        context: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform a request with logging, metrics, and optional circuit breaker.

        Parameters
        ----------
        method:
            HTTP method ("GET", "POST", etc.).
        path:
            Request path relative to the client's base URL.
        context:
            Optional mapping of extra fields to be attached to log/metrics
            events (e.g., correlation IDs, job identifiers, etc.).
        kwargs:
            Passed directly to :meth:`DynamicAPIClient.request`.
        """
        ctx = dict(context or {})
        now = time.monotonic()

        # Circuit breaker: fail fast if open
        if self.circuit_breaker is not None and now < self._opened_until:
            raise CircuitOpenError(
                f"Circuit is open for {self.name!r} until {self._opened_until:.3f} (now={now:.3f})"
            )

        logger = self.logger
        metrics = self.metrics_handler

        start = time.monotonic()
        success = False
        error: Optional[BaseException] = None
        response: Optional[requests.Response] = None

        try:
            response = self.client.request(method, path, **kwargs)
            success = True
            return response
        except BaseException as exc:  # noqa: BLE001 - we want to capture everything
            error = exc
            raise
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            snapshot = self.client.limiter.snapshot()

            event: Dict[str, Any] = {
                "event": "api_request",
                "integration": self.name,
                "tenant_id": self.tenant_id,
                "method": method,
                "path": path,
                "elapsed_ms": elapsed_ms,
                "rate_snapshot": snapshot,
                "context": ctx,
            }

            if response is not None:
                event["status_code"] = response.status_code

            if error is not None:
                event["error"] = repr(error)

            # Logging: attach structured data under a single key
            if logger is not None:
                if success:
                    logger.info("api_request success", extra={"api_ratelimiter": event})
                else:
                    logger.warning("api_request failure", extra={"api_ratelimiter": event})

            # Metrics: hand off to caller-provided callback
            if metrics is not None:
                try:
                    metrics(event)
                except Exception:  # pragma: no cover - defensive
                    if logger is not None:
                        logger.exception("metrics_handler raised an exception")

            # Circuit breaker: update state
            if self.circuit_breaker is not None:
                if success:
                    self._failure_count = 0
                else:
                    self._failure_count += 1
                    if self._failure_count >= self.circuit_breaker.failure_threshold:
                        self._opened_until = time.monotonic() + self.circuit_breaker.open_interval
                        if logger is not None:
                            logger.error(
                                "Circuit opened for %s (failures=%d, open_interval=%s)",
                                self.name,
                                self._failure_count,
                                self.circuit_breaker.open_interval,
                            )


def make_enterprise_client(
    api_name: str,
    *,
    tenant_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
    metrics_handler: Optional[MetricsHandler] = None,
    circuit_breaker: Optional[CircuitBreakerConfig] = None,
) -> EnterpriseClient:
    """Create an :class:`EnterpriseClient` for a named integration.

    This is a convenience wrapper around :func:`make_client_for` that adds
    the features provided by :class:`EnterpriseClient`.
    """
    base_client = make_client_for(api_name)
    return EnterpriseClient(
        name=api_name,
        client=base_client,
        tenant_id=tenant_id,
        logger=logger,
        metrics_handler=metrics_handler,
        circuit_breaker=circuit_breaker,
    )


__all__ = [
    "EnterpriseClient",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "MetricsHandler",
    "make_enterprise_client",
]
