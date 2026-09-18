"""
CMIDO — RO1 Step 26C.3-C
Actual Time-Aware CQR Calibration

Purpose
-------
Implement Conformalized Quantile Regression (CQR) calibration on the
FROZEN probabilistic ML forecasts produced by Step 26C.2.

Scientific rules
----------------
1. Do not retrain 26C.2 models.
2. Do not reselect 26C.2 models.
3. Do not use test observations.
4. Do not create synthetic observations.
5. Use monotone-repaired 26C.2 quantiles.
6. Use horizon-specific calibration.
7. Use series-specific calibration.
8. Use separate 50% and 80% interval calibration.
9. Preserve chronological ordering.
10. Validation prequential calibration uses only earlier forecast errors.
11. Final calibration parameters are frozen from permitted validation history.
12. Test calibration is NOT performed in this step.

This step produces:
- validation conformity scores
- prequential validation calibration parameters
- prequential validation calibrated intervals
- final frozen validation-derived calibration parameters
- audit tables
- run summary

Test forecasts are deliberately NOT loaded or modified here.
"""

from __future__ import annotations

from pathlib import Path
from math import ceil
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

RESULTS_DIR = (
    PROJECT_ROOT
    / "results"
    / "forecasting"
    / "probabilistic_calibration"
)

PROB_ML_DIR = (
    PROJECT_ROOT
    / "results"
    / "forecasting"
    / "probabilistic_ml"
)

SPEC_FILE = PROJECT_ROOT / "docs" / (
    "RO1_26C3A_Probabilistic_Calibration_Specification_v1.0.md"
)

C26C2_VALIDATION = PROB_ML_DIR / (
    "RO1_step26c2_validation_forecasts.csv"
)

C26C2_SELECTION = PROB_ML_DIR / (
    "RO1_step26c2_model_selection.csv"
)

C26C2_SPEC_JSON = PROB_ML_DIR / (
    "RO1_step26c1_probabilistic_ml_specification.json"
)

C26C2_SPEC_TXT = PROB_ML_DIR / (
    "RO1_step26c1_probabilistic_ml_specification.txt"
)


# ============================================================================
# 2. FROZEN CONFIGURATION
# ============================================================================

STEP = "26C.3-C"

CALIBRATION_METHOD = "CQR"

CALIBRATION_MODE = "PREQUENTIAL_TIME_AWARE"

HORIZONS = [1, 3, 6, 12]

PRIMARY_HORIZON = 3

QUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]

POINT_QUANTILE = 0.50

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


EXPECTED_SERIES = {
    "RO1_PRICE": [
        "Cement",
        "Concreting Sand",
        "Granite",
        "Ready Mixed Concrete",
        "Steel Reinforcement Bars",
    ],
    "RO1_DEMAND": [
        "Cement",
        "Granite",
        "Ready Mixed Concrete",
        "Steel Reinforcement Bars",
    ],
}


EXPECTED_SERIES_COUNT = 9


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


# ============================================================================
# 4. EXPECTED VALIDATION ORIGINS
# ============================================================================

EXPECTED_VALIDATION_ORIGINS = {
    1: 23,
    3: 21,
    6: 18,
    12: 12,
}


# ============================================================================
# 5. UTILITY FUNCTIONS
# ============================================================================

def log(message: str) -> None:
    print(message, flush=True)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def normalize_series(value: str) -> str:
    mapping = {
        "Cement": "Cement",
        "Cement In Bulk (Ordinary Portland Cement)": "Cement",
        "Concreting Sand": "Concreting Sand",
        "Granite": "Granite",
        "Granite (20mm Aggregate)": "Granite",
        "Ready Mixed Concrete": "Ready Mixed Concrete",
        "Ready-Mixed Concrete": "Ready Mixed Concrete",
        "Steel Reinforcement Bars": "Steel Reinforcement Bars",
        "Steel Reinforcement Bars (16-32mm High Tensile)": (
            "Steel Reinforcement Bars"
        ),
    }

    return mapping.get(str(value), str(value))


def normalize_dataset(value: str) -> str:
    value = str(value).strip()

    mapping = {
        "RO1_PRICE": "RO1_PRICE",
        "PRICE": "RO1_PRICE",
        "Price": "RO1_PRICE",
        "RO1_DEMAND": "RO1_DEMAND",
        "DEMAND": "RO1_DEMAND",
        "Demand": "RO1_DEMAND",
    }

    return mapping.get(value, value)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def find_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:

    lower_map = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for candidate in candidates:
        key = candidate.strip().lower()

        if key in lower_map:
            return lower_map[key]

    return None


# ============================================================================
# 6. QUANTILE COLUMN DISCOVERY
# ============================================================================

def find_quantile_columns(
    df: pd.DataFrame,
) -> dict[float, str]:

    result = {}

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

        col = find_column(df, candidates)

        if col is not None:
            result[q] = col

    missing = [
        q
        for q in QUANTILES
        if q not in result
    ]

    require(
        not missing,
        "Missing required quantile columns: "
        + ", ".join(map(str, missing)),
    )

    return result


# ============================================================================
# 7. LOAD 26C.2 VALIDATION FORECASTS
# ============================================================================

def load_validation_forecasts() -> pd.DataFrame:

    require(
        C26C2_VALIDATION.exists(),
        f"26C.2 validation forecast file not found:\n"
        f"{C26C2_VALIDATION}",
    )

    df = pd.read_csv(C26C2_VALIDATION)

    require(
        len(df) > 0,
        "26C.2 validation forecast file is empty.",
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
        "Missing dataset column in 26C.2 validation output.",
    )

    require(
        series_col is not None,
        "Missing series column in 26C.2 validation output.",
    )

    require(
        horizon_col is not None,
        "Missing horizon column in 26C.2 validation output.",
    )

    require(
        origin_col is not None,
        "Missing forecast-origin column in 26C.2 validation output.",
    )

    require(
        target_date_col is not None,
        "Missing target-date column in 26C.2 validation output.",
    )

    require(
        actual_col is not None,
        "Missing actual-value column in 26C.2 validation output.",
    )

    quantile_cols = find_quantile_columns(df)

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

    for q, col in quantile_cols.items():

        work[f"q{int(q * 100):02d}"] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    # ------------------------------------------------------------------------
    # Required fields
    # ------------------------------------------------------------------------

    require(
        work["horizon"].notna().all(),
        "Invalid horizon values.",
    )

    require(
        work["forecast_origin"].notna().all(),
        "Invalid forecast-origin values.",
    )

    require(
        work["target_date"].notna().all(),
        "Invalid target-date values.",
    )

    require(
        work["actual"].notna().all(),
        "Invalid/missing actual values.",
    )

    for q in QUANTILES:

        col = f"q{int(q * 100):02d}"

        require(
            work[col].notna().all(),
            f"Missing/non-numeric values in {col}.",
        )

        require(
            np.isfinite(work[col]).all(),
            f"Non-finite values in {col}.",
        )

    # ------------------------------------------------------------------------
    # Frozen horizons
    # ------------------------------------------------------------------------

    require(
        set(work["horizon"].astype(int).unique())
        <= set(HORIZONS),
        "Unexpected horizon found.",
    )

    work["horizon"] = work["horizon"].astype(int)

    # ------------------------------------------------------------------------
    # Temporal ordering
    # ------------------------------------------------------------------------

    require(
        (
            work["target_date"]
            > work["forecast_origin"]
        ).all(),
        "Target date must be after forecast origin.",
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

    monotone = np.all(
        np.diff(q_matrix, axis=1) >= -1e-12
    )

    require(
        monotone,
        "26C.2 forecasts contain quantile crossing. "
        "26C.3 requires monotone-repaired forecasts.",
    )

    # ------------------------------------------------------------------------
    # Duplicate check
    # ------------------------------------------------------------------------

    key = [
        "dataset",
        "series",
        "horizon",
        "forecast_origin",
        "target_date",
    ]

    duplicates = int(
        work.duplicated(key).sum()
    )

    require(
        duplicates == 0,
        f"Duplicate forecast records detected: {duplicates}",
    )

    # ------------------------------------------------------------------------
    # Series contract
    # ------------------------------------------------------------------------

    observed_pairs = set(
        zip(
            work["dataset"],
            work["series"],
        )
    )

    expected_pairs = set(
        EXPECTED_WINNERS
    )

    require(
        expected_pairs.issubset(observed_pairs),
        "Not all nine frozen series are present.",
    )

    log(
        f"Loaded frozen 26C.2 validation forecasts: "
        f"{len(work)} rows"
    )

    return work


# ============================================================================
# 8. CQR MATHEMATICS
# ============================================================================

def conformity_score(
    lower: float,
    upper: float,
    actual: float,
) -> float:

    score = max(
        float(lower) - float(actual),
        float(actual) - float(upper),
        0.0,
    )

    require(
        np.isfinite(score),
        "Non-finite conformity score.",
    )

    require(
        score >= 0.0,
        "Conformity score cannot be negative.",
    )

    return float(score)


def conformal_rank(
    n: int,
    alpha: float,
) -> int:

    require(
        n >= MIN_CALIBRATION_N,
        (
            f"Insufficient calibration observations: "
            f"n={n}; minimum={MIN_CALIBRATION_N}"
        ),
    )

    k = ceil(
        (n + 1) * (1.0 - alpha)
    )

    return min(k, n)


def calculate_adjustment(
    scores: list[float],
    alpha: float,
) -> tuple[int, float]:

    n = len(scores)

    require(
        n >= MIN_CALIBRATION_N,
        f"Calibration n={n} is below minimum.",
    )

    arr = np.asarray(
        scores,
        dtype=float,
    )

    require(
        np.all(np.isfinite(arr)),
        "Calibration scores contain non-finite values.",
    )

    require(
        np.all(arr >= 0),
        "Calibration scores must be non-negative.",
    )

    arr = np.sort(arr)

    k = conformal_rank(
        n,
        alpha,
    )

    adjustment = float(
        arr[k - 1]
    )

    require(
        adjustment >= 0,
        "Conformal adjustment cannot be negative.",
    )

    return k, adjustment


def apply_interval_calibration(
    lower: float,
    upper: float,
    adjustment: float,
) -> tuple[float, float]:

    lower_cal = max(
        0.0,
        float(lower) - float(adjustment),
    )

    upper_cal = (
        float(upper)
        + float(adjustment)
    )

    require(
        lower_cal <= upper_cal,
        "Calibrated interval is invalid.",
    )

    return lower_cal, upper_cal


# ============================================================================
# 9. BUILD INTERVALS AND SCORES
# ============================================================================

def add_raw_intervals(
    df: pd.DataFrame,
) -> pd.DataFrame:

    work = df.copy()

    work["raw_lower_50"] = work["q25"]
    work["raw_upper_50"] = work["q75"]

    work["raw_lower_80"] = work["q10"]
    work["raw_upper_80"] = work["q90"]

    require(
        (
            work["raw_lower_50"]
            <= work["raw_upper_50"]
        ).all(),
        "Invalid raw 50% intervals.",
    )

    require(
        (
            work["raw_lower_80"]
            <= work["raw_upper_80"]
        ).all(),
        "Invalid raw 80% intervals.",
    )

    return work


def calculate_scores(
    df: pd.DataFrame,
) -> pd.DataFrame:

    work = df.copy()

    work["score_50"] = [
        conformity_score(
            l,
            u,
            y,
        )
        for l, u, y in zip(
            work["raw_lower_50"],
            work["raw_upper_50"],
            work["actual"],
        )
    ]

    work["score_80"] = [
        conformity_score(
            l,
            u,
            y,
        )
        for l, u, y in zip(
            work["raw_lower_80"],
            work["raw_upper_80"],
            work["actual"],
        )
    ]

    return work


# ============================================================================
# 10. PREQUENTIAL VALIDATION CALIBRATION
# ============================================================================

def prequential_validation_calibration(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    """
    For each series × horizon:

    Sort validation origins chronologically.

    For forecast origin t:
        calibration scores may only come from observations with
        forecast origins strictly earlier than t.

    Therefore the current target's own score is NEVER used to calibrate
    its interval.

    A forecast becomes eligible for calibrated evaluation once at least
    MIN_CALIBRATION_N earlier scores exist.

    This is a validation diagnostic of time-aware calibration.

    Returns
    -------
    calibrated_forecasts
    prequential_parameters
    """

    forecast_rows = []
    parameter_rows = []

    grouped = df.groupby(
        [
            "dataset",
            "series",
            "horizon",
        ],
        sort=True,
    )

    for (dataset, series, horizon), group in grouped:

        group = group.sort_values(
            [
                "forecast_origin",
                "target_date",
            ]
        ).reset_index(drop=True)

        require(
            len(group) == EXPECTED_VALIDATION_ORIGINS[horizon],
            (
                f"Unexpected validation-origin count for "
                f"{dataset}/{series}/h{horizon}: "
                f"{len(group)}; expected "
                f"{EXPECTED_VALIDATION_ORIGINS[horizon]}"
            ),
        )

        prior_scores_50 = []
        prior_scores_80 = []

        for idx, row in group.iterrows():

            n50 = len(prior_scores_50)
            n80 = len(prior_scores_80)

            eligible_50 = (
                n50 >= MIN_CALIBRATION_N
            )

            eligible_80 = (
                n80 >= MIN_CALIBRATION_N
            )

            adjustment_50 = np.nan
            adjustment_80 = np.nan

            rank_50 = np.nan
            rank_80 = np.nan

            lower_50 = np.nan
            upper_50 = np.nan

            lower_80 = np.nan
            upper_80 = np.nan

            if eligible_50:

                rank_50, adjustment_50 = (
                    calculate_adjustment(
                        prior_scores_50,
                        INTERVALS["50"]["alpha"],
                    )
                )

                lower_50, upper_50 = (
                    apply_interval_calibration(
                        row["raw_lower_50"],
                        row["raw_upper_50"],
                        adjustment_50,
                    )
                )

            if eligible_80:

                rank_80, adjustment_80 = (
                    calculate_adjustment(
                        prior_scores_80,
                        INTERVALS["80"]["alpha"],
                    )
                )

                lower_80, upper_80 = (
                    apply_interval_calibration(
                        row["raw_lower_80"],
                        row["raw_upper_80"],
                        adjustment_80,
                    )
                )

            forecast_rows.append(
                {
                    "dataset": dataset,
                    "series": series,
                    "horizon": horizon,
                    "forecast_origin": row[
                        "forecast_origin"
                    ],
                    "target_date": row[
                        "target_date"
                    ],
                    "actual": row["actual"],

                    "q10": row["q10"],
                    "q25": row["q25"],
                    "q50": row["q50"],
                    "q75": row["q75"],
                    "q90": row["q90"],

                    "raw_lower_50": row[
                        "raw_lower_50"
                    ],
                    "raw_upper_50": row[
                        "raw_upper_50"
                    ],

                    "raw_lower_80": row[
                        "raw_lower_80"
                    ],
                    "raw_upper_80": row[
                        "raw_upper_80"
                    ],

                    "calibrated_lower_50": lower_50,
                    "calibrated_upper_50": upper_50,

                    "calibrated_lower_80": lower_80,
                    "calibrated_upper_80": upper_80,

                    "calibration_n_50": n50,
                    "calibration_n_80": n80,

                    "conformal_rank_50": rank_50,
                    "conformal_rank_80": rank_80,

                    "adjustment_50": adjustment_50,
                    "adjustment_80": adjustment_80,

                    "calibration_available_50": (
                        eligible_50
                    ),
                    "calibration_available_80": (
                        eligible_80
                    ),
                }
            )

            # IMPORTANT:
            # Only AFTER evaluating the current forecast do we add its
            # conformity scores to the historical calibration pool.
            prior_scores_50.append(
                float(row["score_50"])
            )

            prior_scores_80.append(
                float(row["score_80"])
            )

        # --------------------------------------------------------------------
        # Store final frozen validation parameters based on the FULL
        # permitted validation history.
        #
        # These are NOT applied to the current validation observations as
        # an independent evaluation. They are reserved for downstream
        # untouched-test application.
        # --------------------------------------------------------------------

        final_n50 = len(prior_scores_50)
        final_n80 = len(prior_scores_80)

        require(
            final_n50 == len(group),
            "Final 50% score count mismatch.",
        )

        require(
            final_n80 == len(group),
            "Final 80% score count mismatch.",
        )

        final_rank_50, final_adjustment_50 = (
            calculate_adjustment(
                prior_scores_50,
                INTERVALS["50"]["alpha"],
            )
        )

        final_rank_80, final_adjustment_80 = (
            calculate_adjustment(
                prior_scores_80,
                INTERVALS["80"]["alpha"],
            )
        )

        parameter_rows.append(
            {
                "dataset": dataset,
                "series": series,
                "horizon": horizon,

                "interval": "50",
                "alpha": INTERVALS["50"]["alpha"],
                "nominal_coverage": (
                    INTERVALS["50"]["nominal_coverage"]
                ),

                "calibration_n": final_n50,
                "conformal_rank": final_rank_50,
                "conformal_adjustment": (
                    final_adjustment_50
                ),

                "calibration_mode": (
                    CALIBRATION_MODE
                ),

                "parameter_status": (
                    "FROZEN_FROM_VALIDATION"
                ),
            }
        )

        parameter_rows.append(
            {
                "dataset": dataset,
                "series": series,
                "horizon": horizon,

                "interval": "80",
                "alpha": INTERVALS["80"]["alpha"],
                "nominal_coverage": (
                    INTERVALS["80"]["nominal_coverage"]
                ),

                "calibration_n": final_n80,
                "conformal_rank": final_rank_80,
                "conformal_adjustment": (
                    final_adjustment_80
                ),

                "calibration_mode": (
                    CALIBRATION_MODE
                ),

                "parameter_status": (
                    "FROZEN_FROM_VALIDATION"
                ),
            }
        )

    forecast_df = pd.DataFrame(
        forecast_rows
    )

    parameter_df = pd.DataFrame(
        parameter_rows
    )

    return forecast_df, parameter_df


# ============================================================================
# 11. VALIDATION METRICS
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
        "No valid observations for coverage calculation.",
    )

    covered = (
        (actual[mask] >= lower[mask])
        & (actual[mask] <= upper[mask])
    )

    return float(
        covered.mean()
    )


def winkler_score(
    actual: pd.Series,
    lower: pd.Series,
    upper: pd.Series,
    alpha: float,
) -> float:

    mask = (
        actual.notna()
        & lower.notna()
        & upper.notna()
    )

    y = actual[mask].to_numpy(
        dtype=float
    )

    l = lower[mask].to_numpy(
        dtype=float
    )

    u = upper[mask].to_numpy(
        dtype=float
    )

    scores = u - l

    below = y < l
    above = y > u

    scores[below] += (
        (2.0 / alpha)
        * (l[below] - y[below])
    )

    scores[above] += (
        (2.0 / alpha)
        * (y[above] - u[above])
    )

    return float(
        np.mean(scores)
    )


def calculate_metrics(
    calibrated_df: pd.DataFrame,
) -> pd.DataFrame:

    rows = []

    grouped = calibrated_df.groupby(
        [
            "dataset",
            "series",
            "horizon",
        ],
        sort=True,
    )

    for (dataset, series, horizon), group in grouped:

        # ---------------------------------------------------------------
        # Raw ML
        # ---------------------------------------------------------------

        raw_mask = (
            group["actual"].notna()
        )

        actual = group.loc[
            raw_mask,
            "actual",
        ]

        q50 = group.loc[
            raw_mask,
            "q50",
        ]

        mae = float(
            np.mean(
                np.abs(
                    actual.to_numpy()
                    - q50.to_numpy()
                )
            )
        )

        rmse = float(
            np.sqrt(
                np.mean(
                    (
                        actual.to_numpy()
                        - q50.to_numpy()
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

        raw_width_50 = float(
            (
                group["raw_upper_50"]
                - group["raw_lower_50"]
            ).mean()
        )

        raw_width_80 = float(
            (
                group["raw_upper_80"]
                - group["raw_lower_80"]
            ).mean()
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
        # Prequential calibrated intervals
        # ---------------------------------------------------------------

        cal50 = group[
            "calibration_available_50"
        ]

        cal80 = group[
            "calibration_available_80"
        ]

        cal50_group = group.loc[
            cal50
        ]

        cal80_group = group.loc[
            cal80
        ]

        if len(cal50_group) > 0:

            cal_cov_50 = coverage(
                cal50_group["actual"],
                cal50_group[
                    "calibrated_lower_50"
                ],
                cal50_group[
                    "calibrated_upper_50"
                ],
            )

            cal_width_50 = float(
                (
                    cal50_group[
                        "calibrated_upper_50"
                    ]
                    - cal50_group[
                        "calibrated_lower_50"
                    ]
                ).mean()
            )

            cal_winkler_50 = winkler_score(
                cal50_group["actual"],
                cal50_group[
                    "calibrated_lower_50"
                ],
                cal50_group[
                    "calibrated_upper_50"
                ],
                alpha=0.50,
            )

        else:

            cal_cov_50 = np.nan
            cal_width_50 = np.nan
            cal_winkler_50 = np.nan

        if len(cal80_group) > 0:

            cal_cov_80 = coverage(
                cal80_group["actual"],
                cal80_group[
                    "calibrated_lower_80"
                ],
                cal80_group[
                    "calibrated_upper_80"
                ],
            )

            cal_width_80 = float(
                (
                    cal80_group[
                        "calibrated_upper_80"
                    ]
                    - cal80_group[
                        "calibrated_lower_80"
                    ]
                ).mean()
            )

            cal_winkler_80 = winkler_score(
                cal80_group["actual"],
                cal80_group[
                    "calibrated_lower_80"
                ],
                cal80_group[
                    "calibrated_upper_80"
                ],
                alpha=0.20,
            )

        else:

            cal_cov_80 = np.nan
            cal_width_80 = np.nan
            cal_winkler_80 = np.nan

        rows.append(
            {
                "dataset": dataset,
                "series": series,
                "horizon": horizon,

                "n_raw": len(group),

                "n_calibrated_50": len(
                    cal50_group
                ),

                "n_calibrated_80": len(
                    cal80_group
                ),

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

                "prequential_coverage_50": (
                    cal_cov_50
                ),

                "prequential_coverage_80": (
                    cal_cov_80
                ),

                "prequential_coverage_error_50": (
                    np.nan
                    if pd.isna(cal_cov_50)
                    else abs(cal_cov_50 - 0.50)
                ),

                "prequential_coverage_error_80": (
                    np.nan
                    if pd.isna(cal_cov_80)
                    else abs(cal_cov_80 - 0.80)
                ),

                "prequential_mean_width_50": (
                    cal_width_50
                ),

                "prequential_mean_width_80": (
                    cal_width_80
                ),

                "prequential_winkler_50": (
                    cal_winkler_50
                ),

                "prequential_winkler_80": (
                    cal_winkler_80
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================================
# 12. AUDITS
# ============================================================================

def run_audits(
    source_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    parameter_df: pd.DataFrame,
) -> pd.DataFrame:

    audit_rows = []

    def add(
        name: str,
        status: str,
        detail: str,
    ) -> None:

        audit_rows.append(
            {
                "audit": name,
                "status": status,
                "detail": detail,
            }
        )

    # ------------------------------------------------------------------------
    # Series
    # ------------------------------------------------------------------------

    observed_series = set(
        zip(
            source_df["dataset"],
            source_df["series"],
        )
    )

    require(
        set(EXPECTED_WINNERS).issubset(
            observed_series
        ),
        "Series audit failed.",
    )

    add(
        "series_count",
        "PASS",
        "Nine frozen series present.",
    )

    # ------------------------------------------------------------------------
    # Horizons
    # ------------------------------------------------------------------------

    require(
        set(source_df["horizon"].unique())
        == set(HORIZONS),
        "Horizon audit failed.",
    )

    add(
        "horizon_set",
        "PASS",
        "Horizon set is 1,3,6,12.",
    )

    # ------------------------------------------------------------------------
    # Temporal ordering
    # ------------------------------------------------------------------------

    require(
        (
            forecast_df["target_date"]
            > forecast_df["forecast_origin"]
        ).all(),
        "Forecast target chronology failed.",
    )

    add(
        "forecast_chronology",
        "PASS",
        "Target dates occur after forecast origins.",
    )

    # ------------------------------------------------------------------------
    # Prequential leakage
    # ------------------------------------------------------------------------

    available = forecast_df[
        "calibration_available_50"
    ]

    if available.any():

        require(
            (
                forecast_df.loc[
                    available,
                    "calibration_n_50",
                ]
                >= MIN_CALIBRATION_N
            ).all(),
            "Minimum 50% calibration n failed.",
        )

    available80 = forecast_df[
        "calibration_available_80"
    ]

    if available80.any():

        require(
            (
                forecast_df.loc[
                    available80,
                    "calibration_n_80",
                ]
                >= MIN_CALIBRATION_N
            ).all(),
            "Minimum 80% calibration n failed.",
        )

    add(
        "minimum_calibration_n",
        "PASS",
        f"Minimum calibration n={MIN_CALIBRATION_N}.",
    )

    # ------------------------------------------------------------------------
    # No current target self-calibration
    # ------------------------------------------------------------------------

    require(
        (
            forecast_df[
                "calibration_n_50"
            ]
            < forecast_df.groupby(
                [
                    "dataset",
                    "series",
                    "horizon",
                ]
            ).cumcount()
            + 1
        ).all(),
        (
            "Potential current-observation inclusion "
            "detected in 50% calibration."
        ),
    )

    require(
        (
            forecast_df[
                "calibration_n_80"
            ]
            < forecast_df.groupby(
                [
                    "dataset",
                    "series",
                    "horizon",
                ]
            ).cumcount()
            + 1
        ).all(),
        (
            "Potential current-observation inclusion "
            "detected in 80% calibration."
        ),
    )

    add(
        "prequential_leakage",
        "PASS",
        "Current forecast score is added only after "
        "current prediction evaluation.",
    )

    # ------------------------------------------------------------------------
    # Calibration parameters
    # ------------------------------------------------------------------------

    require(
        len(parameter_df)
        == EXPECTED_SERIES_COUNT
        * len(HORIZONS)
        * 2,
        (
            "Expected 72 final calibration parameter rows; "
            f"found {len(parameter_df)}."
        ),
    )

    require(
        (
            parameter_df[
                "parameter_status"
            ]
            == "FROZEN_FROM_VALIDATION"
        ).all(),
        "Final calibration parameters are not frozen.",
    )

    require(
        (
            parameter_df[
                "conformal_adjustment"
            ]
            >= 0
        ).all(),
        "Negative conformal adjustment detected.",
    )

    add(
        "calibration_parameter_count",
        "PASS",
        "72 series × horizon × interval parameter cells.",
    )

    # ------------------------------------------------------------------------
    # Test isolation
    # ------------------------------------------------------------------------

    require(
        not any(
            [
                "test" in str(c).lower()
                for c in source_df.columns
            ]
        ),
        "Unexpected test field detected in source dataframe.",
    )

    add(
        "test_isolation",
        "PASS",
        "Only 26C.2 validation forecasts loaded; no test forecasts used.",
    )

    # ------------------------------------------------------------------------
    # Synthetic data
    # ------------------------------------------------------------------------

    add(
        "synthetic_calibration",
        "PASS",
        "No synthetic calibration observations generated.",
    )

    # ------------------------------------------------------------------------
    # Model changes
    # ------------------------------------------------------------------------

    add(
        "model_retraining",
        "PASS",
        "No forecasting models retrained.",
    )

    add(
        "model_reselection",
        "PASS",
        "No forecasting models reselected.",
    )

    return pd.DataFrame(audit_rows)


# ============================================================================
# 13. SAVE OUTPUTS
# ============================================================================

def save_outputs(
    source_df: pd.DataFrame,
    calibrated_df: pd.DataFrame,
    parameter_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    audit_df: pd.DataFrame,
) -> None:

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    scores_path = RESULTS_DIR / (
        "RO1_step26c3_calibration_scores.csv"
    )

    parameters_path = RESULTS_DIR / (
        "RO1_step26c3_calibration_parameters.csv"
    )

    validation_forecasts_path = RESULTS_DIR / (
        "RO1_step26c3_validation_forecasts.csv"
    )

    validation_metrics_path = RESULTS_DIR / (
        "RO1_step26c3_validation_metrics.csv"
    )

    audit_path = RESULTS_DIR / (
        "RO1_step26c3_audit.csv"
    )

    summary_path = RESULTS_DIR / (
        "RO1_step26c3_run_summary.txt"
    )

    # ------------------------------------------------------------------------
    # Calibration scores
    # ------------------------------------------------------------------------

    score_columns = [
        "dataset",
        "series",
        "horizon",
        "forecast_origin",
        "target_date",
        "actual",
        "raw_lower_50",
        "raw_upper_50",
        "raw_lower_80",
        "raw_upper_80",
        "score_50",
        "score_80",
    ]

    source_df[
        score_columns
    ].to_csv(
        scores_path,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Final frozen parameters
    # ------------------------------------------------------------------------

    parameter_df.to_csv(
        parameters_path,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Validation forecasts
    # ------------------------------------------------------------------------

    calibrated_df.to_csv(
        validation_forecasts_path,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Validation metrics
    # ------------------------------------------------------------------------

    metrics_df.to_csv(
        validation_metrics_path,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Audits
    # ------------------------------------------------------------------------

    audit_df.to_csv(
        audit_path,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------------

    spec_hash = (
        sha256_file(SPEC_FILE)
        if SPEC_FILE.exists()
        else None
    )

    c26c2_hash = (
        sha256_file(C26C2_VALIDATION)
        if C26C2_VALIDATION.exists()
        else None
    )

    lines = [
        "CMIDO — RO1 STEP 26C.3-C",
        "Actual Time-Aware CQR Calibration",
        "",
        "STATUS: PASS",
        "",
        f"Calibration method: {CALIBRATION_METHOD}",
        f"Calibration mode: {CALIBRATION_MODE}",
        f"Minimum calibration n: {MIN_CALIBRATION_N}",
        f"Horizons: {HORIZONS}",
        f"Primary horizon: {PRIMARY_HORIZON}",
        f"Quantiles: {QUANTILES}",
        "",
        "50% interval: q25–q75",
        "80% interval: q10–q90",
        "",
        "Model retraining: DISABLED",
        "Model reselection: DISABLED",
        "Random split: DISABLED",
        "Synthetic calibration: DISABLED",
        "Test-data calibration: DISABLED",
        "",
        f"Validation source rows: {len(source_df)}",
        f"Prequential calibrated rows: {len(calibrated_df)}",
        f"Final calibration parameter rows: {len(parameter_df)}",
        "",
        "Final calibration parameters:",
        "FROZEN FROM VALIDATION",
        "",
        "Test forecasts were NOT loaded or modified in 26C.3-C.",
        "",
        f"26C.3-A specification SHA256: {spec_hash}",
        f"26C.2 validation SHA256: {c26c2_hash}",
        "",
        "Output files:",
        str(scores_path),
        str(parameters_path),
        str(validation_forecasts_path),
        str(validation_metrics_path),
        str(audit_path),
        str(summary_path),
        "",
        "ALL STEP 26C.3-C ASSERTIONS: PASS",
    ]

    summary_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    log("\nSaved outputs:")

    for path in [
        scores_path,
        parameters_path,
        validation_forecasts_path,
        validation_metrics_path,
        audit_path,
        summary_path,
    ]:
        log(f"  {path}")


# ============================================================================
# 14. MAIN
# ============================================================================

def main() -> int:

    start = datetime.now(
        timezone.utc
    )

    print("=" * 78)
    print("CMIDO — RO1 STEP 26C.3-C")
    print("ACTUAL TIME-AWARE CQR CALIBRATION")
    print("=" * 78)

    log(f"Project root: {PROJECT_ROOT}")
    log(f"Calibration method: {CALIBRATION_METHOD}")
    log(f"Calibration mode: {CALIBRATION_MODE}")
    log(f"Minimum calibration n: {MIN_CALIBRATION_N}")
    log(f"Horizons: {HORIZONS}")
    log(f"Primary horizon: {PRIMARY_HORIZON}")
    log(f"Quantiles: {QUANTILES}")

    log("50% interval: q25–q75")
    log("80% interval: q10–q90")

    log("Models frozen: YES")
    log("Model retraining: NO")
    log("Model reselection: NO")
    log("Random split: NO")
    log("Synthetic calibration: NO")
    log("Test calibration: NO")

    try:

        # --------------------------------------------------------------------
        # Load
        # --------------------------------------------------------------------

        source_df = load_validation_forecasts()

        # --------------------------------------------------------------------
        # Construct raw intervals
        # --------------------------------------------------------------------

        source_df = add_raw_intervals(
            source_df
        )

        # --------------------------------------------------------------------
        # Calculate conformity scores
        # --------------------------------------------------------------------

        source_df = calculate_scores(
            source_df
        )

        # --------------------------------------------------------------------
        # Prequential calibration
        # --------------------------------------------------------------------

        (
            calibrated_df,
            parameter_df,
        ) = prequential_validation_calibration(
            source_df
        )

        # --------------------------------------------------------------------
        # Validation metrics
        # --------------------------------------------------------------------

        metrics_df = calculate_metrics(
            calibrated_df
        )

        # --------------------------------------------------------------------
        # Audits
        # --------------------------------------------------------------------

        audit_df = run_audits(
            source_df,
            calibrated_df,
            parameter_df,
        )

        require(
            (
                audit_df["status"]
                == "PASS"
            ).all(),
            "At least one audit failed.",
        )

        # --------------------------------------------------------------------
        # Save
        # --------------------------------------------------------------------

        save_outputs(
            source_df,
            calibrated_df,
            parameter_df,
            metrics_df,
            audit_df,
        )

        elapsed = (
            datetime.now(
                timezone.utc
            ) - start
        ).total_seconds()

        print("\n" + "=" * 78)
        print("ALL STEP 26C.3-C ASSERTIONS: PASS")
        print("=" * 78)
        print(
            f"Validation rows: {len(source_df)}"
        )
        print(
            f"Prequential calibrated rows: "
            f"{len(calibrated_df)}"
        )
        print(
            f"Frozen parameter rows: "
            f"{len(parameter_df)}"
        )
        print(
            "Calibration parameters: "
            "FROZEN FROM VALIDATION"
        )
        print(
            "Test data used: NO"
        )
        print(
            f"Elapsed: {elapsed:.2f} seconds"
        )
        print("=" * 78)

        return 0

    except Exception as exc:

        print("\n" + "=" * 78)
        print("STEP 26C.3-C FAILED")
        print("=" * 78)
        print(
            f"{type(exc).__name__}: {exc}"
        )
        print("=" * 78)

        return 1


if __name__ == "__main__":
    sys.exit(main())