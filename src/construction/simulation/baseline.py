from __future__ import annotations

from typing import Any

from src.construction.scheduling import (
    calculate_critical_path,
)


def create_baseline_snapshot(
    project_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Create an immutable-style snapshot of the current
    project scheduling state.

    The original project_data is not modified.
    """

    result = calculate_critical_path(project_data)

    activities = {}

    for item in result["critical_activities"]:
        activities[item["activity_id"]] = {
            "activity_id": item["activity_id"],
            "activity_name": item["activity_name"],
            "duration_days": item["duration_days"],
            "es": item["es"],
            "ef": item["ef"],
            "ls": item["ls"],
            "lf": item["lf"],
            "total_float": item["total_float"],
            "classification": item["classification"],
        }

    for item in result["non_critical_activities"]:
        activities[item["activity_id"]] = {
            "activity_id": item["activity_id"],
            "activity_name": item["activity_name"],
            "duration_days": item["duration_days"],
            "es": item["es"],
            "ef": item["ef"],
            "ls": item["ls"],
            "lf": item["lf"],
            "total_float": item["total_float"],
            "classification": item["classification"],
        }

    return {
        "project_duration": result["project_duration"],
        "critical_path_duration": result["critical_path_duration"],
        "critical_path": list(result["critical_path"]),
        "activities": activities,
    }