from __future__ import annotations

import json

import pytest

from src.construction.integration import (
    build_resource_procurement_context,
)


PROJECT_PATH = (
    "data/projects/cmido_demo_project.json"
)


AVAILABLE_RESOURCES = {
    "M001": 500,
    "M002": 100,
    "M003": 100,
    "M004": 500,
    "M005": 20000,
    "M006": 2000,
    "M007": 2000,
    "M008": 20,
    "M009": 20,
}


def load_project() -> dict:
    with open(
        PROJECT_PATH,
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_resource_procurement_context_contains_domains():
    result = build_resource_procurement_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert "schedule" in result
    assert "resources" in result
    assert "procurement" in result


def test_baseline_schedule_is_exposed():
    result = build_resource_procurement_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert result[
        "schedule"
    ]["project_duration_days"] == 74


def test_critical_path_is_exposed():
    result = build_resource_procurement_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert result[
        "schedule"
    ]["critical_path"] == [
        "A001",
        "A002",
        "A003",
        "A004",
        "A006",
        "A007",
        "A008",
        "A009",
        "A011",
    ]


def test_resource_dashboard_is_integrated():
    result = build_resource_procurement_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert "summary" in result[
        "resources"
    ]

    assert "resources" in result[
        "resources"
    ]


def test_procurement_requirements_are_integrated():
    result = build_resource_procurement_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    procurement = result[
        "procurement"
    ]

    assert procurement[
        "total_requirements"
    ] > 0

    assert len(
        procurement["requirements"]
    ) == procurement[
        "total_requirements"
    ]


def test_procurement_requirement_contains_resource_status():
    result = build_resource_procurement_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    item = result[
        "procurement"
    ]["requirements"][0]

    assert "resource_status" in item
    assert "resource_available_quantity" in item
    assert "resource_shortage_quantity" in item


def test_procurement_requirement_contains_supplier_information():
    result = build_resource_procurement_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    item = result[
        "procurement"
    ]["requirements"][0]

    assert "procurement_status" in item
    assert "supplier_id" in item
    assert "supplier_name" in item
    assert "lead_time_days" in item
    assert "latest_order_date" in item


def test_resource_shortage_is_reflected():
    resources = dict(
        AVAILABLE_RESOURCES
    )

    resources["M001"] = 300

    result = build_resource_procurement_context(
        load_project(),
        resources,
    )

    concrete = next(
        item
        for item in result[
            "resources"
        ]["resources"]
        if item["resource_id"] == "M001"
    )

    assert concrete[
        "status"
    ] == "SHORTAGE"

    assert concrete[
        "shortage_quantity"
    ] > 0


def test_invalid_project_data_is_rejected():
    with pytest.raises(ValueError):
        build_resource_procurement_context(
            [],
            AVAILABLE_RESOURCES,
        )


def test_invalid_resource_input_is_rejected():
    with pytest.raises(ValueError):
        build_resource_procurement_context(
            load_project(),
            [],
        )