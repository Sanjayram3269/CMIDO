import pytest

from src.construction.resource_allocation import (
    allocate_resource,
)


def test_resource_demand_fully_satisfied():
    result = allocate_resource(
        500,
        [
            {
                "activity_id": "A003",
                "quantity": 120,
            },
            {
                "activity_id": "A004",
                "quantity": 60,
            },
            {
                "activity_id": "A006",
                "quantity": 180,
            },
        ],
    )

    assert result["total_required"] == 360
    assert result["total_allocated"] == 360
    assert result["total_shortage"] == 0
    assert result["remaining_quantity"] == 140
    assert result["fully_satisfied"] is True


def test_resource_shortage_is_detected():
    result = allocate_resource(
        300,
        [
            {
                "activity_id": "A003",
                "quantity": 120,
            },
            {
                "activity_id": "A004",
                "quantity": 60,
            },
            {
                "activity_id": "A006",
                "quantity": 180,
            },
        ],
    )

    assert result["total_required"] == 360
    assert result["total_allocated"] == 300
    assert result["total_shortage"] == 60
    assert result["remaining_quantity"] == 0
    assert result["fully_satisfied"] is False


def test_allocation_is_activity_specific():
    result = allocate_resource(
        150,
        [
            {
                "activity_id": "A003",
                "quantity": 100,
            },
            {
                "activity_id": "A004",
                "quantity": 100,
            },
        ],
    )

    assert result["allocations"][0]["allocated_quantity"] == 100
    assert result["allocations"][0]["shortage_quantity"] == 0

    assert result["allocations"][1]["allocated_quantity"] == 50
    assert result["allocations"][1]["shortage_quantity"] == 50


def test_zero_available_resource():
    result = allocate_resource(
        0,
        [
            {
                "activity_id": "A003",
                "quantity": 120,
            },
        ],
    )

    assert result["total_allocated"] == 0
    assert result["total_shortage"] == 120
    assert result["remaining_quantity"] == 0


def test_zero_demand():
    result = allocate_resource(
        500,
        [],
    )

    assert result["total_required"] == 0
    assert result["total_allocated"] == 0
    assert result["total_shortage"] == 0
    assert result["remaining_quantity"] == 500


def test_negative_available_quantity_rejected():
    with pytest.raises(ValueError):
        allocate_resource(
            -10,
            [],
        )


def test_negative_demand_rejected():
    with pytest.raises(ValueError):
        allocate_resource(
            500,
            [
                {
                    "activity_id": "A003",
                    "quantity": -10,
                }
            ],
        )


def test_allocation_never_exceeds_availability():
    result = allocate_resource(
        100,
        [
            {
                "activity_id": "A003",
                "quantity": 500,
            },
        ],
    )

    assert result["total_allocated"] == 100
    assert result["total_allocated"] <= result["available_quantity"]