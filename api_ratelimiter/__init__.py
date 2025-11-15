"""Public package interface for dynamic-api-rate-limiter.

This module exposes the primary public types and helpers:

- :class:`DynamicRateLimiter`
- :class:`DynamicAPIClient`
- :func:`make_client_for`
- :func:`make_client_from_config`
- :class:`ApiRateConfig`
- :func:`get_api_rate_config`
- :data:`API_RATE_CONFIGS`
- :func:`load_api_rate_overrides_json`
- :func:`merged_api_rate_configs`
- :func:`list_available_integrations`
"""

from __future__ import annotations

from .dynamic_ratelimiter import DynamicRateLimiter
from .clients import DynamicAPIClient, make_client_for, make_client_from_config
from .api_rate_config import ApiRateConfig, API_RATE_CONFIGS, get_api_rate_config
from .config_overrides import (
    load_api_rate_overrides_json,
    merged_api_rate_configs,
    list_available_integrations,
)

__all__ = [
    "DynamicRateLimiter",
    "DynamicAPIClient",
    "make_client_for",
    "make_client_from_config",
    "ApiRateConfig",
    "API_RATE_CONFIGS",
    "get_api_rate_config",
    "load_api_rate_overrides_json",
    "merged_api_rate_configs",
    "list_available_integrations",
]

__version__ = "0.1.0"
