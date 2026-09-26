from __future__ import annotations

from datetime import date
from typing import Any

from .quantity_engine import calculate_activity_material_requirements


def build_time_phased_demand(
    project_data: dict[str, Any],
    activity_schedule: dict[str, dict[str, date]],
) -> list[dict[str, Any]]:
    """
    Combine material requirements with activity schedule dates.

    activity_schedule format:

    {
        "A003": {
            "start": date(...),
            "finish": date(...),
        }
    }

    Scheduling logic itself is intentionally kept outside this
    module. The CPM engine will provide the dates later.
    """

    requirements = calculate_activity_material_requirements(
        project_data
    )

    activity_ids = {
        activity["activity_id"]
        for activity in project_data["activities"]
    }

    for activity_id in activity_schedule:
        if activity_id not in activity_ids:
            raise ValueError(
                f"Schedule contains unknown activity: {activity_id}"
            )

    result: list[dict[str, Any]] = []

    for requirement in requirements:
        activity_id = requirement["activity_id"]

        if activity_id not in activity_schedule:
            raise ValueError(
                f"Missing schedule for activity: {activity_id}"
            )

        schedule = activity_schedule[activity_id]

        if "start" not in schedule or "finish" not in schedule:
            raise ValueError(
                f"Schedule for {activity_id} must contain "
                "'start' and 'finish'"
            )

        start = schedule["start"]
        finish = schedule["finish"]

        if finish < start:
            raise ValueError(
                f"Finish date cannot be before start date: "
                f"{activity_id}"
            )

        result.append(
            {
                "activity_id": activity_id,
                "activity_name": requirement["activity_name"],
                "material_id": requirement["material_id"],
                "material_name": requirement["material_name"],
                "quantity": requirement["quantity_required"],
                "unit": requirement["unit"],
                "start": start,
                "finish": finish,
            }
        )

    return result


def aggregate_time_phased_demand(
    project_data: dict[str, Any],
    activity_schedule: dict[str, dict[str, date]],
) -> list[dict[str, Any]]:
    """
    Aggregate material demand by scheduled activity window.
    """

    demand = build_time_phased_demand(
        project_data,
        activity_schedule,
    )

    result: list[dict[str, Any]] = []

    for item in demand:
        result.append(
            {
                "material_id": item["material_id"],
                "material_name": item["material_name"],
                "quantity": item["quantity"],
                "unit": item["unit"],
                "activity_id": item["activity_id"],
                "activity_name": item["activity_name"],
                "start": item["start"],
                "finish": item["finish"],
            }
        )

    return result
