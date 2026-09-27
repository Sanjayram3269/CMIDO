from __future__ import annotations

from typing import Any

from src.construction.simulation.impact import (
    analyze_schedule_impact,
)


def analyze_resource_schedule_impact(
    project_data: dict[str, Any],
    resource_id: str,
    activity_id: str,
    shortage_quantity: float,
    shortage_days: int,
) -> dict[str, Any]:
    """
    Connect a resource shortage to a schedule-delay scenario.

    The shortage quantity describes how much resource is missing.

    The shortage_days parameter explicitly describes the resulting
    activity delay. This keeps the model deterministic until a
    productivity/rate model is introduced.

    Returns both the resource constraint information and the
    resulting CPM schedule impact.
    """

    if shortage_quantity < 0:
        raise ValueError(
            "shortage_quantity cannot be negative"
        )

    if shortage_days < 0:
        raise ValueError(
            "shortage_days cannot be negative"
        )

    activity_exists = any(
        activity["activity_id"] == activity_id
        for activity in project_data["activities"]
    )

    if not activity_exists:
        raise ValueError(
            f"Activity not found: {activity_id}"
        )

    schedule_impact = analyze_schedule_impact(
        project_data,
        activity_id,
        shortage_days,
    )

    affected_activity = next(
        (
            item
            for item in schedule_impact["activity_changes"]
            if item["activity_id"] == activity_id
        ),
        None,
    )

    if affected_activity is None:
        raise ValueError(
            f"Schedule impact not found for activity: "
            f"{activity_id}"
        )

    return {
        "resource_id": resource_id,
        "activity_id": activity_id,
        "shortage_quantity": shortage_quantity,
        "shortage_days": shortage_days,
        "baseline_project_duration": (
            schedule_impact[
                "baseline_project_duration"
            ]
        ),
        "scenario_project_duration": (
            schedule_impact[
                "scenario_project_duration"
            ]
        ),
        "project_delay_days": (
            schedule_impact[
                "project_delay_days"
            ]
        ),
        "critical_path_before": (
            schedule_impact[
                "critical_path_before"
            ]
        ),
        "critical_path_after": (
            schedule_impact[
                "critical_path_after"
            ]
        ),
        "critical_path_changed": (
            schedule_impact[
                "critical_path_changed"
            ]
        ),
        "activity_es_change": (
            affected_activity["es_change"]
        ),
        "activity_ef_change": (
            affected_activity["ef_change"]
        ),
        "activity_float_before": (
            affected_activity["float_before"]
        ),
        "activity_float_after": (
            affected_activity["float_after"]
        ),
        "activity_float_change": (
            affected_activity["float_change"]
        ),
        "classification_before": (
            affected_activity[
                "classification_before"
            ]
        ),
        "classification_after": (
            affected_activity[
                "classification_after"
            ]
        ),
    }