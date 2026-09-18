from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

ROOT = Path(r"D:\CMIDO")
RAW = ROOT / "data" / "raw"
OUT = ROOT / "results" / "RO3" / "ablation"
OUT.mkdir(parents=True, exist_ok=True)

ORIGINS = pd.to_datetime([
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
    "2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"
])

MATERIALS = [
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
]

PRICE_MAP = {
    "Cement": "Cement In Bulk (Ordinary Portland Cement)",
    "Steel Reinforcement Bars": "Steel Reinforcement Bars (16-32mm High Tensile)",
    "Granite": "Granite (20mm Aggregate)",
    "Ready Mixed Concrete": "Ready Mixed Concrete",
}

DEMAND_MAP = {
    "Cement": "Cement",
    "Steel Reinforcement Bars": "Steel Reinforcement Bars",
    "Granite": "Granite",
    "Ready Mixed Concrete": "Ready-Mixed Concrete",
}

PRICE_FILE = RAW / "ConstructionMaterialMarketPricesMonthly.csv"
DEMAND_FILE = RAW / "DemandForConstructionMaterialsMonthly.csv"
FORECAST_FILE = ROOT / "results" / "forecasting" / "probabilistic_calibration" / "RO1_step26c3_validation_forecasts.csv"


def load_raw_wide(path):
    x = pd.read_csv(path)
    material_col = x.columns[0]
    x = x.rename(columns={material_col: "raw_material"})
    long = x.melt(id_vars=["raw_material"], var_name="raw_date", value_name="value")

    # Actual CMIDO raw schema: YYYYMon, e.g. 2026Jun.
    long["date"] = pd.to_datetime(
        long["raw_date"].astype(str).str.strip(),
        format="%Y%b",
        errors="coerce",
    )
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    return long


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=12)
    args = ap.parse_args()

    print("=" * 78)
    print("CMIDO RO3.6 — CORRECTED EVALUATION REALIZATION AUDIT")
    print("=" * 78)

    price = load_raw_wide(PRICE_FILE)
    demand = load_raw_wide(DEMAND_FILE)

    rows = []

    for origin in ORIGINS:
        evaluation_dates = pd.date_range(
            origin + pd.offsets.MonthBegin(1),
            periods=args.horizon,
            freq="MS",
        )

        for material in MATERIALS:
            p = price[
                price.raw_material.eq(PRICE_MAP[material])
                & price.date.isin(evaluation_dates)
            ].copy()

            d = demand[
                demand.raw_material.eq(DEMAND_MAP[material])
                & demand.date.isin(evaluation_dates)
            ].copy()

            rows.append({
                "forecast_origin": origin.strftime("%Y-%m-%d"),
                "material": material,
                "eval_start": evaluation_dates.min().strftime("%Y-%m-%d"),
                "eval_end": evaluation_dates.max().strftime("%Y-%m-%d"),
                "expected_months": args.horizon,

                "demand_months": int(d.date.nunique()),
                "price_months": int(p.date.nunique()),

                "demand_complete": d.date.nunique() == args.horizon,
                "price_complete": p.date.nunique() == args.horizon,

                "demand_finite": (
                    bool(np.isfinite(d.value).all()) if len(d) else False
                ),
                "price_finite": (
                    bool(np.isfinite(p.value).all()) if len(p) else False
                ),

                "strictly_after_origin": bool((evaluation_dates > origin).all()),
                "demand_duplicate_dates": int(
                    d.duplicated(subset=["date"]).sum()
                ),
                "price_duplicate_dates": int(
                    p.duplicated(subset=["date"]).sum()
                ),
            })

    matrix = pd.DataFrame(rows)

    checks = [
        ("11_locked_origins", matrix.forecast_origin.nunique() == 11),
        ("four_common_materials", matrix.material.nunique() == 4),
        ("all_12_demand_months_available", bool(matrix.demand_complete.all())),
        ("all_12_price_months_available", bool(matrix.price_complete.all())),
        ("all_demand_values_finite", bool(matrix.demand_finite.all())),
        ("all_price_values_finite", bool(matrix.price_finite.all())),
        ("evaluation_strictly_after_origin", bool(matrix.strictly_after_origin.all())),
        ("no_demand_duplicate_dates", bool((matrix.demand_duplicate_dates == 0).all())),
        ("no_price_duplicate_dates", bool((matrix.price_duplicate_dates == 0).all())),
        ("price_material_mapping_exact", all(
            PRICE_MAP[m] in set(price.raw_material.unique()) for m in MATERIALS
        )),
        ("demand_material_mapping_exact", all(
            DEMAND_MAP[m] in set(demand.raw_material.unique()) for m in MATERIALS
        )),
    ]

    # Confirm raw data extend through the latest required evaluation month.
    latest_eval = max(
        o + pd.offsets.MonthBegin(1) + pd.DateOffset(months=args.horizon - 1)
        for o in ORIGINS
    )

    checks.extend([
        ("raw_demand_covers_latest_evaluation",
         bool(demand.date.max() >= latest_eval)),
        ("raw_price_covers_latest_evaluation",
         bool(price.date.max() >= latest_eval)),
    ])

    # Forecast file is a diagnostic only. Realized evaluation values remain
    # sourced from the raw historical datasets above.
    if FORECAST_FILE.exists():
        f = pd.read_csv(FORECAST_FILE)
        f["forecast_origin"] = pd.to_datetime(f["forecast_origin"], errors="coerce")
        f["target_date"] = pd.to_datetime(f["target_date"], errors="coerce")

        common = f[
            f.dataset.isin(["RO1_DEMAND", "RO1_PRICE"])
            & f.forecast_origin.isin(ORIGINS)
            & f.series.isin(MATERIALS)
        ]

        checks.extend([
            ("forecast_actual_column_present", "actual" in f.columns),
            ("forecast_targets_after_origin",
             bool((common.target_date > common.forecast_origin).all())),
        ])
    else:
        checks.append(("forecast_file_present", False))

    audit = pd.DataFrame([
        {"check": name, "passed": bool(value)}
        for name, value in checks
    ])

    matrix_path = OUT / "RO3_step36_evaluation_realization_matrix.csv"
    audit_path = OUT / "RO3_step36_evaluation_realization_audit.csv"
    manifest_path = OUT / "RO3_step36_evaluation_realization_manifest.json"

    matrix.to_csv(matrix_path, index=False)
    audit.to_csv(audit_path, index=False)

    passed = int(audit.passed.sum())
    total = len(audit)
    decision = "PASS" if passed == total else "HOLD_FOR_REVIEW"

    manifest = {
        "origins": [o.strftime("%Y-%m-%d") for o in ORIGINS],
        "materials": MATERIALS,
        "price_mapping": PRICE_MAP,
        "demand_mapping": DEMAND_MAP,
        "horizon_months": args.horizon,
        "evaluation_rule": (
            "first calendar month after forecast origin through "
            "the next 12 monthly observations"
        ),
        "realized_demand_source": str(DEMAND_FILE),
        "realized_price_source": str(PRICE_FILE),
        "checks_passed": passed,
        "checks_total": total,
        "decision": decision,
    }

    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print("\nEvaluation matrix:")
    print(
        matrix.groupby("forecast_origin").agg(
            materials=("material", "nunique"),
            demand_complete=("demand_complete", "all"),
            price_complete=("price_complete", "all"),
            demand_months=("demand_months", "min"),
            price_months=("price_months", "min"),
            eval_start=("eval_start", "min"),
            eval_end=("eval_end", "max"),
        ).to_string()
    )

    print("\nChecks:")
    print(audit.to_string(index=False))

    print("\n" + "=" * 78)
    print(f"RO3.6 EVALUATION AUDIT: {passed}/{total} checks passed")
    print(f"DECISION: {decision}")
    print(f"Matrix: {matrix_path}")
    print(f"Audit:  {audit_path}")
    print(f"Manifest: {manifest_path}")
    print("=" * 78)


if __name__ == "__main__":
    main()
