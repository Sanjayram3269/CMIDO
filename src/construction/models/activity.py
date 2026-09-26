from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ActivityStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


class Activity(BaseModel):
    activity_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)

    activity_code: str = Field(min_length=1)
    activity_name: str = Field(min_length=1)
    description: str | None = None

    duration_days: float = Field(gt=0)

    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = None

    status: ActivityStatus = ActivityStatus.NOT_STARTED

    planned_start: date | None = None
    planned_finish: date | None = None

    actual_start: date | None = None
    actual_finish: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "Activity":
        if (
            self.planned_start is not None
            and self.planned_finish is not None
            and self.planned_finish < self.planned_start
        ):
            raise ValueError(
                "planned_finish cannot be earlier than planned_start"
            )

        if (
            self.actual_start is not None
            and self.actual_finish is not None
            and self.actual_finish < self.actual_start
        ):
            raise ValueError(
                "actual_finish cannot be earlier than actual_start"
            )

        return self
