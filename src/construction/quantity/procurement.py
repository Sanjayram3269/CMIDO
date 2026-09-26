from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .time_phased import build_time_phased_demand


def _supplier_material_map(
    project_data: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """
    Build a material -> supplier mapping.
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

    This is a feasibility analysis, not an optimization algorithm.
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

        suppliers = supplier_map.get(material_id, [])

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
            required_date - timedelta(days=lead_time)
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
                "supplier_id": selected_supplier["supplier_id"],
                "supplier_name": selected_supplier["supplier_name"],
                "available_capacity": selected_supplier["capacity"],
                "lead_time_days": lead_time,
                "latest_order_date": latest_order_date,
            }
        )

    return results
