from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from .normalization import DEFAULT_ALIASES, normalize_dataset


INGESTION_SCHEMA_VERSION = "9A-1.0"
SUPPORTED_FORMAT = "csv_bundle"


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise ValueError(f"source table does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"source table has no header: {path}")
        return [dict(row) for row in reader]


def _map_row(row: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for target, source in mapping.items():
        if source not in row:
            raise ValueError(f"mapped source column missing: {source}")
        result[target] = row.get(source)
    return result


def _coerce_number(value: Any, field: str) -> float:
    if value in (None, ""):
        raise ValueError(f"missing numeric value for {field}")
    try:
        return float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"invalid numeric value for {field}: {value}") from exc


def _convert_duration(value: Any, unit: str) -> int:
    number = _coerce_number(value, "duration_days")
    factors = {"day": 1.0, "days": 1.0, "hour": 1.0 / 24.0, "hours": 1.0 / 24.0, "week": 7.0, "weeks": 7.0}
    unit = unit.strip().lower()
    if unit not in factors:
        raise ValueError(f"unsupported duration unit: {unit}")
    converted = number * factors[unit]
    if converted < 0 or not converted.is_integer():
        raise ValueError(f"duration does not convert to an integer CMIDO day value: {value} {unit}")
    return int(converted)


def _fingerprint(dataset: dict[str, Any]) -> str:
    canonical = json.dumps(dataset, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ingest_csv_bundle(root: str | Path, mapping_path: str | Path, *, dataset_id: str = "CMIDO_REAL_DATASET") -> dict[str, Any]:
    """Ingest an external civil-project CSV bundle using explicit mappings.

    No semantic fields are guessed. Every source-to-CMIDO mapping is declared
    in the mapping file; invalid rows are reported rather than silently dropped.
    """
    root_path = Path(root).resolve()
    mapping_file = Path(mapping_path).resolve()
    if not mapping_file.exists():
        raise ValueError(f"mapping file does not exist: {mapping_file}")
    config = json.loads(mapping_file.read_text(encoding="utf-8"))
    if config.get("schema_version") != INGESTION_SCHEMA_VERSION:
        raise ValueError("unsupported 9A mapping schema version")
    if config.get("source_format") != SUPPORTED_FORMAT:
        raise ValueError("unsupported 9A source format")

    tables = config.get("tables")
    if not isinstance(tables, dict) or set(tables) != {"project", "activities", "dependencies"}:
        raise ValueError("9A mapping must define project, activities, and dependencies tables")

    rejected: list[dict[str, Any]] = []
    mapped: dict[str, list[dict[str, Any]]] = {}
    row_counts: dict[str, int] = {}

    for table_name in ("project", "activities", "dependencies"):
        spec = tables[table_name]
        if not isinstance(spec, dict) or not spec.get("file") or not isinstance(spec.get("mapping"), dict):
            raise ValueError(f"invalid mapping specification for {table_name}")
        rows = _read_csv(root_path / str(spec["file"]))
        row_counts[table_name] = len(rows)
        mapped_rows: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=2):
            try:
                item = _map_row(row, spec["mapping"])
                if table_name == "activities":
                    unit_column = spec.get("duration_unit_column")
                    unit = row.get(unit_column) if unit_column else spec.get("duration_unit", "day")
                    item["duration_days"] = _convert_duration(item.get("duration_days"), str(unit or "day"))
                mapped_rows.append(item)
            except ValueError as exc:
                rejected.append({"table": table_name, "source_row": index, "reason": str(exc)})
        mapped[table_name] = mapped_rows

    if rejected:
        raise ValueError(json.dumps({"rejected_records": rejected}, indent=2))

    raw = {
        "schema_version": config.get("source_schema_version"),
        "project": mapped["project"][0] if len(mapped["project"]) == 1 else {},
        "activities": mapped["activities"],
        "dependencies": mapped["dependencies"],
    }
    if not raw["project"]:
        raise ValueError("exactly one project record is required")

    canonical = normalize_dataset(raw, source=str(root_path), dataset_id=dataset_id, aliases=DEFAULT_ALIASES)
    canonical["schema_version"] = "8I-1.0"
    canonical["metadata"].update({
        "ingestion_schema_version": INGESTION_SCHEMA_VERSION,
        "source_format": SUPPORTED_FORMAT,
        "mapping_file": str(mapping_file),
        "source_row_counts": row_counts,
        "rejected_record_count": len(rejected),
        "source_traceability": "table + 1-based CSV row validated during ingestion",
    })
    canonical["fingerprint_sha256"] = _fingerprint(canonical)
    return canonical


def build_ingestion_audit(dataset: dict[str, Any]) -> dict[str, Any]:
    metadata = dataset.get("metadata", {})
    return {
        "ingestion_schema_version": INGESTION_SCHEMA_VERSION,
        "dataset_id": dataset.get("dataset_id"),
        "canonical_schema_version": dataset.get("schema_version"),
        "source": dataset.get("source"),
        "fingerprint_sha256": dataset.get("fingerprint_sha256"),
        "source_row_counts": metadata.get("source_row_counts", {}),
        "rejected_record_count": metadata.get("rejected_record_count", 0),
        "traceability": metadata.get("source_traceability"),
    }
