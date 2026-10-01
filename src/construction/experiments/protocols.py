from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .factors import (
    VALID_CONFIGURATIONS,
    VALID_SCENARIO_TYPES,
    validate_configuration,
    validate_scenario_type,
)


CONFIGURATION_ORDER = (
    "CPM",
    "CPM_DELAY",
    "INTEGRATED_OPERATIONAL",
    "FULL_CMIDO",
)


@dataclass(frozen=True)
class ExperimentalConfiguration:
    """Named CMIDO analysis configuration used as a research factor."""

    configuration_id: str
    name: str
    includes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.configuration_id not in VALID_CONFIGURATIONS:
            raise ValueError(f"Invalid configuration_id: {self.configuration_id}")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("configuration name must be non-empty")
        if not self.includes:
            raise ValueError("configuration must include at least one component")

    def to_dict(self) -> dict[str, Any]:
        return {
            "configuration_id": self.configuration_id,
            "name": self.name,
            "includes": list(self.includes),
        }


CONFIGURATIONS = {
    "CPM": ExperimentalConfiguration("CPM", "CPM only", ("scheduling",)),
    "CPM_DELAY": ExperimentalConfiguration(
        "CPM_DELAY", "CPM + delay propagation", ("scheduling", "delay_simulation")
    ),
    "INTEGRATED_OPERATIONAL": ExperimentalConfiguration(
        "INTEGRATED_OPERATIONAL",
        "Integrated operational context",
        ("scheduling", "quantity", "procurement", "resources"),
    ),
    "FULL_CMIDO": ExperimentalConfiguration(
        "FULL_CMIDO",
        "Full CMIDO",
        ("scheduling", "quantity", "procurement", "resources", "risk", "scenario_analysis"),
    ),
}


@dataclass(frozen=True)
class ScenarioProtocol:
    """Controlled scenario definition for reproducible CMIDO experiments."""

    scenario_id: str
    scenario_type: str
    configuration: str
    factors: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("scenario_id must be a non-empty string")
        validate_scenario_type(self.scenario_type)
        validate_configuration(self.configuration)
        if not isinstance(self.factors, dict):
            raise ValueError("factors must be a dictionary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_type": self.scenario_type,
            "configuration": self.configuration,
            "factors": dict(self.factors),
        }


def get_experimental_configurations() -> list[dict[str, Any]]:
    """Return the registered research configurations in stable order."""
    return [CONFIGURATIONS[key].to_dict() for key in CONFIGURATION_ORDER]


def build_scenario_protocol(
    scenario_id: str,
    scenario_type: str,
    configuration: str,
    factors: dict[str, Any] | None = None,
) -> dict[str, Any]:
    protocol = ScenarioProtocol(
        scenario_id=scenario_id,
        scenario_type=scenario_type,
        configuration=configuration,
        factors={} if factors is None else factors,
    )
    return protocol.to_dict()
