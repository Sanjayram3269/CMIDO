import json

import pytest

from src.construction.quantity.procurement import (
    analyze_procurement_feasibility,
)


PROJECT_PATH = (
    "data/projects/cmido_demo_project.json"
)


def load_project():
    with open(
        PROJECT_PATH,
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_concrete_procurement_is_feasible():
    project = load_project()

    result = analyze_procurement_feasibility(
        project,
        "M001",
        360,
    )

    assert result["material_id"] == "M001"
    assert result["required_quantity"] == 360
    assert result["status"] == "FEASIBLE"

    assert len(result["suppliers"]) == 1

    supplier = result["suppliers"][0]

    assert supplier["supplier_id"] == "S001"
    assert supplier["supplier_name"] == "Concrete Supplier"
    assert supplier["capacity"] == 500
    assert supplier["lead_time_days"] == 3
    assert supplier["minimum_order_quantity"] == 10
    assert supplier["unit_price"] == 6500


def test_concrete_shortage_when_requirement_exceeds_capacity():
    project = load_project()

    result = analyze_procurement_feasibility(
        project,
        "M001",
        600,
    )

    assert result["status"] == "SHORTAGE"
    assert result["required_quantity"] == 600

    supplier = result["suppliers"][0]

    assert supplier["capacity"] == 500
    assert supplier["shortage_quantity"] == 100


def test_moq_violation_is_detected():
    project = load_project()

    result = analyze_procurement_feasibility(
        project,
        "M005",
        100,
    )

    assert result["status"] == "MOQ_VIOLATION"

    supplier = result["suppliers"][0]

    assert supplier["minimum_order_quantity"] == 500
    assert supplier["required_quantity"] == 100


def test_supplier_mapping_is_found():
    project = load_project()

    result = analyze_procurement_feasibility(
        project,
        "M008",
        5,
    )

    assert result["status"] == "FEASIBLE"
    assert len(result["suppliers"]) == 1

    assert (
        result["suppliers"][0]["supplier_id"]
        == "S004"
    )


def test_unknown_material_is_rejected():
    project = load_project()

    with pytest.raises(ValueError):
        analyze_procurement_feasibility(
            project,
            "M999",
            10,
        )


def test_negative_quantity_is_rejected():
    project = load_project()

    with pytest.raises(ValueError):
        analyze_procurement_feasibility(
            project,
            "M001",
            -10,
        )


def test_procurement_cost_is_calculated():
    project = load_project()

    result = analyze_procurement_feasibility(
        project,
        "M001",
        360,
    )

    supplier = result["suppliers"][0]

    assert supplier["estimated_cost"] == (
        360 * 6500
    )