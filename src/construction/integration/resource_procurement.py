from __future__ import annotations

from datetime import date
from typing import Any

from src.construction.quantity.procurement import (
    evaluate_procurement_feasibility,
)
from src.construction.resource_dashboard import (
    build_resource_dashboard,
)
from src.construction.scheduling import (
    calculate_critical_path,
)


def build_resource_procurement_context(
    project_data: dict[str, Any],
    available_resources: dict[str, float],
) -> dict[str, Any]:
    """
    Build the CMIDO 7C-B resource + procurement context.

    Flow:

        Project Data
             ↓
        CPM Schedule
             ↓
        Resource Availability
             ↓
        Procurement Feasibility
             ↓
        Integrated Resource/Procurement Context

    This layer does not simulate schedule delays.

    It only establishes whether the required material
    quantities can be supported by currently available
    resources and procurement capacity/lead time.
    """

    if not isinstance(project_data, dict):
        raise ValueError(
            "project_data must be a dictionary"
        )

    if not isinstance(available_resources, dict):
        raise ValueError(
            "available_resources must be a dictionary"
        )

    # ---------------------------------------------------------
    # 1. Baseline CPM schedule
    # ---------------------------------------------------------

    schedule = calculate_critical_path(
        project_data
    )

    # ---------------------------------------------------------
    # 2. Resource availability
    # ---------------------------------------------------------

    resource_context = build_resource_dashboard(
        project_data,
        available_resources,
    )

    # ---------------------------------------------------------
    # 3. Build activity schedule required by procurement
    # ---------------------------------------------------------

    activity_schedule: dict[
        str,
        dict[str, date],
    ] = {}

    for activity in (
        schedule["critical_activities"]
        + schedule["non_critical_activities"]
    ):
        activity_schedule[
            activity["activity_id"]
        ] = {
            "start": _day_to_date(
                activity["es"]
            ),
            "finish": _day_to_date(
                activity["ef"]
            ),
        }

    # ---------------------------------------------------------
    # 4. Procurement feasibility
    # ---------------------------------------------------------

    procurement = evaluate_procurement_feasibility(
        project_data,
        activity_schedule,
    )

    # ---------------------------------------------------------
    # 5. Couple resource status with procurement status
    # ---------------------------------------------------------

    resource_by_id = {
        item["resource_id"]: item
        for item in resource_context[
            "resources"
        ]
    }

    integrated_procurement = []

    for item in procurement:
        resource = resource_by_id.get(
            item["material_id"]
        )

        integrated_procurement.append(
            {
                "activity_id": item[
                    "activity_id"
                ],
                "material_id": item[
                    "material_id"
                ],
                "material_name": item[
                    "material_name"
                ],
                "required_quantity": item[
                    "required_quantity"
                ],
                "unit": item["unit"],
                "required_date": item[
                    "required_date"
                ],
                "procurement_status": item[
                    "status"
                ],
                "supplier_id": item[
                    "supplier_id"
                ],
                "supplier_name": item[
                    "supplier_name"
                ],
                "available_capacity": item[
                    "available_capacity"
                ],
                "lead_time_days": item[
                    "lead_time_days"
                ],
                "latest_order_date": item[
                    "latest_order_date"
                ],
                "resource_status": (
                    resource["status"]
                    if resource
                    else "UNKNOWN"
                ),
                "resource_available_quantity": (
                    resource[
                        "available_quantity"
                    ]
                    if resource
                    else 0
                ),
                "resource_shortage_quantity": (
                    resource[
                        "shortage_quantity"
                    ]
                    if resource
                    else 0
                ),
            }
        )

    return {
        "schedule": {
            "project_duration_days": (
                schedule["project_duration"]
            ),
            "critical_path": (
                schedule["critical_path"]
            ),
        },
        "resources": resource_context,
        "procurement": {
            "total_requirements": len(
                integrated_procurement
            ),
            "requirements": (
                integrated_procurement
            ),
        },
    }


def _day_to_date(
    day: int,
) -> date:
    """
    Convert deterministic CPM day numbering into
    a date-like value for the procurement engine.

    Day 0 is represented as 1970-01-01.

    The actual project calendar can be introduced later
    without changing the integration contract.
    """

    return date(
        1970,
        1,
        1,
    ).fromordinal(
        date(1970, 1, 1).toordinal()
        + day
    )