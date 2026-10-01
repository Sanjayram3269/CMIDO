from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExperimentConfig:
    """Immutable configuration for a reproducible CMIDO experiment."""

    experiment_id: str
    name: str
    seed: int = 0
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.experiment_id, str) or not self.experiment_id.strip():
            raise ValueError("experiment_id must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        if not isinstance(self.parameters, dict):
            raise ValueError("parameters must be a dictionary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "seed": self.seed,
            "description": self.description,
            "parameters": dict(self.parameters),
        }
