from __future__ import annotations

from typing import Any

from src.construction.scheduling import (
    calculate_critical_path,
)
from src.construction.uncertainty.risk import (
    VALID_RISK_TYPES,
    VALID_SEVERITIES,
    build_risk,
)
from src.construction.uncertainty.scenario import (
    build_risk_scenario,
)


def build_uncertainty_context(
    project_data: dict[str, Any],
    risks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build the integrated CMIDO 7D uncertainty context.

    The function combines:

        Baseline Project
             +
        Risk Representation
             +
        Deterministic Risk Scenarios
             ↓
        Integrated Uncertainty Context

    This layer does not perform probabilistic simulation,
    Monte Carlo analysis, optimization, or prediction.

    It reuses the existing deterministic scheduling engine.
    """

    if not isinstance(project_data, dict):
        raise ValueError(
            "project_data must be a dictionary"
        )

    if risks is None:
        risks = []

    if not isinstance(risks, list):
        raise ValueError(
            "risks must be a list"
        )

    # ---------------------------------------------------------
    # 1. Baseline
    # ---------------------------------------------------------

    baseline = calculate_critical_path(
        project_data
    )

    baseline_duration = baseline[
        "project_duration"
    ]

    # ---------------------------------------------------------
    # 2. Validate and normalize risks
    # ---------------------------------------------------------

    normalized_risks: list[dict[str, Any]] = []

    for risk in risks:

        if not isinstance(risk, dict):
            raise ValueError(
                "Each risk must be a dictionary"
            )

        required_fields = {
            "risk_id",
            "risk_type",
            "description",
            "severity",
            "probability",
            "impact_days",
        }

        missing = (
            required_fields
            - risk.keys()
        )

        if missing:
            raise ValueError(
                "Risk missing fields: "
                f"{sorted(missing)}"
            )

        normalized_risks.append(
            build_risk(
                risk_id=risk["risk_id"],
                risk_type=risk["risk_type"],
                description=risk["description"],
                severity=risk["severity"],
                probability=risk["probability"],
                impact_days=risk["impact_days"],
                activity_id=risk.get(
                    "activity_id"
                ),
                material_id=risk.get(
                    "material_id"
                ),
            )
        )

    # ---------------------------------------------------------
    # 3. Risk summary
    # ---------------------------------------------------------

    risk_summary = {
        "total_risks": len(
            normalized_risks
        ),
        "schedule_risks": 0,
        "resource_risks": 0,
        "procurement_risks": 0,
        "cost_risks": 0,
        "quality_risks": 0,
        "safety_risks": 0,
        "high_risk_count": 0,
        "critical_risk_count": 0,
    }

    for risk in normalized_risks:

        risk_type = risk[
            "risk_type"
        ]

        severity = risk[
            "severity"
        ]

        if risk_type == "SCHEDULE":
            risk_summary[
                "schedule_risks"
            ] += 1

        elif risk_type == "RESOURCE":
            risk_summary[
                "resource_risks"
            ] += 1

        elif risk_type == "PROCUREMENT":
            risk_summary[
                "procurement_risks"
            ] += 1

        elif risk_type == "COST":
            risk_summary[
                "cost_risks"
            ] += 1

        elif risk_type == "QUALITY":
            risk_summary[
                "quality_risks"
            ] += 1

        elif risk_type == "SAFETY":
            risk_summary[
                "safety_risks"
            ] += 1

        if severity == "HIGH":
            risk_summary[
                "high_risk_count"
            ] += 1

        if severity == "CRITICAL":
            risk_summary[
                "critical_risk_count"
            ] += 1

    # ---------------------------------------------------------
    # 4. Evaluate scenarios
    # ---------------------------------------------------------

    scenarios: list[dict[str, Any]] = []

    for risk in normalized_risks:

        scenarios.append(
            build_risk_scenario(
                project_data,
                risk,
            )
        )

    # ---------------------------------------------------------
    # 5. Aggregate project impact
    # ---------------------------------------------------------

    scenario_duration = (
        baseline_duration
    )

    project_delay_days = 0

    for item in scenarios:

        schedule = item[
            "schedule"
        ]

        if schedule is None:
            continue

        delay = schedule[
            "project_delay_days"
        ]

        duration = schedule[
            "scenario_project_duration"
        ]

        if delay > project_delay_days:
            project_delay_days = delay

        if duration > scenario_duration:
            scenario_duration = duration

    project_impact = {
        "baseline_duration_days": (
            baseline_duration
        ),
        "scenario_duration_days": (
            scenario_duration
        ),
        "project_delay_days": (
            project_delay_days
        ),
        "delay_present": (
            project_delay_days > 0
        ),
    }

    # ---------------------------------------------------------
    # 6. Final integrated context
    # ---------------------------------------------------------

    return {
        "baseline": {
            "project_duration_days": (
                baseline_duration
            ),
            "critical_path": (
                baseline["critical_path"]
            ),
        },
        "risks": normalized_risks,
        "risk_summary": risk_summary,
        "scenarios": scenarios,
        "project_impact": project_impact,
    }