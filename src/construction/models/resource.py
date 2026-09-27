from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    MATERIAL = "MATERIAL"
    LABOUR = "LABOUR"
    EQUIPMENT = "EQUIPMENT"


class Resource(BaseModel):
    """
    Represents a construction resource available
    for project execution.
    """

    resource_id: str = Field(
        min_length=1,
        description="Unique resource identifier",
    )

    resource_name: str = Field(
        min_length=1,
        description="Human-readable resource name",
    )

    resource_type: ResourceType

    unit: str = Field(
        min_length=1,
        description="Measurement unit",
    )

    available_quantity: float = Field(
        ge=0,
        description="Available quantity of the resource",
    )

    description: str | None = None