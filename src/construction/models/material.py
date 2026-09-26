from __future__ import annotations

from pydantic import BaseModel, Field


class Material(BaseModel):
    material_id: str = Field(min_length=1)
    material_name: str = Field(min_length=1)

    category: str | None = None
    unit: str = Field(min_length=1)


class ActivityMaterial(BaseModel):
    activity_id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)

    quantity_required: float = Field(ge=0)
    unit: str = Field(min_length=1)

    consumption_factor: float | None = Field(default=None, ge=0)

    required_offset_days: float = 0
