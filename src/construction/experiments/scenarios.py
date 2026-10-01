from __future__ import annotations

from typing import Any


def validate_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize one deterministic experiment scenario."""
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be a dictionary")

    activity_id = scenario.get("activity_id")
    delay_days = scenario.get("delay_days", 0)

    if not isinstance(activity_id, str) or not activity_id.strip():
        raise ValueError("scenario activity_id must be a non-empty string")
    if not isinstance(delay_days, int):
        raise ValueError("scenario delay_days must be an integer")
    if delay_days < 0:
        raise ValueError("scenario delay_days cannot be negative")

    return {
        "activity_id": activity_id,
        "delay_days": delay_days,
    }


def build_delay_scenarios(
    activity_id: str,
    delay_days: list[int],
) -> list[dict[str, Any]]:
    """Create a deterministic set of single-activity delay scenarios."""
    if not isinstance(activity_id, str) or not activity_id.strip():
        raise ValueError("activity_id must be a non-empty string")
    if not isinstance(delay_days, list):
        raise ValueError("delay_days must be a list")

    return [
        validate_scenario({"activity_id": activity_id, "delay_days": days})
        for days in delay_days
    ]
