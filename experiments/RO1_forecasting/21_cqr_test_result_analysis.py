"""
CMIDO — RO1 Step 26C.3-E
Frozen CQR Test-Result Analysis

Reads only the completed Step 26C.3-D test artifacts.
No retraining, reselection, recalibration, or parameter modification.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"D:\CMIDO")
CAL_DIR = ROOT / "results" / "forecasting" / "probabilistic_calibration"
OUT_DIR = CAL_DIR / "analysis_26c3e"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FORECAST_PATH = CAL_DIR / "RO1_step26c3_test_forecasts.csv"
METRICS_PATH = CAL_DIR / "RO1_step26c3_test_metrics.csv"
PRIMARY_INPUT = CAL_DIR / "RO1_step26c3_primary_h3_summary.csv"

HORIZONS = [1, 3, 6, 12]
PRIMARY_HORIZON = 3

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
        f"Could not find {label}. Available columns:\n"
        + "\n".join(map(str, columns))
    )


def load_inputs():
    require(FORECAST_PATH.exists(), f"Missing: {FORECAST_PATH}")
    require(METRICS_PATH.exists(), f"Missing: {METRICS_PATH}")
    require(PRIMARY_INPUT.exists(), f"Missing: {PRIMARY_INPUT}")

    fc = pd.read_csv(FORECAST_PATH)
    mt = pd.read_csv(METRICS_PATH)
    primary_original = pd.read_csv(PRIMARY_INPUT)

    print("Forecast columns:")
    print(", ".join(fc.columns.astype(str)))
    print()
    print("Metric columns:")
    print(", ".join(mt.columns.astype(str)))
    print()

    require(len(fc) == 666, f"Expected 666 test forecasts, found {len(fc)}")
    require(len(mt) == 36, f"Expected 36 metric cells, found {len(mt)}")

    dataset_col = first_existing(
        mt.columns,
        ["dataset", "Dataset"],
        "dataset column",
    )
    series_col = first_existing(
        mt.columns,
        ["series", "Series", "material", "Material"],
        "series/material column",
    )
    horizon_col = first_existing(
        mt.columns,
        ["horizon", "Horizon"],
        "horizon column",
    )

    pairs = set(
        zip(
            mt[dataset_col].astype(str),
            mt[series_col].astype(str),
        )
    )
    require(
        pairs == EXPECTED_PAIRS,
        "Expected nine dataset/material series are not present.",
    )

    require(
        set(mt[horizon_col].astype(int)) == set(HORIZONS),
        "Not all required horizons are present.",
    )

    # The Step 26C.3-D artifact is already test-only.
    # A split column is optional.
    if "split" in fc.columns:
        require(
            fc["split"].astype(str).str.lower().eq("test").all(),
            "Non-test rows found in forecast artifact.",
        )

    print(f"Loaded frozen test forecasts: {len(fc)}")
    print(f"Loaded metric cells:          {len(mt)}")
    print(f"Loaded original h=3 summary:  {len(primary_original)} rows")

    return fc, mt


def get_metric_col(df, candidates, label):
    return first_existing(df.columns, candidates, label)


def material_horizon_table(mt):
    dataset_col = get_metric_col(mt, ["dataset", "Dataset"], "dataset")
    series_col = get_metric_col(
        mt, ["series", "Series", "material", "Material"], "series"
    )
    horizon_col = get_metric_col(mt, ["horizon", "Horizon"], "horizon")

    c50r = get_metric_col(
        mt,
        ["raw_coverage_50", "Raw_coverage_50", "raw_50_coverage"],
        "raw 50% coverage",
    )
    c50c = get_metric_col(
        mt,
        ["cqr_coverage_50", "CQR_coverage_50", "cqr_50_coverage"],
        "CQR 50% coverage",
    )
    e50r = get_metric_col(
        mt,
        ["raw_coverage_error_50", "Raw_coverage_error_50"],
        "raw 50% coverage error",
    )
    e50c = get_metric_col(
        mt,
        ["cqr_coverage_error_50", "CQR_coverage_error_50"],
        "CQR 50% coverage error",
    )
    w50r = get_metric_col(
        mt,
        ["raw_mean_width_50", "Raw_mean_width_50"],
        "raw 50% width",
    )
    w50c = get_metric_col(
        mt,
        ["cqr_mean_width_50", "CQR_mean_width_50"],
        "CQR 50% width",
    )
    c80r = get_metric_col(
        mt,
        ["raw_coverage_80", "Raw_coverage_80", "raw_80_coverage"],
        "raw 80% coverage",
    )
    c80c = get_metric_col(
        mt,
        ["cqr_coverage_80", "CQR_coverage_80", "cqr_80_coverage"],
        "CQR 80% coverage",
    )
    e80r = get_metric_col(
        mt,
        ["raw_coverage_error_80", "Raw_coverage_error_80"],
        "raw 80% coverage error",
    )
    e80c = get_metric_col(
        mt,
        ["cqr_coverage_error_80", "CQR_coverage_error_80"],
        "CQR 80% coverage error",
    )
    w80r = get_metric_col(
        mt,
        ["raw_mean_width_80", "Raw_mean_width_80"],
        "raw 80% width",
    )
    w80c = get_metric_col(
        mt,
        ["cqr_mean_width_80", "CQR_mean_width_80"],
        "CQR 80% width",
    )
    winkr = get_metric_col(
        mt,
        ["raw_winkler_80", "Raw_winkler_80"],
        "raw Winkler-80",
    )
    winkc = get_metric_col(
        mt,
        ["cqr_winkler_80", "CQR_winkler_80"],
        "CQR Winkler-80",
    )

    rows = []

    for _, r in mt.sort_values(
        [dataset_col, series_col, horizon_col]
    ).iterrows():
        rows.append({
            "Dataset": r[dataset_col],
            "Material": r[series_col],
            "Horizon": int(r[horizon_col]),
            "N": int(r["n_test"]) if "n_test" in mt.columns else np.nan,

            "Raw_50_Coverage": r[c50r],
            "CQR_50_Coverage": r[c50c],
            "Raw_50_Coverage_Error": r[e50r],
            "CQR_50_Coverage_Error": r[e50c],
            "Raw_50_Width": r[w50r],
            "CQR_50_Width": r[w50c],

            "Raw_80_Coverage": r[c80r],
            "CQR_80_Coverage": r[c80c],
            "Raw_80_Coverage_Error": r[e80r],
            "CQR_80_Coverage_Error": r[e80c],
            "Raw_80_Width": r[w80r],
            "CQR_80_Width": r[w80c],

            "Raw_Winkler_80": r[winkr],
            "CQR_Winkler_80": r[winkc],

            "Coverage_Error_Change_50": r[e50c] - r[e50r],
            "Coverage_Error_Change_80": r[e80c] - r[e80r],
            "Width_Change_50": r[w50c] - r[w50r],
            "Width_Change_80": r[w80c] - r[w80r],
            "Winkler_Change_80": r[winkc] - r[winkr],
        })

    return pd.DataFrame(rows)


def primary_h3_table(mt):
    t = material_horizon_table(mt)
    p = t[t["Horizon"] == PRIMARY_HORIZON].copy()

    require(len(p) == 9, "Primary h=3 must contain nine series.")

    p["CQR_Improves_50_Calibration"] = (
        p["CQR_50_Coverage_Error"]
        < p["Raw_50_Coverage_Error"]
    )
    p["CQR_Improves_80_Calibration"] = (
        p["CQR_80_Coverage_Error"]
        < p["Raw_80_Coverage_Error"]
    )
    p["CQR_Better_Winkler_80"] = (
        p["CQR_Winkler_80"] < p["Raw_Winkler_80"]
    )
    p["CQR_Narrower_50"] = (
        p["CQR_50_Width"] < p["Raw_50_Width"]
    )
    p["CQR_Narrower_80"] = (
        p["CQR_80_Width"] < p["Raw_80_Width"]
    )

    return p.reset_index(drop=True)


def aggregate_table(t):
    groups = [
        ("ALL", t),
        ("RO1_PRICE", t[t["Dataset"] == "RO1_PRICE"]),
        ("RO1_DEMAND", t[t["Dataset"] == "RO1_DEMAND"]),
    ]

    rows = []

    for label, g in groups:
        for h in HORIZONS:
            x = g[g["Horizon"] == h]
            if x.empty:
                continue

            rows.append({
                "Group": label,
                "Horizon": h,
                "N_series": len(x),

                "Raw_Mean_Coverage_50":
                    x["Raw_50_Coverage"].mean(),
                "CQR_Mean_Coverage_50":
                    x["CQR_50_Coverage"].mean(),
                "Raw_Mean_Coverage_Error_50":
                    x["Raw_50_Coverage_Error"].mean(),
                "CQR_Mean_Coverage_Error_50":
                    x["CQR_50_Coverage_Error"].mean(),
                "Raw_Mean_Width_50":
                    x["Raw_50_Width"].mean(),
                "CQR_Mean_Width_50":
                    x["CQR_50_Width"].mean(),

                "Raw_Mean_Coverage_80":
                    x["Raw_80_Coverage"].mean(),
                "CQR_Mean_Coverage_80":
                    x["CQR_80_Coverage"].mean(),
                "Raw_Mean_Coverage_Error_80":
                    x["Raw_80_Coverage_Error"].mean(),
                "CQR_Mean_Coverage_Error_80":
                    x["CQR_80_Coverage_Error"].mean(),
                "Raw_Mean_Width_80":
                    x["Raw_80_Width"].mean(),
                "CQR_Mean_Width_80":
                    x["CQR_80_Width"].mean(),

                "Raw_Mean_Winkler_80":
                    x["Raw_Winkler_80"].mean(),
                "CQR_Mean_Winkler_80":
                    x["CQR_Winkler_80"].mean(),

                "Mean_Coverage_Error_Change_50":
                    x["Coverage_Error_Change_50"].mean(),
                "Mean_Coverage_Error_Change_80":
                    x["Coverage_Error_Change_80"].mean(),
                "Mean_Width_Change_50":
                    x["Width_Change_50"].mean(),
                "Mean_Width_Change_80":
                    x["Width_Change_80"].mean(),
                "Mean_Winkler_Change_80":
                    x["Winkler_Change_80"].mean(),

                "N_Better_50_Calibration":
                    int((x["Coverage_Error_Change_50"] < 0).sum()),
                "N_Better_80_Calibration":
                    int((x["Coverage_Error_Change_80"] < 0).sum()),
                "N_Better_Winkler_80":
                    int((x["Winkler_Change_80"] < 0).sum()),
            })

    return pd.DataFrame(rows)


def observation_level_paired(fc):
    # Detect actual forecast column names once.
    actual_col = first_existing(
        fc.columns,
        ["actual", "y_true", "target", "observed"],
        "actual target",
    )
    dataset_col = first_existing(
        fc.columns, ["dataset", "Dataset"], "dataset"
    )
    series_col = first_existing(
        fc.columns,
        ["series", "Series", "material", "Material"],
        "series",
    )
    horizon_col = first_existing(
        fc.columns, ["horizon", "Horizon"], "horizon"
    )

    raw_l50 = first_existing(
        fc.columns,
        ["raw_lower_50", "raw_q25", "raw_lower50"],
        "raw lower 50%",
    )
    raw_u50 = first_existing(
        fc.columns,
        ["raw_upper_50", "raw_q75", "raw_upper50"],
        "raw upper 50%",
    )
    cqr_l50 = first_existing(
        fc.columns,
        ["calibrated_lower_50", "cqr_lower_50", "cqr_lower50"],
        "CQR lower 50%",
    )
    cqr_u50 = first_existing(
        fc.columns,
        ["calibrated_upper_50", "cqr_upper_50", "cqr_upper50"],
        "CQR upper 50%",
    )
    raw_l80 = first_existing(
        fc.columns,
        ["raw_lower_80", "raw_q10", "raw_lower80"],
        "raw lower 80%",
    )
    raw_u80 = first_existing(
        fc.columns,
        ["raw_upper_80", "raw_q90", "raw_upper80"],
        "raw upper 80%",
    )
    cqr_l80 = first_existing(
        fc.columns,
        ["calibrated_lower_80", "cqr_lower_80", "cqr_lower80"],
        "CQR lower 80%",
    )
    cqr_u80 = first_existing(
        fc.columns,
        ["calibrated_upper_80", "cqr_upper_80", "cqr_upper80"],
        "CQR upper 80%",
    )

    rows = []

    for (dataset, series, horizon), g in fc.groupby(
        [dataset_col, series_col, horizon_col],
        sort=True,
    ):
        y = g[actual_col].to_numpy(float)

        rl50 = g[raw_l50].to_numpy(float)
        ru50 = g[raw_u50].to_numpy(float)
        cl50 = g[cqr_l50].to_numpy(float)
        cu50 = g[cqr_u50].to_numpy(float)

        rl80 = g[raw_l80].to_numpy(float)
        ru80 = g[raw_u80].to_numpy(float)
        cl80 = g[cqr_l80].to_numpy(float)
        cu80 = g[cqr_u80].to_numpy(float)

        raw50 = (y >= rl50) & (y <= ru50)
        cqr50 = (y >= cl50) & (y <= cu50)
        raw80 = (y >= rl80) & (y <= ru80)
        cqr80 = (y >= cl80) & (y <= cu80)

        rows.append({
            "Dataset": dataset,
            "Material": series,
            "Horizon": int(horizon),
            "N": len(g),

            "Raw_50_Coverage": raw50.mean(),
            "CQR_50_Coverage": cqr50.mean(),
            "Raw_80_Coverage": raw80.mean(),
            "CQR_80_Coverage": cqr80.mean(),

            "Paired_Coverage_Gain_50":
                (cqr50.astype(int) - raw50.astype(int)).mean(),
            "Paired_Coverage_Gain_80":
                (cqr80.astype(int) - raw80.astype(int)).mean(),

            "Raw_50_Width": (ru50 - rl50).mean(),
            "CQR_50_Width": (cu50 - cl50).mean(),
            "Raw_80_Width": (ru80 - rl80).mean(),
            "CQR_80_Width": (cu80 - cl80).mean(),
        })

    return pd.DataFrame(rows)


def make_verdict(primary, agg):
    h3 = agg[
        (agg["Group"] == "ALL")
        & (agg["Horizon"] == PRIMARY_HORIZON)
    ].iloc[0]

    n = len(primary)
    n50 = int(primary["CQR_Improves_50_Calibration"].sum())
    n80 = int(primary["CQR_Improves_80_Calibration"].sum())
    nw = int(primary["CQR_Better_Winkler_80"].sum())

    raw50 = float(h3["Raw_Mean_Coverage_Error_50"])
    cqr50 = float(h3["CQR_Mean_Coverage_Error_50"])
    raw80 = float(h3["Raw_Mean_Coverage_Error_80"])
    cqr80 = float(h3["CQR_Mean_Coverage_Error_80"])
    dw50 = float(h3["Mean_Width_Change_50"])
    dw80 = float(h3["Mean_Width_Change_80"])
    dw = float(h3["Mean_Winkler_Change_80"])

    if n80 > n / 2 and cqr80 < raw80:
        calibration = "DESCRIPTIVE EVIDENCE FAVORS CQR"
    elif n80 < n / 2 and cqr80 > raw80:
        calibration = "DESCRIPTIVE EVIDENCE DOES NOT FAVOR CQR"
    else:
        calibration = "MIXED DESCRIPTIVE EVIDENCE"

    if dw < 0:
        winkler = "Mean Winkler-80 improves with CQR."
    elif dw > 0:
        winkler = "Mean Winkler-80 worsens with CQR."
    else:
        winkler = "Mean Winkler-80 is unchanged."

    return f"""CMIDO — RO1 STEP 26C.3-E
FROZEN CQR TEST-RESULT ANALYSIS

Status: COMPLETED
Test set: UNTOUCHED BEFORE FROZEN CQR APPLICATION
Primary horizon: h=3
Result type: DESCRIPTIVE ONLY

Series evaluated: {n}
Improved 50% calibration: {n50}/{n}
Improved 80% calibration: {n80}/{n}
Better Winkler-80: {nw}/{n}

Mean 50% coverage error
Raw: {raw50:.6f}
CQR: {cqr50:.6f}

Mean 80% coverage error
Raw: {raw80:.6f}
CQR: {cqr80:.6f}

Mean width change (CQR - Raw)
50%: {dw50:.6f}
80%: {dw80:.6f}

Mean Winkler-80 change (CQR - Raw)
{dw:.6f}

Calibration verdict:
{calibration}

Winkler verdict:
{winkler}

Scientific caution:
This analysis is descriptive and does not establish statistical significance
or overall model superiority. Frozen CQR parameters and forecasts were not
modified. The next inferential step should compare paired test losses and
the frozen conventional probabilistic statistical baselines.
"""


def main():
    print("=" * 78)
    print("CMIDO — STEP 26C.3-E")
    print("FROZEN CQR TEST-RESULT ANALYSIS")
    print("=" * 78)

    fc, mt = load_inputs()

    material = material_horizon_table(mt)
    primary = primary_h3_table(mt)
    agg = aggregate_table(material)
    paired = observation_level_paired(fc)
    verdict = make_verdict(primary, agg)

    material_path = OUT_DIR / "RO1_step26c3_material_horizon_comparison.csv"
    primary_path = OUT_DIR / "RO1_step26c3_primary_h3_comparison.csv"
    aggregate_path = OUT_DIR / "RO1_step26c3_aggregate_summary.csv"
    paired_path = OUT_DIR / "RO1_step26c3_observation_level_summary.csv"
    verdict_path = OUT_DIR / "RO1_step26c3_preliminary_verdict.txt"

    material.to_csv(material_path, index=False)
    primary.to_csv(primary_path, index=False)
    agg.to_csv(aggregate_path, index=False)
    paired.to_csv(paired_path, index=False)
    verdict_path.write_text(verdict, encoding="utf-8")

    print()
    print("-" * 78)
    print("PRIMARY h=3 COMPARISON")
    print("-" * 78)

    display_cols = [
        "Dataset",
        "Material",
        "Raw_50_Coverage",
        "CQR_50_Coverage",
        "Raw_80_Coverage",
        "CQR_80_Coverage",
        "Raw_80_Width",
        "CQR_80_Width",
        "Raw_Winkler_80",
        "CQR_Winkler_80",
    ]

    print(
        primary[display_cols].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )

    print()
    print("-" * 78)
    print("OVERALL h=3 SUMMARY")
    print("-" * 78)

    h3 = agg[
        (agg["Group"] == "ALL")
        & (agg["Horizon"] == PRIMARY_HORIZON)
    ].iloc[0]

    print(f"Raw mean 50% coverage error : {h3['Raw_Mean_Coverage_Error_50']:.6f}")
    print(f"CQR mean 50% coverage error : {h3['CQR_Mean_Coverage_Error_50']:.6f}")
    print(f"Raw mean 80% coverage error : {h3['Raw_Mean_Coverage_Error_80']:.6f}")
    print(f"CQR mean 80% coverage error : {h3['CQR_Mean_Coverage_Error_80']:.6f}")
    print(f"Mean 50% width change       : {h3['Mean_Width_Change_50']:.6f}")
    print(f"Mean 80% width change       : {h3['Mean_Width_Change_80']:.6f}")
    print(f"Mean Winkler-80 change      : {h3['Mean_Winkler_Change_80']:.6f}")

    print()
    print("-" * 78)
    print("DESCRIPTIVE VERDICT")
    print("-" * 78)
    print(verdict)

    print()
    print("-" * 78)
    print("SAVED OUTPUTS")
    print("-" * 78)

    for path in [
        material_path,
        primary_path,
        aggregate_path,
        paired_path,
        verdict_path,
    ]:
        print(path)

    print()
    print("=" * 78)
    print("ALL STEP 26C.3-E ASSERTIONS: PASS")
    print("=" * 78)


if __name__ == "__main__":
    main()
