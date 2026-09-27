import json

import pytest

from src.construction.scheduling import calculate_forward_pass
from src.construction.time_phased_resources import (
    build_time_phased_resource_demand,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_time_phased_resource_demand_contains_all_requirements():
    project = load_project()

    schedule = calculate_forward_pass(project)

    result = build_time_phased_resource_demand(
        project,
        schedule,
    )

    assert len(result) == len(
        project["activity_materials"]
    )


def test_foundation_concrete_is_time_phased():
    project = load_project()

    schedule = calculate_forward_pass(project)

    result = build_time_phased_resource_demand(
        project,
        schedule,
    )

    foundation_concrete = next(
        item
        for item in result
        if (
            item["activity_id"] == "A003"
            and item["material_id"] == "M001"
        )
    )

    assert foundation_concrete["activity_name"] == "Foundation"
    assert foundation_concrete["material_name"] == "Concrete"
    assert foundation_concrete["quantity"] == 120
    assert foundation_concrete["unit"] == "m3"
    assert foundation_concrete["start_day"] == 13
    assert foundation_concrete["finish_day"] == 25


def test_slab_concrete_is_time_phased():
    project = load_project()

    schedule = calculate_forward_pass(project)

    result = build_time_phased_resource_demand(
        project,
        schedule,
    )

    slab_concrete = next(
        item
        for item in result
        if (
            item["activity_id"] == "A006"
            and item["material_id"] == "M001"
        )
    )

    assert slab_concrete["quantity"] == 180
    assert slab_concrete["start_day"] == 33
    assert slab_concrete["finish_day"] == 43


def test_material_name_and_unit_are_resolved():
    project = load_project()

    schedule = calculate_forward_pass(project)

    result = build_time_phased_resource_demand(
        project,
        schedule,
    )

    concrete_records = [
        item
        for item in result
        if item["material_id"] == "M001"
    ]

    assert len(concrete_records) == 3

    for item in concrete_records:
        assert item["material_name"] == "Concrete"
        assert item["unit"] == "m3"


def test_missing_activity_schedule_is_rejected():
    project = load_project()

    schedule = calculate_forward_pass(project)

    incomplete_schedule = [
        item
        for item in schedule
        if item["activity_id"] != "A003"
    ]

    with pytest.raises(ValueError):
        build_time_phased_resource_demand(
            project,
            incomplete_schedule,
        )


def test_unknown_material_is_rejected():
    project = load_project()

    project["activity_materials"].append(
    {
        "activity_id": "A003",
        "material_id": "UNKNOWN",
        "quantity_required": 10,
        "unit": "m3",
    }
)

    schedule = calculate_forward_pass(project)

    with pytest.raises(ValueError):
        build_time_phased_resource_demand(
            project,
            schedule,
        )