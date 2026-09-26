from __future__ import annotations

from typing import Any

from .quantity_engine import calculate_activity_material_requirements


def build_material_demand_report(
    project_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Build a traceable material-demand report.

    Each material contains its project-level total and
    the activities contributing to that total.
    """

    requirements = calculate_activity_material_requirements(
        project_data
    )

    report: dict[str, dict[str, Any]] = {}

    for requirement in requirements:
        material_id = requirement["material_id"]

        if material_id not in report:
            report[material_id] = {
                "material_id": material_id,
                "material_name": requirement["material_name"],
                "unit": requirement["unit"],
                "total_quantity": 0.0,
                "activity_count": 0,
                "activities": [],
            }

        material = report[material_id]

        material["total_quantity"] += (
            requirement["quantity_required"]
        )

        material["activity_count"] += 1

        material["activities"].append(
            {
                "activity_id": requirement["activity_id"],
                "activity_name": requirement["activity_name"],
                "quantity": requirement["quantity_required"],
                "unit": requirement["unit"],
            }
        )

    return list(report.values())


def get_material_demand(
    project_data: dict[str, Any],
    material_id: str,
) -> dict[str, Any]:
    """
    Return the demand report for one material.
    """

    report = build_material_demand_report(project_data)

    for material in report:
        if material["material_id"] == material_id:
            return material

    raise ValueError(
        f"Material not found in demand report: {material_id}"
    )
