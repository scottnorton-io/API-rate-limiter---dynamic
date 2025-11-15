"""Per-API rate configuration registry.

This module defines :class:`ApiRateConfig` and a central mapping
:data:`API_RATE_CONFIGS` that stores configuration for commonly-used APIs,
such as Notion, Vanta, and Fieldguide.

You can extend this registry with additional APIs or override these
defaults in your own code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ApiRateConfig:
    """Configuration for a single API's rate limiting behavior.

    Parameters
    ----------
    name:
        Logical name for the API (e.g. "notion").
    base_url:
        Base URL for the API, without a trailing slash.
    initial_rate:
        Starting rate in requests per second.
    min_rate:
        Minimum allowed rate in requests per second.
    max_rate:
        Maximum allowed rate in requests per second.
    increase_step:
        Additive increase step for the AIMD algorithm.
    decrease_factor:
        Multiplicative decrease factor for backoff (0 < factor <= 1).
    documented_limit_desc:
        Optional free-text description of the vendor's documented limits
        or any notes about how this configuration was chosen.
    """

    name: str
    base_url: str

    initial_rate: float
    min_rate: float
    max_rate: float
    increase_step: float
    decrease_factor: float

    documented_limit_desc: Optional[str] = None


# NOTE:
# These values are intentionally conservative starting points and may not
# exactly reflect current vendor documentation. They are meant to be
# safe defaults that AIMD can tune around. Adjust them as needed for
# your environment and workloads.
API_RATE_CONFIGS: Dict[str, ApiRateConfig] = {
    "notion": ApiRateConfig(
        name="notion",
        base_url="https://api.notion.com/v1",
        initial_rate=2.0,
        min_rate=0.3,
        max_rate=3.5,
        increase_step=0.1,
        decrease_factor=0.5,
        documented_limit_desc=(
            "Conservative starting point near typical Notion guidance of "
            "a few requests per second per integration."
        ),
    ),
    "vanta": ApiRateConfig(
        name="vanta",
        base_url="https://api.vanta.com",
        initial_rate=2.0,
        min_rate=0.5,
        max_rate=5.0,
        increase_step=0.2,
        decrease_factor=0.5,
        documented_limit_desc=(
            "Placeholder configuration for Vanta API. Tune based on your "
            "observed behavior and vendor guidance."
        ),
    ),
    "fieldguide": ApiRateConfig(
        name="fieldguide",
        base_url="https://api.fieldguide.io",
        initial_rate=2.0,
        min_rate=0.5,
        max_rate=5.0,
        increase_step=0.2,
        decrease_factor=0.5,
        documented_limit_desc=(
            "Placeholder configuration for Fieldguide API. Tune based on "
            "your observed behavior and vendor guidance."
        ),
    ),
}


def get_api_rate_config(name: str) -> ApiRateConfig:
    """Return the :class:`ApiRateConfig` for a given API name.

    Raises
    ------
    KeyError
        If the API name is unknown. The error message will include the
        available keys to help with debugging.
    """
    try:
        return API_RATE_CONFIGS[name]
    except KeyError as exc:  # pragma: no cover - simple error path
        available = ", ".join(sorted(API_RATE_CONFIGS.keys()))
        raise KeyError(
            f"Unknown API name {name!r}. Available configurations: {available}"            ) from exc


__all__ = [
    "ApiRateConfig",
    "API_RATE_CONFIGS",
    "get_api_rate_config",
]
