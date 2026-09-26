import json

from src.construction.scheduling.backward_pass import (
    calculate_backward_pass,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_backward_pass_contains_all_activities():
    project = load_project()

    results = calculate_backward_pass(project)

    assert len(results) == 11


def test_backward_pass_has_ls_and_lf():
    project = load_project()

    results = calculate_backward_pass(project)

    for result in results:
        assert "ls" in result
        assert "lf" in result

        assert result["ls"] + result["duration_days"] == result["lf"]


def test_final_activity_finishes_at_project_duration():
    project = load_project()

    results = calculate_backward_pass(project)

    project_duration = max(
        result["ef"]
        for result in results
    )

    final_activities = [
        result
        for result in results
        if not result["successors"]
    ]

    assert len(final_activities) >= 1

    for result in final_activities:
        assert result["lf"] == project_duration


def test_backward_pass_respects_successors():
    project = load_project()

    results = calculate_backward_pass(project)

    by_id = {
        result["activity_id"]: result
        for result in results
    }

    for dependency in project["dependencies"]:
        predecessor = dependency["predecessor_id"]
        successor = dependency["successor_id"]
        lag = dependency["lag_days"]

        assert (
            by_id[predecessor]["lf"]
            <= by_id[successor]["ls"] - lag
        )


def test_latest_start_is_not_after_latest_finish():
    project = load_project()

    results = calculate_backward_pass(project)

    for result in results:
        assert result["ls"] <= result["lf"]