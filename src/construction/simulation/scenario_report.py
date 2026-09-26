from __future__ import annotations

from typing import Any

from src.construction.simulation.float_analysis import (
    analyze_float_consumption,
)
from src.construction.simulation.impact import (
    analyze_schedule_impact,
)


def generate_scenario_report(
    project_data: dict[str, Any],
    activity_id: str,
    delay_days: int,
) -> dict[str, Any]:
    """
    Generate a frontend-ready construction delay scenario report.

    Uses the existing CMIDO simulation and impact engines.
    """

    if delay_days < 0:
        raise ValueError("delay_days cannot be negative")

    float_result = analyze_float_consumption(
        project_data,
        activity_id,
        delay_days,
    )

    impact = analyze_schedule_impact(
        project_data,
        activity_id,
        delay_days,
    )

    activity = next(
        (
            item
            for item in project_data["activities"]
            if item["activity_id"] == activity_id
        ),
        None,
    )

    if activity is None:
        raise ValueError(
            f"Activity not found: {activity_id}"
        )

    return {
        "scenario": {
            "activity_id": activity_id,
            "activity_name": activity["activity_name"],
            "delay_days": delay_days,
        },

        "project": {
            "baseline_duration": float_result[
                "project_duration_before"
            ],
            "scenario_duration": float_result[
                "project_duration_after"
            ],
            "project_delay_days": float_result[
                "project_delay_days"
            ],
        },

        "float": {
            "baseline_float": float_result[
                "baseline_float"
            ],
            "float_consumed": float_result[
                "float_consumed"
            ],
            "remaining_float": float_result[
                "remaining_float"
            ],
            "excess_delay": float_result[
                "excess_delay"
            ],
        },

        "critical_path": {
            "changed": float_result[
                "critical_path_changed"
            ],
            "before": impact[
                "critical_path_before"
            ],
            "after": impact[
                "critical_path_after"
            ],
        },

        "affected_activities": impact[
            "affected_activities"
        ],

        "activity_changes": impact[
            "activity_changes"
        ],
    }