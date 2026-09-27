import json

import pytest

from src.construction.dashboard import (
    build_dashboard_data,
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


def test_dashboard_contains_required_sections():
    result = build_dashboard_data(
        load_project()
    )

    assert "overview" in result
    assert "schedule" in result
    assert "materials" in result
    assert "resources" in result


def test_dashboard_overview_is_correct():
    result = build_dashboard_data(
        load_project()
    )

    overview = result["overview"]

    assert overview[
        "project_id"
    ] == "CMIDO-DEMO-001"

    assert overview[
        "project_name"
    ] == "Residential Building Demo"

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


def test_dashboard_schedule_contains_all_activities():
    result = build_dashboard_data(
        load_project()
    )

    activities = result[
        "schedule"
    ]["activities"]

    assert len(activities) == 11


def test_dashboard_critical_path_is_correct():
    result = build_dashboard_data(
        load_project()
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


def test_dashboard_activity_critical_flags():
    result = build_dashboard_data(
        load_project()
    )

    activities = {
        item["activity_id"]: item
        for item in result[
            "schedule"
        ]["activities"]
    }

    assert activities[
        "A001"
    ]["is_critical"] is True

    assert activities[
        "A006"
    ]["is_critical"] is True

    assert activities[
        "A005"
    ]["is_critical"] is False

    assert activities[
        "A010"
    ]["is_critical"] is False


def test_dashboard_materials_contains_all_types():
    result = build_dashboard_data(
        load_project()
    )

    materials = result[
        "materials"
    ]["materials"]

    assert len(materials) == 9


def test_dashboard_concrete_quantity():
    result = build_dashboard_data(
        load_project()
    )

    concrete = next(
        item
        for item in result[
            "materials"
        ]["materials"]
        if item["material_name"]
        == "Concrete"
    )

    assert concrete[
        "material_id"
    ] == "M001"

    assert concrete[
        "total_quantity"
    ] == 360

    assert concrete[
        "unit"
    ] == "m3"


def test_dashboard_resource_placeholder_is_explicit():
    result = build_dashboard_data(
        load_project()
    )

    assert result[
        "resources"
    ]["status"] == "NOT_ANALYZED"


def test_dashboard_rejects_missing_project():
    project = load_project()

    del project["project"]

    with pytest.raises(ValueError):
        build_dashboard_data(project)


def test_dashboard_does_not_modify_project():
    project = load_project()

    original_activity_count = len(
        project["activities"]
    )

    build_dashboard_data(project)

    assert len(
        project["activities"]
    ) == original_activity_count