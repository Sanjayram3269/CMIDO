import json

import pytest

from src.construction.simulation.delay import (
    simulate_activity_delay,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_zero_delay_preserves_project():
    project = load_project()

    result = simulate_activity_delay(
        project,
        "A005",
        0,
    )

    assert result["baseline_project_duration"] == 74
    assert result["scenario_project_duration"] == 74
    assert result["project_delay_days"] == 0


def test_non_critical_delay_within_float():
    project = load_project()

    result = simulate_activity_delay(
        project,
        "A005",
        1,
    )

    assert result["scenario_project_duration"] == 74
    assert result["project_delay_days"] == 0


def test_non_critical_delay_beyond_float():
    project = load_project()

    result = simulate_activity_delay(
        project,
        "A005",
        3,
    )

    assert result["scenario_project_duration"] == 75
    assert result["project_delay_days"] == 1


def test_critical_activity_delay():
    project = load_project()

    result = simulate_activity_delay(
        project,
        "A004",
        2,
    )

    assert result["scenario_project_duration"] == 76
    assert result["project_delay_days"] == 2


def test_original_project_is_not_modified():
    project = load_project()

    original_duration = next(
        item["duration_days"]
        for item in project["activities"]
        if item["activity_id"] == "A005"
    )

    simulate_activity_delay(
        project,
        "A005",
        10,
    )

    current_duration = next(
        item["duration_days"]
        for item in project["activities"]
        if item["activity_id"] == "A005"
    )

    assert current_duration == original_duration


def test_unknown_activity_fails():
    project = load_project()

    with pytest.raises(ValueError):
        simulate_activity_delay(
            project,
            "INVALID",
            2,
        )


def test_negative_delay_fails():
    project = load_project()

    with pytest.raises(ValueError):
        simulate_activity_delay(
            project,
            "A005",
            -1,
        )