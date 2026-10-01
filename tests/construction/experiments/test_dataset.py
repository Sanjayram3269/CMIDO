import pytest

from src.construction.experiments.dataset import (
    build_canonical_dataset,
    validate_dataset_structure,
)


def make_dataset():
    return build_canonical_dataset(
        {
            "project_id": "P1",
            "project_name": "Demo",
        },
        [
            {"activity_id": "A", "duration": 2},
            {"activity_id": "B", "duration": 3},
        ],
        [
            {"predecessor_id": "A", "successor_id": "B"},
        ],
        source="test",
        dataset_id="TEST_8H",
    )


def test_canonical_dataset_is_valid():
    dataset = make_dataset()
    result = validate_dataset_structure(dataset)

    assert result.valid is True
    assert result.project_count == 1
    assert result.activity_count == 2
    assert result.dependency_count == 1
    assert dataset["schema_version"] == "8H-1.0"


def test_duplicate_activity_ids_are_rejected():
    with pytest.raises(ValueError, match="duplicate activity_id"):
        build_canonical_dataset(
            {"project_id": "P1"},
            [
                {"activity_id": "A", "duration": 1},
                {"activity_id": "A", "duration": 2},
            ],
            [],
        )


def test_unknown_dependency_reference_is_rejected():
    with pytest.raises(ValueError, match="unknown successor"):
        build_canonical_dataset(
            {"project_id": "P1"},
            [{"activity_id": "A", "duration": 1}],
            [{"predecessor_id": "A", "successor_id": "B"}],
        )


def test_negative_duration_is_rejected():
    with pytest.raises(ValueError, match="invalid duration"):
        build_canonical_dataset(
            {"project_id": "P1"},
            [{"activity_id": "A", "duration": -1}],
            [],
        )
