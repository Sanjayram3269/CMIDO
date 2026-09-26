import json
from pathlib import Path

import pytest

from datetime import date

from src.construction.quantity import (
    aggregate_material_requirements,
    build_material_demand_report,
    calculate_activity_material_requirements,
    get_material_demand,
    build_time_phased_demand,
    aggregate_time_phased_demand,
    evaluate_procurement_feasibility,
)


PROJECT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "projects"
    / "cmido_demo_project.json"
)


def load_project():
    with PROJECT_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_activity_material_requirements():
    project = load_project()

    requirements = calculate_activity_material_requirements(project)

    assert len(requirements) == 15


def test_foundation_concrete_requirement():
    project = load_project()

    requirements = calculate_activity_material_requirements(project)

    foundation_concrete = next(
        item
        for item in requirements
        if item["activity_id"] == "A003"
        and item["material_id"] == "M001"
    )

    assert foundation_concrete["quantity_required"] == 120
    assert foundation_concrete["unit"] == "m3"


def test_foundation_steel_requirement():
    project = load_project()

    requirements = calculate_activity_material_requirements(project)

    foundation_steel = next(
        item
        for item in requirements
        if item["activity_id"] == "A003"
        and item["material_id"] == "M002"
    )

    assert foundation_steel["quantity_required"] == 18
    assert foundation_steel["unit"] == "tonne"


def test_concrete_project_total():
    project = load_project()

    totals = aggregate_material_requirements(project)

    concrete = next(
        item
        for item in totals
        if item["material_id"] == "M001"
    )

    assert concrete["total_quantity"] == 360
    assert concrete["unit"] == "m3"


def test_steel_project_total():
    project = load_project()

    totals = aggregate_material_requirements(project)

    steel = next(
        item
        for item in totals
        if item["material_id"] == "M002"
    )

    assert steel["total_quantity"] == 54
    assert steel["unit"] == "tonne"


def test_unknown_activity_is_rejected():
    project = load_project()

    project["activity_materials"].append(
        {
            "activity_id": "A999",
            "material_id": "M001",
            "quantity_required": 10,
            "unit": "m3",
        }
    )

    with pytest.raises(ValueError, match="Unknown activity"):
        calculate_activity_material_requirements(project)


def test_unknown_material_is_rejected():
    project = load_project()

    project["activity_materials"].append(
        {
            "activity_id": "A001",
            "material_id": "M999",
            "quantity_required": 10,
            "unit": "m3",
        }
    )

    with pytest.raises(ValueError, match="Unknown material"):
        calculate_activity_material_requirements(project)


def test_negative_quantity_is_rejected():
    project = load_project()

    project["activity_materials"][0]["quantity_required"] = -10

    with pytest.raises(
        ValueError,
        match="Material quantity cannot be negative",
    ):
        calculate_activity_material_requirements(project)

def test_material_demand_report_contains_all_materials():
    project = load_project()

    report = build_material_demand_report(project)

    assert len(report) == 9


def test_concrete_demand_report():
    project = load_project()

    report = build_material_demand_report(project)

    concrete = next(
        item
        for item in report
        if item["material_id"] == "M001"
    )

    assert concrete["material_name"] == "Concrete"
    assert concrete["total_quantity"] == 360
    assert concrete["unit"] == "m3"
    assert concrete["activity_count"] == 3


def test_concrete_activity_breakdown():
    project = load_project()

    report = build_material_demand_report(project)

    concrete = next(
        item
        for item in report
        if item["material_id"] == "M001"
    )

    quantities = {
        item["activity_id"]: item["quantity"]
        for item in concrete["activities"]
    }

    assert quantities["A003"] == 120
    assert quantities["A004"] == 60
    assert quantities["A006"] == 180


def test_steel_demand_report():
    project = load_project()

    report = build_material_demand_report(project)

    steel = next(
        item
        for item in report
        if item["material_id"] == "M002"
    )

    assert steel["total_quantity"] == 54
    assert steel["activity_count"] == 3


def test_single_material_lookup():
    project = load_project()

    concrete = get_material_demand(
        project,
        "M001",
    )

    assert concrete["material_name"] == "Concrete"
    assert concrete["total_quantity"] == 360


def test_unknown_material_lookup_fails():
    project = load_project()

    with pytest.raises(
        ValueError,
        match="Material not found",
    ):
        get_material_demand(
            project,
            "M999",
        )

def demo_schedule():
    return {
        "A001": {
            "start": date(2026, 10, 1),
            "finish": date(2026, 10, 3),
        },
        "A002": {
            "start": date(2026, 10, 4),
            "finish": date(2026, 10, 6),
        },
        "A003": {
            "start": date(2026, 10, 7),
            "finish": date(2026, 10, 15),
        },
        "A004": {
            "start": date(2026, 10, 16),
            "finish": date(2026, 10, 20),
        },
        "A005": {
            "start": date(2026, 10, 21),
            "finish": date(2026, 10, 25),
        },
        "A006": {
            "start": date(2026, 10, 26),
            "finish": date(2026, 11, 2),
        },
        "A007": {
            "start": date(2026, 11, 3),
            "finish": date(2026, 11, 8),
        },
        "A008": {
            "start": date(2026, 11, 9),
            "finish": date(2026, 11, 13),
        },
        "A009": {
            "start": date(2026, 11, 14),
            "finish": date(2026, 11, 18),
        },
        "A010": {
            "start": date(2026, 11, 19),
            "finish": date(2026, 11, 22),
        },
        "A011": {
            "start": date(2026, 11, 23),
            "finish": date(2026, 11, 25),
        },
    }


def test_time_phased_demand_contains_schedule_dates():
    project = load_project()

    demand = build_time_phased_demand(
        project,
        demo_schedule(),
    )

    foundation_concrete = next(
        item
        for item in demand
        if item["activity_id"] == "A003"
        and item["material_id"] == "M001"
    )

    assert foundation_concrete["quantity"] == 120
    assert foundation_concrete["start"] == date(2026, 10, 7)
    assert foundation_concrete["finish"] == date(2026, 10, 15)


def test_time_phased_demand_preserves_material_totals():
    project = load_project()

    demand = build_time_phased_demand(
        project,
        demo_schedule(),
    )

    concrete = [
        item
        for item in demand
        if item["material_id"] == "M001"
    ]

    assert sum(item["quantity"] for item in concrete) == 360


def test_unknown_scheduled_activity_is_rejected():
    project = load_project()

    schedule = demo_schedule()
    schedule["A999"] = {
        "start": date(2026, 12, 1),
        "finish": date(2026, 12, 2),
    }

    with pytest.raises(
        ValueError,
        match="unknown activity",
    ):
        build_time_phased_demand(
            project,
            schedule,
        )


def test_missing_activity_schedule_is_rejected():
    project = load_project()

    schedule = demo_schedule()
    del schedule["A003"]

    with pytest.raises(
        ValueError,
        match="Missing schedule",
    ):
        build_time_phased_demand(
            project,
            schedule,
        )


def test_invalid_date_range_is_rejected():
    project = load_project()

    schedule = demo_schedule()
    schedule["A003"] = {
        "start": date(2026, 10, 15),
        "finish": date(2026, 10, 7),
    }

    with pytest.raises(
        ValueError,
        match="Finish date cannot be before start date",
    ):
        build_time_phased_demand(
            project,
            schedule,
        )


def test_time_phased_aggregation_preserves_activity_traceability():
    project = load_project()

    demand = aggregate_time_phased_demand(
        project,
        demo_schedule(),
    )

    concrete = [
        item
        for item in demand
        if item["material_id"] == "M001"
    ]

    assert len(concrete) == 3

    activity_ids = {
        item["activity_id"]
        for item in concrete
    }

    assert activity_ids == {"A003", "A004", "A006"}

def test_procurement_feasibility_returns_results():
    project = load_project()

    results = evaluate_procurement_feasibility(
        project,
        demo_schedule(),
    )

    assert len(results) == 15


def test_concrete_procurement_is_evaluated():
    project = load_project()

    results = evaluate_procurement_feasibility(
        project,
        demo_schedule(),
    )

    concrete = next(
        item
        for item in results
        if item["material_id"] == "M001"
        and item["activity_id"] == "A003"
    )

    assert concrete["required_quantity"] == 120
    assert concrete["required_date"] == date(2026, 10, 7)


def test_missing_supplier_is_detected():
    project = load_project()

    project["supplier_materials"] = [
        mapping
        for mapping in project["supplier_materials"]
        if mapping["material_id"] != "M001"
    ]

    results = evaluate_procurement_feasibility(
        project,
        demo_schedule(),
    )

    concrete = next(
        item
        for item in results
        if item["material_id"] == "M001"
    )

    assert concrete["status"] == "NO_SUPPLIER"


def test_insufficient_supplier_capacity_is_detected():
    project = load_project()

    concrete_mapping = next(
        mapping
        for mapping in project["supplier_materials"]
        if mapping["material_id"] == "M001"
    )

    concrete_mapping["capacity"] = 50

    results = evaluate_procurement_feasibility(
        project,
        demo_schedule(),
    )

    concrete = next(
        item
        for item in results
        if item["material_id"] == "M001"
        and item["activity_id"] == "A003"
    )

    assert concrete["status"] == "INSUFFICIENT_CAPACITY"


def test_latest_order_date_respects_lead_time():
    project = load_project()

    results = evaluate_procurement_feasibility(
        project,
        demo_schedule(),
    )

    concrete = next(
        item
        for item in results
        if item["material_id"] == "M001"
        and item["activity_id"] == "A003"
    )

    if concrete["status"] == "FEASIBLE":
        expected = date(
            2026,
            10,
            7,
        ) - __import__("datetime").timedelta(
            days=concrete["lead_time_days"]
        )

        assert concrete["latest_order_date"] == expected


def test_procurement_result_contains_traceability():
    project = load_project()

    results = evaluate_procurement_feasibility(
        project,
        demo_schedule(),
    )

    result = results[0]

    assert "activity_id" in result
    assert "material_id" in result
    assert "required_quantity" in result
    assert "required_date" in result
    assert "status" in result