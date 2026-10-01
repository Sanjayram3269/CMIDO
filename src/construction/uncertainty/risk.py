from __future__ import annotations

from typing import Any


VALID_RISK_TYPES = {
    "SCHEDULE",
    "RESOURCE",
    "PROCUREMENT",
    "COST",
    "QUALITY",
    "SAFETY",
}


VALID_SEVERITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


def build_risk(
    risk_id: str,
    risk_type: str,
    description: str,
    severity: str,
    probability: float,
    impact_days: int = 0,
    activity_id: str | None = None,
    material_id: str | None = None,
) -> dict[str, Any]:
    """
    Build a validated deterministic construction-risk record.

    This function only represents risk information.
    It does not simulate or predict project outcomes.
    """

    if not isinstance(risk_id, str) or not risk_id.strip():
        raise ValueError(
            "risk_id must be a non-empty string"
        )

    if risk_type not in VALID_RISK_TYPES:
        raise ValueError(
            f"Invalid risk_type: {risk_type}"
        )

    if not isinstance(description, str) or not description.strip():
        raise ValueError(
            "description must be a non-empty string"
        )

    if severity not in VALID_SEVERITIES:
        raise ValueError(
            f"Invalid severity: {severity}"
        )

    if not isinstance(probability, (int, float)):
        raise ValueError(
            "probability must be numeric"
        )

    if not 0 <= probability <= 1:
        raise ValueError(
            "probability must be between 0 and 1"
        )

    if not isinstance(impact_days, int):
        raise ValueError(
            "impact_days must be an integer"
        )

    if impact_days < 0:
        raise ValueError(
            "impact_days cannot be negative"
        )

    return {
        "risk_id": risk_id,
        "risk_type": risk_type,
        "description": description,
        "severity": severity,
        "probability": float(probability),
        "impact_days": impact_days,
        "activity_id": activity_id,
        "material_id": material_id,
    }