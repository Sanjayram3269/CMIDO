from __future__ import annotations

from typing import Any


def analyze_resource_shortage(
    time_phased_demand: list[dict[str, Any]],
    available_quantity: float,
) -> dict[str, Any]:
    """
    Analyze whether a resource can satisfy its
    time-phased activity demand.

    Demands must represent the same resource/material.
    """

    if available_quantity < 0:
        raise ValueError(
            "available_quantity cannot be negative"
        )

    total_required = sum(
        item["quantity"]
        for item in time_phased_demand
    )

    remaining = available_quantity
    allocations = []

    for item in time_phased_demand:
        required = item["quantity"]

        allocated = min(
            required,
            remaining,
        )

        shortage = required - allocated

        allocations.append(
            {
                "activity_id": item["activity_id"],
                "activity_name": item["activity_name"],
                "quantity_required": required,
                "quantity_allocated": allocated,
                "shortage_quantity": shortage,
                "start_day": item["start_day"],
                "finish_day": item["finish_day"],
                "status": (
                    "FULLY_SUPPLIED"
                    if shortage == 0
                    else "SHORTAGE"
                ),
            }
        )

        remaining -= allocated

    total_allocated = sum(
        item["quantity_allocated"]
        for item in allocations
    )

    total_shortage = sum(
        item["shortage_quantity"]
        for item in allocations
    )

    affected_activities = [
        item
        for item in allocations
        if item["shortage_quantity"] > 0
    ]

    return {
        "available_quantity": available_quantity,
        "total_required": total_required,
        "total_allocated": total_allocated,
        "total_shortage": total_shortage,
        "remaining_quantity": remaining,
        "status": (
            "FEASIBLE"
            if total_shortage == 0
            else "SHORTAGE"
        ),
        "affected_activities": affected_activities,
        "allocations": allocations,
    }