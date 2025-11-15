from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ApiRateConfig:
    """
    Configuration for a given external API.

    This defines:
    - base_url: the API base URL
    - initial_rate: starting requests per second
    - min_rate / max_rate: dynamic rate bounds
    - increase_step / decrease_factor: tuning parameters for AIMD
    - documented_limit_desc: optional human-readable description of vendor limits
    """
    name: str
    base_url: str

    initial_rate: float
    min_rate: float
    max_rate: float
    increase_step: float
    decrease_factor: float

    documented_limit_desc: Optional[str] = None


API_RATE_CONFIGS: Dict[str, ApiRateConfig] = {
    # Notion: docs describe a recommended average of about 3 requests per second
    # per integration, with some burst tolerance.
    "notion": ApiRateConfig(
        name="notion",
        base_url="https://api.notion.com/v1",
        initial_rate=2.0,          # start slightly below 3 req/s
        min_rate=0.3,
        max_rate=3.5,
        increase_step=0.1,
        decrease_factor=0.5,
        documented_limit_desc="Approx. 3 requests/second per integration on average.",
    ),

    # Vanta: numeric limits are not clearly published; let the limiter learn.
    "vanta": ApiRateConfig(
        name="vanta",
        base_url="https://api.vanta.com",
        initial_rate=3.0,
        min_rate=0.5,
        max_rate=10.0,
        increase_step=0.2,
        decrease_factor=0.5,
        documented_limit_desc="Rate limit not clearly published; dynamic tuning + 429 handling.",
    ),

    # Fieldguide: similar situation to Vanta.
    "fieldguide": ApiRateConfig(
        name="fieldguide",
        base_url="https://api.fieldguide.io",
        initial_rate=3.0,
        min_rate=0.5,
        max_rate=10.0,
        increase_step=0.2,
        decrease_factor=0.5,
        documented_limit_desc="Rate limit not clearly published; dynamic tuning + 429 handling.",
    ),
}


def get_api_rate_config(name: str) -> ApiRateConfig:
    """
    Look up a named API config (e.g. 'notion', 'vanta', 'fieldguide').

    Raises KeyError if not found.
    """
    key = name.lower()
    return API_RATE_CONFIGS[key]
