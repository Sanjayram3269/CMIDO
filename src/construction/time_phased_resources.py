from __future__ import annotations

from typing import Any


def build_time_phased_resource_demand(
    project_data: dict[str, Any],
    schedule: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build time-phased material/resource demand by combining:

    1. Activity material requirements
    2. Material definitions
    3. Activity schedule

    Existing CMIDO schema uses:
        quantity_required
    for activity_materials.
    """

    activities = {
        item["activity_id"]: item
        for item in project_data["activities"]
    }

    materials = {
        item["material_id"]: item
        for item in project_data["materials"]
    }

    schedule_by_activity = {
        item["activity_id"]: item
        for item in schedule
    }

    result = []

    for requirement in project_data["activity_materials"]:
        activity_id = requirement["activity_id"]
        material_id = requirement["material_id"]

        if activity_id not in activities:
            raise ValueError(
                f"Unknown activity: {activity_id}"
            )

        if material_id not in materials:
            raise ValueError(
                f"Unknown material: {material_id}"
            )

        if activity_id not in schedule_by_activity:
            raise ValueError(
                f"No schedule found for activity: {activity_id}"
            )

        activity = activities[activity_id]
        material = materials[material_id]
        scheduled = schedule_by_activity[activity_id]

        result.append(
            {
                "activity_id": activity_id,
                "activity_name": activity["activity_name"],
                "material_id": material_id,
                "material_name": material["material_name"],
                "quantity": requirement["quantity_required"],
                "unit": requirement["unit"],
                "start_day": scheduled["es"],
                "finish_day": scheduled["ef"],
            }
        )

    return result