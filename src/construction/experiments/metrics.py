from __future__ import annotations

from typing import Any


def summarize_schedule_impact(
    baseline_duration: int,
    scenario_duration: int,
) -> dict[str, Any]:
    """Compute transparent project-level schedule metrics."""
    if not isinstance(baseline_duration, int):
        raise ValueError("baseline_duration must be an integer")
    if not isinstance(scenario_duration, int):
        raise ValueError("scenario_duration must be an integer")

    delay = scenario_duration - baseline_duration

    return {
        "baseline_duration_days": baseline_duration,
        "scenario_duration_days": scenario_duration,
        "project_delay_days": delay,
        "delay_present": delay > 0,
        "relative_delay": (
            delay / baseline_duration if baseline_duration else 0.0
        ),
    }


def summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Extract standard metrics from a CMIDO schedule-impact result."""
    if not isinstance(result, dict):
        raise ValueError("result must be a dictionary")

    if "baseline_project_duration" not in result:
        raise ValueError("result missing baseline_project_duration")
    if "scenario_project_duration" not in result:
        raise ValueError("result missing scenario_project_duration")

    return summarize_schedule_impact(
        result["baseline_project_duration"],
        result["scenario_project_duration"],
    )
