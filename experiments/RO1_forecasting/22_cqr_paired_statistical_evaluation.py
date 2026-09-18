"""
CMIDO — RO1 Step 26C.3-F
Paired Statistical Evaluation of Frozen CQR on the Untouched Test Set

Purpose
-------
Inferential/descriptive comparison of RAW ML intervals versus frozen CQR
intervals using the already-generated Step 26C.3-D test forecasts.

No:
- retraining
- model reselection
- recalibration
- parameter estimation
- test-based model tuning

Primary horizon:
    h = 3

Primary interval:
    80% interval

Statistical design
------------------
For each dataset/material/horizon, paired forecast origins are retained.

Primary loss:
    Winkler interval score for the 80% interval.

Secondary losses:
    50% interval Winkler score
    80% interval width
    50% interval width
    absolute coverage-indicator deviation from nominal coverage

Because forecast errors are serially dependent, the script uses a
paired block bootstrap over chronological forecast origins for the
difference in mean loss.

The block length is horizon-dependent:
    block length = max(2, horizon)

The bootstrap resamples contiguous blocks with replacement until the
original sample size is restored.

A two-sided empirical bootstrap p-value and percentile 95% CI are
reported.

Important:
This is an inferential comparison of RAW versus CQR on the fixed test
forecasts. It is NOT a claim of universal model superiority.

Multiple-comparison adjustment:
Benjamini-Hochberg FDR is applied separately within each metric and
horizon across the nine series. The primary h=3 80% Winkler comparison
therefore reports both raw and BH-adjusted p-values.

"""

from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd


ROOT = Path(r"D:\CMIDO")
CAL_DIR = ROOT / "results" / "forecasting" / "probabilistic_calibration"
INPUT_PATH = CAL_DIR / "RO1_step26c3_test_forecasts.csv"
OUT_DIR = CAL_DIR / "analysis_26c3f"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HORIZONS = [1, 3, 6, 12]
PRIMARY_HORIZON = 3
PRIMARY_INTERVAL = 0.80

BOOTSTRAP_REPS = 10000
BOOTSTRAP_SEED = 26306

EXPECTED_FORECAST_ROWS = 666

EXPECTED_PAIRS = {
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


def first_existing(columns, candidates, label):
    for c in candidates:
        if c in columns:
            return c
    raise KeyError(
        f"Missing {label}. Available columns:\n"
        + "\n".join(map(str, columns))
    )


def load_forecasts():
    require(INPUT_PATH.exists(), f"Missing: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)

    require(
        len(df) == EXPECTED_FORECAST_ROWS,
        f"Expected {EXPECTED_FORECAST_ROWS} rows, found {len(df)}",
    )

    dataset_col = first_existing(
        df.columns, ["dataset", "Dataset"], "dataset"
    )
    series_col = first_existing(
        df.columns,
        ["series", "Series", "material", "Material"],
        "series",
    )
    horizon_col = first_existing(
        df.columns, ["horizon", "Horizon"], "horizon"
    )
    origin_col = first_existing(
        df.columns,
        ["forecast_origin", "origin", "ForecastOrigin"],
        "forecast origin",
    )
    target_col = first_existing(
        df.columns,
        ["target_date", "target", "TargetDate"],
        "target date",
    )
    actual_col = first_existing(
        df.columns,
        ["actual", "y_true", "observed"],
        "actual",
    )

    required_interval_cols = [
        "raw_lower_50",
        "raw_upper_50",
        "raw_lower_80",
        "raw_upper_80",
        "calibrated_lower_50",
        "calibrated_upper_50",
        "calibrated_lower_80",
        "calibrated_upper_80",
    ]

    for c in required_interval_cols:
        require(
            c in df.columns,
            f"Missing required interval column: {c}",
        )

    # Normalize internal names without changing source data.
    df = df.rename(
        columns={
            dataset_col: "_dataset",
            series_col: "_series",
            horizon_col: "_horizon",
            origin_col: "_origin",
            target_col: "_target",
            actual_col: "_actual",
        }
    )

    df["_horizon"] = df["_horizon"].astype(int)
    df["_origin_dt"] = pd.to_datetime(
        df["_origin"], errors="coerce"
    )
    df["_target_dt"] = pd.to_datetime(
        df["_target"], errors="coerce"
    )

    require(
        df["_origin_dt"].notna().all(),
        "Invalid forecast-origin dates detected.",
    )
    require(
        df["_target_dt"].notna().all(),
        "Invalid target dates detected.",
    )

    require(
        set(df["_horizon"]) == set(HORIZONS),
        "Required horizons missing.",
    )

    pairs = set(
        zip(df["_dataset"], df["_series"])
    )
    require(
        pairs == EXPECTED_PAIRS,
        "Expected nine dataset/material pairs missing.",
    )

    # Exact one row per dataset/series/horizon/origin.
    require(
        not df.duplicated(
            ["_dataset", "_series", "_horizon", "_origin_dt"]
        ).any(),
        "Duplicate forecast-origin rows detected.",
    )

    # Test artifact should not contain a calibration-updated test parameter.
    if "test_recalibration" in df.columns:
        vals = (
            df["test_recalibration"]
            .astype(str)
            .str.upper()
        )
        require(
            ~vals.isin(["YES", "TRUE", "1"]).any(),
            "Test recalibration flag indicates test recalibration.",
        )

    print(f"Loaded frozen test forecasts: {len(df)}")
    print("Test forecast structure: PASS")

    return df


def winkler_score(y, lower, upper, alpha):
    y = np.asarray(y, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)

    width = upper - lower

    below = y < lower
    above = y > upper

    score = width.copy()

    score[below] += (
        (2.0 / alpha)
        * (lower[below] - y[below])
    )

    score[above] += (
        (2.0 / alpha)
        * (y[above] - upper[above])
    )

    return score


def interval_width(lower, upper):
    return np.asarray(upper, dtype=float) - np.asarray(
        lower, dtype=float
    )


def coverage_indicator(y, lower, upper):
    return (
        (np.asarray(y) >= np.asarray(lower))
        & (np.asarray(y) <= np.asarray(upper))
    ).astype(float)


def block_indices(n, block_length, rng):
    if n <= 0:
        return np.array([], dtype=int)

    if block_length >= n:
        return np.arange(n, dtype=int)

    starts = np.arange(
        0,
        n - block_length + 1,
        dtype=int,
    )

    selected = []

    while len(selected) < n:
        start = int(
            rng.choice(starts)
        )
        selected.extend(
            range(
                start,
                min(
                    start + block_length,
                    n,
                ),
            )
        )

    return np.asarray(
        selected[:n],
        dtype=int,
    )


def bootstrap_difference(
    difference,
    block_length,
    reps,
    seed,
):
    difference = np.asarray(
        difference,
        dtype=float,
    )

    difference = difference[
        np.isfinite(difference)
    ]

    n = len(difference)

    require(
        n >= 2,
        "At least two paired observations are required.",
    )

    observed = float(
        np.mean(difference)
    )

    rng = np.random.default_rng(seed)

    boot = np.empty(
        reps,
        dtype=float,
    )

    for b in range(reps):
        idx = block_indices(
            n,
            block_length,
            rng,
        )
        boot[b] = np.mean(
            difference[idx]
        )

    ci_low, ci_high = np.quantile(
        boot,
        [0.025, 0.975],
    )

    # Two-sided empirical p-value for H0: mean difference = 0.
    # Center bootstrap distribution around zero.
    centered = boot - observed
    p = 2.0 * min(
        np.mean(centered <= -abs(observed)),
        np.mean(centered >= abs(observed)),
    )

    p = float(
        min(1.0, max(0.0, p))
    )

    return (
        observed,
        float(ci_low),
        float(ci_high),
        p,
    )


def bh_adjust(pvalues):
    """
    Benjamini-Hochberg FDR adjustment.
    NaNs remain NaN.
    """
    p = np.asarray(
        pvalues,
        dtype=float,
    )

    out = np.full_like(
        p,
        np.nan,
    )

    valid = np.isfinite(p)

    if not valid.any():
        return out

    pv = p[valid]
    m = len(pv)

    order = np.argsort(pv)
    ranked = pv[order]

    adjusted = np.empty(
        m,
        dtype=float,
    )

    running = 1.0

    for i in range(
        m - 1,
        -1,
        -1,
    ):
        rank = i + 1
        value = (
            ranked[i]
            * m
            / rank
        )
        running = min(
            running,
            value,
        )
        adjusted[i] = running

    restored = np.empty(
        m,
        dtype=float,
    )
    restored[order] = np.minimum(
        adjusted,
        1.0,
    )

    out[valid] = restored

    return out


def compute_cell(df, dataset, series, horizon):
    g = df[
        (df["_dataset"] == dataset)
        & (df["_series"] == series)
        & (df["_horizon"] == horizon)
    ].copy()

    g = g.sort_values(
        ["_origin_dt", "_target_dt"]
    ).reset_index(drop=True)

    require(
        len(g) >= 2,
        f"Insufficient observations for {dataset}/{series}/h={horizon}",
    )

    y = g["_actual"].to_numpy(float)

    # Raw versus calibrated intervals.
    raw_l50 = g["raw_lower_50"].to_numpy(float)
    raw_u50 = g["raw_upper_50"].to_numpy(float)
    cqr_l50 = g["calibrated_lower_50"].to_numpy(float)
    cqr_u50 = g["calibrated_upper_50"].to_numpy(float)

    raw_l80 = g["raw_lower_80"].to_numpy(float)
    raw_u80 = g["raw_upper_80"].to_numpy(float)
    cqr_l80 = g["calibrated_lower_80"].to_numpy(float)
    cqr_u80 = g["calibrated_upper_80"].to_numpy(float)

    # Primary: lower is better for Winkler loss.
    raw_w80 = winkler_score(
        y,
        raw_l80,
        raw_u80,
        alpha=0.20,
    )
    cqr_w80 = winkler_score(
        y,
        cqr_l80,
        cqr_u80,
        alpha=0.20,
    )

    # Secondary.
    raw_w50 = winkler_score(
        y,
        raw_l50,
        raw_u50,
        alpha=0.50,
    )
    cqr_w50 = winkler_score(
        y,
        cqr_l50,
        cqr_u50,
        alpha=0.50,
    )

    raw_width50 = interval_width(
        raw_l50,
        raw_u50,
    )
    cqr_width50 = interval_width(
        cqr_l50,
        cqr_u50,
    )

    raw_width80 = interval_width(
        raw_l80,
        raw_u80,
    )
    cqr_width80 = interval_width(
        cqr_l80,
        cqr_u80,
    )

    raw_cov50 = coverage_indicator(
        y,
        raw_l50,
        raw_u50,
    )
    cqr_cov50 = coverage_indicator(
        y,
        cqr_l50,
        cqr_u50,
    )

    raw_cov80 = coverage_indicator(
        y,
        raw_l80,
        raw_u80,
    )
    cqr_cov80 = coverage_indicator(
        y,
        cqr_l80,
        cqr_u80,
    )

    metrics = [
        (
            "winkler_80",
            raw_w80,
            cqr_w80,
        ),
        (
            "winkler_50",
            raw_w50,
            cqr_w50,
        ),
        (
            "width_80",
            raw_width80,
            cqr_width80,
        ),
        (
            "width_50",
            raw_width50,
            cqr_width50,
        ),
        (
            "coverage_indicator_80",
            raw_cov80,
            cqr_cov80,
        ),
        (
            "coverage_indicator_50",
            raw_cov50,
            cqr_cov50,
        ),
    ]

    block_length = max(
        2,
        int(horizon),
    )

    rows = []

    for metric_name, raw, cqr in metrics:
        difference = cqr - raw

        observed, ci_low, ci_high, p = (
            bootstrap_difference(
                difference=difference,
                block_length=block_length,
                reps=BOOTSTRAP_REPS,
                seed=(
                    BOOTSTRAP_SEED
                    + horizon * 100
                    + len(rows)
                    + abs(hash((dataset, series))) % 10000
                ),
            )
        )

        rows.append({
            "dataset": dataset,
            "series": series,
            "horizon": horizon,
            "n_test": len(g),
            "metric": metric_name,

            "raw_mean": float(np.mean(raw)),
            "cqr_mean": float(np.mean(cqr)),

            # Difference is always CQR - Raw.
            # Negative is better for loss/width.
            "difference_cqr_minus_raw": observed,

            "bootstrap_ci_low": ci_low,
            "bootstrap_ci_high": ci_high,
            "p_value": p,
            "block_length": block_length,
            "bootstrap_reps": BOOTSTRAP_REPS,
        })

    return rows


def run_all_cells(df):
    rows = []

    for dataset, series in sorted(EXPECTED_PAIRS):
        for horizon in HORIZONS:
            rows.extend(
                compute_cell(
                    df,
                    dataset,
                    series,
                    horizon,
                )
            )

    out = pd.DataFrame(rows)

    require(
        len(out) == 9 * 4 * 6,
        f"Expected 216 inferential rows, found {len(out)}",
    )

    return out


def add_fdr_adjustment(results):
    results = results.copy()

    results["p_value_bh"] = np.nan

    # Adjust across the nine series separately for every
    # metric/horizon combination.
    for (metric, horizon), idx in results.groupby(
        ["metric", "horizon"]
    ).groups.items():

        p = results.loc[
            idx,
            "p_value",
        ].to_numpy(float)

        results.loc[
            idx,
            "p_value_bh",
        ] = bh_adjust(p)

    results["raw_significant_05"] = (
        results["p_value"] < 0.05
    )

    results["bh_significant_05"] = (
        results["p_value_bh"] < 0.05
    )

    return results


def primary_summary(results):
    p = results[
        (results["horizon"] == PRIMARY_HORIZON)
        & (results["metric"] == "winkler_80")
    ].copy()

    require(
        len(p) == 9,
        "Primary h=3 Winkler-80 must contain nine series.",
    )

    # For Winkler, lower is better.
    p["cqr_better"] = (
        p["difference_cqr_minus_raw"] < 0
    )

    p["ci_excludes_zero"] = (
        (
            p["bootstrap_ci_low"] > 0
        )
        |
        (
            p["bootstrap_ci_high"] < 0
        )
    )

    return p.sort_values(
        ["dataset", "series"]
    ).reset_index(drop=True)


def aggregate_primary(primary):
    diff = primary[
        "difference_cqr_minus_raw"
    ].to_numpy(float)

    raw = primary[
        "raw_mean"
    ].to_numpy(float)

    cqr = primary[
        "cqr_mean"
    ].to_numpy(float)

    return pd.DataFrame([{
        "horizon": PRIMARY_HORIZON,
        "metric": "winkler_80",
        "n_series": len(primary),

        "mean_of_series_raw": float(np.mean(raw)),
        "mean_of_series_cqr": float(np.mean(cqr)),
        "mean_of_series_difference":
            float(np.mean(diff)),

        "median_series_difference":
            float(np.median(diff)),

        "n_cqr_better":
            int((diff < 0).sum()),

        "n_cqr_worse":
            int((diff > 0).sum()),

        "n_equal":
            int((diff == 0).sum()),

        "n_raw_p_lt_005":
            int(
                (primary["p_value"] < 0.05).sum()
            ),

        "n_bh_p_lt_005":
            int(
                (primary["p_value_bh"] < 0.05).sum()
            ),
    }])


def make_report(primary, aggregate):
    a = aggregate.iloc[0]

    lines = [
        "CMIDO — RO1 STEP 26C.3-F",
        "PAIRED STATISTICAL EVALUATION OF FROZEN CQR",
        "",
        "STATUS: COMPLETED",
        "",
        "Primary horizon: h=3",
        "Primary metric: 80% Winkler interval score",
        "Lower Winkler score = better.",
        "",
        "Test set: untouched before frozen CQR application.",
        "CQR parameters: frozen from validation.",
        "Bootstrap: chronological block bootstrap.",
        f"Bootstrap repetitions: {BOOTSTRAP_REPS}",
        f"Bootstrap seed: {BOOTSTRAP_SEED}",
        "",
        "PRIMARY h=3 AGGREGATE DESCRIPTIVE RESULT",
        f"Mean series-level raw Winkler-80: {a['mean_of_series_raw']:.6f}",
        f"Mean series-level CQR Winkler-80: {a['mean_of_series_cqr']:.6f}",
        f"Mean series-level difference (CQR-Raw): {a['mean_of_series_difference']:.6f}",
        f"Median series-level difference: {a['median_series_difference']:.6f}",
        f"CQR better: {int(a['n_cqr_better'])}/9",
        f"CQR worse: {int(a['n_cqr_worse'])}/9",
        "",
        "SIGNIFICANCE COUNTS",
        f"Raw p<0.05: {int(a['n_raw_p_lt_005'])}/9",
        f"BH-adjusted p<0.05: {int(a['n_bh_p_lt_005'])}/9",
        "",
        "INTERPRETATION RULE",
        "A negative CQR-Raw Winkler difference favors CQR.",
        "A bootstrap confidence interval excluding zero indicates evidence",
        "of a difference for that individual series.",
        "BH-adjusted significance controls false-discovery rate across the",
        "nine series for the primary metric/horizon family.",
        "",
        "CAUTION",
        "The nine series are not independent replications of one population.",
        "Therefore the primary scientific claim should emphasize consistency",
        "of paired time-series evidence and effect direction rather than treating",
        "the nine material series as a conventional independent sample.",
        "",
        "This analysis does not compare CQR against conventional statistical",
        "probabilistic forecasting. That is a separate RO1 comparison.",
    ]

    return "\n".join(lines)


def main():
    print("=" * 78)
    print("CMIDO — STEP 26C.3-F")
    print("PAIRED STATISTICAL EVALUATION OF FROZEN CQR")
    print("=" * 78)

    df = load_forecasts()

    print()
    print("Running paired chronological block-bootstrap comparisons...")
    print(f"Bootstrap repetitions per metric cell: {BOOTSTRAP_REPS}")

    results = run_all_cells(df)
    results = add_fdr_adjustment(results)

    primary = primary_summary(results)
    aggregate = aggregate_primary(primary)
    report = make_report(
        primary,
        aggregate,
    )

    all_results_path = OUT_DIR / (
        "RO1_step26c3f_paired_bootstrap_results.csv"
    )
    primary_path = OUT_DIR / (
        "RO1_step26c3f_primary_h3_winkler_results.csv"
    )
    aggregate_path = OUT_DIR / (
        "RO1_step26c3f_primary_h3_aggregate.csv"
    )
    report_path = OUT_DIR / (
        "RO1_step26c3f_statistical_report.txt"
    )

    results.to_csv(
        all_results_path,
        index=False,
    )
    primary.to_csv(
        primary_path,
        index=False,
    )
    aggregate.to_csv(
        aggregate_path,
        index=False,
    )
    report_path.write_text(
        report,
        encoding="utf-8",
    )

    print()
    print("-" * 78)
    print("PRIMARY h=3 WINKLER-80 RESULTS")
    print("-" * 78)

    display_cols = [
        "dataset",
        "series",
        "n_test",
        "raw_mean",
        "cqr_mean",
        "difference_cqr_minus_raw",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
        "p_value",
        "p_value_bh",
        "cqr_better",
    ]

    print(
        primary[display_cols].to_string(
            index=False,
            float_format=lambda x: f"{x:.6f}",
        )
    )

    print()
    print("-" * 78)
    print("PRIMARY h=3 AGGREGATE")
    print("-" * 78)

    print(
        aggregate.to_string(
            index=False,
            float_format=lambda x: f"{x:.6f}",
        )
    )

    print()
    print("-" * 78)
    print("SAVED OUTPUTS")
    print("-" * 78)

    for path in [
        all_results_path,
        primary_path,
        aggregate_path,
        report_path,
    ]:
        print(path)

    print()
    print("=" * 78)
    print("ALL STEP 26C.3-F ASSERTIONS: PASS")
    print("=" * 78)


if __name__ == "__main__":
    main()
