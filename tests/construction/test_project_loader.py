from pathlib import Path

from src.construction.loader import load_project_json
from src.construction.validation.project_validator import validate_project


PROJECT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "projects"
    / "cmido_demo_project.json"
)


def test_demo_project_loads():
    data = load_project_json(PROJECT_PATH)

    assert data["project"]["project_id"] == "CMIDO-DEMO-001"


def test_demo_project_passes_whole_project_validation():
    data = load_project_json(PROJECT_PATH)

    validate_project(data)


def test_demo_project_has_expected_counts():
    data = load_project_json(PROJECT_PATH)

    assert len(data["activities"]) == 11
    assert len(data["dependencies"]) == 12
    assert len(data["materials"]) == 9
    assert len(data["suppliers"]) == 6
