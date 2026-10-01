from src.construction.experiments.dataset import build_canonical_dataset
from src.construction.experiments.dataset_fingerprint import (
    build_dataset_metadata,
    fingerprint_dataset,
)


def make_dataset():
    return build_canonical_dataset(
        {"project_id": "P1", "project_name": "Demo"},
        [{"activity_id": "A", "duration": 2}],
        [],
        source="test",
        dataset_id="FP_8H",
    )


def test_dataset_fingerprint_is_stable():
    dataset = make_dataset()
    assert fingerprint_dataset(dataset) == fingerprint_dataset(dataset)


def test_dataset_metadata_contains_provenance():
    metadata = build_dataset_metadata(make_dataset())
    assert metadata["dataset_id"] == "FP_8H"
    assert metadata["schema_version"] == "8H-1.0"
    assert len(metadata["dataset_fingerprint"]) > 0
    assert metadata["activity_count"] == 1
