"""
CMIDO — RO1 STEP 22

Forecasting Data Contract + Rolling-Origin Evaluation Engine

This script is the executable experiment runner.

It:
    1. Loads RO1 price and demand data.
    2. Validates the forecasting data contract.
    3. Checks monthly continuity.
    4. Builds independent evaluation windows.
    5. Generates validation/test rolling-origin tasks.
    6. Audits training leakage and temporal separation.
    7. Saves all evaluation-contract tables.
    8. Performs final acceptance assertions.

No forecasting models are trained in Step 22.
"""


# ============================================================================
# IMPORTS
# ============================================================================

from pathlib import Path
import sys

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
# CMIDO ENGINE IMPORTS
# ============================================================================

from evaluation.rolling_origin import (
    validate_forecasting_data,
    validate_monthly_continuity,
    build_evaluation_window,
    generate_forecast_tasks,
    tasks_to_dataframe,
    audit_tasks,
    summarize_tasks,
)


# ============================================================================
# FILE PATHS
# ============================================================================

PRICE_FILE = (
    ROOT
    / "data"
    / "interim"
    / "RO1_price_long.csv"
)

DEMAND_FILE = (
    ROOT
    / "data"
    / "interim"
    / "RO1_demand_long.csv"
)

RESULT_DIR = (
    ROOT
    / "results"
    / "forecasting"
    / "tables"
)

RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================================
# HEADER
# ============================================================================

print("=" * 78)
print("CMIDO RO1 — STEP 22")
print("FORECASTING DATA CONTRACT + ROLLING-ORIGIN ENGINE")
print("=" * 78)


# ============================================================================
# 1. LOAD DATA
# ============================================================================

print("\n[1] LOADING RO1 DATA")

price = pd.read_csv(
    PRICE_FILE,
    parse_dates=["date"],
)

demand = pd.read_csv(
    DEMAND_FILE,
    parse_dates=["date"],
)


# ============================================================================
# 2. STANDARDIZE SCHEMA
# ============================================================================

print("\n[2] STANDARDIZING DATA SCHEMA")

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


# ============================================================================
# 3. DATA CONTRACT
# ============================================================================

print("\n[3] DATA CONTRACT VALIDATION")

price = validate_forecasting_data(
    price,
    dataset_name="RO1_PRICE",
)

demand = validate_forecasting_data(
    demand,
    dataset_name="RO1_DEMAND",
)

print("Price contract : PASS")
print("Demand contract: PASS")


# ============================================================================
# 4. MONTHLY CONTINUITY
# ============================================================================

print("\n[4] MONTHLY CONTINUITY")

price_continuity = validate_monthly_continuity(
    price
)

demand_continuity = validate_monthly_continuity(
    demand
)

print("\nPRICE")
print(
    price_continuity.to_string(
        index=False
    )
)

print("\nDEMAND")
print(
    demand_continuity.to_string(
        index=False
    )
)

if price_continuity[
    "missing_months"
].sum() != 0:

    raise AssertionError(
        "Price monthly continuity failed."
    )

if demand_continuity[
    "missing_months"
].sum() != 0:

    raise AssertionError(
        "Demand monthly continuity failed."
    )

print("\nContinuity: PASS")


# ============================================================================
# 5. EVALUATION WINDOWS
# ============================================================================

print("\n[5] EVALUATION WINDOWS")

price_window = build_evaluation_window(
    price,
    validation_months=24,
    test_months=24,
)

demand_window = build_evaluation_window(
    demand,
    validation_months=24,
    test_months=24,
)

print("\nPRICE WINDOW")
print(price_window)

print("\nDEMAND WINDOW")
print(demand_window)


# ============================================================================
# 6. FORECAST HORIZONS
# ============================================================================

horizons = (
    1,
    3,
    6,
    12,
)

print("\n[6] FORECAST HORIZONS")
print("Horizons:", horizons)


# ============================================================================
# 7. GENERATE VALIDATION TASKS
# ============================================================================

print("\n[7] GENERATING VALIDATION TASKS")

price_validation_tasks = generate_forecast_tasks(
    price,
    dataset_name="RO1_PRICE",
    horizons=horizons,
    start_date=price_window.validation_start,
    end_date=price_window.validation_end,
    minimum_training_months=60,
    split="validation",
)

demand_validation_tasks = generate_forecast_tasks(
    demand,
    dataset_name="RO1_DEMAND",
    horizons=horizons,
    start_date=demand_window.validation_start,
    end_date=demand_window.validation_end,
    minimum_training_months=60,
    split="validation",
)


# ============================================================================
# 8. GENERATE TEST TASKS
# ============================================================================

print("\n[8] GENERATING TEST TASKS")

price_test_tasks = generate_forecast_tasks(
    price,
    dataset_name="RO1_PRICE",
    horizons=horizons,
    start_date=price_window.test_start,
    end_date=price_window.test_end,
    minimum_training_months=60,
    split="test",
)

demand_test_tasks = generate_forecast_tasks(
    demand,
    dataset_name="RO1_DEMAND",
    horizons=horizons,
    start_date=demand_window.test_start,
    end_date=demand_window.test_end,
    minimum_training_months=60,
    split="test",
)


# ============================================================================
# 9. CONVERT TASKS TO TABLES
# ============================================================================

price_validation = tasks_to_dataframe(
    price_validation_tasks
)

demand_validation = tasks_to_dataframe(
    demand_validation_tasks
)

price_test = tasks_to_dataframe(
    price_test_tasks
)

demand_test = tasks_to_dataframe(
    demand_test_tasks
)


# ============================================================================
# 10. VALIDATION AUDIT
# ============================================================================

print("\n[9] VALIDATION LEAKAGE AUDIT")

price_val_audit = audit_tasks(
    price,
    price_validation_tasks,
    price_window,
    split="validation",
    minimum_training_months=60,
)

demand_val_audit = audit_tasks(
    demand,
    demand_validation_tasks,
    demand_window,
    split="validation",
    minimum_training_months=60,
)

print(
    f"Price validation tasks : "
    f"{len(price_val_audit)}"
)

print(
    f"Demand validation tasks: "
    f"{len(demand_val_audit)}"
)

print("Validation audit: PASS")


# ============================================================================
# 11. TEST AUDIT
# ============================================================================

print("\n[10] TEST LEAKAGE AUDIT")

price_test_audit = audit_tasks(
    price,
    price_test_tasks,
    price_window,
    split="test",
    minimum_training_months=60,
)

demand_test_audit = audit_tasks(
    demand,
    demand_test_tasks,
    demand_window,
    split="test",
    minimum_training_months=60,
)

print(
    f"Price test tasks       : "
    f"{len(price_test_audit)}"
)

print(
    f"Demand test tasks      : "
    f"{len(demand_test_audit)}"
)

print("Test audit: PASS")


# ============================================================================
# 12. TASK SUMMARIES
# ============================================================================

price_val_summary = summarize_tasks(
    price_validation_tasks
)

demand_val_summary = summarize_tasks(
    demand_validation_tasks
)

price_test_summary = summarize_tasks(
    price_test_tasks
)

demand_test_summary = summarize_tasks(
    demand_test_tasks
)


# ============================================================================
# 13. SAVE OUTPUTS
# ============================================================================

print("\n[11] SAVING DATA CONTRACT OUTPUTS")

price_continuity.to_csv(
    RESULT_DIR
    / "RO1_price_monthly_continuity.csv",
    index=False,
)

demand_continuity.to_csv(
    RESULT_DIR
    / "RO1_demand_monthly_continuity.csv",
    index=False,
)

price_validation.to_csv(
    RESULT_DIR
    / "RO1_price_validation_tasks.csv",
    index=False,
)

demand_validation.to_csv(
    RESULT_DIR
    / "RO1_demand_validation_tasks.csv",
    index=False,
)

price_test.to_csv(
    RESULT_DIR
    / "RO1_price_test_tasks.csv",
    index=False,
)

demand_test.to_csv(
    RESULT_DIR
    / "RO1_demand_test_tasks.csv",
    index=False,
)

price_val_summary.to_csv(
    RESULT_DIR
    / "RO1_price_validation_summary.csv",
    index=False,
)

demand_val_summary.to_csv(
    RESULT_DIR
    / "RO1_demand_validation_summary.csv",
    index=False,
)

price_test_summary.to_csv(
    RESULT_DIR
    / "RO1_price_test_summary.csv",
    index=False,
)

demand_test_summary.to_csv(
    RESULT_DIR
    / "RO1_demand_test_summary.csv",
    index=False,
)


# ============================================================================
# 14. FINAL ASSERTIONS
# ============================================================================

print("\n[12] FINAL ASSERTIONS")


all_audits = [
    price_val_audit,
    demand_val_audit,
    price_test_audit,
    demand_test_audit,
]


# --------------------------------------------------------------------------
# Every audit must be non-empty and completely passed.
# --------------------------------------------------------------------------

for audit in all_audits:

    if audit.empty:
        raise AssertionError(
            "An evaluation audit is empty."
        )

    for column in [
        "leakage_ok",
        "target_ok",
        "actual_ok",
        "chronology_ok",
    ]:

        if not audit[column].all():

            raise AssertionError(
                f"Failed audit column: {column}"
            )


# --------------------------------------------------------------------------
# Validation/test target separation — PRICE
# --------------------------------------------------------------------------

if (
    price_validation["target_date"].max()
    >= price_test["target_date"].min()
):

    raise AssertionError(
        "Price validation/test target temporal separation failed."
    )


# --------------------------------------------------------------------------
# Validation/test target separation — DEMAND
# --------------------------------------------------------------------------

if (
    demand_validation["target_date"].max()
    >= demand_test["target_date"].min()
):

    raise AssertionError(
        "Demand validation/test target temporal separation failed."
    )


# --------------------------------------------------------------------------
# Validation/test origin separation — PRICE
# --------------------------------------------------------------------------

if (
    price_validation["forecast_origin"].max()
    >= price_test["forecast_origin"].min()
):

    raise AssertionError(
        "Price validation/test forecast-origin separation failed."
    )


# --------------------------------------------------------------------------
# Validation/test origin separation — DEMAND
# --------------------------------------------------------------------------

if (
    demand_validation["forecast_origin"].max()
    >= demand_test["forecast_origin"].min()
):

    raise AssertionError(
        "Demand validation/test forecast-origin separation failed."
    )


# --------------------------------------------------------------------------
# Horizon checks
# --------------------------------------------------------------------------

if set(
    price_validation["horizon"].unique()
) != set(horizons):

    raise AssertionError(
        "Price validation horizons are incomplete."
    )

if set(
    demand_validation["horizon"].unique()
) != set(horizons):

    raise AssertionError(
        "Demand validation horizons are incomplete."
    )

if set(
    price_test["horizon"].unique()
) != set(horizons):

    raise AssertionError(
        "Price test horizons are incomplete."
    )

if set(
    demand_test["horizon"].unique()
) != set(horizons):

    raise AssertionError(
        "Demand test horizons are incomplete."
    )


# ============================================================================
# 15. FINAL REPORT
# ============================================================================

print("Data contract: PASS")
print("Monthly continuity: PASS")
print("Forecast chronology: PASS")
print("Training leakage audit: PASS")
print("Validation target separation: PASS")
print("Test target separation: PASS")
print("Validation/test separation: PASS")
print("Horizon coverage: PASS")

print("\n" + "=" * 78)
print("STEP 22 COMPLETE")
print("=" * 78)

print(
    f"Price validation tasks : "
    f"{len(price_validation)}"
)

print(
    f"Demand validation tasks: "
    f"{len(demand_validation)}"
)

print(
    f"Price test tasks       : "
    f"{len(price_test)}"
)

print(
    f"Demand test tasks      : "
    f"{len(demand_test)}"
)

print(
    "\nHORIZONS:",
    horizons,
)

print(
    "\nRO1 ROLLING-ORIGIN ENGINE: READY"
)

print("=" * 78)