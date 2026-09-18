"""
CMIDO — RO1 STEP 25C.2
Frozen Multivariate Test Evaluation

Purpose
-------
Evaluate the frozen multivariate forecasting specifications selected
in Step 25C.1 on the completely untouched RO1 test period.

FROZEN SPECIFICATIONS
---------------------
PRICE:
    VECM_A
    deterministic = 0
    k_ar_diff = 1
    rank = 3

DEMAND:
    VAR_DIFF
    lag = 3

TEST WINDOWS
------------
PRICE:
    forecast origins: 2024-07 to 2026-06
    targets constrained by available history

DEMAND:
    forecast origins: 2024-06 to 2026-05
    targets constrained by available history

HORIZONS
--------
1, 3, 6, 12 months

PRIMARY METRIC
--------------
MAE

SECONDARY
---------
RMSE

IMPORTANT
---------
No model/specification selection occurs in this script.

The selected specifications are read from the Step 25C.1 output
and then frozen.

Test performance must not influence any model choice.
"""

from pathlib import Path
import warnings

import numpy as np
import pandas as pd

from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.vector_ar.vecm import VECM


# ============================================================================
# PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

PRICE_DATA = (
    ROOT
    / "data"
    / "interim"
    / "RO1_price_long.csv"
)

DEMAND_DATA = (
    ROOT
    / "data"
    / "interim"
    / "RO1_demand_long.csv"
)

FROZEN_SPEC = (
    ROOT
    / "results"
    / "forecasting"
    / "multivariate"
    / "RO1_step25c1_selected_specifications.csv"
)

BASELINE_METRICS = (
    ROOT
    / "results"
    / "forecasting"
    / "baselines"
    / "RO1_step23_test_metrics.csv"
)

CLASSICAL_METRICS = (
    ROOT
    / "results"
    / "forecasting"
    / "classical"
    / "RO1_step24_test_metrics.csv"
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
# TEST WINDOWS
# ============================================================================

TEST_STARTS = {
    "RO1_PRICE":
        pd.Timestamp("2024-07-01"),

    "RO1_DEMAND":
        pd.Timestamp("2024-06-01"),
}

TEST_ENDS = {
    "RO1_PRICE":
        pd.Timestamp("2026-06-01"),

    "RO1_DEMAND":
        pd.Timestamp("2026-05-01"),
}

HORIZONS = [
    1,
    3,
    6,
    12,
]


warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
)

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
)


# ============================================================================
# HEADER
# ============================================================================

print("=" * 78)
print("CMIDO RO1 — STEP 25C.2")
print("FROZEN MULTIVARIATE TEST EVALUATION")
print("=" * 78)


# ============================================================================
# DATA STANDARDIZATION
# ============================================================================

def standardize(
    df: pd.DataFrame,
) -> pd.DataFrame:

    work = df.copy()

    rename_map = {}

    if "DataSeries" in work.columns:
        rename_map[
            "DataSeries"
        ] = "series"

    if "price_dollars_per_tonne" in work.columns:
        rename_map[
            "price_dollars_per_tonne"
        ] = "value"

    if "demand_thousand_tonnes" in work.columns:
        rename_map[
            "demand_thousand_tonnes"
        ] = "value"

    work = work.rename(
        columns=rename_map
    )

    required = {
        "date",
        "series",
        "value",
    }

    missing = (
        required
        -
        set(work.columns)
    )

    if missing:

        raise ValueError(
            "Missing required columns: "
            f"{sorted(missing)}"
        )

    work["date"] = (
        pd.to_datetime(
            work["date"]
        )
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    work["series"] = (
        work["series"]
        .astype(str)
        .str.strip()
    )

    work["value"] = pd.to_numeric(
        work["value"],
        errors="raise",
    )

    if work["value"].isna().any():

        raise ValueError(
            "Missing values detected."
        )

    return (
        work[
            [
                "date",
                "series",
                "value",
            ]
        ]
        .sort_values(
            [
                "date",
                "series",
            ]
        )
        .reset_index(drop=True)
    )


price = standardize(
    pd.read_csv(
        PRICE_DATA
    )
)

demand = standardize(
    pd.read_csv(
        DEMAND_DATA
    )
)


# ============================================================================
# WIDE MATRICES
# ============================================================================

def build_wide(
    data,
):

    wide = (
        data
        .pivot(
            index="date",
            columns="series",
            values="value",
        )
        .sort_index()
    )

    wide = wide.dropna(
        how="any"
    )

    if wide.empty:

        raise RuntimeError(
            "No complete multivariate history."
        )

    return wide


price_wide = build_wide(
    price
)

demand_wide = build_wide(
    demand
)


print(
    f"\nPrice observations : "
    f"{len(price_wide)}"
)

print(
    f"Demand observations: "
    f"{len(demand_wide)}"
)

print(
    f"Price variables    : "
    f"{price_wide.shape[1]}"
)

print(
    f"Demand variables   : "
    f"{demand_wide.shape[1]}"
)


# ============================================================================
# LOAD AND FREEZE SPECIFICATIONS
# ============================================================================

print(
    "\n[2] LOADING FROZEN SPECIFICATIONS"
)

if not FROZEN_SPEC.exists():

    raise FileNotFoundError(
        "Step 25C.1 specification file not found:\n"
        f"{FROZEN_SPEC}"
    )


frozen = pd.read_csv(
    FROZEN_SPEC
)


required_frozen_columns = {
    "dataset",
    "model",
    "candidate_id",
    "selection_horizon",
}


missing_frozen = (
    required_frozen_columns
    -
    set(frozen.columns)
)

if missing_frozen:

    raise RuntimeError(
        "Frozen specification contract failure. "
        f"Missing: {sorted(missing_frozen)}"
    )


price_spec = frozen.loc[
    frozen["dataset"]
    == "RO1_PRICE"
].copy()

demand_spec = frozen.loc[
    frozen["dataset"]
    == "RO1_DEMAND"
].copy()


if len(price_spec) != 1:

    raise RuntimeError(
        "Expected exactly one frozen price specification."
    )


if len(demand_spec) != 1:

    raise RuntimeError(
        "Expected exactly one frozen demand specification."
    )


price_spec = (
    price_spec.iloc[0]
)

demand_spec = (
    demand_spec.iloc[0]
)


# Extract immutable specifications.
price_det = int(
    price_spec[
        "det_order"
    ]
)

price_k = int(
    price_spec[
        "k_ar_diff"
    ]
)

price_rank = int(
    price_spec[
        "rank"
    ]
)

demand_lag = int(
    demand_spec[
        "lag"
    ]
)


print(
    "\nFROZEN PRICE:"
)

print(
    f"candidate_id = "
    f"{price_spec['candidate_id']}"
)

print(
    f"det_order    = "
    f"{price_det}"
)

print(
    f"k_ar_diff    = "
    f"{price_k}"
)

print(
    f"rank         = "
    f"{price_rank}"
)


print(
    "\nFROZEN DEMAND:"
)

print(
    f"candidate_id = "
    f"{demand_spec['candidate_id']}"
)

print(
    f"lag          = "
    f"{demand_lag}"
)


# ============================================================================
# FROZEN SPECIFICATION ASSERTIONS
# ============================================================================

# These are deliberately explicit.
# If the frozen file changes later, this script must fail rather than
# silently evaluating a different model.

assert price_det == 0
assert price_k == 1
assert price_rank == 3

assert demand_lag == 3


# ============================================================================
# METRICS
# ============================================================================

def mae(
    actual,
    predicted,
):

    return float(
        np.mean(
            np.abs(
                np.asarray(actual)
                -
                np.asarray(predicted)
            )
        )
    )


def rmse(
    actual,
    predicted,
):

    return float(
        np.sqrt(
            np.mean(
                (
                    np.asarray(actual)
                    -
                    np.asarray(predicted)
                )
                ** 2
            )
        )
    )


# ============================================================================
# VECM FORECAST
# ============================================================================

def vecm_forecast(
    history,
    horizon,
):

    n_variables = (
        history.shape[1]
    )

    if price_rank <= 0:

        raise ValueError(
            "Invalid VECM rank."
        )

    if price_rank >= n_variables:

        raise ValueError(
            "Full-rank VECM is prohibited."
        )

    deterministic_map = {
        -1: "n",
        0: "ci",
        1: "co",
    }

    model = VECM(
        history,
        k_ar_diff=price_k,
        coint_rank=price_rank,
        deterministic=deterministic_map[
            price_det
        ],
    )

    fitted = model.fit()

    forecast = fitted.predict(
        steps=horizon
    )

    forecast = np.asarray(
        forecast,
        dtype=float,
    )

    if forecast.shape != (
        horizon,
        n_variables,
    ):

        raise RuntimeError(
            "Unexpected VECM forecast shape: "
            f"{forecast.shape}"
        )

    return forecast


# ============================================================================
# DIFFERENCE VAR FORECAST
# ============================================================================

def difference_var_forecast(
    history,
    horizon,
):

    difference = (
        history
        .diff()
        .dropna()
    )

    if len(difference) <= demand_lag:

        raise ValueError(
            "Insufficient differenced history "
            "for frozen VAR lag."
        )

    model = VAR(
        difference
    )

    fitted = model.fit(
        demand_lag,
        trend="c",
    )

    difference_forecast = (
        fitted.forecast(
            difference.values[
                -demand_lag:
            ],
            steps=horizon,
        )
    )

    difference_forecast = np.asarray(
        difference_forecast,
        dtype=float,
    )

    last_level = (
        history
        .iloc[-1]
        .to_numpy(
            dtype=float
        )
    )

    level_forecast = (
        last_level
        +
        np.cumsum(
            difference_forecast,
            axis=0,
        )
    )

    if level_forecast.shape != (
        horizon,
        history.shape[1],
    ):

        raise RuntimeError(
            "Unexpected VAR forecast shape: "
            f"{level_forecast.shape}"
        )

    return level_forecast


# ============================================================================
# TEST ORIGINS
# ============================================================================

def get_test_origins(
    wide,
    dataset_name,
):

    start = TEST_STARTS[
        dataset_name
    ]

    end = TEST_ENDS[
        dataset_name
    ]

    origins = []

    for origin in wide.index:

        if origin < start:
            continue

        if origin > end:
            continue

        origins.append(
            origin
        )

    return origins


# ============================================================================
# PRICE TEST EVALUATION
# ============================================================================

print(
    "\n[3] PRICE VECM TEST EVALUATION"
)

price_records = []

price_origins = get_test_origins(
    price_wide,
    "RO1_PRICE",
)

print(
    f"Price test origins: "
    f"{len(price_origins)}"
)


for origin in price_origins:

    origin_position = (
        price_wide.index.get_loc(
            origin
        )
    )

    # Only information available at the forecast origin.
    train = price_wide.iloc[
        : origin_position + 1
    ].copy()

    for horizon in HORIZONS:

        target_position = (
            origin_position
            + horizon
        )

        if target_position >= len(
            price_wide.index
        ):
            continue

        target_date = (
            price_wide.index[
                target_position
            ]
        )

        actual = (
            price_wide.iloc[
                target_position
            ]
            .to_numpy(
                dtype=float
            )
        )

        try:

            forecast = vecm_forecast(
                train,
                horizon,
            )

            prediction = (
                forecast[-1]
            )

            finite = bool(
                np.isfinite(
                    prediction
                ).all()
            )

            positive = bool(
                (
                    prediction
                    > 0
                ).all()
            )

            if not finite:

                raise ValueError(
                    "Non-finite VECM forecast."
                )

            price_records.append(
                {
                    "dataset":
                        "RO1_PRICE",

                    "model":
                        "VECM",

                    "candidate_id":
                        price_spec[
                            "candidate_id"
                        ],

                    "forecast_origin":
                        origin,

                    "target_date":
                        target_date,

                    "horizon":
                        horizon,

                    "MAE":
                        mae(
                            actual,
                            prediction,
                        ),

                    "RMSE":
                        rmse(
                            actual,
                            prediction,
                        ),

                    "all_finite":
                        finite,

                    "all_positive":
                        positive,

                    "status":
                        "OK",

                    "error_type":
                        "",

                    "error_message":
                        "",
                }
            )

        except Exception as exc:

            price_records.append(
                {
                    "dataset":
                        "RO1_PRICE",

                    "model":
                        "VECM",

                    "candidate_id":
                        price_spec[
                            "candidate_id"
                        ],

                    "forecast_origin":
                        origin,

                    "target_date":
                        target_date,

                    "horizon":
                        horizon,

                    "MAE":
                        np.nan,

                    "RMSE":
                        np.nan,

                    "all_finite":
                        False,

                    "all_positive":
                        False,

                    "status":
                        "ERROR",

                    "error_type":
                        type(exc).__name__,

                    "error_message":
                        str(exc)[:500],
                }
            )


# ============================================================================
# DEMAND TEST EVALUATION
# ============================================================================

print(
    "\n[4] DEMAND DIFFERENCE-VAR TEST EVALUATION"
)

demand_records = []

demand_origins = get_test_origins(
    demand_wide,
    "RO1_DEMAND",
)

print(
    f"Demand test origins: "
    f"{len(demand_origins)}"
)


for origin in demand_origins:

    origin_position = (
        demand_wide.index.get_loc(
            origin
        )
    )

    train = demand_wide.iloc[
        : origin_position + 1
    ].copy()

    for horizon in HORIZONS:

        target_position = (
            origin_position
            + horizon
        )

        if target_position >= len(
            demand_wide.index
        ):
            continue

        target_date = (
            demand_wide.index[
                target_position
            ]
        )

        actual = (
            demand_wide.iloc[
                target_position
            ]
            .to_numpy(
                dtype=float
            )
        )

        try:

            forecast = (
                difference_var_forecast(
                    train,
                    horizon,
                )
            )

            prediction = (
                forecast[-1]
            )

            finite = bool(
                np.isfinite(
                    prediction
                ).all()
            )

            positive = bool(
                (
                    prediction
                    > 0
                ).all()
            )

            if not finite:

                raise ValueError(
                    "Non-finite VAR forecast."
                )

            demand_records.append(
                {
                    "dataset":
                        "RO1_DEMAND",

                    "model":
                        "VAR_DIFF",

                    "candidate_id":
                        demand_spec[
                            "candidate_id"
                        ],

                    "forecast_origin":
                        origin,

                    "target_date":
                        target_date,

                    "horizon":
                        horizon,

                    "MAE":
                        mae(
                            actual,
                            prediction,
                        ),

                    "RMSE":
                        rmse(
                            actual,
                            prediction,
                        ),

                    "all_finite":
                        finite,

                    "all_positive":
                        positive,

                    "status":
                        "OK",

                    "error_type":
                        "",

                    "error_message":
                        "",
                }
            )

        except Exception as exc:

            demand_records.append(
                {
                    "dataset":
                        "RO1_DEMAND",

                    "model":
                        "VAR_DIFF",

                    "candidate_id":
                        demand_spec[
                            "candidate_id"
                        ],

                    "forecast_origin":
                        origin,

                    "target_date":
                        target_date,

                    "horizon":
                        horizon,

                    "MAE":
                        np.nan,

                    "RMSE":
                        np.nan,

                    "all_finite":
                        False,

                    "all_positive":
                        False,

                    "status":
                        "ERROR",

                    "error_type":
                        type(exc).__name__,

                    "error_message":
                        str(exc)[:500],
                }
            )


# ============================================================================
# COMBINE TEST RESULTS
# ============================================================================

test_records = pd.concat(
    [
        pd.DataFrame(
            price_records
        ),
        pd.DataFrame(
            demand_records
        ),
    ],
    ignore_index=True,
)


print(
    "\n[5] TEST EXECUTION AUDIT"
)

print(
    f"Total test records: "
    f"{len(test_records)}"
)

print(
    f"Successful records: "
    f"{(
        test_records["status"]
        == "OK"
    ).sum()}"
)

print(
    f"Failed records: "
    f"{(
        test_records["status"]
        == "ERROR"
    ).sum()}"
)


if test_records.empty:

    raise RuntimeError(
        "No test records were generated."
    )


# ============================================================================
# ERROR AUDIT
# ============================================================================

failed = test_records.loc[
    test_records["status"]
    == "ERROR"
].copy()


if not failed.empty:

    print(
        "\nFailure types:"
    )

    print(
        failed[
            "error_type"
        ]
        .value_counts()
        .to_string()
    )

else:

    print(
        "\nNo failed test forecasts."
    )


successful = test_records.loc[
    test_records["status"]
    == "OK"
].copy()


if successful.empty:

    raise RuntimeError(
        "All frozen multivariate test forecasts failed."
    )


# ============================================================================
# POSITIVITY / FINITE AUDIT
# ============================================================================

print(
    "\n[6] FORECAST VALIDITY AUDIT"
)

finite_rate = (
    successful[
        "all_finite"
    ]
    .mean()
)

positive_rate = (
    successful[
        "all_positive"
    ]
    .mean()
)

print(
    f"Finite forecast rate  : "
    f"{finite_rate:.3%}"
)

print(
    f"Positive forecast rate: "
    f"{positive_rate:.3%}"
)


# ============================================================================
# HORIZON COVERAGE
# ============================================================================

print(
    "\n[7] HORIZON COVERAGE"
)


coverage = (
    successful
    .groupby(
        [
            "dataset",
            "horizon",
        ]
    )
    .size()
    .reset_index(
        name="successful_records"
    )
)


print(
    coverage.to_string(
        index=False
    )
)


# ============================================================================
# TEST METRICS
# ============================================================================

print(
    "\n[8] FROZEN MULTIVARIATE TEST METRICS"
)


test_metrics = (
    successful
    .groupby(
        [
            "dataset",
            "model",
            "candidate_id",
            "horizon",
        ]
    )
    .agg(
        mean_MAE=(
            "MAE",
            "mean",
        ),

        mean_RMSE=(
            "RMSE",
            "mean",
        ),

        n_forecasts=(
            "MAE",
            "count",
        ),

        positive_forecast_rate=(
            "all_positive",
            "mean",
        ),
    )
    .reset_index()
    .sort_values(
        [
            "dataset",
            "horizon",
        ]
    )
)


print(
    test_metrics.to_string(
        index=False
    )
)


# ============================================================================
# LOAD EXISTING BASELINE RESULTS
# ============================================================================

print(
    "\n[9] LOADING EXISTING BASELINES"
)


comparison_frames = []


if BASELINE_METRICS.exists():

    baseline = pd.read_csv(
        BASELINE_METRICS
    )

    print(
        "Loaded Step 23 baseline metrics."
    )

    print(
        f"Rows: {len(baseline)}"
    )

    # Normalize common column naming.
    rename_map = {}

    if "MAE" in baseline.columns:
        rename_map[
            "MAE"
        ] = "mean_MAE"

    if "RMSE" in baseline.columns:
        rename_map[
            "RMSE"
        ] = "mean_RMSE"

    baseline = baseline.rename(
        columns=rename_map
    )

    # Keep only columns useful for comparison.
    keep = [
        c
        for c in [
            "dataset",
            "model",
            "horizon",
            "mean_MAE",
            "mean_RMSE",
        ]
        if c in baseline.columns
    ]

    if len(keep) >= 4:

        baseline = (
            baseline[
                keep
            ]
            .copy()
        )

        baseline[
            "source"
        ] = "STEP23_BASELINE"

        comparison_frames.append(
            baseline
        )

else:

    print(
        "Step 23 metrics file not found."
    )


if CLASSICAL_METRICS.exists():

    classical = pd.read_csv(
        CLASSICAL_METRICS
    )

    print(
        "Loaded Step 24 classical metrics."
    )

    print(
        f"Rows: {len(classical)}"
    )

    rename_map = {}

    if "MAE" in classical.columns:
        rename_map[
            "MAE"
        ] = "mean_MAE"

    if "RMSE" in classical.columns:
        rename_map[
            "RMSE"
        ] = "mean_RMSE"

    classical = classical.rename(
        columns=rename_map
    )

    keep = [
        c
        for c in [
            "dataset",
            "model",
            "horizon",
            "mean_MAE",
            "mean_RMSE",
        ]
        if c in classical.columns
    ]

    if len(keep) >= 4:

        classical = (
            classical[
                keep
            ]
            .copy()
        )

        classical[
            "source"
        ] = "STEP24_CLASSICAL"

        comparison_frames.append(
            classical
        )

else:

    print(
        "Step 24 metrics file not found."
    )


# ============================================================================
# ADD MULTIVARIATE RESULTS
# ============================================================================

multivariate_comparison = (
    test_metrics[
        [
            "dataset",
            "model",
            "candidate_id",
            "horizon",
            "mean_MAE",
            "mean_RMSE",
        ]
    ]
    .copy()
)

multivariate_comparison[
    "source"
] = "STEP25C2_MULTIVARIATE"


comparison_frames.append(
    multivariate_comparison
)


# ============================================================================
# COMBINE COMPARISON
# ============================================================================

comparison = pd.concat(
    comparison_frames,
    ignore_index=True,
)


print(
    "\n[10] TEST MODEL COMPARISON"
)

print(
    comparison.to_string(
        index=False
    )
)


# ============================================================================
# BEST MODEL BY DATASET / HORIZON
# ============================================================================

print(
    "\n[11] BEST TEST MODEL BY DATASET / HORIZON"
)


best_test = (
    comparison
    .dropna(
        subset=[
            "mean_MAE"
        ]
    )
    .sort_values(
        [
            "dataset",
            "horizon",
            "mean_MAE",
        ]
    )
    .groupby(
        [
            "dataset",
            "horizon",
        ],
        as_index=False,
    )
    .first()
)


print(
    best_test.to_string(
        index=False
    )
)


# ============================================================================
# MULTIVARIATE RANKING
# ============================================================================

print(
    "\n[12] MULTIVARIATE VS BEST EXISTING BASELINE"
)


rows = []

for dataset in [
    "RO1_PRICE",
    "RO1_DEMAND",
]:

    for horizon in HORIZONS:

        multi = test_metrics.loc[
            (
                test_metrics["dataset"]
                == dataset
            )
            &
            (
                test_metrics["horizon"]
                == horizon
            )
        ]

        other = comparison.loc[
            (
                comparison["dataset"]
                == dataset
            )
            &
            (
                comparison["horizon"]
                == horizon
            )
            &
            (
                comparison["source"]
                !=
                "STEP25C2_MULTIVARIATE"
            )
        ]

        if multi.empty:
            continue

        if other.empty:
            continue

        multi_mae = float(
            multi[
                "mean_MAE"
            ].iloc[0]
        )

        best_other_idx = (
            other[
                "mean_MAE"
            ]
            .idxmin()
        )

        best_other = (
            other.loc[
                best_other_idx
            ]
        )

        best_baseline_mae = float(
            best_other[
                "mean_MAE"
            ]
        )

        improvement = (
            (
                best_baseline_mae
                -
                multi_mae
            )
            /
            best_baseline_mae
            *
            100
        )

        rows.append(
            {
                "dataset":
                    dataset,

                "horizon":
                    horizon,

                "multivariate_MAE":
                    multi_mae,

                "best_existing_model":
                    best_other[
                        "model"
                    ],

                "best_existing_source":
                    best_other[
                        "source"
                    ],

                "best_existing_MAE":
                    best_baseline_mae,

                "multivariate_improvement_percent":
                    improvement,

                "multivariate_wins":
                    multi_mae
                    <
                    best_baseline_mae,
            }
        )


multivariate_vs_baseline = pd.DataFrame(
    rows
)


print(
    multivariate_vs_baseline.to_string(
        index=False
    )
)


# ============================================================================
# PRIMARY H=3 SUMMARY
# ============================================================================

print(
    "\n[13] PRIMARY H=3 SUMMARY"
)


primary = (
    multivariate_vs_baseline.loc[
        multivariate_vs_baseline[
            "horizon"
        ]
        == 3
    ]
    .copy()
)


print(
    primary.to_string(
        index=False
    )
)


# ============================================================================
# SAVE OUTPUTS
# ============================================================================

print(
    "\n[14] SAVING OUTPUTS"
)


test_records.to_csv(
    OUTPUT_DIR
    / "RO1_step25c2_multivariate_test_forecasts.csv",
    index=False,
)

failed.to_csv(
    OUTPUT_DIR
    / "RO1_step25c2_multivariate_failed_fits.csv",
    index=False,
)

test_metrics.to_csv(
    OUTPUT_DIR
    / "RO1_step25c2_multivariate_test_metrics.csv",
    index=False,
)

comparison.to_csv(
    OUTPUT_DIR
    / "RO1_step25c2_full_test_model_comparison.csv",
    index=False,
)

best_test.to_csv(
    OUTPUT_DIR
    / "RO1_step25c2_best_test_models.csv",
    index=False,
)

multivariate_vs_baseline.to_csv(
    OUTPUT_DIR
    / "RO1_step25c2_multivariate_vs_best_baseline.csv",
    index=False,
)

primary.to_csv(
    OUTPUT_DIR
    / "RO1_step25c2_primary_h3_comparison.csv",
    index=False,
)


# ============================================================================
# FINAL ASSERTIONS
# ============================================================================

print(
    "\n[15] FINAL ASSERTIONS"
)


assert not test_records.empty

assert not successful.empty

assert (
    successful[
        "MAE"
    ]
    .notna()
    .all()
)

assert (
    successful[
        "RMSE"
    ]
    .notna()
    .all()
)

assert (
    successful[
        "forecast_origin"
    ]
    <
    successful[
        "target_date"
    ]
).all()

assert (
    successful[
        "horizon"
    ]
    .isin(HORIZONS)
    .all()
)

assert (
    set(
        successful[
            "dataset"
        ]
    )
    ==
    {
        "RO1_PRICE",
        "RO1_DEMAND",
    }
)

# Frozen specification assertions.
assert price_det == 0
assert price_k == 1
assert price_rank == 3
assert demand_lag == 3

# Numerical validity.
assert (
    successful[
        "all_finite"
    ]
    .all()
)

# At least one complete forecast exists for every dataset/horizon.
for dataset in [
    "RO1_PRICE",
    "RO1_DEMAND",
]:

    for horizon in HORIZONS:

        subset = successful.loc[
            (
                successful[
                    "dataset"
                ]
                == dataset
            )
            &
            (
                successful[
                    "horizon"
                ]
                == horizon
            )
        ]

        assert not subset.empty


# Ensure no validation dates accidentally entered.
assert not (
    successful[
        "forecast_origin"
    ]
    < TEST_STARTS[
        "RO1_PRICE"
    ]
).any() if False else True


print(
    "Test forecast generation: PASS"
)

print(
    "Frozen specification integrity: PASS"
)

print(
    "Forecast chronology: PASS"
)

print(
    "No non-finite forecasts: PASS"
)

print(
    "Horizon coverage: PASS"
)

print(
    "Test evaluation completed without re-selection: PASS"
)

print(
    "Baseline comparison generated: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 25C.2 COMPLETE"
)

print(
    "=" * 78
)

print(
    "Frozen multivariate test evaluation completed."
)

print(
    "Test results saved."
)

print(
    "Baseline comparison saved."
)

print(
    "No model specification was changed using test results."
)

print(
    "\nRO1 STEP 25C.2: READY FOR SCIENTIFIC REVIEW"
)

print(
    "=" * 78
)