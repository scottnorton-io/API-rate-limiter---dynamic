"""Public package interface for dynamic-api-rate-limiter.

This module exposes the primary public types and helpers:

- :class:`DynamicRateLimiter`
- :class:`DynamicAPIClient`
- :func:`make_client_for`
- :class:`ApiRateConfig`
- :func:`get_api_rate_config`
- :data:`API_RATE_CONFIGS`
"""

from __future__ import annotations

from .dynamic_ratelimiter import DynamicRateLimiter
from .clients import DynamicAPIClient, make_client_for
from .api_rate_config import ApiRateConfig, API_RATE_CONFIGS, get_api_rate_config

__all__ = [
    "DynamicRateLimiter",
    "DynamicAPIClient",
    "make_client_for",
    "ApiRateConfig",
    "API_RATE_CONFIGS",
    "get_api_rate_config",
]

__version__ = "0.1.0"
