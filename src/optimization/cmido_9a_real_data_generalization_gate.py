"""CMIDO 9A — real-data ingestion and generalization gate.

This gate proves the reusable external-data boundary without modifying the
frozen 8M–8S evidence package. It validates explicit source mappings,
unit normalization, canonicalization, dependency integrity, provenance,
stable fingerprinting, and rejected-record reporting.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from src.construction.experiments.real_data_ingestion import build_ingestion_audit, ingest_csv_bundle
from src.construction.experiments.dataset import validate_dataset_structure


def project_root() -> Path:
    override = os.getenv("CMIDO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def run_gate(root: Path | None = None) -> dict:
    root = (root or project_root()).resolve()
    checks: list[dict] = []

    def ck(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    fixture = root / "examples/9A_real_data"
    mapping = fixture / "mapping.json"
    project = fixture / "project.csv"
    activities = fixture / "activities.csv"
    dependencies = fixture / "dependencies.csv"

    ck("9a_mapping_exists", mapping.exists(), str(mapping))
    ck("9a_project_source_exists", project.exists(), str(project))
    ck("9a_activities_source_exists", activities.exists(), str(activities))
    ck("9a_dependencies_source_exists", dependencies.exists(), str(dependencies))

    dataset = None
    if all(path.exists() for path in (mapping, project, activities, dependencies)):
        try:
            dataset = ingest_csv_bundle(fixture, mapping, dataset_id="CMIDO_9A_FIXTURE")
            ck("explicit_mapping_ingestion", True)
        except Exception as exc:  # pragma: no cover - reported as a gate failure
            ck("explicit_mapping_ingestion", False, str(exc))

    if dataset is not None:
        validation = validate_dataset_structure(dataset)
        ck("canonical_schema_valid", validation.valid)
        ck("single_project", validation.project_count == 1, str(validation.project_count))
        ck("four_activities", validation.activity_count == 4, str(validation.activity_count))
        ck("three_dependencies", validation.dependency_count == 3, str(validation.dependency_count))
        ck("duration_unit_normalization", [a["duration_days"] for a in dataset["activities"]] == [2, 5, 7, 1])
        ck("dependency_integrity", all(d["predecessor_id"] != d["successor_id"] for d in dataset["dependencies"]))
        ck("provenance_present", dataset["metadata"].get("source_traceability") is not None)
        ck("source_row_counts_present", dataset["metadata"].get("source_row_counts") == {"project": 1, "activities": 4, "dependencies": 3})
        ck("zero_rejected_records", dataset["metadata"].get("rejected_record_count") == 0)
        fingerprint = dataset.get("fingerprint_sha256", "")
        ck("sha256_fingerprint_present", len(fingerprint) == 64 and all(c in "0123456789abcdef" for c in fingerprint))
        audit = build_ingestion_audit(dataset)
        ck("machine_readable_audit", audit["dataset_id"] == "CMIDO_9A_FIXTURE")

        try:
            repeat = ingest_csv_bundle(fixture, mapping, dataset_id="CMIDO_9A_FIXTURE")
            ck("deterministic_fingerprint", repeat["fingerprint_sha256"] == fingerprint)
        except Exception as exc:
            ck("deterministic_fingerprint", False, str(exc))

        ck("no_source_semantic_guessing", dataset["metadata"].get("source_format") == "csv_bundle")

    # Negative-path proof: invalid source data must be surfaced, not silently dropped.
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        for source_name in ("project.csv", "activities.csv", "dependencies.csv", "mapping.json"):
            (temp_root / source_name).write_text((fixture / source_name).read_text(encoding="utf-8"), encoding="utf-8")
        bad = (temp_root / "activities.csv").read_text(encoding="utf-8").replace("48,hours", "bad,hours", 1)
        (temp_root / "activities.csv").write_text(bad, encoding="utf-8")
        try:
            ingest_csv_bundle(temp_root, temp_root / "mapping.json", dataset_id="CMIDO_9A_INVALID")
            ck("rejected_record_reporting", False, "invalid row was accepted")
        except ValueError as exc:
            payload = json.loads(str(exc))
            rejected = payload.get("rejected_records", [])
            ck("rejected_record_reporting", len(rejected) == 1 and rejected[0]["source_row"] == 2)

    status = "PASS" if checks and all(row["passed"] for row in checks) else "HOLD"
    return {
        "stage": "9A",
        "status": status,
        "checks_passed": sum(row["passed"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
        "frozen_predecessor_phases": ["8M", "8N", "8O", "8P", "8Q", "8R", "8S"],
        "scope": "real-data ingestion/generalization boundary; no UI changes",
    }


def main() -> int:
    root = project_root()
    result = run_gate(root)
    out = root / "results/9A_real_data_generalization"
    out.mkdir(parents=True, exist_ok=True)
    (out / "CMIDO_9A_REAL_DATA_GENERALIZATION_MANIFEST.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "CMIDO_9A_REAL_DATA_GENERALIZATION_AUDIT.csv").write_text(
        "check,passed,detail\n" + "\n".join(
            f"{row['check']},{row['passed']},{json.dumps(row['detail'])}" for row in result["checks"]
        ) + "\n",
        encoding="utf-8",
    )
    if result["status"] == "PASS":
        fixture = root / "examples/9A_real_data"
        dataset = ingest_csv_bundle(fixture, fixture / "mapping.json", dataset_id="CMIDO_9A_FIXTURE")
        (out / "CMIDO_9A_CANONICAL_DATASET.json").write_text(json.dumps(dataset, indent=2), encoding="utf-8")
        (out / "CMIDO_9A_INGESTION_AUDIT.json").write_text(json.dumps(build_ingestion_audit(dataset), indent=2), encoding="utf-8")

    print("=" * 78)
    print("CMIDO 9A — REAL-DATA INGESTION / GENERALIZATION GATE")
    print("=" * 78)
    for row in result["checks"]:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = f" — {row['detail']}" if row["detail"] else ""
        print(f"[{marker}] {row['check']}{suffix}")
    print("=" * 78)
    print(f"STATUS: {result['status']} ({result['checks_passed']}/{result['checks_total']})")
    print(f"OUTPUT: {out}")
    print("=" * 78)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
