from __future__ import annotations

from typing import Any

from src.construction.integrated_analysis import (
    analyze_project,
)


def build_dashboard_data(
    project_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert CMIDO's integrated analysis into a
    frontend-ready dashboard data structure.

    This layer does not perform domain calculations.
    It only organizes existing analysis results.
    """

    analysis = analyze_project(project_data)

    schedule = analysis["schedule"]
    activities = analysis["activities"]
    materials = analysis["materials"]

    critical_ids = set(
        schedule["critical_path"]
    )

    critical_count = len(
        schedule["critical_activities"]
    )

    non_critical_count = len(
        schedule["non_critical_activities"]
    )

    schedule_rows = []

    for activity in activities:
        schedule_rows.append(
            {
                "activity_id": activity[
                    "activity_id"
                ],
                "activity_name": activity[
                    "activity_name"
                ],
                "duration_days": activity[
                    "duration_days"
                ],
                "is_critical": (
                    activity["activity_id"]
                    in critical_ids
                ),
            }
        )

    material_rows = []

    for material in materials[
        "requirements"
    ]:
        material_rows.append(
            {
                "material_name": material[
                    "material_name"
                ],
                "material_id": material[
                    "material_id"
                ],
                "total_quantity": material[
                    "total_quantity"
                ],
                "unit": material["unit"],
            }
        )

    return {
        "overview": {
            "project_id": analysis[
                "project"
            ]["project_id"],
            "project_name": analysis[
                "project"
            ]["project_name"],
            "location": analysis[
                "project"
            ]["location"],
            "project_duration_days": (
                schedule["project_duration"]
            ),
            "critical_path_duration_days": (
                schedule[
                    "critical_path_duration"
                ]
            ),
            "total_activities": len(
                activities
            ),
            "critical_activities": (
                critical_count
            ),
            "non_critical_activities": (
                non_critical_count
            ),
            "total_material_types": (
                materials[
                    "total_material_types"
                ]
            ),
        },
        "schedule": {
            "project_duration_days": (
                schedule["project_duration"]
            ),
            "critical_path": schedule[
                "critical_path"
            ],
            "activities": schedule_rows,
        },
        "materials": {
            "total_material_types": (
                materials[
                    "total_material_types"
                ]
            ),
            "materials": material_rows,
        },
        "resources": {
            "status": "NOT_ANALYZED",
            "message": (
                "Resource dashboard data will be "
                "populated by the resource integration "
                "layer."
            ),
        },
    }