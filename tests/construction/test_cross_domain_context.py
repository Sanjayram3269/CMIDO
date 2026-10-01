import json

import pytest

from src.construction.integration.cross_domain_context import (
    build_cross_domain_context,
)


PROJECT_PATH = "data/projects/cmido_demo_project.json"

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
    with open(PROJECT_PATH, encoding="utf-8") as file:
        return json.load(file)


def test_cross_domain_context_contains_all_domains():
    result = build_cross_domain_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert "project" in result
    assert "baseline" in result
    assert "activities" in result
    assert "materials" in result
    assert "resources" in result
    assert "procurement" in result
    assert "delay_scenarios" in result
    assert "schedule_impacts" in result
    assert "risks" in result
    assert "risk_summary" in result
    assert "risk_scenarios" in result
    assert "project_impact" in result
    assert "decision" in result
    assert "evidence" in result


def test_cross_domain_baseline_is_preserved():
    result = build_cross_domain_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert result["baseline"]["project_duration_days"] == 74
    assert result["project_impact"]["baseline_duration_days"] == 74
    assert result["project_impact"]["project_delay_days"] == 0
    assert result["decision"]["status"] == "FEASIBLE"


def test_7c_c_delay_is_visible_in_7e():
    result = build_cross_domain_context(
        load_project(),
        AVAILABLE_RESOURCES,
        delay_scenarios=[
            {
                "activity_id": "A006",
                "delay_days": 3,
            }
        ],
    )

    assert len(result["schedule_impacts"]) == 1
    assert result["project_impact"]["schedule_delay_days"] == 3
    assert result["project_impact"]["project_delay_days"] == 3
    assert result["decision"]["status"] == "PROJECT_DELAY"
    assert result["evidence"]["delay_scenarios"]["count"] == 1


def test_7d_risk_is_visible_in_7e():
    result = build_cross_domain_context(
        load_project(),
        AVAILABLE_RESOURCES,
        risks=[
            {
                "risk_id": "R001",
                "risk_type": "SCHEDULE",
                "description": "Concrete placement delay",
                "severity": "HIGH",
                "probability": 0.4,
                "impact_days": 3,
                "activity_id": "A006",
            }
        ],
    )

    assert result["risk_summary"]["total_risks"] == 1
    assert result["risk_summary"]["schedule_risks"] == 1
    assert result["risk_summary"]["high_risk_count"] == 1
    assert len(result["risk_scenarios"]) == 1
    assert result["project_impact"]["risk_delay_days"] == 3
    assert result["project_impact"]["project_delay_days"] == 3


def test_7e_preserves_procurement_evidence():
    result = build_cross_domain_context(
        load_project(),
        AVAILABLE_RESOURCES,
    )

    assert result["procurement"]["total_requirements"] > 0
    assert (
        result["evidence"]["procurement"]["total_requirements"]
        == result["procurement"]["total_requirements"]
    )
    assert len(result["evidence"]["procurement"]["requirements"]) == (
        result["procurement"]["total_requirements"]
    )


def test_7e_rejects_invalid_delay_and_risk_containers():
    with pytest.raises(ValueError):
        build_cross_domain_context(
            load_project(),
            AVAILABLE_RESOURCES,
            delay_scenarios={},
        )

    with pytest.raises(ValueError):
        build_cross_domain_context(
            load_project(),
            AVAILABLE_RESOURCES,
            risks={},
        )
