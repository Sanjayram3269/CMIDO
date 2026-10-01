from __future__ import annotations

from datetime import date
from typing import Any


DEFAULT_ALIASES = {
    "project_id": ("project_id", "project", "project_code"),
    "project_name": ("project_name", "project_title", "name"),
    "activity_id": ("activity_id", "task_id", "id", "activity_code"),
    "activity_code": ("activity_code", "task_code", "activity_id"),
    "activity_name": ("activity_name", "task_name", "name", "description"),
    "duration_days": ("duration_days", "duration", "planned_duration", "days"),
    "predecessor_id": ("predecessor_id", "predecessor", "predecessor_task", "pred"),
    "successor_id": ("successor_id", "successor", "successor_task", "successor_task_id"),
    "lag_days": ("lag_days", "lag", "lead_lag"),
    "relationship_type": ("relationship_type", "dependency_type", "relationship", "type"),
}


def _pick(record: dict[str, Any], field: str, aliases: dict[str, tuple[str, ...]]) -> Any:
    for key in aliases.get(field, (field,)):
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def _required(value: Any, field: str) -> Any:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"required source field missing for {field}")
    return value


def _number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric value for {field}: {value}") from exc
    if number < 0:
        raise ValueError(f"{field} cannot be negative")
    return number


def _normalize_date(value: Any, field: str) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise ValueError(f"invalid ISO date for {field}: {value}") from exc


def normalize_project(
    record: dict[str, Any],
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, Any]:
    """Map one source project record into the CMIDO project representation."""
    aliases = aliases or DEFAULT_ALIASES
    project_id = _required(_pick(record, "project_id", aliases), "project_id")
    project_name = _required(_pick(record, "project_name", aliases), "project_name")
    result = {
        "project_id": str(project_id),
        "project_name": str(project_name),
    }
    for field in ("location", "project_type", "status", "calendar_id"):
        if field in record and record[field] not in (None, ""):
            result[field] = record[field]
    return result


def normalize_activity(
    record: dict[str, Any],
    *,
    project_id: str,
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, Any]:
    """Map one source activity/task record into CMIDO's activity schema."""
    aliases = aliases or DEFAULT_ALIASES
    activity_id = str(_required(_pick(record, "activity_id", aliases), "activity_id"))
    activity_code = str(_pick(record, "activity_code", aliases) or activity_id)
    activity_name = str(_required(_pick(record, "activity_name", aliases), "activity_name"))
    duration = _number(_required(_pick(record, "duration_days", aliases), "duration_days"), "duration_days")

    result: dict[str, Any] = {
        "activity_id": activity_id,
        "project_id": project_id,
        "activity_code": activity_code,
        "activity_name": activity_name,
        "duration_days": duration,
    }

    for field in ("description", "unit", "status"):
        if record.get(field) not in (None, ""):
            result[field] = record[field]

    if record.get("quantity") not in (None, ""):
        result["quantity"] = _number(record["quantity"], "quantity")

    for field in ("planned_start", "planned_finish", "actual_start", "actual_finish"):
        if field in record:
            result[field] = _normalize_date(record[field], field)

    return result


def normalize_dependency(
    record: dict[str, Any],
    *,
    project_id: str,
    dependency_index: int,
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, Any]:
    """Map one source relationship record into CMIDO's dependency schema."""
    aliases = aliases or DEFAULT_ALIASES
    predecessor = str(_required(_pick(record, "predecessor_id", aliases), "predecessor_id"))
    successor = str(_required(_pick(record, "successor_id", aliases), "successor_id"))
    if predecessor == successor:
        raise ValueError("predecessor_id and successor_id must be different")

    relationship = str(_pick(record, "relationship_type", aliases) or "FS").upper()
    if relationship not in {"FS", "SS", "FF", "SF"}:
        raise ValueError(f"invalid relationship_type: {relationship}")

    lag = _number(_pick(record, "lag_days", aliases) or 0, "lag_days")
    dependency_id = str(record.get("dependency_id") or f"D{dependency_index:04d}")

    return {
        "dependency_id": dependency_id,
        "project_id": project_id,
        "predecessor_id": predecessor,
        "successor_id": successor,
        "relationship_type": relationship,
        "lag_days": lag,
    }


def normalize_dataset(
    raw: dict[str, Any],
    *,
    source: str = "external",
    dataset_id: str = "CMIDO_REAL_DATASET",
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, Any]:
    """Normalize a supported external dataset into the canonical 8H envelope.

    Required source collections are intentionally explicit. The mapper does not
    infer project structure from arbitrary prose or silently discard invalid rows.
    """
    if not isinstance(raw, dict):
        raise ValueError("raw dataset must be a dictionary")

    aliases = aliases or DEFAULT_ALIASES
    source_project = raw.get("project")
    source_activities = raw.get("activities")
    source_dependencies = raw.get("dependencies")

    if not isinstance(source_project, dict):
        raise ValueError("raw dataset project must be a dictionary")
    if not isinstance(source_activities, list):
        raise ValueError("raw dataset activities must be a list")
    if not isinstance(source_dependencies, list):
        raise ValueError("raw dataset dependencies must be a list")

    project = normalize_project(source_project, aliases)
    activities = [
        normalize_activity(item, project_id=project["project_id"], aliases=aliases)
        for item in source_activities
    ]
    dependencies = [
        normalize_dependency(
            item,
            project_id=project["project_id"],
            dependency_index=index + 1,
            aliases=aliases,
        )
        for index, item in enumerate(source_dependencies)
    ]

    activity_ids = {item["activity_id"] for item in activities}
    for dependency in dependencies:
        if dependency["predecessor_id"] not in activity_ids:
            raise ValueError(f"dependency references unknown predecessor: {dependency['predecessor_id']}")
        if dependency["successor_id"] not in activity_ids:
            raise ValueError(f"dependency references unknown successor: {dependency['successor_id']}")

    return {
        "schema_version": "8I-1.0",
        "dataset_id": dataset_id,
        "source": source,
        "project": project,
        "activities": activities,
        "dependencies": dependencies,
        "metadata": {
            "normalization": "explicit_column_mapping",
            "source_schema_version": raw.get("schema_version"),
        },
    }
