from __future__ import annotations

from dataclasses import dataclass
from typing import Any


REQUIRED_DATASET_KEYS = {
    "project",
    "activities",
    "dependencies",
}


@dataclass(frozen=True)
class DatasetValidationResult:
    """Deterministic validation summary for a CMIDO project dataset."""

    valid: bool
    project_count: int
    activity_count: int
    dependency_count: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "project_count": self.project_count,
            "activity_count": self.activity_count,
            "dependency_count": self.dependency_count,
            "warnings": list(self.warnings),
        }


def validate_dataset_structure(dataset: dict[str, Any]) -> DatasetValidationResult:
    """Validate the minimum canonical structure needed by CMIDO experiments."""
    if not isinstance(dataset, dict):
        raise ValueError("dataset must be a dictionary")

    missing = REQUIRED_DATASET_KEYS - dataset.keys()
    if missing:
        raise ValueError(f"dataset missing fields: {sorted(missing)}")

    project = dataset["project"]
    activities = dataset["activities"]
    dependencies = dataset["dependencies"]

    if not isinstance(project, dict):
        raise ValueError("dataset project must be a dictionary")
    if not isinstance(activities, list):
        raise ValueError("dataset activities must be a list")
    if not isinstance(dependencies, list):
        raise ValueError("dataset dependencies must be a list")

    if not project.get("project_id"):
        raise ValueError("dataset project_id must be present")

    warnings: list[str] = []
    activity_ids: set[str] = set()

    for index, activity in enumerate(activities):
        if not isinstance(activity, dict):
            raise ValueError(f"activity at index {index} must be a dictionary")
        activity_id = activity.get("activity_id")
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ValueError(f"activity at index {index} has invalid activity_id")
        if activity_id in activity_ids:
            raise ValueError(f"duplicate activity_id: {activity_id}")
        activity_ids.add(activity_id)
        duration = activity.get("duration")
        if not isinstance(duration, int) or duration < 0:
            raise ValueError(f"activity {activity_id} has invalid duration")

    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise ValueError(f"dependency at index {index} must be a dictionary")
        predecessor = dependency.get("predecessor_id")
        successor = dependency.get("successor_id")
        if predecessor not in activity_ids:
            raise ValueError(f"dependency references unknown predecessor: {predecessor}")
        if successor not in activity_ids:
            raise ValueError(f"dependency references unknown successor: {successor}")
        if predecessor == successor:
            raise ValueError(f"self dependency is not allowed: {predecessor}")

    if not activities:
        warnings.append("dataset contains no activities")
    if not dependencies and len(activities) > 1:
        warnings.append("dataset contains activities but no dependencies")

    return DatasetValidationResult(
        valid=True,
        project_count=1,
        activity_count=len(activities),
        dependency_count=len(dependencies),
        warnings=tuple(warnings),
    )


def build_canonical_dataset(
    project: dict[str, Any],
    activities: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    *,
    source: str = "unknown",
    dataset_id: str = "CMIDO_DATASET",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical, experiment-ready CMIDO dataset envelope."""
    dataset = {
        "schema_version": "8H-1.0",
        "dataset_id": dataset_id,
        "source": source,
        "project": dict(project),
        "activities": [dict(item) for item in activities],
        "dependencies": [dict(item) for item in dependencies],
        "metadata": {} if metadata is None else dict(metadata),
    }
    validation = validate_dataset_structure(dataset)
    dataset["validation"] = validation.to_dict()
    return dataset
