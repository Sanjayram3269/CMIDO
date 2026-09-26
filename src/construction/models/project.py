from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class Project(BaseModel):
    project_id: str = Field(min_length=1)
    project_name: str = Field(min_length=1)

    location: str | None = None
    project_type: str | None = None

    start_date: date
    planned_end_date: date

    calendar_id: str = Field(min_length=1)

    status: str = "planned"

    @model_validator(mode="after")
    def validate_dates(self) -> "Project":
        if self.planned_end_date < self.start_date:
            raise ValueError(
                "planned_end_date cannot be earlier than start_date"
            )
        return self
