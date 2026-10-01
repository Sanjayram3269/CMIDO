from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


LOGISTICS_INGESTION_SCHEMA_VERSION = "9B-1.0"
EXPECTED_FILES = {
    "CCC_options_data.csv",
    "construction sites_data.csv",
    "material_demand.csv",
    "material_demand_periods.csv",
    "origin_destination.csv",
    "suppliers_data.csv",
    "trucks_data.csv",
}
EXPECTED_HEADERS = {
    "CCC_options_data.csv": ["ccc_id", "capacity_sqm", "capacity_cubic_meters", "Activation_Cost"],
    "construction sites_data.csv": ["site_id", "private_public", "site_profile", "start", "end", "duration"],
    "material_demand.csv": ["demand_id", "profile", "start_date", "end_date", "number_of_days", "material", "supplier_id"],
    "material_demand_periods.csv": ["demand_id", "profile", "period", "demand_m3", "demand_kg"],
    "origin_destination.csv": ["origin", "destination", "meters", "seconds"],
    "suppliers_data.csv": ["supplier_id", "Material delivered", "Truck"],
    "trucks_data.csv": ["Truck_id", "Vehicle", "Capacity (kg)", "Capacity (m3)"],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_date(value: str, field: str) -> str:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError as exc:
        raise ValueError(f"invalid {field} date: {value!r}") from exc


def _audit_table(path: Path, expected_headers: list[str]) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"missing logistics source file: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        headers = reader.fieldnames or []
        missing = [header for header in expected_headers if header not in headers]
        if missing:
            raise ValueError(f"{path.name}: missing expected headers {missing}")
        row_count = 0
        invalid_rows = 0
        sample: list[dict[str, Any]] = []
        for row in reader:
            row_count += 1
            try:
                if path.name == "construction sites_data.csv":
                    _parse_date(row["start"], "start")
                    _parse_date(row["end"], "end")
                    int(row["duration"])
                elif path.name == "material_demand.csv":
                    _parse_date(row["start_date"], "start_date")
                    _parse_date(row["end_date"], "end_date")
                    int(row["number_of_days"])
                elif path.name == "material_demand_periods.csv":
                    int(row["period"])
                    int(row["demand_m3"])
                    int(row["demand_kg"])
                elif path.name == "origin_destination.csv":
                    int(row["meters"])
                    int(row["seconds"])
            except (TypeError, ValueError):
                invalid_rows += 1
            if len(sample) < 3:
                sample.append(dict(row))
    return {
        "file": path.name,
        "sha256": _sha256(path),
        "headers": headers,
        "row_count": row_count,
        "invalid_numeric_or_date_rows": invalid_rows,
        "sample_rows": sample,
        "provenance": "OBS",
    }


def ingest_construction_logistics(root: str | Path) -> dict[str, Any]:
    """Audit the public SUCCESS construction-logistics bundle without semantic fabrication."""
    root_path = Path(root).resolve()
    missing = EXPECTED_FILES - {p.name for p in root_path.glob("*.csv")}
    if missing:
        raise ValueError(f"construction-logistics dataset missing files: {sorted(missing)}")

    tables = {name: _audit_table(root_path / name, EXPECTED_HEADERS[name]) for name in sorted(EXPECTED_FILES)}

    with (root_path / "material_demand.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        demands = list(csv.DictReader(handle, delimiter=";"))
    material_counts = Counter(row["material"].strip() for row in demands if row.get("material"))
    supplier_counts = Counter(row["supplier_id"].strip() for row in demands if row.get("supplier_id"))

    return {
        "schema_version": LOGISTICS_INGESTION_SCHEMA_VERSION,
        "source_format": "SUCCESS_CSV_BUNDLE",
        "source": str(root_path),
        "dataset_doi": "10.5281/zenodo.1249519",
        "tables": tables,
        "derived_summary": {
            "site_count": tables["construction sites_data.csv"]["row_count"],
            "material_demand_count": tables["material_demand.csv"]["row_count"],
            "material_demand_period_count": tables["material_demand_periods.csv"]["row_count"],
            "origin_destination_count": tables["origin_destination.csv"]["row_count"],
            "supplier_material_rows": tables["suppliers_data.csv"]["row_count"],
            "truck_count": tables["trucks_data.csv"]["row_count"],
            "ccc_count": tables["CCC_options_data.csv"]["row_count"],
            "unique_materials_in_demand": len(material_counts),
            "unique_suppliers_in_demand": len(supplier_counts),
            "top_materials_by_demand_rows": material_counts.most_common(10),
        },
        "provenance": "OBS",
    }
