from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .dataset import build_canonical_dataset, validate_dataset_structure


def load_json_dataset(path: str | Path) -> dict[str, Any]:
    """Load a JSON dataset and validate its canonical CMIDO structure."""
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

    validate_dataset_structure(dataset)
    return dataset


def load_source_records(
    path: str | Path,
    *,
    dataset_id: str = "CMIDO_DATASET",
    source: str | None = None,
) -> dict[str, Any]:
    """Load a source JSON record and normalize it into the 8H envelope.

    The source must already expose project, activities, and dependencies.
    8H intentionally validates rather than guessing missing domain semantics.
    """
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
