import json

import pytest

from src.construction.simulation.float_analysis import (
    analyze_float_consumption,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_zero_delay():
    project = load_project()

    result = analyze_float_consumption(
        project,
        "A005",
        0,
    )

    assert result["baseline_float"] == 2
    assert result["float_consumed"] == 0
    assert result["remaining_float"] == 2
    assert result["excess_delay"] == 0
    assert result["project_delay_days"] == 0


def test_one_day_delay_consumes_one_day_float():
    project = load_project()

    result = analyze_float_consumption(
        project,
        "A005",
        1,
    )

    assert result["baseline_float"] == 2
    assert result["float_consumed"] == 1
    assert result["remaining_float"] == 1
    assert result["excess_delay"] == 0
    assert result["project_delay_days"] == 0


def test_two_day_delay_consumes_all_float():
    project = load_project()

    result = analyze_float_consumption(
        project,
        "A005",
        2,
    )

    assert result["baseline_float"] == 2
    assert result["float_consumed"] == 2
    assert result["remaining_float"] == 0
    assert result["excess_delay"] == 0
    assert result["project_delay_days"] == 0


def test_three_day_delay_exceeds_float():
    project = load_project()

    result = analyze_float_consumption(
        project,
        "A005",
        3,
    )

    assert result["baseline_float"] == 2
    assert result["float_consumed"] == 2
    assert result["remaining_float"] == 0
    assert result["excess_delay"] == 1
    assert result["project_delay_days"] == 1


def test_critical_activity_has_zero_float():
    project = load_project()

    result = analyze_float_consumption(
        project,
        "A004",
        2,
    )

    assert result["baseline_float"] == 0
    assert result["float_consumed"] == 0
    assert result["remaining_float"] == 0
    assert result["excess_delay"] == 2
    assert result["project_delay_days"] == 2


def test_negative_delay_is_rejected():
    project = load_project()

    with pytest.raises(ValueError):
        analyze_float_consumption(
            project,
            "A005",
            -1,
        )