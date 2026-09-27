from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.construction.time_phased_resources import (
    build_time_phased_resource_demand,
)
from src.construction.resource_shortage import (
    analyze_resource_shortage,
)


def build_time_phased_resource_integration(
    project_data: dict[str, Any],
    schedule: list[dict[str, Any]],
    available_resources: dict[str, float],
) -> dict[str, Any]:
    """
    Integrate CMIDO's time-phased resource demand
    with available resource quantities.

    This function intentionally reuses the existing:

        build_time_phased_resource_demand()
        analyze_resource_shortage()

    implementations.

    It does not recalculate material requirements.
    """

    if not isinstance(schedule, list):
        raise ValueError(
            "schedule must be a list"
        )

    if not isinstance(available_resources, dict):
        raise ValueError(
            "available_resources must be a dictionary"
        )

    demand = build_time_phased_resource_demand(
        project_data,
        schedule,
    )

    grouped: dict[str, list[dict[str, Any]]] = (
        defaultdict(list)
    )

    for item in demand:
        grouped[
            item["material_id"]
        ].append(item)

    materials = {
        item["material_id"]: item
        for item in project_data["materials"]
    }

    resource_results = []

    for material_id, material_demand in grouped.items():
        available = available_resources.get(
            material_id,
            0,
        )

        shortage = analyze_resource_shortage(
            material_demand,
            available,
        )

        material = materials[material_id]

        resource_results.append(
            {
                "resource_id": material_id,
                "resource_name": material[
                    "material_name"
                ],
                "unit": material_demand[0]["unit"],
                "available_quantity": (
                    shortage[
                        "available_quantity"
                    ]
                ),
                "total_required": (
                    shortage["total_required"]
                ),
                "total_allocated": (
                    shortage["total_allocated"]
                ),
                "total_shortage": (
                    shortage["total_shortage"]
                ),
                "remaining_quantity": (
                    shortage["remaining_quantity"]
                ),
                "status": shortage["status"],
                "allocations": shortage[
                    "allocations"
                ],
                "affected_activities": shortage[
                    "affected_activities"
                ],
            }
        )

    total_resources = len(resource_results)

    feasible_resources = sum(
        item["status"] == "FEASIBLE"
        for item in resource_results
    )

    shortage_resources = sum(
        item["status"] == "SHORTAGE"
        for item in resource_results
    )

    total_required = sum(
        item["total_required"]
        for item in resource_results
    )

    total_allocated = sum(
        item["total_allocated"]
        for item in resource_results
    )

    total_shortage = sum(
        item["total_shortage"]
        for item in resource_results
    )

    return {
        "summary": {
            "total_resources": total_resources,
            "feasible_resources": feasible_resources,
            "shortage_resources": shortage_resources,
            "total_required": total_required,
            "total_allocated": total_allocated,
            "total_shortage": total_shortage,
        },
        "resources": resource_results,
    }