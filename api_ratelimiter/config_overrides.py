"""Helpers for customizing and overriding API rate configurations.

This module makes it easier to:

- Load :class:`ApiRateConfig` definitions from JSON files.
- Merge those definitions with the built-in :data:`API_RATE_CONFIGS`.
- Inspect the available integrations at runtime.

The JSON format is intentionally simple. For example::

    {
      "my-internal-api": {
        "base_url": "https://internal.example.com/api",
        "initial_rate": 5.0,
        "min_rate": 1.0,
        "max_rate": 20.0,
        "increase_step": 0.5,
        "decrease_factor": 0.5,
        "documented_limit_desc": "Internal service, tuned for higher throughput."
      }
    }

All numeric fields are required; ``documented_limit_desc`` is optional.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Mapping, Any, Union

from .api_rate_config import ApiRateConfig, API_RATE_CONFIGS


PathLike = Union[str, "Path"]


def _parse_api_rate_config_from_mapping(name: str, data: Mapping[str, Any]) -> ApiRateConfig:
    """Create an :class:`ApiRateConfig` from a mapping.

    Parameters
    ----------
    name:
        Logical name for the integration. Used as the default if ``data``
        does not include its own ``name`` field.
    data:
        Mapping containing at least:

        - ``base_url``
        - ``initial_rate``
        - ``min_rate``
        - ``max_rate``
        - ``increase_step``
        - ``decrease_factor``
    """
    try:
        base_url = str(data["base_url"])
        initial_rate = float(data["initial_rate"])
        min_rate = float(data["min_rate"])
        max_rate = float(data["max_rate"])
        increase_step = float(data["increase_step"])
        decrease_factor = float(data["decrease_factor"])
    except KeyError as exc:  # pragma: no cover - simple error path
        missing = getattr(exc, "args", ["?"])[0]
        raise KeyError(f"Missing required field {missing!r} for ApiRateConfig {name!r}") from exc

    documented_limit_desc = data.get("documented_limit_desc")
    cfg_name = str(data.get("name", name))

    return ApiRateConfig(
        name=cfg_name,
        base_url=base_url,
        initial_rate=initial_rate,
        min_rate=min_rate,
        max_rate=max_rate,
        increase_step=increase_step,
        decrease_factor=decrease_factor,
        documented_limit_desc=documented_limit_desc,
    )


def load_api_rate_overrides_json(path: PathLike) -> Dict[str, ApiRateConfig]:
    """Load API rate configurations from a JSON file.

    The file should contain a mapping of integration names to configuration
    dictionaries as described in this module's docstring.
    """
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError("Top-level JSON structure must be an object/dict")

    overrides: Dict[str, ApiRateConfig] = {}
    for name, value in raw.items():
        if not isinstance(value, dict):
            raise ValueError(f"Expected object for override {name!r}, got {type(value).__name__}")
        overrides[name] = _parse_api_rate_config_from_mapping(name, value)

    return overrides


def merged_api_rate_configs(overrides: Mapping[str, ApiRateConfig]) -> Dict[str, ApiRateConfig]:
    """Return a new mapping that merges built-in configs with ``overrides``.

    ``overrides`` will replace any existing entry with the same key.
    """
    merged: Dict[str, ApiRateConfig] = dict(API_RATE_CONFIGS)
    merged.update(overrides)
    return merged


def list_available_integrations() -> Dict[str, str]:
    """Return a mapping of integration name to base URL.

    This is a light-weight introspection helper that can be used in CLIs or
    dashboards to show which integrations are configured by default.
    """
    return {name: cfg.base_url for name, cfg in API_RATE_CONFIGS.items()}


__all__ = [
    "load_api_rate_overrides_json",
    "merged_api_rate_configs",
    "list_available_integrations",
]
