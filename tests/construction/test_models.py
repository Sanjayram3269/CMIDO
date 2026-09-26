from datetime import date

import pytest
from pydantic import ValidationError

from src.construction.models import (
    Activity,
    ActivityProgress,
    Dependency,
    DependencyType,
    Material,
    Project,
    SupplierMaterial,
    WorkingCalendar,
)


def test_valid_project():
    project = Project(
        project_id="P001",
        project_name="Residential Building",
        location="Bengaluru",
        project_type="Residential",
        start_date=date(2026, 10, 1),
        planned_end_date=date(2027, 6, 30),
        calendar_id="CAL-5D",
    )

    assert project.project_id == "P001"


def test_project_rejects_invalid_dates():
    with pytest.raises(ValidationError):
        Project(
            project_id="P001",
            project_name="Invalid Project",
            start_date=date(2027, 1, 1),
            planned_end_date=date(2026, 1, 1),
            calendar_id="CAL-5D",
        )


def test_valid_activity():
    activity = Activity(
        activity_id="A001",
        project_id="P001",
        activity_code="A001",
        activity_name="Excavation",
        duration_days=10,
        quantity=450,
        unit="m3",
    )

    assert activity.duration_days == 10
    assert activity.quantity == 450


def test_activity_rejects_zero_duration():
    with pytest.raises(ValidationError):
        Activity(
            activity_id="A001",
            project_id="P001",
            activity_code="A001",
            activity_name="Excavation",
            duration_days=0,
        )


def test_activity_rejects_invalid_planned_dates():
    with pytest.raises(ValidationError):
        Activity(
            activity_id="A001",
            project_id="P001",
            activity_code="A001",
            activity_name="Excavation",
            duration_days=5,
            planned_start=date(2026, 10, 10),
            planned_finish=date(2026, 10, 5),
        )


def test_valid_dependency():
    dependency = Dependency(
        dependency_id="D001",
        project_id="P001",
        predecessor_id="A001",
        successor_id="A002",
        relationship_type=DependencyType.FINISH_TO_START,
    )

    assert dependency.relationship_type == DependencyType.FINISH_TO_START


def test_dependency_rejects_self_reference():
    with pytest.raises(ValidationError):
        Dependency(
            dependency_id="D001",
            project_id="P001",
            predecessor_id="A001",
            successor_id="A001",
        )


def test_valid_material():
    material = Material(
        material_id="M001",
        material_name="Concrete",
        category="Structural",
        unit="m3",
    )

    assert material.material_name == "Concrete"


def test_valid_supplier_material():
    supplier_material = SupplierMaterial(
        supplier_id="S001",
        material_id="M001",
        unit_price=6500,
        capacity=100,
        lead_time_days=7,
        minimum_order_quantity=10,
    )

    assert supplier_material.capacity == 100
    assert supplier_material.lead_time_days == 7


def test_progress_percentage_bounds():
    progress = ActivityProgress(
        activity_id="A001",
        percent_complete=75,
    )

    assert progress.percent_complete == 75


def test_progress_rejects_over_100():
    with pytest.raises(ValidationError):
        ActivityProgress(
            activity_id="A001",
            percent_complete=101,
        )


def test_working_calendar_default():
    calendar = WorkingCalendar(
        calendar_id="CAL-5D",
        name="Standard 5-Day Calendar",
    )

    assert calendar.working_weekdays == [0, 1, 2, 3, 4]
