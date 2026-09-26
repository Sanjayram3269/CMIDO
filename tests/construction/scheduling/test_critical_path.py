import json

from src.construction.scheduling.critical_path import (
    calculate_critical_path,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_critical_path_contains_expected_activities():
    project = load_project()

    result = calculate_critical_path(project)

    assert result["critical_path"] == [
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


def test_critical_path_duration_is_74_days():
    project = load_project()

    result = calculate_critical_path(project)

    assert result["critical_path_duration"] == 74


def test_critical_path_matches_project_duration():
    project = load_project()

    result = calculate_critical_path(project)

    assert (
        result["critical_path_duration"]
        == result["project_duration"]
    )


def test_non_critical_activities_are_excluded():
    project = load_project()

    result = calculate_critical_path(project)

    assert "A005" not in result["critical_path"]
    assert "A010" not in result["critical_path"]


def test_all_zero_float_activities_are_on_path():
    project = load_project()

    result = calculate_critical_path(project)

    critical_ids = {
        item["activity_id"]
        for item in result["critical_activities"]
    }

    expected = {
        "A001",
        "A002",
        "A003",
        "A004",
        "A006",
        "A007",
        "A008",
        "A009",
        "A011",
    }

    assert critical_ids == expected


def test_non_critical_float_values():
    project = load_project()

    result = calculate_critical_path(project)

    non_critical = {
        item["activity_id"]: item["total_float"]
        for item in result["non_critical_activities"]
    }

    assert non_critical["A005"] == 2
    assert non_critical["A010"] == 1