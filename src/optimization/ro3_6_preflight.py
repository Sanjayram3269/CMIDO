from pathlib import Path
import json
import pandas as pd

ROOT = Path(r"D:\CMIDO")
checks = []

def check(label, path):
    ok = path.exists()
    checks.append((label, ok, str(path)))
    return ok

print("=" * 78)
print("CMIDO RO3.6 — IMPLEMENTATION PREFLIGHT")
print("=" * 78)

# Frozen RO1/RO3 artifacts
check("RO1 calibrated demand forecasts",
      ROOT / "results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv")

check("RO1 demand long data",
      ROOT / "results/forecasting/RO1_demand_long.csv")

check("RO1 price long data",
      ROOT / "results/forecasting/RO1_price_long.csv")

check("RO3 primary scenario set",
      ROOT / "results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv")

check("RO3.5 aggregate Pareto results",
      ROOT / "results/RO3/multi_origin/RO3_step35_pareto_all_origins_N2500.csv")

check("RO3.5 aggregate decisions",
      ROOT / "results/RO3/multi_origin/RO3_step35_decisions_all_origins_N2500.csv")

# Locked origin set
origins = pd.to_datetime([
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01",
    "2022-11-01","2022-12-01","2023-01-01","2023-02-01",
    "2023-03-01","2023-04-01","2023-05-01"
])

forecast_path = ROOT / "results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv"
if forecast_path.exists():
    f = pd.read_csv(forecast_path)
    f["forecast_origin"] = pd.to_datetime(f["forecast_origin"])
    common = sorted(set(f.loc[f["dataset"].eq("RO1_DEMAND"), "forecast_origin"])
                    & set(f.loc[f["dataset"].eq("RO1_PRICE"), "forecast_origin"]))
    common = pd.to_datetime(common)
    checks.append(("exact 11-origin common forecast intersection",
                   set(common) == set(origins), ""))
    print(f"Common RO1 demand/price origins: {len(common)}")

# Inspect available forecast columns
if forecast_path.exists():
    print("\nRO1 calibrated forecast columns:")
    print(", ".join(f.columns.tolist()))

# Inspect scenario schema
scenario_path = ROOT / "results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv"
if scenario_path.exists():
    s = pd.read_csv(scenario_path, nrows=5)
    print("\nRO3 scenario columns:")
    print(", ".join(s.columns.tolist()))

# Inspect evaluation-data availability and avoid guessing
print("\nEvaluation-realization gate:")
print("This script does NOT assume that validation forecasts themselves are")
print("the realized future observations. A separate held-out realization")
print("must be identified before O1/O2/O3/O4 execution.")

# Search likely raw data files by filename only
raw = ROOT / "data/raw"
candidates = []
if raw.exists():
    for x in raw.rglob("*"):
        if x.is_file():
            name = x.name.lower()
            if any(k in name for k in ["demand", "price", "material", "construction"]):
                candidates.append(str(x))
print("\nCandidate raw demand/price files:")
for x in candidates[:50]:
    print(" -", x)

result = {
    "passed": sum(x[1] for x in checks),
    "total": len(checks),
    "checks": [{"name":a,"passed":b,"path":c} for a,b,c in checks]
}
out = ROOT / "results/RO3/ablation"
out.mkdir(parents=True, exist_ok=True)
(out / "RO3_step36_preflight.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

print("\n" + "=" * 78)
print(f"FILE/ORIGIN PREFLIGHT: {result['passed']}/{result['total']} checks passed")
print("IMPORTANT: this is not yet an O1/O2/O3/O4 scientific lock.")
print(f"Manifest: {out / 'RO3_step36_preflight.json'}")
print("=" * 78)
