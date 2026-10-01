import pytest

from src.construction.experiments.normalization import (
    normalize_activity,
    normalize_dataset,
    normalize_dependency,
    normalize_project,
)


def raw_dataset():
    return {
        "project": {"project": "P-REAL", "name": "Real Construction Project"},
        "activities": [
            {"task_id": "T1", "task_name": "Foundation", "duration": "5"},
            {"task_id": "T2", "task_name": "Structure", "duration": 8},
        ],
        "dependencies": [
            {"predecessor": "T1", "successor": "T2", "type": "FS"},
        ],
    }


def test_project_aliases_are_normalized():
    result = normalize_project(raw_dataset()["project"])
    assert result == {
        "project_id": "P-REAL",
        "project_name": "Real Construction Project",
    }


def test_activity_aliases_and_numeric_duration_are_normalized():
    result = normalize_activity(
        raw_dataset()["activities"][0],
        project_id="P-REAL",
    )
    assert result["activity_id"] == "T1"
    assert result["activity_code"] == "T1"
    assert result["duration_days"] == 5.0


def test_dependency_aliases_are_normalized():
    result = normalize_dependency(
        raw_dataset()["dependencies"][0],
        project_id="P-REAL",
        dependency_index=1,
    )
    assert result["dependency_id"] == "D0001"
    assert result["predecessor_id"] == "T1"
    assert result["successor_id"] == "T2"
    assert result["relationship_type"] == "FS"


def test_full_dataset_normalization_is_explicit_and_deterministic():
    result = normalize_dataset(
        raw_dataset(),
        source="real_source.csv",
        dataset_id="REAL_001",
    )
    assert result["schema_version"] == "8I-1.0"
    assert result["dataset_id"] == "REAL_001"
    assert result["project"]["project_id"] == "P-REAL"
    assert [a["activity_id"] for a in result["activities"]] == ["T1", "T2"]
    assert result["dependencies"][0]["predecessor_id"] == "T1"


def test_missing_required_source_field_is_rejected():
    raw = raw_dataset()
    del raw["activities"][0]["task_name"]
    with pytest.raises(ValueError, match="activity_name"):
        normalize_dataset(raw)


def test_unknown_dependency_reference_is_rejected():
    raw = raw_dataset()
    raw["dependencies"][0]["successor"] = "UNKNOWN"
    with pytest.raises(ValueError, match="unknown successor"):
        normalize_dataset(raw)


def test_invalid_relationship_type_is_rejected():
    raw = raw_dataset()
    raw["dependencies"][0]["type"] = "INVALID"
    with pytest.raises(ValueError, match="invalid relationship_type"):
        normalize_dataset(raw)


def test_negative_quantity_is_rejected():
    raw = raw_dataset()
    raw["activities"][0]["quantity"] = -2
    with pytest.raises(ValueError, match="quantity"):
        normalize_dataset(raw)
