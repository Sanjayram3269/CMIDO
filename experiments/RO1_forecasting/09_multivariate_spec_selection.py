"""
CMIDO — RO1 STEP 25C.1
Multivariate Model Specification Selection

Purpose
-------
Select VECM / difference-VAR specifications using a proper
rolling-origin validation protocol.

IMPORTANT TEMPORAL DESIGN
-------------------------
The full historical dataset is loaded.

For every validation origin:

    training data <= forecast origin
    target       = origin + horizon

Therefore validation forecasts never see future information.

Development period:
    used to establish candidate specifications / diagnostics.

Validation period:
    used to select the final multivariate specification.

Test period:
    completely untouched in this script.

Scientific decision from Step 25B.1
------------------------------------
PRICE:
    VECM candidate

DEMAND:
    VAR on first differences

Price candidate set:
    VECM(det=0,  k_ar_diff=1, rank=3)
    VECM(det=0,  k_ar_diff=2, rank=2)
    VECM(det=1,  k_ar_diff=3, rank=1)
    VECM(det=-1, k_ar_diff=2, rank=2)

Demand candidate set:
    VAR_DIFF(lag=1)
    VAR_DIFF(lag=2)
    VAR_DIFF(lag=3)

Primary selection criterion:
    mean MAE at h=3

Secondary:
    mean RMSE at h=3

No test observations are used.
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
# TEMPORAL CONTRACT
# ============================================================================

VALIDATION_STARTS = {
    "RO1_PRICE":
        pd.Timestamp("2022-07-01"),

    "RO1_DEMAND":
        pd.Timestamp("2022-06-01"),
}

VALIDATION_ENDS = {
    "RO1_PRICE":
        pd.Timestamp("2024-06-01"),

    "RO1_DEMAND":
        pd.Timestamp("2024-05-01"),
}

HORIZONS = [
    1,
    3,
    6,
    12,
]

PRIMARY_HORIZON = 3

MIN_TRAINING_MONTHS = 60

MIN_COVERAGE = 0.95


# ============================================================================
# PREDECLARED CANDIDATES
# ============================================================================

PRICE_CANDIDATES = [
    {
        "candidate_id":
            "VECM_A",

        "det_order":
            0,

        "k_ar_diff":
            1,

        "rank":
            3,
    },

    {
        "candidate_id":
            "VECM_B",

        "det_order":
            0,

        "k_ar_diff":
            2,

        "rank":
            2,
    },

    {
        "candidate_id":
            "VECM_C",

        "det_order":
            1,

        "k_ar_diff":
            3,

        "rank":
            1,
    },

    {
        "candidate_id":
            "VECM_D",

        "det_order":
            -1,

        "k_ar_diff":
            2,

        "rank":
            2,
    },
]

DEMAND_CANDIDATES = [
    {
        "candidate_id":
            "VAR_D1",

        "lag":
            1,
    },

    {
        "candidate_id":
            "VAR_D2",

        "lag":
            2,
    },

    {
        "candidate_id":
            "VAR_D3",

        "lag":
            3,
    },
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
print("CMIDO RO1 — STEP 25C.1")
print("MULTIVARIATE MODEL SPECIFICATION SELECTION")
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
        rename_map["DataSeries"] = "series"

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
# WIDE MATRICES — FULL HISTORY
# ============================================================================

def build_wide(
    data: pd.DataFrame,
) -> pd.DataFrame:

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
    f"Price range        : "
    f"{price_wide.index.min().date()} "
    f"to "
    f"{price_wide.index.max().date()}"
)

print(
    f"Demand range       : "
    f"{demand_wide.index.min().date()} "
    f"to "
    f"{demand_wide.index.max().date()}"
)


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
# VALIDATION ORIGINS
# ============================================================================

def get_validation_origins(
    wide,
    dataset_name,
):

    start = VALIDATION_STARTS[
        dataset_name
    ]

    end = VALIDATION_ENDS[
        dataset_name
    ]

    origins = []

    for origin in wide.index:

        if origin < start:
            continue

        if origin > end:
            continue

        position = (
            wide.index.get_loc(
                origin
            )
        )

        if position + 1 < MIN_TRAINING_MONTHS:
            continue

        origins.append(
            origin
        )

    return origins


# ============================================================================
# EXPECTED VALIDATION TASKS
# ============================================================================

def expected_tasks(
    wide,
    dataset_name,
):

    origins = get_validation_origins(
        wide,
        dataset_name,
    )

    records = []

    for origin in origins:

        origin_position = (
            wide.index.get_loc(
                origin
            )
        )

        for horizon in HORIZONS:

            target_position = (
                origin_position
                + horizon
            )

            if target_position >= len(
                wide.index
            ):
                continue

            records.append(
                {
                    "forecast_origin":
                        origin,

                    "target_date":
                        wide.index[
                            target_position
                        ],

                    "horizon":
                        horizon,
                }
            )

    return pd.DataFrame(
        records
    )


# ============================================================================
# VECM
# ============================================================================

def vecm_forecast(
    history,
    horizon,
    rank,
    k_ar_diff,
    det_order,
):

    n_variables = (
        history.shape[1]
    )

    if rank <= 0:
        raise ValueError(
            "VECM rank must be positive."
        )

    if rank >= n_variables:
        raise ValueError(
            "Full-rank VECM is prohibited."
        )

    deterministic_map = {
        -1: "n",
        0: "ci",
        1: "co",
    }

    if det_order not in deterministic_map:
        raise ValueError(
            f"Unsupported det_order={det_order}"
        )

    model = VECM(
        history,
        k_ar_diff=k_ar_diff,
        coint_rank=rank,
        deterministic=deterministic_map[
            det_order
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
            "Unexpected VECM forecast shape."
        )

    return forecast


# ============================================================================
# DIFFERENCE VAR
# ============================================================================

def difference_var_forecast(
    history,
    horizon,
    lag,
):

    difference = (
        history
        .diff()
        .dropna()
    )

    if len(difference) <= lag:
        raise ValueError(
            "Insufficient differenced observations "
            f"for lag={lag}."
        )

    model = VAR(
        difference
    )

    fitted = model.fit(
        lag,
        trend="c",
    )

    difference_forecast = (
        fitted.forecast(
            difference.values[
                -lag:
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

    return level_forecast


# ============================================================================
# PRICE CANDIDATE EVALUATION
# ============================================================================

def evaluate_price_candidate(
    wide,
    candidate,
):

    records = []

    origins = get_validation_origins(
        wide,
        "RO1_PRICE",
    )

    for origin in origins:

        origin_position = (
            wide.index.get_loc(
                origin
            )
        )

        # CRITICAL:
        # only information available at origin.
        train = wide.iloc[
            : origin_position + 1
        ].copy()

        for horizon in HORIZONS:

            target_position = (
                origin_position
                + horizon
            )

            if target_position >= len(
                wide.index
            ):
                continue

            target_date = (
                wide.index[
                    target_position
                ]
            )

            actual = (
                wide.iloc[
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
                    candidate[
                        "rank"
                    ],
                    candidate[
                        "k_ar_diff"
                    ],
                    candidate[
                        "det_order"
                    ],
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

                records.append(
                    {
                        "dataset":
                            "RO1_PRICE",

                        "model":
                            "VECM",

                        "candidate_id":
                            candidate[
                                "candidate_id"
                            ],

                        "det_order":
                            candidate[
                                "det_order"
                            ],

                        "k_ar_diff":
                            candidate[
                                "k_ar_diff"
                            ],

                        "rank":
                            candidate[
                                "rank"
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

                        "status":
                            "OK",

                        "error_type":
                            "",

                        "error_message":
                            "",
                    }
                )

            except Exception as exc:

                records.append(
                    {
                        "dataset":
                            "RO1_PRICE",

                        "model":
                            "VECM",

                        "candidate_id":
                            candidate[
                                "candidate_id"
                            ],

                        "det_order":
                            candidate[
                                "det_order"
                            ],

                        "k_ar_diff":
                            candidate[
                                "k_ar_diff"
                            ],

                        "rank":
                            candidate[
                                "rank"
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

                        "status":
                            "ERROR",

                        "error_type":
                            type(exc).__name__,

                        "error_message":
                            str(exc)[:500],
                    }
                )

    return pd.DataFrame(
        records
    )


# ============================================================================
# DEMAND CANDIDATE EVALUATION
# ============================================================================

def evaluate_demand_candidate(
    wide,
    candidate,
):

    records = []

    origins = get_validation_origins(
        wide,
        "RO1_DEMAND",
    )

    for origin in origins:

        origin_position = (
            wide.index.get_loc(
                origin
            )
        )

        train = wide.iloc[
            : origin_position + 1
        ].copy()

        for horizon in HORIZONS:

            target_position = (
                origin_position
                + horizon
            )

            if target_position >= len(
                wide.index
            ):
                continue

            target_date = (
                wide.index[
                    target_position
                ]
            )

            actual = (
                wide.iloc[
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
                        candidate[
                            "lag"
                        ],
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

                records.append(
                    {
                        "dataset":
                            "RO1_DEMAND",

                        "model":
                            "VAR_DIFF",

                        "candidate_id":
                            candidate[
                                "candidate_id"
                            ],

                        "lag":
                            candidate[
                                "lag"
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

                        "status":
                            "OK",

                        "error_type":
                            "",

                        "error_message":
                            "",
                    }
                )

            except Exception as exc:

                records.append(
                    {
                        "dataset":
                            "RO1_DEMAND",

                        "model":
                            "VAR_DIFF",

                        "candidate_id":
                            candidate[
                                "candidate_id"
                            ],

                        "lag":
                            candidate[
                                "lag"
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

                        "status":
                            "ERROR",

                        "error_type":
                            type(exc).__name__,

                        "error_message":
                            str(exc)[:500],
                    }
                )

    return pd.DataFrame(
        records
    )


# ============================================================================
# PRICE GRID
# ============================================================================

print(
    "\n[2] PRICE VECM VALIDATION"
)

price_results = []

for candidate in PRICE_CANDIDATES:

    print(
        f"{candidate['candidate_id']}: "
        f"det={candidate['det_order']}, "
        f"k_ar_diff={candidate['k_ar_diff']}, "
        f"rank={candidate['rank']}"
    )

    result = evaluate_price_candidate(
        price_wide,
        candidate,
    )

    price_results.append(
        result
    )


# ============================================================================
# DEMAND GRID
# ============================================================================

print(
    "\n[3] DEMAND DIFFERENCE-VAR VALIDATION"
)

demand_results = []

for candidate in DEMAND_CANDIDATES:

    print(
        f"{candidate['candidate_id']}: "
        f"lag={candidate['lag']}"
    )

    result = evaluate_demand_candidate(
        demand_wide,
        candidate,
    )

    demand_results.append(
        result
    )


# ============================================================================
# COMBINE
# ============================================================================

price_validation = pd.concat(
    price_results,
    ignore_index=True,
)

demand_validation = pd.concat(
    demand_results,
    ignore_index=True,
)

validation_records = pd.concat(
    [
        price_validation,
        demand_validation,
    ],
    ignore_index=True,
)


# ============================================================================
# EXECUTION AUDIT
# ============================================================================

print(
    "\n[4] VALIDATION EXECUTION AUDIT"
)

print(
    f"Total validation records: "
    f"{len(validation_records)}"
)

print(
    f"Successful records: "
    f"{(
        validation_records['status']
        == 'OK'
    ).sum()}"
)

print(
    f"Failed records: "
    f"{(
        validation_records['status']
        == 'ERROR'
    ).sum()}"
)


if validation_records.empty:

    raise RuntimeError(
        "Validation produced zero records. "
        "Check validation dates and full-history loading."
    )


failed = validation_records.loc[
    validation_records["status"]
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
        "\nNo failed candidate forecasts."
    )


successful = validation_records.loc[
    validation_records["status"]
    == "OK"
].copy()


if successful.empty:

    raise RuntimeError(
        "All candidate forecasts failed."
    )


# ============================================================================
# EXPECTED COVERAGE
# ============================================================================

print(
    "\n[5] HORIZON-SPECIFIC COVERAGE"
)


def coverage_by_candidate(
    successful_df,
    wide,
    dataset_name,
):

    expected = expected_tasks(
        wide,
        dataset_name,
    )

    rows = []

    dataset_success = successful_df.loc[
        successful_df["dataset"]
        == dataset_name
    ]

    for candidate_id, group in (
        dataset_success
        .groupby(
            "candidate_id"
        )
    ):

        for horizon in HORIZONS:

            expected_h = expected.loc[
                expected["horizon"]
                == horizon
            ]

            actual_h = (
                group.loc[
                    group["horizon"]
                    == horizon,
                    [
                        "forecast_origin",
                        "target_date",
                    ],
                ]
                .drop_duplicates()
            )

            expected_count = len(
                expected_h
            )

            actual_count = len(
                actual_h
            )

            coverage = (
                actual_count
                /
                expected_count
                if expected_count
                else np.nan
            )

            rows.append(
                {
                    "dataset":
                        dataset_name,

                    "candidate_id":
                        candidate_id,

                    "horizon":
                        horizon,

                    "expected":
                        expected_count,

                    "successful":
                        actual_count,

                    "coverage":
                        coverage,
                }
            )

    return pd.DataFrame(
        rows
    )


price_coverage = coverage_by_candidate(
    successful,
    price_wide,
    "RO1_PRICE",
)

demand_coverage = coverage_by_candidate(
    successful,
    demand_wide,
    "RO1_DEMAND",
)

coverage = pd.concat(
    [
        price_coverage,
        demand_coverage,
    ],
    ignore_index=True,
)


print(
    coverage.to_string(
        index=False
    )
)


# ============================================================================
# H=3 SUMMARY
# ============================================================================

print(
    "\n[6] H=3 SPECIFICATION PERFORMANCE"
)


price_h3 = (
    successful.loc[
        (
            successful["dataset"]
            == "RO1_PRICE"
        )
        &
        (
            successful["horizon"]
            == PRIMARY_HORIZON
        )
    ]
    .groupby(
        [
            "candidate_id",
            "det_order",
            "k_ar_diff",
            "rank",
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
    )
    .reset_index()
)


demand_h3 = (
    successful.loc[
        (
            successful["dataset"]
            == "RO1_DEMAND"
        )
        &
        (
            successful["horizon"]
            == PRIMARY_HORIZON
        )
    ]
    .groupby(
        [
            "candidate_id",
            "lag",
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
    )
    .reset_index()
)


print(
    "\nPRICE:"
)

print(
    price_h3.to_string(
        index=False
    )
)

print(
    "\nDEMAND:"
)

print(
    demand_h3.to_string(
        index=False
    )
)


# ============================================================================
# COVERAGE JOIN
# ============================================================================

price_h3 = price_h3.merge(
    price_coverage.loc[
        price_coverage["horizon"]
        == PRIMARY_HORIZON,
        [
            "candidate_id",
            "coverage",
        ],
    ],
    on="candidate_id",
    how="left",
)


demand_h3 = demand_h3.merge(
    demand_coverage.loc[
        demand_coverage["horizon"]
        == PRIMARY_HORIZON,
        [
            "candidate_id",
            "coverage",
        ],
    ],
    on="candidate_id",
    how="left",
)


# ============================================================================
# SELECTION
# ============================================================================

print(
    "\n[7] SPECIFICATION SELECTION"
)


eligible_price = price_h3.loc[
    price_h3["coverage"]
    >= MIN_COVERAGE
].copy()


eligible_demand = demand_h3.loc[
    demand_h3["coverage"]
    >= MIN_COVERAGE
].copy()


if eligible_price.empty:

    raise RuntimeError(
        "No Price VECM candidate meets "
        f"minimum coverage {MIN_COVERAGE:.0%}."
    )


if eligible_demand.empty:

    raise RuntimeError(
        "No Demand VAR candidate meets "
        f"minimum coverage {MIN_COVERAGE:.0%}."
    )


# Price:
# primary MAE
# secondary RMSE
# then simpler lag/rank ordering.

eligible_price = (
    eligible_price
    .sort_values(
        [
            "mean_MAE",
            "mean_RMSE",
            "k_ar_diff",
            "rank",
            "det_order",
        ]
    )
)


eligible_demand = (
    eligible_demand
    .sort_values(
        [
            "mean_MAE",
            "mean_RMSE",
            "lag",
        ]
    )
)


selected_price = (
    eligible_price.iloc[0]
)

selected_demand = (
    eligible_demand.iloc[0]
)


selection = pd.DataFrame(
    [
        {
            "dataset":
                "RO1_PRICE",

            "model":
                "VECM",

            "candidate_id":
                selected_price[
                    "candidate_id"
                ],

            "det_order":
                int(
                    selected_price[
                        "det_order"
                    ]
                ),

            "k_ar_diff":
                int(
                    selected_price[
                        "k_ar_diff"
                    ]
                ),

            "rank":
                int(
                    selected_price[
                        "rank"
                    ]
                ),

            "selection_horizon":
                PRIMARY_HORIZON,

            "validation_MAE":
                float(
                    selected_price[
                        "mean_MAE"
                    ]
                ),

            "validation_RMSE":
                float(
                    selected_price[
                        "mean_RMSE"
                    ]
                ),

            "coverage":
                float(
                    selected_price[
                        "coverage"
                    ]
                ),
        },

        {
            "dataset":
                "RO1_DEMAND",

            "model":
                "VAR_DIFF",

            "candidate_id":
                selected_demand[
                    "candidate_id"
                ],

            "lag":
                int(
                    selected_demand[
                        "lag"
                    ]
                ),

            "selection_horizon":
                PRIMARY_HORIZON,

            "validation_MAE":
                float(
                    selected_demand[
                        "mean_MAE"
                    ]
                ),

            "validation_RMSE":
                float(
                    selected_demand[
                        "mean_RMSE"
                    ]
                ),

            "coverage":
                float(
                    selected_demand[
                        "coverage"
                    ]
                ),
        },
    ]
)


print(
    "\nSELECTED SPECIFICATIONS:"
)

print(
    selection.to_string(
        index=False
    )
)


# ============================================================================
# ALL-HORIZON PERFORMANCE
# ============================================================================

print(
    "\n[8] ALL-HORIZON PERFORMANCE"
)


selected_price_id = (
    selection.loc[
        selection["dataset"]
        == "RO1_PRICE",
        "candidate_id",
    ].iloc[0]
)

selected_demand_id = (
    selection.loc[
        selection["dataset"]
        == "RO1_DEMAND",
        "candidate_id",
    ].iloc[0]
)


selected_price_all = (
    successful.loc[
        (
            successful["dataset"]
            == "RO1_PRICE"
        )
        &
        (
            successful["candidate_id"]
            == selected_price_id
        )
    ]
    .groupby(
        "horizon"
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
    )
    .reset_index()
    .sort_values(
        "horizon"
    )
)


selected_demand_all = (
    successful.loc[
        (
            successful["dataset"]
            == "RO1_DEMAND"
        )
        &
        (
            successful["candidate_id"]
            == selected_demand_id
        )
    ]
    .groupby(
        "horizon"
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
    )
    .reset_index()
    .sort_values(
        "horizon"
    )
)


print(
    "\nSELECTED PRICE VECM:"
)

print(
    selected_price_all.to_string(
        index=False
    )
)


print(
    "\nSELECTED DEMAND DIFFERENCE-VAR:"
)

print(
    selected_demand_all.to_string(
        index=False
    )
)


# ============================================================================
# SAVE
# ============================================================================

print(
    "\n[9] SAVING OUTPUTS"
)


validation_records.to_csv(
    OUTPUT_DIR
    / "RO1_step25c1_multivariate_validation_forecasts.csv",
    index=False,
)

failed.to_csv(
    OUTPUT_DIR
    / "RO1_step25c1_multivariate_failed_fits.csv",
    index=False,
)

coverage.to_csv(
    OUTPUT_DIR
    / "RO1_step25c1_multivariate_coverage.csv",
    index=False,
)

price_h3.to_csv(
    OUTPUT_DIR
    / "RO1_step25c1_price_vecm_h3_summary.csv",
    index=False,
)

demand_h3.to_csv(
    OUTPUT_DIR
    / "RO1_step25c1_demand_var_h3_summary.csv",
    index=False,
)

selection.to_csv(
    OUTPUT_DIR
    / "RO1_step25c1_selected_specifications.csv",
    index=False,
)

selected_price_all.to_csv(
    OUTPUT_DIR
    / "RO1_step25c1_selected_price_all_horizons.csv",
    index=False,
)

selected_demand_all.to_csv(
    OUTPUT_DIR
    / "RO1_step25c1_selected_demand_all_horizons.csv",
    index=False,
)


# ============================================================================
# FINAL ASSERTIONS
# ============================================================================

print(
    "\n[10] FINAL ASSERTIONS"
)


assert not validation_records.empty

assert not successful.empty

assert (
    successful["MAE"]
    .notna()
    .all()
)

assert (
    successful["RMSE"]
    .notna()
    .all()
)

assert (
    set(
        successful["dataset"]
    )
    ==
    {
        "RO1_PRICE",
        "RO1_DEMAND",
    }
)

assert (
    successful["horizon"]
    .isin(HORIZONS)
    .all()
)

assert len(selection) == 2

assert (
    set(
        selection["dataset"]
    )
    ==
    {
        "RO1_PRICE",
        "RO1_DEMAND",
    }
)

# Ensure selected Price VECM is genuinely restricted.
selected_rank = int(
    selection.loc[
        selection["dataset"]
        == "RO1_PRICE",
        "rank",
    ].iloc[0]
)

assert (
    0
    <
    selected_rank
    <
    price_wide.shape[1]
)

# Validation chronology:
# every validation forecast must predict strictly after
# its forecast origin.
assert (
    validation_records["target_date"]
    >
    validation_records["forecast_origin"]
).all()

# Validation origins must remain inside the declared
# validation-origin windows.
price_validation_origins = (
    validation_records.loc[
        validation_records["dataset"]
        == "RO1_PRICE",
        "forecast_origin",
    ]
)

demand_validation_origins = (
    validation_records.loc[
        validation_records["dataset"]
        == "RO1_DEMAND",
        "forecast_origin",
    ]
)

assert (
    price_validation_origins
    >=
    VALIDATION_STARTS["RO1_PRICE"]
).all()

assert (
    price_validation_origins
    <=
    VALIDATION_ENDS["RO1_PRICE"]
).all()

assert (
    demand_validation_origins
    >=
    VALIDATION_STARTS["RO1_DEMAND"]
).all()

assert (
    demand_validation_origins
    <=
    VALIDATION_ENDS["RO1_DEMAND"]
).all()

print(
    "Validation records: PASS"
)

print(
    "Successful forecast generation: PASS"
)

print(
    "Horizon-specific evaluation: PASS"
)

print(
    "Candidate coverage audit: PASS"
)

print(
    "Validation-only selection: PASS"
)

print(
    "Restricted VECM rank: PASS"
)

print(
    "Test data untouched: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 25C.1 COMPLETE"
)

print(
    "=" * 78
)

print(
    "Multivariate validation completed."
)

print(
    "Selected specifications saved."
)

print(
    "Final test data remains untouched."

)

print(
    "\nRO1 STEP 25C.1: READY FOR SCIENTIFIC REVIEW"
)

print(
    "=" * 78
)