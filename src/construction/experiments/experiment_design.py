from __future__ import annotations

from typing import Any

from .factors import build_factor_space, validate_configuration, validate_scenario_type
from .protocols import build_scenario_protocol


EXPERIMENTAL_METRICS = (
    "baseline_duration_days",
    "scenario_duration_days",
    "project_delay_days",
    "relative_delay",
    "critical_path_changed",
    "affected_activity_count",
)

RESEARCH_HYPOTHESES = {
    "H1": "Increasing a critical-path activity delay should produce non-decreasing project delay.",
    "H2": "Equivalent disruptions can have different project effects depending on activity schedule sensitivity.",
    "H3": "Procurement or resource disruptions can propagate into schedule outcomes even when the baseline activity network is unchanged.",
    "H4": "Combined disruptions can reveal cross-domain effects that are not represented by isolated disruption analysis.",
    "H5": "The integrated CMIDO representation can expose cross-domain effects that are not visible in scheduling-only analysis.",
}


SCENARIO_TEMPLATES = {
    "BASELINE": {"delay_days": 0},
    "SCHEDULE_DELAY": {"delay_days": 1},
    "PROCUREMENT_DISRUPTION": {"procurement_condition": "MODERATE"},
    "RESOURCE_DISRUPTION": {"resource_condition": "MODERATE"},
    "RISK_EVENT": {"risk_severity": "HIGH"},
    "COMBINED_DISRUPTION": {
        "delay_days": 3,
        "procurement_condition": "MODERATE",
        "resource_condition": "MODERATE",
        "risk_severity": "HIGH",
    },
}


CONFIGURATION_ORDER = (
    "CPM",
    "CPM_DELAY",
    "INTEGRATED_OPERATIONAL",
    "FULL_CMIDO",
)

SCENARIO_ORDER = (
    "BASELINE",
    "SCHEDULE_DELAY",
    "PROCUREMENT_DISRUPTION",
    "RESOURCE_DISRUPTION",
    "RISK_EVENT",
    "COMBINED_DISRUPTION",
)


def build_experiment_design(
    experiment_id: str,
    project_id: str,
    seed: int = 0,
    factor_space: dict[str, Any] | None = None,
    configurations: list[str] | tuple[str, ...] = CONFIGURATION_ORDER,
    scenario_types: list[str] | tuple[str, ...] = SCENARIO_ORDER,
) -> dict[str, Any]:
    """Build a deterministic 8G research protocol without executing scenarios.

    The design layer defines what will be tested. It deliberately does not
    run the construction engines or make claims about expected outcomes.
    """
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("experiment_id must be a non-empty string")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id must be a non-empty string")
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    if not isinstance(configurations, (list, tuple)) or not configurations:
        raise ValueError("configurations must be a non-empty list or tuple")
    if not isinstance(scenario_types, (list, tuple)) or not scenario_types:
        raise ValueError("scenario_types must be a non-empty list or tuple")

    normalized_configs = tuple(configurations)
    normalized_scenarios = tuple(scenario_types)

    if len(set(normalized_configs)) != len(normalized_configs):
        raise ValueError("configurations must be unique")
    if len(set(normalized_scenarios)) != len(normalized_scenarios):
        raise ValueError("scenario_types must be unique")

    for configuration in normalized_configs:
        validate_configuration(configuration)
    for scenario_type in normalized_scenarios:
        validate_scenario_type(scenario_type)

    factors = build_factor_space() if factor_space is None else factor_space
    if not isinstance(factors, dict):
        raise ValueError("factor_space must be a dictionary")

    scenarios: list[dict[str, Any]] = []
    sequence = 1
    for configuration in normalized_configs:
        for scenario_type in normalized_scenarios:
            template = dict(SCENARIO_TEMPLATES[scenario_type])
            scenario_id = f"{experiment_id}_S{sequence:03d}"
            scenarios.append(
                build_scenario_protocol(
                    scenario_id=scenario_id,
                    scenario_type=scenario_type,
                    configuration=configuration,
                    factors=template,
                )
            )
            sequence += 1

    return {
        "experiment_id": experiment_id,
        "project_id": project_id,
        "seed": seed,
        "factor_space": factors,
        "configurations": list(normalized_configs),
        "scenario_types": list(normalized_scenarios),
        "metrics": list(EXPERIMENTAL_METRICS),
        "hypotheses": dict(RESEARCH_HYPOTHESES),
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }
