import json

import pytest

from src.construction.uncertainty.context import (
    build_uncertainty_context,
)


PROJECT_PATH = (
    "data/projects/cmido_demo_project.json"
)


def load_project():

    with open(
        PROJECT_PATH,
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_uncertainty_context_contains_all_domains():

    result = build_uncertainty_context(
        load_project()
    )

    assert "baseline" in result
    assert "risks" in result
    assert "risk_summary" in result
    assert "scenarios" in result
    assert "project_impact" in result


def test_baseline_is_preserved():

    result = build_uncertainty_context(
        load_project()
    )

    assert result[
        "baseline"
    ][
        "project_duration_days"
    ] == 74

    assert result[
        "baseline"
    ][
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


def test_risks_are_integrated():

    result = build_uncertainty_context(
        load_project(),
        [
            {
                "risk_id": "R001",
                "risk_type": "SCHEDULE",
                "description": "Activity delay",
                "severity": "HIGH",
                "probability": 0.4,
                "impact_days": 3,
                "activity_id": "A006",
            }
        ],
    )

    assert len(
        result["risks"]
    ) == 1

    assert result[
        "risks"
    ][0][
        "risk_id"
    ] == "R001"

    assert result[
        "risk_summary"
    ][
        "total_risks"
    ] == 1

    assert result[
        "risk_summary"
    ][
        "schedule_risks"
    ] == 1

    assert result[
        "risk_summary"
    ][
        "high_risk_count"
    ] == 1


def test_schedule_scenario_is_integrated():

    result = build_uncertainty_context(
        load_project(),
        [
            {
                "risk_id": "R001",
                "risk_type": "SCHEDULE",
                "description": "Critical activity delay",
                "severity": "HIGH",
                "probability": 0.4,
                "impact_days": 3,
                "activity_id": "A006",
            }
        ],
    )

    assert len(
        result["scenarios"]
    ) == 1

    scenario = result[
        "scenarios"
    ][0]

    assert scenario[
        "scenario"
    ][
        "risk_id"
    ] == "R001"

    assert scenario[
        "schedule"
    ][
        "project_delay_days"
    ] == 3


def test_project_impact_is_propagated():

    result = build_uncertainty_context(
        load_project(),
        [
            {
                "risk_id": "R001",
                "risk_type": "SCHEDULE",
                "description": "Critical activity delay",
                "severity": "HIGH",
                "probability": 0.4,
                "impact_days": 3,
                "activity_id": "A006",
            }
        ],
    )

    assert result[
        "project_impact"
    ][
        "baseline_duration_days"
    ] == 74

    assert result[
        "project_impact"
    ][
        "scenario_duration_days"
    ] == 77

    assert result[
        "project_impact"
    ][
        "project_delay_days"
    ] == 3


def test_non_critical_risk_can_be_absorbed():

    result = build_uncertainty_context(
        load_project(),
        [
            {
                "risk_id": "R002",
                "risk_type": "SCHEDULE",
                "description": "Small delay",
                "severity": "LOW",
                "probability": 0.2,
                "impact_days": 1,
                "activity_id": "A005",
            }
        ],
    )

    assert result[
        "project_impact"
    ][
        "project_delay_days"
    ] == 0


def test_non_schedule_risk_is_preserved():

    result = build_uncertainty_context(
        load_project(),
        [
            {
                "risk_id": "R003",
                "risk_type": "COST",
                "description": "Material cost increase",
                "severity": "MEDIUM",
                "probability": 0.3,
                "impact_days": 0,
                "material_id": "M001",
            }
        ],
    )

    assert result[
        "risk_summary"
    ][
        "cost_risks"
    ] == 1

    assert result[
        "scenarios"
    ][0][
        "schedule"
    ] is None


def test_multiple_risks_are_supported():

    result = build_uncertainty_context(
        load_project(),
        [
            {
                "risk_id": "R001",
                "risk_type": "SCHEDULE",
                "description": "Critical delay",
                "severity": "HIGH",
                "probability": 0.4,
                "impact_days": 3,
                "activity_id": "A006",
            },
            {
                "risk_id": "R002",
                "risk_type": "SCHEDULE",
                "description": "Non-critical delay",
                "severity": "LOW",
                "probability": 0.2,
                "impact_days": 1,
                "activity_id": "A005",
            },
        ],
    )

    assert len(
        result["risks"]
    ) == 2

    assert len(
        result["scenarios"]
    ) == 2

    assert result[
        "project_impact"
    ][
        "project_delay_days"
    ] == 3


def test_invalid_risk_input_is_rejected():

    with pytest.raises(ValueError):

        build_uncertainty_context(
            load_project(),
            {},
        )


def test_missing_risk_field_is_rejected():

    with pytest.raises(ValueError):

        build_uncertainty_context(
            load_project(),
            [
                {
                    "risk_id": "R004",
                    "risk_type": "SCHEDULE",
                    "description": "Missing severity",
                    "probability": 0.2,
                    "impact_days": 1,
                }
            ],
        )