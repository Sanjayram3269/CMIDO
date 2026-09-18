"""
CMIDO — RO1 Step 26C.3-G
FINAL PROBABILISTIC COMPARISON

Frozen conventional probabilistic statistical baseline
vs
Frozen ML + CQR

Important:
- No test-based model selection
- No test retraining
- No test recalibration
- Frozen 26B.1 selections are applied before comparison
- Series names are normalized ONLY for cross-artifact matching
- Primary: h=3, 80% interval, Winkler score
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"D:\CMIDO")

STAT_DIR = ROOT / "results" / "forecasting" / "probabilistic_statistical"
CQR_DIR = ROOT / "results" / "forecasting" / "probabilistic_calibration"
OUT_DIR = ROOT / "results" / "forecasting" / "final_probabilistic_comparison"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STAT_FORECAST = STAT_DIR / "RO1_step26b1_probabilistic_forecasts.csv"
STAT_SELECTION = STAT_DIR / "RO1_step26b1_selected_probabilistic_baselines.csv"
CQR_FORECAST = CQR_DIR / "RO1_step26c3_test_forecasts.csv"

PRIMARY_H = 3
HORIZONS = [1, 3, 6, 12]

EXPECTED_CANONICAL = {
    ("RO1_PRICE", "Cement"),
    ("RO1_PRICE", "Concreting Sand"),
    ("RO1_PRICE", "Granite"),
    ("RO1_PRICE", "Ready Mixed Concrete"),
    ("RO1_PRICE", "Steel Reinforcement Bars"),
    ("RO1_DEMAND", "Cement"),
    ("RO1_DEMAND", "Granite"),
    ("RO1_DEMAND", "Ready Mixed Concrete"),
    ("RO1_DEMAND", "Steel Reinforcement Bars"),
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def canonical_series(dataset, series):
    """Normalize only known source-name variants."""
    s = str(series).strip()

    if dataset == "RO1_PRICE":
        mapping = {
            "Cement In Bulk (Ordinary Portland Cement)": "Cement",
            "Concreting Sand": "Concreting Sand",
            "Granite (20mm Aggregate)": "Granite",
            "Ready Mixed Concrete": "Ready Mixed Concrete",
            "Steel Reinforcement Bars (16-32mm High Tensile)": "Steel Reinforcement Bars",
        }
        return mapping.get(s, s)

    if dataset == "RO1_DEMAND":
        mapping = {
            "Cement": "Cement",
            "Granite": "Granite",
            "Ready-Mixed Concrete": "Ready Mixed Concrete",
            "Ready Mixed Concrete": "Ready Mixed Concrete",
            "Steel Reinforcement Bars": "Steel Reinforcement Bars",
        }
        return mapping.get(s, s)

    return s


def winkler(y, lower, upper, alpha):
    y = np.asarray(y, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)

    score = upper - lower

    below = y < lower
    above = y > upper

    score[below] += (2.0 / alpha) * (lower[below] - y[below])
    score[above] += (2.0 / alpha) * (y[above] - upper[above])

    return score


def load_cqr():
    print("=" * 78)
    print("ML + CQR TEST ARTIFACT")
    print("=" * 78)

    require(CQR_FORECAST.exists(), f"Missing CQR file: {CQR_FORECAST}")

    df = pd.read_csv(CQR_FORECAST)

    required = [
        "dataset",
        "series",
        "horizon",
        "forecast_origin",
        "target_date",
        "actual",
        "calibrated_lower_50",
        "calibrated_upper_50",
        "calibrated_lower_80",
        "calibrated_upper_80",
    ]

    for c in required:
        require(c in df.columns, f"CQR file missing column: {c}")

    require(len(df) == 666, f"Expected 666 CQR test rows, found {len(df)}")

    df["series_canonical"] = [
        canonical_series(d, s)
        for d, s in zip(df["dataset"], df["series"])
    ]

    df["forecast_origin_dt"] = pd.to_datetime(
        df["forecast_origin"], errors="coerce"
    )
    df["target_date_dt"] = pd.to_datetime(
        df["target_date"], errors="coerce"
    )

    require(df["forecast_origin_dt"].notna().all(), "Invalid CQR origin dates.")
    require(df["target_date_dt"].notna().all(), "Invalid CQR target dates.")

    if "test_recalibration" in df.columns:
        flags = df["test_recalibration"].astype(str).str.upper()
        require(
            not flags.isin(["YES", "TRUE", "1"]).any(),
            "Test recalibration detected in CQR artifact.",
        )

    if "calibration_source" in df.columns:
        src = df["calibration_source"].astype(str).str.upper()
        require(
            src.str.contains("VALIDATION").all(),
            "CQR calibration source is not validation-only.",
        )

    out = pd.DataFrame({
        "dataset": df["dataset"].astype(str),
        "series_canonical": df["series_canonical"],
        "horizon": pd.to_numeric(df["horizon"], errors="raise").astype(int),
        "forecast_origin_dt": df["forecast_origin_dt"],
        "target_date_dt": df["target_date_dt"],
        "actual": pd.to_numeric(df["actual"], errors="coerce"),
        "ml_lower_50": pd.to_numeric(df["calibrated_lower_50"], errors="coerce"),
        "ml_upper_50": pd.to_numeric(df["calibrated_upper_50"], errors="coerce"),
        "ml_lower_80": pd.to_numeric(df["calibrated_lower_80"], errors="coerce"),
        "ml_upper_80": pd.to_numeric(df["calibrated_upper_80"], errors="coerce"),
    })

    require(out["actual"].notna().all(), "Missing CQR actual values.")
    require(
        set(zip(out["dataset"], out["series_canonical"])) == EXPECTED_CANONICAL,
        "CQR artifact does not contain exactly the expected nine canonical series.",
    )

    print(f"Loaded frozen ML+CQR test rows: {len(out)}")
    print("CQR validation-only calibration: PASS")
    print("CQR test recalibration: DISABLED")
    return out


def load_statistical():
    print("=" * 78)
    print("CONVENTIONAL PROBABILISTIC STATISTICAL ARTIFACT")
    print("=" * 78)

    require(STAT_FORECAST.exists(), f"Missing statistical file: {STAT_FORECAST}")
    require(STAT_SELECTION.exists(), f"Missing selection file: {STAT_SELECTION}")

    raw = pd.read_csv(STAT_FORECAST)
    selection = pd.read_csv(STAT_SELECTION)

    print(f"Loaded raw 26B.1 rows: {len(raw)}")
    print(f"Loaded frozen selection rows: {len(selection)}")

    required_raw = [
        "dataset",
        "split",
        "series",
        "model",
        "specification",
        "forecast_origin",
        "target_date",
        "horizon",
        "actual",
        "q10",
        "q25",
        "q50",
        "q75",
        "q90",
    ]

    for c in required_raw:
        require(c in raw.columns, f"26B.1 missing column: {c}")

    required_sel = [
        "dataset",
        "series",
        "primary_horizon",
        "selected_model",
    ]

    for c in required_sel:
        require(c in selection.columns, f"26B.1 selection missing column: {c}")

    # Normalize source names in BOTH artifacts before matching.
    selection["series_canonical"] = [
        canonical_series(d, s)
        for d, s in zip(selection["dataset"], selection["series"])
    ]

    raw["series_canonical"] = [
        canonical_series(d, s)
        for d, s in zip(raw["dataset"], raw["series"])
    ]

    selected_pairs = set(
        zip(
            selection["dataset"].astype(str),
            selection["series_canonical"].astype(str),
        )
    )

    require(
        selected_pairs == EXPECTED_CANONICAL,
        "Frozen 26B.1 selection does not contain exactly the nine expected canonical series.",
    )

    # One frozen selection per dataset/series.
    require(
        not selection.duplicated(
            ["dataset", "series_canonical"]
        ).any(),
        "Duplicate/ambiguous frozen 26B.1 selections.",
    )

    require(
        (pd.to_numeric(selection["primary_horizon"], errors="coerce") == PRIMARY_H).all(),
        "Frozen 26B.1 selection is not based on primary horizon h=3.",
    )

    # Apply frozen selection to TEST rows ONLY.
    test = raw[
        raw["split"].astype(str).str.lower() == "test"
    ].copy()

    require(len(test) > 0, "No 26B.1 test rows found.")

    test["forecast_origin_dt"] = pd.to_datetime(
        test["forecast_origin"], errors="coerce"
    )
    test["target_date_dt"] = pd.to_datetime(
        test["target_date"], errors="coerce"
    )

    require(
        test["forecast_origin_dt"].notna().all(),
        "Invalid statistical forecast-origin dates.",
    )
    require(
        test["target_date_dt"].notna().all(),
        "Invalid statistical target dates.",
    )

    frozen = selection[
        [
            "dataset",
            "series_canonical",
            "selected_model",
        ]
    ].copy()

    frozen["selected_model"] = frozen["selected_model"].astype(str)

    test = test.merge(
        frozen,
        on=["dataset", "series_canonical"],
        how="inner",
        validate="many_to_one",
    )

    # THIS is the critical correction:
    # filter the raw 26B.1 test artifact to the exact frozen model
    # only AFTER source-name normalization and selection merge.
    test = test[
        test["model"].astype(str) == test["selected_model"].astype(str)
    ].copy()

    require(
        len(test) > 0,
        "No 26B.1 test rows remain after frozen model selection.",
    )

    out = pd.DataFrame({
        "dataset": test["dataset"].astype(str),
        "series_canonical": test["series_canonical"],
        "horizon": pd.to_numeric(test["horizon"], errors="raise").astype(int),
        "forecast_origin_dt": test["forecast_origin_dt"],
        "target_date_dt": test["target_date_dt"],
        "actual": pd.to_numeric(test["actual"], errors="coerce"),
        "stat_lower_50": pd.to_numeric(test["q25"], errors="coerce"),
        "stat_upper_50": pd.to_numeric(test["q75"], errors="coerce"),
        "stat_lower_80": pd.to_numeric(test["q10"], errors="coerce"),
        "stat_upper_80": pd.to_numeric(test["q90"], errors="coerce"),
        "stat_model": test["model"].astype(str),
        "stat_specification": test["specification"].astype(str),
    })

    require(out["actual"].notna().all(), "Missing statistical actual values.")

    require(
        set(zip(out["dataset"], out["series_canonical"])) == EXPECTED_CANONICAL,
        "Filtered 26B.1 test artifact does not contain exactly nine expected series.",
    )

    print(f"Frozen statistical test rows: {len(out)}")
    print("Frozen 26B.1 model selection applied: PASS")

    print("\nFrozen models actually used:")
    print(
        out[
            ["dataset", "series_canonical", "stat_model"]
        ].drop_duplicates().sort_values(
            ["dataset", "series_canonical"]
        ).to_string(index=False)
    )

    return out


def match_artifacts(stat, ml):
    keys = [
        "dataset",
        "series_canonical",
        "horizon",
        "forecast_origin_dt",
        "target_date_dt",
    ]

    matched = stat.merge(
        ml,
        on=keys,
        how="inner",
        suffixes=("_stat", "_ml"),
        validate="one_to_one",
    )

    require(len(matched) > 0, "No matched statistical/ML test forecasts.")

    require(
        np.allclose(
            matched["actual_stat"].to_numpy(float),
            matched["actual_ml"].to_numpy(float),
            rtol=0.0,
            atol=1e-10,
        ),
        "Actual values differ between the two test artifacts.",
    )

    matched["actual"] = matched["actual_stat"]

    matched = matched.drop(
        columns=["actual_stat", "actual_ml"]
    )

    # Exact target-date/origin matching is required.
    require(
        not matched.duplicated(keys).any(),
        "Duplicate matched forecast target/origin keys.",
    )

    # Confirm every expected material/horizon cell is represented.
    expected_cells = {
        (d, s, h)
        for d, s in EXPECTED_CANONICAL
        for h in HORIZONS
    }

    actual_cells = set(
        zip(
            matched["dataset"],
            matched["series_canonical"],
            matched["horizon"],
        )
    )

    require(
        actual_cells == expected_cells,
        "Matched artifacts do not cover all nine series across all four horizons.",
    )

    return matched


def calculate_results(matched):
    rows = []

    for (
        dataset,
        series,
        horizon,
    ), g in matched.groupby(
        ["dataset", "series_canonical", "horizon"],
        sort=True,
    ):
        y = g["actual"].to_numpy(float)

        sl50 = g["stat_lower_50"].to_numpy(float)
        su50 = g["stat_upper_50"].to_numpy(float)
        sl80 = g["stat_lower_80"].to_numpy(float)
        su80 = g["stat_upper_80"].to_numpy(float)

        ml50 = g["ml_lower_50"].to_numpy(float)
        mu50 = g["ml_upper_50"].to_numpy(float)
        ml80 = g["ml_lower_80"].to_numpy(float)
        mu80 = g["ml_upper_80"].to_numpy(float)

        stat_cov50 = ((y >= sl50) & (y <= su50)).mean()
        ml_cov50 = ((y >= ml50) & (y <= mu50)).mean()

        stat_cov80 = ((y >= sl80) & (y <= su80)).mean()
        ml_cov80 = ((y >= ml80) & (y <= mu80)).mean()

        stat_w50 = winkler(y, sl50, su50, 0.50).mean()
        ml_w50 = winkler(y, ml50, mu50, 0.50).mean()

        stat_w80 = winkler(y, sl80, su80, 0.20).mean()
        ml_w80 = winkler(y, ml80, mu80, 0.20).mean()

        stat_ce50 = abs(stat_cov50 - 0.50)
        ml_ce50 = abs(ml_cov50 - 0.50)

        stat_ce80 = abs(stat_cov80 - 0.80)
        ml_ce80 = abs(ml_cov80 - 0.80)

        stat_width50 = (su50 - sl50).mean()
        ml_width50 = (mu50 - ml50).mean()

        stat_width80 = (su80 - sl80).mean()
        ml_width80 = (mu80 - ml80).mean()

        rows.append({
            "dataset": dataset,
            "series": series,
            "horizon": int(horizon),
            "n_matched": len(g),
            "stat_model": g["stat_model"].iloc[0],

            "stat_coverage_50": stat_cov50,
            "ml_cqr_coverage_50": ml_cov50,
            "stat_coverage_error_50": stat_ce50,
            "ml_cqr_coverage_error_50": ml_ce50,
            "stat_width_50": stat_width50,
            "ml_cqr_width_50": ml_width50,
            "stat_winkler_50": stat_w50,
            "ml_cqr_winkler_50": ml_w50,
            "winkler_50_change_ml_minus_stat": ml_w50 - stat_w50,

            "stat_coverage_80": stat_cov80,
            "ml_cqr_coverage_80": ml_cov80,
            "stat_coverage_error_80": stat_ce80,
            "ml_cqr_coverage_error_80": ml_ce80,
            "stat_width_80": stat_width80,
            "ml_cqr_width_80": ml_width80,
            "stat_winkler_80": stat_w80,
            "ml_cqr_winkler_80": ml_w80,
            "winkler_80_change_ml_minus_stat": ml_w80 - stat_w80,
            "coverage_error_80_change_ml_minus_stat": ml_ce80 - stat_ce80,
            "width_80_change_ml_minus_stat": ml_width80 - stat_width80,
        })

    out = pd.DataFrame(rows)

    require(
        len(out) == 36,
        f"Expected 36 series/horizon cells, found {len(out)}",
    )

    return out


def make_primary(results):
    p = results[
        results["horizon"] == PRIMARY_H
    ].copy()

    require(len(p) == 9, "Expected nine primary h=3 cells.")

    p["ML_CQR_Better_Winkler_80"] = (
        p["winkler_80_change_ml_minus_stat"] < 0
    )

    p["ML_CQR_Better_Calibration_80"] = (
        p["coverage_error_80_change_ml_minus_stat"] < 0
    )

    return p.sort_values(
        ["dataset", "series"]
    ).reset_index(drop=True)


def make_aggregate(primary):
    d = primary["winkler_80_change_ml_minus_stat"]

    return pd.DataFrame([{
        "horizon": PRIMARY_H,
        "n_series": len(primary),

        "mean_stat_winkler_80":
            primary["stat_winkler_80"].mean(),

        "mean_ml_cqr_winkler_80":
            primary["ml_cqr_winkler_80"].mean(),

        "mean_winkler_80_change_ml_minus_stat":
            d.mean(),

        "median_winkler_80_change_ml_minus_stat":
            d.median(),

        "n_ml_cqr_better_winkler_80":
            int((d < 0).sum()),

        "n_ml_cqr_worse_winkler_80":
            int((d > 0).sum()),

        "n_equal_winkler_80":
            int((d == 0).sum()),

        "mean_stat_coverage_error_80":
            primary["stat_coverage_error_80"].mean(),

        "mean_ml_cqr_coverage_error_80":
            primary["ml_cqr_coverage_error_80"].mean(),

        "mean_coverage_error_change_ml_minus_stat":
            primary["coverage_error_80_change_ml_minus_stat"].mean(),

        "mean_stat_width_80":
            primary["stat_width_80"].mean(),

        "mean_ml_cqr_width_80":
            primary["ml_cqr_width_80"].mean(),

        "mean_width_change_ml_minus_stat":
            primary["width_80_change_ml_minus_stat"].mean(),
    }])


def make_paired_observation_data(matched):
    """Long paired observation table for later paired statistical testing."""
    rows = []

    for _, r in matched.iterrows():
        rows.append({
            "dataset": r["dataset"],
            "series": r["series_canonical"],
            "horizon": int(r["horizon"]),
            "forecast_origin": r["forecast_origin_dt"],
            "target_date": r["target_date_dt"],
            "actual": r["actual"],

            "stat_lower_80": r["stat_lower_80"],
            "stat_upper_80": r["stat_upper_80"],
            "ml_cqr_lower_80": r["ml_lower_80"],
            "ml_cqr_upper_80": r["ml_upper_80"],

            "stat_winkler_80":
                winkler(
                    np.array([r["actual"]]),
                    np.array([r["stat_lower_80"]]),
                    np.array([r["stat_upper_80"]]),
                    0.20,
                )[0],

            "ml_cqr_winkler_80":
                winkler(
                    np.array([r["actual"]]),
                    np.array([r["ml_lower_80"]]),
                    np.array([r["ml_upper_80"]]),
                    0.20,
                )[0],
        })

    return pd.DataFrame(rows)


def main():
    print("=" * 78)
    print("CMIDO — RO1 STEP 26C.3-G")
    print("FINAL PROBABILISTIC COMPARISON")
    print("FROZEN CONVENTIONAL PROBABILISTIC vs FROZEN ML + CQR")
    print("=" * 78)
    print("Test model selection: DISABLED")
    print("Test retraining: DISABLED")
    print("Test recalibration: DISABLED")
    print("Primary horizon: 3")
    print("Primary interval: 80%")
    print()

    ml = load_cqr()
    stat = load_statistical()

    print()
    print("=" * 78)
    print("EXACT PAIRED MATCHING")
    print("=" * 78)

    matched = match_artifacts(stat, ml)

    print(f"Matched test forecast rows: {len(matched)}")

    results = calculate_results(matched)
    primary = make_primary(results)
    aggregate = make_aggregate(primary)
    paired = make_paired_observation_data(matched)

    full_path = OUT_DIR / "RO1_step26c3g_material_horizon_comparison.csv"
    primary_path = OUT_DIR / "RO1_step26c3g_primary_h3_comparison.csv"
    aggregate_path = OUT_DIR / "RO1_step26c3g_primary_h3_aggregate.csv"
    paired_path = OUT_DIR / "RO1_step26c3g_paired_observation_data.csv"

    results.to_csv(full_path, index=False)
    primary.to_csv(primary_path, index=False)
    aggregate.to_csv(aggregate_path, index=False)
    paired.to_csv(paired_path, index=False)

    print("Exact origin/target matching: PASS")
    print("Actual-value identity check: PASS")
    print("Nine-series × four-horizon coverage: PASS")

    print()
    print("=" * 78)
    print("PRIMARY h=3 / 80% INTERVAL")
    print("=" * 78)

    cols = [
        "dataset",
        "series",
        "n_matched",
        "stat_model",
        "stat_coverage_80",
        "ml_cqr_coverage_80",
        "stat_coverage_error_80",
        "ml_cqr_coverage_error_80",
        "stat_width_80",
        "ml_cqr_width_80",
        "stat_winkler_80",
        "ml_cqr_winkler_80",
        "winkler_80_change_ml_minus_stat",
    ]

    print(
        primary[cols].to_string(
            index=False,
            float_format=lambda x: f"{x:.6f}",
        )
    )

    print()
    print("=" * 78)
    print("PRIMARY AGGREGATE")
    print("=" * 78)

    print(
        aggregate.to_string(
            index=False,
            float_format=lambda x: f"{x:.6f}",
        )
    )

    print()
    print("=" * 78)
    print("OUTPUTS")
    print("=" * 78)
    print(full_path)
    print(primary_path)
    print(aggregate_path)
    print(paired_path)

    print()
    print("=" * 78)
    print("ALL STEP 26C.3-G ASSERTIONS: PASS")
    print("=" * 78)


if __name__ == "__main__":
    main()
