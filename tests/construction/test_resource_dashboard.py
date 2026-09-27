import json

import pytest

from src.construction.resource_dashboard import (
    build_resource_dashboard,
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


def test_resource_dashboard_contains_all_resources():
    project = load_project()

    result = build_resource_dashboard(
        project,
        {
            "M001": 500,
            "M002": 100,
            "M003": 100,
            "M004": 500,
            "M005": 20000,
            "M006": 2000,
            "M007": 2000,
            "M008": 20,
            "M009": 20,
        },
    )

    assert len(
        result["resources"]
    ) == 9


def test_resource_dashboard_summary():
    project = load_project()

    result = build_resource_dashboard(
        project,
        {
            "M001": 500,
            "M002": 100,
            "M003": 100,
            "M004": 500,
            "M005": 20000,
            "M006": 2000,
            "M007": 2000,
            "M008": 20,
            "M009": 20,
        },
    )

    assert result[
        "summary"
    ]["total_resources"] == 9

    assert result[
        "summary"
    ]["feasible_resources"] == 9

    assert result[
        "summary"
    ]["shortage_resources"] == 0


def test_concrete_resource_is_feasible():
    project = load_project()

    result = build_resource_dashboard(
        project,
        {
            "M001": 500,
        },
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    assert concrete[
        "resource_name"
    ] == "Concrete"

    assert concrete[
        "required_quantity"
    ] == 360

    assert concrete[
        "available_quantity"
    ] == 500

    assert concrete[
        "allocated_quantity"
    ] == 360

    assert concrete[
        "shortage_quantity"
    ] == 0

    assert concrete[
        "status"
    ] == "FEASIBLE"


def test_concrete_shortage_is_detected():
    project = load_project()

    result = build_resource_dashboard(
        project,
        {
            "M001": 300,
        },
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    assert concrete[
        "required_quantity"
    ] == 360

    assert concrete[
        "available_quantity"
    ] == 300

    assert concrete[
        "allocated_quantity"
    ] == 300

    assert concrete[
        "shortage_quantity"
    ] == 60

    assert concrete[
        "status"
    ] == "SHORTAGE"


def test_shortage_identifies_affected_activity():
    project = load_project()

    result = build_resource_dashboard(
        project,
        {
            "M001": 300,
        },
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    affected = concrete[
        "affected_activities"
    ]

    assert len(affected) == 1

    assert affected[0][
        "activity_id"
    ] == "A006"

    assert affected[0][
        "shortage_quantity"
    ] == 60


def test_resource_dashboard_handles_zero_supply():
    project = load_project()

    result = build_resource_dashboard(
        project,
        {
            "M001": 0,
        },
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    assert concrete[
        "allocated_quantity"
    ] == 0

    assert concrete[
        "shortage_quantity"
    ] == 360

    assert concrete[
        "status"
    ] == "SHORTAGE"


def test_missing_resource_defaults_to_zero():
    project = load_project()

    result = build_resource_dashboard(
        project,
        {},
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    assert concrete[
        "available_quantity"
    ] == 0

    assert concrete[
        "shortage_quantity"
    ] == 360


def test_multiple_resources_can_be_analyzed():
    project = load_project()

    result = build_resource_dashboard(
        project,
        {
            "M001": 300,
            "M002": 100,
            "M005": 5000,
        },
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    steel = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M002"
    )

    bricks = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M005"
    )

    assert concrete[
        "status"
    ] == "SHORTAGE"

    assert steel[
        "status"
    ] == "FEASIBLE"

    assert bricks[
        "status"
    ] == "SHORTAGE"


def test_invalid_project_data_is_rejected():
    project = load_project()

    del project[
        "activity_materials"
    ]

    with pytest.raises(ValueError):
        build_resource_dashboard(
            project,
            {},
        )