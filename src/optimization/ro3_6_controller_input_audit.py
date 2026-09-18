"""
CMIDO RO3.6 controller-definition audit.

This script checks the frozen methodological contract and the availability of
the RO1 calibrated forecast inputs required to implement O1/O2/O3/O4.
It does not execute the ablation and does not inspect evaluation outcomes.
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(r"D:\CMIDO")
FORECAST = ROOT / "results" / "forecasting" / "probabilistic_calibration" / "RO1_step26c3_validation_forecasts.csv"
OUT = ROOT / "results" / "RO3" / "ablation"
OUT.mkdir(parents=True, exist_ok=True)

ORIGINS = pd.to_datetime([
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
    "2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"
])
MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]

REQUIRED = [
    "dataset","series","horizon","forecast_origin","target_date","actual",
    "q10","q25","q50","q75","q90"
]

def main():
    checks = []
    f = pd.read_csv(FORECAST)
    f["forecast_origin"] = pd.to_datetime(f["forecast_origin"], errors="coerce")
    f["target_date"] = pd.to_datetime(f["target_date"], errors="coerce")

    checks.append(("forecast_file_exists", True))
    checks.append(("required_columns_present", all(c in f.columns for c in REQUIRED)))

    z = f[
        f.dataset.isin(["RO1_DEMAND","RO1_PRICE"])
        & f.forecast_origin.isin(ORIGINS)
        & f.series.isin(MATERIALS)
        & f.horizon.isin([1,3,6,12])
    ].copy()

    checks.append(("11_origins_present", z.forecast_origin.nunique() == 11))
    checks.append(("four_materials_present", z.series.nunique() == 4))
    checks.append(("four_required_horizons_present",
                   set(z.horizon.unique()) == {1,3,6,12}))
    checks.append(("forecast_targets_after_origin",
                   bool((z.target_date > z.forecast_origin).all())))

    for qlo, qhi in [("q10","q25"),("q25","q50"),("q50","q75"),("q75","q90")]:
        checks.append((f"{qlo}_le_{qhi}", bool((z[qlo] <= z[qhi]).all())))

    checks.append(("all_quantiles_finite",
                   bool(z[["q10","q25","q50","q75","q90"]].notna().all().all())))

    # Count complete origin/material/dataset blocks for horizons used by O1/O3.
    block = z.groupby(["dataset","forecast_origin","series"])["horizon"].nunique()
    checks.append(("complete_four_horizon_blocks", bool((block == 4).all())))

    out = pd.DataFrame([{"check": n, "passed": bool(v)} for n,v in checks])
    out.to_csv(OUT/"RO3_step36_controller_input_audit.csv", index=False)

    manifest = {
        "controller_contract": "v1.0",
        "O1": "q50 demand heuristic replenishment",
        "O2": "deterministic q50 optimization",
        "O3": "q90 demand heuristic replenishment",
        "O4": "probabilistic CMIDO optimization",
        "primary_scenario_count": 2500,
        "sensitivity_scenario_count": 5000,
        "checks_passed": int(out.passed.sum()),
        "checks_total": len(out),
        "decision": "PASS" if out.passed.all() else "HOLD_FOR_REVIEW",
    }
    (OUT/"RO3_step36_controller_freeze_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print("="*78)
    print("CMIDO RO3.6 — CONTROLLER INPUT / FREEZE AUDIT")
    print("="*78)
    print(out.to_string(index=False))
    print("="*78)
    print(f"STATUS: {manifest['decision']} ({manifest['checks_passed']}/{manifest['checks_total']})")
    print("="*78)

if __name__ == "__main__":
    main()
