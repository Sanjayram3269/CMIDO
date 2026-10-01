import pytest

from src.construction.experiments import ExperimentConfig


def test_experiment_config_is_serializable():
    config = ExperimentConfig(
        experiment_id="EXP-001",
        name="baseline",
        seed=42,
        parameters={"delay": 3},
    )
    assert config.to_dict()["seed"] == 42
    assert config.to_dict()["parameters"] == {"delay": 3}


def test_invalid_config_is_rejected():
    with pytest.raises(ValueError):
        ExperimentConfig("", "baseline")

    with pytest.raises(ValueError):
        ExperimentConfig("EXP-001", "baseline", seed="42")
