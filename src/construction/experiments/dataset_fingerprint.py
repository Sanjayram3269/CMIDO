from __future__ import annotations

from typing import Any

from .reproducibility import stable_hash


def fingerprint_dataset(dataset: dict[str, Any]) -> str:
    """Return a stable fingerprint for an experiment input dataset."""
    if not isinstance(dataset, dict):
        raise ValueError("dataset must be a dictionary")
    return stable_hash(dataset)


def build_dataset_metadata(dataset: dict[str, Any]) -> dict[str, Any]:
    """Build compact provenance metadata for a canonical dataset."""
    if not isinstance(dataset, dict):
        raise ValueError("dataset must be a dictionary")

    return {
        "dataset_id": dataset.get("dataset_id"),
        "schema_version": dataset.get("schema_version"),
        "source": dataset.get("source"),
        "dataset_fingerprint": fingerprint_dataset(dataset),
        "activity_count": len(dataset.get("activities", [])),
        "dependency_count": len(dataset.get("dependencies", [])),
    }
