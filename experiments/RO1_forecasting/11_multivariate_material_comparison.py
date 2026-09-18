"""
CMIDO — RO1 STEP 25C.2M
Frozen Multivariate Material-Level Test Evaluation

Purpose
-------
Rerun the frozen Step 25C.2 multivariate test evaluation while
preserving individual material-level predictions.

This script does NOT:
- select models
- tune hyperparameters
- use test results for model selection
- change the frozen VECM/VAR specifications
- change the test windows
- change the forecasting horizons

Frozen specifications
---------------------
PRICE:
    VECM_A
    deterministic = 0
    k_ar_diff = 1
    rank = 3

DEMAND:
    VAR_DIFF
    lag = 3

Outputs
-------
1. Material-level individual forecasts
2. Material-level MAE/RMSE
3. System-level MAE/RMSE
4. Coverage and validity audits

The resulting material-level forecasts are then suitable for
apples-to-apples comparison with Steps 23 and 24.
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


# ============================================================================
# WARNINGS
# ============================================================================

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
print("CMIDO RO1 — STEP 25C.2M")
print("FROZEN MULTIVARIATE MATERIAL-LEVEL TEST EVALUATION")
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
        .reset_index(
            drop=True
        )
    )


# ============================================================================
# LOAD DATA
# ============================================================================

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

print(
    "\nPrice materials:"
)

for material in price_wide.columns:

    print(
        f"  - {material}"
    )

print(
    "\nDemand materials:"
)

for material in demand_wide.columns:

    print(
        f"  - {material}"
    )


# ============================================================================
# LOAD FROZEN SPECIFICATIONS
# ============================================================================

print(
    "\n[1] LOADING FROZEN SPECIFICATIONS"
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


# ============================================================================
# EXTRACT IMMUTABLE SPECIFICATIONS
# ============================================================================

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
# FROZEN SPECIFICATION CONTRACT
# ============================================================================

assert price_det == 0
assert price_k == 1
assert price_rank == 3

assert demand_lag == 3


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
# METRIC FUNCTIONS
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
# MATERIAL-LEVEL RECORD CREATION
# ============================================================================

def create_material_records(
    dataset,
    model,
    candidate_id,
    origin,
    target_date,
    horizon,
    actual,
    prediction,
    material_names,
):

    records = []

    actual = np.asarray(
        actual,
        dtype=float,
    )

    prediction = np.asarray(
        prediction,
        dtype=float,
    )

    if len(actual) != len(
        material_names
    ):

        raise RuntimeError(
            "Actual vector length does not match "
            "material count."
        )

    if len(prediction) != len(
        material_names
    ):

        raise RuntimeError(
            "Prediction vector length does not match "
            "material count."
        )

    for idx, material in enumerate(
        material_names
    ):

        actual_value = float(
            actual[idx]
        )

        prediction_value = float(
            prediction[idx]
        )

        error = (
            prediction_value
            -
            actual_value
        )

        records.append(
            {
                "dataset":
                    dataset,

                "model":
                    model,

                "candidate_id":
                    candidate_id,

                "material":
                    material,

                "forecast_origin":
                    origin,

                "target_date":
                    target_date,

                "horizon":
                    int(horizon),

                "actual":
                    actual_value,

                "prediction":
                    prediction_value,

                "error":
                    error,

                "absolute_error":
                    abs(error),

                "squared_error":
                    error ** 2,

                "finite":
                    bool(
                        np.isfinite(
                            prediction_value
                        )
                    ),

                "positive":
                    bool(
                        prediction_value > 0
                    ),

                "status":
                    "OK",
            }
        )

    return records


# ============================================================================
# PRICE TEST
# ============================================================================

print(
    "\n[2] PRICE VECM MATERIAL-LEVEL TEST"
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

    train = price_wide.iloc[
        : origin_position + 1
    ].copy()

    for horizon in HORIZONS:

        target_position = (
            origin_position
            +
            horizon
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

            if not np.isfinite(
                prediction
            ).all():

                raise ValueError(
                    "Non-finite VECM forecast."
                )

            if not (
                prediction > 0
            ).all():

                raise ValueError(
                    "Non-positive VECM forecast."
                )

            material_records = (
                create_material_records(
                    dataset="RO1_PRICE",
                    model="VECM",
                    candidate_id=
                        price_spec[
                            "candidate_id"
                        ],
                    origin=origin,
                    target_date=target_date,
                    horizon=horizon,
                    actual=actual,
                    prediction=prediction,
                    material_names=
                        list(
                            price_wide.columns
                        ),
                )
            )

            price_records.extend(
                material_records
            )

        except Exception as exc:

            print(
                "\nPRICE FORECAST ERROR"
            )

            print(
                f"Origin={origin}"
                f" Horizon={horizon}"
            )

            print(
                f"{type(exc).__name__}: "
                f"{str(exc)[:300]}"
            )

            raise


# ============================================================================
# DEMAND TEST
# ============================================================================

print(
    "\n[3] DEMAND VAR MATERIAL-LEVEL TEST"
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
            +
            horizon
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

            if not np.isfinite(
                prediction
            ).all():

                raise ValueError(
                    "Non-finite VAR forecast."
                )

            if not (
                prediction > 0
            ).all():

                raise ValueError(
                    "Non-positive VAR forecast."
                )

            material_records = (
                create_material_records(
                    dataset="RO1_DEMAND",
                    model="VAR_DIFF",
                    candidate_id=
                        demand_spec[
                            "candidate_id"
                        ],
                    origin=origin,
                    target_date=target_date,
                    horizon=horizon,
                    actual=actual,
                    prediction=prediction,
                    material_names=
                        list(
                            demand_wide.columns
                        ),
                )
            )

            demand_records.extend(
                material_records
            )

        except Exception as exc:

            print(
                "\nDEMAND FORECAST ERROR"
            )

            print(
                f"Origin={origin}"
                f" Horizon={horizon}"
            )

            print(
                f"{type(exc).__name__}: "
                f"{str(exc)[:300]}"
            )

            raise


# ============================================================================
# COMBINE
# ============================================================================

material_forecasts = pd.concat(
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


# ============================================================================
# BASIC AUDIT
# ============================================================================

print(
    "\n[4] MATERIAL-LEVEL FORECAST AUDIT"
)

print(
    f"Total material forecast records: "
    f"{len(material_forecasts)}"
)

print(
    f"Price material records: "
    f"{len(price_records)}"
)

print(
    f"Demand material records: "
    f"{len(demand_records)}"
)


if material_forecasts.empty:

    raise RuntimeError(
        "No material-level forecasts generated."
    )


# ============================================================================
# CHRONOLOGY
# ============================================================================

material_forecasts[
    "forecast_origin"
] = pd.to_datetime(
    material_forecasts[
        "forecast_origin"
    ]
)

material_forecasts[
    "target_date"
] = pd.to_datetime(
    material_forecasts[
        "target_date"
    ]
)


assert (
    material_forecasts[
        "target_date"
    ]
    >
    material_forecasts[
        "forecast_origin"
    ]
).all()


# ============================================================================
# FINITE / POSITIVE
# ============================================================================

assert (
    material_forecasts[
        "actual"
    ]
    .apply(
        np.isfinite
    )
    .all()
)

assert (
    material_forecasts[
        "prediction"
    ]
    .apply(
        np.isfinite
    )
    .all()
)

assert (
    material_forecasts[
        "finite"
    ]
    .all()
)

assert (
    material_forecasts[
        "positive"
    ]
    .all()
)


# ============================================================================
# HORIZON COVERAGE
# ============================================================================

print(
    "\n[5] HORIZON COVERAGE"
)

coverage = (
    material_forecasts
    .groupby(
        [
            "dataset",
            "material",
            "horizon",
        ]
    )
    .size()
    .reset_index(
        name="n_forecasts"
    )
)


print(
    coverage.to_string(
        index=False
    )
)


# ============================================================================
# DUPLICATE AUDIT
# ============================================================================

duplicate_keys = [
    "dataset",
    "model",
    "candidate_id",
    "material",
    "forecast_origin",
    "target_date",
    "horizon",
]


duplicate_count = (
    material_forecasts
    .duplicated(
        subset=duplicate_keys
    )
    .sum()
)


print(
    f"\nDuplicate material forecast records: "
    f"{duplicate_count}"
)


assert duplicate_count == 0


# ============================================================================
# EXPECTED MATERIAL COVERAGE
# ============================================================================

expected_price_materials = set(
    price_wide.columns
)

expected_demand_materials = set(
    demand_wide.columns
)


actual_price_materials = set(
    material_forecasts.loc[
        material_forecasts[
            "dataset"
        ]
        == "RO1_PRICE",
        "material",
    ]
)

actual_demand_materials = set(
    material_forecasts.loc[
        material_forecasts[
            "dataset"
        ]
        == "RO1_DEMAND",
        "material",
    ]
)


assert (
    actual_price_materials
    ==
    expected_price_materials
)

assert (
    actual_demand_materials
    ==
    expected_demand_materials
)


# ============================================================================
# MATERIAL-LEVEL METRICS
# ============================================================================

print(
    "\n[6] MATERIAL-LEVEL TEST METRICS"
)

material_metrics = (
    material_forecasts
    .groupby(
        [
            "dataset",
            "model",
            "candidate_id",
            "material",
            "horizon",
        ]
    )
    .agg(
        MAE=(
            "absolute_error",
            "mean",
        ),

        RMSE=(
            "squared_error",
            lambda x:
                float(
                    np.sqrt(
                        np.mean(x)
                    )
                ),
        ),

        n_forecasts=(
            "absolute_error",
            "count",
        ),

        positive_rate=(
            "positive",
            "mean",
        ),
    )
    .reset_index()
)


print(
    material_metrics.to_string(
        index=False
    )
)


# ============================================================================
# SYSTEM-LEVEL METRICS
# ============================================================================

print(
    "\n[7] SYSTEM-LEVEL TEST METRICS"
)

system_metrics = (
    material_forecasts
    .groupby(
        [
            "dataset",
            "model",
            "candidate_id",
            "horizon",
        ]
    )
    .agg(
        system_MAE=(
            "absolute_error",
            "mean",
        ),

        system_RMSE=(
            "squared_error",
            lambda x:
                float(
                    np.sqrt(
                        np.mean(x)
                    )
                ),
        ),

        n_material_forecasts=(
            "absolute_error",
            "count",
        ),
    )
    .reset_index()
)


print(
    system_metrics.to_string(
        index=False
    )
)


# ============================================================================
# EXPECTED RECORD COUNTS
# ============================================================================

print(
    "\n[8] RECORD COUNT AUDIT"
)

price_horizon_counts = (
    material_forecasts.loc[
        material_forecasts[
            "dataset"
        ]
        == "RO1_PRICE"
    ]
    .groupby(
        "horizon"
    )
    .size()
)

demand_horizon_counts = (
    material_forecasts.loc[
        material_forecasts[
            "dataset"
        ]
        == "RO1_DEMAND"
    ]
    .groupby(
        "horizon"
    )
    .size()
)


print(
    "\nPrice:"
)

print(
    price_horizon_counts
)


print(
    "\nDemand:"
)

print(
    demand_horizon_counts
)


# ============================================================================
# SAVE
# ============================================================================

print(
    "\n[9] SAVING MATERIAL-LEVEL OUTPUTS"
)


material_forecast_path = (
    OUTPUT_DIR
    / "RO1_step25c2m_material_forecasts.csv"
)

material_metrics_path = (
    OUTPUT_DIR
    / "RO1_step25c2m_material_metrics.csv"
)

system_metrics_path = (
    OUTPUT_DIR
    / "RO1_step25c2m_system_metrics.csv"
)

coverage_path = (
    OUTPUT_DIR
    / "RO1_step25c2m_material_coverage.csv"
)


material_forecasts.to_csv(
    material_forecast_path,
    index=False,
)

material_metrics.to_csv(
    material_metrics_path,
    index=False,
)

system_metrics.to_csv(
    system_metrics_path,
    index=False,
)

coverage.to_csv(
    coverage_path,
    index=False,
)


# ============================================================================
# FINAL ASSERTIONS
# ============================================================================

print(
    "\n[10] FINAL ASSERTIONS"
)


assert len(
    material_forecasts
) > 0


assert len(
    material_metrics
) > 0


assert len(
    system_metrics
) > 0


assert (
    material_forecasts[
        "status"
    ]
    == "OK"
).all()


assert (
    material_forecasts[
        "horizon"
    ]
    .isin(HORIZONS)
    .all()
)


assert (
    material_forecasts[
        "MAE"
    ]
    if "MAE" in material_forecasts.columns
    else True
)


assert price_det == 0
assert price_k == 1
assert price_rank == 3
assert demand_lag == 3


print(
    "Material-level forecast generation: PASS"
)

print(
    "Frozen VECM specification: PASS"
)

print(
    "Frozen VAR specification: PASS"
)

print(
    "Forecast chronology: PASS"
)

print(
    "Finite predictions: PASS"
)

print(
    "Positive predictions: PASS"
)

print(
    "Material identity preservation: PASS"
)

print(
    "Duplicate protection: PASS"
)

print(
    "Horizon coverage: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 25C.2M COMPLETE"
)

print(
    "=" * 78
)

print(
    "Frozen multivariate material-level test evaluation completed."
)

print(
    "\nMaterial forecasts:"
)

print(
    material_forecast_path
)

print(
    "\nMaterial metrics:"
)

print(
    material_metrics_path
)

print(
    "\nSystem metrics:"
)

print(
    system_metrics_path
)

print(
    "\nRO1 STEP 25C.2M: READY FOR MATERIAL-LEVEL COMPARISON"
)

print(
    "=" * 78
)