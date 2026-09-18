"""
CMIDO — RO1 Rolling-Origin Evaluation Engine

Reusable utilities for:
    - forecasting data-contract validation
    - monthly continuity validation
    - evaluation-window construction
    - expanding-window task generation
    - leakage auditing
    - task summaries

Core methodological rule
-------------------------
Validation/test membership is determined by TARGET DATE.

For every forecasting task:

    training observations <= forecast origin < target date

Validation:
    validation_start <= target_date <= validation_end

Test:
    test_start <= target_date <= test_end

This prevents multi-step validation forecasts from reaching into
the test period.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import pandas as pd


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass(frozen=True)
class ForecastTask:
    """One direct multi-horizon forecasting task."""

    dataset: str
    series: str
    forecast_origin: pd.Timestamp
    target_date: pd.Timestamp
    horizon: int
    split: str


@dataclass(frozen=True)
class EvaluationWindow:
    """Temporal development, validation, and test boundaries."""

    development_start: pd.Timestamp
    development_end: pd.Timestamp

    validation_start: pd.Timestamp
    validation_end: pd.Timestamp

    test_start: pd.Timestamp
    test_end: pd.Timestamp


# ============================================================================
# DATA CONTRACT
# ============================================================================

def validate_forecasting_data(
    df: pd.DataFrame,
    dataset_name: str | None = None,
    date_col: str = "date",
    series_col: str = "series",
    value_col: str = "value",
) -> pd.DataFrame:
    """
    Validate and standardize forecasting data.

    Returns a cleaned copy with:
        date
        series
        value

    No observations are removed.
    """

    required = {date_col, series_col, value_col}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{dataset_name or 'Dataset'} contract failed. "
            f"Missing columns: {sorted(missing)}"
        )

    work = df[[date_col, series_col, value_col]].copy()

    work[date_col] = pd.to_datetime(
        work[date_col],
        errors="coerce",
    )

    if work[date_col].isna().any():
        raise ValueError(
            f"{dataset_name or 'Dataset'} contract failed: "
            "invalid or missing dates."
        )

    # Normalize to month-start.
    work[date_col] = (
        work[date_col]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    if work[series_col].isna().any():
        raise ValueError(
            f"{dataset_name or 'Dataset'} contract failed: "
            "missing series identifiers."
        )

    work[series_col] = work[series_col].astype(str).str.strip()

    if (work[series_col] == "").any():
        raise ValueError(
            f"{dataset_name or 'Dataset'} contract failed: "
            "blank series identifiers."
        )

    work[value_col] = pd.to_numeric(
        work[value_col],
        errors="coerce",
    )

    if work[value_col].isna().any():
        raise ValueError(
            f"{dataset_name or 'Dataset'} contract failed: "
            "missing/non-numeric values."
        )

    if (~work[value_col].gt(0)).any():
        raise ValueError(
            f"{dataset_name or 'Dataset'} contract failed: "
            "all forecasting values must be > 0."
        )

    duplicate_mask = work.duplicated(
        subset=[date_col, series_col],
        keep=False,
    )

    if duplicate_mask.any():
        duplicates = work.loc[
            duplicate_mask,
            [date_col, series_col, value_col],
        ].sort_values(
            [series_col, date_col]
        )

        raise ValueError(
            f"{dataset_name or 'Dataset'} contract failed: "
            "duplicate date-series observations found.\n"
            f"{duplicates.to_string(index=False)}"
        )

    # Rename to canonical internal schema.
    work = work.rename(
        columns={
            date_col: "date",
            series_col: "series",
            value_col: "value",
        }
    )

    work = work.sort_values(
        ["series", "date"]
    ).reset_index(drop=True)

    return work


# ============================================================================
# MONTHLY CONTINUITY
# ============================================================================

def validate_monthly_continuity(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Verify that every series has complete monthly observations.
    """

    records = []

    for series_name, group in df.groupby(
        "series",
        sort=True,
    ):

        dates = pd.DatetimeIndex(
            sorted(group["date"].drop_duplicates())
        )

        if len(dates) == 0:
            continue

        start = dates.min()
        end = dates.max()

        expected = pd.date_range(
            start=start,
            end=end,
            freq="MS",
        )

        missing = expected.difference(dates)

        records.append(
            {
                "series": series_name,
                "start": start,
                "end": end,
                "observed_months": len(dates),
                "expected_months": len(expected),
                "missing_months": len(missing),
                "missing_dates": ",".join(
                    d.strftime("%Y-%m-%d")
                    for d in missing
                ),
            }
        )

    result = pd.DataFrame(records)

    if not result.empty:
        if result["missing_months"].sum() != 0:
            bad = result.loc[
                result["missing_months"] > 0
            ]

            raise AssertionError(
                "Monthly continuity failed.\n"
                f"{bad.to_string(index=False)}"
            )

    return result


# ============================================================================
# EVALUATION WINDOW
# ============================================================================

def build_evaluation_window(
    df: pd.DataFrame,
    validation_months: int = 24,
    test_months: int = 24,
) -> EvaluationWindow:
    """
    Construct the common evaluation window.

    Structure:

        DEVELOPMENT | VALIDATION | TEST
                    24 months    24 months

    The latest common observation across all series determines
    the end of the test period.
    """

    if validation_months <= 0:
        raise ValueError(
            "validation_months must be positive."
        )

    if test_months <= 0:
        raise ValueError(
            "test_months must be positive."
        )

    common_end = (
        df.groupby("series")["date"]
        .max()
        .min()
    )

    if pd.isna(common_end):
        raise ValueError(
            "Could not determine common dataset endpoint."
        )

    test_end = pd.Timestamp(common_end)

    test_start = (
        test_end
        - pd.DateOffset(months=test_months - 1)
    )

    validation_end = (
        test_start
        - pd.DateOffset(months=1)
    )

    validation_start = (
        validation_end
        - pd.DateOffset(months=validation_months - 1)
    )

    development_start = pd.Timestamp(
        df["date"].min()
    )

    development_end = (
        validation_start
        - pd.DateOffset(months=1)
    )

    if development_end < development_start:
        raise ValueError(
            "Insufficient historical data before validation period."
        )

    return EvaluationWindow(
        development_start=development_start,
        development_end=development_end,
        validation_start=validation_start,
        validation_end=validation_end,
        test_start=test_start,
        test_end=test_end,
    )


# ============================================================================
# FORECAST TASK GENERATION
# ============================================================================

def generate_forecast_tasks(
    df: pd.DataFrame,
    dataset_name: str,
    horizons: Sequence[int],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    minimum_training_months: int = 60,
    split: str | None = None,
) -> list[ForecastTask]:
    """
    Generate direct multi-horizon rolling-origin forecasting tasks.

    IMPORTANT:
    The target date must remain inside the requested evaluation period.

    Example:

        origin = 2024-05
        horizon = 3
        target = 2024-08

    If the validation period ends in 2024-06, this task is NOT
    a validation task because the target falls outside validation.

    This is the critical protection against multi-step leakage.
    """

    if split is None:
        raise ValueError(
            "split must be explicitly provided as "
            "'validation' or 'test'."
        )

    if split not in {"validation", "test"}:
        raise ValueError(
            "split must be 'validation' or 'test'."
        )

    if minimum_training_months <= 0:
        raise ValueError(
            "minimum_training_months must be positive."
        )

    horizons = tuple(
        sorted(
            set(
                int(h)
                for h in horizons
            )
        )
    )

    if not horizons:
        raise ValueError(
            "At least one forecast horizon is required."
        )

    if any(h <= 0 for h in horizons):
        raise ValueError(
            "All forecast horizons must be positive."
        )

    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)

    tasks: list[ForecastTask] = []

    for series_name, group in df.groupby(
        "series",
        sort=True,
    ):

        group = group.sort_values("date")

        series_dates = pd.DatetimeIndex(
            group["date"].drop_duplicates()
        )

        # Origins are restricted to the requested split.
        origins = series_dates[
            (series_dates >= start_date)
            & (series_dates <= end_date)
        ]

        for origin in origins:

            training_dates = series_dates[
                series_dates <= origin
            ]

            if len(training_dates) < minimum_training_months:
                continue

            for horizon in horizons:

                target_date = (
                    origin
                    + pd.DateOffset(
                        months=horizon
                    )
                )

                # ------------------------------------------------------------
                # CRITICAL RULE
                # ------------------------------------------------------------
                #
                # The target must remain inside the requested split.
                #
                if target_date < start_date:
                    continue

                if target_date > end_date:
                    continue

                # Target must exist in the observed data.
                if target_date not in series_dates:
                    continue

                # Chronology invariant.
                if not origin < target_date:
                    raise AssertionError(
                        "Invalid forecasting task: "
                        "forecast origin must precede target."
                    )

                tasks.append(
                    ForecastTask(
                        dataset=dataset_name,
                        series=str(series_name),
                        forecast_origin=pd.Timestamp(origin),
                        target_date=pd.Timestamp(target_date),
                        horizon=int(horizon),
                        split=split,
                    )
                )

    tasks.sort(
        key=lambda x: (
            x.dataset,
            x.series,
            x.forecast_origin,
            x.horizon,
        )
    )

    return tasks


# ============================================================================
# TASKS → DATAFRAME
# ============================================================================

def tasks_to_dataframe(
    tasks: Iterable[ForecastTask],
) -> pd.DataFrame:

    records = [
        {
            "dataset": task.dataset,
            "series": task.series,
            "forecast_origin": task.forecast_origin,
            "target_date": task.target_date,
            "horizon": task.horizon,
            "split": task.split,
        }
        for task in tasks
    ]

    return pd.DataFrame(
        records,
        columns=[
            "dataset",
            "series",
            "forecast_origin",
            "target_date",
            "horizon",
            "split",
        ],
    )


# ============================================================================
# TRAINING DATA
# ============================================================================

def get_training_data(
    df: pd.DataFrame,
    task: ForecastTask,
) -> pd.DataFrame:
    """
    Return observations available at the forecast origin.
    """

    training = df.loc[
        (df["series"].astype(str) == task.series)
        & (
            df["date"]
            <= task.forecast_origin
        )
    ].copy()

    return training.sort_values(
        "date"
    ).reset_index(drop=True)


# ============================================================================
# TARGET VALUE
# ============================================================================

def get_target_value(
    df: pd.DataFrame,
    task: ForecastTask,
) -> float:
    """
    Retrieve exactly one observed target value.
    """

    target = df.loc[
        (df["series"].astype(str) == task.series)
        & (
            df["date"]
            == task.target_date
        )
    ]

    if len(target) != 1:
        raise ValueError(
            "Expected exactly one target observation.\n"
            f"Task: {task}"
        )

    return float(
        target.iloc[0]["value"]
    )


# ============================================================================
# TASK AUDIT
# ============================================================================

def audit_tasks(
    df: pd.DataFrame,
    tasks: Iterable[ForecastTask],
    window: EvaluationWindow,
    split: str,
    minimum_training_months: int = 60,
) -> pd.DataFrame:
    """
    Strict audit of forecasting tasks.

    Required output columns:

        leakage_ok
        target_ok
        actual_ok
        chronology_ok

    These are retained because the experiment runner uses them
    as final acceptance criteria.
    """

    if split not in {"validation", "test"}:
        raise ValueError(
            "split must be 'validation' or 'test'."
        )

    tasks = list(tasks)

    if split == "validation":
        split_start = window.validation_start
        split_end = window.validation_end
    else:
        split_start = window.test_start
        split_end = window.test_end

    records = []

    for task in tasks:

        series_data = df.loc[
            df["series"].astype(str)
            == task.series
        ].sort_values("date")

        training = series_data.loc[
            series_data["date"]
            <= task.forecast_origin
        ]

        # ------------------------------------------------------------
        # Leakage check
        # ------------------------------------------------------------

        leakage_ok = (
            len(training) >= minimum_training_months
            and (
                training["date"].max()
                <= task.forecast_origin
            )
        )

        # ------------------------------------------------------------
        # Target temporal placement
        # ------------------------------------------------------------

        target_ok = (
            split_start
            <= task.target_date
            <= split_end
        )

        # ------------------------------------------------------------
        # Actual target existence
        # ------------------------------------------------------------

        actual_ok = (
            (
                series_data["date"]
                == task.target_date
            ).sum()
            == 1
        )

        # ------------------------------------------------------------
        # Chronology
        # ------------------------------------------------------------

        chronology_ok = (
            task.forecast_origin
            < task.target_date
        )

        passed = (
            leakage_ok
            and target_ok
            and actual_ok
            and chronology_ok
            and task.split == split
        )

        records.append(
            {
                "dataset": task.dataset,
                "series": task.series,
                "forecast_origin": task.forecast_origin,
                "target_date": task.target_date,
                "horizon": task.horizon,
                "split": task.split,
                "leakage_ok": leakage_ok,
                "target_ok": target_ok,
                "actual_ok": actual_ok,
                "chronology_ok": chronology_ok,
                "split_ok": task.split == split,
                "passed": passed,
            }
        )

    audit = pd.DataFrame(records)

    if audit.empty:
        raise AssertionError(
            f"{split.capitalize()} audit produced zero tasks."
        )

    if not audit["passed"].all():
        failed = audit.loc[
            ~audit["passed"]
        ]

        raise AssertionError(
            f"{split.capitalize()} task audit failed.\n"
            f"{failed.to_string(index=False)}"
        )

    # Duplicate task protection.
    duplicate_mask = audit.duplicated(
        subset=[
            "dataset",
            "series",
            "forecast_origin",
            "target_date",
            "horizon",
            "split",
        ],
        keep=False,
    )

    if duplicate_mask.any():
        raise AssertionError(
            "Duplicate forecasting tasks detected.\n"
            f"{audit.loc[duplicate_mask].to_string(index=False)}"
        )

    return audit


# ============================================================================
# TASK SUMMARY
# ============================================================================

def summarize_tasks(
    tasks: Iterable[ForecastTask],
) -> pd.DataFrame:

    task_df = tasks_to_dataframe(tasks)

    if task_df.empty:
        return pd.DataFrame(
            columns=[
                "dataset",
                "series",
                "horizon",
                "tasks",
                "first_origin",
                "last_origin",
                "first_target",
                "last_target",
            ]
        )

    return (
        task_df
        .groupby(
            [
                "dataset",
                "series",
                "horizon",
            ],
            sort=True,
        )
        .agg(
            tasks=("target_date", "size"),
            first_origin=(
                "forecast_origin",
                "min",
            ),
            last_origin=(
                "forecast_origin",
                "max",
            ),
            first_target=(
                "target_date",
                "min",
            ),
            last_target=(
                "target_date",
                "max",
            ),
        )
        .reset_index()
    )


# ============================================================================
# SELF CHECK
# ============================================================================

if __name__ == "__main__":

    print("=" * 78)
    print("CMIDO — RO1 ROLLING-ORIGIN ENGINE")
    print("=" * 78)
    print()
    print(
        "This is a reusable module."
    )
    print()
    print(
        "Run the experiment with:"
    )
    print()
    print(
        "python experiments\\RO1_forecasting\\04_rolling_origin_engine.py"
    )