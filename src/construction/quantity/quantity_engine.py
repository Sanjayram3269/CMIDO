from __future__ import annotations

from collections import defaultdict
from typing import Any


def calculate_activity_material_requirements(
    project_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Convert activity-material mappings into validated
    material requirements for each construction activity.

    Returns one record for every activity-material mapping.
    """

    activities = {
        activity["activity_id"]: activity
        for activity in project_data["activities"]
    }

    materials = {
        material["material_id"]: material
        for material in project_data["materials"]
    }

    requirements: list[dict[str, Any]] = []

    for mapping in project_data["activity_materials"]:
        activity_id = mapping["activity_id"]
        material_id = mapping["material_id"]

        if activity_id not in activities:
            raise ValueError(
                f"Unknown activity: {activity_id}"
            )

        if material_id not in materials:
            raise ValueError(
                f"Unknown material: {material_id}"
            )

        quantity = mapping["quantity_required"]

        if quantity < 0:
            raise ValueError(
                f"Material quantity cannot be negative: "
                f"{activity_id} -> {material_id}"
            )

        requirements.append(
            {
                "activity_id": activity_id,
                "activity_name": activities[activity_id]["activity_name"],
                "material_id": material_id,
                "material_name": materials[material_id]["material_name"],
                "quantity_required": quantity,
                "unit": mapping["unit"],
            }
        )

    return requirements


def aggregate_material_requirements(
    project_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Aggregate material requirements across all activities.
    """

    requirements = calculate_activity_material_requirements(
        project_data
    )

    totals: dict[str, float] = defaultdict(float)

    material_names: dict[str, str] = {}
    units: dict[str, str] = {}

    for requirement in requirements:
        material_id = requirement["material_id"]

        totals[material_id] += requirement["quantity_required"]

        material_names[material_id] = requirement["material_name"]
        units[material_id] = requirement["unit"]

    return [
        {
            "material_id": material_id,
            "material_name": material_names[material_id],
            "total_quantity": quantity,
            "unit": units[material_id],
        }
        for material_id, quantity in totals.items()
    ]
