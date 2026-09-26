from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class WorkingCalendar(BaseModel):
    calendar_id: str = Field(min_length=1)
    name: str = Field(min_length=1)

    working_weekdays: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4]
    )

    holidays: list[date] = Field(default_factory=list)
