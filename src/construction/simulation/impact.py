from __future__ import annotations

from typing import Any

from src.construction.scheduling import calculate_critical_path
from .delay import simulate_activity_delay


def analyze_schedule_impact(
    project_data: dict[str, Any],
    activity_id: str,
    delay_days: int,
) -> dict[str, Any]:
    """
    Compare the baseline schedule against a delayed scenario.
    """

    baseline = calculate_critical_path(project_data)

    scenario = simulate_activity_delay(
        project_data,
        activity_id,
        delay_days,
    )

    baseline_activities = {
        item["activity_id"]: item
        for item in (
            baseline["critical_activities"]
            + baseline["non_critical_activities"]
        )
    }

    scenario_activities = {
        item["activity_id"]: item
        for item in scenario["activities"]
    }

    activity_changes = []

    for current_id in baseline_activities:
        before = baseline_activities[current_id]
        after = scenario_activities[current_id]

        activity_changes.append(
            {
                "activity_id": current_id,
                "activity_name": before["activity_name"],
                "es_change": after["es"] - before["es"],
                "ef_change": after["ef"] - before["ef"],
                "ls_change": after["ls"] - before["ls"],
                "lf_change": after["lf"] - before["lf"],
                "float_before": before["total_float"],
                "float_after": after["total_float"],
                "float_change": (
                    after["total_float"]
                    - before["total_float"]
                ),
                "classification_before": (
                    before["classification"]
                ),
                "classification_after": (
                    after["classification"]
                ),
            }
        )

    affected = [
        item
        for item in activity_changes
        if (
            item["es_change"] != 0
            or item["ef_change"] != 0
            or item["ls_change"] != 0
            or item["lf_change"] != 0
            or item["float_change"] != 0
            or (
                item["classification_before"]
                != item["classification_after"]
            )
        )
    ]

    return {
        "activity_id": activity_id,
        "delay_days": delay_days,
        "baseline_project_duration": baseline[
            "project_duration"
        ],
        "scenario_project_duration": scenario[
            "scenario_project_duration"
        ],
        "project_delay_days": scenario[
            "project_delay_days"
        ],
        "critical_path_before": baseline[
            "critical_path"
        ],
        "critical_path_after": scenario[
            "scenario_critical_path"
        ],
        "critical_path_changed": scenario[
            "critical_path_changed"
        ],
        "affected_activities": affected,
        "activity_changes": activity_changes,
    }