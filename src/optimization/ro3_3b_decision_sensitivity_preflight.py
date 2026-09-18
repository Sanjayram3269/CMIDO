from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SCEN_DIR = ROOT / "results" / "RO3" / "scenario_generation"
OUT_DIR = ROOT / "results" / "RO3" / "decision_sensitivity"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SIZES = [1000, 2500, 5000]
MATERIALS = [
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
]
ORIGINS = [
    "2022-07-01", "2022-08-01", "2022-09-01", "2022-10-01",
    "2022-11-01", "2022-12-01", "2023-01-01", "2023-02-01",
    "2023-03-01", "2023-04-01", "2023-05-01",
]

REQUIRED = [
    "scenario_id", "forecast_origin", "material", "period", "month_ahead",
    "demand", "price", "internal_duration_days", "podn_duration_days",
    "total_duration_days", "scenario_set_size", "stream_id",
]

def validate_scenario(n):
    path = SCEN_DIR / f"RO3_step32_scenarios_{n}.csv"
    if not path.exists():
        raise FileNotFoundError(path)

    print(f"[LOAD] {n:,} scenarios", flush=True)
    df = pd.read_csv(path, usecols=REQUIRED)

    expected = 11 * 4 * 12 * n
    if len(df) != expected:
        raise ValueError(
            f"{path.name}: expected {expected:,} rows, got {len(df):,}"
        )

    df["forecast_origin"] = (
        pd.to_datetime(df["forecast_origin"]).dt.strftime("%Y-%m-%d")
    )
    df["period"] = pd.to_datetime(df["period"])

    numeric = [
        "scenario_id", "month_ahead", "demand", "price",
        "internal_duration_days", "podn_duration_days",
        "total_duration_days", "scenario_set_size",
    ]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if sorted(df["forecast_origin"].unique()) != sorted(ORIGINS):
        raise ValueError(f"{path.name}: origin set changed")

    if sorted(df["material"].unique()) != sorted(MATERIALS):
        raise ValueError(f"{path.name}: material set changed")

    if set(df["scenario_set_size"].unique()) != {n}:
        raise ValueError(f"{path.name}: scenario_set_size mismatch")

    if not np.isfinite(df[numeric].to_numpy()).all():
        raise ValueError(f"{path.name}: non-finite numeric values")

    reconstruction = (
        df["internal_duration_days"]
        + df["podn_duration_days"]
        - df["total_duration_days"]
    ).abs().max()

    if reconstruction > 1e-9:
        raise ValueError(
            f"{path.name}: duration reconstruction error {reconstruction}"
        )

    path_counts = (
        df.groupby(["stream_id", "scenario_id"])["month_ahead"]
        .agg(["count", "nunique", "min", "max"])
    )

    valid = (
        (path_counts["count"] == 12)
        & (path_counts["nunique"] == 12)
        & (path_counts["min"] == 1)
        & (path_counts["max"] == 12)
    )

    if not valid.all():
        raise ValueError(f"{path.name}: invalid scenario paths")

    print(f"[PASS] {n:,}: {len(df):,} rows validated", flush=True)
    return df


def check_nested_prefix(small, large, small_n, large_n):
    cols = [
        "scenario_id", "month_ahead", "demand", "price",
        "internal_duration_days", "podn_duration_days",
        "total_duration_days",
    ]

    for stream in sorted(small["stream_id"].unique()):
        a = (
            small[small["stream_id"] == stream]
            .sort_values(["scenario_id", "month_ahead"])[cols]
            .reset_index(drop=True)
        )

        b = (
            large[large["stream_id"] == stream]
            .sort_values(["scenario_id", "month_ahead"])[cols]
            .reset_index(drop=True)
        )

        if not a.equals(b.iloc[:len(a)].reset_index(drop=True)):
            raise ValueError(
                f"Nested prefix failure {small_n}->{large_n}: {stream}"
            )


def main():
    print("=" * 78)
    print("CMIDO RO3.3B — DECISION-LEVEL SCENARIO SENSITIVITY PRE-FLIGHT")
    print("=" * 78)
    print("This stage prepares and validates inputs.")
    print("It does NOT run the optimizer or invent optimization parameters.")
    print()

    data = {n: validate_scenario(n) for n in SIZES}

    print("[AUDIT] Checking 1,000 -> 2,500 nesting...", flush=True)
    check_nested_prefix(data[1000], data[2500], 1000, 2500)
    print("[PASS] 1,000 -> 2,500 nested prefix", flush=True)

    print("[AUDIT] Checking 2,500 -> 5,000 nesting...", flush=True)
    check_nested_prefix(data[2500], data[5000], 2500, 5000)
    print("[PASS] 2,500 -> 5,000 nested prefix", flush=True)

    print("[AUDIT] Checking 1,000 -> 5,000 nesting...", flush=True)
    check_nested_prefix(data[1000], data[5000], 1000, 5000)
    print("[PASS] 1,000 -> 5,000 nested prefix", flush=True)

    manifest = {
        "stage": "RO3.3B",
        "status": "DESIGN_READY_OPTIMIZER_FREEZE_REQUIRED",
        "scenario_sizes": SIZES,
        "forecast_origins": ORIGINS,
        "materials": MATERIALS,
        "primary_comparisons": [
            "1000_vs_2500",
            "2500_vs_5000",
        ],
        "secondary_comparison": "1000_vs_5000",
        "scenario_nesting_verified": True,
        "optimizer_run": False,
        "optimization_parameters_invented": False,
        "required_before_optimizer_run": [
            "freeze decision variables",
            "freeze feasible-region constraints",
            "freeze objective definitions",
            "freeze cost parameters",
            "freeze service/risk parameters",
            "freeze supplier/duration representation",
            "freeze safety-stock formulation",
            "freeze solver and settings",
            "freeze Pareto-generation procedure",
            "freeze decision-level materiality thresholds",
        ],
    }

    path = OUT_DIR / "RO3_step33B_preflight_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print()
    print("=" * 78)
    print("RO3.3B PRE-FLIGHT RESULT")
    print("=" * 78)
    print("Scenario integrity: PASS")
    print("Nested 1,000 -> 2,500: PASS")
    print("Nested 2,500 -> 5,000: PASS")
    print("Nested 1,000 -> 5,000: PASS")
    print("Optimizer execution: NOT RUN")
    print("Decision: RO3_3B_DESIGN_READY_OPTIMIZER_FREEZE_REQUIRED")
    print()
    print("Manifest:")
    print(path)


if __name__ == "__main__":
    main()
