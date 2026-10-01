import pytest

from src.construction.uncertainty.risk import (
    build_risk,
)


def test_build_schedule_risk():

    result = build_risk(
        risk_id="R001",
        risk_type="SCHEDULE",
        description="Activity may be delayed",
        severity="HIGH",
        probability=0.4,
        impact_days=3,
        activity_id="A006",
    )

    assert result["risk_id"] == "R001"
    assert result["risk_type"] == "SCHEDULE"
    assert result["severity"] == "HIGH"
    assert result["probability"] == 0.4
    assert result["impact_days"] == 3
    assert result["activity_id"] == "A006"


def test_build_procurement_risk():

    result = build_risk(
        risk_id="R002",
        risk_type="PROCUREMENT",
        description="Material delivery may be delayed",
        severity="MEDIUM",
        probability=0.25,
        impact_days=2,
        material_id="M001",
    )

    assert result["risk_type"] == "PROCUREMENT"
    assert result["material_id"] == "M001"


def test_invalid_probability_is_rejected():

    with pytest.raises(ValueError):
        build_risk(
            risk_id="R003",
            risk_type="SCHEDULE",
            description="Invalid probability",
            severity="LOW",
            probability=1.5,
        )


def test_negative_impact_is_rejected():

    with pytest.raises(ValueError):
        build_risk(
            risk_id="R004",
            risk_type="SCHEDULE",
            description="Negative impact",
            severity="LOW",
            probability=0.2,
            impact_days=-1,
        )


def test_invalid_risk_type_is_rejected():

    with pytest.raises(ValueError):
        build_risk(
            risk_id="R005",
            risk_type="INVALID",
            description="Invalid type",
            severity="LOW",
            probability=0.2,
        )