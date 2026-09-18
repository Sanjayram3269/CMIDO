"""
CMIDO RO1 — STEP 26B.1
PROBABILISTIC STATISTICAL BASELINE

Purpose
-------
Establish a conventional statistical probabilistic forecasting baseline
before developing probabilistic ML models.

Models
------
1. ETS
2. SARIMA

The model specifications are frozen from Step 24.
No model selection is performed using test data.

Forecast horizons
-----------------
1, 3, 6, 12 months

Primary horizon
---------------
3 months

Predictive quantiles
--------------------
q0.10, q0.25, q0.50, q0.75, q0.90

Intervals
---------
50% interval: q0.25 - q0.75
80% interval: q0.10 - q0.90

Evaluation
----------
Point:
    MAE
    RMSE

Probabilistic:
    Pinball loss
    Empirical coverage
    Mean interval width
    Coverage error
    Winkler interval score

Design
------
Expanding-window rolling-origin evaluation.

IMPORTANT:
------------
Split membership is horizon-specific and determined by the TARGET DATE,
matching the frozen Step 22 rolling-origin design.

Validation is used only for selecting the probabilistic statistical
baseline representation.

Test data remains untouched for model selection.

No ML model is trained.
No conformal calibration is performed.
No previous deterministic result is modified.
"""


# =============================================================================
# IMPORTS
# =============================================================================

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parents[2]

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

CLASSICAL_SPEC_FILE = (
    ROOT
    / "results"
    / "forecasting"
    / "classical"
    / "RO1_step24_selected_specifications.csv"
)

OUT_DIR = (
    ROOT
    / "results"
    / "forecasting"
    / "probabilistic_statistical"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# FROZEN EXPERIMENT CONTRACT
# =============================================================================

HORIZONS = [1, 3, 6, 12]

PRIMARY_HORIZON = 3

QUANTILES = [
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
]

INTERVALS = {
    "50": (0.25, 0.75),
    "80": (0.10, 0.90),
}

MIN_TRAINING_MONTHS = 60

# Number of simulated future paths used for ETS empirical predictive
# distributions.
ETS_SIMULATIONS = 2000

# Fixed seed for reproducibility of the empirical ETS predictive
# distribution.
ETS_RANDOM_SEED = 2601


# =============================================================================
# FROZEN TEMPORAL WINDOWS
# =============================================================================

VALIDATION_PRICE_START = pd.Timestamp(
    "2022-07-01"
)

VALIDATION_PRICE_END = pd.Timestamp(
    "2024-06-01"
)

TEST_PRICE_START = pd.Timestamp(
    "2024-07-01"
)

TEST_PRICE_END = pd.Timestamp(
    "2026-06-01"
)

VALIDATION_DEMAND_START = pd.Timestamp(
    "2022-06-01"
)

VALIDATION_DEMAND_END = pd.Timestamp(
    "2024-05-01"
)

TEST_DEMAND_START = pd.Timestamp(
    "2024-06-01"
)

TEST_DEMAND_END = pd.Timestamp(
    "2026-05-01"
)


# =============================================================================
# WARNING CONTROL
# =============================================================================

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
)

warnings.filterwarnings(
    "ignore",
    category=RuntimeWarning,
)


# =============================================================================
# BASIC UTILITIES
# =============================================================================

def fail(message: str) -> None:
    raise RuntimeError(message)


def require_columns(
    df: pd.DataFrame,
    columns: List[str],
    name: str,
) -> None:

    missing = [
        column
        for column in columns
        if column not in df.columns
    ]

    if missing:
        fail(
            f"{name}: missing required columns: "
            f"{missing}"
        )


# =============================================================================
# DATA LOADING
# =============================================================================

def load_long_dataframe(
    path: Path,
    dataset_name: str,
) -> pd.DataFrame:

    if not path.exists():
        fail(
            f"{dataset_name}: file not found:\n{path}"
        )

    df = pd.read_csv(path)

    require_columns(
        df,
        [
            "date",
            "DataSeries",
        ],
        dataset_name,
    )

    value_candidates = [
        "price_dollars_per_tonne",
        "demand_thousand_tonnes",
        "value",
        "Value",
    ]

    value_col = None

    for candidate in value_candidates:

        if candidate in df.columns:

            value_col = candidate
            break

    if value_col is None:

        fail(
            f"{dataset_name}: could not identify "
            f"value column.\n"
            f"Available columns: {list(df.columns)}"
        )

    df = df.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    df["value"] = pd.to_numeric(
        df[value_col],
        errors="coerce",
    )

    if df["date"].isna().any():

        fail(
            f"{dataset_name}: invalid dates detected."
        )

    if df["value"].isna().any():

        fail(
            f"{dataset_name}: missing or "
            f"non-numeric values detected."
        )

    df = (
        df[
            [
                "date",
                "DataSeries",
                "value",
            ]
        ]
        .rename(
            columns={
                "DataSeries": "series"
            }
        )
        .sort_values(
            [
                "series",
                "date",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    duplicate_count = int(
        df.duplicated(
            [
                "series",
                "date",
            ]
        ).sum()
    )

    if duplicate_count:

        fail(
            f"{dataset_name}: duplicate "
            f"series-date rows = "
            f"{duplicate_count}"
        )

    if (
        df["value"] <= 0
    ).any():

        fail(
            f"{dataset_name}: non-positive "
            f"observations detected."
        )

    return df


# =============================================================================
# SERIES CONVERSION
# =============================================================================

def series_to_monthly(
    df: pd.DataFrame,
    series: str,
) -> pd.Series:

    subset = (
        df[
            df["series"] == series
        ]
        .set_index("date")["value"]
        .sort_index()
    )

    if subset.empty:

        fail(
            f"Series not found: {series}"
        )

    subset.index = (
        pd.DatetimeIndex(
            subset.index
        )
        .to_period("M")
        .to_timestamp()
    )

    subset = subset[
        ~subset.index.duplicated(
            keep="first"
        )
    ]

    return subset.astype(float)


# =============================================================================
# SARIMA SPECIFICATION PARSER
# =============================================================================

def parse_sarima_order(
    value: str,
) -> Tuple[
    Tuple[int, int, int],
    Tuple[int, int, int, int],
]:

    matches = re.findall(
        r"\(([^()]*)\)",
        str(value),
    )

    if len(matches) < 2:

        fail(
            "Could not parse SARIMA "
            f"specification: {value}"
        )

    order = tuple(
        int(x.strip())
        for x in matches[0].split(",")
    )

    seasonal_order = tuple(
        int(x.strip())
        for x in matches[1].split(",")
    )

    if len(order) != 3:

        fail(
            f"Invalid ARIMA order: {order}"
        )

    if len(seasonal_order) != 4:

        fail(
            "Invalid seasonal ARIMA "
            f"order: {seasonal_order}"
        )

    return (
        order,
        seasonal_order,
    )


# =============================================================================
# LOAD FROZEN STEP 24 SPECIFICATIONS
# =============================================================================

def load_frozen_classical_specs() -> pd.DataFrame:
    """
    Step 24 stores one row per selected model.

    Required columns:
        dataset
        series
        model_family
        selected_model
        order
        seasonal_order
        selection_method

    ETS and SARIMA specifications are reconstructed into one row
    per dataset-series combination.
    """

    if not CLASSICAL_SPEC_FILE.exists():

        fail(
            "Frozen Step 24 specification "
            "file not found:\n"
            f"{CLASSICAL_SPEC_FILE}"
        )

    specs = pd.read_csv(
        CLASSICAL_SPEC_FILE
    )

    print(
        "\n[1] FROZEN STEP 24 SPECIFICATIONS"
    )

    print(
        f"Rows: {len(specs)}"
    )

    print(
        f"Columns: {list(specs.columns)}"
    )

    required = {
        "dataset",
        "series",
        "model_family",
        "selected_model",
        "order",
        "seasonal_order",
        "selection_method",
    }

    missing = (
        required
        - set(specs.columns)
    )

    if missing:

        fail(
            "Frozen Step 24 specification "
            "file is missing columns: "
            f"{sorted(missing)}"
        )

    specs = specs.copy()

    for column in required:

        specs[column] = (
            specs[column]
            .astype(str)
            .str.strip()
        )

    specs[
        "model_family_normalized"
    ] = (
        specs[
            "model_family"
        ]
        .str.upper()
        .str.replace(
            "-",
            "",
            regex=False,
        )
        .str.replace(
            "_",
            "",
            regex=False,
        )
        .str.replace(
            " ",
            "",
            regex=False,
        )
    )

    ets_rows = specs[
        specs[
            "model_family_normalized"
        ].str.contains(
            "ETS",
            regex=False,
            na=False,
        )
    ].copy()

    sarima_rows = specs[
        specs[
            "model_family_normalized"
        ].str.contains(
            "SARIMA",
            regex=False,
            na=False,
        )
    ].copy()

    if ets_rows.empty:

        fail(
            "No ETS rows found in frozen "
            "Step 24 specifications."
        )

    if sarima_rows.empty:

        fail(
            "No SARIMA rows found in frozen "
            "Step 24 specifications."
        )

    ets_duplicates = int(
        ets_rows.duplicated(
            [
                "dataset",
                "series",
            ]
        ).sum()
    )

    sarima_duplicates = int(
        sarima_rows.duplicated(
            [
                "dataset",
                "series",
            ]
        ).sum()
    )

    if ets_duplicates:

        fail(
            "Multiple ETS specifications "
            "found for the same "
            f"dataset-series: {ets_duplicates}"
        )

    if sarima_duplicates:

        fail(
            "Multiple SARIMA specifications "
            "found for the same "
            f"dataset-series: {sarima_duplicates}"
        )

    ets_compact = (
        ets_rows[
            [
                "dataset",
                "series",
                "selected_model",
            ]
        ]
        .rename(
            columns={
                "selected_model": "ets_spec"
            }
        )
    )

    sarima_compact = sarima_rows[
        [
            "dataset",
            "series",
            "order",
            "seasonal_order",
        ]
    ].copy()

    sarima_compact[
        "sarima_spec"
    ] = (
        sarima_compact[
            "order"
        ]
        + sarima_compact[
            "seasonal_order"
        ]
    )

    sarima_compact = (
        sarima_compact[
            [
                "dataset",
                "series",
                "sarima_spec",
            ]
        ]
    )

    out = ets_compact.merge(
        sarima_compact,
        on=[
            "dataset",
            "series",
        ],
        how="outer",
        validate="one_to_one",
    )

    if out["ets_spec"].isna().any():

        missing_ets = out.loc[
            out["ets_spec"].isna(),
            [
                "dataset",
                "series",
            ],
        ]

        fail(
            "Missing ETS specification:\n"
            f"{missing_ets.to_string(index=False)}"
        )

    if out["sarima_spec"].isna().any():

        missing_sarima = out.loc[
            out["sarima_spec"].isna(),
            [
                "dataset",
                "series",
            ],
        ]

        fail(
            "Missing SARIMA specification:\n"
            f"{missing_sarima.to_string(index=False)}"
        )

    required_price = {
        "Cement In Bulk (Ordinary Portland Cement)",
        "Concreting Sand",
        "Granite (20mm Aggregate)",
        "Ready Mixed Concrete",
        "Steel Reinforcement Bars (16-32mm High Tensile)",
    }

    required_demand = {
        "Cement",
        "Granite",
        "Ready-Mixed Concrete",
        "Steel Reinforcement Bars",
    }

    price_rows = out[
        out["dataset"].str.contains(
            "PRICE",
            case=False,
            na=False,
        )
    ]

    demand_rows = out[
        out["dataset"].str.contains(
            "DEMAND",
            case=False,
            na=False,
        )
    ]

    missing_price = (
        required_price
        - set(price_rows["series"])
    )

    missing_demand = (
        required_demand
        - set(demand_rows["series"])
    )

    if missing_price:

        fail(
            "Missing frozen price "
            f"specifications: {sorted(missing_price)}"
        )

    if missing_demand:

        fail(
            "Missing frozen demand "
            f"specifications: {sorted(missing_demand)}"
        )

    assert len(price_rows) == 5
    assert len(demand_rows) == 4

    print(
        "\nFrozen specifications:"
    )

    for _, row in out.sort_values(
        [
            "dataset",
            "series",
        ]
    ).iterrows():

        print(
            f"  {row['dataset']} | "
            f"{row['series']} | "
            f"ETS={row['ets_spec']} | "
            f"SARIMA={row['sarima_spec']}"
        )

    print(
        f"\nETS specifications: "
        f"{len(ets_rows)}"
    )

    print(
        f"SARIMA specifications: "
        f"{len(sarima_rows)}"
    )

    print(
        "FROZEN SPECIFICATION CONTRACT: PASS"
    )

    return out[
        [
            "dataset",
            "series",
            "ets_spec",
            "sarima_spec",
        ]
    ].copy()


# =============================================================================
# HORIZON-SPECIFIC ROLLING-ORIGIN WINDOWS
# =============================================================================

def get_origins(
    series: pd.Series,
    validation_start: pd.Timestamp,
    validation_end: pd.Timestamp,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
) -> Dict[
    str,
    Dict[int, List[pd.Timestamp]]
]:
    """
    Horizon-specific rolling-origin design.

    A forecast origin belongs to a split according to the TARGET DATE
    for that specific horizon.

    This is deliberately aligned with Step 22.
    """

    dates = pd.DatetimeIndex(
        series.index
    )

    validation_origins = {
        h: []
        for h in HORIZONS
    }

    test_origins = {
        h: []
        for h in HORIZONS
    }

    for origin in dates:

        train_count = int(
            (
                dates <= origin
            ).sum()
        )

        if (
            train_count
            < MIN_TRAINING_MONTHS
        ):
            continue

        for h in HORIZONS:

            target_date = (
                origin
                + pd.DateOffset(
                    months=h
                )
            )

            if target_date not in dates:
                continue

            # Validation membership based on target.
            if (
                validation_start
                <= target_date
                <= validation_end
            ):

                validation_origins[h].append(
                    origin
                )

            # Test membership based on target.
            if (
                test_start
                <= target_date
                <= test_end
            ):

                test_origins[h].append(
                    origin
                )

    return {
        "validation": validation_origins,
        "test": test_origins,
    }


# =============================================================================
# ETS FITTING
# =============================================================================

def fit_ets(
    y_train: pd.Series,
    spec: str,
):
    """
    Fit the exact frozen Step 24 ETS structure.
    """

    spec = str(
        spec
    ).strip()

    if spec == "ETS_A_N_N":

        model = ExponentialSmoothing(
            y_train,
            trend=None,
            seasonal=None,
            initialization_method="estimated",
        )

    elif spec == "ETS_AAd_N":

        model = ExponentialSmoothing(
            y_train,
            trend="add",
            damped_trend=True,
            seasonal=None,
            initialization_method="estimated",
        )

    elif spec == "ETS_AAd_A":

        model = ExponentialSmoothing(
            y_train,
            trend="add",
            damped_trend=True,
            seasonal="add",
            seasonal_periods=12,
            initialization_method="estimated",
        )

    else:

        fail(
            f"Unsupported frozen ETS "
            f"specification: {spec}"
        )

    return model.fit(
        optimized=True,
        use_brute=True,
    )


# =============================================================================
# SARIMA FITTING
# =============================================================================

def fit_sarima(
    y_train: pd.Series,
    spec: str,
):

    order, seasonal_order = (
        parse_sarima_order(spec)
    )

    model = SARIMAX(
        y_train,
        order=order,
        seasonal_order=seasonal_order,
        trend="n",
        enforce_stationarity=False,
        enforce_invertibility=False,
    )

    return model.fit(
        disp=False,
    )


# =============================================================================
# SARIMA PREDICTIVE DISTRIBUTION
# =============================================================================

def sarima_predictive_distribution(
    fitted,
    steps: int,
) -> Dict[
    float,
    np.ndarray
]:
    """
    SARIMA predictive distribution derived directly from the
    fitted state-space model's forecast mean and forecast variance.

    Quantiles are obtained under the fitted model's Gaussian
    predictive-error representation.
    """

    prediction = fitted.get_forecast(
        steps=steps
    )

    mean = np.asarray(
        prediction.predicted_mean,
        dtype=float,
    )

    variance = np.asarray(
        prediction.var_pred_mean,
        dtype=float,
    )

    if len(mean) != steps:

        fail(
            "SARIMA forecast length "
            "mismatch."
        )

    if len(variance) != steps:

        fail(
            "SARIMA predictive variance "
            "length mismatch."
        )

    if not np.isfinite(mean).all():

        fail(
            "SARIMA forecast contains "
            "non-finite values."
        )

    if not np.isfinite(variance).all():

        fail(
            "SARIMA forecast variance "
            "contains non-finite values."
        )

    variance = np.maximum(
        variance,
        0.0,
    )

    std = np.sqrt(
        variance
    )

    from scipy.stats import norm

    result = {}

    for q in QUANTILES:

        result[q] = (
            mean
            + norm.ppf(q) * std
        )

    return result


# =============================================================================
# ETS PREDICTIVE DISTRIBUTION
# =============================================================================

def ets_predictive_distribution(
    fitted,
    steps: int,
    seed: int,
) -> Dict[
    float,
    np.ndarray
]:
    """
    Generate an empirical ETS predictive distribution using the
    fitted ETS model's native state-space simulation.

    The frozen ETS specification is not changed. The fitted model
    generates 2,000 future paths and the required predictive quantiles
    are extracted empirically from those paths.

    statsmodels Holt-Winters simulate() accepts an integer seed or a
    legacy np.random.RandomState, not a numpy Generator. Therefore the
    integer seed is passed directly. The simulations are generated in
    one native call using repetitions=ETS_SIMULATIONS rather than making
    2,000 separate simulate() calls.
    """

    if not hasattr(
        fitted,
        "simulate",
    ):
        raise RuntimeError(
            "ETS fitted object does not provide the "
            "native simulate() interface required for "
            "the empirical predictive distribution."
        )

    if (
        not isinstance(
            steps,
            (int, np.integer),
        )
        or steps <= 0
    ):
        raise RuntimeError(
            f"Invalid ETS simulation horizon: {steps}"
        )

    # -------------------------------------------------------------------------
    # Native ETS state-space simulation.
    # -------------------------------------------------------------------------

    try:

        simulations = fitted.simulate(
            nsimulations=int(steps),
            anchor="end",
            repetitions=int(ETS_SIMULATIONS),
            random_state=int(seed),
        )

    except (TypeError, ValueError):

        # Compatibility route for versions that reject an integer seed but
        # accept the legacy RandomState object.
        random_state = np.random.RandomState(
            int(seed)
        )

        try:

            simulations = fitted.simulate(
                nsimulations=int(steps),
                anchor="end",
                repetitions=int(ETS_SIMULATIONS),
                random_state=random_state,
            )

        except Exception as exc:

            raise RuntimeError(
                "Unable to generate the native ETS "
                "empirical predictive distribution. "
                f"Underlying error: {exc}"
            ) from exc

    except Exception as exc:

        raise RuntimeError(
            "Unable to generate the native ETS "
            "empirical predictive distribution. "
            f"Underlying error: {exc}"
        ) from exc

    # -------------------------------------------------------------------------
    # Validate simulation output.
    # -------------------------------------------------------------------------

    simulations = np.asarray(
        simulations,
        dtype=float,
    )

    if simulations.ndim != 2:

        raise RuntimeError(
            "ETS simulation output must be "
            "two-dimensional."
        )

    if simulations.shape[0] != int(steps):

        raise RuntimeError(
            "ETS simulation horizon mismatch: "
            f"shape={simulations.shape}, "
            f"steps={steps}"
        )

    if simulations.shape[1] != int(
        ETS_SIMULATIONS
    ):

        raise RuntimeError(
            "Unexpected number of ETS simulation "
            f"paths: {simulations.shape[1]}; "
            f"expected {ETS_SIMULATIONS}."
        )

    if not np.isfinite(
        simulations
    ).all():

        raise RuntimeError(
            "ETS simulations contain "
            "non-finite values."
        )

    # Do not clip negative simulated values here. Clipping would alter the
    # predictive distribution generated by the frozen ETS model.

    result = {}

    for q in QUANTILES:

        result[q] = np.quantile(
            simulations,
            q,
            axis=1,
        )

    return result


# =============================================================================
# METRICS
# =============================================================================

def pinball_loss(
    actual: np.ndarray,
    prediction: np.ndarray,
    q: float,
) -> float:

    actual = np.asarray(
        actual,
        dtype=float,
    )

    prediction = np.asarray(
        prediction,
        dtype=float,
    )

    error = (
        actual
        - prediction
    )

    return float(
        np.mean(
            np.maximum(
                q * error,
                (q - 1.0) * error,
            )
        )
    )


def interval_metrics(
    actual: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    nominal_coverage: float,
) -> Dict[str, float]:

    actual = np.asarray(
        actual,
        dtype=float,
    )

    lower = np.asarray(
        lower,
        dtype=float,
    )

    upper = np.asarray(
        upper,
        dtype=float,
    )

    if (
        lower > upper
    ).any():

        raise RuntimeError(
            "Invalid interval: lower "
            "bound exceeds upper bound."
        )

    covered = (
        (actual >= lower)
        & (actual <= upper)
    )

    empirical_coverage = float(
        np.mean(covered)
    )

    mean_width = float(
        np.mean(
            upper - lower
        )
    )

    coverage_error = float(
        empirical_coverage
        - nominal_coverage
    )

    alpha = (
        1.0
        - nominal_coverage
    )

    winkler = (
        upper
        - lower
        + (
            2.0 / alpha
        )
        * (
            lower - actual
        )
        * (
            actual < lower
        )
        + (
            2.0 / alpha
        )
        * (
            actual - upper
        )
        * (
            actual > upper
        )
    )

    return {
        "coverage": empirical_coverage,
        "mean_interval_width": mean_width,
        "coverage_error": coverage_error,
        "winkler_score": float(
            np.mean(winkler)
        ),
    }


def point_metrics(
    actual: np.ndarray,
    prediction: np.ndarray,
) -> Dict[str, float]:

    error = (
        actual
        - prediction
    )

    return {
        "MAE": float(
            np.mean(
                np.abs(error)
            )
        ),
        "RMSE": float(
            np.sqrt(
                np.mean(
                    error ** 2
                )
            )
        ),
    }


# =============================================================================
# FORECAST GENERATION
# =============================================================================

def generate_forecast(
    y: pd.Series,
    origin: pd.Timestamp,
    max_horizon: int,
    model_name: str,
    spec: str,
) -> Dict[
    float,
    np.ndarray
]:

    train = y.loc[
        y.index <= origin
    ].copy()

    if (
        len(train)
        < MIN_TRAINING_MONTHS
    ):

        raise RuntimeError(
            f"Insufficient training history "
            f"at {origin.date()}: "
            f"{len(train)} months."
        )

    if model_name == "ETS":

        fitted = fit_ets(
            train,
            spec,
        )

        return ets_predictive_distribution(
            fitted,
            max_horizon,
            seed=ETS_RANDOM_SEED,
        )

    if model_name == "SARIMA":

        fitted = fit_sarima(
            train,
            spec,
        )

        return sarima_predictive_distribution(
            fitted,
            max_horizon,
        )

    raise RuntimeError(
        f"Unsupported model: "
        f"{model_name}"
    )


# =============================================================================
# EVALUATION ENGINE
# =============================================================================

def evaluate_split(
    dataset: str,
    df: pd.DataFrame,
    specs: pd.DataFrame,
    split: str,
    validation_start: pd.Timestamp,
    validation_end: pd.Timestamp,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
) -> Tuple[
    pd.DataFrame,
    pd.DataFrame,
]:

    rows = []

    error_rows = []

    dataset_specs = specs[
        specs["dataset"].str.contains(
            dataset,
            case=False,
            na=False,
        )
    ].copy()

    if dataset_specs.empty:

        fail(
            f"No frozen specifications "
            f"found for {dataset}"
        )

    for _, spec_row in dataset_specs.iterrows():

        series_name = spec_row[
            "series"
        ]

        y = series_to_monthly(
            df,
            series_name,
        )

        windows = get_origins(
            y,
            validation_start,
            validation_end,
            test_start,
            test_end,
        )

        origins_by_horizon = (
            windows[split]
        )

        print(
            f"\n{dataset} | "
            f"{series_name} | "
            f"{split} horizon-specific origins:"
        )

        for h in HORIZONS:

            print(
                f"  h={h}: "
                f"{len(origins_by_horizon[h])} origins"
            )

        for model_name, spec_col in [
            ("ETS", "ets_spec"),
            ("SARIMA", "sarima_spec"),
        ]:

            frozen_spec = spec_row[
                spec_col
            ]

            for h in HORIZONS:

                origins = (
                    origins_by_horizon[h]
                )

                for origin in origins:

                    try:

                        distribution = (
                            generate_forecast(
                                y=y,
                                origin=origin,
                                max_horizon=h,
                                model_name=model_name,
                                spec=frozen_spec,
                            )
                        )

                        target_date = (
                            origin
                            + pd.DateOffset(
                                months=h
                            )
                        )

                        actual = float(
                            y.loc[
                                target_date
                            ]
                        )

                        record = {
                            "dataset": dataset,
                            "split": split,
                            "series": series_name,
                            "model": model_name,
                            "specification": frozen_spec,
                            "forecast_origin": origin,
                            "target_date": target_date,
                            "horizon": h,
                            "actual": actual,
                        }

                        for q in QUANTILES:

                            values = (
                                distribution[q]
                            )

                            if len(values) != h:

                                raise RuntimeError(
                                    "Predictive "
                                    "distribution "
                                    "length mismatch."
                                )

                            prediction = float(
                                values[h - 1]
                            )

                            record[
                                f"q{int(q * 100):02d}"
                            ] = prediction

                        rows.append(
                            record
                        )

                    except Exception as exc:

                        error_rows.append(
                            {
                                "dataset": dataset,
                                "split": split,
                                "series": series_name,
                                "model": model_name,
                                "specification": frozen_spec,
                                "forecast_origin": origin,
                                "horizon": h,
                                "error": str(exc),
                            }
                        )

    forecasts = pd.DataFrame(
        rows
    )

    errors = pd.DataFrame(
        error_rows
    )

    return (
        forecasts,
        errors,
    )


# =============================================================================
# METRIC AGGREGATION
# =============================================================================

def calculate_metrics(
    forecasts: pd.DataFrame,
) -> pd.DataFrame:

    if forecasts.empty:

        fail(
            "No probabilistic forecast "
            "records were generated."
        )

    records = []

    group_columns = [
        "dataset",
        "split",
        "series",
        "model",
        "horizon",
    ]

    for (
        dataset,
        split,
        series,
        model,
        horizon,
    ), group in forecasts.groupby(
        group_columns,
        sort=True,
    ):

        actual = group[
            "actual"
        ].to_numpy(
            dtype=float
        )

        q10 = group[
            "q10"
        ].to_numpy(
            dtype=float
        )

        q25 = group[
            "q25"
        ].to_numpy(
            dtype=float
        )

        q50 = group[
            "q50"
        ].to_numpy(
            dtype=float
        )

        q75 = group[
            "q75"
        ].to_numpy(
            dtype=float
        )

        q90 = group[
            "q90"
        ].to_numpy(
            dtype=float
        )

        point = point_metrics(
            actual,
            q50,
        )

        interval50 = interval_metrics(
            actual,
            q25,
            q75,
            nominal_coverage=0.50,
        )

        interval80 = interval_metrics(
            actual,
            q10,
            q90,
            nominal_coverage=0.80,
        )

        row = {
            "dataset": dataset,
            "split": split,
            "series": series,
            "model": model,
            "horizon": horizon,
            "n_forecasts": len(group),

            "MAE": point["MAE"],
            "RMSE": point["RMSE"],

            "pinball_q10": pinball_loss(
                actual,
                q10,
                0.10,
            ),

            "pinball_q25": pinball_loss(
                actual,
                q25,
                0.25,
            ),

            "pinball_q50": pinball_loss(
                actual,
                q50,
                0.50,
            ),

            "pinball_q75": pinball_loss(
                actual,
                q75,
                0.75,
            ),

            "pinball_q90": pinball_loss(
                actual,
                q90,
                0.90,
            ),

            "coverage_50": interval50[
                "coverage"
            ],

            "interval_width_50": interval50[
                "mean_interval_width"
            ],

            "coverage_error_50": interval50[
                "coverage_error"
            ],

            "winkler_50": interval50[
                "winkler_score"
            ],

            "coverage_80": interval80[
                "coverage"
            ],

            "interval_width_80": interval80[
                "mean_interval_width"
            ],

            "coverage_error_80": interval80[
                "coverage_error"
            ],

            "winkler_80": interval80[
                "winkler_score"
            ],
        }

        row[
            "mean_pinball"
        ] = float(
            np.mean(
                [
                    row[
                        "pinball_q10"
                    ],
                    row[
                        "pinball_q25"
                    ],
                    row[
                        "pinball_q50"
                    ],
                    row[
                        "pinball_q75"
                    ],
                    row[
                        "pinball_q90"
                    ],
                ]
            )
        )

        records.append(
            row
        )

    return pd.DataFrame(
        records
    )


# =============================================================================
# VALIDATION-ONLY MODEL SELECTION
# =============================================================================

def select_validation_baseline(
    metrics: pd.DataFrame,
) -> pd.DataFrame:

    validation = metrics[
        (
            metrics["split"]
            == "validation"
        )
        & (
            metrics["horizon"]
            == PRIMARY_HORIZON
        )
    ].copy()

    if validation.empty:

        fail(
            "No validation metrics "
            "available for probabilistic "
            "model selection."
        )

    selected_rows = []

    for (
        dataset,
        series,
    ), group in validation.groupby(
        [
            "dataset",
            "series",
        ],
        sort=True,
    ):

        group = group.sort_values(
            [
                "mean_pinball",
                "winkler_80",
                "MAE",
            ]
        )

        selected = (
            group.iloc[0]
        )

        selected_rows.append(
            {
                "dataset": dataset,
                "series": series,
                "primary_horizon": PRIMARY_HORIZON,
                "selected_model": selected[
                    "model"
                ],
                "selected_mean_pinball": selected[
                    "mean_pinball"
                ],
                "selected_winkler_80": selected[
                    "winkler_80"
                ],
                "selected_coverage_50": selected[
                    "coverage_50"
                ],
                "selected_coverage_80": selected[
                    "coverage_80"
                ],
                "selected_MAE": selected[
                    "MAE"
                ],
                "selected_RMSE": selected[
                    "RMSE"
                ],
                "selection_basis": (
                    "Validation mean pinball "
                    "loss across "
                    "q0.10/q0.25/q0.50/q0.75/q0.90; "
                    "Winkler-80 and MAE used "
                    "as tie-break diagnostics."
                ),
            }
        )

    return pd.DataFrame(
        selected_rows
    )


# =============================================================================
# DATA CONTRACT / FORECAST AUDITS
# =============================================================================

def audit_forecast_records(
    forecasts: pd.DataFrame,
) -> None:

    required_columns = [
        "dataset",
        "split",
        "series",
        "model",
        "specification",
        "forecast_origin",
        "target_date",
        "horizon",
        "actual",
        "q10",
        "q25",
        "q50",
        "q75",
        "q90",
    ]

    missing = (
        set(required_columns)
        - set(forecasts.columns)
    )

    assert not missing, (
        f"Missing forecast columns: "
        f"{sorted(missing)}"
    )

    numeric_columns = [
        "actual",
        "q10",
        "q25",
        "q50",
        "q75",
        "q90",
    ]

    assert np.isfinite(
        forecasts[
            numeric_columns
        ].to_numpy()
    ).all()

    # Quantile monotonicity.
    assert (
        forecasts["q10"]
        <= forecasts["q25"]
    ).all()

    assert (
        forecasts["q25"]
        <= forecasts["q50"]
    ).all()

    assert (
        forecasts["q50"]
        <= forecasts["q75"]
    ).all()

    assert (
        forecasts["q75"]
        <= forecasts["q90"]
    ).all()

    # Forecast chronology.
    assert (
        forecasts["target_date"]
        > forecasts["forecast_origin"]
    ).all()

    # Correct horizon.
    expected_target = (
        forecasts["forecast_origin"]
        + pd.to_timedelta(
            forecasts["horizon"],
            unit="D",
        )
    )

    # The above day conversion is NOT used for the actual assertion because
    # month horizons are calendar-based. Validate using DateOffset row-wise.
    chronology_ok = []

    for _, row in forecasts.iterrows():

        expected = (
            row["forecast_origin"]
            + pd.DateOffset(
                months=int(
                    row["horizon"]
                )
            )
        )

        chronology_ok.append(
            pd.Timestamp(
                expected
            )
            == pd.Timestamp(
                row["target_date"]
            )
        )

    assert all(
        chronology_ok
    )

    # Duplicate protection.
    duplicate_count = int(
        forecasts.duplicated(
            [
                "dataset",
                "split",
                "series",
                "model",
                "forecast_origin",
                "horizon",
            ]
        ).sum()
    )

    assert duplicate_count == 0

    # Expected models.
    assert set(
        forecasts["model"].unique()
    ) == {
        "ETS",
        "SARIMA",
    }

    # Expected horizons.
    assert set(
        forecasts["horizon"].unique()
    ) == set(HORIZONS)


# =============================================================================
# FINAL ASSERTIONS
# =============================================================================

def run_assertions(
    forecasts: pd.DataFrame,
    metrics: pd.DataFrame,
    selected: pd.DataFrame,
    errors: pd.DataFrame,
) -> None:

    print(
        "\n[FINAL ASSERTIONS]"
    )

    assert not forecasts.empty

    print(
        "Forecast generation: PASS"
    )

    assert errors.empty, (
        "Forecast failures detected:\n"
        f"{errors.head(20).to_string(index=False)}"
    )

    print(
        "Forecast failure audit: PASS"
    )

    audit_forecast_records(
        forecasts
    )

    print(
        "Forecast record integrity: PASS"
    )

    required_quantiles = [
        "q10",
        "q25",
        "q50",
        "q75",
        "q90",
    ]

    for column in required_quantiles:

        assert column in forecasts.columns

    print(
        "Quantile columns: PASS"
    )

    print(
        "Quantile monotonicity: PASS"
    )

    assert set(
        forecasts["model"].unique()
    ) == {
        "ETS",
        "SARIMA",
    }

    print(
        "Model coverage: PASS"
    )

    assert set(
        forecasts["horizon"].unique()
    ) == set(HORIZONS)

    print(
        "Horizon coverage: PASS"
    )

    assert set(
        forecasts["split"].unique()
    ) == {
        "validation",
        "test",
    }

    print(
        "Validation/test coverage: PASS"
    )

    assert (
        metrics["n_forecasts"]
        > 0
    ).all()

    print(
        "Metric record coverage: PASS"
    )

    assert len(selected) == 9

    print(
        "Validation-only selection coverage: PASS"
    )

    # -------------------------------------------------------------------------
    # Verify every material/model/horizon has the expected number of forecasts.
    #
    # Step 22 gives 24 origins per horizon for the complete validation/test
    # design. This is checked explicitly here.
    # -------------------------------------------------------------------------

    expected_n = 24

    counts = (
        forecasts.groupby(
            [
                "dataset",
                "split",
                "series",
                "model",
                "horizon",
            ]
        )
        .size()
    )

    assert (
        counts == expected_n
    ).all(), (
        "Unexpected forecast count detected. "
        f"Expected {expected_n} per "
        "dataset/split/series/model/horizon."
    )

    print(
        "24-origin horizon-specific coverage: PASS"
    )

    # Expected total records:
    #
    # 9 series × 2 models × 2 splits ×
    # 4 horizons × 24 origins = 3456
    expected_total = (
        9
        * 2
        * 2
        * 4
        * 24
    )

    assert (
        len(forecasts)
        == expected_total
    ), (
        f"Expected {expected_total} "
        f"forecast records, found "
        f"{len(forecasts)}"
    )

    print(
        "Total forecast record count: PASS"
    )

    assert not metrics[
        metrics["split"] == "test"
    ].empty

    print(
        "Frozen test evaluation availability: PASS"
    )

    print(
        "\nALL STEP 26B.1 ASSERTIONS: PASS"
    )


# =============================================================================
# PRIMARY SUMMARY
# =============================================================================

def print_primary_summary(
    metrics: pd.DataFrame,
) -> None:

    print(
        "\n[7] PRIMARY HORIZON — h=3"
    )

    primary = metrics[
        metrics["horizon"]
        == PRIMARY_HORIZON
    ].copy()

    columns = [
        "dataset",
        "split",
        "series",
        "model",
        "n_forecasts",
        "MAE",
        "RMSE",
        "mean_pinball",
        "coverage_50",
        "interval_width_50",
        "coverage_80",
        "interval_width_80",
        "winkler_80",
    ]

    print(
        primary[
            columns
        ].to_string(
            index=False
        )
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print(
        "=" * 78
    )

    print(
        "CMIDO RO1 — STEP 26B.1"
    )

    print(
        "PROBABILISTIC STATISTICAL BASELINE"
    )

    print(
        "=" * 78
    )

    # =========================================================================
    # 1. LOAD DATA
    # =========================================================================

    print(
        "\n[1] LOADING DATA"
    )

    price = load_long_dataframe(
        PRICE_FILE,
        "RO1_PRICE",
    )

    demand = load_long_dataframe(
        DEMAND_FILE,
        "RO1_DEMAND",
    )

    print(
        f"Price rows: {len(price)}"
    )

    print(
        f"Demand rows: {len(demand)}"
    )

    # =========================================================================
    # 2. FROZEN SPECIFICATIONS
    # =========================================================================

    specs = (
        load_frozen_classical_specs()
    )

    # =========================================================================
    # 3. VALIDATION
    # =========================================================================

    print(
        "\n" + "=" * 78
    )

    print(
        "[2] VALIDATION — "
        "PROBABILISTIC STATISTICAL BASELINES"
    )

    print(
        "=" * 78
    )

    price_val, price_val_errors = (
        evaluate_split(
            dataset="RO1_PRICE",
            df=price,
            specs=specs,
            split="validation",
            validation_start=(
                VALIDATION_PRICE_START
            ),
            validation_end=(
                VALIDATION_PRICE_END
            ),
            test_start=(
                TEST_PRICE_START
            ),
            test_end=(
                TEST_PRICE_END
            ),
        )
    )

    demand_val, demand_val_errors = (
        evaluate_split(
            dataset="RO1_DEMAND",
            df=demand,
            specs=specs,
            split="validation",
            validation_start=(
                VALIDATION_DEMAND_START
            ),
            validation_end=(
                VALIDATION_DEMAND_END
            ),
            test_start=(
                TEST_DEMAND_START
            ),
            test_end=(
                TEST_DEMAND_END
            ),
        )
    )

    validation_forecasts = pd.concat(
        [
            price_val,
            demand_val,
        ],
        ignore_index=True,
    )

    validation_errors = pd.concat(
        [
            price_val_errors,
            demand_val_errors,
        ],
        ignore_index=True,
    )

    # =========================================================================
    # 4. TEST
    # =========================================================================

    print(
        "\n" + "=" * 78
    )

    print(
        "[3] TEST — "
        "FROZEN PROBABILISTIC STATISTICAL BASELINES"
    )

    print(
        "=" * 78
    )

    price_test, price_test_errors = (
        evaluate_split(
            dataset="RO1_PRICE",
            df=price,
            specs=specs,
            split="test",
            validation_start=(
                VALIDATION_PRICE_START
            ),
            validation_end=(
                VALIDATION_PRICE_END
            ),
            test_start=(
                TEST_PRICE_START
            ),
            test_end=(
                TEST_PRICE_END
            ),
        )
    )

    demand_test, demand_test_errors = (
        evaluate_split(
            dataset="RO1_DEMAND",
            df=demand,
            specs=specs,
            split="test",
            validation_start=(
                VALIDATION_DEMAND_START
            ),
            validation_end=(
                VALIDATION_DEMAND_END
            ),
            test_start=(
                TEST_DEMAND_START
            ),
            test_end=(
                TEST_DEMAND_END
            ),
        )
    )

    test_forecasts = pd.concat(
        [
            price_test,
            demand_test,
        ],
        ignore_index=True,
    )

    test_errors = pd.concat(
        [
            price_test_errors,
            demand_test_errors,
        ],
        ignore_index=True,
    )

    # =========================================================================
    # 5. COMBINE
    # =========================================================================

    forecasts = pd.concat(
        [
            validation_forecasts,
            test_forecasts,
        ],
        ignore_index=True,
    )

    errors = pd.concat(
        [
            validation_errors,
            test_errors,
        ],
        ignore_index=True,
    )

    print(
        "\n[4] FORECAST RECORD SUMMARY"
    )

    print(
        f"Validation records: "
        f"{len(validation_forecasts)}"
    )

    print(
        f"Test records: "
        f"{len(test_forecasts)}"
    )

    print(
        f"Total records: "
        f"{len(forecasts)}"
    )

    print(
        f"Forecast failures: "
        f"{len(errors)}"
    )

    # =========================================================================
    # 6. METRICS
    # =========================================================================

    print(
        "\n[5] PROBABILISTIC METRICS"
    )

    metrics = calculate_metrics(
        forecasts
    )

    display_columns = [
        "dataset",
        "split",
        "series",
        "model",
        "horizon",
        "n_forecasts",
        "MAE",
        "RMSE",
        "mean_pinball",
        "coverage_50",
        "interval_width_50",
        "coverage_80",
        "interval_width_80",
    ]

    print(
        metrics[
            display_columns
        ].to_string(
            index=False
        )
    )

    # =========================================================================
    # 7. VALIDATION-ONLY SELECTION
    # =========================================================================

    print(
        "\n[6] VALIDATION-ONLY "
        "PROBABILISTIC MODEL SELECTION"
    )

    selected = (
        select_validation_baseline(
            metrics
        )
    )

    print(
        selected.to_string(
            index=False
        )
    )

    # =========================================================================
    # 8. PRIMARY HORIZON
    # =========================================================================

    print_primary_summary(
        metrics
    )

    # =========================================================================
    # 9. SAVE OUTPUTS
    # =========================================================================

    print(
        "\n[8] SAVING OUTPUTS"
    )

    forecast_path = (
        OUT_DIR
        / "RO1_step26b1_probabilistic_forecasts.csv"
    )

    metrics_path = (
        OUT_DIR
        / "RO1_step26b1_probabilistic_metrics.csv"
    )

    validation_metrics_path = (
        OUT_DIR
        / "RO1_step26b1_validation_metrics.csv"
    )

    test_metrics_path = (
        OUT_DIR
        / "RO1_step26b1_test_metrics.csv"
    )

    selected_path = (
        OUT_DIR
        / "RO1_step26b1_selected_probabilistic_baselines.csv"
    )

    errors_path = (
        OUT_DIR
        / "RO1_step26b1_forecast_errors.csv"
    )

    forecasts.to_csv(
        forecast_path,
        index=False,
    )

    metrics.to_csv(
        metrics_path,
        index=False,
    )

    metrics[
        metrics["split"] == "validation"
    ].to_csv(
        validation_metrics_path,
        index=False,
    )

    metrics[
        metrics["split"] == "test"
    ].to_csv(
        test_metrics_path,
        index=False,
    )

    selected.to_csv(
        selected_path,
        index=False,
    )

    errors.to_csv(
        errors_path,
        index=False,
    )

    print(
        f"Forecasts: {forecast_path}"
    )

    print(
        f"Metrics: {metrics_path}"
    )

    print(
        f"Validation metrics: "
        f"{validation_metrics_path}"
    )

    print(
        f"Test metrics: "
        f"{test_metrics_path}"
    )

    print(
        f"Selected baselines: "
        f"{selected_path}"
    )

    print(
        f"Errors: {errors_path}"
    )

    # =========================================================================
    # 10. FINAL ASSERTIONS
    # =========================================================================

    run_assertions(
        forecasts=forecasts,
        metrics=metrics,
        selected=selected,
        errors=errors,
    )

    print(
        "\n" + "=" * 78
    )

    print(
        "STEP 26B.1 COMPLETE"
    )

    print(
        "=" * 78
    )

    print(
        "\nConventional statistical "
        "probabilistic baseline established."
    )

    print(
        "Models: ETS + SARIMA"
    )

    print(
        "Predictive quantiles: "
        "q={0.10,0.25,0.50,0.75,0.90}"
    )

    print(
        "Primary horizon: h=3 months"
    )

    print(
        "Rolling-origin design: "
        "horizon-specific target membership"
    )

    print(
        "Model selection: validation only"
    )

    print(
        "Test evaluation: frozen"
    )

    print(
        "\nNo ML model was trained."
    )

    print(
        "No conformal calibration was performed."
    )

    print(
        "No previous deterministic result "
        "was modified."
    )

    print(
        "\nRO1 STEP 26B.1: COMPLETE"
    )

    print(
        "=" * 78
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()