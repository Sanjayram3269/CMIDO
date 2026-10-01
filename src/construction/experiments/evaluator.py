from __future__ import annotations

from typing import Any

from src.construction.simulation.impact import (
    analyze_schedule_impact,
)


def evaluate_schedule_scenario(
    project_data: dict[str, Any],
    activity_id: str,
    delay_days: int,
) -> dict[str, Any]:
    """
    Evaluate one experiment scenario using the real CMIDO
    schedule-impact engine.

    This adapter keeps the experiment framework independent
    from the underlying construction-domain implementation.
    """

    if not isinstance(project_data, dict):
        raise ValueError(
            "project_data must be a dictionary"
        )

    if not isinstance(activity_id, str) or not activity_id.strip():
        raise ValueError(
            "activity_id must be a non-empty string"
        )

    if not isinstance(delay_days, int):
        raise ValueError(
            "delay_days must be an integer"
        )

    if delay_days < 0:
        raise ValueError(
            "delay_days cannot be negative"
        )

    return analyze_schedule_impact(
        project_data,
        activity_id,
        delay_days,
    )
