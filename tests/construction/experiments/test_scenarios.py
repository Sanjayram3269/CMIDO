import pytest

from src.construction.experiments import (
    build_delay_scenarios,
    validate_scenario,
)


def test_delay_scenarios_are_deterministic():
    assert build_delay_scenarios("A005", [0, 1, 3]) == [
        {"activity_id": "A005", "delay_days": 0},
        {"activity_id": "A005", "delay_days": 1},
        {"activity_id": "A005", "delay_days": 3},
    ]


def test_invalid_scenario_is_rejected():
    with pytest.raises(ValueError):
        validate_scenario({"activity_id": "A005", "delay_days": -1})

    with pytest.raises(ValueError):
        validate_scenario({"activity_id": "A005", "delay_days": 1.5})
