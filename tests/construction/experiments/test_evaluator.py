import json

import pytest

from src.construction.experiments import (
    evaluate_schedule_scenario,
)


PROJECT_PATH = "data/projects/cmido_demo_project.json"


def load_project():
    with open(
        PROJECT_PATH,
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_real_cmido_evaluator_zero_delay():
    result = evaluate_schedule_scenario(
        load_project(),
        "A005",
        0,
    )

    assert result["baseline_project_duration"] == 74
    assert result["scenario_project_duration"] == 74
    assert result["project_delay_days"] == 0


def test_real_cmido_evaluator_critical_delay():
    result = evaluate_schedule_scenario(
        load_project(),
        "A006",
        3,
    )

    assert result["baseline_project_duration"] == 74
    assert result["scenario_project_duration"] == 77
    assert result["project_delay_days"] == 3


def test_real_cmido_evaluator_rejects_negative_delay():
    with pytest.raises(ValueError):
        evaluate_schedule_scenario(
            load_project(),
            "A006",
            -1,
        )


def test_real_cmido_evaluator_rejects_invalid_activity():
    with pytest.raises(ValueError):
        evaluate_schedule_scenario(
            load_project(),
            "INVALID",
            1,
        )
