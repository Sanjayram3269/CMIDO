"""
CMIDO — RO1 STEP 23
Naïve and Seasonal Naïve Forecasting Baselines

Purpose
-------
Establish transparent forecasting baselines before introducing
statistical and machine-learning models.

Models
------
1. Naïve:
       forecast(t+h) = y(t)

2. Seasonal Naïve:
       forecast(t+h) = y(t+h-12)

Evaluation
----------
- Horizons: 1, 3, 6, 12 months
- Expanding-window rolling-origin tasks generated in Step 22
- Validation and test splits
- Primary metric: MAE
- Secondary metrics: RMSE, sMAPE, MAPE

Important
---------
The Step 22 task definitions are treated as authoritative.
No random splitting is used.
No observations are removed or modified.
"""


# ============================================================================
# IMPORTS
# ============================================================================

from pathlib import Path
import sys

import numpy as np
import pandas as pd


# ============================================================================
# PROJECT PATH
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / "src"),
)


# ============================================================================
# FILE PATHS
# ============================================================================

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
    / "baselines"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================================
# CONSTANTS
# ============================================================================

HORIZONS = (
    1,
    3,
    6,
    12,
)

SEASONAL_PERIOD = 12

MODELS = (
    "Naive",
    "SeasonalNaive",
)


# ============================================================================
# HEADER
# ============================================================================

print("=" * 78)
print("CMIDO RO1 — STEP 23")
print("NAÏVE + SEASONAL NAÏVE FORECASTING BASELINES")
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
# STANDARDIZE DATA
# ============================================================================

price = price.rename(
    columns={
        "DataSeries": "series",
        "price_dollars_per_tonne": "value",
    }
)

demand = demand.rename(
    columns={
        "DataSeries": "series",
        "demand_thousand_tonnes": "value",
    }
)


def standardize_data(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize the RO1 long-format dataset."""

    work = df[
        [
            "date",
            "series",
            "value",
        ]
    ].copy()

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

    work = work.sort_values(
        [
            "series",
            "date",
        ]
    ).reset_index(drop=True)

    return work


price = standardize_data(price)
demand = standardize_data(demand)

print(
    f"Price observations : {len(price)}"
)

print(
    f"Demand observations: {len(demand)}"
)


# ============================================================================
# TASK FILES
# ============================================================================

TASK_FILES = {
    "price_validation": (
        TABLE_DIR
        / "RO1_price_validation_tasks.csv"
    ),
    "price_test": (
        TABLE_DIR
        / "RO1_price_test_tasks.csv"
    ),
    "demand_validation": (
        TABLE_DIR
        / "RO1_demand_validation_tasks.csv"
    ),
    "demand_test": (
        TABLE_DIR
        / "RO1_demand_test_tasks.csv"
    ),
}


# ============================================================================
# LOAD TASKS
# ============================================================================

def load_tasks(path: Path) -> pd.DataFrame:
    """
    Load and validate Step 22 task definitions.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Required Step 22 task file not found:\n{path}"
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

    missing = required - set(tasks.columns)

    if missing:
        raise ValueError(
            f"Task file {path.name} is missing columns: "
            f"{sorted(missing)}"
        )

    tasks["horizon"] = tasks["horizon"].astype(int)

    if not set(tasks["horizon"]).issubset(
        set(HORIZONS)
    ):
        raise ValueError(
            f"Unexpected horizons in {path.name}: "
            f"{sorted(tasks['horizon'].unique())}"
        )

    return tasks.sort_values(
        [
            "series",
            "forecast_origin",
            "horizon",
        ]
    ).reset_index(drop=True)


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
    "Price validation:",
    len(price_validation_tasks),
)

print(
    "Price test      :",
    len(price_test_tasks),
)

print(
    "Demand validation:",
    len(demand_validation_tasks),
)

print(
    "Demand test      :",
    len(demand_test_tasks),
)


# ============================================================================
# FORECAST FUNCTIONS
# ============================================================================

def naive_forecast(
    series_data: pd.DataFrame,
    forecast_origin: pd.Timestamp,
) -> float:
    """
    Naïve forecast:

        y_hat(t+h) = y(t)

    Uses the last observation available at the forecast origin.
    """

    history = series_data.loc[
        series_data["date"]
        <= forecast_origin
    ]

    if history.empty:
        raise ValueError(
            "No historical observations available "
            f"at origin {forecast_origin}."
        )

    return float(
        history.iloc[-1]["value"]
    )


def seasonal_naive_forecast(
    series_data: pd.DataFrame,
    target_date: pd.Timestamp,
) -> float:
    """
    Seasonal naïve forecast for monthly data:

        y_hat(t+h) = y(t+h-12)

    Therefore the forecast uses the observation from the
    same calendar month one year earlier.

    For horizons 1, 3, 6 and 12, the source observation
    is always available no later than the forecast origin.
    """

    seasonal_source_date = (
        target_date
        - pd.DateOffset(
            months=SEASONAL_PERIOD
        )
    )

    source = series_data.loc[
        series_data["date"]
        == seasonal_source_date
    ]

    if len(source) != 1:
        raise ValueError(
            "Seasonal-naïve source observation unavailable.\n"
            f"Target: {target_date}\n"
            f"Required source: {seasonal_source_date}"
        )

    return float(
        source.iloc[0]["value"]
    )


# ============================================================================
# METRICS
# ============================================================================

def mae(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:

    return float(
        np.mean(
            np.abs(
                actual - predicted
            )
        )
    )


def rmse(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:

    return float(
        np.sqrt(
            np.mean(
                (actual - predicted) ** 2
            )
        )
    )


def smape(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:

    denominator = (
        np.abs(actual)
        + np.abs(predicted)
    )

    values = np.where(
        denominator == 0,
        0.0,
        2.0
        * np.abs(
            predicted - actual
        )
        / denominator,
    )

    return float(
        np.mean(values) * 100.0
    )


def mape(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> float:

    values = np.where(
        actual == 0,
        np.nan,
        np.abs(
            (actual - predicted)
            / actual
        ),
    )

    return float(
        np.nanmean(values) * 100.0
    )


# ============================================================================
# TASK EVALUATION
# ============================================================================

def evaluate_tasks(
    data: pd.DataFrame,
    tasks: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Generate baseline forecasts for every Step 22 task.
    """

    records = []

    series_groups = {
        name: group.sort_values("date").reset_index(drop=True)
        for name, group in data.groupby(
            "series",
            sort=True,
        )
    }

    for row in tasks.itertuples(
        index=False
    ):

        series_name = str(row.series)

        if series_name not in series_groups:
            raise ValueError(
                f"Series '{series_name}' from task file "
                f"not found in {dataset_name} data."
            )

        series_data = series_groups[
            series_name
        ]

        origin = pd.Timestamp(
            row.forecast_origin
        )

        target = pd.Timestamp(
            row.target_date
        )

        horizon = int(
            row.horizon
        )

        split = str(
            row.split
        )

        # ------------------------------------------------------------
        # Actual target
        # ------------------------------------------------------------

        actual_rows = series_data.loc[
            series_data["date"] == target
        ]

        if len(actual_rows) != 1:
            raise ValueError(
                "Expected exactly one actual target value.\n"
                f"Dataset: {dataset_name}\n"
                f"Series: {series_name}\n"
                f"Target: {target}"
            )

        actual = float(
            actual_rows.iloc[0]["value"]
        )

        # ------------------------------------------------------------
        # Strict chronology check
        # ------------------------------------------------------------

        if not origin < target:
            raise AssertionError(
                "Forecast chronology violated:\n"
                f"Origin={origin}, Target={target}"
            )

        # ------------------------------------------------------------
        # Verify target is future relative to available history.
        # ------------------------------------------------------------

        history = series_data.loc[
            series_data["date"] <= origin
        ]

        if history.empty:
            raise AssertionError(
                f"No training history at origin {origin}."
            )

        # ------------------------------------------------------------
        # Naïve
        # ------------------------------------------------------------

        naive_prediction = naive_forecast(
            series_data,
            origin,
        )

        # ------------------------------------------------------------
        # Seasonal naïve
        # ------------------------------------------------------------

        seasonal_prediction = seasonal_naive_forecast(
            series_data,
            target,
        )

        # ------------------------------------------------------------
        # Record both forecasts
        # ------------------------------------------------------------

        records.append(
            {
                "dataset": dataset_name,
                "series": series_name,
                "forecast_origin": origin,
                "target_date": target,
                "horizon": horizon,
                "split": split,
                "model": "Naive",
                "prediction": naive_prediction,
                "actual": actual,
            }
        )

        records.append(
            {
                "dataset": dataset_name,
                "series": series_name,
                "forecast_origin": origin,
                "target_date": target,
                "horizon": horizon,
                "split": split,
                "model": "SeasonalNaive",
                "prediction": seasonal_prediction,
                "actual": actual,
            }
        )

    return pd.DataFrame(records)


# ============================================================================
# GENERATE FORECASTS
# ============================================================================

print("\n[3] GENERATING BASELINE FORECASTS")

price_validation_results = evaluate_tasks(
    price,
    price_validation_tasks,
    "RO1_PRICE",
)

price_test_results = evaluate_tasks(
    price,
    price_test_tasks,
    "RO1_PRICE",
)

demand_validation_results = evaluate_tasks(
    demand,
    demand_validation_tasks,
    "RO1_DEMAND",
)

demand_test_results = evaluate_tasks(
    demand,
    demand_test_tasks,
    "RO1_DEMAND",
)


forecast_results = pd.concat(
    [
        price_validation_results,
        price_test_results,
        demand_validation_results,
        demand_test_results,
    ],
    ignore_index=True,
)


print(
    f"Generated forecast records: "
    f"{len(forecast_results)}"
)


# ============================================================================
# FORECAST RESULT VALIDATION
# ============================================================================

print("\n[4] FORECAST RESULT VALIDATION")

expected_tasks = (
    len(price_validation_tasks)
    + len(price_test_tasks)
    + len(demand_validation_tasks)
    + len(demand_test_tasks)
)

expected_records = (
    expected_tasks * len(MODELS)
)

if len(forecast_results) != expected_records:
    raise AssertionError(
        "Unexpected number of forecast records.\n"
        f"Expected: {expected_records}\n"
        f"Actual:   {len(forecast_results)}"
    )


if forecast_results[
    "prediction"
].isna().any():

    raise AssertionError(
        "Missing baseline predictions detected."
    )


if forecast_results[
    "actual"
].isna().any():

    raise AssertionError(
        "Missing actual target values detected."
    )


if (
    forecast_results["prediction"] <= 0
).any():

    raise AssertionError(
        "Non-positive baseline prediction detected."
    )


# ============================================================================
# METRIC CALCULATION
# ============================================================================

def calculate_metrics(
    results: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate baseline performance by:

        dataset
        split
        series
        horizon
        model
    """

    records = []

    grouped = results.groupby(
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

        actual = (
            group["actual"]
            .to_numpy(
                dtype=float
            )
        )

        predicted = (
            group["prediction"]
            .to_numpy(
                dtype=float
            )
        )

        dataset_name, split, series, horizon, model = keys

        records.append(
            {
                "dataset": dataset_name,
                "split": split,
                "series": series,
                "horizon": int(horizon),
                "model": model,
                "n_forecasts": len(group),
                "MAE": mae(
                    actual,
                    predicted,
                ),
                "RMSE": rmse(
                    actual,
                    predicted,
                ),
                "sMAPE_percent": smape(
                    actual,
                    predicted,
                ),
                "MAPE_percent": mape(
                    actual,
                    predicted,
                ),
            }
        )

    return pd.DataFrame(records)


metrics = calculate_metrics(
    forecast_results
)


# ============================================================================
# VALIDATION BASELINE COMPARISON
# ============================================================================

validation_metrics = metrics.loc[
    metrics["split"] == "validation"
].copy()

test_metrics = metrics.loc[
    metrics["split"] == "test"
].copy()


# ============================================================================
# PRIMARY BASELINE RANKING
# ============================================================================

validation_ranking = (
    validation_metrics
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

test_ranking = (
    test_metrics
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
# SAVE OUTPUTS
# ============================================================================

print("\n[5] SAVING BASELINE OUTPUTS")

forecast_results.to_csv(
    OUTPUT_DIR
    / "RO1_step23_baseline_forecasts.csv",
    index=False,
)

metrics.to_csv(
    OUTPUT_DIR
    / "RO1_step23_baseline_metrics.csv",
    index=False,
)

validation_ranking.to_csv(
    OUTPUT_DIR
    / "RO1_step23_validation_metrics.csv",
    index=False,
)

test_ranking.to_csv(
    OUTPUT_DIR
    / "RO1_step23_test_metrics.csv",
    index=False,
)


# ============================================================================
# CONSOLE SUMMARY
# ============================================================================

print("\n[6] VALIDATION PERFORMANCE")

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
    ].to_string(index=False)
)


print("\n[7] TEST PERFORMANCE")

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
    ].to_string(index=False)
)


# ============================================================================
# FINAL ASSERTIONS
# ============================================================================

print("\n[8] FINAL ASSERTIONS")

expected_splits = {
    "validation",
    "test",
}

if set(
    forecast_results["split"].unique()
) != expected_splits:

    raise AssertionError(
        "Expected both validation and test forecasts."
    )


if set(
    forecast_results["model"].unique()
) != set(MODELS):

    raise AssertionError(
        "Expected exactly Naive and SeasonalNaive models."
    )


if set(
    forecast_results["horizon"].unique()
) != set(HORIZONS):

    raise AssertionError(
        "Not all requested horizons are represented."
    )


# One result per task per model.
duplicate_mask = forecast_results.duplicated(
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

if duplicate_mask.any():

    raise AssertionError(
        "Duplicate forecast records detected."
    )


print(
    "Forecast records: PASS"
)

print(
    "No missing predictions: PASS"
)

print(
    "No missing actuals: PASS"
)

print(
    "Positive forecasts: PASS"
)

print(
    "Model coverage: PASS"
)

print(
    "Horizon coverage: PASS"
)

print(
    "Duplicate protection: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print("\n" + "=" * 78)
print("STEP 23 COMPLETE")
print("=" * 78)

print(
    "Naïve baseline       : READY"
)

print(
    "Seasonal naïve       : READY"
)

print(
    "Validation metrics   : SAVED"
)

print(
    "Test metrics         : SAVED"
)

print(
    "Forecast records     : SAVED"
)

print(
    "\nRO1 STEP 23 BASELINES: READY"
)

print("=" * 78)