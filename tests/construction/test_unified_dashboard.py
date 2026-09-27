import json

import pytest

from src.construction.unified_dashboard import (
    build_unified_dashboard,
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


def load_project():
    with open(
        PROJECT_PATH,
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_unified_dashboard_contains_all_sections():
    result = build_unified_dashboard(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert "overview" in result
    assert "schedule" in result
    assert "materials" in result
    assert "resources" in result
    assert "status" in result


def test_unified_dashboard_overview():
    result = build_unified_dashboard(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    overview = result["overview"]

    assert overview["project_id"] == (
        "CMIDO-DEMO-001"
    )

    assert overview["project_name"] == (
        "Residential Building Demo"
    )

    assert overview[
        "project_duration_days"
    ] == 74

    assert overview[
        "critical_path_duration_days"
    ] == 74

    assert overview[
        "total_activities"
    ] == 11

    assert overview[
        "critical_activities"
    ] == 9

    assert overview[
        "non_critical_activities"
    ] == 2

    assert overview[
        "total_material_types"
    ] == 9


def test_unified_dashboard_schedule():
    result = build_unified_dashboard(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    schedule = result["schedule"]

    assert schedule[
        "project_duration_days"
    ] == 74

    assert schedule[
        "critical_path"
    ] == [
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

    assert len(
        schedule["activities"]
    ) == 11


def test_unified_dashboard_materials():
    result = build_unified_dashboard(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    materials = result["materials"]

    assert materials[
        "total_material_types"
    ] == 9

    assert len(
        materials["materials"]
    ) == 9


def test_unified_dashboard_resources():
    result = build_unified_dashboard(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    resources = result["resources"]

    assert resources[
        "summary"
    ]["total_resources"] == 9

    assert resources[
        "summary"
    ]["feasible_resources"] == 9

    assert resources[
        "summary"
    ]["shortage_resources"] == 0

    assert len(
        resources["resources"]
    ) == 9


def test_unified_dashboard_status_is_feasible():
    result = build_unified_dashboard(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert result[
        "status"
    ] == "FEASIBLE"


def test_unified_dashboard_detects_resource_shortage():
    resources = dict(
        AVAILABLE_RESOURCES
    )

    resources["M001"] = 300

    result = build_unified_dashboard(
        load_project(),
        resources,
    )

    assert result[
        "status"
    ] == "RESOURCE_SHORTAGE"

    assert result[
        "resources"
    ]["summary"][
        "shortage_resources"
    ] == 1


def test_unified_dashboard_exposes_shortage_details():
    resources = dict(
        AVAILABLE_RESOURCES
    )

    resources["M001"] = 300

    result = build_unified_dashboard(
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
    ] == 60


def test_unified_dashboard_rejects_missing_project():
    project = load_project()

    del project["project"]

    with pytest.raises(ValueError):
        build_unified_dashboard(
            project,
            AVAILABLE_RESOURCES,
        )


def test_unified_dashboard_does_not_modify_project():
    project = load_project()

    original_activity_count = len(
        project["activities"]
    )

    build_unified_dashboard(
        project,
        AVAILABLE_RESOURCES,
    )

    assert len(
        project["activities"]
    ) == original_activity_count