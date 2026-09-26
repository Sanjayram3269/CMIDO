import json

from src.construction.simulation.impact import (
    analyze_schedule_impact,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_one_day_noncritical_delay_is_absorbed():
    project = load_project()

    result = analyze_schedule_impact(
        project,
        "A005",
        1,
    )

    assert result["baseline_project_duration"] == 74
    assert result["scenario_project_duration"] == 74
    assert result["project_delay_days"] == 0


def test_three_day_noncritical_delay_extends_project():
    project = load_project()

    result = analyze_schedule_impact(
        project,
        "A005",
        3,
    )

    assert result["baseline_project_duration"] == 74
    assert result["scenario_project_duration"] == 75
    assert result["project_delay_days"] == 1


def test_delayed_activity_is_reported_as_affected():
    project = load_project()

    result = analyze_schedule_impact(
        project,
        "A005",
        3,
    )

    affected_ids = {
        item["activity_id"]
        for item in result["affected_activities"]
    }

    assert "A005" in affected_ids


def test_critical_activity_delay_propagates():
    project = load_project()

    result = analyze_schedule_impact(
        project,
        "A004",
        2,
    )

    assert result["project_delay_days"] == 2

    affected_ids = {
        item["activity_id"]
        for item in result["affected_activities"]
    }

    assert "A004" in affected_ids
    assert "A006" in affected_ids
    assert "A007" in affected_ids


def test_critical_path_is_reported():
    project = load_project()

    result = analyze_schedule_impact(
        project,
        "A005",
        1,
    )

    assert result["critical_path_before"] == [
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

    assert result["critical_path_after"] == (
        result["critical_path_before"]
    )