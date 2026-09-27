import json

from src.construction.time_phased_resource_integration import (
    build_time_phased_resource_integration,
)


PROJECT_PATH = (
    "data/projects/cmido_demo_project.json"
)


def load_project():
    with open(
        PROJECT_PATH,
        encoding="utf-8",
    ) as file:
        return json.load(file)


def build_schedule():
    return [
        {
            "activity_id": "A001",
            "es": 0,
            "ef": 5,
        },
        {
            "activity_id": "A002",
            "es": 5,
            "ef": 13,
        },
        {
            "activity_id": "A003",
            "es": 13,
            "ef": 25,
        },
        {
            "activity_id": "A004",
            "es": 25,
            "ef": 33,
        },
        {
            "activity_id": "A005",
            "es": 25,
            "ef": 31,
        },
        {
            "activity_id": "A006",
            "es": 33,
            "ef": 43,
        },
        {
            "activity_id": "A007",
            "es": 43,
            "ef": 55,
        },
        {
            "activity_id": "A008",
            "es": 55,
            "ef": 63,
        },
        {
            "activity_id": "A009",
            "es": 63,
            "ef": 70,
        },
        {
            "activity_id": "A010",
            "es": 63,
            "ef": 69,
        },
        {
            "activity_id": "A011",
            "es": 70,
            "ef": 74,
        },
    ]


def full_supply():
    return {
        "M001": 500,
        "M002": 100,
        "M003": 100,
        "M004": 500,
        "M005": 20000,
        "M006": 2000,
        "M007": 2000,
        "M008": 20,
        "M009": 20,
    }


def test_integration_contains_all_materials():
    project = load_project()

    result = build_time_phased_resource_integration(
        project,
        build_schedule(),
        full_supply(),
    )

    assert result["summary"][
        "total_resources"
    ] == 9

    assert len(
        result["resources"]
    ) == 9


def test_full_supply_is_feasible():
    project = load_project()

    result = build_time_phased_resource_integration(
        project,
        build_schedule(),
        full_supply(),
    )

    assert result["summary"][
        "feasible_resources"
    ] == 9

    assert result["summary"][
        "shortage_resources"
    ] == 0


def test_concrete_demand_is_360():
    project = load_project()

    result = build_time_phased_resource_integration(
        project,
        build_schedule(),
        full_supply(),
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    assert concrete[
        "total_required"
    ] == 360

    assert concrete[
        "total_allocated"
    ] == 360

    assert concrete[
        "total_shortage"
    ] == 0


def test_concrete_shortage_is_detected():
    project = load_project()

    supply = full_supply()
    supply["M001"] = 300

    result = build_time_phased_resource_integration(
        project,
        build_schedule(),
        supply,
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    assert concrete[
        "status"
    ] == "SHORTAGE"

    assert concrete[
        "total_required"
    ] == 360

    assert concrete[
        "total_allocated"
    ] == 300

    assert concrete[
        "total_shortage"
    ] == 60


def test_concrete_allocations_preserve_activity_order():
    project = load_project()

    result = build_time_phased_resource_integration(
        project,
        build_schedule(),
        full_supply(),
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    allocations = concrete[
        "allocations"
    ]

    assert [
        item["activity_id"]
        for item in allocations
    ] == [
        "A003",
        "A004",
        "A006",
    ]


def test_concrete_shortage_affects_final_activity():
    project = load_project()

    supply = full_supply()
    supply["M001"] = 300

    result = build_time_phased_resource_integration(
        project,
        build_schedule(),
        supply,
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    affected = concrete[
        "affected_activities"
    ]

    assert len(affected) == 1

    assert affected[0][
        "activity_id"
    ] == "A006"

    assert affected[0][
        "shortage_quantity"
    ] == 60


def test_missing_resource_means_zero_supply():
    project = load_project()

    result = build_time_phased_resource_integration(
        project,
        build_schedule(),
        {},
    )

    concrete = next(
        item
        for item in result["resources"]
        if item["resource_id"] == "M001"
    )

    assert concrete[
        "available_quantity"
    ] == 0

    assert concrete[
        "total_shortage"
    ] == 360


def test_summary_totals_are_consistent():
    project = load_project()

    result = build_time_phased_resource_integration(
        project,
        build_schedule(),
        full_supply(),
    )

    summary = result["summary"]

    assert (
        summary["total_required"]
        == summary["total_allocated"]
    )

    assert (
        summary["total_shortage"]
        == 0
    )