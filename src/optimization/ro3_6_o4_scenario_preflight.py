from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(r"D:\CMIDO")
F = ROOT / "results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv"
SCEN = ROOT / "results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv"

ORIGINS = pd.to_datetime([
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
    "2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"
])
MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
REQ_SCEN_COLS = [
    "scenario_id","forecast_origin","material","period","month_ahead",
    "demand","price","internal_duration_days","podn_duration_days",
    "total_duration_days","scenario_set_size","stream_id"
]

def main():
    checks = []
    def ck(name, ok, detail=""):
        checks.append(bool(ok))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    ck("RO1 file exists", F.exists())
    ck("N2500 scenario file exists", SCEN.exists(), str(SCEN))

    f = pd.read_csv(F)
    f["forecast_origin"] = pd.to_datetime(f["forecast_origin"])
    f["target_date"] = pd.to_datetime(f["target_date"])
    sub = f[
        f.forecast_origin.isin(ORIGINS) &
        f.series.isin(MATERIALS) &
        f.dataset.isin(["RO1_DEMAND","RO1_PRICE"])
    ].copy()

    ck("RO1 required datasets", set(sub.dataset.unique()) == {"RO1_DEMAND","RO1_PRICE"})
    ck("RO1 required materials", set(sub.series.unique()) == set(MATERIALS))
    ck("RO1 quantiles present", all(c in sub.columns for c in ["q10","q25","q50","q75","q90"]))
    q = sub[["q10","q25","q50","q75","q90"]].to_numpy(float)
    ck("RO1 quantiles ordered", bool(np.all(np.diff(q, axis=1) >= -1e-9)))
    ck("RO1 values finite", bool(np.isfinite(q).all()))
    ck("RO1 targets after origins", bool((sub.target_date > sub.forecast_origin).all()))

    s = pd.read_csv(SCEN)
    ck("Scenario schema complete", all(c in s.columns for c in REQ_SCEN_COLS))
    s["forecast_origin"] = pd.to_datetime(s["forecast_origin"])
    s["period"] = pd.to_datetime(s["period"])

    ck("Scenario set size = 2500", set(s.scenario_set_size.unique()) == {2500})
    ck("Scenario origins = 11", set(s.forecast_origin.unique()) == set(ORIGINS))
    ck("Scenario materials = 4", set(s.material.unique()) == set(MATERIALS))
    ck("Scenario rows = 1,320,000", len(s) == 1320000, len(s))
    ck("Scenario values finite", bool(np.isfinite(s[["demand","price","internal_duration_days","podn_duration_days","total_duration_days"]].to_numpy(float)).all()))
    ck("Demand/price nonnegative", bool((s[["demand","price"]] >= 0).all().all()))
    ck("Durations positive", bool((s[["total_duration_days"]] > 0).all().all()))
    ck("Duration reconstruction", bool(np.allclose(
        s.total_duration_days,
        s.internal_duration_days + s.podn_duration_days,
        atol=0, rtol=0
    )))
    ck("No target before origin", bool((s.period > s.forecast_origin).all()))
    ck("Month-ahead range 1..12", set(s.month_ahead.unique()) == set(range(1,13)))

    # Confirm 2500 file is the expected nested prefix-compatible scenario set.
    # IDs should be unique within each origin/material/month-ahead stream.
    dup = s.duplicated(["forecast_origin","material","month_ahead","scenario_id"]).sum()
    ck("Scenario IDs unique within streams", dup == 0, f"duplicates={dup}")

    print("\n" + "="*68)
    print("CMIDO RO3.6 — O4 SCENARIO PREFLIGHT")
    print(f"Checks passed: {sum(checks)}/{len(checks)}")
    status = "O4_PREFLIGHT_PASS" if all(checks) else "O4_PREFLIGHT_HOLD"
    print(f"STATUS: {status}")
    print("="*68)

if __name__ == "__main__":
    main()
