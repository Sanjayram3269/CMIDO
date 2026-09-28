from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .time_phased import build_time_phased_demand


def _supplier_material_map(
    project_data: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """
    Build a material -> supplier mapping.

    Each supplier-material relationship contains the commercial
    and operational procurement attributes required by the
    procurement feasibility engine.
    """

    suppliers = {
        supplier["supplier_id"]: supplier
        for supplier in project_data["suppliers"]
    }

    result: dict[str, list[dict[str, Any]]] = {}

    for mapping in project_data["supplier_materials"]:
        supplier_id = mapping["supplier_id"]
        material_id = mapping["material_id"]

        if supplier_id not in suppliers:
            raise ValueError(
                f"Unknown supplier: {supplier_id}"
            )

        supplier = suppliers[supplier_id]

        result.setdefault(material_id, []).append(
            {
                "supplier_id": supplier_id,
                "supplier_name": supplier["supplier_name"],
                "capacity": mapping["capacity"],
                "lead_time_days": mapping["lead_time_days"],
                "unit_price": mapping["unit_price"],
                "minimum_order_quantity": (
                    mapping["minimum_order_quantity"]
                ),
            }
        )

    return result


def evaluate_procurement_feasibility(
    project_data: dict[str, Any],
    activity_schedule: dict[str, dict[str, date]],
) -> list[dict[str, Any]]:
    """
    Evaluate whether supplier capacity and lead time can satisfy
    each time-phased material requirement.

    This function is intended for time-phased project-level
    procurement analysis.

    It evaluates:

    - material requirement
    - supplier mapping
    - supplier capacity
    - lead time
    - required-by date
    - latest order date

    This is a deterministic feasibility analysis, not an
    optimization algorithm.
    """

    demand = build_time_phased_demand(
        project_data,
        activity_schedule,
    )

    supplier_map = _supplier_material_map(project_data)

    results: list[dict[str, Any]] = []

    for item in demand:
        material_id = item["material_id"]
        required_quantity = item["quantity"]
        required_date = item["start"]

        suppliers = supplier_map.get(
            material_id,
            [],
        )

        if not suppliers:
            results.append(
                {
                    "activity_id": item["activity_id"],
                    "material_id": material_id,
                    "material_name": item["material_name"],
                    "required_quantity": required_quantity,
                    "unit": item["unit"],
                    "required_date": required_date,
                    "status": "NO_SUPPLIER",
                    "supplier_id": None,
                    "supplier_name": None,
                    "available_capacity": 0,
                    "lead_time_days": None,
                    "latest_order_date": None,
                }
            )
            continue

        selected_supplier = None

        for supplier in suppliers:
            if supplier["capacity"] >= required_quantity:
                selected_supplier = supplier
                break

        if selected_supplier is None:
            results.append(
                {
                    "activity_id": item["activity_id"],
                    "material_id": material_id,
                    "material_name": item["material_name"],
                    "required_quantity": required_quantity,
                    "unit": item["unit"],
                    "required_date": required_date,
                    "status": "INSUFFICIENT_CAPACITY",
                    "supplier_id": None,
                    "supplier_name": None,
                    "available_capacity": max(
                        supplier["capacity"]
                        for supplier in suppliers
                    ),
                    "lead_time_days": None,
                    "latest_order_date": None,
                }
            )
            continue

        lead_time = selected_supplier["lead_time_days"]

        latest_order_date = (
            required_date
            - timedelta(days=lead_time)
        )

        results.append(
            {
                "activity_id": item["activity_id"],
                "material_id": material_id,
                "material_name": item["material_name"],
                "required_quantity": required_quantity,
                "unit": item["unit"],
                "required_date": required_date,
                "status": "FEASIBLE",
                "supplier_id": selected_supplier[
                    "supplier_id"
                ],
                "supplier_name": selected_supplier[
                    "supplier_name"
                ],
                "available_capacity": selected_supplier[
                    "capacity"
                ],
                "lead_time_days": lead_time,
                "latest_order_date": latest_order_date,
            }
        )

    return results


def analyze_procurement_feasibility(
    project_data: dict[str, Any],
    material_id: str,
    quantity: float,
) -> dict[str, Any]:
    """
    Analyze procurement feasibility for one material.

    Evaluates every mapped supplier against:

    - supplier capacity
    - minimum order quantity
    - unit price
    - estimated procurement quantity
    - estimated procurement cost

    Returns a deterministic supplier-by-supplier analysis.
    """

    if quantity < 0:
        raise ValueError(
            "quantity cannot be negative"
        )

    materials = {
        material["material_id"]: material
        for material in project_data["materials"]
    }

    if material_id not in materials:
        raise ValueError(
            f"Unknown material: {material_id}"
        )

    material = materials[material_id]

    supplier_map = _supplier_material_map(
        project_data
    )

    suppliers = supplier_map.get(
        material_id,
        [],
    )

    supplier_results = []

    for supplier in suppliers:
        capacity = supplier["capacity"]
        moq = supplier[
            "minimum_order_quantity"
        ]
        unit_price = supplier["unit_price"]

        capacity_sufficient = (
            quantity <= capacity
        )

        moq_satisfied = (
            quantity >= moq
        )

        if not capacity_sufficient:
            supplier_status = "SHORTAGE"
        elif not moq_satisfied:
            supplier_status = "MOQ_VIOLATION"
        else:
            supplier_status = "FEASIBLE"

        procurement_quantity = (
            moq
            if quantity < moq
            else quantity
        )

        procurement_cost = (
            procurement_quantity
            * unit_price
        )

        shortage_quantity = max(
            quantity - capacity,
            0,
        )

        supplier_results.append(
            {
                "supplier_id": supplier[
                    "supplier_id"
                ],
                "supplier_name": supplier[
                    "supplier_name"
                ],
                "capacity": capacity,
                "available_capacity": capacity,
                "shortage_quantity": shortage_quantity,
                "required_quantity": quantity,
                "lead_time_days": supplier[
                    "lead_time_days"
                ],
                "unit_price": unit_price,
                "minimum_order_quantity": moq,
                "procurement_quantity": (
                    procurement_quantity
                ),
                "estimated_cost": (
                    procurement_cost
                ),
                "procurement_cost": (
                    procurement_cost
                ),
                "status": supplier_status,
            }
        )

    if not supplier_results:
        return {
            "material_id": material_id,
            "material_name": material[
                "material_name"
            ],
            "required_quantity": quantity,
            "status": "NO_SUPPLIER",
            "suppliers": [],
        }

    feasible_suppliers = [
        supplier
        for supplier in supplier_results
        if supplier["status"] == "FEASIBLE"
    ]

    if feasible_suppliers:
        status = "FEASIBLE"
    elif any(
        supplier["status"] == "MOQ_VIOLATION"
        for supplier in supplier_results
    ):
        status = "MOQ_VIOLATION"
    else:
        status = "SHORTAGE"

    return {
        "material_id": material_id,
        "material_name": material[
            "material_name"
        ],
        "required_quantity": quantity,
        "status": status,
        "suppliers": supplier_results,
    }