import json

import pytest

from src.construction.resource_schedule_impact import (
    analyze_resource_schedule_impact,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_critical_activity_shortage_delays_project():
    project = load_project()

    result = analyze_resource_schedule_impact(
        project,
        resource_id="M001",
        activity_id="A006",
        shortage_quantity=60,
        shortage_days=3,
    )

    assert result["resource_id"] == "M001"
    assert result["activity_id"] == "A006"
    assert result["shortage_quantity"] == 60
    assert result["shortage_days"] == 3

    assert result["baseline_project_duration"] == 74
    assert result["scenario_project_duration"] == 77
    assert result["project_delay_days"] == 3


def test_critical_activity_remains_on_critical_path():
    project = load_project()

    result = analyze_resource_schedule_impact(
        project,
        resource_id="M001",
        activity_id="A006",
        shortage_quantity=60,
        shortage_days=3,
    )

    assert "A006" in result["critical_path_before"]
    assert "A006" in result["critical_path_after"]


def test_non_critical_activity_can_consume_float():
    project = load_project()

    result = analyze_resource_schedule_impact(
        project,
        resource_id="M008",
        activity_id="A005",
        shortage_quantity=1,
        shortage_days=2,
    )

    assert result["activity_id"] == "A005"
    assert result["shortage_days"] == 2

    assert result["activity_float_before"] == 2
    assert result["activity_float_after"] == 0


def test_non_critical_activity_delay_within_float_does_not_delay_project():
    project = load_project()

    result = analyze_resource_schedule_impact(
        project,
        resource_id="M008",
        activity_id="A005",
        shortage_quantity=1,
        shortage_days=1,
    )

    assert result["project_delay_days"] == 0
    assert result["scenario_project_duration"] == 74
    assert result["activity_float_after"] == 1


def test_resource_shortage_can_change_classification():
    project = load_project()

    result = analyze_resource_schedule_impact(
        project,
        resource_id="M008",
        activity_id="A005",
        shortage_quantity=1,
        shortage_days=3,
    )

    assert result["activity_float_before"] == 2
    assert result["activity_float_after"] == 0
    assert result["classification_before"] == "NON_CRITICAL"
    assert result["classification_after"] == "CRITICAL"


def test_negative_shortage_quantity_is_rejected():
    project = load_project()

    with pytest.raises(ValueError):
        analyze_resource_schedule_impact(
            project,
            resource_id="M001",
            activity_id="A006",
            shortage_quantity=-1,
            shortage_days=2,
        )


def test_negative_shortage_days_are_rejected():
    project = load_project()

    with pytest.raises(ValueError):
        analyze_resource_schedule_impact(
            project,
            resource_id="M001",
            activity_id="A006",
            shortage_quantity=60,
            shortage_days=-1,
        )


def test_unknown_activity_is_rejected():
    project = load_project()

    with pytest.raises(ValueError):
        analyze_resource_schedule_impact(
            project,
            resource_id="M001",
            activity_id="UNKNOWN",
            shortage_quantity=60,
            shortage_days=2,
        )