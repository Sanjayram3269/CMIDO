from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.construction.scheduling import calculate_critical_path


def simulate_activity_delay(
    project_data: dict[str, Any],
    activity_id: str,
    delay_days: int,
) -> dict[str, Any]:
    """
    Simulate a delay to one activity.

    The original project is never modified.
    """

    if delay_days < 0:
        raise ValueError("delay_days cannot be negative")

    baseline = calculate_critical_path(project_data)

    project = deepcopy(project_data)

    activity = next(
        (
            item
            for item in project["activities"]
            if item["activity_id"] == activity_id
        ),
        None,
    )

    if activity is None:
        raise ValueError(
            f"Activity not found: {activity_id}"
        )

    original_duration = activity["duration_days"]

    activity["duration_days"] = (
        original_duration + delay_days
    )

    scenario = calculate_critical_path(project)

    return {
        "activity_id": activity_id,
        "delay_days": delay_days,
        "original_duration": original_duration,
        "new_duration": activity["duration_days"],
        "baseline_project_duration": baseline[
            "project_duration"
        ],
        "scenario_project_duration": scenario[
            "project_duration"
        ],
        "project_delay_days": (
            scenario["project_duration"]
            - baseline["project_duration"]
        ),
        "baseline_critical_path": baseline[
            "critical_path"
        ],
        "scenario_critical_path": scenario[
            "critical_path"
        ],
        "critical_path_changed": (
            baseline["critical_path"]
            != scenario["critical_path"]
        ),
        "critical_path_duration": scenario[
            "critical_path_duration"
        ],
        "activities": (
            scenario["critical_activities"]
            + scenario["non_critical_activities"]
        ),
    }