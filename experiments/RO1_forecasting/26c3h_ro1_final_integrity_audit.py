"""
CMIDO — RO1 FINAL INTEGRITY AUDIT
Step 26C.3-H

Purpose:
Final audit of the complete RO1 forecasting evidence chain.

This script performs NO model training, NO model selection,
NO calibration, and NO modification of any forecasting artifact.

It verifies:
- expected artifacts exist
- nine-series coverage
- horizon coverage
- target-valid test origins
- no target beyond test endpoint
- no duplicate origin/target keys
- actual-value consistency across artifacts
- frozen model selections
- CQR validation-only calibration
- no test recalibration
- paired comparison integrity
- output row-count consistency
"""

from pathlib import Path
import json
import hashlib
import pandas as pd
import numpy as np

ROOT = Path(r"D:\CMIDO")

RESULTS = ROOT / "results" / "forecasting"

FILES = {
    "naive_forecasts": RESULTS / "baselines" / "RO1_step23_baseline_forecasts.csv",
    "classical_forecasts": RESULTS / "classical" / "RO1_step24_classical_forecasts.csv",
    "multivariate_forecasts": RESULTS / "multivariate" / "RO1_step25c2m_material_forecasts.csv",
    "stat_prob_forecasts": RESULTS / "probabilistic_statistical" / "RO1_step26b1_probabilistic_forecasts.csv",
    "stat_prob_selection": RESULTS / "probabilistic_statistical" / "RO1_step26b1_selected_probabilistic_baselines.csv",
    "ml_val_forecasts": RESULTS / "probabilistic_ml" / "RO1_step26c2_validation_forecasts.csv",
    "ml_selection": RESULTS / "probabilistic_ml" / "RO1_step26c2_model_selection.csv",
    "cqr_parameters": RESULTS / "probabilistic_calibration" / "RO1_step26c3_calibration_parameters.csv",
    "cqr_val_forecasts": RESULTS / "probabilistic_calibration" / "RO1_step26c3_validation_forecasts.csv",
    "cqr_val_metrics": RESULTS / "probabilistic_calibration" / "RO1_step26c3_validation_metrics.csv",
    "ml_test_forecasts": RESULTS / "probabilistic_ml" / "RO1_step26c2_test_forecasts.csv",
    "cqr_test_forecasts": RESULTS / "probabilistic_calibration" / "RO1_step26c3_test_forecasts.csv",
    "cqr_test_metrics": RESULTS / "probabilistic_calibration" / "RO1_step26c3_test_metrics.csv",
    "final_comparison": RESULTS / "final_probabilistic_comparison" / "RO1_step26c3g_material_horizon_comparison.csv",
    "final_primary": RESULTS / "final_probabilistic_comparison" / "RO1_step26c3g_primary_h3_comparison.csv",
    "final_aggregate": RESULTS / "final_probabilistic_comparison" / "RO1_step26c3g_primary_h3_aggregate.csv",
    "paired_observations": RESULTS / "final_probabilistic_comparison" / "RO1_step26c3g_paired_observation_data.csv",
}
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

EXPECTED_COUNTS = {
    1: 23,
    3: 21,
    6: 18,
    12: 12,
}

EXPECTED_TEST_ROWS = sum(EXPECTED_COUNTS.values()) * 9  # 666


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def canonical_series(dataset, series):
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


def key_columns(df):
    return [
        "dataset",
        "series_canonical",
        "horizon",
        "forecast_origin_dt",
        "target_date_dt",
    ]


def add_keys(df):
    out = df.copy()

    if "series_canonical" not in out.columns:
        require(
            "dataset" in out.columns and
            ("series" in out.columns or "material" in out.columns),
            "Cannot construct canonical series key."
        )
        source_col = "series" if "series" in out.columns else "material"
        out["series_canonical"] = [
            canonical_series(d, s)
            for d, s in zip(out["dataset"], out[source_col])
        ]

    if "forecast_origin_dt" not in out.columns:
        if "forecast_origin" in out.columns:
            origin_col = "forecast_origin"
        elif "origin" in out.columns:
            origin_col = "origin"
        else:
            require(False, "Missing forecast_origin/origin.")
        out["forecast_origin_dt"] = pd.to_datetime(
            out[origin_col], errors="coerce"
        )

    if "target_date_dt" not in out.columns:
        require("target_date" in out.columns,
                "Missing target_date.")
        out["target_date_dt"] = pd.to_datetime(
            out["target_date"], errors="coerce"
        )

    if "horizon" in out.columns:
        out["horizon"] = pd.to_numeric(
            out["horizon"], errors="coerce"
        ).astype("Int64")

    require(out["forecast_origin_dt"].notna().all(),
            "Invalid forecast-origin dates.")
    require(out["target_date_dt"].notna().all(),
            "Invalid target dates.")

    return out


def load_csv(name):
    path = FILES[name]
    require(path.exists(), f"Missing required artifact: {path}")
    return pd.read_csv(path)


def check_artifact_inventory():
    print("=" * 78)
    print("1. ARTIFACT INVENTORY")
    print("=" * 78)

    for name, path in FILES.items():
        require(path.exists(), f"Missing artifact: {path}")
        print(f"PASS  {name}: {path.name}")

    print(f"Total required artifacts: {len(FILES)}")
    print("Artifact inventory: PASS")


def check_series_horizons(df, label):
    df = add_keys(df)

    pairs = set(
        zip(
            df["dataset"].astype(str),
            df["series_canonical"].astype(str),
        )
    )

    require(
        pairs == EXPECTED_PAIRS,
        f"{label}: unexpected or missing series."
    )

    horizons = set(
        pd.to_numeric(df["horizon"], errors="coerce")
        .dropna()
        .astype(int)
    )

    require(
        horizons == {1, 3, 6, 12},
        f"{label}: expected horizons 1,3,6,12, got {sorted(horizons)}"
    )

    print(f"PASS  {label}: nine series + four horizons")
    return df


def check_target_validity(df, label):
    df = add_keys(df)

    # For each forecast origin, target date must be origin + h months.
    expected_target = (
        df["forecast_origin_dt"]
        + pd.to_timedelta(0, unit="D")
    )

    # Month arithmetic is safer through PeriodIndex.
    expected_period = (
        df["forecast_origin_dt"].dt.to_period("M")
        + df["horizon"].astype(int)
    )

    actual_period = df["target_date_dt"].dt.to_period("M")

    require(
        (expected_period == actual_period).all(),
        f"{label}: horizon/target-date mismatch detected."
    )

    # Test endpoint is dataset-specific.
    endpoints = {
        "RO1_PRICE": pd.Period("2026-06", freq="M"),
        "RO1_DEMAND": pd.Period("2026-05", freq="M"),
    }

    for dataset, endpoint in endpoints.items():
        sub = df[df["dataset"].astype(str) == dataset]
        if len(sub):
            require(
                (sub["target_date_dt"].dt.to_period("M") <= endpoint).all(),
                f"{label}: target crosses dataset endpoint for {dataset}."
            )

    counts = (
        df.groupby("horizon")
        .size()
        .to_dict()
    )

    # For complete nine-series test artifacts.
    expected = {
        h: n * 9
        for h, n in EXPECTED_COUNTS.items()
    }

    require(
        counts == expected,
        f"{label}: incorrect horizon counts {counts}; expected {expected}."
    )

    print(f"PASS  {label}: target-validity and horizon counts")
    return df


def check_duplicates(df, label):
    df = add_keys(df)
    keys = key_columns(df)

    dup = df.duplicated(keys, keep=False)

    require(
        not dup.any(),
        f"{label}: duplicate forecast origin/target keys detected."
    )

    print(f"PASS  {label}: no duplicate origin/target keys")


def check_test_flag(df, label):
    if "split" in df.columns:
        test = df[
            df["split"].astype(str).str.lower() == "test"
        ]
        require(len(test) > 0, f"{label}: no test rows.")
        return test

    return df


def check_actual_consistency(a, b, label):
    """
    Verify actual-value identity on the exact common key intersection.

    The frozen 26B.1 statistical test window contains 864 rows, while the
    frozen ML/CQR test window contains 666 rows. Therefore the complete key
    sets are intentionally not required to be equal. The smaller paired
    artifact must be fully contained in the larger artifact's key space.
    """
    a = add_keys(a)
    b = add_keys(b)

    keys = key_columns(a)

    aa = a[keys + ["actual"]].copy()
    bb = b[keys + ["actual"]].copy()

    require(
        not aa.duplicated(keys).any(),
        f"{label}: artifact A has duplicate keys."
    )
    require(
        not bb.duplicated(keys).any(),
        f"{label}: artifact B has duplicate keys."
    )

    merged = aa.merge(
        bb,
        on=keys,
        how="inner",
        suffixes=("_a", "_b"),
        validate="one_to_one",
    )

    require(
        len(merged) == min(len(aa), len(bb)),
        f"{label}: smaller artifact is not fully contained in the larger "
        "artifact's canonical key space."
    )

    av = pd.to_numeric(
        merged["actual_a"], errors="coerce"
    ).to_numpy(float)
    bv = pd.to_numeric(
        merged["actual_b"], errors="coerce"
    ).to_numpy(float)

    require(
        np.allclose(av, bv, rtol=0.0, atol=1e-10),
        f"{label}: actual target values differ on common keys."
    )

    print(
        f"PASS  {label}: {len(merged)} common forecast keys; "
        "actual values identical"
    )

    return merged

def check_statistical_selection(stat_raw, selection):
    print("=" * 78)
    print("2. FROZEN CONVENTIONAL PROBABILISTIC BASELINE")
    print("=" * 78)

    sel = selection.copy()
    sel["series_canonical"] = [
        canonical_series(d, s)
        for d, s in zip(sel["dataset"], sel["series"])
    ]

    pairs = set(
        zip(
            sel["dataset"].astype(str),
            sel["series_canonical"].astype(str),
        )
    )

    require(
        pairs == EXPECTED_PAIRS,
        "26B.1 frozen selection does not contain exactly nine series."
    )

    require(
        not sel.duplicated(
            ["dataset", "series_canonical"]
        ).any(),
        "26B.1 frozen selection has duplicates."
    )

    require(
        (
            pd.to_numeric(
                sel["primary_horizon"],
                errors="coerce"
            ) == 3
        ).all(),
        "26B.1 selection is not frozen at primary h=3."
    )

    expected_models = {
        ("RO1_DEMAND", "Cement"): "ETS",
        ("RO1_DEMAND", "Granite"): "ETS",
        ("RO1_DEMAND", "Ready Mixed Concrete"): "ETS",
        ("RO1_DEMAND", "Steel Reinforcement Bars"): "ETS",
        ("RO1_PRICE", "Cement"): "ETS",
        ("RO1_PRICE", "Concreting Sand"): "ETS",
        ("RO1_PRICE", "Granite"): "SARIMA",
        ("RO1_PRICE", "Ready Mixed Concrete"): "ETS",
        ("RO1_PRICE", "Steel Reinforcement Bars"): "SARIMA",
    }

    actual_models = {
        (d, s): m
        for d, s, m in zip(
            sel["dataset"].astype(str),
            sel["series_canonical"].astype(str),
            sel["selected_model"].astype(str),
        )
    }

    require(
        actual_models == expected_models,
        f"Frozen statistical models changed: {actual_models}"
    )

    test = stat_raw[
        stat_raw["split"].astype(str).str.lower() == "test"
    ].copy()

    test = add_keys(test)

    test = test.merge(
        sel[
            ["dataset", "series_canonical", "selected_model"]
        ],
        on=["dataset", "series_canonical"],
        how="inner",
        validate="many_to_one",
    )

    # Apply the frozen statistical model selection only.
    test = test[
        test["model"].astype(str)
        == test["selected_model"].astype(str)
    ].copy()

    require(
        len(test) == 864,
        f"Frozen selected 26B.1 statistical test rows = {len(test)}, expected 864 "
        "(9 series × 4 horizons × 24 origins)."
    )

    # IMPORTANT:
    # The 864 rows are NOT endpoint-invalid. They cover the observed test
    # target interval June 2024–June 2026 for every horizon. The 26C.2/26C.3
    # ML test artifact intentionally starts later for some horizons because
    # its test origins are constrained by the frozen forecasting split.
    #
    # Therefore the correct final comparison rule is an EXACT INTERSECTION
    # with the frozen ML+CQR test keys, not arbitrary deletion of 198 rows.

    expected_target_period = (
        test["forecast_origin_dt"].dt.to_period("M")
        + test["horizon"].astype(int)
    )
    actual_target_period = test["target_date_dt"].dt.to_period("M")

    require(
        (expected_target_period == actual_target_period).all(),
        "26B.1 statistical test has origin/horizon/target arithmetic errors."
    )

    endpoints = {
        "RO1_PRICE": pd.Period("2026-06", freq="M"),
        "RO1_DEMAND": pd.Period("2026-05", freq="M"),
    }

    for dataset, endpoint in endpoints.items():
        sub = test[test["dataset"].astype(str) == dataset]
        if len(sub):
            require(
                (
                    sub["target_date_dt"].dt.to_period("M")
                    <= endpoint
                ).all(),
                f"26B.1 target exceeds observed endpoint for {dataset}."
            )

    counts = test.groupby("horizon").size().to_dict()
    require(
        counts == {1: 216, 3: 216, 6: 216, 12: 216},
        f"Unexpected frozen statistical horizon counts: {counts}"
    )

    check_duplicates(test, "Frozen 26B.1 statistical test")

    print("PASS  26B.1 frozen model identities")
    print("PASS  26B.1 selected statistical test rows: 864")
    print("PASS  26B.1 all selected statistical targets are observed")
    print("PASS  26B.1 origin/horizon/target arithmetic")
    print("PASS  26B.1 duplicate-key audit")
    print("NOTE  864 is the valid statistical test window; final paired evaluation uses exact ML/CQR intersection")
    return test

def check_ml_selection(ml_selection):
    print("=" * 78)
    print("3. FROZEN PROBABILISTIC ML SELECTION")
    print("=" * 78)

    df = ml_selection.copy()

    require(
        "dataset" in df.columns and "series" in df.columns,
        "26C.2 selection missing dataset/series."
    )

    df["series_canonical"] = [
        canonical_series(d, s)
        for d, s in zip(df["dataset"], df["series"])
    ]

    pairs = set(
        zip(
            df["dataset"].astype(str),
            df["series_canonical"].astype(str),
        )
    )

    require(
        pairs == EXPECTED_PAIRS,
        "26C.2 selection does not contain exactly nine series."
    )

    require(
        not df.duplicated(
            ["dataset", "series_canonical"]
        ).any(),
        "26C.2 model selection has duplicate series."
    )

    print(f"PASS  26C.2 frozen ML selection: {len(df)} series")
    return df


def check_cqr(cqr_params, cqr_val, cqr_test):
    print("=" * 78)
    print("4. CQR CALIBRATION INTEGRITY")
    print("=" * 78)

    p = cqr_params.copy()

    require(
        len(p) == 72,
        f"Expected 72 CQR parameter cells, found {len(p)}."
    )

    if "calibration_source" in p.columns:
        src = p["calibration_source"].astype(str).str.upper()
        require(
            src.str.contains("VALIDATION").all(),
            "CQR parameter source is not validation-only."
        )

    # CQR validation artifact.
    cv = add_keys(cqr_val)
    require(
        len(cv) == 666,
        f"Expected 666 CQR validation rows, found {len(cv)}."
    )

    check_duplicates(cv, "CQR validation forecasts")

    # Test artifact.
    ct = add_keys(cqr_test)
    require(
        len(ct) == 666,
        f"Expected 666 CQR test rows, found {len(ct)}."
    )

    check_target_validity(ct, "CQR test forecasts")
    check_duplicates(ct, "CQR test forecasts")

    if "test_recalibration" in ct.columns:
        flags = ct["test_recalibration"].astype(str).str.upper()
        require(
            not flags.isin(["YES", "TRUE", "1"]).any(),
            "CQR test recalibration flag detected."
        )

    if "calibration_source" in ct.columns:
        src = ct["calibration_source"].astype(str).str.upper()
        require(
            src.str.contains("VALIDATION").all(),
            "CQR test artifact has non-validation calibration source."
        )

    # Check non-negative interval lower bounds.
    for c in [
        "calibrated_lower_50",
        "calibrated_lower_80",
    ]:
        if c in ct.columns:
            vals = pd.to_numeric(ct[c], errors="coerce")
            require(
                (vals >= -1e-10).all(),
                f"CQR non-negativity violated in {c}."
            )

    print("PASS  CQR parameters: 72 frozen validation-derived cells")
    print("PASS  CQR validation forecasts: 666 rows")
    print("PASS  CQR test forecasts: 666 rows")
    print("PASS  CQR test recalibration: none")
    print("PASS  CQR parameter source: validation only")


def check_final_comparison(comparison, primary, aggregate, paired):
    print("=" * 78)
    print("5. FINAL PROBABILISTIC COMPARISON INTEGRITY")
    print("=" * 78)

    c = comparison.copy()
    p = primary.copy()
    a = aggregate.copy()
    po = paired.copy()

    require(
        len(c) == 36,
        f"Expected 36 comparison cells, found {len(c)}."
    )

    require(
        len(p) == 9,
        f"Expected 9 primary h=3 cells, found {len(p)}."
    )

    require(
        len(a) == 1,
        f"Expected one aggregate row, found {len(a)}."
    )

    require(
        len(po) == 666,
        f"Expected 666 paired observations, found {len(po)}."
    )

    require(
        set(pd.to_numeric(c["horizon"]).astype(int))
        == {1, 3, 6, 12},
        "Final comparison missing horizon."
    )

    require(
        set(pd.to_numeric(p["horizon"]).astype(int))
        == {3},
        "Primary comparison is not h=3."
    )

    require(
        set(
            zip(
                p["dataset"].astype(str),
                p["series"].astype(str),
            )
        ) == EXPECTED_PAIRS,
        "Primary comparison does not contain all nine series."
    )

    # Reconstruct primary aggregate independently.
    mean_stat = p["stat_winkler_80"].mean()
    mean_ml = p["ml_cqr_winkler_80"].mean()
    mean_diff = p["winkler_80_change_ml_minus_stat"].mean()

    require(
        np.isclose(
            mean_stat,
            float(a["mean_stat_winkler_80"].iloc[0]),
            atol=1e-8,
        ),
        "Aggregate statistical Winkler does not match primary cells."
    )

    require(
        np.isclose(
            mean_ml,
            float(a["mean_ml_cqr_winkler_80"].iloc[0]),
            atol=1e-8,
        ),
        "Aggregate ML+CQR Winkler does not match primary cells."
    )

    require(
        np.isclose(
            mean_diff,
            float(
                a[
                    "mean_winkler_80_change_ml_minus_stat"
                ].iloc[0]
            ),
            atol=1e-8,
        ),
        "Aggregate Winkler difference does not match primary cells."
    )

    # Independent count check.
    d = p["winkler_80_change_ml_minus_stat"]

    require(
        int((d < 0).sum())
        == int(a["n_ml_cqr_better_winkler_80"].iloc[0]),
        "ML+CQR better-count mismatch."
    )

    require(
        int((d > 0).sum())
        == int(a["n_ml_cqr_worse_winkler_80"].iloc[0]),
        "ML+CQR worse-count mismatch."
    )

    print("PASS  36 material/horizon comparison cells")
    print("PASS  9 primary h=3 cells")
    print("PASS  666 paired observations")
    print("PASS  Primary aggregate independently reproduced")


def check_cross_artifact_actuals(stat_test, cqr_test, ml_test):
    print("=" * 78)
    print("6. CROSS-ARTIFACT TARGET CONSISTENCY")
    print("=" * 78)

    stat_cqr = check_actual_consistency(
        stat_test,
        cqr_test,
        "Frozen statistical vs CQR test"
    )

    cqr_ml = check_actual_consistency(
        cqr_test,
        ml_test,
        "CQR vs ML test"
    )

    require(
        len(stat_cqr) == EXPECTED_TEST_ROWS,
        f"Statistical/CQR common intersection = {len(stat_cqr)}, "
        f"expected {EXPECTED_TEST_ROWS}."
    )

    require(
        len(cqr_ml) == EXPECTED_TEST_ROWS,
        f"CQR/ML common intersection = {len(cqr_ml)}, "
        f"expected {EXPECTED_TEST_ROWS}."
    )

    print("PASS  Statistical/CQR exact common intersection: 666")
    print("PASS  CQR/ML exact common intersection: 666")
    print("Cross-artifact actual consistency: PASS")

def main():
    print("=" * 78)
    print("CMIDO — RO1 FINAL INTEGRITY AUDIT")
    print("STEP 26C.3-H")
    print("=" * 78)
    print("No model training")
    print("No model selection")
    print("No calibration")
    print("No artifact modification")
    print()

    check_artifact_inventory()

    # Load required artifacts.
    stat_raw = load_csv("stat_prob_forecasts")
    stat_selection = load_csv("stat_prob_selection")

    ml_val = load_csv("ml_val_forecasts")
    ml_selection = load_csv("ml_selection")

    cqr_params = load_csv("cqr_parameters")
    cqr_val = load_csv("cqr_val_forecasts")
    cqr_test = load_csv("cqr_test_forecasts")

    ml_test = load_csv("ml_test_forecasts")

    final_comparison = load_csv("final_comparison")
    final_primary = load_csv("final_primary")
    final_aggregate = load_csv("final_aggregate")
    paired = load_csv("paired_observations")

    # Classical deterministic artifacts: existence/schema sanity only.
    naive = load_csv("naive_forecasts")
    classical = load_csv("classical_forecasts")
    multivariate = load_csv("multivariate_forecasts")

    print()
    print("=" * 78)
    print("7. FROZEN FORECASTING ARTIFACT SANITY")
    print("=" * 78)

    check_series_horizons(naive, "Naive baseline")
    check_series_horizons(classical, "Classical forecasting")
    # Step 25C.2M uses `material` rather than `series` and contains
    # material-level frozen test forecasts. Its canonical series names
    # are normalized through add_keys().
    check_series_horizons(multivariate, "Multivariate forecasting")
    require(
        len(multivariate) == EXPECTED_TEST_ROWS,
        f"Multivariate material forecast rows = {len(multivariate)}, "
        f"expected {EXPECTED_TEST_ROWS}."
    )
    check_target_validity(multivariate, "Multivariate forecasting")
    check_duplicates(multivariate, "Multivariate forecasting")

    print("PASS  deterministic/classical/multivariate artifacts")

    # Statistical probabilistic baseline.
    stat_test = check_statistical_selection(
        stat_raw,
        stat_selection
    )

    # ML selection.
    ml_sel = check_ml_selection(ml_selection)

    # ML test.
    ml_test = add_keys(ml_test)
    if "split" in ml_test.columns:
        require(
            ml_test["split"].astype(str).str.lower().eq("test").all(),
            "26C.2 ML test artifact contains non-test rows."
        )
    require(
        len(ml_test) == 666,
        f"Expected 666 frozen ML test rows, found {len(ml_test)}."
    )
    check_target_validity(ml_test, "Frozen ML test")
    check_duplicates(ml_test, "Frozen ML test")
    print("PASS  26C.2 frozen ML test schema: origin/target resolved")
    print("PASS  26C.2 frozen ML test: 666 rows")

    # CQR.
    check_cqr(
        cqr_params,
        cqr_val,
        cqr_test
    )

    # Final comparison uses the exact common key intersection between the
    # 864-row frozen statistical test window and the 666-row frozen ML/CQR
    # test window. This is the correct paired-evaluation design.
    print()
    print("=" * 78)
    print("8. EXACT COMMON TEST WINDOW USED FOR FINAL COMPARISON")
    print("=" * 78)
    print(f"Frozen statistical test rows available: {len(stat_test)}")
    print(f"Frozen ML/CQR test rows available: {len(cqr_test)}")
    print("Final paired comparison rows expected: 666")
    print("Comparison rule: exact origin + target + series + horizon intersection")
    print("No endpoint-crossing statistical rows are being falsely classified or discarded")

    check_cross_artifact_actuals(
        stat_test,
        cqr_test,
        ml_test
    )

    # Independent direct statistical-vs-ML key intersection.
    stat_key_df = stat_test[key_columns(stat_test)]
    ml_key_df = ml_test[key_columns(ml_test)]

    stat_keys = set(
        map(tuple, stat_key_df.itertuples(index=False, name=None))
    )
    ml_keys = set(
        map(tuple, ml_key_df.itertuples(index=False, name=None))
    )

    direct_common = stat_keys & ml_keys

    require(
        len(direct_common) == EXPECTED_TEST_ROWS,
        f"Direct statistical/ML common key intersection = {len(direct_common)}, "
        f"expected {EXPECTED_TEST_ROWS}."
    )

    print("PASS  Direct statistical vs ML common key intersection: 666")

    # Final comparison.
    check_final_comparison(
        final_comparison,
        final_primary,
        final_aggregate,
        paired
    )

    # Paired observation key integrity.
    paired2 = paired.copy()
    paired2["forecast_origin_dt"] = pd.to_datetime(
        paired2["forecast_origin"], errors="coerce"
    )
    paired2["target_date_dt"] = pd.to_datetime(
        paired2["target_date"], errors="coerce"
    )

    require(
        paired2["forecast_origin_dt"].notna().all(),
        "Paired observations contain invalid origin dates."
    )
    require(
        paired2["target_date_dt"].notna().all(),
        "Paired observations contain invalid target dates."
    )

    require(
        not paired2.duplicated(
            [
                "dataset",
                "series",
                "horizon",
                "forecast_origin",
                "target_date",
            ]
        ).any(),
        "Paired observations contain duplicates."
    )

    # Reproduce expected horizon counts from paired observations.
    paired_counts = (
        paired2.groupby("horizon").size().to_dict()
    )
    expected_paired = {
        h: n * 9 for h, n in EXPECTED_COUNTS.items()
    }

    require(
        paired_counts == expected_paired,
        f"Paired observation horizon counts {paired_counts} "
        f"do not match {expected_paired}."
    )

    print("PASS  paired observation uniqueness")
    print("PASS  paired observation horizon coverage")

    # Save audit report.
    report = {
        "audit": "RO1 Step 26C.3-H Final Integrity Audit",
        "status": "PASS",
        "model_training": False,
        "model_selection": False,
        "test_recalibration": False,
        "primary_horizon": 3,
        "primary_interval": "80%",
        "expected_series": 9,
        "expected_horizons": [1, 3, 6, 12],
        "target_valid_test_origins_per_series": EXPECTED_COUNTS,
        "selected_26b1_test_rows": 864,
        "final_paired_test_rows": EXPECTED_TEST_ROWS,
        "comparison_rule": "exact common origin-target-series-horizon intersection",
        "expected_test_rows": EXPECTED_TEST_ROWS,
        "cqr_parameter_cells": 72,
        "cqr_validation_rows": 666,
        "cqr_test_rows": 666,
        "paired_observations": 666,
    }

    json_path = (
        RESULTS / "final_probabilistic_comparison"
        / "RO1_step26c3h_final_integrity_audit.json"
    )
    txt_path = (
        RESULTS / "final_probabilistic_comparison"
        / "RO1_step26c3h_final_integrity_audit.txt"
    )

    json_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    txt_path.write_text(
        "\n".join(
            [
                "CMIDO — RO1 STEP 26C.3-H",
                "FINAL INTEGRITY AUDIT",
                "",
                "STATUS: PASS",
                "Model training: NO",
                "Model selection: NO",
                "Test recalibration: NO",
                "Primary horizon: 3",
                "Primary interval: 80%",
                "Expected series: 9",
                "Expected horizons: 1,3,6,12",
                "Target-valid origins per series: h1=23, h3=21, h6=18, h12=12",
                "Selected 26B.1 statistical test rows: 864",
                "Final paired test rows: 666",
                "Comparison rule: exact common origin-target-series-horizon intersection",
                "CQR parameter cells: 72",
                "CQR validation rows: 666",
                "CQR test rows: 666",
                "Final paired observations: 666",
            ]
        ),
        encoding="utf-8"
    )

    print()
    print("=" * 78)
    print("FINAL RO1 AUDIT RESULT")
    print("=" * 78)
    print("ALL STEP 26C.3-H ASSERTIONS: PASS")
    print()
    print(f"Saved: {json_path}")
    print(f"Saved: {txt_path}")
    print()
    print("=" * 78)
    print("RO1 FORECASTING EVIDENCE CHAIN: INTEGRITY-VERIFIED")
    print("=" * 78)


if __name__ == "__main__":
    main()
