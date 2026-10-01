"""
CMIDO 8P — Real-data dashboard E2E gate.

Validates that the dashboard's real-data experiment path, deterministic
scenario controls, research-evidence path, and supporting output contracts
are all present in the checked-out repository. The gate is deliberately
non-mutating: it does not launch Streamlit or recompute the research results.
A separate local smoke run should exercise the interactive UI.
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

    def ck(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    dashboard = root / "apps/cmido_dashboard.py"
    guide = root / "docs/dashboard_8L.md"
    ro1 = root / "results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv"
    ro2 = root / "results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv"
    ro3 = root / "results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv"
    ablation = root / "results/RO3/ablation/final_comparison/RO3_step36_origin_level_results.csv"

    ck("dashboard_exists", dashboard.exists(), str(dashboard))
    ck("dashboard_guide_exists", guide.exists(), str(guide))
    for name, path in [("ro1_source", ro1), ("ro2_source", ro2), ("ro3_source", ro3), ("ablation_source", ablation)]:
        ck(f"{name}_exists", path.exists(), str(path))

    if dashboard.exists():
        text = dashboard.read_text(encoding="utf-8")
        required = [
            "file_uploader",
            "run_real_dataset_experiment",
            "ExperimentConfig(",
            'experiment_id="CMIDO_DASHBOARD_RUN"',
            'name="CMIDO Dashboard Experiment"',
            "Deterministic CMIDO scenarios",
            "Execute experiment",
            "Research Evidence",
            "mean_project_delay_confidence_interval",
            "95% bootstrap CI",
        ]
        for marker in required:
            ck(f"dashboard_contains_{marker.replace(' ', '_').replace('"', '').lower()}", marker in text)

    if ro1.exists():
        df = pd.read_csv(ro1, nrows=20)
        ck(
            "ro1_forecast_contract",
            {"forecast_origin", "target_date", "q50", "q90"} <= set(df.columns),
        )

    if ro2.exists():
        df = pd.read_csv(ro2, nrows=20)
        ck(
            "ro2_modelling_contract",
            {"admissible_component", "Internal_num", "PODN_num", "TotalDN_num"} <= set(df.columns),
        )

    if ro3.exists():
        df = pd.read_csv(ro3, nrows=20)
        ck(
            "ro3_scenario_contract",
            {"forecast_origin", "material", "scenario_id", "demand", "price", "total_duration_days"} <= set(df.columns),
        )

    if ablation.exists():
        df = pd.read_csv(ablation)
        ck(
            "ablation_controller_contract",
            set(df["controller"].dropna()) == {"O1", "O2", "O3", "O4"},
        )

    status = "PASS" if checks and all(row["passed"] for row in checks) else "HOLD"
    return {
        "stage": "8P",
        "status": status,
        "checks_passed": sum(row["passed"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
        "interactive_smoke_required": True,
    }


def main() -> int:
    root = project_root()
    result = run_gate(root)
    out = root / "results/8P_dashboard_e2e"
    out.mkdir(parents=True, exist_ok=True)
    (out / "CMIDO_8P_DASHBOARD_E2E_MANIFEST.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    pd.DataFrame(result["checks"]).to_csv(out / "CMIDO_8P_DASHBOARD_E2E_AUDIT.csv", index=False)

    print("=" * 78)
    print("CMIDO 8P — REAL-DATA DASHBOARD E2E GATE")
    print("=" * 78)
    for row in result["checks"]:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = f" — {row['detail']}" if row["detail"] else ""
        print(f"[{marker}] {row['check']}{suffix}")
    print("=" * 78)
    print(f"STATUS: {result['status']} ({result['checks_passed']}/{result['checks_total']})")
    print("INTERACTIVE SMOKE: required")
    print(f"OUTPUT: {out}")
    print("=" * 78)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
