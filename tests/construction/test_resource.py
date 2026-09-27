import pytest
from pydantic import ValidationError

from src.construction.models.resource import (
    Resource,
    ResourceType,
)


def test_material_resource_creation():
    resource = Resource(
        resource_id="R001",
        resource_name="Concrete",
        resource_type=ResourceType.MATERIAL,
        unit="m3",
        available_quantity=500,
    )

    assert resource.resource_id == "R001"
    assert resource.resource_name == "Concrete"
    assert resource.resource_type == ResourceType.MATERIAL
    assert resource.unit == "m3"
    assert resource.available_quantity == 500


def test_labour_resource_creation():
    resource = Resource(
        resource_id="R002",
        resource_name="Masonry Crew",
        resource_type=ResourceType.LABOUR,
        unit="crew",
        available_quantity=4,
    )

    assert resource.resource_type == ResourceType.LABOUR
    assert resource.available_quantity == 4


def test_equipment_resource_creation():
    resource = Resource(
        resource_id="R003",
        resource_name="Concrete Mixer",
        resource_type=ResourceType.EQUIPMENT,
        unit="unit",
        available_quantity=2,
    )

    assert resource.resource_type == ResourceType.EQUIPMENT
    assert resource.available_quantity == 2


def test_resource_allows_zero_quantity():
    resource = Resource(
        resource_id="R004",
        resource_name="Steel",
        resource_type=ResourceType.MATERIAL,
        unit="tonne",
        available_quantity=0,
    )

    assert resource.available_quantity == 0


def test_resource_rejects_negative_quantity():
    with pytest.raises(ValidationError):
        Resource(
            resource_id="R005",
            resource_name="Concrete",
            resource_type=ResourceType.MATERIAL,
            unit="m3",
            available_quantity=-10,
        )


def test_resource_requires_name():
    with pytest.raises(ValidationError):
        Resource(
            resource_id="R006",
            resource_name="",
            resource_type=ResourceType.MATERIAL,
            unit="m3",
            available_quantity=100,
        )


def test_resource_requires_unit():
    with pytest.raises(ValidationError):
        Resource(
            resource_id="R007",
            resource_name="Concrete",
            resource_type=ResourceType.MATERIAL,
            unit="",
            available_quantity=100,
        )


def test_resource_accepts_description():
    resource = Resource(
        resource_id="R008",
        resource_name="Concrete",
        resource_type=ResourceType.MATERIAL,
        unit="m3",
        available_quantity=500,
        description="Ready-mix concrete",
    )

    assert resource.description == "Ready-mix concrete"