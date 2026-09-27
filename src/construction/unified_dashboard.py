from __future__ import annotations

from typing import Any

from src.construction.dashboard import build_dashboard_data
from src.construction.resource_dashboard import (
    build_resource_dashboard,
)


def build_unified_dashboard(
    project_data: dict[str, Any],
    available_resources: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Build the unified CMIDO project dashboard.

    This function acts as the product-level orchestration
    layer. Existing deterministic engines remain responsible
    for their individual calculations.

    Dashboard domains:

    1. Project overview
    2. Schedule / CPM
    3. Materials
    4. Resource feasibility
    """

    if not isinstance(project_data, dict):
        raise ValueError(
            "project_data must be a dictionary"
        )

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

    if "materials" not in project_data:
        raise ValueError(
            "Project data must contain 'materials'"
        )

    if "activity_materials" not in project_data:
        raise ValueError(
            "Project data must contain "
            "'activity_materials'"
        )

    # ---------------------------------------------------------
    # Core deterministic dashboard
    # ---------------------------------------------------------

    dashboard = build_dashboard_data(
        project_data
    )

    # ---------------------------------------------------------
    # Resource analysis
    # ---------------------------------------------------------

    if available_resources is None:
        available_resources = {}

    resource_dashboard = build_resource_dashboard(
        project_data,
        available_resources,
    )

    # ---------------------------------------------------------
    # Unified product response
    # ---------------------------------------------------------

    overview = dashboard["overview"]

        # ---------------------------------------------------------
    # Overall project status
    # ---------------------------------------------------------

    status = (
        "FEASIBLE"
        if resource_dashboard["summary"][
            "shortage_resources"
        ] == 0
        else "RESOURCE_SHORTAGE"
    )

    # ---------------------------------------------------------
    # Unified product response
    # ---------------------------------------------------------

    return {
        "project": {
            "project_id": overview[
                "project_id"
            ],
            "project_name": overview[
                "project_name"
            ],
        },

        "overview": overview,

        "schedule": dashboard[
            "schedule"
        ],

        "materials": dashboard[
            "materials"
        ],

        "resources": {
            "summary": resource_dashboard[
                "summary"
            ],
            "resources": resource_dashboard[
                "resources"
            ],
        },

        "status": status,
    }