import pytest

from src.construction.experiments.experiment_design import (
    EXPERIMENTAL_METRICS,
    RESEARCH_HYPOTHESES,
    build_experiment_design,
)
from src.construction.experiments.factors import (
    build_factor_space,
    validate_configuration,
    validate_delay_levels,
)
from src.construction.experiments.protocols import (
    build_scenario_protocol,
    get_experimental_configurations,
)


def test_factor_space_is_deterministic():
    first = build_factor_space()
    second = build_factor_space()
    assert first == second
    assert first["delay_days"] == [0, 1, 3, 5, 7, 14]


def test_factor_validation_rejects_invalid_values():
    with pytest.raises(ValueError):
        validate_configuration("UNKNOWN")
    with pytest.raises(ValueError):
        validate_delay_levels([0, -1])
    with pytest.raises(ValueError):
        validate_delay_levels([0, 1, 1])


def test_protocol_is_serializable_and_validated():
    protocol = build_scenario_protocol(
        "E1_S001",
        "BASELINE",
        "CPM",
        {"delay_days": 0},
    )
    assert protocol == {
        "scenario_id": "E1_S001",
        "scenario_type": "BASELINE",
        "configuration": "CPM",
        "factors": {"delay_days": 0},
    }


def test_registered_configurations_are_stable():
    configurations = get_experimental_configurations()
    assert [item["configuration_id"] for item in configurations] == [
        "CPM",
        "CPM_DELAY",
        "INTEGRATED_OPERATIONAL",
        "FULL_CMIDO",
    ]


def test_experiment_design_builds_controlled_matrix():
    design = build_experiment_design(
        experiment_id="8G_TEST",
        project_id="CMIDO_DEMO",
        seed=42,
    )

    assert design["scenario_count"] == 24
    assert len(design["scenarios"]) == 24
    assert design["scenarios"][0]["scenario_id"] == "8G_TEST_S001"
    assert design["scenarios"][-1]["scenario_id"] == "8G_TEST_S024"
    assert design["metrics"] == list(EXPERIMENTAL_METRICS)
    assert design["hypotheses"] == RESEARCH_HYPOTHESES


def test_experiment_design_does_not_duplicate_configuration_scenarios():
    design = build_experiment_design(
        experiment_id="8G_SMALL",
        project_id="P1",
        configurations=("CPM", "FULL_CMIDO"),
        scenario_types=("BASELINE", "SCHEDULE_DELAY"),
    )
    assert design["scenario_count"] == 4
    assert [item["configuration"] for item in design["scenarios"]] == [
        "CPM",
        "CPM",
        "FULL_CMIDO",
        "FULL_CMIDO",
    ]


def test_experiment_design_rejects_duplicate_factors():
    with pytest.raises(ValueError):
        build_experiment_design(
            "8G_BAD",
            "P1",
            configurations=("CPM", "CPM"),
        )


def test_experiment_design_rejects_unknown_scenario():
    with pytest.raises(ValueError):
        build_experiment_design(
            "8G_BAD",
            "P1",
            scenario_types=("UNKNOWN",),
        )
