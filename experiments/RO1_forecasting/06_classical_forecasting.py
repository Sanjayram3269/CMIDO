"""
CMIDO — RO1 STEP 24
Classical Statistical Forecasting

Models
------
ETS family:
    1. ETS_A_N_N
    2. ETS_AAd_N
    3. ETS_AAd_A

SARIMA:
    Compact candidate family selected using development data only.

Evaluation
----------
- Horizons: 1, 3, 6, 12 months
- Expanding-window rolling-origin evaluation
- Validation + test
- MAE primary
- RMSE, sMAPE, MAPE secondary
- No random split
- Test data never used for model specification selection

Important
---------
For each series and forecast origin, each model is fitted once
and produces a 12-month forecast. Required horizons are then
extracted from that single forecast path.
"""

from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd

from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX


# ============================================================================
# PROJECT PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / "src"),
)

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

TABLE_DIR = (
    ROOT
    / "results"
    / "forecasting"
    / "tables"
)

OUTPUT_DIR = (
    ROOT
    / "results"
    / "forecasting"
    / "classical"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

HORIZONS = (
    1,
    3,
    6,
    12,
)

MAX_HORIZON = max(HORIZONS)

SEASONAL_PERIOD = 12

MIN_TRAINING_MONTHS = 60

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
)

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
)


# ============================================================================
# HEADER
# ============================================================================

print("=" * 78)
print("CMIDO RO1 — STEP 24")
print("CLASSICAL STATISTICAL FORECASTING")
print("=" * 78)


# ============================================================================
# DATA LOADING
# ============================================================================

print("\n[1] LOADING DATA")

price = pd.read_csv(
    PRICE_DATA,
    parse_dates=["date"],
)

demand = pd.read_csv(
    DEMAND_DATA,
    parse_dates=["date"],
)


# ============================================================================
# STANDARDIZATION
# ============================================================================

def standardize_data(
    df: pd.DataFrame,
) -> pd.DataFrame:

    rename_map = {
        "DataSeries": "series",
        "price_dollars_per_tonne": "value",
        "demand_thousand_tonnes": "value",
    }

    work = df.rename(
        columns=rename_map
    ).copy()

    work = work[
        [
            "date",
            "series",
            "value",
        ]
    ]

    work["date"] = (
        pd.to_datetime(work["date"])
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

    return (
        work
        .sort_values(
            [
                "series",
                "date",
            ]
        )
        .reset_index(drop=True)
    )


price = standardize_data(price)
demand = standardize_data(demand)

print(
    f"Price observations : {len(price)}"
)

print(
    f"Demand observations: {len(demand)}"
)


# ============================================================================
# TASK LOADING
# ============================================================================

TASK_FILES = {
    "price_validation":
        TABLE_DIR / "RO1_price_validation_tasks.csv",

    "price_test":
        TABLE_DIR / "RO1_price_test_tasks.csv",

    "demand_validation":
        TABLE_DIR / "RO1_demand_validation_tasks.csv",

    "demand_test":
        TABLE_DIR / "RO1_demand_test_tasks.csv",
}


def load_tasks(path: Path) -> pd.DataFrame:

    if not path.exists():
        raise FileNotFoundError(
            f"Required task file missing:\n{path}"
        )

    tasks = pd.read_csv(
        path,
        parse_dates=[
            "forecast_origin",
            "target_date",
        ],
    )

    required = {
        "series",
        "forecast_origin",
        "target_date",
        "horizon",
        "split",
    }

    missing = (
        required
        - set(tasks.columns)
    )

    if missing:
        raise ValueError(
            f"{path.name} missing columns: "
            f"{sorted(missing)}"
        )

    tasks["horizon"] = (
        tasks["horizon"]
        .astype(int)
    )

    return (
        tasks
        .sort_values(
            [
                "series",
                "forecast_origin",
                "horizon",
            ]
        )
        .reset_index(drop=True)
    )


price_validation_tasks = load_tasks(
    TASK_FILES["price_validation"]
)

price_test_tasks = load_tasks(
    TASK_FILES["price_test"]
)

demand_validation_tasks = load_tasks(
    TASK_FILES["demand_validation"]
)

demand_test_tasks = load_tasks(
    TASK_FILES["demand_test"]
)


print("\n[2] TASK COUNTS")

print(
    f"Price validation : {len(price_validation_tasks)}"
)

print(
    f"Price test       : {len(price_test_tasks)}"
)

print(
    f"Demand validation: {len(demand_validation_tasks)}"
)

print(
    f"Demand test      : {len(demand_test_tasks)}"
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
                actual - predicted
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
                (actual - predicted) ** 2
            )
        )
    )


def smape(
    actual,
    predicted,
):
    denominator = (
        np.abs(actual)
        + np.abs(predicted)
    )

    values = np.where(
        denominator == 0,
        0.0,
        2.0
        * np.abs(
            actual - predicted
        )
        / denominator,
    )

    return float(
        np.mean(values) * 100
    )


def mape(
    actual,
    predicted,
):
    values = np.where(
        actual == 0,
        np.nan,
        np.abs(
            (actual - predicted)
            / actual
        ),
    )

    return float(
        np.nanmean(values) * 100
    )


# ============================================================================
# ETS SPECIFICATIONS
# ============================================================================

ETS_SPECS = {
    "ETS_A_N_N": {
        "trend": None,
        "damped_trend": False,
        "seasonal": None,
    },

    "ETS_AAd_N": {
        "trend": "add",
        "damped_trend": True,
        "seasonal": None,
    },

    "ETS_AAd_A": {
        "trend": "add",
        "damped_trend": True,
        "seasonal": "add",
    },
}


# ============================================================================
# SARIMA CANDIDATES
# ============================================================================

SARIMA_CANDIDATES = [
    {
        "order": (0, 1, 1),
        "seasonal_order": (0, 1, 1, 12),
    },

    {
        "order": (1, 1, 0),
        "seasonal_order": (0, 1, 1, 12),
    },

    {
        "order": (1, 1, 1),
        "seasonal_order": (0, 1, 1, 12),
    },

    {
        "order": (0, 1, 1),
        "seasonal_order": (1, 1, 0, 12),
    },

    {
        "order": (1, 1, 0),
        "seasonal_order": (1, 1, 0, 12),
    },
]


# ============================================================================
# DEVELOPMENT MODEL SELECTION
# ============================================================================

def fit_ets_development(
    y,
):
    """
    Select ETS specification using development data only.

    Selection criterion:
        AIC

    The selected specification is then frozen for all
    rolling-origin validation and test forecasts.
    """

    results = []

    for name, spec in ETS_SPECS.items():

        try:

            model = ExponentialSmoothing(
                y,
                trend=spec["trend"],
                damped_trend=spec[
                    "damped_trend"
                ],
                seasonal=spec["seasonal"],
                seasonal_periods=(
                    SEASONAL_PERIOD
                    if spec["seasonal"]
                    is not None
                    else None
                ),
                initialization_method="estimated",
            )

            fitted = model.fit(
                optimized=True,
            )

            results.append(
                {
                    "model": name,
                    "aic": float(
                        fitted.aic
                    ),
                    "status": "OK",
                }
            )

        except Exception as exc:

            results.append(
                {
                    "model": name,
                    "aic": np.inf,
                    "status": (
                        f"FAILED: {type(exc).__name__}"
                    ),
                }
            )

    result_df = pd.DataFrame(
        results
    )

    valid = result_df.loc[
        np.isfinite(
            result_df["aic"]
        )
    ]

    if valid.empty:
        raise RuntimeError(
            "No ETS specification successfully "
            "fit development data."
        )

    best = valid.sort_values(
        "aic"
    ).iloc[0]

    return (
        str(best["model"]),
        result_df,
    )


def fit_sarima_development(
    y,
):
    """
    Select SARIMA order using development data only.

    A compact pre-specified candidate family is used.
    No test observations enter specification selection.
    """

    results = []

    for candidate in SARIMA_CANDIDATES:

        order = candidate["order"]

        seasonal_order = (
            candidate[
                "seasonal_order"
            ]
        )

        try:

            model = SARIMAX(
                y,
                order=order,
                seasonal_order=seasonal_order,
                trend=None,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )

            fitted = model.fit(
                disp=False,
                maxiter=200,
            )

            results.append(
                {
                    "order": str(order),
                    "seasonal_order":
                        str(seasonal_order),
                    "aic": float(
                        fitted.aic
                    ),
                    "status": "OK",
                }
            )

        except Exception as exc:

            results.append(
                {
                    "order": str(order),
                    "seasonal_order":
                        str(seasonal_order),
                    "aic": np.inf,
                    "status":
                        f"FAILED: {type(exc).__name__}",
                }
            )

    result_df = pd.DataFrame(
        results
    )

    valid = result_df.loc[
        np.isfinite(
            result_df["aic"]
        )
    ]

    if valid.empty:
        raise RuntimeError(
            "No SARIMA specification successfully "
            "fit development data."
        )

    best = valid.sort_values(
        "aic"
    ).iloc[0]

    best_order = eval(
        best["order"]
    )

    best_seasonal_order = eval(
        best["seasonal_order"]
    )

    return (
        best_order,
        best_seasonal_order,
        result_df,
    )


# ============================================================================
# DEVELOPMENT DATA LIMITS
# ============================================================================

def development_end_for_dataset(
    dataset_name,
):
    if dataset_name == "RO1_PRICE":
        return pd.Timestamp(
            "2022-06-01"
        )

    if dataset_name == "RO1_DEMAND":
        return pd.Timestamp(
            "2022-05-01"
        )

    raise ValueError(
        f"Unknown dataset: {dataset_name}"
    )


# ============================================================================
# MODEL SPECIFICATION SELECTION
# ============================================================================

def select_model_specifications(
    data,
    dataset_name,
):
    """
    Select ETS and SARIMA specifications separately
    for every material using development data only.
    """

    development_end = (
        development_end_for_dataset(
            dataset_name
        )
    )

    records = []
    selection_details = []

    for series_name, group in data.groupby(
        "series",
        sort=True,
    ):

        y = (
            group.loc[
                group["date"]
                <= development_end,
                "value",
            ]
            .astype(float)
            .to_numpy()
        )

        if len(y) < MIN_TRAINING_MONTHS:
            raise ValueError(
                f"Insufficient development observations "
                f"for {dataset_name} / {series_name}: "
                f"{len(y)}"
            )

        print(
            f"  Selecting specifications: "
            f"{dataset_name} / {series_name}"
        )

        # ETS
        best_ets, ets_details = (
            fit_ets_development(y)
        )

        # SARIMA
        (
            best_order,
            best_seasonal_order,
            sarima_details,
        ) = fit_sarima_development(y)

        records.extend(
            [
                {
                    "dataset":
                        dataset_name,
                    "series":
                        series_name,
                    "model_family":
                        "ETS",
                    "selected_model":
                        best_ets,
                    "order":
                        "",
                    "seasonal_order":
                        "",
                    "selection_method":
                        "Development AIC",
                },
                {
                    "dataset":
                        dataset_name,
                    "series":
                        series_name,
                    "model_family":
                        "SARIMA",
                    "selected_model":
                        "SARIMA",
                    "order":
                        str(best_order),
                    "seasonal_order":
                        str(
                            best_seasonal_order
                        ),
                    "selection_method":
                        "Development AIC",
                },
            ]
        )

        selection_details.append(
            {
                "dataset":
                    dataset_name,
                "series":
                    series_name,
                "ets_details":
                    ets_details.to_dict(
                        orient="records"
                    ),
                "sarima_details":
                    sarima_details.to_dict(
                        orient="records"
                    ),
            }
        )

    return (
        pd.DataFrame(records),
        selection_details,
    )


# ============================================================================
# FIT + FORECAST ETS
# ============================================================================

def forecast_ets(
    y,
    model_name,
):
    spec = ETS_SPECS[
        model_name
    ]

    model = ExponentialSmoothing(
        y,
        trend=spec["trend"],
        damped_trend=spec[
            "damped_trend"
        ],
        seasonal=spec["seasonal"],
        seasonal_periods=(
            SEASONAL_PERIOD
            if spec["seasonal"]
            is not None
            else None
        ),
        initialization_method="estimated",
    )

    fitted = model.fit(
        optimized=True,
    )

    forecast = fitted.forecast(
        MAX_HORIZON
    )

    return np.asarray(
        forecast,
        dtype=float,
    )


# ============================================================================
# FIT + FORECAST SARIMA
# ============================================================================

def forecast_sarima(
    y,
    order,
    seasonal_order,
):
    model = SARIMAX(
        y,
        order=order,
        seasonal_order=seasonal_order,
        trend=None,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )

    fitted = model.fit(
        disp=False,
        maxiter=200,
    )

    forecast = fitted.forecast(
        MAX_HORIZON
    )

    return np.asarray(
        forecast,
        dtype=float,
    )


# ============================================================================
# BUILD SPECIFICATION LOOKUP
# ============================================================================

def build_spec_lookup(
    selection_df,
):
    lookup = {}

    for row in selection_df.itertuples(
        index=False
    ):

        key = (
            row.dataset,
            row.series,
            row.model_family,
        )

        lookup[key] = row

    return lookup


# ============================================================================
# ROLLING-ORIGIN FORECAST GENERATION
# ============================================================================

def evaluate_classical_models(
    data,
    tasks,
    dataset_name,
    spec_lookup,
):
    """
    For each unique series/origin:
        fit each frozen classical specification once,
        forecast 12 months,
        extract h = 1,3,6,12.
    """

    records = []

    groups = {
        name:
            group.sort_values("date")
            .reset_index(drop=True)
        for name, group
        in data.groupby(
            "series",
            sort=True,
        )
    }

    unique_task_origins = (
        tasks[
            [
                "series",
                "forecast_origin",
                "split",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "series",
                "forecast_origin",
            ]
        )
    )

    total_origins = (
        len(unique_task_origins)
    )

    completed = 0

    for task_info in (
        unique_task_origins.itertuples(
            index=False
        )
    ):

        series_name = (
            str(task_info.series)
        )

        origin = pd.Timestamp(
            task_info.forecast_origin
        )

        split = str(
            task_info.split
        )

        series_data = groups[
            series_name
        ]

        history = series_data.loc[
            series_data["date"]
            <= origin
        ]

        y = (
            history["value"]
            .astype(float)
            .to_numpy()
        )

        if len(y) < MIN_TRAINING_MONTHS:
            raise ValueError(
                "Insufficient training history:\n"
                f"{dataset_name}\n"
                f"{series_name}\n"
                f"{origin}\n"
                f"n={len(y)}"
            )

        # ------------------------------------------------------------
        # Fit ETS
        # ------------------------------------------------------------

        ets_spec = spec_lookup[
            (
                dataset_name,
                series_name,
                "ETS",
            )
        ]

        ets_name = (
            ets_spec.selected_model
        )

        try:

            ets_forecast = forecast_ets(
                y,
                ets_name,
            )

        except Exception as exc:

            print(
                "\nWARNING: ETS fit failed"
            )

            print(
                dataset_name,
                series_name,
                origin,
                ets_name,
                type(exc).__name__,
            )

            ets_forecast = np.full(
                MAX_HORIZON,
                np.nan,
            )

        # ------------------------------------------------------------
        # Fit SARIMA
        # ------------------------------------------------------------

        sarima_spec = spec_lookup[
            (
                dataset_name,
                series_name,
                "SARIMA",
            )
        ]

        sarima_order = eval(
            sarima_spec.order
        )

        sarima_seasonal_order = eval(
            sarima_spec.seasonal_order
        )

        try:

            sarima_forecast = (
                forecast_sarima(
                    y,
                    sarima_order,
                    sarima_seasonal_order,
                )
            )

        except Exception as exc:

            print(
                "\nWARNING: SARIMA fit failed"
            )

            print(
                dataset_name,
                series_name,
                origin,
                sarima_order,
                sarima_seasonal_order,
                type(exc).__name__,
            )

            sarima_forecast = np.full(
                MAX_HORIZON,
                np.nan,
            )

        # ------------------------------------------------------------
        # Extract requested horizons
        # ------------------------------------------------------------

        origin_tasks = tasks.loc[
            (
                tasks["series"]
                == series_name
            )
            &
            (
                tasks["forecast_origin"]
                == origin
            )
            &
            (
                tasks["split"]
                == split
            )
        ].copy()

        for row in origin_tasks.itertuples(
            index=False
        ):

            horizon = int(
                row.horizon
            )

            target = pd.Timestamp(
                row.target_date
            )

            actual_rows = series_data.loc[
                series_data["date"]
                == target
            ]

            if len(actual_rows) != 1:
                raise ValueError(
                    "Missing unique actual target:\n"
                    f"{dataset_name}\n"
                    f"{series_name}\n"
                    f"{target}"
                )

            actual = float(
                actual_rows.iloc[0]["value"]
            )

            # zero-based index
            idx = horizon - 1

            predictions = {
                "ETS": (
                    ets_forecast[idx]
                ),
                "SARIMA": (
                    sarima_forecast[idx]
                ),
            }

            for model_name, prediction in (
                predictions.items()
            ):

                records.append(
                    {
                        "dataset":
                            dataset_name,
                        "series":
                            series_name,
                        "forecast_origin":
                            origin,
                        "target_date":
                            target,
                        "horizon":
                            horizon,
                        "split":
                            split,
                        "model":
                            model_name,
                        "prediction":
                            float(prediction)
                            if np.isfinite(
                                prediction
                            )
                            else np.nan,
                        "actual":
                            actual,
                    }
                )

        completed += 1

        if (
            completed == 1
            or completed % 10 == 0
            or completed == total_origins
        ):
            print(
                f"    {completed:>3}/"
                f"{total_origins} origins"
            )

    return pd.DataFrame(
        records
    )


# ============================================================================
# METRIC TABLE
# ============================================================================

def calculate_metrics(
    forecasts,
):
    records = []

    grouped = forecasts.groupby(
        [
            "dataset",
            "split",
            "series",
            "horizon",
            "model",
        ],
        sort=True,
    )

    for keys, group in grouped:

        valid = group.loc[
            group["prediction"].notna()
        ]

        if valid.empty:
            records.append(
                {
                    "dataset":
                        keys[0],
                    "split":
                        keys[1],
                    "series":
                        keys[2],
                    "horizon":
                        int(keys[3]),
                    "model":
                        keys[4],
                    "n_forecasts":
                        0,
                    "MAE":
                        np.nan,
                    "RMSE":
                        np.nan,
                    "sMAPE_percent":
                        np.nan,
                    "MAPE_percent":
                        np.nan,
                }
            )

            continue

        actual = (
            valid["actual"]
            .to_numpy(
                dtype=float
            )
        )

        predicted = (
            valid["prediction"]
            .to_numpy(
                dtype=float
            )
        )

        records.append(
            {
                "dataset":
                    keys[0],
                "split":
                    keys[1],
                "series":
                    keys[2],
                "horizon":
                    int(keys[3]),
                "model":
                    keys[4],
                "n_forecasts":
                    len(valid),
                "MAE":
                    mae(
                        actual,
                        predicted,
                    ),
                "RMSE":
                    rmse(
                        actual,
                        predicted,
                    ),
                "sMAPE_percent":
                    smape(
                        actual,
                        predicted,
                    ),
                "MAPE_percent":
                    mape(
                        actual,
                        predicted,
                    ),
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================================
# PROCESS ONE DATASET
# ============================================================================

def run_dataset(
    data,
    tasks_validation,
    tasks_test,
    dataset_name,
):
    print(
        "\n" + "-" * 78
    )

    print(
        f"DATASET: {dataset_name}"
    )

    print(
        "-" * 78
    )

    # ------------------------------------------------------------
    # Select specifications on development data only
    # ------------------------------------------------------------

    print(
        "\n[3] DEVELOPMENT-ONLY MODEL SELECTION"
    )

    (
        selection_df,
        selection_details,
    ) = select_model_specifications(
        data,
        dataset_name,
    )

    # ------------------------------------------------------------
    # Print selected models
    # ------------------------------------------------------------

    print(
        "\nSelected specifications:"
    )

    print(
        selection_df.to_string(
            index=False
        )
    )

    # ------------------------------------------------------------
    # Rolling validation
    # ------------------------------------------------------------

    print(
        "\n[4] VALIDATION FORECASTING"
    )

    validation = (
        evaluate_classical_models(
            data,
            tasks_validation,
            dataset_name,
            build_spec_lookup(
                selection_df
            ),
        )
    )

    # ------------------------------------------------------------
    # Rolling test
    # ------------------------------------------------------------

    print(
        "\n[5] TEST FORECASTING"
    )

    test = (
        evaluate_classical_models(
            data,
            tasks_test,
            dataset_name,
            build_spec_lookup(
                selection_df
            ),
        )
    )

    forecasts = pd.concat(
        [
            validation,
            test,
        ],
        ignore_index=True,
    )

    return (
        forecasts,
        selection_df,
        selection_details,
    )


# ============================================================================
# RUN PRICE
# ============================================================================

(
    price_forecasts,
    price_selection,
    price_selection_details,
) = run_dataset(
    price,
    price_validation_tasks,
    price_test_tasks,
    "RO1_PRICE",
)


# ============================================================================
# RUN DEMAND
# ============================================================================

(
    demand_forecasts,
    demand_selection,
    demand_selection_details,
) = run_dataset(
    demand,
    demand_validation_tasks,
    demand_test_tasks,
    "RO1_DEMAND",
)


# ============================================================================
# COMBINE
# ============================================================================

print(
    "\n[6] COMBINING RESULTS"
)

all_forecasts = pd.concat(
    [
        price_forecasts,
        demand_forecasts,
    ],
    ignore_index=True,
)

all_selection = pd.concat(
    [
        price_selection,
        demand_selection,
    ],
    ignore_index=True,
)

metrics = calculate_metrics(
    all_forecasts
)


# ============================================================================
# VALIDATION / TEST TABLES
# ============================================================================

validation_metrics = (
    metrics.loc[
        metrics["split"]
        == "validation"
    ]
    .sort_values(
        [
            "dataset",
            "series",
            "horizon",
            "MAE",
        ]
    )
    .reset_index(drop=True)
)

test_metrics = (
    metrics.loc[
        metrics["split"]
        == "test"
    ]
    .sort_values(
        [
            "dataset",
            "series",
            "horizon",
            "MAE",
        ]
    )
    .reset_index(drop=True)
)


# ============================================================================
# SAVE
# ============================================================================

print(
    "\n[7] SAVING OUTPUTS"
)

all_forecasts.to_csv(
    OUTPUT_DIR
    / "RO1_step24_classical_forecasts.csv",
    index=False,
)

metrics.to_csv(
    OUTPUT_DIR
    / "RO1_step24_classical_metrics.csv",
    index=False,
)

validation_metrics.to_csv(
    OUTPUT_DIR
    / "RO1_step24_validation_metrics.csv",
    index=False,
)

test_metrics.to_csv(
    OUTPUT_DIR
    / "RO1_step24_test_metrics.csv",
    index=False,
)

all_selection.to_csv(
    OUTPUT_DIR
    / "RO1_step24_selected_specifications.csv",
    index=False,
)


# ============================================================================
# CONSOLE RESULTS
# ============================================================================

print(
    "\n[8] SELECTED MODEL SPECIFICATIONS"
)

print(
    all_selection.to_string(
        index=False
    )
)


print(
    "\n[9] VALIDATION PERFORMANCE"
)

print(
    validation_metrics[
        [
            "dataset",
            "series",
            "horizon",
            "model",
            "n_forecasts",
            "MAE",
            "RMSE",
            "sMAPE_percent",
            "MAPE_percent",
        ]
    ].to_string(
        index=False
    )
)


print(
    "\n[10] TEST PERFORMANCE"
)

print(
    test_metrics[
        [
            "dataset",
            "series",
            "horizon",
            "model",
            "n_forecasts",
            "MAE",
            "RMSE",
            "sMAPE_percent",
            "MAPE_percent",
        ]
    ].to_string(
        index=False
    )
)


# ============================================================================
# ASSERTIONS
# ============================================================================

print(
    "\n[11] FINAL ASSERTIONS"
)

if set(
    all_forecasts["model"].unique()
) != {
    "ETS",
    "SARIMA",
}:

    raise AssertionError(
        "Classical model coverage failed."
    )


if set(
    all_forecasts["horizon"].unique()
) != set(HORIZONS):

    raise AssertionError(
        "Horizon coverage failed."
    )


if set(
    all_forecasts["split"].unique()
) != {
    "validation",
    "test",
}:

    raise AssertionError(
        "Validation/test coverage failed."
    )


expected_task_count = (
    len(price_validation_tasks)
    + len(price_test_tasks)
    + len(demand_validation_tasks)
    + len(demand_test_tasks)
)

expected_forecast_count = (
    expected_task_count * 2
)

if len(all_forecasts) != (
    expected_forecast_count
):

    raise AssertionError(
        "Unexpected number of classical forecasts.\n"
        f"Expected: {expected_forecast_count}\n"
        f"Actual: {len(all_forecasts)}"
    )


duplicate_mask = (
    all_forecasts.duplicated(
        subset=[
            "dataset",
            "series",
            "forecast_origin",
            "target_date",
            "horizon",
            "split",
            "model",
        ],
        keep=False,
    )
)

if duplicate_mask.any():

    raise AssertionError(
        "Duplicate classical forecast records detected."
    )


print(
    "Model coverage: PASS"
)

print(
    "Horizon coverage: PASS"
)

print(
    "Validation/test coverage: PASS"
)

print(
    "Forecast count: PASS"
)

print(
    "Duplicate protection: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 24 COMPLETE"
)

print(
    "=" * 78
)

print(
    "ETS forecasting       : READY"
)

print(
    "SARIMA forecasting    : READY"
)

print(
    "Development selection : FROZEN"
)

print(
    "Validation metrics    : SAVED"
)

print(
    "Test metrics          : SAVED"
)

print(
    "\nRO1 STEP 24 CLASSICAL MODELS: READY"
)

print(
    "=" * 78
)