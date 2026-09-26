from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ActivityProgress(BaseModel):
    activity_id: str = Field(min_length=1)

    planned_start: date | None = None
    planned_finish: date | None = None

    actual_start: date | None = None
    actual_finish: date | None = None

    percent_complete: float = Field(default=0, ge=0, le=100)

    delay_days: float = Field(default=0, ge=0)
