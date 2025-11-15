import json
from pathlib import Path

import pytest

from api_ratelimiter.api_rate_config import ApiRateConfig
from api_ratelimiter.config_overrides import (
    load_api_rate_overrides_json,
    merged_api_rate_configs,
    list_available_integrations,
)


def _write_json(tmp_path: Path, name: str, data: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_api_rate_overrides_json_happy_path(tmp_path):
    overrides_data = {
        "custom_api": {
            "rate_limit_per_sec": 2.0,
            "burst_size": 2.0,
            "increase_factor": 0.1,
            "decrease_factor": 0.5,
            "min_rate": 0.1,
            "max_rate": 5.0,
            "cooldown_multiplier": 1.5,
        }
    }
    json_path = _write_json(tmp_path, "overrides.json", overrides_data)

    overrides = load_api_rate_overrides_json(str(json_path))

    assert "custom_api" in overrides
    cfg = overrides["custom_api"]
    assert isinstance(cfg, ApiRateConfig)
    assert cfg.rate_limit_per_sec == 2.0
    assert cfg.burst_size == 2.0
    assert cfg.max_rate == 5.0


def test_load_api_rate_overrides_json_invalid_top_level(tmp_path):
    # Top level must be a mapping of names -> config dicts.
    json_path = _write_json(tmp_path, "overrides.json", ["not-a-mapping"])

    with pytest.raises(ValueError):
        load_api_rate_overrides_json(str(json_path))


def test_load_api_rate_overrides_json_missing_required_fields(tmp_path):
    # Missing required numeric fields should raise a clear error.
    overrides_data = {"custom_api": {}}
    json_path = _write_json(tmp_path, "overrides.json", overrides_data)

    with pytest.raises(Exception):
        # Implementation may raise ValueError or KeyError; we accept either here.
        load_api_rate_overrides_json(str(json_path))


def test_merged_api_rate_configs_includes_overrides(tmp_path):
    overrides_data = {
        "custom_api": {
            "rate_limit_per_sec": 1.0,
            "burst_size": 1.0,
            "increase_factor": 0.1,
            "decrease_factor": 0.5,
            "min_rate": 0.1,
            "max_rate": 2.0,
            "cooldown_multiplier": 1.5,
        }
    }
    json_path = _write_json(tmp_path, "overrides.json", overrides_data)
    overrides = load_api_rate_overrides_json(str(json_path))

    all_configs = merged_api_rate_configs(overrides)

    # Should include built-in configs (like "notion") and our override.
    assert "custom_api" in all_configs
    assert "notion" in all_configs

    custom_cfg = all_configs["custom_api"]
    assert isinstance(custom_cfg, ApiRateConfig)
    assert custom_cfg.max_rate == 2.0


def test_list_available_integrations_uses_provided_mapping(tmp_path):
    overrides_data = {
        "custom_api": {
            "rate_limit_per_sec": 1.0,
            "burst_size": 1.0,
            "increase_factor": 0.1,
            "decrease_factor": 0.5,
            "min_rate": 0.1,
            "max_rate": 2.0,
            "cooldown_multiplier": 1.5,
        }
    }
    json_path = _write_json(tmp_path, "overrides.json", overrides_data)
    overrides = load_api_rate_overrides_json(str(json_path))
    all_configs = merged_api_rate_configs(overrides)

    names = list_available_integrations(all_configs)

    assert "custom_api" in names
    # We expect at least one built-in integration to be present as well.
    assert any(name in names for name in ("notion", "airtable", "github"))
