from __future__ import annotations

from typing import Any


VALID_CONFIGURATIONS = {
    "CPM",
    "CPM_DELAY",
    "INTEGRATED_OPERATIONAL",
    "FULL_CMIDO",
}

VALID_SCENARIO_TYPES = {
    "BASELINE",
    "SCHEDULE_DELAY",
    "PROCUREMENT_DISRUPTION",
    "RESOURCE_DISRUPTION",
    "RISK_EVENT",
    "COMBINED_DISRUPTION",
}

VALID_RISK_SEVERITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}

DEFAULT_DELAY_LEVELS = (0, 1, 3, 5, 7, 14)
DEFAULT_PROCUREMENT_LEVELS = ("BASELINE", "MODERATE", "SEVERE")
DEFAULT_RESOURCE_LEVELS = ("BASELINE", "MODERATE", "SEVERE")


def validate_configuration(configuration: str) -> str:
    if configuration not in VALID_CONFIGURATIONS:
        raise ValueError(f"Invalid experiment configuration: {configuration}")
    return configuration


def validate_scenario_type(scenario_type: str) -> str:
    if scenario_type not in VALID_SCENARIO_TYPES:
        raise ValueError(f"Invalid scenario type: {scenario_type}")
    return scenario_type


def validate_delay_levels(levels: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    if not isinstance(levels, (list, tuple)):
        raise ValueError("delay levels must be a list or tuple")
    normalized = tuple(levels)
    if any(not isinstance(value, int) for value in normalized):
        raise ValueError("delay levels must contain integers")
    if any(value < 0 for value in normalized):
        raise ValueError("delay levels cannot be negative")
    if len(set(normalized)) != len(normalized):
        raise ValueError("delay levels must be unique")
    return normalized


def build_factor_space(
    delay_levels: list[int] | tuple[int, ...] = DEFAULT_DELAY_LEVELS,
    procurement_levels: list[str] | tuple[str, ...] = DEFAULT_PROCUREMENT_LEVELS,
    resource_levels: list[str] | tuple[str, ...] = DEFAULT_RESOURCE_LEVELS,
    risk_severities: list[str] | tuple[str, ...] = tuple(sorted(VALID_RISK_SEVERITIES)),
) -> dict[str, Any]:
    """Return a validated, serializable CMIDO experimental factor space."""
    delays = validate_delay_levels(delay_levels)
    procurement = tuple(procurement_levels)
    resources = tuple(resource_levels)
    risks = tuple(risk_severities)

    if not procurement or any(not isinstance(value, str) or not value.strip() for value in procurement):
        raise ValueError("procurement levels must contain non-empty strings")
    if not resources or any(not isinstance(value, str) or not value.strip() for value in resources):
        raise ValueError("resource levels must contain non-empty strings")
    if not risks or any(value not in VALID_RISK_SEVERITIES for value in risks):
        raise ValueError("risk severities contain an invalid value")

    return {
        "delay_days": list(delays),
        "procurement_condition": list(procurement),
        "resource_condition": list(resources),
        "risk_severity": list(risks),
    }
