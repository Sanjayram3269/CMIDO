import json

import pytest

from src.construction.integrated_analysis import (
    analyze_project,
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


def test_integrated_analysis_contains_project():
    result = analyze_project(
        load_project()
    )

    assert "project" in result

    assert (
        result["project"]["project_id"]
        == "CMIDO-DEMO-001"
    )

    assert (
        result["project"]["project_name"]
        == "Residential Building Demo"
    )


def test_integrated_analysis_contains_schedule():
    result = analyze_project(
        load_project()
    )

    schedule = result["schedule"]

    assert schedule[
        "project_duration"
    ] == 74

    assert schedule[
        "critical_path_duration"
    ] == 74


def test_integrated_analysis_contains_critical_path():
    result = analyze_project(
        load_project()
    )

    assert result["schedule"][
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


def test_integrated_analysis_contains_non_critical_activities():
    result = analyze_project(
        load_project()
    )

    non_critical = {
        item["activity_id"]
        for item in result["schedule"][
            "non_critical_activities"
        ]
    }

    assert non_critical == {
        "A005",
        "A010",
    }


def test_integrated_analysis_contains_all_activities():
    result = analyze_project(
        load_project()
    )

    assert len(
        result["activities"]
    ) == 11


def test_critical_activity_flags_are_correct():
    result = analyze_project(
        load_project()
    )

    by_id = {
        item["activity_id"]: item
        for item in result["activities"]
    }

    assert by_id["A001"][
        "is_critical"
    ] is True

    assert by_id["A004"][
        "is_critical"
    ] is True

    assert by_id["A006"][
        "is_critical"
    ] is True

    assert by_id["A005"][
        "is_critical"
    ] is False

    assert by_id["A010"][
        "is_critical"
    ] is False


def test_integrated_analysis_contains_materials():
    result = analyze_project(
        load_project()
    )

    materials = result["materials"]

    assert materials[
        "total_material_types"
    ] == 9

    assert len(
        materials["requirements"]
    ) == 9


def test_concrete_quantity_is_present():
    result = analyze_project(
        load_project()
    )

    concrete = next(
        item
        for item in result["materials"][
            "requirements"
        ]
        if item["material_name"]
        == "Concrete"
    )

    assert concrete[
        "total_quantity"
    ] == 360


def test_integrated_analysis_rejects_missing_project():
    project = load_project()

    del project["project"]

    with pytest.raises(ValueError):
        analyze_project(project)


def test_integrated_analysis_rejects_missing_material_data():
    project = load_project()

    del project["activity_materials"]

    with pytest.raises(ValueError):
        analyze_project(project)