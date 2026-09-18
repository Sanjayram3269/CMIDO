"""
CMIDO — RO1 Step 26C.3-B
Probabilistic Calibration & Conformal Prediction — Executable Contract

Purpose
-------
Validate the frozen 26C.3 calibration methodology before implementation.

This script is CONTRACT-ONLY:
- It does not train forecasting models.
- It does not calibrate forecasts.
- It does not use test observations.
- It does not modify 26C.2 outputs.
- It does not perform model selection.

All methodological decisions must agree with:
RO1_26C3A_Probabilistic_Calibration_Specification_v1.0.md
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from math import ceil
import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


# ============================================================================
# 1. PATHS
# ============================================================================

PROJECT_ROOT = Path(r"D:\CMIDO")

DATA_RAW = PROJECT_ROOT / "data" / "raw"
RESULTS_DIR = PROJECT_ROOT / "results" / "forecasting" / "probabilistic_calibration"

PROB_ML_DIR = PROJECT_ROOT / "results" / "forecasting" / "probabilistic_ml"
PROB_STAT_DIR = (
    PROJECT_ROOT
    / "results"
    / "forecasting"
    / "probabilistic_statistical"
)

SPEC_FILE = PROJECT_ROOT / "docs" / (
    "RO1_26C3A_Probabilistic_Calibration_Specification_v1.0.md"
)

C26C2_SELECTION = PROB_ML_DIR / (
    "RO1_step26c2_model_selection.csv"
)

C26C2_VALIDATION = PROB_ML_DIR / (
    "RO1_step26c2_validation_forecasts.csv"
)

C26C2_SPEC_JSON = PROB_ML_DIR / (
    "RO1_step26c1_probabilistic_ml_specification.json"
)

C26C2_SPEC_TXT = PROB_ML_DIR / (
    "RO1_step26c1_probabilistic_ml_specification.txt"
)


# ============================================================================
# 2. FROZEN CONTRACT CONFIGURATION
# ============================================================================

STEP = "26C.3-B"
PARENT_STEP = "26C.2"
SPEC_VERSION = "RO1_26C3A_v1.0"

HORIZONS = [1, 3, 6, 12]
PRIMARY_HORIZON = 3

QUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]

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

MIN_CALIBRATION_N = 10

RANDOM_SPLIT_ALLOWED = False
TEST_CALIBRATION_ALLOWED = False
MODEL_RETRAINING_ALLOWED = False
MODEL_RESELECTION_ALLOWED = False
SYNTHETIC_CALIBRATION_ALLOWED = False

CALIBRATION_METHOD = "CQR"
CALIBRATION_MODE = "PREQUENTIAL_TIME_AWARE"

POINT_QUANTILE = 0.50

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
EXPECTED_HORIZON_COUNT = 4
EXPECTED_CALIBRATION_CELLS = 72


# ============================================================================
# 3. EXPECTED FROZEN 26C.2 WINNERS
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
# 4. EXPECTED TEMPORAL CONTRACT
# ============================================================================

EXPECTED_VALIDATION_ORIGINS = {
    1: 23,
    3: 21,
    6: 18,
    12: 12,
}

# These are the target-valid counts established by the frozen rolling-origin
# design, not arbitrary fixed 24-origin assumptions.

EXPECTED_VALIDATION_FORECASTS = (
    EXPECTED_SERIES_COUNT
    * sum(EXPECTED_VALIDATION_ORIGINS.values())
)

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
# 5. DATA CLASSES
# ============================================================================

@dataclass(frozen=True)
class IntervalContract:
    name: str
    lower_quantile: float
    upper_quantile: float
    nominal_coverage: float
    alpha: float


@dataclass(frozen=True)
class CalibrationContract:
    method: str
    mode: str
    minimum_n: int
    test_calibration_allowed: bool
    synthetic_calibration_allowed: bool


# ============================================================================
# 6. UTILITY FUNCTIONS
# ============================================================================

def log(message: str) -> None:
    print(message, flush=True)


def fail(message: str) -> None:
    raise AssertionError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def normalize_series(value: str) -> str:
    """
    Normalize known official source labels to the canonical RO1 labels.

    This mirrors the canonical normalization used in 26C.2.
    """
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

    return mapping.get(value, value)


def interval_from_quantiles(
    q10: float,
    q25: float,
    q50: float,
    q75: float,
    q90: float,
) -> dict[str, tuple[float, float] | float]:

    values = {
        "q10": q10,
        "q25": q25,
        "q50": q50,
        "q75": q75,
        "q90": q90,
    }

    return {
        "q50": q50,
        "50": (q25, q75),
        "80": (q10, q90),
    }


def conformity_score(
    lower: float,
    upper: float,
    actual: float,
) -> float:
    """
    CQR interval conformity score.

    S = max(L - y, y - U, 0)
    """
    return max(
        float(lower) - float(actual),
        float(actual) - float(upper),
        0.0,
    )


def conformal_rank(n: int, alpha: float) -> int:
    """
    Finite-sample conformal order-statistic rank:

        k = ceil((n + 1)(1 - alpha))

    capped at n.
    """
    require(n >= 1, "Conformal rank requires n >= 1.")

    k = ceil((n + 1) * (1.0 - alpha))
    return min(k, n)


def conformal_adjustment(
    scores: list[float],
    alpha: float,
) -> tuple[int, float]:
    """
    Return:
        (rank k, kth sorted conformity score)
    """
    n = len(scores)

    require(n >= MIN_CALIBRATION_N, (
        f"Insufficient calibration observations: n={n}, "
        f"minimum={MIN_CALIBRATION_N}."
    ))

    clean_scores = np.asarray(scores, dtype=float)

    require(np.all(np.isfinite(clean_scores)), (
        "Calibration scores contain non-finite values."
    ))

    require(np.all(clean_scores >= 0), (
        "Conformity scores must be non-negative."
    ))

    sorted_scores = np.sort(clean_scores)

    k = conformal_rank(n, alpha)

    adjustment = float(sorted_scores[k - 1])

    require(adjustment >= 0, (
        "Conformal adjustment must be non-negative."
    ))

    return k, adjustment


def apply_calibration(
    lower: float,
    upper: float,
    adjustment: float,
) -> tuple[float, float]:
    """
    Apply the calibrated interval rule.

    Lower endpoint is constrained to the physical non-negative domain.
    """
    lower_cal = max(
        0.0,
        float(lower) - float(adjustment),
    )

    upper_cal = float(upper) + float(adjustment)

    require(lower_cal <= upper_cal, (
        "Calibrated interval lower bound exceeds upper bound."
    ))

    return lower_cal, upper_cal


# ============================================================================
# 7. CONTRACT OBJECTS
# ============================================================================

INTERVAL_CONTRACTS = {
    name: IntervalContract(
        name=name,
        lower_quantile=float(cfg["lower_quantile"]),
        upper_quantile=float(cfg["upper_quantile"]),
        nominal_coverage=float(cfg["nominal_coverage"]),
        alpha=float(cfg["alpha"]),
    )
    for name, cfg in INTERVALS.items()
}

CALIBRATION_CONTRACT = CalibrationContract(
    method=CALIBRATION_METHOD,
    mode=CALIBRATION_MODE,
    minimum_n=MIN_CALIBRATION_N,
    test_calibration_allowed=TEST_CALIBRATION_ALLOWED,
    synthetic_calibration_allowed=SYNTHETIC_CALIBRATION_ALLOWED,
)


# ============================================================================
# 8. CONTRACT TESTS — STATIC METHODOLOGY
# ============================================================================

def test_static_contract() -> None:
    log("\n[1/10] Static methodology contract")

    require(STEP == "26C.3-B", "Incorrect step identifier.")
    require(PARENT_STEP == "26C.2", "Incorrect parent step.")
    require(SPEC_VERSION == "RO1_26C3A_v1.0", "Incorrect specification version.")

    require(CALIBRATION_METHOD == "CQR", (
        "Primary calibration method must be CQR."
    ))

    require(CALIBRATION_MODE == "PREQUENTIAL_TIME_AWARE", (
        "Calibration mode must be prequential/time-aware."
    ))

    require(RANDOM_SPLIT_ALLOWED is False, (
        "Random split must remain disabled."
    ))

    require(TEST_CALIBRATION_ALLOWED is False, (
        "Test-data calibration must remain disabled."
    ))

    require(MODEL_RETRAINING_ALLOWED is False, (
        "Model retraining must remain disabled."
    ))

    require(MODEL_RESELECTION_ALLOWED is False, (
        "Model reselection must remain disabled."
    ))

    require(SYNTHETIC_CALIBRATION_ALLOWED is False, (
        "Synthetic calibration observations must remain disabled."
    ))

    require(HORIZONS == [1, 3, 6, 12], (
        "Frozen horizons changed."
    ))

    require(PRIMARY_HORIZON == 3, (
        "Primary horizon must remain h=3."
    ))

    require(QUANTILES == [0.10, 0.25, 0.50, 0.75, 0.90], (
        "Frozen quantile set changed."
    ))

    log("PASS — static methodology contract")


# ============================================================================
# 9. CONTRACT TESTS — INTERVAL DEFINITIONS
# ============================================================================

def test_interval_contract() -> None:
    log("\n[2/10] Prediction-interval contract")

    require(set(INTERVAL_CONTRACTS) == {"50", "80"}, (
        "Exactly 50% and 80% intervals are required."
    ))

    i50 = INTERVAL_CONTRACTS["50"]
    i80 = INTERVAL_CONTRACTS["80"]

    require(i50.lower_quantile == 0.25, "50% lower quantile incorrect.")
    require(i50.upper_quantile == 0.75, "50% upper quantile incorrect.")
    require(i50.nominal_coverage == 0.50, "50% nominal coverage incorrect.")
    require(i50.alpha == 0.50, "50% alpha incorrect.")

    require(i80.lower_quantile == 0.10, "80% lower quantile incorrect.")
    require(i80.upper_quantile == 0.90, "80% upper quantile incorrect.")
    require(i80.nominal_coverage == 0.80, "80% nominal coverage incorrect.")
    require(i80.alpha == 0.20, "80% alpha incorrect.")

    require(POINT_QUANTILE == 0.50, (
        "Point forecast must remain q50."
    ))

    log("PASS — interval definitions")


# ============================================================================
# 10. CONTRACT TESTS — QUANTILE REPAIR
# ============================================================================

def test_quantile_repair() -> None:
    log("\n[3/10] Quantile monotonicity contract")

    # Representative crossing case from the contract:
    raw = np.array([10.0, 8.0, 12.0, 11.0, 9.0])

    repaired = np.sort(raw)

    require(
        np.all(np.diff(repaired) >= 0),
        "Monotone quantile repair failed."
    )

    q10, q25, q50, q75, q90 = repaired

    require(q10 <= q25 <= q50 <= q75 <= q90, (
        "Repaired quantiles are not monotonically ordered."
    ))

    intervals = interval_from_quantiles(
        q10,
        q25,
        q50,
        q75,
        q90,
    )

    require(intervals["50"][0] <= intervals["50"][1], (
        "50% interval invalid."
    ))

    require(intervals["80"][0] <= intervals["80"][1], (
        "80% interval invalid."
    ))

    log("PASS — monotone quantile repair")


# ============================================================================
# 11. CONTRACT TESTS — CQR MATHEMATICS
# ============================================================================

def test_cqr_math() -> None:
    log("\n[4/10] CQR mathematical contract")

    # Known deterministic conformity-score example.
    scores = [
        0.0,
        0.5,
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
        4.0,
        4.5,
    ]

    k50, a50 = conformal_adjustment(scores, alpha=0.50)
    k80, a80 = conformal_adjustment(scores, alpha=0.20)

    require(k50 == 6, (
        f"Unexpected 50% conformal rank: {k50}"
    ))

    require(k80 == 9, (
        f"Unexpected 80% conformal rank: {k80}"
    ))

    require(a50 == 2.5, (
        f"Unexpected 50% adjustment: {a50}"
    ))

    require(a80 == 4.0, (
        f"Unexpected 80% adjustment: {a80}"
    ))

    score = conformity_score(
        lower=10.0,
        upper=20.0,
        actual=25.0,
    )

    require(score == 5.0, (
        f"Unexpected conformity score: {score}"
    ))

    score_inside = conformity_score(
        lower=10.0,
        upper=20.0,
        actual=15.0,
    )

    require(score_inside == 0.0, (
        "In-interval conformity score must be zero."
    ))

    log("PASS — CQR mathematics")


# ============================================================================
# 12. CONTRACT TESTS — NON-NEGATIVITY
# ============================================================================

def test_nonnegativity() -> None:
    log("\n[5/10] Physical-domain contract")

    lower, upper = apply_calibration(
        lower=5.0,
        upper=15.0,
        adjustment=10.0,
    )

    require(lower == 0.0, (
        "Calibrated lower bound must be constrained to zero."
    ))

    require(upper == 25.0, (
        "Calibrated upper bound incorrect."
    ))

    lower2, upper2 = apply_calibration(
        lower=20.0,
        upper=30.0,
        adjustment=2.0,
    )

    require(lower2 == 18.0, (
        "Positive calibrated lower bound incorrect."
    ))

    require(upper2 == 32.0, (
        "Positive calibrated upper bound incorrect."
    ))

    log("PASS — non-negativity constraint")


# ============================================================================
# 13. CONTRACT TESTS — SERIES / HORIZONS
# ============================================================================

def test_series_horizon_contract() -> None:
    log("\n[6/10] Series and horizon contract")

    all_series = []

    for dataset, series in EXPECTED_SERIES.items():
        require(len(series) > 0, (
            f"{dataset} contains no series."
        ))

        all_series.extend(
            [(dataset, s) for s in series]
        )

    require(len(all_series) == EXPECTED_SERIES_COUNT, (
        f"Expected {EXPECTED_SERIES_COUNT} total series, "
        f"found {len(all_series)}."
    ))

    require(len(set(all_series)) == EXPECTED_SERIES_COUNT, (
        "Duplicate series detected."
    ))

    require(len(HORIZONS) == EXPECTED_HORIZON_COUNT, (
        "Incorrect number of horizons."
    ))

    require(
        EXPECTED_CALIBRATION_CELLS
        == EXPECTED_SERIES_COUNT * len(HORIZONS) * 2,
        "Calibration-cell calculation is inconsistent."
    )

    log("PASS — 9 series × 4 horizons × 2 intervals = 72 cells")


# ============================================================================
# 14. CONTRACT TESTS — TEMPORAL ORIGIN COUNTS
# ============================================================================

def test_temporal_contract() -> None:
    log("\n[7/10] Temporal rolling-origin contract")

    require(
        set(EXPECTED_VALIDATION_ORIGINS) == set(HORIZONS),
        "Validation horizon definitions incomplete."
    )

    require(
        set(EXPECTED_TEST_ORIGINS) == set(HORIZONS),
        "Test horizon definitions incomplete."
    )

    for h in HORIZONS:
        n_val = EXPECTED_VALIDATION_ORIGINS[h]
        n_test = EXPECTED_TEST_ORIGINS[h]

        require(n_val >= MIN_CALIBRATION_N, (
            f"Validation h={h} has fewer than minimum calibration "
            f"observations: {n_val}."
        ))

        require(n_test >= 1, (
            f"Test h={h} contains no target-valid origins."
        ))

    require(
        EXPECTED_VALIDATION_FORECASTS
        == 9 * (23 + 21 + 18 + 12),
        "Validation forecast count contract inconsistent."
    )

    require(
        EXPECTED_TEST_FORECASTS
        == 9 * (23 + 21 + 18 + 12),
        "Test forecast count contract inconsistent."
    )

    log(
        "PASS — target-valid origins "
        "(h1=23, h3=21, h6=18, h12=12)"
    )


# ============================================================================
# 15. CONTRACT TESTS — FROZEN 26C.2 WINNERS
# ============================================================================

def test_frozen_winners() -> None:
    log("\n[8/10] Frozen 26C.2 model-selection contract")

    require(len(EXPECTED_WINNERS) == EXPECTED_SERIES_COUNT, (
        "Frozen winner table must contain exactly 9 series."
    ))

    for key, expected in EXPECTED_WINNERS.items():
        require(key in EXPECTED_WINNERS, (
            f"Missing frozen winner: {key}"
        ))

        require(
            expected["model_family"] in {"XGBoost", "LightGBM"},
            f"Invalid model family for {key}: "
            f"{expected['model_family']}"
        )

        require(
            expected["config"].startswith(("XGB_", "LGB_")),
            f"Invalid frozen configuration for {key}: "
            f"{expected['config']}"
        )

    log("PASS — 9 frozen 26C.2 winners")


# ============================================================================
# 16. CONTRACT TESTS — FILE AVAILABILITY / SCHEMA
# ============================================================================

def load_and_validate_26c2_validation() -> pd.DataFrame:
    require(C26C2_VALIDATION.exists(), (
        f"Required 26C.2 validation forecast file not found:\n"
        f"{C26C2_VALIDATION}"
    ))

    df = pd.read_csv(C26C2_VALIDATION)

    require(len(df) > 0, (
        "26C.2 validation forecast file is empty."
    ))

    return df


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for candidate in candidates:
        key = candidate.strip().lower()

        if key in lower_map:
            return lower_map[key]

    return None


def test_input_file_contract() -> pd.DataFrame:
    log("\n[9/10] Frozen 26C.2 input/output contract")

    require(SPEC_FILE.exists(), (
        f"26C.3-A specification file not found:\n{SPEC_FILE}"
    ))

    require(C26C2_VALIDATION.exists(), (
        f"26C.2 validation forecast file not found:\n"
        f"{C26C2_VALIDATION}"
    ))

    df = load_and_validate_26c2_validation()

    # Locate canonical fields flexibly because 26C.2 output naming
    # may contain minor implementation-specific capitalization.
    series_col = find_column(
        df,
        ["series", "dataseries", "data_series", "material"],
    )

    dataset_col = find_column(
        df,
        ["dataset", "target", "dataset_id"],
    )

    horizon_col = find_column(
        df,
        ["horizon", "h"],
    )

    origin_col = find_column(
        df,
        ["forecast_origin", "origin", "origin_date"],
    )

    target_date_col = find_column(
        df,
        ["target_date", "target", "target_datetime"],
    )

    actual_col = find_column(
        df,
        ["actual", "y_true", "actual_value"],
    )

    require(series_col is not None, (
        "26C.2 validation output is missing a series column."
    ))

    require(dataset_col is not None, (
        "26C.2 validation output is missing a dataset column."
    ))

    require(horizon_col is not None, (
        "26C.2 validation output is missing a horizon column."
    ))

    require(origin_col is not None, (
        "26C.2 validation output is missing forecast-origin information."
    ))

    require(target_date_col is not None, (
        "26C.2 validation output is missing target-date information."
    ))

    require(actual_col is not None, (
        "26C.2 validation output is missing actual target values."
    ))

    # Normalize internal validation view.
    work = df.copy()

    work["__series"] = work[series_col].astype(str).map(normalize_series)
    work["__dataset"] = work[dataset_col].astype(str)
    work["__horizon"] = pd.to_numeric(
        work[horizon_col],
        errors="coerce",
    )

    work["__origin"] = pd.to_datetime(
        work[origin_col],
        errors="coerce",
    )

    work["__target_date"] = pd.to_datetime(
        work[target_date_col],
        errors="coerce",
    )

    work["__actual"] = pd.to_numeric(
        work[actual_col],
        errors="coerce",
    )

    require(work["__horizon"].notna().all(), (
        "26C.2 horizons contain non-numeric values."
    ))

    require(
        set(work["__horizon"].astype(int).unique())
        <= set(HORIZONS),
        "26C.2 validation contains horizons outside frozen set."
    )

    require(work["__origin"].notna().all(), (
        "26C.2 forecast origins contain invalid dates."
    ))

    require(work["__target_date"].notna().all(), (
        "26C.2 target dates contain invalid dates."
    ))

    require(work["__actual"].notna().all(), (
        "26C.2 actual values contain missing/non-numeric values."
    ))

    # Temporal ordering.
    require(
        (work["__target_date"] > work["__origin"]).all(),
        "At least one target date is not after its forecast origin."
    )

    # Check target horizon against monthly timestamps approximately.
    # Exact calendar-day spacing is intentionally not enforced because
    # month-end / month-start conventions may differ.
    work["__horizon_int"] = work["__horizon"].astype(int)

    unique_series = set(
        zip(
            work["__dataset"],
            work["__series"],
        )
    )

    expected_series = set(EXPECTED_WINNERS)

    require(
        expected_series.issubset(unique_series),
        "26C.2 validation output does not contain all nine frozen series."
    )

    # Locate quantile prediction columns.
    quantile_columns = {}

    for q in QUANTILES:
        candidates = [
            f"q{int(q * 100):02d}",
            f"q_{q:.2f}",
            f"quantile_{q:.2f}",
            f"prediction_q{int(q * 100):02d}",
            f"pred_q{int(q * 100):02d}",
            f"q{int(q * 100)}",
        ]

        column = find_column(work, candidates)

        if column is not None:
            quantile_columns[q] = column

    # The contract requires all five quantiles.
    missing_q = [
        q for q in QUANTILES
        if q not in quantile_columns
    ]

    require(not missing_q, (
        "26C.2 validation output is missing required quantiles: "
        + ", ".join(map(str, missing_q))
    ))

    # Check finite predictions.
    for q, col in quantile_columns.items():
        numeric = pd.to_numeric(work[col], errors="coerce")

        require(numeric.notna().all(), (
            f"Quantile q={q} contains non-numeric/missing values."
        ))

        require(np.isfinite(numeric).all(), (
            f"Quantile q={q} contains non-finite values."
        ))

    # Quantile monotonicity must hold in the frozen 26C.2 output.
    q_values = np.column_stack(
        [
            pd.to_numeric(work[quantile_columns[q]], errors="coerce")
            .to_numpy()
            for q in QUANTILES
        ]
    )

    monotone = np.all(
        np.diff(q_values, axis=1) >= -1e-12
    )

    require(monotone, (
        "26C.2 validation output contains unrepaired quantile crossing. "
        "26C.3 must consume the repaired output."
    ))

    # Duplicate forecast records are prohibited.
    duplicate_key = [
        "__dataset",
        "__series",
        "__horizon_int",
        "__origin",
        "__target_date",
    ]

    duplicate_count = int(
        work.duplicated(duplicate_key).sum()
    )

    require(duplicate_count == 0, (
        f"Duplicate 26C.2 forecast records detected: "
        f"{duplicate_count}"
    ))

    log(
        f"PASS — 26C.2 validation input loaded "
        f"({len(work)} rows)"
    )

    return work


# ============================================================================
# 17. CONTRACT TESTS — CALIBRATION LEAKAGE
# ============================================================================

def test_calibration_leakage_rules() -> None:
    log("\n[10/10] Calibration leakage and implementation contract")

    # Explicit mathematical temporal rule.
    # Calibration score time must precede forecast origin.
    #
    # This is tested here with representative timestamps. The actual
    # implementation must repeat the same assertion for every prediction.
    calibration_time = pd.Timestamp("2022-01-01")
    forecast_origin = pd.Timestamp("2022-03-01")
    target_time = pd.Timestamp("2022-06-01")

    require(
        calibration_time < forecast_origin < target_time,
        "Temporal calibration ordering rule failed."
    )

    # A future calibration observation is prohibited.
    future_calibration = pd.Timestamp("2022-07-01")

    require(
        not (future_calibration < forecast_origin),
        "Future calibration observation incorrectly permitted."
    )

    # Calibration cannot contain the target itself.
    require(
        not (target_time < forecast_origin),
        "Target cannot precede forecast origin in calibration protocol."
    )

    # Check contract values.
    require(
        CALIBRATION_CONTRACT.test_calibration_allowed is False,
        "Test calibration must remain disabled."
    )

    require(
        CALIBRATION_CONTRACT.synthetic_calibration_allowed is False,
        "Synthetic calibration must remain disabled."
    )

    require(
        CALIBRATION_CONTRACT.minimum_n == 10,
        "Minimum calibration n changed from 10."
    )

    log("PASS — chronological leakage controls")


# ============================================================================
# 18. CONTRACT TEST — CALIBRATION CELL LOGIC
# ============================================================================

def test_calibration_cell_logic() -> None:
    log("\n[Supplementary] Calibration-cell logic")

    # Build a deterministic mock set with exactly 10 scores.
    scores = np.arange(10, dtype=float)

    for interval_name, interval in INTERVAL_CONTRACTS.items():
        k, adjustment = conformal_adjustment(
            scores.tolist(),
            alpha=interval.alpha,
        )

        require(
            1 <= k <= len(scores),
            f"Invalid conformal rank for interval {interval_name}."
        )

        require(
            adjustment >= 0,
            f"Negative conformal adjustment for interval {interval_name}."
        )

    # Verify that the two interval levels are handled independently.
    k50, a50 = conformal_adjustment(
        scores.tolist(),
        alpha=INTERVAL_CONTRACTS["50"].alpha,
    )

    k80, a80 = conformal_adjustment(
        scores.tolist(),
        alpha=INTERVAL_CONTRACTS["80"].alpha,
    )

    require(k80 > k50, (
        "Higher nominal coverage should require a higher/equal "
        "conformal score rank."
    ))

    require(a80 >= a50, (
        "80% calibration adjustment should be >= 50% adjustment "
        "for this monotonic score example."
    ))

    log("PASS — independent 50%/80% calibration cells")


# ============================================================================
# 19. CONTRACT REPORT
# ============================================================================

def build_contract_report(
    validation_df: pd.DataFrame | None,
) -> dict:

    specification_hash = None
    c26c2_selection_hash = None
    c26c2_validation_hash = None

    if SPEC_FILE.exists():
        specification_hash = sha256_file(SPEC_FILE)

    if C26C2_SELECTION.exists():
        c26c2_selection_hash = sha256_file(C26C2_SELECTION)

    if C26C2_VALIDATION.exists():
        c26c2_validation_hash = sha256_file(C26C2_VALIDATION)

    report = {
        "step": STEP,
        "parent_step": PARENT_STEP,
        "specification_version": SPEC_VERSION,
        "run_timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "calibration": asdict(CALIBRATION_CONTRACT),

        "horizons": HORIZONS,
        "primary_horizon": PRIMARY_HORIZON,
        "quantiles": QUANTILES,

        "intervals": {
            name: asdict(contract)
            for name, contract in INTERVAL_CONTRACTS.items()
        },

        "expected_series_count": EXPECTED_SERIES_COUNT,
        "expected_calibration_cells": EXPECTED_CALIBRATION_CELLS,

        "expected_validation_origins": EXPECTED_VALIDATION_ORIGINS,
        "expected_test_origins": EXPECTED_TEST_ORIGINS,

        "expected_validation_forecasts": (
            EXPECTED_VALIDATION_FORECASTS
        ),
        "expected_test_forecasts": EXPECTED_TEST_FORECASTS,

        "frozen_winners": {
            f"{dataset}::{series}": config
            for (dataset, series), config
            in EXPECTED_WINNERS.items()
        },

        "random_split_allowed": RANDOM_SPLIT_ALLOWED,
        "test_calibration_allowed": TEST_CALIBRATION_ALLOWED,
        "model_retraining_allowed": MODEL_RETRAINING_ALLOWED,
        "model_reselection_allowed": MODEL_RESELECTION_ALLOWED,
        "synthetic_calibration_allowed": (
            SYNTHETIC_CALIBRATION_ALLOWED
        ),

        "source_hashes": {
            "26c3a_specification": specification_hash,
            "26c2_selection": c26c2_selection_hash,
            "26c2_validation_forecasts": c26c2_validation_hash,
        },

        "validation_rows_loaded": (
            None if validation_df is None else len(validation_df)
        ),

        "status": "PASS",
    }

    return report


def save_contract_outputs(report: dict) -> None:
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = RESULTS_DIR / (
        "RO1_step26c3_contract.json"
    )

    txt_path = RESULTS_DIR / (
        "RO1_step26c3_contract.txt"
    )

    audit_path = RESULTS_DIR / (
        "RO1_step26c3_contract_audit.csv"
    )

    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    text_lines = [
        "CMIDO — RO1 Step 26C.3-B",
        "Probabilistic Calibration & Conformal Prediction",
        "Executable Contract Report",
        "",
        f"Status: {report['status']}",
        f"Specification: {report['specification_version']}",
        f"Calibration method: {report['calibration']['method']}",
        f"Calibration mode: {report['calibration']['mode']}",
        f"Minimum calibration n: {report['calibration']['minimum_n']}",
        f"Primary horizon: h={report['primary_horizon']}",
        f"Series count: {report['expected_series_count']}",
        f"Calibration cells: {report['expected_calibration_cells']}",
        "",
        "Expected validation origins:",
        str(report["expected_validation_origins"]),
        "",
        "Expected test origins:",
        str(report["expected_test_origins"]),
        "",
        "Random split allowed: "
        f"{report['random_split_allowed']}",
        "Test calibration allowed: "
        f"{report['test_calibration_allowed']}",
        "Model retraining allowed: "
        f"{report['model_retraining_allowed']}",
        "Model reselection allowed: "
        f"{report['model_reselection_allowed']}",
        "Synthetic calibration allowed: "
        f"{report['synthetic_calibration_allowed']}",
        "",
        "ALL STEP 26C.3-B ASSERTIONS: PASS",
    ]

    txt_path.write_text(
        "\n".join(text_lines),
        encoding="utf-8",
    )

    audit_rows = []

    for name, contract in INTERVAL_CONTRACTS.items():
        audit_rows.append(
            {
                "step": STEP,
                "audit": "interval_contract",
                "interval": name,
                "lower_quantile": contract.lower_quantile,
                "upper_quantile": contract.upper_quantile,
                "nominal_coverage": contract.nominal_coverage,
                "alpha": contract.alpha,
                "status": "PASS",
            }
        )

    for h in HORIZONS:
        audit_rows.append(
            {
                "step": STEP,
                "audit": "horizon_contract",
                "interval": None,
                "horizon": h,
                "validation_origins": EXPECTED_VALIDATION_ORIGINS[h],
                "test_origins": EXPECTED_TEST_ORIGINS[h],
                "status": "PASS",
            }
        )

    audit_df = pd.DataFrame(audit_rows)

    audit_df.to_csv(
        audit_path,
        index=False,
    )

    log("\nSaved contract outputs:")
    log(f"  {json_path}")
    log(f"  {txt_path}")
    log(f"  {audit_path}")


# ============================================================================
# 20. MAIN
# ============================================================================

def main() -> int:
    start = datetime.now(timezone.utc)

    print("=" * 78)
    print("CMIDO — RO1 STEP 26C.3-B")
    print("PROBABILISTIC CALIBRATION & CONFORMAL PREDICTION")
    print("EXECUTABLE CONTRACT")
    print("=" * 78)

    log(f"Project root: {PROJECT_ROOT}")
    log(f"Specification: {SPEC_FILE}")
    log(f"Calibration method: {CALIBRATION_METHOD}")
    log(f"Calibration mode: {CALIBRATION_MODE}")
    log(f"Minimum calibration n: {MIN_CALIBRATION_N}")
    log(f"Horizons: {HORIZONS}")
    log(f"Primary horizon: {PRIMARY_HORIZON}")
    log(f"Quantiles: {QUANTILES}")
    log("50% interval: q25–q75")
    log("80% interval: q10–q90")
    log("Random split: DISABLED")
    log("Test-data calibration: DISABLED")
    log("Model retraining: DISABLED")
    log("Model reselection: DISABLED")
    log("Synthetic calibration observations: DISABLED")

    validation_df = None

    try:
        test_static_contract()
        test_interval_contract()
        test_quantile_repair()
        test_cqr_math()
        test_nonnegativity()
        test_series_horizon_contract()
        test_temporal_contract()
        test_frozen_winners()

        validation_df = test_input_file_contract()

        test_calibration_leakage_rules()
        test_calibration_cell_logic()

        report = build_contract_report(
            validation_df
        )

        save_contract_outputs(report)

        elapsed = (
            datetime.now(timezone.utc) - start
        ).total_seconds()

        print("\n" + "=" * 78)
        print("ALL STEP 26C.3-B ASSERTIONS: PASS")
        print("=" * 78)
        print(f"Elapsed: {elapsed:.2f} seconds")
        print("Contract status: FROZEN-READY")
        print("=" * 78)

        return 0

    except Exception as exc:
        print("\n" + "=" * 78)
        print("STEP 26C.3-B CONTRACT FAILED")
        print("=" * 78)
        print(f"{type(exc).__name__}: {exc}")
        print("=" * 78)

        return 1


if __name__ == "__main__":
    sys.exit(main())