from __future__ import annotations

from typing import Any

from src.construction.quantity import (
    aggregate_material_requirements,
)
from src.construction.scheduling import (
    calculate_critical_path,
)


def analyze_project(
    project_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Run the core CMIDO deterministic analysis engines
    and return one unified project-level result.

    This function intentionally acts as an orchestration
    layer. Individual domain calculations remain in their
    existing modules.
    """

    if "project" not in project_data:
        raise ValueError(
            "Project data must contain 'project'"
        )

    if "activities" not in project_data:
        raise ValueError(
            "Project data must contain 'activities'"
        )

    if "dependencies" not in project_data:
        raise ValueError(
            "Project data must contain 'dependencies'"
        )

    if "activity_materials" not in project_data:
        raise ValueError(
            "Project data must contain 'activity_materials'"
        )

    if "materials" not in project_data:
        raise ValueError(
            "Project data must contain 'materials'"
        )

    project = project_data["project"]

    schedule = calculate_critical_path(
        project_data
    )

    material_requirements = (
        aggregate_material_requirements(
            project_data
        )
    )

    activities = project_data["activities"]

    critical_ids = set(
        schedule["critical_path"]
    )

    activity_summary = []

    for activity in activities:
        activity_id = activity["activity_id"]

        activity_summary.append(
            {
                "activity_id": activity_id,
                "activity_name": activity[
                    "activity_name"
                ],
                "duration_days": activity[
                    "duration_days"
                ],
                "is_critical": (
                    activity_id in critical_ids
                ),
            }
        )

    return {
        "project": {
            "project_id": project[
                "project_id"
            ],
            "project_name": project[
                "project_name"
            ],
            "location": project.get(
                "location"
            ),
        },
        "schedule": {
            "project_duration": schedule[
                "project_duration"
            ],
            "critical_path_duration": schedule[
                "critical_path_duration"
            ],
            "critical_path": schedule[
                "critical_path"
            ],
            "critical_activities": schedule[
                "critical_activities"
            ],
            "non_critical_activities": schedule[
                "non_critical_activities"
            ],
        },
        "activities": activity_summary,
        "materials": {
            "total_material_types": len(
                material_requirements
            ),
            "requirements": (
                material_requirements
            ),
        },
    }