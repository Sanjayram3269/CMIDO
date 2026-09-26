import json

from src.construction.scheduling.forward_pass import (
    calculate_forward_pass,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_forward_pass_contains_all_activities():
    project = load_project()

    results = calculate_forward_pass(project)

    assert len(results) == 11


def test_forward_pass_has_es_and_ef():
    project = load_project()

    results = calculate_forward_pass(project)

    for result in results:
        assert "es" in result
        assert "ef" in result
        assert result["ef"] == (
            result["es"] + result["duration_days"]
        )


def test_forward_pass_respects_dependencies():
    project = load_project()

    results = calculate_forward_pass(project)

    by_id = {
        result["activity_id"]: result
        for result in results
    }

    for dependency in project["dependencies"]:
        predecessor = dependency["predecessor_id"]
        successor = dependency["successor_id"]
        lag = dependency["lag_days"]

        assert (
            by_id[successor]["es"]
            >= by_id[predecessor]["ef"] + lag
        )


def test_root_activity_starts_at_zero():
    project = load_project()

    results = calculate_forward_pass(project)

    root_results = [
        result
        for result in results
        if not result["predecessors"]
    ]

    assert len(root_results) >= 1

    for result in root_results:
        assert result["es"] == 0


def test_forward_pass_project_duration_is_max_ef():
    project = load_project()

    results = calculate_forward_pass(project)

    project_duration = max(
        result["ef"]
        for result in results
    )

    assert project_duration > 0


def test_duration_comes_from_project_schema():
    project = load_project()

    results = calculate_forward_pass(project)

    activities = {
        activity["activity_id"]: activity
        for activity in project["activities"]
    }

    for result in results:
        activity = activities[result["activity_id"]]

        assert (
            result["duration_days"]
            == activity["duration_days"]
        )
