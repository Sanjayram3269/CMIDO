from __future__ import annotations

from typing import Any

from src.construction.quantity import (
    aggregate_material_requirements,
)
from src.construction.resource_shortage import (
    analyze_resource_shortage,
)


def build_resource_dashboard(
    project_data: dict[str, Any],
    available_resources: dict[str, float],
) -> dict[str, Any]:
    """
    Build frontend-ready resource dashboard data.

    available_resources maps material/resource IDs to
    available quantities.

    Example:
        {
            "M001": 500,
            "M002": 100,
        }
    """

    if "materials" not in project_data:
        raise ValueError(
            "Project data must contain 'materials'"
        )

    if "activity_materials" not in project_data:
        raise ValueError(
            "Project data must contain "
            "'activity_materials'"
        )

    requirements = (
        aggregate_material_requirements(
            project_data
        )
    )

    materials_by_id = {
        material["material_id"]: material
        for material in project_data["materials"]
    }

    activity_by_id = {
        activity["activity_id"]: activity
        for activity in project_data["activities"]
    }

    resource_rows = []

    for requirement in requirements:
        material_id = requirement[
            "material_id"
        ]

        available = available_resources.get(
            material_id,
            0,
        )

        demand = []

        for item in project_data[
            "activity_materials"
        ]:
            if item["material_id"] != material_id:
                continue

            activity = activity_by_id[
                item["activity_id"]
            ]

            demand.append(
                {
                    "activity_id": item[
                        "activity_id"
                    ],
                    "activity_name": activity[
                        "activity_name"
                    ],
                    "quantity": item[
                        "quantity_required"
                    ],
                    "unit": item["unit"],
                    "start_day": None,
                    "finish_day": None,
                }
            )

        shortage = analyze_resource_shortage(
            demand,
            available,
        )

        material = materials_by_id[
            material_id
        ]

        resource_rows.append(
            {
                "resource_id": material_id,
                "resource_name": material[
                    "material_name"
                ],
                "unit": requirement["unit"],
                "required_quantity": (
                    shortage["total_required"]
                ),
                "available_quantity": (
                    shortage["available_quantity"]
                ),
                "allocated_quantity": (
                    shortage["total_allocated"]
                ),
                "shortage_quantity": (
                    shortage["total_shortage"]
                ),
                "remaining_quantity": (
                    shortage["remaining_quantity"]
                ),
                "status": shortage["status"],
                "affected_activities": (
                    shortage[
                        "affected_activities"
                    ]
                ),
            }
        )

    feasible_count = sum(
        row["status"] == "FEASIBLE"
        for row in resource_rows
    )

    shortage_count = sum(
        row["status"] == "SHORTAGE"
        for row in resource_rows
    )

    return {
        "summary": {
            "total_resources": len(
                resource_rows
            ),
            "feasible_resources": (
                feasible_count
            ),
            "shortage_resources": (
                shortage_count
            ),
        },
        "resources": resource_rows,
    }