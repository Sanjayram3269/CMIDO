from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "results" / "RO3" / "scenario_generation" / "RO3_step32_scenarios_100.csv"
LOCK = ROOT / "docs" / "RO3_STEP32_FORECAST_ORIGIN_LOCK_v1.0.json"

EXPECTED_ROWS = 11 * 4 * 12 * 100

def main():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected = lock["forecast_origins"]

    df = pd.read_csv(SCENARIO)
    actual = sorted(pd.to_datetime(df["forecast_origin"]).dt.strftime("%Y-%m-%d").unique().tolist())

    checks = [
        ("origin_count", len(actual) == 11),
        ("origin_set_exact", actual == sorted(expected)),
        ("row_count", len(df) == EXPECTED_ROWS),
        ("excluded_demand_only_absent", "2022-06-01" not in actual),
        ("excluded_price_only_absent", "2023-06-01" not in actual),
    ]

    print("=" * 78)
    print("CMIDO RO3.2 — FROZEN FORECAST-ORIGIN AUDIT")
    print("=" * 78)
    print(f"Scenario file: {SCENARIO}")
    print(f"Actual origins: {len(actual)}")
    print(f"Expected origins: {len(expected)}")
    print(f"Rows: {len(df)}")
    print()

    for name, ok in checks:
        print(f"{name}: {'PASS' if ok else 'FAIL'}")

    print("\nActual origin set:")
    print("\n".join(actual))

    if all(ok for _, ok in checks):
        print("\nDECISION: RO3_STEP32_ORIGIN_LOCK_PASS")
    else:
        print("\nDECISION: RO3_STEP32_ORIGIN_LOCK_FAIL")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
