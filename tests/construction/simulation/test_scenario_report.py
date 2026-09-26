import json

from src.construction.simulation.scenario_report import (
    generate_scenario_report,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_report_contains_scenario_information():
    project = load_project()

    report = generate_scenario_report(
        project,
        "A005",
        1,
    )

    assert report["scenario"]["activity_id"] == "A005"
    assert report["scenario"]["activity_name"] == "MEP Rough-in"
    assert report["scenario"]["delay_days"] == 1


def test_report_contains_project_impact():
    project = load_project()

    report = generate_scenario_report(
        project,
        "A005",
        3,
    )

    assert report["project"]["baseline_duration"] == 74
    assert report["project"]["scenario_duration"] == 75
    assert report["project"]["project_delay_days"] == 1


def test_report_contains_float_analysis():
    project = load_project()

    report = generate_scenario_report(
        project,
        "A005",
        3,
    )

    assert report["float"]["baseline_float"] == 2
    assert report["float"]["float_consumed"] == 2
    assert report["float"]["remaining_float"] == 0
    assert report["float"]["excess_delay"] == 1


def test_report_contains_critical_path_information():
    project = load_project()

    report = generate_scenario_report(
        project,
        "A005",
        1,
    )

    assert "before" in report["critical_path"]
    assert "after" in report["critical_path"]
    assert "changed" in report["critical_path"]

    assert report["critical_path"]["before"]


def test_report_contains_affected_activities():
    project = load_project()

    report = generate_scenario_report(
        project,
        "A005",
        3,
    )

    assert isinstance(
        report["affected_activities"],
        list,
    )

    affected_ids = {
        item["activity_id"]
        for item in report["affected_activities"]
    }

    assert "A005" in affected_ids


def test_report_contains_activity_changes():
    project = load_project()

    report = generate_scenario_report(
        project,
        "A005",
        3,
    )

    assert isinstance(
        report["activity_changes"],
        list,
    )

    assert len(report["activity_changes"]) == 11