import json

import pytest

from src.construction.uncertainty.scenario import (
    build_risk_scenario,
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


def test_schedule_risk_scenario_is_integrated():

    result = build_risk_scenario(
        load_project(),
        {
            "risk_id": "R001",
            "risk_type": "SCHEDULE",
            "description": "Activity delay",
            "severity": "HIGH",
            "probability": 0.4,
            "impact_days": 3,
            "activity_id": "A006",
        },
    )

    assert result["risk"]["risk_id"] == "R001"

    assert result[
        "scenario"
    ]["activity_id"] == "A006"

    assert result[
        "scenario"
    ]["impact_days"] == 3

    assert result[
        "schedule"
    ]["project_delay_days"] == 3


def test_non_critical_risk_can_be_absorbed():

    result = build_risk_scenario(
        load_project(),
        {
            "risk_id": "R002",
            "risk_type": "SCHEDULE",
            "description": "Small activity delay",
            "severity": "LOW",
            "probability": 0.2,
            "impact_days": 1,
            "activity_id": "A005",
        },
    )

    assert result[
        "schedule"
    ]["project_delay_days"] == 0


def test_risk_without_activity_has_no_schedule_simulation():

    result = build_risk_scenario(
        load_project(),
        {
            "risk_id": "R003",
            "risk_type": "COST",
            "description": "Material cost increase",
            "severity": "MEDIUM",
            "probability": 0.3,
            "impact_days": 0,
        },
    )

    assert result["schedule"] is None

    assert result[
        "risk"
    ]["risk_type"] == "COST"


def test_invalid_risk_is_rejected():

    with pytest.raises(ValueError):

        build_risk_scenario(
            load_project(),
            {
                "risk_id": "R004",
                "risk_type": "INVALID",
                "description": "Invalid risk",
                "severity": "LOW",
                "probability": 0.2,
                "impact_days": 1,
                "activity_id": "A006",
            },
        )


def test_missing_risk_field_is_rejected():

    with pytest.raises(ValueError):

        build_risk_scenario(
            load_project(),
            {
                "risk_id": "R005",
                "risk_type": "SCHEDULE",
                "description": "Missing probability",
                "severity": "LOW",
                "impact_days": 1,
                "activity_id": "A006",
            },
        )