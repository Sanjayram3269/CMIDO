"""
CMIDO 8N — Integrated Evidence Gate.

Checks the existence and basic integrity of the authoritative RO1/RO2/RO3
evidence sources and verifies that the 8M controlled baseline/ablation gate
is green. This module is intentionally non-mutating and does not recompute
scientific results.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


def project_root() -> Path:
    override = os.getenv("CMIDO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def run_gate(root: Path | None = None) -> dict:
    root = (root or project_root()).resolve()
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    ro1 = root / "results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv"
    ro2_view = root / "results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv"
    ro3_scen = root / "results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv"
    ro3_multi = root / "results/RO3/multi_origin"
    ro3_ablation = root / "results/RO3/ablation/final_comparison"
    gate8m = root / "results/RO3/ablation/8M_gate/CMIDO_8M_GATE_MANIFEST.json"

    check("ro1_calibrated_forecasts_exist", ro1.exists(), str(ro1))
    check("ro2_admissible_view_exists", ro2_view.exists(), str(ro2_view))
    check("ro3_primary_scenario_set_exists", ro3_scen.exists(), str(ro3_scen))
    check("ro3_multi_origin_directory_exists", ro3_multi.exists(), str(ro3_multi))
    check("ro3_ablation_directory_exists", ro3_ablation.exists(), str(ro3_ablation))
    check("8m_gate_manifest_exists", gate8m.exists(), str(gate8m))

    if ro1.exists():
        df = pd.read_csv(ro1, nrows=200000)
        required = {"dataset", "series", "horizon", "forecast_origin", "target_date", "q10", "q25", "q50", "q75", "q90"}
        check("ro1_required_fields_present", required <= set(df.columns))

    if ro2_view.exists():
        df = pd.read_csv(ro2_view, nrows=200000)
        required = {"admissible_component", "Internal_num", "PODN_num", "TotalDN_num"}
        check("ro2_admissible_fields_present", required <= set(df.columns))

    if ro3_ablation.exists():
        required_files = {
            "pairwise": ro3_ablation / "RO3_step36_statistical_pairwise_comparisons.csv",
            "primary": ro3_ablation / "RO3_step36_primary_ablation_results.csv",
            "descriptive": ro3_ablation / "RO3_step36_controller_descriptive_statistics.csv",
            "origin": ro3_ablation / "RO3_step36_origin_level_results.csv",
        }
        for name, path in required_files.items():
            check(f"8m_{name}_artifact_exists", path.exists(), str(path))

    if gate8m.exists():
        m = json.loads(gate8m.read_text(encoding="utf-8"))
        check("8m_gate_status_pass", m.get("status") == "PASS", str(m.get("status")))

    status = "PASS" if checks and all(row["passed"] for row in checks) else "HOLD"
    return {
        "stage": "8N",
        "status": status,
        "checks_passed": sum(row["passed"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
    }


def main() -> int:
    root = project_root()
    result = run_gate(root)
    out = root / "results/8N_integrated_evidence"
    out.mkdir(parents=True, exist_ok=True)
    (out / "CMIDO_8N_INTEGRATED_EVIDENCE_MANIFEST.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    pd.DataFrame(result["checks"]).to_csv(out / "CMIDO_8N_INTEGRATED_EVIDENCE_AUDIT.csv", index=False)

    print("=" * 78)
    print("CMIDO 8N — INTEGRATED EVIDENCE GATE")
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
