from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .dataset import build_canonical_dataset, validate_dataset_structure


def load_json_dataset(path: str | Path) -> dict[str, Any]:
    """Load JSON and return a canonical 8H dataset envelope."""
    file_path = Path(path)
    if not file_path.exists():
        raise ValueError(f"dataset file does not exist: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"dataset path is not a file: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as file:
            dataset = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON dataset: {file_path}") from exc

    if not isinstance(dataset, dict):
        raise ValueError("dataset must be a dictionary")

    if "schema_version" in dataset and "dataset_id" in dataset:
        validate_dataset_structure(dataset)
        return dataset

    required = {"project", "activities", "dependencies"}
    missing = required - dataset.keys()
    if missing:
        raise ValueError(f"dataset missing fields: {sorted(missing)}")

    return build_canonical_dataset(
        dataset["project"],
        dataset["activities"],
        dataset["dependencies"],
        source=str(file_path),
        dataset_id="CMIDO_DATASET",
        metadata={"source_path": str(file_path)},
    )


def load_source_records(
    path: str | Path,
    *,
    dataset_id: str = "CMIDO_DATASET",
    source: str | None = None,
) -> dict[str, Any]:
    """Load a source JSON record and normalize it into the 8H envelope."""
    file_path = Path(path)
    if not file_path.exists():
        raise ValueError(f"dataset file does not exist: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON dataset: {file_path}") from exc

    if not isinstance(raw, dict):
        raise ValueError("source dataset must be a dictionary")

    return build_canonical_dataset(
        raw.get("project", {}),
        raw.get("activities", []),
        raw.get("dependencies", []),
        source=source or str(file_path),
        dataset_id=dataset_id,
        metadata={"source_path": str(file_path)},
    )
