from __future__ import annotations

import json

import pytest

from src.construction.integration import (
    build_project_context,
)


PROJECT_PATH = (
    "data/projects/cmido_demo_project.json"
)


def load_project() -> dict:
    with open(
        PROJECT_PATH,
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_project_context_contains_all_core_domains():
    result = build_project_context(
        load_project()
    )

    assert "project" in result
    assert "schedule" in result
    assert "activities" in result
    assert "materials" in result


def test_project_context_contains_project_identity():
    result = build_project_context(
        load_project()
    )

    assert result["project"]["project_id"] == (
        "CMIDO-DEMO-001"
    )

    assert result["project"]["project_name"] == (
        "Residential Building Demo"
    )


def test_project_context_contains_baseline_schedule():
    result = build_project_context(
        load_project()
    )

    assert result[
        "schedule"
    ]["project_duration_days"] == 74


def test_project_context_contains_critical_path():
    result = build_project_context(
        load_project()
    )

    assert result[
        "schedule"
    ]["critical_path"] == [
        "A001",
        "A002",
        "A003",
        "A004",
        "A006",
        "A007",
        "A008",
        "A009",
        "A011",
    ]


def test_project_context_contains_critical_activities():
    result = build_project_context(
        load_project()
    )

    critical_ids = {
        item["activity_id"]
        for item in result[
            "schedule"
        ]["critical_activities"]
    }

    assert "A001" in critical_ids
    assert "A006" in critical_ids
    assert "A011" in critical_ids


def test_project_context_contains_non_critical_activities():
    result = build_project_context(
        load_project()
    )

    non_critical_ids = {
        item["activity_id"]
        for item in result[
            "schedule"
        ]["non_critical_activities"]
    }

    assert len(non_critical_ids) > 0


def test_project_context_contains_activity_summary():
    result = build_project_context(
        load_project()
    )

    activities = result["activities"]

    assert len(activities) > 0

    first = activities[0]

    assert "activity_id" in first
    assert "activity_name" in first
    assert "duration_days" in first
    assert "is_critical" in first


def test_project_context_contains_material_requirements():
    result = build_project_context(
        load_project()
    )

    materials = result["materials"]

    assert "total_material_types" in materials
    assert "requirements" in materials

    assert (
        materials["total_material_types"]
        == len(materials["requirements"])
    )

    assert (
        materials["total_material_types"] > 0
    )


def test_project_context_preserves_material_requirement_data():
    result = build_project_context(
        load_project()
    )

    requirements = result[
        "materials"
    ]["requirements"]

    requirement = requirements[0]

    assert "material_id" in requirement
    assert "material_name" in requirement
    assert "total_quantity" in requirement
    assert "unit" in requirement


def test_invalid_project_data_is_rejected():
    with pytest.raises(ValueError):
        build_project_context(
            []
        )


def test_missing_project_data_is_rejected():
    project = load_project()

    del project["project"]

    with pytest.raises(ValueError):
        build_project_context(project)


def test_missing_material_data_is_rejected():
    project = load_project()

    del project["materials"]

    with pytest.raises(ValueError):
        build_project_context(project)


def test_missing_activity_material_mapping_is_rejected():
    project = load_project()

    del project["activity_materials"]

    with pytest.raises(ValueError):
        build_project_context(project)