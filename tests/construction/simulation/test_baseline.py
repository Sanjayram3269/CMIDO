import json

from src.construction.simulation.baseline import (
    create_baseline_snapshot,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_baseline_project_duration():
    project = load_project()

    baseline = create_baseline_snapshot(project)

    assert baseline["project_duration"] == 74


def test_baseline_critical_path():
    project = load_project()

    baseline = create_baseline_snapshot(project)

    assert baseline["critical_path"] == [
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


def test_baseline_contains_all_activities():
    project = load_project()

    baseline = create_baseline_snapshot(project)

    assert len(baseline["activities"]) == 11


def test_baseline_does_not_modify_project():
    project = load_project()

    original = json.dumps(project, sort_keys=True)

    create_baseline_snapshot(project)

    after = json.dumps(project, sort_keys=True)

    assert original == after


def test_baseline_float_values():
    project = load_project()

    baseline = create_baseline_snapshot(project)

    assert baseline["activities"]["A005"]["total_float"] == 2
    assert baseline["activities"]["A010"]["total_float"] == 1