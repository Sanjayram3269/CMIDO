from __future__ import annotations

from typing import Any

from src.construction.simulation.impact import (
    analyze_schedule_impact,
)
from src.construction.uncertainty.risk import (
    VALID_RISK_TYPES,
    build_risk,
)


def build_risk_scenario(
    project_data: dict[str, Any],
    risk: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate one deterministic construction-risk scenario.

    The risk record is validated and then, when it targets an
    activity with a positive impact_days value, the existing
    schedule-impact engine is used to propagate that impact
    through the project schedule.

    This function does not modify project_data.
    """

    if not isinstance(project_data, dict):
        raise ValueError(
            "project_data must be a dictionary"
        )

    if not isinstance(risk, dict):
        raise ValueError(
            "risk must be a dictionary"
        )

    required_fields = {
        "risk_id",
        "risk_type",
        "description",
        "severity",
        "probability",
        "impact_days",
    }

    missing = required_fields - risk.keys()

    if missing:
        raise ValueError(
            "Risk missing fields: "
            f"{sorted(missing)}"
        )

    normalized_risk = build_risk(
        risk_id=risk["risk_id"],
        risk_type=risk["risk_type"],
        description=risk["description"],
        severity=risk["severity"],
        probability=risk["probability"],
        impact_days=risk["impact_days"],
        activity_id=risk.get("activity_id"),
        material_id=risk.get("material_id"),
    )

    activity_id = normalized_risk["activity_id"]
    impact_days = normalized_risk["impact_days"]

    schedule = None

    if activity_id is not None:
        schedule = analyze_schedule_impact(
            project_data,
            activity_id,
            impact_days,
        )

    return {
        "risk": normalized_risk,
        "scenario": {
            "risk_id": normalized_risk["risk_id"],
            "risk_type": normalized_risk["risk_type"],
            "activity_id": activity_id,
            "impact_days": impact_days,
        },
        "schedule": schedule,
    }