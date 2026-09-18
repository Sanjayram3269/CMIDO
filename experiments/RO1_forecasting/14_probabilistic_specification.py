"""
CMIDO — RO1 STEP 26A
Probabilistic Forecasting Specification & Data Contract

Purpose
-------
Define and audit the probabilistic forecasting contract before any
probabilistic model is trained.

This step DOES NOT:
- train XGBoost
- train LightGBM
- fit conformal calibration
- select a probabilistic model
- modify the frozen deterministic forecasting results

This step verifies that the data and rolling-origin framework can
support uncertainty-aware forecasting.

Canonical probabilistic representation
---------------------------------------
For each:

    dataset × material × forecast_origin × horizon

the future target is represented by predictive quantiles:

    q = {0.10, 0.25, 0.50, 0.75, 0.90}

Interpretation:

    q0.50              point forecast
    q0.10–q0.90         nominal 80% predictive interval
    q0.25–q0.75         nominal 50% predictive interval

The predictive quantiles will later be used as inputs to CMIDO's
uncertainty propagation layer.

Feature contract
----------------
Own lags:
    1, 2, 3, 6, 12

Rolling statistics:
    mean 3, 6, 12
    std  3, 6, 12

Calendar:
    month
    quarter

Momentum:
    lag-1 log change
    lag-3 log change

Cross-material features are NOT included in the primary feature
contract. They may be evaluated later as an ablation.

Temporal protocol
-----------------
Expanding-window rolling-origin forecasting.

No random train/test split.

No future information may enter the feature vector.

Primary horizon:
    h = 3

Secondary horizons:
    h = 1, 6, 12

Validation/test boundaries remain those already frozen in Step 22.
"""


from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

PRICE_PATH = (
    ROOT
    / "data"
    / "interim"
    / "RO1_price_long.csv"
)

DEMAND_PATH = (
    ROOT
    / "data"
    / "interim"
    / "RO1_demand_long.csv"
)

OUTPUT_DIR = (
    ROOT
    / "results"
    / "forecasting"
    / "probabilistic"
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

QUANTILES = [
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
]

OWN_LAGS = [
    1,
    2,
    3,
    6,
    12,
]

ROLLING_WINDOWS = [
    3,
    6,
    12,
]

MOMENTUM_LAGS = [
    1,
    3,
]

CALENDAR_FEATURES = [
    "month",
    "quarter",
]


# ============================================================================
# EXPECTED MATERIALS
# ============================================================================

EXPECTED_PRICE_MATERIALS = [
    "Cement In Bulk (Ordinary Portland Cement)",
    "Concreting Sand",
    "Granite (20mm Aggregate)",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars (16-32mm High Tensile)",
]

EXPECTED_DEMAND_MATERIALS = [
    "Cement",
    "Granite",
    "Ready-Mixed Concrete",
    "Steel Reinforcement Bars",
]


# ============================================================================
# HEADER
# ============================================================================

print("=" * 78)
print("CMIDO RO1 — STEP 26A")
print("PROBABILISTIC FORECASTING SPECIFICATION & DATA CONTRACT")
print("=" * 78)


# ============================================================================
# LOAD DATA
# ============================================================================

print("\n[1] LOADING RO1 DATA")


if not PRICE_PATH.exists():
    raise FileNotFoundError(
        f"Missing price long-format dataset:\n{PRICE_PATH}"
    )


if not DEMAND_PATH.exists():
    raise FileNotFoundError(
        f"Missing demand long-format dataset:\n{DEMAND_PATH}"
    )


price = pd.read_csv(
    PRICE_PATH
)

demand = pd.read_csv(
    DEMAND_PATH
)


print(
    f"Price rows: {len(price)}"
)

print(
    f"Demand rows: {len(demand)}"
)

print(
    f"Price columns: {list(price.columns)}"
)

print(
    f"Demand columns: {list(demand.columns)}"
)


# ============================================================================
# STANDARDIZE COLUMN NAMES
# ============================================================================

def find_column(
    df,
    candidates,
    description,
):

    for column in candidates:

        if column in df.columns:
            return column

    raise RuntimeError(
        f"Could not identify {description}.\n"
        f"Available columns: {list(df.columns)}"
    )


def standardize_long_dataframe(
    df,
    dataset_name,
):

    series_col = find_column(
        df,
        [
            "series",
            "DataSeries",
            "material",
        ],
        f"{dataset_name} series/material column",
    )

    date_col = find_column(
        df,
        [
            "date",
            "Date",
            "month",
            "Month",
        ],
        f"{dataset_name} date column",
    )

    value_col = find_column(
        df,
        [
            "value",
            "Value",
            "price",
            "demand",
            "price_dollars_per_tonne",
            "demand_thousand_tonnes",
        ],
        f"{dataset_name} value column",
    )

    result = df.rename(
        columns={
            series_col:
                "series",

            date_col:
                "date",

            value_col:
                "value",
        }
    ).copy()


    result["date"] = pd.to_datetime(
        result["date"],
        errors="raise",
    )


    result["value"] = pd.to_numeric(
        result["value"],
        errors="raise",
    )


    result["series"] = (
        result["series"]
        .astype(str)
        .str.strip()
    )


    result = result.sort_values(
        [
            "series",
            "date",
        ]
    ).reset_index(
        drop=True
    )


    return result


price = standardize_long_dataframe(
    price,
    "RO1_PRICE",
)

demand = standardize_long_dataframe(
    demand,
    "RO1_DEMAND",
)


# ============================================================================
# BASIC DATA CONTRACT
# ============================================================================

print("\n[2] BASIC DATA CONTRACT")


def audit_basic_data(
    df,
    expected_materials,
    dataset_name,
):

    observed_materials = sorted(
        df["series"]
        .unique()
        .tolist()
    )

    expected_sorted = sorted(
        expected_materials
    )


    print(
        f"\n{dataset_name}"
    )

    print(
        "Observed materials:"
    )

    for material in observed_materials:
        print(
            f"  - {material}"
        )


    assert (
        observed_materials
        ==
        expected_sorted
    ), (
        f"{dataset_name}: material mismatch.\n"
        f"Expected: {expected_sorted}\n"
        f"Observed: {observed_materials}"
    )


    assert (
        df["date"]
        .notna()
        .all()
    )


    assert (
        df["value"]
        .notna()
        .all()
    )


    assert (
        np.isfinite(
            df["value"]
        )
        .all()
    )


    assert (
        df["value"]
        > 0
    ).all()


    duplicate_count = (
        df
        .duplicated(
            subset=[
                "series",
                "date",
            ]
        )
        .sum()
    )


    print(
        f"Duplicate series-date rows: "
        f"{duplicate_count}"
    )


    assert duplicate_count == 0


    print(
        f"{dataset_name}: BASIC CONTRACT PASS"
    )


audit_basic_data(
    price,
    EXPECTED_PRICE_MATERIALS,
    "RO1_PRICE",
)

audit_basic_data(
    demand,
    EXPECTED_DEMAND_MATERIALS,
    "RO1_DEMAND",
)


# ============================================================================
# TEMPORAL CONTINUITY
# ============================================================================

print(
    "\n[3] MONTHLY CONTINUITY AUDIT"
)


def audit_monthly_continuity(
    df,
    dataset_name,
):

    records = []


    for series, group in (
        df.groupby(
            "series",
            sort=True,
        )
    ):

        dates = (
            group["date"]
            .sort_values()
            .drop_duplicates()
        )


        expected_dates = pd.date_range(
            start=dates.iloc[0],
            end=dates.iloc[-1],
            freq="MS",
        )


        missing_dates = (
            expected_dates
            .difference(dates)
        )


        records.append(
            {
                "dataset":
                    dataset_name,

                "series":
                    series,

                "start":
                    dates.iloc[0],

                "end":
                    dates.iloc[-1],

                "n_months":
                    len(dates),

                "expected_months":
                    len(expected_dates),

                "missing_months":
                    len(missing_dates),

                "continuous":
                    len(missing_dates) == 0,
            }
        )


    result = pd.DataFrame(
        records
    )


    print(
        result.to_string(
            index=False
        )
    )


    assert (
        result["continuous"]
        .all()
    )


    return result


price_continuity = audit_monthly_continuity(
    price,
    "RO1_PRICE",
)

demand_continuity = audit_monthly_continuity(
    demand,
    "RO1_DEMAND",
)


# ============================================================================
# QUANTILE CONTRACT
# ============================================================================

print("\n[4] QUANTILE CONTRACT")
print(f"Quantiles: {QUANTILES}")

EXPECTED_QUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]

assert len(QUANTILES) == 5, "Expected exactly 5 forecast quantiles"
assert all(
    abs(float(a) - float(b)) < 1e-12
    for a, b in zip(QUANTILES, EXPECTED_QUANTILES)
), f"Unexpected quantile specification: {QUANTILES}"

assert all(
    0.0 < float(q) < 1.0
    for q in QUANTILES
), "All quantiles must lie strictly between 0 and 1"

assert all(
    QUANTILES[i] < QUANTILES[i + 1]
    for i in range(len(QUANTILES) - 1)
), "Quantiles must be strictly increasing"

assert abs(QUANTILES[0] - 0.10) < 1e-12
assert abs(QUANTILES[1] - 0.25) < 1e-12
assert abs(QUANTILES[2] - 0.50) < 1e-12
assert abs(QUANTILES[3] - 0.75) < 1e-12
assert abs(QUANTILES[4] - 0.90) < 1e-12

MEDIAN_QUANTILE = 0.50
LOWER_50 = (0.25, 0.75)
LOWER_80 = (0.10, 0.90)

assert abs(MEDIAN_QUANTILE - QUANTILES[2]) < 1e-12
assert LOWER_50 == (QUANTILES[1], QUANTILES[3])
assert LOWER_80 == (QUANTILES[0], QUANTILES[4])

print("Median forecast: q0.50")
print("Central 50% interval: q0.25–q0.75")
print("Central 80% interval: q0.10–q0.90")
print("QUANTILE CONTRACT PASS")


# ============================================================================
# FEATURE CONTRACT
# ============================================================================

print(
    "\n[5] FEATURE CONTRACT"
)


feature_names = []


for lag in OWN_LAGS:

    feature_names.append(
        f"lag_{lag}"
    )


for window in ROLLING_WINDOWS:

    feature_names.append(
        f"rolling_mean_{window}"
    )

    feature_names.append(
        f"rolling_std_{window}"
    )


for feature in CALENDAR_FEATURES:

    feature_names.append(
        feature
    )


for lag in MOMENTUM_LAGS:

    feature_names.append(
        f"log_change_{lag}"
    )


print(
    "\nPrimary feature set:"
)

for feature in feature_names:

    print(
        f"  - {feature}"
    )


print(
    "\nCross-material features:"
)

print(
    "  EXCLUDED FROM PRIMARY MODEL"
)

print(
    "  Reserved for ablation analysis."
)


# ============================================================================
# FEATURE REQUIREMENTS
# ============================================================================

expected_feature_count = (
    len(OWN_LAGS)
    +
    2 * len(ROLLING_WINDOWS)
    +
    len(CALENDAR_FEATURES)
    +
    len(MOMENTUM_LAGS)
)


assert (
    len(feature_names)
    ==
    expected_feature_count
)


assert len(
    set(feature_names)
) == len(
    feature_names
)


assert all(
    isinstance(
        feature,
        str
    )
    for feature in feature_names
)


print(
    f"\nPrimary feature count: "
    f"{len(feature_names)}"
)

print(
    "Feature contract: PASS"
)


# ============================================================================
# FEATURE LEAKAGE DESIGN AUDIT
# ============================================================================

print(
    "\n[6] FEATURE LEAKAGE DESIGN AUDIT"
)


def build_features(
    df,
):

    """
    Build features using information available at forecast origin t.

    Every lag/rolling feature is based only on observations at or
    before t.

    The target at t+h is NEVER used.
    """

    result = df.copy()

    result = result.sort_values(
        [
            "series",
            "date",
        ]
    ).reset_index(
        drop=True
    )


    grouped = result.groupby(
        "series",
        group_keys=False,
    )


    # ------------------------------------------------------------------------
    # Own lags
    # ------------------------------------------------------------------------

    for lag in OWN_LAGS:

        result[
            f"lag_{lag}"
        ] = grouped[
            "value"
        ].shift(
            lag
        )


    # ------------------------------------------------------------------------
    # Rolling features
    #
    # Shift(1) is critical:
    #
    # At origin t, rolling statistics must use observations through t-1
    # when the feature represents information available BEFORE forecasting.
    #
    # The contemporaneous target value y_t is not used.
    # ------------------------------------------------------------------------

    shifted = grouped[
        "value"
    ].shift(
        1
    )


    for window in ROLLING_WINDOWS:

        result[
            f"rolling_mean_{window}"
        ] = (
            shifted
            .groupby(
                result["series"]
            )
            .rolling(
                window
            )
            .mean()
            .reset_index(
                level=0,
                drop=True,
            )
        )


        result[
            f"rolling_std_{window}"
        ] = (
            shifted
            .groupby(
                result["series"]
            )
            .rolling(
                window
            )
            .std()
            .reset_index(
                level=0,
                drop=True,
            )
        )


    # ------------------------------------------------------------------------
    # Calendar
    # ------------------------------------------------------------------------

    result[
        "month"
    ] = result[
        "date"
    ].dt.month


    result[
        "quarter"
    ] = result[
        "date"
    ].dt.quarter


    # ------------------------------------------------------------------------
    # Momentum
    # ------------------------------------------------------------------------

    log_value = np.log(
        result["value"]
    )


    for lag in MOMENTUM_LAGS:

        result[
            f"log_change_{lag}"
        ] = (
            log_value
            -
            log_value.groupby(
                result["series"]
            ).shift(
                lag
            )
        )


    return result


price_features = build_features(
    price
)

demand_features = build_features(
    demand
)


print(
    "Price feature rows:",
    len(price_features)
)

print(
    "Demand feature rows:",
    len(demand_features)
)


# ============================================================================
# FEATURE COLUMN AUDIT
# ============================================================================

print(
    "\n[7] FEATURE COLUMN AUDIT"
)


for name, df in [
    (
        "RO1_PRICE",
        price_features,
    ),
    (
        "RO1_DEMAND",
        demand_features,
    ),
]:

    missing = (
        set(feature_names)
        -
        set(df.columns)
    )


    assert not missing, (
        f"{name}: missing feature columns "
        f"{sorted(missing)}"
    )


    assert (
        df["date"]
        .notna()
        .all()
    )


    print(
        f"{name}: feature columns PASS"
    )


# ============================================================================
# TRAINING MINIMUM
# ============================================================================

print(
    "\n[8] TRAINING WINDOW SUFFICIENCY"
)


MINIMUM_TRAINING_MONTHS = 60


def calculate_required_history():

    maximum_lag = max(
        OWN_LAGS
    )

    maximum_rolling = max(
        ROLLING_WINDOWS
    )

    maximum_momentum = max(
        MOMENTUM_LAGS
    )

    maximum_feature_lookback = max(
        maximum_lag,
        maximum_rolling,
        maximum_momentum,
    )


    return maximum_feature_lookback


required_history = (
    calculate_required_history()
)


print(
    f"Maximum feature lookback: "
    f"{required_history} months"
)

print(
    f"Minimum model training history: "
    f"{MINIMUM_TRAINING_MONTHS} months"
)


assert (
    MINIMUM_TRAINING_MONTHS
    >
    required_history
)


print(
    "Training-window sufficiency: PASS"
)


# ============================================================================
# FORECAST ORIGIN / TARGET CHRONOLOGY
# ============================================================================

print(
    "\n[9] FORECAST CHRONOLOGY CONTRACT"
)


def audit_horizon_relationship(
    df,
    dataset_name,
):

    failures = []


    for horizon in HORIZONS:

        # Every possible origin must have target t+h
        # inside the observed data range.
        for series, group in (
            df.groupby(
                "series",
                sort=True,
            )
        ):

            dates = (
                group[
                    "date"
                ]
                .sort_values()
                .tolist()
            )


            date_set = set(
                dates
            )


            for origin in dates:

                target = (
                    origin
                    +
                    pd.DateOffset(
                        months=horizon
                    )
                )


                if target in date_set:

                    if not (
                        target
                        >
                        origin
                    ):

                        failures.append(
                            (
                                dataset_name,
                                series,
                                horizon,
                                origin,
                                target,
                            )
                        )


    print(
        f"{dataset_name}: "
        f"chronology failures = "
        f"{len(failures)}"
    )


    assert not failures


audit_horizon_relationship(
    price,
    "RO1_PRICE",
)

audit_horizon_relationship(
    demand,
    "RO1_DEMAND",
)


print(
    "Forecast chronology contract: PASS"
)


# ============================================================================
# FEATURE LEAKAGE CHECK
# ============================================================================

print(
    "\n[10] EXPLICIT FEATURE LEAKAGE CHECK"
)


def audit_feature_leakage(
    raw_df,
    feature_df,
    dataset_name,
):

    raw_lookup = (
        raw_df
        .set_index(
            [
                "series",
                "date",
            ]
        )[
            "value"
        ]
    )


    checked = 0


    for row in feature_df.itertuples(
        index=False
    ):

        origin = row.date
        series = row.series


        # --------------------------------------------------------------
        # Own lag checks
        # --------------------------------------------------------------

        for lag in OWN_LAGS:

            expected_date = (
                origin
                -
                pd.DateOffset(
                    months=lag
                )
            )


            key = (
                series,
                expected_date,
            )


            expected_value = (
                raw_lookup.get(
                    key,
                    np.nan,
                )
            )


            observed_value = getattr(
                row,
                f"lag_{lag}",
            )


            if np.isfinite(
                observed_value
            ):

                assert np.isclose(
                    observed_value,
                    expected_value,
                    atol=1e-10,
                    rtol=1e-10,
                )


        # --------------------------------------------------------------
        # Momentum checks
        # --------------------------------------------------------------

        for lag in MOMENTUM_LAGS:

            lag_date = (
                origin
                -
                pd.DateOffset(
                    months=lag
                )
            )


            current_value = (
                raw_lookup.get(
                    (
                        series,
                        origin,
                    ),
                    np.nan,
                )
            )


            lag_value = (
                raw_lookup.get(
                    (
                        series,
                        lag_date,
                    ),
                    np.nan,
                )
            )


            observed_change = getattr(
                row,
                f"log_change_{lag}",
            )


            if (
                np.isfinite(
                    observed_change
                )
                and
                np.isfinite(
                    current_value
                )
                and
                np.isfinite(
                    lag_value
                )
            ):

                expected_change = (
                    np.log(
                        current_value
                    )
                    -
                    np.log(
                        lag_value
                    )
                )


                assert np.isclose(
                    observed_change,
                    expected_change,
                    atol=1e-10,
                    rtol=1e-10,
                )


        checked += 1


    print(
        f"{dataset_name}: "
        f"checked {checked} rows"
    )

    print(
        f"{dataset_name}: "
        f"feature leakage audit PASS"
    )


audit_feature_leakage(
    price,
    price_features,
    "RO1_PRICE",
)

audit_feature_leakage(
    demand,
    demand_features,
    "RO1_DEMAND",
)


# ============================================================================
# FEATURE AVAILABILITY AT FORECAST ORIGIN
# ============================================================================

print(
    "\n[11] FORECAST-ORIGIN FEATURE AVAILABILITY"
)


def audit_feature_availability(
    df,
    dataset_name,
):

    valid_rows = 0


    for series, group in (
        df.groupby(
            "series",
            sort=True,
        )
    ):

        group = group.sort_values(
            "date"
        )


        for horizon in HORIZONS:

            eligible = group.loc[
                group["date"]
                +
                pd.DateOffset(
                    months=horizon
                )
                <=
                group["date"].max()
            ]


            if eligible.empty:
                continue


            # At least one valid complete-feature row must exist
            # before the target horizon.
            complete = eligible[
                feature_names
            ].notna().all(
                axis=1
            )


            valid_rows += int(
                complete.sum()
            )


    print(
        f"{dataset_name}: "
        f"complete feature-origin rows = "
        f"{valid_rows}"
    )


    assert valid_rows > 0


    print(
        f"{dataset_name}: "
        f"feature availability PASS"
    )


audit_feature_availability(
    price_features,
    "RO1_PRICE",
)

audit_feature_availability(
    demand_features,
    "RO1_DEMAND",
)


# ============================================================================
# VALIDATION / TEST BOUNDARY AUDIT
# ============================================================================

print(
    "\n[12] VALIDATION / TEST BOUNDARY AUDIT"
)


# Frozen boundaries from Step 22.

PRICE_VALIDATION_START = pd.Timestamp(
    "2022-07-01"
)

PRICE_VALIDATION_END = pd.Timestamp(
    "2024-06-01"
)

PRICE_TEST_START = pd.Timestamp(
    "2024-07-01"
)

PRICE_TEST_END = pd.Timestamp(
    "2026-06-01"
)


DEMAND_VALIDATION_START = pd.Timestamp(
    "2022-06-01"
)

DEMAND_VALIDATION_END = pd.Timestamp(
    "2024-05-01"
)

DEMAND_TEST_START = pd.Timestamp(
    "2024-06-01"
)

DEMAND_TEST_END = pd.Timestamp(
    "2026-05-01"
)


print(
    "Price validation:",
    PRICE_VALIDATION_START.date(),
    "→",
    PRICE_VALIDATION_END.date(),
)

print(
    "Price test:",
    PRICE_TEST_START.date(),
    "→",
    PRICE_TEST_END.date(),
)

print(
    "Demand validation:",
    DEMAND_VALIDATION_START.date(),
    "→",
    DEMAND_VALIDATION_END.date(),
)

print(
    "Demand test:",
    DEMAND_TEST_START.date(),
    "→",
    DEMAND_TEST_END.date(),
)


assert (
    PRICE_VALIDATION_END
    <
    PRICE_TEST_START
)

assert (
    DEMAND_VALIDATION_END
    <
    DEMAND_TEST_START
)


print(
    "Validation/test separation: PASS"
)


# ============================================================================
# COVID RETENTION AUDIT
# ============================================================================

print(
    "\n[13] COVID PERIOD RETENTION AUDIT"
)


COVID_START = pd.Timestamp(
    "2020-03-01"
)

COVID_END = pd.Timestamp(
    "2020-07-01"
)


def audit_covid_retention(
    df,
    dataset_name,
):

    covid = df.loc[
        df["date"].between(
            COVID_START,
            COVID_END,
        )
    ]


    print(
        f"{dataset_name}: "
        f"COVID-period observations = "
        f"{len(covid)}"
    )


    assert not covid.empty


    assert (
        covid["value"]
        .notna()
        .all()
    )


    print(
        f"{dataset_name}: "
        f"COVID observations retained: PASS"
    )


audit_covid_retention(
    price,
    "RO1_PRICE",
)

audit_covid_retention(
    demand,
    "RO1_DEMAND",
)


# ============================================================================
# DISTRIBUTION REPRESENTATION CONTRACT
# ============================================================================

print(
    "\n[14] DOWNSTREAM DISTRIBUTION CONTRACT"
)


distribution_contract = pd.DataFrame(
    [
        {
            "representation":
                "quantiles",

            "quantile_levels":
                str(QUANTILES),

            "primary_point":
                "q0.50",

            "interval_50":
                "q0.25-q0.75",

            "interval_80":
                "q0.10-q0.90",

            "downstream_use":
                "RO2 uncertainty propagation",
        },

        {
            "representation":
                "predictive_samples",

            "quantile_levels":
                "derived from samples",

            "primary_point":
                "sample median",

            "interval_50":
                "empirical 25th-75th percentiles",

            "interval_80":
                "empirical 10th-90th percentiles",

            "downstream_use":
                "Monte Carlo propagation / stochastic optimization",
        },
    ]
)


print(
    distribution_contract.to_string(
        index=False
    )
)


# ============================================================================
# SPECIFICATION SUMMARY
# ============================================================================

print(
    "\n[15] SPECIFICATION SUMMARY"
)


summary = pd.DataFrame(
    [
        {
            "item":
                "Targets",

            "price_series":
                len(
                    EXPECTED_PRICE_MATERIALS
                ),

            "demand_series":
                len(
                    EXPECTED_DEMAND_MATERIALS
                ),
        },

        {
            "item":
                "Forecast horizons",

            "price_series":
                str(HORIZONS),

            "demand_series":
                str(HORIZONS),
        },

        {
            "item":
                "Primary horizon",

            "price_series":
                PRIMARY_HORIZON,

            "demand_series":
                PRIMARY_HORIZON,
        },

        {
            "item":
                "Quantiles",

            "price_series":
                str(QUANTILES),

            "demand_series":
                str(QUANTILES),
        },

        {
            "item":
                "Own lags",

            "price_series":
                str(OWN_LAGS),

            "demand_series":
                str(OWN_LAGS),
        },

        {
            "item":
                "Rolling windows",

            "price_series":
                str(ROLLING_WINDOWS),

            "demand_series":
                str(ROLLING_WINDOWS),
        },

        {
            "item":
                "Cross-material features",

            "price_series":
                "Excluded from primary",

            "demand_series":
                "Excluded from primary",
        },

        {
            "item":
                "Model training",

            "price_series":
                "Not performed",

            "demand_series":
                "Not performed",
        },
    ]
)


print(
    summary.to_string(
        index=False
    )
)


# ============================================================================
# SAVE CONTRACT
# ============================================================================

print(
    "\n[16] SAVING STEP 26A CONTRACT"
)


contract_path = (
    OUTPUT_DIR
    / "RO1_step26a_probabilistic_contract.csv"
)


feature_path = (
    OUTPUT_DIR
    / "RO1_step26a_feature_contract.csv"
)


continuity_path = (
    OUTPUT_DIR
    / "RO1_step26a_continuity_audit.csv"
)


distribution_path = (
    OUTPUT_DIR
    / "RO1_step26a_distribution_contract.csv"
)


summary_path = (
    OUTPUT_DIR
    / "RO1_step26a_specification_summary.csv"
)


contract_rows = []


for dataset_name, materials in [
    (
        "RO1_PRICE",
        EXPECTED_PRICE_MATERIALS,
    ),
    (
        "RO1_DEMAND",
        EXPECTED_DEMAND_MATERIALS,
    ),
]:

    for material in materials:

        for horizon in HORIZONS:

            for quantile in QUANTILES:

                contract_rows.append(
                    {
                        "dataset":
                            dataset_name,

                        "material":
                            material,

                        "horizon":
                            horizon,

                        "quantile":
                            quantile,

                        "primary_horizon":
                            horizon
                            ==
                            PRIMARY_HORIZON,

                        "primary_point_quantile":
                            quantile
                            ==
                            0.50,
                    }
                )


contract_df = pd.DataFrame(
    contract_rows
)


contract_df.to_csv(
    contract_path,
    index=False,
)


pd.DataFrame(
    {
        "feature":
            feature_names,

        "feature_group":
            [
                (
                    "lag"
                    if feature.startswith(
                        "lag_"
                    )
                    else
                    "rolling"
                    if feature.startswith(
                        "rolling_"
                    )
                    else
                    "calendar"
                    if feature in
                    CALENDAR_FEATURES
                    else
                    "momentum"
                )
                for feature in feature_names
            ],
    }
).to_csv(
    feature_path,
    index=False,
)


pd.concat(
    [
        price_continuity,
        demand_continuity,
    ],
    ignore_index=True,
).to_csv(
    continuity_path,
    index=False,
)


distribution_contract.to_csv(
    distribution_path,
    index=False,
)


summary.to_csv(
    summary_path,
    index=False,
)


# ============================================================================
# FINAL ASSERTIONS
# ============================================================================

print(
    "\n[17] FINAL ASSERTIONS"
)


expected_contract_rows = (
    (
        len(
            EXPECTED_PRICE_MATERIALS
        )
        +
        len(
            EXPECTED_DEMAND_MATERIALS
        )
    )
    *
    len(HORIZONS)
    *
    len(QUANTILES)
)


assert (
    len(contract_df)
    ==
    expected_contract_rows
)


assert (
    contract_df[
        "quantile"
    ]
    .between(
        0,
        1,
    )
    .all()
)


assert (
    contract_df[
        "horizon"
    ]
    .isin(
        HORIZONS
    )
    .all()
)


assert (
    len(feature_names)
    ==
    5
    +
    6
    +
    2
    +
    2
)


assert (
    not price_continuity.empty
)

assert (
    not demand_continuity.empty
)

assert (
    price_continuity[
        "continuous"
    ].all()
)

assert (
    demand_continuity[
        "continuous"
    ].all()
)


print(
    "Target-series contract: PASS"
)

print(
    "Horizon contract: PASS"
)

print(
    "Quantile contract: PASS"
)

print(
    "Feature contract: PASS"
)

print(
    "Feature leakage audit: PASS"
)

print(
    "Training-window sufficiency: PASS"
)

print(
    "Chronology contract: PASS"
)

print(
    "Validation/test separation: PASS"
)

print(
    "COVID retention: PASS"
)

print(
    "Downstream distribution contract: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 26A COMPLETE"
)

print(
    "=" * 78
)

print(
    "\nProbabilistic forecasting specification is frozen."
)

print(
    "\nPrimary representation:"
)

print(
    "Predictive quantiles q={0.10,0.25,0.50,0.75,0.90}"
)

print(
    "\nPrimary horizon:"
)

print(
    "h=3 months"
)

print(
    "\nPrimary feature set:"
)

print(
    "own lags + rolling statistics + calendar + momentum"
)

print(
    "\nCross-material features:"
)

print(
    "reserved for ablation"
)

print(
    "\nNo probabilistic model has been trained."
)

print(
    "No deterministic model has been changed."
)

print(
    "\nRO1 STEP 26A: READY FOR PROBABILISTIC MODEL DEVELOPMENT"
)

print(
    "=" * 78
)