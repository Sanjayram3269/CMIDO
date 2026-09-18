"""
CMIDO — RO1 Step 26C.3-D
Frozen CQR Application + Untouched Test Evaluation

Purpose
-------
Apply the validation-derived CQR calibration parameters from Step 26C.3-C
to the FROZEN 26C.2 test forecasts.

IMPORTANT
---------
This is the first test evaluation of the CQR layer.

Rules:
1. 26C.2 forecasting models remain frozen.
2. 26C.3-C calibration parameters remain frozen.
3. No test observations are used to estimate calibration parameters.
4. No test recalibration is permitted.
5. No model retraining.
6. No model reselection.
7. No random splitting.
8. Raw ML and CQR ML use identical test observations.
9. Test performance is reported only after all calibration parameters
   have been loaded from validation.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

import numpy as np
import pandas as pd


# ============================================================================
# 1. PATHS
# ============================================================================

PROJECT_ROOT = Path(r"D:\CMIDO")

PROB_ML_DIR = (
    PROJECT_ROOT
    / "results"
    / "forecasting"
    / "probabilistic_ml"
)

CALIBRATION_DIR = (
    PROJECT_ROOT
    / "results"
    / "forecasting"
    / "probabilistic_calibration"
)

RESULTS_DIR = CALIBRATION_DIR


C26C2_TEST = PROB_ML_DIR / (
    "RO1_step26c2_test_forecasts.csv"
)

C26C2_SELECTION = PROB_ML_DIR / (
    "RO1_step26c2_model_selection.csv"
)

C26C3_PARAMETERS = CALIBRATION_DIR / (
    "RO1_step26c3_calibration_parameters.csv"
)

C26C3_VALIDATION = CALIBRATION_DIR / (
    "RO1_step26c3_validation_forecasts.csv"
)

C26C3_SPEC = PROJECT_ROOT / "docs" / (
    "RO1_26C3A_Probabilistic_Calibration_Specification_v1.0.md"
)


# ============================================================================
# 2. FROZEN CONFIGURATION
# ============================================================================

STEP = "26C.3-D"

CALIBRATION_METHOD = "CQR"

CALIBRATION_MODE = "PREQUENTIAL_TIME_AWARE"

HORIZONS = [1, 3, 6, 12]

PRIMARY_HORIZON = 3

QUANTILES = [
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
]

MIN_CALIBRATION_N = 10

INTERVALS = {
    "50": {
        "lower_quantile": 0.25,
        "upper_quantile": 0.75,
        "nominal_coverage": 0.50,
        "alpha": 0.50,
    },
    "80": {
        "lower_quantile": 0.10,
        "upper_quantile": 0.90,
        "nominal_coverage": 0.80,
        "alpha": 0.20,
    },
}


# ============================================================================
# 3. FROZEN 26C.2 WINNERS
# ============================================================================

EXPECTED_WINNERS = {
    ("RO1_PRICE", "Cement"): {
        "model_family": "LightGBM",
        "config": "LGB_C1",
    },
    ("RO1_PRICE", "Concreting Sand"): {
        "model_family": "XGBoost",
        "config": "XGB_C2",
    },
    ("RO1_PRICE", "Granite"): {
        "model_family": "XGBoost",
        "config": "XGB_C3",
    },
    ("RO1_PRICE", "Ready Mixed Concrete"): {
        "model_family": "XGBoost",
        "config": "XGB_C2",
    },
    ("RO1_PRICE", "Steel Reinforcement Bars"): {
        "model_family": "XGBoost",
        "config": "XGB_C2",
    },
    ("RO1_DEMAND", "Cement"): {
        "model_family": "XGBoost",
        "config": "XGB_C3",
    },
    ("RO1_DEMAND", "Granite"): {
        "model_family": "LightGBM",
        "config": "LGB_C3",
    },
    ("RO1_DEMAND", "Ready Mixed Concrete"): {
        "model_family": "XGBoost",
        "config": "XGB_C2",
    },
    ("RO1_DEMAND", "Steel Reinforcement Bars"): {
        "model_family": "XGBoost",
        "config": "XGB_C3",
    },
}


EXPECTED_SERIES_COUNT = 9


# ============================================================================
# 4. EXPECTED TEST ORIGINS
# ============================================================================

EXPECTED_TEST_ORIGINS = {
    1: 23,
    3: 21,
    6: 18,
    12: 12,
}


EXPECTED_TEST_FORECASTS = (
    EXPECTED_SERIES_COUNT
    * sum(EXPECTED_TEST_ORIGINS.values())
)


# ============================================================================
# 5. UTILITIES
# ============================================================================

def log(message: str) -> None:
    print(message, flush=True)


def require(
    condition: bool,
    message: str,
) -> None:

    if not condition:
        raise AssertionError(message)


def normalize_dataset(
    value: str,
) -> str:

    value = str(value).strip()

    mapping = {
        "RO1_PRICE": "RO1_PRICE",
        "PRICE": "RO1_PRICE",
        "Price": "RO1_PRICE",
        "RO1_DEMAND": "RO1_DEMAND",
        "DEMAND": "RO1_DEMAND",
        "Demand": "RO1_DEMAND",
    }

    return mapping.get(
        value,
        value,
    )


def normalize_series(
    value: str,
) -> str:

    value = str(value).strip()

    mapping = {
        "Cement": "Cement",
        "Cement In Bulk (Ordinary Portland Cement)": "Cement",

        "Concreting Sand": "Concreting Sand",

        "Granite": "Granite",
        "Granite (20mm Aggregate)": "Granite",

        "Ready Mixed Concrete": "Ready Mixed Concrete",
        "Ready-Mixed Concrete": "Ready Mixed Concrete",

        "Steel Reinforcement Bars":
            "Steel Reinforcement Bars",

        "Steel Reinforcement Bars (16-32mm High Tensile)":
            "Steel Reinforcement Bars",
    }

    return mapping.get(
        value,
        value,
    )


def find_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:

    mapping = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for candidate in candidates:

        key = candidate.strip().lower()

        if key in mapping:
            return mapping[key]

    return None


def sha256_file(
    path: Path,
) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


# ============================================================================
# 6. LOAD FROZEN 26C.2 TEST FORECASTS
# ============================================================================

def load_test_forecasts() -> pd.DataFrame:

    require(
        C26C2_TEST.exists(),
        (
            "Frozen 26C.2 TEST forecast file not found:\n"
            f"{C26C2_TEST}"
        ),
    )

    df = pd.read_csv(
        C26C2_TEST
    )

    require(
        len(df) > 0,
        "26C.2 test forecast file is empty.",
    )

    dataset_col = find_column(
        df,
        [
            "dataset",
            "dataset_id",
            "target",
        ],
    )

    series_col = find_column(
        df,
        [
            "series",
            "dataseries",
            "data_series",
            "material",
        ],
    )

    horizon_col = find_column(
        df,
        [
            "horizon",
            "h",
        ],
    )

    origin_col = find_column(
        df,
        [
            "forecast_origin",
            "origin",
            "origin_date",
        ],
    )

    target_date_col = find_column(
        df,
        [
            "target_date",
            "target_datetime",
            "target_timestamp",
        ],
    )

    actual_col = find_column(
        df,
        [
            "actual",
            "actual_value",
            "y_true",
            "target_value",
        ],
    )

    require(
        dataset_col is not None,
        "Test forecasts missing dataset column.",
    )

    require(
        series_col is not None,
        "Test forecasts missing series column.",
    )

    require(
        horizon_col is not None,
        "Test forecasts missing horizon column.",
    )

    require(
        origin_col is not None,
        "Test forecasts missing forecast-origin column.",
    )

    require(
        target_date_col is not None,
        "Test forecasts missing target-date column.",
    )

    require(
        actual_col is not None,
        "Test forecasts missing actual column.",
    )

    work = pd.DataFrame()

    work["dataset"] = (
        df[dataset_col]
        .astype(str)
        .map(normalize_dataset)
    )

    work["series"] = (
        df[series_col]
        .astype(str)
        .map(normalize_series)
    )

    work["horizon"] = pd.to_numeric(
        df[horizon_col],
        errors="coerce",
    )

    work["forecast_origin"] = pd.to_datetime(
        df[origin_col],
        errors="coerce",
    )

    work["target_date"] = pd.to_datetime(
        df[target_date_col],
        errors="coerce",
    )

    work["actual"] = pd.to_numeric(
        df[actual_col],
        errors="coerce",
    )

    # ------------------------------------------------------------------------
    # Quantiles
    # ------------------------------------------------------------------------

    quantile_columns = {}

    for q in QUANTILES:

        q_int = int(round(q * 100))

        candidates = [
            f"q{q_int:02d}",
            f"q{q_int}",
            f"q_{q:.2f}",
            f"quantile_{q:.2f}",
            f"prediction_q{q_int:02d}",
            f"pred_q{q_int:02d}",
            f"pred_q{q_int}",
            f"forecast_q{q_int:02d}",
            f"forecast_q{q_int}",
        ]

        col = find_column(
            df,
            candidates,
        )

        require(
            col is not None,
            (
                f"Missing test quantile q={q}."
            ),
        )

        quantile_columns[q] = col

        work[
            f"q{q_int:02d}"
        ] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    # ------------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------------

    require(
        work["horizon"].notna().all(),
        "Test horizons contain invalid values.",
    )

    work["horizon"] = work[
        "horizon"
    ].astype(int)

    require(
        set(work["horizon"].unique())
        <= set(HORIZONS),
        "Unexpected test horizon detected.",
    )

    require(
        work["forecast_origin"].notna().all(),
        "Invalid test forecast origins.",
    )

    require(
        work["target_date"].notna().all(),
        "Invalid test target dates.",
    )

    require(
        work["actual"].notna().all(),
        "Invalid/missing test actual values.",
    )

    for q in QUANTILES:

        col = f"q{int(q * 100):02d}"

        require(
            work[col].notna().all(),
            f"Missing test predictions in {col}.",
        )

        require(
            np.isfinite(
                work[col]
            ).all(),
            f"Non-finite test predictions in {col}.",
        )

    # ------------------------------------------------------------------------
    # Chronology
    # ------------------------------------------------------------------------

    require(
        (
            work["target_date"]
            > work["forecast_origin"]
        ).all(),
        "Test target must occur after forecast origin.",
    )

    # ------------------------------------------------------------------------
    # Quantile monotonicity
    # ------------------------------------------------------------------------

    q_matrix = work[
        [
            "q10",
            "q25",
            "q50",
            "q75",
            "q90",
        ]
    ].to_numpy()

    require(
        np.all(
            np.diff(
                q_matrix,
                axis=1,
            ) >= -1e-12
        ),
        (
            "Frozen 26C.2 test quantiles contain "
            "unrepaired crossing."
        ),
    )

    # ------------------------------------------------------------------------
    # Duplicate records
    # ------------------------------------------------------------------------

    key = [
        "dataset",
        "series",
        "horizon",
        "forecast_origin",
        "target_date",
    ]

    duplicate_count = int(
        work.duplicated(key).sum()
    )

    require(
        duplicate_count == 0,
        (
            "Duplicate test forecast records detected: "
            f"{duplicate_count}"
        ),
    )

    # ------------------------------------------------------------------------
    # Nine frozen series
    # ------------------------------------------------------------------------

    expected_pairs = set(
        EXPECTED_WINNERS
    )

    observed_pairs = set(
        zip(
            work["dataset"],
            work["series"],
        )
    )

    require(
        expected_pairs.issubset(
            observed_pairs
        ),
        "Not all nine frozen series are present in test forecasts.",
    )

    log(
        f"Loaded frozen 26C.2 TEST forecasts: "
        f"{len(work)} rows"
    )

    return work


# ============================================================================
# 7. LOAD FROZEN VALIDATION-DERIVED CQR PARAMETERS
# ============================================================================

def load_cqr_parameters() -> pd.DataFrame:

    require(
        C26C3_PARAMETERS.exists(),
        (
            "26C.3 frozen calibration parameters not found:\n"
            f"{C26C3_PARAMETERS}"
        ),
    )

    df = pd.read_csv(
        C26C3_PARAMETERS
    )

    require(
        len(df) > 0,
        "CQR parameter file is empty.",
    )

    required_columns = [
        "dataset",
        "series",
        "horizon",
        "interval",
        "alpha",
        "nominal_coverage",
        "calibration_n",
        "conformal_rank",
        "conformal_adjustment",
        "calibration_mode",
        "parameter_status",
    ]

    missing = [
        c
        for c in required_columns
        if c not in df.columns
    ]

    require(
        not missing,
        (
            "CQR parameter file missing columns: "
            + ", ".join(missing)
        ),
    )

    work = df.copy()

    work["dataset"] = (
        work["dataset"]
        .astype(str)
        .map(normalize_dataset)
    )

    work["series"] = (
        work["series"]
        .astype(str)
        .map(normalize_series)
    )

    work["horizon"] = pd.to_numeric(
        work["horizon"],
        errors="coerce",
    ).astype(int)

    work["interval"] = (
        work["interval"]
        .astype(str)
    )

    work["calibration_n"] = pd.to_numeric(
        work["calibration_n"],
        errors="coerce",
    )

    work["conformal_rank"] = pd.to_numeric(
        work["conformal_rank"],
        errors="coerce",
    )

    work["conformal_adjustment"] = pd.to_numeric(
        work["conformal_adjustment"],
        errors="coerce",
    )

    work["alpha"] = pd.to_numeric(
        work["alpha"],
        errors="coerce",
    )

    work["nominal_coverage"] = pd.to_numeric(
        work["nominal_coverage"],
        errors="coerce",
    )

    # ------------------------------------------------------------------------
    # Parameter status
    # ------------------------------------------------------------------------

    require(
        (
            work["parameter_status"]
            == "FROZEN_FROM_VALIDATION"
        ).all(),
        (
            "Not all CQR parameters are marked "
            "FROZEN_FROM_VALIDATION."
        ),
    )

    require(
        (
            work["calibration_mode"]
            == CALIBRATION_MODE
        ).all(),
        "Unexpected calibration mode in parameter file.",
    )

    # ------------------------------------------------------------------------
    # Exactly 72 cells
    # ------------------------------------------------------------------------

    require(
        len(work)
        == EXPECTED_SERIES_COUNT
        * len(HORIZONS)
        * 2,
        (
            "Expected 72 frozen CQR parameter rows; "
            f"found {len(work)}."
        ),
    )

    key = [
        "dataset",
        "series",
        "horizon",
        "interval",
    ]

    require(
        work.duplicated(key).sum() == 0,
        "Duplicate CQR parameter cells detected.",
    )

    # ------------------------------------------------------------------------
    # Exact interval set
    # ------------------------------------------------------------------------

    require(
        set(work["interval"].unique())
        == {"50", "80"},
        "CQR parameter intervals must be exactly 50 and 80.",
    )

    # ------------------------------------------------------------------------
    # Numeric validity
    # ------------------------------------------------------------------------

    for col in [
        "calibration_n",
        "conformal_rank",
        "conformal_adjustment",
        "alpha",
        "nominal_coverage",
    ]:

        require(
            work[col].notna().all(),
            f"CQR parameter field {col} contains missing values.",
        )

        require(
            np.isfinite(
                work[col]
            ).all(),
            f"CQR parameter field {col} contains non-finite values.",
        )

    require(
        (
            work["calibration_n"]
            >= MIN_CALIBRATION_N
        ).all(),
        "Frozen CQR calibration n below minimum.",
    )

    require(
        (
            work["conformal_adjustment"]
            >= 0
        ).all(),
        "Negative frozen CQR adjustment detected.",
    )

    require(
        (
            work["conformal_rank"]
            >= 1
        ).all(),
        "Invalid CQR rank.",
    )

    require(
        (
            work["conformal_rank"]
            <= work["calibration_n"]
        ).all(),
        "CQR rank exceeds calibration sample size.",
    )

    # ------------------------------------------------------------------------
    # Frozen 9-series set
    # ------------------------------------------------------------------------

    expected_cells = {
        (
            dataset,
            series,
            horizon,
            interval,
        )
        for dataset, series in EXPECTED_WINNERS
        for horizon in HORIZONS
        for interval in ["50", "80"]
    }

    observed_cells = set(
        zip(
            work["dataset"],
            work["series"],
            work["horizon"],
            work["interval"],
        )
    )

    require(
        observed_cells == expected_cells,
        "Frozen CQR parameter cells do not match expected 72 cells.",
    )

    log(
        "Loaded frozen CQR parameters: "
        f"{len(work)} rows"
    )

    log(
        "Parameter source status: "
        "FROZEN_FROM_VALIDATION"
    )

    return work


# ============================================================================
# 8. APPLY FROZEN CQR
# ============================================================================

def apply_frozen_cqr(
    test_df: pd.DataFrame,
    parameter_df: pd.DataFrame,
) -> pd.DataFrame:

    rows = []

    parameter_lookup = {}

    for _, row in parameter_df.iterrows():

        key = (
            row["dataset"],
            row["series"],
            int(row["horizon"]),
            str(row["interval"]),
        )

        require(
            key not in parameter_lookup,
            f"Duplicate parameter key: {key}",
        )

        parameter_lookup[key] = row

    for _, row in test_df.iterrows():

        key_base = (
            row["dataset"],
            row["series"],
            int(row["horizon"]),
        )

        p50_key = (
            key_base[0],
            key_base[1],
            key_base[2],
            "50",
        )

        p80_key = (
            key_base[0],
            key_base[1],
            key_base[2],
            "80",
        )

        require(
            p50_key in parameter_lookup,
            f"Missing frozen 50% CQR parameter: {p50_key}",
        )

        require(
            p80_key in parameter_lookup,
            f"Missing frozen 80% CQR parameter: {p80_key}",
        )

        p50 = parameter_lookup[p50_key]
        p80 = parameter_lookup[p80_key]

        # Raw intervals
        raw_lower_50 = float(row["q25"])
        raw_upper_50 = float(row["q75"])

        raw_lower_80 = float(row["q10"])
        raw_upper_80 = float(row["q90"])

        # Frozen validation-derived adjustments
        adjustment_50 = float(
            p50["conformal_adjustment"]
        )

        adjustment_80 = float(
            p80["conformal_adjustment"]
        )

        # Physical-domain lower bound
        calibrated_lower_50 = max(
            0.0,
            raw_lower_50 - adjustment_50,
        )

        calibrated_upper_50 = (
            raw_upper_50
            + adjustment_50
        )

        calibrated_lower_80 = max(
            0.0,
            raw_lower_80 - adjustment_80,
        )

        calibrated_upper_80 = (
            raw_upper_80
            + adjustment_80
        )

        require(
            calibrated_lower_50
            <= calibrated_upper_50,
            "Invalid calibrated 50% interval.",
        )

        require(
            calibrated_lower_80
            <= calibrated_upper_80,
            "Invalid calibrated 80% interval.",
        )

        rows.append(
            {
                "dataset": row["dataset"],
                "series": row["series"],
                "horizon": int(row["horizon"]),
                "forecast_origin": row[
                    "forecast_origin"
                ],
                "target_date": row[
                    "target_date"
                ],
                "actual": float(row["actual"]),

                "q10": float(row["q10"]),
                "q25": float(row["q25"]),
                "q50": float(row["q50"]),
                "q75": float(row["q75"]),
                "q90": float(row["q90"]),

                "raw_lower_50": raw_lower_50,
                "raw_upper_50": raw_upper_50,
                "raw_lower_80": raw_lower_80,
                "raw_upper_80": raw_upper_80,

                "calibrated_lower_50": (
                    calibrated_lower_50
                ),
                "calibrated_upper_50": (
                    calibrated_upper_50
                ),

                "calibrated_lower_80": (
                    calibrated_lower_80
                ),
                "calibrated_upper_80": (
                    calibrated_upper_80
                ),

                "conformal_adjustment_50": (
                    adjustment_50
                ),
                "conformal_adjustment_80": (
                    adjustment_80
                ),

                "calibration_n_50": int(
                    p50["calibration_n"]
                ),
                "calibration_n_80": int(
                    p80["calibration_n"]
                ),

                "conformal_rank_50": int(
                    p50["conformal_rank"]
                ),
                "conformal_rank_80": int(
                    p80["conformal_rank"]
                ),

                "calibration_source": (
                    "VALIDATION_ONLY"
                ),

                "test_recalibration": False,
            }
        )

    result = pd.DataFrame(rows)

    return result


# ============================================================================
# 9. METRICS
# ============================================================================

def coverage(
    actual: pd.Series,
    lower: pd.Series,
    upper: pd.Series,
) -> float:

    mask = (
        actual.notna()
        & lower.notna()
        & upper.notna()
    )

    require(
        mask.any(),
        "No valid observations for coverage.",
    )

    y = actual[mask]
    l = lower[mask]
    u = upper[mask]

    covered = (
        (y >= l)
        & (y <= u)
    )

    return float(
        covered.mean()
    )


def interval_width(
    lower: pd.Series,
    upper: pd.Series,
) -> float:

    return float(
        (
            upper
            - lower
        ).mean()
    )


def winkler_score(
    actual: pd.Series,
    lower: pd.Series,
    upper: pd.Series,
    alpha: float,
) -> float:

    y = actual.to_numpy(
        dtype=float
    )

    l = lower.to_numpy(
        dtype=float
    )

    u = upper.to_numpy(
        dtype=float
    )

    score = (
        u - l
    )

    below = y < l
    above = y > u

    score[below] += (
        2.0
        / alpha
        * (
            l[below]
            - y[below]
        )
    )

    score[above] += (
        2.0
        / alpha
        * (
            y[above]
            - u[above]
        )
    )

    return float(
        np.mean(score)
    )


def pinball_loss(
    actual: np.ndarray,
    prediction: np.ndarray,
    q: float,
) -> float:

    error = (
        actual
        - prediction
    )

    loss = np.maximum(
        q * error,
        (q - 1.0) * error,
    )

    return float(
        np.mean(loss)
    )


def calculate_metrics(
    df: pd.DataFrame,
) -> pd.DataFrame:

    rows = []

    grouped = df.groupby(
        [
            "dataset",
            "series",
            "horizon",
        ],
        sort=True,
    )

    for (
        dataset,
        series,
        horizon,
    ), group in grouped:

        actual = group[
            "actual"
        ].to_numpy(
            dtype=float
        )

        q50 = group[
            "q50"
        ].to_numpy(
            dtype=float
        )

        # ---------------------------------------------------------------
        # Point metrics
        # ---------------------------------------------------------------

        mae = float(
            np.mean(
                np.abs(
                    actual - q50
                )
            )
        )

        rmse = float(
            np.sqrt(
                np.mean(
                    (
                        actual - q50
                    ) ** 2
                )
            )
        )

        # ---------------------------------------------------------------
        # Raw intervals
        # ---------------------------------------------------------------

        raw_cov_50 = coverage(
            group["actual"],
            group["raw_lower_50"],
            group["raw_upper_50"],
        )

        raw_cov_80 = coverage(
            group["actual"],
            group["raw_lower_80"],
            group["raw_upper_80"],
        )

        raw_width_50 = interval_width(
            group["raw_lower_50"],
            group["raw_upper_50"],
        )

        raw_width_80 = interval_width(
            group["raw_lower_80"],
            group["raw_upper_80"],
        )

        raw_winkler_50 = winkler_score(
            group["actual"],
            group["raw_lower_50"],
            group["raw_upper_50"],
            alpha=0.50,
        )

        raw_winkler_80 = winkler_score(
            group["actual"],
            group["raw_lower_80"],
            group["raw_upper_80"],
            alpha=0.20,
        )

        # ---------------------------------------------------------------
        # CQR intervals
        # ---------------------------------------------------------------

        cqr_cov_50 = coverage(
            group["actual"],
            group["calibrated_lower_50"],
            group["calibrated_upper_50"],
        )

        cqr_cov_80 = coverage(
            group["actual"],
            group["calibrated_lower_80"],
            group["calibrated_upper_80"],
        )

        cqr_width_50 = interval_width(
            group["calibrated_lower_50"],
            group["calibrated_upper_50"],
        )

        cqr_width_80 = interval_width(
            group["calibrated_lower_80"],
            group["calibrated_upper_80"],
        )

        cqr_winkler_50 = winkler_score(
            group["actual"],
            group["calibrated_lower_50"],
            group["calibrated_upper_50"],
            alpha=0.50,
        )

        cqr_winkler_80 = winkler_score(
            group["actual"],
            group["calibrated_lower_80"],
            group["calibrated_upper_80"],
            alpha=0.20,
        )

        # ---------------------------------------------------------------
        # Pinball loss
        # ---------------------------------------------------------------

        pinballs = {}

        for q in QUANTILES:

            col = (
                f"q{int(q * 100):02d}"
            )

            pinballs[
                f"pinball_q{int(q * 100):02d}"
            ] = pinball_loss(
                actual,
                group[col].to_numpy(
                    dtype=float
                ),
                q,
            )

        rows.append(
            {
                "dataset": dataset,
                "series": series,
                "horizon": int(horizon),
                "n_test": len(group),

                "mae_q50": mae,
                "rmse_q50": rmse,

                "raw_coverage_50": raw_cov_50,
                "raw_coverage_80": raw_cov_80,

                "raw_coverage_error_50": abs(
                    raw_cov_50 - 0.50
                ),

                "raw_coverage_error_80": abs(
                    raw_cov_80 - 0.80
                ),

                "raw_mean_width_50": raw_width_50,
                "raw_mean_width_80": raw_width_80,

                "raw_winkler_50": raw_winkler_50,
                "raw_winkler_80": raw_winkler_80,

                "cqr_coverage_50": cqr_cov_50,
                "cqr_coverage_80": cqr_cov_80,

                "cqr_coverage_error_50": abs(
                    cqr_cov_50 - 0.50
                ),

                "cqr_coverage_error_80": abs(
                    cqr_cov_80 - 0.80
                ),

                "cqr_mean_width_50": cqr_width_50,
                "cqr_mean_width_80": cqr_width_80,

                "cqr_winkler_50": cqr_winkler_50,
                "cqr_winkler_80": cqr_winkler_80,

                "width_change_50": (
                    cqr_width_50
                    - raw_width_50
                ),

                "width_change_80": (
                    cqr_width_80
                    - raw_width_80
                ),

                "coverage_error_change_50": (
                    abs(cqr_cov_50 - 0.50)
                    - abs(raw_cov_50 - 0.50)
                ),

                "coverage_error_change_80": (
                    abs(cqr_cov_80 - 0.80)
                    - abs(raw_cov_80 - 0.80)
                ),

                **pinballs,
            }
        )

    return pd.DataFrame(rows)


# ============================================================================
# 10. PRIMARY h=3 SUMMARY
# ============================================================================

def build_primary_summary(
    metrics_df: pd.DataFrame,
) -> pd.DataFrame:

    primary = metrics_df[
        metrics_df["horizon"]
        == PRIMARY_HORIZON
    ].copy()

    require(
        len(primary)
        == EXPECTED_SERIES_COUNT,
        (
            "Primary h=3 metrics must contain "
            "exactly nine series."
        ),
    )

    summary_rows = []

    for target in [
        "RO1_PRICE",
        "RO1_DEMAND",
    ]:

        subset = primary[
            primary["dataset"]
            == target
        ]

        if len(subset) == 0:
            continue

        summary_rows.append(
            {
                "dataset": target,
                "horizon": PRIMARY_HORIZON,
                "n_series": len(subset),

                "raw_mean_coverage_error_50": (
                    subset[
                        "raw_coverage_error_50"
                    ].mean()
                ),

                "cqr_mean_coverage_error_50": (
                    subset[
                        "cqr_coverage_error_50"
                    ].mean()
                ),

                "raw_mean_coverage_error_80": (
                    subset[
                        "raw_coverage_error_80"
                    ].mean()
                ),

                "cqr_mean_coverage_error_80": (
                    subset[
                        "cqr_coverage_error_80"
                    ].mean()
                ),

                "raw_mean_width_50": (
                    subset[
                        "raw_mean_width_50"
                    ].mean()
                ),

                "cqr_mean_width_50": (
                    subset[
                        "cqr_mean_width_50"
                    ].mean()
                ),

                "raw_mean_width_80": (
                    subset[
                        "raw_mean_width_80"
                    ].mean()
                ),

                "cqr_mean_width_80": (
                    subset[
                        "cqr_mean_width_80"
                    ].mean()
                ),

                "mean_coverage_error_change_50": (
                    subset[
                        "coverage_error_change_50"
                    ].mean()
                ),

                "mean_coverage_error_change_80": (
                    subset[
                        "coverage_error_change_80"
                    ].mean()
                ),
            }
        )

    # Overall nine-series summary
    summary_rows.append(
        {
            "dataset": "ALL",
            "horizon": PRIMARY_HORIZON,
            "n_series": len(primary),

            "raw_mean_coverage_error_50": (
                primary[
                    "raw_coverage_error_50"
                ].mean()
            ),

            "cqr_mean_coverage_error_50": (
                primary[
                    "cqr_coverage_error_50"
                ].mean()
            ),

            "raw_mean_coverage_error_80": (
                primary[
                    "raw_coverage_error_80"
                ].mean()
            ),

            "cqr_mean_coverage_error_80": (
                primary[
                    "cqr_coverage_error_80"
                ].mean()
            ),

            "raw_mean_width_50": (
                primary[
                    "raw_mean_width_50"
                ].mean()
            ),

            "cqr_mean_width_50": (
                primary[
                    "cqr_mean_width_50"
                ].mean()
            ),

            "raw_mean_width_80": (
                primary[
                    "raw_mean_width_80"
                ].mean()
            ),

            "cqr_mean_width_80": (
                primary[
                    "cqr_mean_width_80"
                ].mean()
            ),

            "mean_coverage_error_change_50": (
                primary[
                    "coverage_error_change_50"
                ].mean()
            ),

            "mean_coverage_error_change_80": (
                primary[
                    "coverage_error_change_80"
                ].mean()
            ),
        }
    )

    return pd.DataFrame(
        summary_rows
    )


# ============================================================================
# 11. AUDITS
# ============================================================================

def run_audits(
    test_df: pd.DataFrame,
    parameter_df: pd.DataFrame,
    result_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
) -> pd.DataFrame:

    rows = []

    def add(
        audit: str,
        detail: str,
    ) -> None:

        rows.append(
            {
                "audit": audit,
                "status": "PASS",
                "detail": detail,
            }
        )

    # ------------------------------------------------------------------------
    # Test count
    # ------------------------------------------------------------------------

    expected_count = EXPECTED_TEST_FORECASTS

    require(
        len(test_df)
        == expected_count,
        (
            f"Expected {expected_count} test forecasts; "
            f"found {len(test_df)}."
        ),
    )

    add(
        "test_forecast_count",
        f"{expected_count} frozen test forecasts.",
    )

    # ------------------------------------------------------------------------
    # Parameter count
    # ------------------------------------------------------------------------

    require(
        len(parameter_df) == 72,
        "Frozen CQR parameter count is not 72.",
    )

    add(
        "frozen_parameter_count",
        "72 validation-derived CQR parameter cells.",
    )

    # ------------------------------------------------------------------------
    # Test calibration source
    # ------------------------------------------------------------------------

    require(
        (
            result_df[
                "calibration_source"
            ]
            == "VALIDATION_ONLY"
        ).all(),
        "Test result contains non-validation calibration source.",
    )

    add(
        "calibration_source",
        "All test intervals use validation-only parameters.",
    )

    # ------------------------------------------------------------------------
    # No test recalibration
    # ------------------------------------------------------------------------

    require(
        (
            result_df[
                "test_recalibration"
            ]
            == False
        ).all(),
        "Test recalibration flag detected.",
    )

    add(
        "test_recalibration",
        "No test recalibration performed.",
    )

    # ------------------------------------------------------------------------
    # Parameter immutability check
    # ------------------------------------------------------------------------

    require(
        (
            parameter_df[
                "parameter_status"
            ]
            == "FROZEN_FROM_VALIDATION"
        ).all(),
        "Frozen parameter status failed.",
    )

    add(
        "parameter_immutability",
        "All CQR parameters remain frozen from validation.",
    )

    # ------------------------------------------------------------------------
    # Interval validity
    # ------------------------------------------------------------------------

    require(
        (
            result_df[
                "calibrated_lower_50"
            ]
            <= result_df[
                "calibrated_upper_50"
            ]
        ).all(),
        "Invalid calibrated 50% interval.",
    )

    require(
        (
            result_df[
                "calibrated_lower_80"
            ]
            <= result_df[
                "calibrated_upper_80"
            ]
        ).all(),
        "Invalid calibrated 80% interval.",
    )

    add(
        "interval_validity",
        "All calibrated intervals have lower ≤ upper.",
    )

    # ------------------------------------------------------------------------
    # Non-negative bounds
    # ------------------------------------------------------------------------

    require(
        (
            result_df[
                "calibrated_lower_50"
            ]
            >= 0
        ).all(),
        "Negative 50% calibrated lower bound.",
    )

    require(
        (
            result_df[
                "calibrated_lower_80"
            ]
            >= 0
        ).all(),
        "Negative 80% calibrated lower bound.",
    )

    add(
        "physical_domain",
        "All calibrated lower bounds are non-negative.",
    )

    # ------------------------------------------------------------------------
    # Identical raw/CQR target set
    # ------------------------------------------------------------------------

    raw_key = [
        "dataset",
        "series",
        "horizon",
        "forecast_origin",
        "target_date",
    ]

    require(
        not test_df.duplicated(
            raw_key
        ).any(),
        "Duplicate raw test target records.",
    )

    require(
        not result_df.duplicated(
            raw_key
        ).any(),
        "Duplicate CQR test target records.",
    )

    require(
        len(result_df) == len(test_df),
        "Raw and CQR test record counts differ.",
    )

    add(
        "paired_target_set",
        "Raw and CQR use identical test targets.",
    )

    # ------------------------------------------------------------------------
    # Metric count
    # ------------------------------------------------------------------------

    require(
        len(metrics_df)
        == EXPECTED_SERIES_COUNT
        * len(HORIZONS),
        (
            "Expected 36 series-horizon metric rows; "
            f"found {len(metrics_df)}."
        ),
    )

    add(
        "metric_cell_count",
        "36 series × horizon metric cells.",
    )

    # ------------------------------------------------------------------------
    # Test data not used for calibration
    # ------------------------------------------------------------------------

    add(
        "test_isolation",
        (
            "Test observations were evaluated only after "
            "loading frozen validation-derived parameters."
        ),
    )

    return pd.DataFrame(rows)


# ============================================================================
# 12. SAVE OUTPUTS
# ============================================================================

def save_outputs(
    result_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    primary_df: pd.DataFrame,
    audit_df: pd.DataFrame,
) -> None:

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    forecasts_path = RESULTS_DIR / (
        "RO1_step26c3_test_forecasts.csv"
    )

    metrics_path = RESULTS_DIR / (
        "RO1_step26c3_test_metrics.csv"
    )

    primary_path = RESULTS_DIR / (
        "RO1_step26c3_primary_h3_summary.csv"
    )

    audit_path = RESULTS_DIR / (
        "RO1_step26c3_test_audit.csv"
    )

    summary_path = RESULTS_DIR / (
        "RO1_step26c3_test_run_summary.txt"
    )

    # ------------------------------------------------------------------------
    # Forecasts
    # ------------------------------------------------------------------------

    result_df.to_csv(
        forecasts_path,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------------

    metrics_df.to_csv(
        metrics_path,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Primary h3
    # ------------------------------------------------------------------------

    primary_df.to_csv(
        primary_path,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------------

    audit_df.to_csv(
        audit_path,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------------

    spec_hash = (
        sha256_file(C26C3_SPEC)
        if C26C3_SPEC.exists()
        else None
    )

    test_hash = sha256_file(
        C26C2_TEST
    )

    parameter_hash = sha256_file(
        C26C3_PARAMETERS
    )

    lines = [
        "CMIDO — RO1 STEP 26C.3-D",
        "Frozen CQR Application + Untouched Test Evaluation",
        "",
        "STATUS: PASS",
        "",
        f"Calibration method: {CALIBRATION_METHOD}",
        f"Calibration mode: {CALIBRATION_MODE}",
        f"Primary horizon: h={PRIMARY_HORIZON}",
        f"Horizons: {HORIZONS}",
        "",
        "Models: FROZEN",
        "CQR parameters: FROZEN FROM VALIDATION",
        "Test recalibration: DISABLED",
        "Test-data parameter estimation: DISABLED",
        "Random split: DISABLED",
        "Synthetic calibration: DISABLED",
        "",
        f"Test forecasts evaluated: {len(result_df)}",
        f"Metric cells: {len(metrics_df)}",
        "",
        "Calibration source: VALIDATION ONLY",
        "Test observations used for calibration: NO",
        "",
        f"26C.3-A specification SHA256: {spec_hash}",
        f"26C.2 test forecast SHA256: {test_hash}",
        f"26C.3 calibration parameter SHA256: {parameter_hash}",
        "",
        "Output files:",
        str(forecasts_path),
        str(metrics_path),
        str(primary_path),
        str(audit_path),
        str(summary_path),
        "",
        "ALL STEP 26C.3-D ASSERTIONS: PASS",
    ]

    summary_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    log("\nSaved outputs:")

    for path in [
        forecasts_path,
        metrics_path,
        primary_path,
        audit_path,
        summary_path,
    ]:
        log(f"  {path}")


# ============================================================================
# 13. MAIN
# ============================================================================

def main() -> int:

    start = datetime.now(
        timezone.utc
    )

    print("=" * 78)
    print("CMIDO — RO1 STEP 26C.3-D")
    print("FROZEN CQR APPLICATION + UNTOUCHED TEST EVALUATION")
    print("=" * 78)

    log(
        "CQR parameters: FROZEN FROM VALIDATION"
    )

    log(
        "Test recalibration: DISABLED"
    )

    log(
        "Test-data parameter estimation: DISABLED"
    )

    log(
        "Model retraining: DISABLED"
    )

    log(
        "Model reselection: DISABLED"
    )

    log(
        "Random split: DISABLED"
    )

    log(
        f"Horizons: {HORIZONS}"
    )

    log(
        f"Primary horizon: {PRIMARY_HORIZON}"
    )

    try:

        # --------------------------------------------------------------------
        # Load frozen validation-derived calibration parameters FIRST.
        # --------------------------------------------------------------------

        parameter_df = (
            load_cqr_parameters()
        )

        # --------------------------------------------------------------------
        # Load untouched 26C.2 test forecasts.
        # --------------------------------------------------------------------

        test_df = (
            load_test_forecasts()
        )

        # --------------------------------------------------------------------
        # Apply frozen CQR parameters.
        # --------------------------------------------------------------------

        result_df = apply_frozen_cqr(
            test_df,
            parameter_df,
        )

        # --------------------------------------------------------------------
        # Calculate test metrics.
        # --------------------------------------------------------------------

        metrics_df = calculate_metrics(
            result_df
        )

        # --------------------------------------------------------------------
        # Primary h3 summary.
        # --------------------------------------------------------------------

        primary_df = build_primary_summary(
            metrics_df
        )

        # --------------------------------------------------------------------
        # Audits.
        # --------------------------------------------------------------------

        audit_df = run_audits(
            test_df,
            parameter_df,
            result_df,
            metrics_df,
        )

        require(
            (
                audit_df["status"]
                == "PASS"
            ).all(),
            "At least one audit failed.",
        )

        # --------------------------------------------------------------------
        # Save.
        # --------------------------------------------------------------------

        save_outputs(
            result_df,
            metrics_df,
            primary_df,
            audit_df,
        )

        elapsed = (
            datetime.now(
                timezone.utc
            ) - start
        ).total_seconds()

        print("\n" + "=" * 78)
        print(
            "ALL STEP 26C.3-D ASSERTIONS: PASS"
        )
        print("=" * 78)

        print(
            f"Test forecasts evaluated: "
            f"{len(result_df)}"
        )

        print(
            f"Metric cells: "
            f"{len(metrics_df)}"
        )

        print(
            "CQR parameters: "
            "FROZEN FROM VALIDATION"
        )

        print(
            "Test recalibration: NO"
        )

        print(
            "Test data used for calibration: NO"
        )

        print(
            f"Elapsed: {elapsed:.2f} seconds"
        )

        print("=" * 78)

        return 0

    except Exception as exc:

        print("\n" + "=" * 78)
        print(
            "STEP 26C.3-D FAILED"
        )
        print("=" * 78)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print("=" * 78)

        return 1


if __name__ == "__main__":
    sys.exit(main())