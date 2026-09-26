from __future__ import annotations

from typing import Any

from src.construction.simulation.impact import (
    analyze_schedule_impact,
)


def analyze_float_consumption(
    project_data: dict[str, Any],
    activity_id: str,
    delay_days: int,
) -> dict[str, Any]:
    """
    Analyze how much of an activity's baseline float
    is consumed by a simulated delay.
    """

    if delay_days < 0:
        raise ValueError("delay_days cannot be negative")

    impact = analyze_schedule_impact(
        project_data,
        activity_id,
        delay_days,
    )

    activity = next(
        (
            item
            for item in impact["activity_changes"]
            if item["activity_id"] == activity_id
        ),
        None,
    )

    if activity is None:
        raise ValueError(
            f"Activity not found: {activity_id}"
        )

    baseline_float = activity["float_before"]

    float_consumed = min(
        delay_days,
        max(baseline_float, 0),
    )

    remaining_float = max(
        baseline_float - delay_days,
        0,
    )

    excess_delay = max(
        delay_days - baseline_float,
        0,
    )

    return {
        "activity_id": activity_id,
        "delay_days": delay_days,
        "baseline_float": baseline_float,
        "float_consumed": float_consumed,
        "remaining_float": remaining_float,
        "excess_delay": excess_delay,
        "project_delay_days": impact[
            "project_delay_days"
        ],
        "project_duration_before": impact[
            "baseline_project_duration"
        ],
        "project_duration_after": impact[
            "scenario_project_duration"
        ],
        "critical_path_changed": impact[
            "critical_path_changed"
        ],
    }