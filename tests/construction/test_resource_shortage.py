import pytest

from src.construction.resource_shortage import (
    analyze_resource_shortage,
)


def make_demands():
    return [
        {
            "activity_id": "A003",
            "activity_name": "Foundation",
            "quantity": 120,
            "unit": "m3",
            "start_day": 13,
            "finish_day": 25,
        },
        {
            "activity_id": "A004",
            "activity_name": "Columns",
            "quantity": 60,
            "unit": "m3",
            "start_day": 25,
            "finish_day": 33,
        },
        {
            "activity_id": "A006",
            "activity_name": "Slab",
            "quantity": 180,
            "unit": "m3",
            "start_day": 33,
            "finish_day": 43,
        },
    ]


def test_resource_is_feasible_when_supply_is_sufficient():
    result = analyze_resource_shortage(
        make_demands(),
        500,
    )

    assert result["total_required"] == 360
    assert result["total_allocated"] == 360
    assert result["total_shortage"] == 0
    assert result["remaining_quantity"] == 140
    assert result["status"] == "FEASIBLE"


def test_resource_shortage_is_detected():
    result = analyze_resource_shortage(
        make_demands(),
        300,
    )

    assert result["total_required"] == 360
    assert result["total_allocated"] == 300
    assert result["total_shortage"] == 60
    assert result["remaining_quantity"] == 0
    assert result["status"] == "SHORTAGE"


def test_shortage_is_assigned_to_later_activity():
    result = analyze_resource_shortage(
        make_demands(),
        300,
    )

    assert len(result["affected_activities"]) == 1

    affected = result["affected_activities"][0]

    assert affected["activity_id"] == "A006"
    assert affected["quantity_required"] == 180
    assert affected["quantity_allocated"] == 120
    assert affected["shortage_quantity"] == 60
    assert affected["status"] == "SHORTAGE"


def test_fully_supplied_activities_are_identified():
    result = analyze_resource_shortage(
        make_demands(),
        300,
    )

    first = result["allocations"][0]
    second = result["allocations"][1]

    assert first["status"] == "FULLY_SUPPLIED"
    assert second["status"] == "FULLY_SUPPLIED"

    assert first["shortage_quantity"] == 0
    assert second["shortage_quantity"] == 0


def test_zero_supply_creates_full_shortage():
    result = analyze_resource_shortage(
        make_demands(),
        0,
    )

    assert result["total_allocated"] == 0
    assert result["total_shortage"] == 360
    assert result["status"] == "SHORTAGE"


def test_empty_demand_is_feasible():
    result = analyze_resource_shortage(
        [],
        500,
    )

    assert result["total_required"] == 0
    assert result["total_allocated"] == 0
    assert result["total_shortage"] == 0
    assert result["remaining_quantity"] == 500
    assert result["status"] == "FEASIBLE"


def test_negative_supply_is_rejected():
    with pytest.raises(ValueError):
        analyze_resource_shortage(
            make_demands(),
            -1,
        )


def test_allocation_never_exceeds_available_quantity():
    result = analyze_resource_shortage(
        make_demands(),
        100,
        )

    assert result["total_allocated"] == 100
    assert result["total_allocated"] <= 100