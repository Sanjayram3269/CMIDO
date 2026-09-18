"""
CMIDO — RO1 STEP 25C.3
Paired Forecast-Error Statistical Comparison

Purpose
-------
Statistically compare frozen multivariate forecasts against
univariate benchmark forecasts using paired rolling-origin errors.

Price:
    VECM vs Naive / SeasonalNaive / ETS / SARIMA

Demand:
    VAR_DIFF vs Naive / SeasonalNaive / ETS / SARIMA

Primary horizon:
    h = 3

Secondary horizons:
    h = 1, 6, 12

IMPORTANT
---------
This script does NOT:
- refit any forecasting model
- tune any model
- select any model
- use test results to alter specifications

It only compares already-generated test forecasts.

The paired unit is:

    dataset × material × horizon × forecast_origin

The statistical comparison uses absolute-error loss.
A positive loss difference means the multivariate model
has larger error than the benchmark.

Diebold-Mariano-style comparison
---------------------------------
Because forecasts are serially dependent across rolling origins,
the test uses a HAC/Newey-West variance estimate.

For multi-step forecasts, the default HAC lag is h-1.

Interpretation
--------------
loss_diff = multivariate_loss - benchmark_loss

loss_diff > 0:
    multivariate model worse

loss_diff < 0:
    multivariate model better

p < 0.05:
    statistically significant difference
"""


from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


# ============================================================================
# PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

MULTI_FORECASTS = (
    ROOT
    / "results"
    / "forecasting"
    / "multivariate"
    / "RO1_step25c2m_material_forecasts.csv"
)

BASELINE_FORECASTS = (
    ROOT
    / "results"
    / "forecasting"
    / "baselines"
    / "RO1_step23_baseline_forecasts.csv"
)

CLASSICAL_FORECASTS = (
    ROOT
    / "results"
    / "forecasting"
    / "classical"
    / "RO1_step24_classical_forecasts.csv"
)

OUTPUT_DIR = (
    ROOT
    / "results"
    / "forecasting"
    / "multivariate"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

HORIZONS = [
    1,
    3,
    6,
    12,
]

PRIMARY_HORIZON = 3

UNIVARIATE_MODELS = {
    "Naive",
    "SeasonalNaive",
    "ETS",
    "SARIMA",
}

MULTIVARIATE_MODELS = {
    "RO1_PRICE": "VECM",
    "RO1_DEMAND": "VAR_DIFF",
}


# ============================================================================
# HEADER
# ============================================================================

print("=" * 78)
print("CMIDO RO1 — STEP 25C.3")
print("PAIRED FORECAST-ERROR STATISTICAL COMPARISON")
print("=" * 78)


# ============================================================================
# HELPERS
# ============================================================================

def detect_column(
    df,
    candidates,
    description,
):

    for candidate in candidates:

        if candidate in df.columns:

            return candidate

    raise RuntimeError(
        f"Could not identify {description}.\n"
        f"Available columns:\n{list(df.columns)}"
    )


def normalize_material(
    value,
):

    text = str(value).strip()

    mapping = {
        "Cement In Bulk (Ordinary Portland Cement)":
            "Cement",

        "Steel Reinforcement Bars (16-32mm High Tensile)":
            "Steel Reinforcement Bars",

        "Granite (20mm Aggregate)":
            "Granite",

        "Ready Mixed Concrete":
            "Ready-Mixed Concrete",

        "Ready-Mixed Concrete":
            "Ready-Mixed Concrete",

        "Concreting Sand":
            "Concreting Sand",

        "Cement":
            "Cement",

        "Steel Reinforcement Bars":
            "Steel Reinforcement Bars",

        "Granite":
            "Granite",
    }

    return mapping.get(
        text,
        text,
    )


# ============================================================================
# LOAD MULTIVARIATE FORECASTS
# ============================================================================

print(
    "\n[1] LOADING MULTIVARIATE FORECASTS"
)

if not MULTI_FORECASTS.exists():

    raise FileNotFoundError(
        f"Missing material-level multivariate forecasts:\n"
        f"{MULTI_FORECASTS}"
    )


multi = pd.read_csv(
    MULTI_FORECASTS
)

print(
    f"Rows: {len(multi)}"
)

print(
    f"Columns: {list(multi.columns)}"
)


# ============================================================================
# STANDARDIZE MULTIVARIATE
# ============================================================================

multi_material = detect_column(
    multi,
    [
        "material",
        "series",
        "DataSeries",
    ],
    "multivariate material column",
)

multi_actual = detect_column(
    multi,
    [
        "actual",
        "observed",
        "y_actual",
    ],
    "multivariate actual column",
)

multi_prediction = detect_column(
    multi,
    [
        "prediction",
        "predicted",
        "forecast",
        "y_pred",
    ],
    "multivariate prediction column",
)


multi = multi.rename(
    columns={
        multi_material:
            "material",

        multi_actual:
            "actual",

        multi_prediction:
            "prediction",
    }
)


required_multi = {
    "dataset",
    "model",
    "forecast_origin",
    "target_date",
    "horizon",
    "material",
    "actual",
    "prediction",
}


missing = (
    required_multi
    -
    set(multi.columns)
)

if missing:

    raise RuntimeError(
        "Multivariate forecast contract failure. "
        f"Missing: {sorted(missing)}"
    )


multi["material"] = (
    multi["material"]
    .map(
        normalize_material
    )
)

multi["forecast_origin"] = pd.to_datetime(
    multi["forecast_origin"]
)

multi["target_date"] = pd.to_datetime(
    multi["target_date"]
)

multi["horizon"] = (
    pd.to_numeric(
        multi["horizon"]
    )
    .astype(int)
)

multi["actual"] = pd.to_numeric(
    multi["actual"],
    errors="raise",
)

multi["prediction"] = pd.to_numeric(
    multi["prediction"],
    errors="raise",
)


multi["absolute_error"] = (
    np.abs(
        multi["prediction"]
        -
        multi["actual"]
    )
)


# ============================================================================
# LOAD STEP 23
# ============================================================================

print(
    "\n[2] LOADING STEP 23 FORECASTS"
)

if not BASELINE_FORECASTS.exists():

    raise FileNotFoundError(
        f"Missing Step 23 forecasts:\n"
        f"{BASELINE_FORECASTS}"
    )


baseline = pd.read_csv(
    BASELINE_FORECASTS
)

print(
    f"Rows: {len(baseline)}"
)

print(
    f"Columns: {list(baseline.columns)}"
)


# ============================================================================
# STANDARDIZE BASELINE
# ============================================================================

baseline_material = detect_column(
    baseline,
    [
        "material",
        "series",
        "DataSeries",
    ],
    "baseline material column",
)

baseline_actual = detect_column(
    baseline,
    [
        "actual",
        "observed",
        "y_actual",
    ],
    "baseline actual column",
)

baseline_prediction = detect_column(
    baseline,
    [
        "prediction",
        "predicted",
        "forecast",
        "y_pred",
    ],
    "baseline prediction column",
)


baseline = baseline.rename(
    columns={
        baseline_material:
            "material",

        baseline_actual:
            "actual",

        baseline_prediction:
            "prediction",
    }
)


required_baseline = {
    "dataset",
    "model",
    "forecast_origin",
    "target_date",
    "horizon",
    "material",
    "actual",
    "prediction",
}


missing = (
    required_baseline
    -
    set(baseline.columns)
)

if missing:

    raise RuntimeError(
        "Step 23 forecast contract failure. "
        f"Missing: {sorted(missing)}"
    )


baseline["material"] = (
    baseline["material"]
    .map(
        normalize_material
    )
)

baseline["forecast_origin"] = pd.to_datetime(
    baseline["forecast_origin"]
)

baseline["target_date"] = pd.to_datetime(
    baseline["target_date"]
)

baseline["horizon"] = (
    pd.to_numeric(
        baseline["horizon"]
    )
    .astype(int)
)

baseline["actual"] = pd.to_numeric(
    baseline["actual"],
    errors="raise",
)

baseline["prediction"] = pd.to_numeric(
    baseline["prediction"],
    errors="raise",
)

baseline["absolute_error"] = (
    np.abs(
        baseline["prediction"]
        -
        baseline["actual"]
    )
)


# ============================================================================
# LOAD STEP 24
# ============================================================================

print(
    "\n[3] LOADING STEP 24 FORECASTS"
)

if not CLASSICAL_FORECASTS.exists():

    raise FileNotFoundError(
        f"Missing Step 24 forecasts:\n"
        f"{CLASSICAL_FORECASTS}"
    )


classical = pd.read_csv(
    CLASSICAL_FORECASTS
)

print(
    f"Rows: {len(classical)}"
)

print(
    f"Columns: {list(classical.columns)}"
)


# ============================================================================
# STANDARDIZE CLASSICAL
# ============================================================================

classical_material = detect_column(
    classical,
    [
        "material",
        "series",
        "DataSeries",
    ],
    "classical material column",
)

classical_actual = detect_column(
    classical,
    [
        "actual",
        "observed",
        "y_actual",
    ],
    "classical actual column",
)

classical_prediction = detect_column(
    classical,
    [
        "prediction",
        "predicted",
        "forecast",
        "y_pred",
    ],
    "classical prediction column",
)


classical = classical.rename(
    columns={
        classical_material:
            "material",

        classical_actual:
            "actual",

        classical_prediction:
            "prediction",
    }
)


required_classical = {
    "dataset",
    "model",
    "forecast_origin",
    "target_date",
    "horizon",
    "material",
    "actual",
    "prediction",
}


missing = (
    required_classical
    -
    set(classical.columns)
)

if missing:

    raise RuntimeError(
        "Step 24 forecast contract failure. "
        f"Missing: {sorted(missing)}"
    )


classical["material"] = (
    classical["material"]
    .map(
        normalize_material
    )
)

classical["forecast_origin"] = pd.to_datetime(
    classical["forecast_origin"]
)

classical["target_date"] = pd.to_datetime(
    classical["target_date"]
)

classical["horizon"] = (
    pd.to_numeric(
        classical["horizon"]
    )
    .astype(int)
)

classical["actual"] = pd.to_numeric(
    classical["actual"],
    errors="raise",
)

classical["prediction"] = pd.to_numeric(
    classical["prediction"],
    errors="raise",
)

classical["absolute_error"] = (
    np.abs(
        classical["prediction"]
        -
        classical["actual"]
    )
)


# ============================================================================
# COMBINE UNIVARIATE FORECASTS
# ============================================================================

print(
    "\n[4] COMBINING UNIVARIATE FORECASTS"
)

univariate = pd.concat(
    [
        baseline[
            [
                "dataset",
                "model",
                "material",
                "forecast_origin",
                "target_date",
                "horizon",
                "actual",
                "prediction",
                "absolute_error",
            ]
        ],

        classical[
            [
                "dataset",
                "model",
                "material",
                "forecast_origin",
                "target_date",
                "horizon",
                "actual",
                "prediction",
                "absolute_error",
            ]
        ],
    ],
    ignore_index=True,
)


print(
    "Univariate models:"
)

print(
    sorted(
        univariate[
            "model"
        ]
        .unique()
    )
)


assert (
    set(
        univariate[
            "model"
        ]
        .unique()
    )
    ==
    UNIVARIATE_MODELS
)


# ============================================================================
# DATA CONTRACT CHECKS
# ============================================================================

print(
    "\n[5] FORECAST CONTRACT AUDIT"
)


def audit_forecasts(
    df,
    name,
):

    assert df["forecast_origin"].notna().all()
    assert df["target_date"].notna().all()

    assert (
        df["target_date"]
        >
        df["forecast_origin"]
    ).all()

    assert (
        df["horizon"]
        .isin(HORIZONS)
        .all()
    )

    assert (
        np.isfinite(
            df["actual"]
        )
        .all()
    )

    assert (
        np.isfinite(
            df["prediction"]
        )
        .all()
    )

    print(
        f"{name}: PASS"
    )


audit_forecasts(
    multi,
    "Multivariate",
)

audit_forecasts(
    univariate,
    "Univariate",
)


# ============================================================================
# PREPARE COMPARISON
# ============================================================================

print(
    "\n[6] BUILDING PAIRED COMPARISONS"
)


pair_key = [
    "dataset",
    "material",
    "forecast_origin",
    "target_date",
    "horizon",
]


def prepare_pairs(
    dataset,
    multi_model,
):

    multi_subset = multi.loc[
        (
            multi["dataset"]
            ==
            dataset
        )
        &
        (
            multi["model"]
            ==
            multi_model
        )
    ].copy()


    uni_subset = univariate.loc[
        univariate["dataset"]
        ==
        dataset
    ].copy()


    if multi_subset.empty:

        raise RuntimeError(
            f"No multivariate forecasts for {dataset}."
        )


    if uni_subset.empty:

        raise RuntimeError(
            f"No univariate forecasts for {dataset}."
        )


    results = []


    for baseline_model in sorted(
        UNIVARIATE_MODELS
    ):

        baseline_subset = uni_subset.loc[
            uni_subset["model"]
            ==
            baseline_model
        ].copy()


        merged = multi_subset.merge(
            baseline_subset,
            on=pair_key,
            suffixes=(
                "_multi",
                "_base",
            ),
            how="inner",
            validate="one_to_one",
        )


        if merged.empty:

            raise RuntimeError(
                f"No paired forecasts for "
                f"{dataset} / "
                f"{multi_model} vs "
                f"{baseline_model}"
            )


        # Ensure actual values agree exactly
        # between the two forecast sources.
        actual_difference = (
            merged["actual_multi"]
            -
            merged["actual_base"]
        )


        if not np.allclose(
            actual_difference,
            0.0,
            atol=1e-10,
            rtol=0,
        ):

            raise RuntimeError(
                f"Actual target mismatch detected "
                f"for {dataset}, "
                f"{baseline_model}."
            )


        merged[
            "multivariate_loss"
        ] = merged[
            "absolute_error_multi"
        ]

        merged[
            "baseline_loss"
        ] = merged[
            "absolute_error_base"
        ]


        merged[
            "loss_difference"
        ] = (
            merged[
                "multivariate_loss"
            ]
            -
            merged[
                "baseline_loss"
            ]
        )


        merged[
            "baseline_model"
        ] = baseline_model

        merged[
            "multivariate_model"
        ] = multi_model


        results.append(
            merged[
                [
                    "dataset",
                    "material",
                    "forecast_origin",
                    "target_date",
                    "horizon",
                    "multivariate_model",
                    "baseline_model",
                    "actual_multi",
                    "prediction_multi",
                    "actual_base",
                    "prediction_base",
                    "multivariate_loss",
                    "baseline_loss",
                    "loss_difference",
                ]
            ]
        )


    return pd.concat(
        results,
        ignore_index=True,
    )


price_pairs = prepare_pairs(
    "RO1_PRICE",
    "VECM",
)

demand_pairs = prepare_pairs(
    "RO1_DEMAND",
    "VAR_DIFF",
)


pairs = pd.concat(
    [
        price_pairs,
        demand_pairs,
    ],
    ignore_index=True,
)


print(
    f"Total paired forecast records: "
    f"{len(pairs)}"
)


# ============================================================================
# PAIRING AUDIT
# ============================================================================

print(
    "\n[7] PAIRING AUDIT"
)


assert (
    pairs["loss_difference"]
    .notna()
    .all()
)


assert (
    np.isfinite(
        pairs["loss_difference"]
    )
    .all()
)


duplicate_pair_count = (
    pairs
    .duplicated(
        subset=[
            "dataset",
            "material",
            "forecast_origin",
            "target_date",
            "horizon",
            "baseline_model",
        ]
    )
    .sum()
)


print(
    f"Duplicate paired records: "
    f"{duplicate_pair_count}"
)


assert duplicate_pair_count == 0


# ============================================================================
# HAC VARIANCE
# ============================================================================

def hac_variance_mean(
    values,
    max_lag,
):

    """
    Newey-West / HAC variance estimator for the sample mean.

    Returns:
        variance of sample mean
    """

    x = np.asarray(
        values,
        dtype=float,
    )

    n = len(x)

    if n < 2:

        return np.nan


    x_centered = (
        x
        -
        np.mean(x)
    )


    gamma0 = (
        np.sum(
            x_centered ** 2
        )
        /
        n
    )


    long_run = gamma0


    max_lag = min(
        int(max_lag),
        n - 1,
    )


    for lag in range(
        1,
        max_lag + 1,
    ):

        weight = (
            1
            -
            lag
            /
            (
                max_lag + 1
            )
        )


        covariance = (
            np.sum(
                x_centered[
                    lag:
                ]
                *
                x_centered[
                    :-lag
                ]
            )
            /
            n
        )


        long_run += (
            2
            *
            weight
            *
            covariance
        )


    return float(
        long_run
        /
        n
    )


# ============================================================================
# DM-STYLE TEST
# ============================================================================

def dm_test(
    loss_difference,
    horizon,
):

    """
    HAC-adjusted mean loss-difference test.

    H0:
        E[d_t] = 0

    where:
        d_t = multivariate loss - baseline loss

    Positive statistic:
        multivariate model has larger loss.

    Negative statistic:
        multivariate model has smaller loss.
    """

    d = np.asarray(
        loss_difference,
        dtype=float,
    )

    d = d[
        np.isfinite(d)
    ]

    n = len(d)

    if n < 5:

        return {
            "n_pairs":
                n,

            "mean_loss_difference":
                np.nan,

            "DM_statistic":
                np.nan,

            "p_value":
                np.nan,

            "significant_5pct":
                False,
        }


    mean_d = float(
        np.mean(d)
    )


    variance = hac_variance_mean(
        d,
        max_lag=max(
            0,
            horizon - 1,
        ),
    )


    if (
        not np.isfinite(
            variance
        )
        or
        variance <= 0
    ):

        return {
            "n_pairs":
                n,

            "mean_loss_difference":
                mean_d,

            "DM_statistic":
                np.nan,

            "p_value":
                np.nan,

            "significant_5pct":
                False,
        }


    statistic = (
        mean_d
        /
        np.sqrt(
            variance
        )
    )


    # Small-sample t reference distribution.
    p_value = float(
        2
        *
        stats.t.sf(
            np.abs(
                statistic
            ),
            df=n - 1,
        )
    )


    return {
        "n_pairs":
            n,

        "mean_loss_difference":
            mean_d,

        "DM_statistic":
            float(
                statistic
            ),

        "p_value":
            p_value,

        "significant_5pct":
            bool(
                p_value < 0.05
            ),
    }


# ============================================================================
# RUN STATISTICAL TESTS
# ============================================================================

print(
    "\n[8] PAIRED STATISTICAL TESTS"
)


results = []


group_columns = [
    "dataset",
    "material",
    "horizon",
    "multivariate_model",
    "baseline_model",
]


for keys, group in (
    pairs.groupby(
        group_columns,
        sort=True,
    )
):

    (
        dataset,
        material,
        horizon,
        multivariate_model,
        baseline_model,
    ) = keys


    test = dm_test(
        group[
            "loss_difference"
        ].to_numpy(
            dtype=float
        ),
        horizon=int(
            horizon
        ),
    )


    mean_multi_loss = float(
        group[
            "multivariate_loss"
        ].mean()
    )


    mean_baseline_loss = float(
        group[
            "baseline_loss"
        ].mean()
    )


    if (
        mean_multi_loss
        <
        mean_baseline_loss
    ):

        direction = (
            "MULTIVARIATE_BETTER"
        )

    elif (
        mean_multi_loss
        >
        mean_baseline_loss
    ):

        direction = (
            "BASELINE_BETTER"
        )

    else:

        direction = "TIE"


    if (
        test["p_value"]
        == test["p_value"]
        and
        test["p_value"] < 0.05
    ):

        if (
            test[
                "mean_loss_difference"
            ]
            < 0
        ):

            conclusion = (
                "SIGNIFICANT_MULTIVARIATE_BETTER"
            )

        else:

            conclusion = (
                "SIGNIFICANT_BASELINE_BETTER"
            )

    else:

        conclusion = (
            "NO_SIGNIFICANT_DIFFERENCE"
        )


    results.append(
        {
            "dataset":
                dataset,

            "material":
                material,

            "horizon":
                horizon,

            "multivariate_model":
                multivariate_model,

            "baseline_model":
                baseline_model,

            "n_pairs":
                test[
                    "n_pairs"
                ],

            "mean_multivariate_MAE":
                mean_multi_loss,

            "mean_baseline_MAE":
                mean_baseline_loss,

            "mean_loss_difference":
                test[
                    "mean_loss_difference"
                ],

            "DM_statistic":
                test[
                    "DM_statistic"
                ],

            "p_value":
                test[
                    "p_value"
                ],

            "significant_5pct":
                test[
                    "significant_5pct"
                ],

            "direction":
                direction,

            "conclusion":
                conclusion,
        }
    )


stat_results = pd.DataFrame(
    results
)


# ============================================================================
# PRINT RESULTS
# ============================================================================

print(
    stat_results.to_string(
        index=False
    )
)


# ============================================================================
# PRIMARY H=3
# ============================================================================

print(
    "\n[9] PRIMARY H=3 STATISTICAL RESULTS"
)


primary_h3 = stat_results.loc[
    stat_results[
        "horizon"
    ]
    == PRIMARY_HORIZON
].copy()


print(
    primary_h3.to_string(
        index=False
    )
)


# ============================================================================
# SUMMARY
# ============================================================================

print(
    "\n[10] STATISTICAL SUMMARY"
)


summary_rows = []


for (
    dataset,
    group,
) in stat_results.groupby(
    "dataset"
):

    significant = group.loc[
        group[
            "significant_5pct"
        ]
    ]


    significant_multi_better = (
        significant[
            "conclusion"
        ]
        ==
        "SIGNIFICANT_MULTIVARIATE_BETTER"
    ).sum()


    significant_baseline_better = (
        significant[
            "conclusion"
        ]
        ==
        "SIGNIFICANT_BASELINE_BETTER"
    ).sum()


    no_difference = (
        group[
            "conclusion"
        ]
        ==
        "NO_SIGNIFICANT_DIFFERENCE"
    ).sum()


    summary_rows.append(
        {
            "dataset":
                dataset,

            "total_comparisons":
                len(group),

            "significant_multivariate_better":
                significant_multi_better,

            "significant_baseline_better":
                significant_baseline_better,

            "no_significant_difference":
                no_difference,
        }
    )


summary = pd.DataFrame(
    summary_rows
)


print(
    summary.to_string(
        index=False
    )
)


# ============================================================================
# PRIMARY H=3 SUMMARY
# ============================================================================

print(
    "\n[11] PRIMARY H=3 SUMMARY"
)


primary_summary_rows = []


for (
    dataset,
    group,
) in primary_h3.groupby(
    "dataset"
):

    primary_summary_rows.append(
        {
            "dataset":
                dataset,

            "comparisons":
                len(group),

            "significant_multivariate_better":
                (
                    group[
                        "conclusion"
                    ]
                    ==
                    "SIGNIFICANT_MULTIVARIATE_BETTER"
                ).sum(),

            "significant_baseline_better":
                (
                    group[
                        "conclusion"
                    ]
                    ==
                    "SIGNIFICANT_BASELINE_BETTER"
                ).sum(),

            "no_significant_difference":
                (
                    group[
                        "conclusion"
                    ]
                    ==
                    "NO_SIGNIFICANT_DIFFERENCE"
                ).sum(),
        }
    )


primary_summary = pd.DataFrame(
    primary_summary_rows
)


print(
    primary_summary.to_string(
        index=False
    )
)


# ============================================================================
# SAVE
# ============================================================================

print(
    "\n[12] SAVING OUTPUTS"
)


pairs_path = (
    OUTPUT_DIR
    / "RO1_step25c3_paired_forecast_errors.csv"
)

results_path = (
    OUTPUT_DIR
    / "RO1_step25c3_dm_results.csv"
)

primary_path = (
    OUTPUT_DIR
    / "RO1_step25c3_primary_h3_results.csv"
)

summary_path = (
    OUTPUT_DIR
    / "RO1_step25c3_statistical_summary.csv"
)

primary_summary_path = (
    OUTPUT_DIR
    / "RO1_step25c3_primary_h3_summary.csv"
)


pairs.to_csv(
    pairs_path,
    index=False,
)

stat_results.to_csv(
    results_path,
    index=False,
)

primary_h3.to_csv(
    primary_path,
    index=False,
)

summary.to_csv(
    summary_path,
    index=False,
)

primary_summary.to_csv(
    primary_summary_path,
    index=False,
)


# ============================================================================
# FINAL ASSERTIONS
# ============================================================================

print(
    "\n[13] FINAL ASSERTIONS"
)


assert not pairs.empty

assert not stat_results.empty

assert not primary_h3.empty

assert (
    set(
        stat_results[
            "horizon"
        ]
    )
    ==
    set(HORIZONS)
)


assert (
    stat_results[
        "n_pairs"
    ]
    >= 5
).all()


assert (
    stat_results[
        "p_value"
    ]
    .dropna()
    .between(
        0,
        1,
    )
    .all()
)


assert (
    stat_results[
        "dataset"
    ]
    .isin(
        [
            "RO1_PRICE",
            "RO1_DEMAND",
        ]
    )
    .all()
)


assert (
    stat_results[
        "baseline_model"
    ]
    .isin(
        UNIVARIATE_MODELS
    )
    .all()
)


assert (
    stat_results[
        "multivariate_model"
    ]
    .isin(
        [
            "VECM",
            "VAR_DIFF",
        ]
    )
    .all()
)


# Exactly 5 price materials × 4 baselines × 4 horizons
expected_price_tests = (
    5
    * 4
    * 4
)

# Exactly 4 demand materials × 4 baselines × 4 horizons
expected_demand_tests = (
    4
    * 4
    * 4
)

expected_total_tests = (
    expected_price_tests
    +
    expected_demand_tests
)


assert (
    len(stat_results)
    ==
    expected_total_tests
)


print(
    "Paired forecast construction: PASS"
)

print(
    "Same-origin pairing: PASS"
)

print(
    "Same-target pairing: PASS"
)

print(
    "Actual-value consistency: PASS"
)

print(
    "HAC-adjusted statistical testing: PASS"
)

print(
    "Price comparison coverage: PASS"
)

print(
    "Demand comparison coverage: PASS"
)

print(
    "Primary h=3 coverage: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 25C.3 COMPLETE"
)

print(
    "=" * 78
)

print(
    "Paired statistical comparison completed."
)

print(
    "\nDM-style results:"
)

print(
    results_path
)

print(
    "\nPrimary h=3 results:"
)

print(
    primary_path
)

print(
    "\nPaired forecast errors:"
)

print(
    pairs_path
)

print(
    "\nNo model was refitted."
)

print(
    "No model was reselected."
)

print(
    "No specification was changed."
)

print(
    "\nRO1 STEP 25C.3: READY FOR SCIENTIFIC INTERPRETATION"
)

print(
    "=" * 78
)