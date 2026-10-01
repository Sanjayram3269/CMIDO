"""CMIDO 9B — empirical project + construction-logistics E2E gate."""

from __future__ import annotations

import json
import os
from pathlib import Path

from src.construction.experiments.config import ExperimentConfig
from src.construction.experiments.logistics_ingestion import ingest_construction_logistics
from src.construction.experiments.pslib_ingestion import build_pslib_audit, ingest_pslib_project
from src.construction.experiments.real_data_runner import run_real_dataset_experiment
from src.construction.experiments.scenarios import build_delay_scenarios


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

    pslib = root / "data/dataset/pslib/DSLIB 3.4/Excel/C2025-02 Urban Road.xlsx"
    logistics = root / "data/dataset/construction logistics"
    output = root / "results/9B_real_project_e2e"
    output.mkdir(parents=True, exist_ok=True)

    ck("pslib_source_exists", pslib.exists(), str(pslib))
    ck("logistics_source_exists", logistics.exists(), str(logistics))

    project = None
    logistics_audit = None

    if pslib.exists():
        try:
            project = ingest_pslib_project(pslib, dataset_id="CMIDO_9B_PSLIB_C2025_02")
            ck("pslib_ingestion", True)
            ck("pslib_canonical_schema", project["validation"]["valid"])
            ck("pslib_has_real_activities", len(project["activities"]) >= 1, str(len(project["activities"])))
            ck("pslib_has_dependencies", len(project["dependencies"]) >= 1, str(len(project["dependencies"])))
            ck("pslib_has_risk_profiles", project["metadata"]["risk_profile_count"] >= 1, str(project["metadata"]["risk_profile_count"]))
            ck("pslib_has_control_snapshots", len(project["metadata"]["control_snapshot_names"]) >= 1)
            ck("pslib_has_resources", len(project["metadata"]["resource_rows"]) >= 1)
            ck("pslib_source_fingerprint", len(project["metadata"]["source_sha256"]) == 64)
        except Exception as exc:
            ck("pslib_ingestion", False, str(exc))

    if logistics.exists():
        try:
            logistics_audit = ingest_construction_logistics(logistics)
            summary = logistics_audit["derived_summary"]
            ck("logistics_ingestion", True)
            ck("logistics_expected_files", set(logistics_audit["tables"]) == {
                "CCC_options_data.csv", "construction sites_data.csv", "material_demand.csv",
                "material_demand_periods.csv", "origin_destination.csv", "suppliers_data.csv", "trucks_data.csv",
            })
            ck("logistics_sites", summary["site_count"] == 99, str(summary["site_count"]))
            ck("logistics_material_demands", summary["material_demand_count"] == 1277, str(summary["material_demand_count"]))
            ck("logistics_period_demands", summary["material_demand_period_count"] == 93663, str(summary["material_demand_period_count"]))
            ck("logistics_origin_destination", summary["origin_destination_count"] == 38640, str(summary["origin_destination_count"]))
            ck("logistics_supplier_rows", summary["supplier_material_rows"] == 407, str(summary["supplier_material_rows"]))
            ck("logistics_truck_rows", summary["truck_count"] == 5, str(summary["truck_count"]))
            ck("logistics_ccc_rows", summary["ccc_count"] == 25, str(summary["ccc_count"]))
            invalid_tables = {
                name: table["invalid_records"]
                for name, table in logistics_audit["tables"].items()
                if table["invalid_numeric_or_date_rows"] > 0
            }
            ck(
                "logistics_no_invalid_rows",
                not invalid_tables,
                json.dumps(invalid_tables, ensure_ascii=False),
            )
        except Exception as exc:
            ck("logistics_ingestion", False, str(exc))

    if project is not None:
        canonical_path = output / "CMIDO_9B_PSLIB_C2025_02_CANONICAL.json"
        canonical_path.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            config = ExperimentConfig(
                experiment_id="9B_REAL_PROJECT_E2E",
                name="9B Empirical PSLIB Project Execution",
                seed=42,
                parameters={"dataset_type": "pslib_empirical", "source_release": "DSLIB 3.4"},
            )
            scenarios = build_delay_scenarios(project["activities"][0]["activity_id"], [0, 1, 3])
            dataset_result = run_real_dataset_experiment(str(canonical_path), config, scenarios)
            ck("cmido_real_project_execution", dataset_result["scenario_count"] == 3)
            ck("cmido_execution_provenance", dataset_result["dataset"]["dataset_id"] == "CMIDO_9B_PSLIB_C2025_02")
            (output / "CMIDO_9B_REAL_PROJECT_EXPERIMENT.json").write_text(
                json.dumps(dataset_result, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            ck("cmido_real_project_execution", False, str(exc))

    if project is not None:
        (output / "CMIDO_9B_PSLIB_AUDIT.json").write_text(
            json.dumps(build_pslib_audit(project), indent=2, ensure_ascii=False), encoding="utf-8"
        )
    if logistics_audit is not None:
        (output / "CMIDO_9B_LOGISTICS_AUDIT.json").write_text(
            json.dumps(logistics_audit, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    status = "PASS" if checks and all(item["passed"] for item in checks) else "HOLD"
    result = {
        "stage": "9B",
        "status": status,
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_total": len(checks),
        "checks": checks,
        "sources": {
            "pslib": str(pslib),
            "construction_logistics": str(logistics),
        },
        "integration_boundary": "PSLIB empirical project and SUCCESS logistics evidence are retained as separate observed datasets; no unsupported cross-dataset project identity is fabricated.",
    }
    (output / "CMIDO_9B_REAL_PROJECT_E2E_MANIFEST.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def main() -> int:
    result = run_gate()
    print("=" * 78)
    print("CMIDO 9B — EMPIRICAL REAL-DATA E2E GATE")
    print("=" * 78)
    for row in result["checks"]:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = f" — {row['detail']}" if row["detail"] else ""
        print(f"[{marker}] {row['check']}{suffix}")
    print("=" * 78)
    print(f"STATUS: {result['status']} ({result['checks_passed']}/{result['checks_total']})")
    print("=" * 78)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
