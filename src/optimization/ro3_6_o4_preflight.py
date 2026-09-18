from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path(r"D:\CMIDO")
F = ROOT / "results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv"
S = ROOT / "results/RO3/scenarios"
MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
ORIGINS = pd.to_datetime([
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
    "2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"
])

def main():
    f = pd.read_csv(F)
    f["forecast_origin"] = pd.to_datetime(f["forecast_origin"])
    f["target_date"] = pd.to_datetime(f["target_date"])
    checks = []

    def ck(name, ok, detail=""):
        checks.append((name,bool(ok),detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    ck("RO1 file exists", F.exists())
    ck("RO1 common origins", set(f.forecast_origin.unique()) >= set(ORIGINS))
    sub = f[(f.forecast_origin.isin(ORIGINS)) & (f.series.isin(MATERIALS)) &
            (f.dataset.isin(["RO1_DEMAND","RO1_PRICE"]))]
    ck("O4 required datasets present", set(sub.dataset.unique()) == {"RO1_DEMAND","RO1_PRICE"})
    ck("O4 required materials present", set(sub.series.unique()) == set(MATERIALS))
    ck("Quantile columns present", all(c in sub.columns for c in ["q10","q25","q50","q75","q90"]))
    ck("Quantiles ordered", bool((sub[["q10","q25","q50","q75","q90"]].diff(axis=1).iloc[:,1:] >= -1e-9).all().all()))
    ck("Forecast values finite", np.isfinite(sub[["q10","q25","q50","q75","q90"]].to_numpy(float)).all())
    ck("Targets after origins", bool((sub.target_date > sub.forecast_origin).all()))

    candidates = sorted(S.glob("*2500*.csv")) if S.exists() else []
    if not candidates:
        candidates = list(S.glob("**/*.csv")) if S.exists() else []
    ck("Scenario directory available", S.exists(), str(S))
    ck("Scenario candidate present", len(candidates)>0, f"{len(candidates)} candidate CSVs")

    print("\nO4 PREFLIGHT")
    print(f"Checks: {sum(x[1] for x in checks)}/{len(checks)}")
    print("Next: single-origin N=2500 optimizer smoke/production.")

if __name__ == "__main__":
    main()
