import json

import pytest

from src.construction.integration.decision_context import (
    build_decision_context,
)


PROJECT_PATH = (
    "data/projects/cmido_demo_project.json"
)


AVAILABLE_RESOURCES = {
    "M001": 500,
    "M002": 100,
    "M003": 100,
    "M004": 500,
    "M005": 20000,
    "M006": 2000,
    "M007": 2000,
    "M008": 20,
    "M009": 20,
}


def load_project():
    with open(
        PROJECT_PATH,
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_decision_context_contains_all_domains():

    result = build_decision_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert "project" in result
    assert "baseline" in result
    assert "materials" in result
    assert "activities" in result
    assert "resources" in result
    assert "procurement" in result
    assert "schedule_impacts" in result
    assert "project_impact" in result
    assert "decision" in result


def test_baseline_is_preserved():

    result = build_decision_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert (
        result["baseline"][
            "project_duration_days"
        ]
        == 74
    )

    assert result["baseline"][
        "critical_path"
    ] == [
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


def test_baseline_project_is_feasible():

    result = build_decision_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert result[
        "decision"
    ]["status"] == "FEASIBLE"

    assert result[
        "project_impact"
    ]["project_delay_days"] == 0


def test_delay_scenario_is_integrated():

    result = build_decision_context(
        load_project(),
        AVAILABLE_RESOURCES,
        [
            {
                "activity_id": "A006",
                "delay_days": 3,
            }
        ],
    )

    assert len(
        result["schedule_impacts"]
    ) == 1

    scenario = result[
        "schedule_impacts"
    ][0]

    assert scenario[
        "scenario"
    ]["activity_id"] == "A006"

    assert scenario[
        "scenario"
    ]["delay_days"] == 3

    assert scenario[
        "schedule"
    ]["project_delay_days"] == 3


def test_project_impact_is_propagated():

    result = build_decision_context(
        load_project(),
        AVAILABLE_RESOURCES,
        [
            {
                "activity_id": "A006",
                "delay_days": 3,
            }
        ],
    )

    assert result[
        "project_impact"
    ]["baseline_duration_days"] == 74

    assert result[
        "project_impact"
    ]["scenario_duration_days"] == 77

    assert result[
        "project_impact"
    ]["project_delay_days"] == 3

    assert result[
        "decision"
    ]["status"] == "PROJECT_DELAY"


def test_multiple_delay_scenarios_are_supported():

    result = build_decision_context(
        load_project(),
        AVAILABLE_RESOURCES,
        [
            {
                "activity_id": "A006",
                "delay_days": 3,
            },
            {
                "activity_id": "A005",
                "delay_days": 1,
            },
        ],
    )

    assert len(
        result["schedule_impacts"]
    ) == 2

    assert result[
        "project_impact"
    ]["project_delay_days"] == 3


def test_non_critical_delay_can_be_absorbed():

    result = build_decision_context(
        load_project(),
        AVAILABLE_RESOURCES,
        [
            {
                "activity_id": "A005",
                "delay_days": 1,
            }
        ],
    )

    assert result[
        "project_impact"
    ]["project_delay_days"] == 0

    assert result[
        "decision"
    ]["status"] == "FEASIBLE"


def test_negative_delay_is_rejected():

    with pytest.raises(ValueError):

        build_decision_context(
            load_project(),
            AVAILABLE_RESOURCES,
            [
                {
                    "activity_id": "A006",
                    "delay_days": -1,
                }
            ],
        )


def test_missing_delay_field_is_rejected():

    with pytest.raises(ValueError):

        build_decision_context(
            load_project(),
            AVAILABLE_RESOURCES,
            [
                {
                    "activity_id": "A006",
                }
            ],
        )


def test_invalid_delay_scenario_type_is_rejected():

    with pytest.raises(ValueError):

        build_decision_context(
            load_project(),
            AVAILABLE_RESOURCES,
            {},
        )