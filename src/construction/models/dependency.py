from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class DependencyType(str, Enum):
    FINISH_TO_START = "FS"
    START_TO_START = "SS"
    FINISH_TO_FINISH = "FF"
    START_TO_FINISH = "SF"


class Dependency(BaseModel):
    dependency_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)

    predecessor_id: str = Field(min_length=1)
    successor_id: str = Field(min_length=1)

    relationship_type: DependencyType = DependencyType.FINISH_TO_START

    lag_days: float = 0

    @model_validator(mode="after")
    def validate_dependency(self) -> "Dependency":
        if self.predecessor_id == self.successor_id:
            raise ValueError(
                "predecessor_id and successor_id must be different"
            )

        if self.lag_days < 0:
            raise ValueError("lag_days cannot be negative")

        return self
