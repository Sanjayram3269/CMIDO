from __future__ import annotations

from pydantic import BaseModel, Field


class Supplier(BaseModel):
    supplier_id: str = Field(min_length=1)
    supplier_name: str = Field(min_length=1)

    location: str | None = None


class SupplierMaterial(BaseModel):
    supplier_id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)

    unit_price: float = Field(ge=0)
    capacity: float = Field(gt=0)
    lead_time_days: float = Field(ge=0)

    minimum_order_quantity: float = Field(default=0, ge=0)
