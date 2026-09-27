from __future__ import annotations

from typing import Any


def allocate_resource(
    available_quantity: float,
    demands: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Allocate an available resource sequentially across
    activity demands.

    Each demand must contain:
        activity_id
        quantity

    Allocation stops when available quantity is exhausted.
    """

    if available_quantity < 0:
        raise ValueError(
            "available_quantity cannot be negative"
        )

    remaining = available_quantity
    allocations = []

    for demand in demands:
        activity_id = demand["activity_id"]
        required = demand["quantity"]

        if required < 0:
            raise ValueError(
                f"Negative demand for activity {activity_id}"
            )

        allocated = min(
            required,
            remaining,
        )

        shortage = required - allocated

        allocations.append(
            {
                "activity_id": activity_id,
                "required_quantity": required,
                "allocated_quantity": allocated,
                "shortage_quantity": shortage,
            }
        )

        remaining -= allocated

    total_required = sum(
        item["required_quantity"]
        for item in allocations
    )

    total_allocated = sum(
        item["allocated_quantity"]
        for item in allocations
    )

    total_shortage = sum(
        item["shortage_quantity"]
        for item in allocations
    )

    return {
        "available_quantity": available_quantity,
        "total_required": total_required,
        "total_allocated": total_allocated,
        "total_shortage": total_shortage,
        "remaining_quantity": remaining,
        "fully_satisfied": total_shortage == 0,
        "allocations": allocations,
    }