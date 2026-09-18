"""
CMIDO — Step 26C.2
Probabilistic ML Forecasting Development

Purpose
-------
Develop and validate the probabilistic ML forecasting layer specified in
Step 26C.1 using expanding rolling-origin validation.

Models
------
Primary   : XGBoost quantile regression
Secondary : LightGBM quantile regression

Targets
-------
5 price series + 4 demand series
Horizons : 1, 3, 6, 12 months
Primary  : h = 3 months
Quantiles: 0.10, 0.25, 0.50, 0.75, 0.90

Important methodological rules
------------------------------
1. No random train/test split.
2. Validation is the only basis for ML model/configuration selection.
3. The test period is NOT touched by this script.
4. Feature construction is leakage-safe:
   - lags end at t-1
   - rolling statistics use shift(1)
   - change features use only observations through t-1
5. Target is kept on the original level scale. No unregistered log transform.
6. Cross-material and external features remain disabled.
7. Candidate model zoo is deliberately controlled.
8. Quantile crossing is measured before repair. A deterministic monotone
   rearrangement (sorting predicted quantiles) is applied identically to all
   validation forecasts and will be frozen for later test evaluation.
9. Model selection is performed separately for each series and primary
   horizon (h=3), using mean pinball loss across the five quantiles, with
   Winkler-80, MAE, and 80% coverage error as tie-breakers.
10. After selection at h=3, the winning model family/configuration for each
    series is evaluated at h=1, 3, 6, 12 using the same frozen configuration.
11. This script does not perform conformal calibration. That belongs to 26C.3.

Outputs
-------
results/forecasting/probabilistic_ml/
    RO1_step26c2_validation_forecasts.csv
    RO1_step26c2_validation_metrics.csv
    RO1_step26c2_model_selection.csv
    RO1_step26c2_primary_h3_selection.csv
    RO1_step26c2_quantile_crossing_audit.csv
    RO1_step26c2_run_summary.txt
"""

from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

from xgboost import XGBRegressor
from lightgbm import LGBMRegressor


# ---------------------------------------------------------------------------
# Paths and frozen contract
# ---------------------------------------------------------------------------

ROOT = Path(r"D:\CMIDO")

PRICE_PATH = ROOT / "data" / "interim" / "RO1_price_long.csv"
DEMAND_PATH = ROOT / "data" / "interim" / "RO1_demand_long.csv"

OUT_DIR = ROOT / "results" / "forecasting" / "probabilistic_ml"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 2601

HORIZONS = (1, 3, 6, 12)
PRIMARY_HORIZON = 3
QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90)

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

EXPECTED_UNITS = {
    "RO1_PRICE": "$ per tonne",
    "RO1_DEMAND": "thousand tonnes",
}

VALUE_CANDIDATES = {
    "RO1_PRICE": [
        "price_dollars_per_tonne",
        "value",
        "price",
    ],
    "RO1_DEMAND": [
        "demand_thousand_tonnes",
        "value",
        "demand",
    ],
}

# Exact chronological contracts established earlier.
SPLITS = {
    "RO1_PRICE": {
        "dev_end": pd.Timestamp("2022-06-01"),
        "val_start": pd.Timestamp("2022-07-01"),
        "val_end": pd.Timestamp("2024-06-01"),
        "test_start": pd.Timestamp("2024-07-01"),
        "test_end": pd.Timestamp("2026-06-01"),
    },
    "RO1_DEMAND": {
        "dev_end": pd.Timestamp("2022-05-01"),
        "val_start": pd.Timestamp("2022-06-01"),
        "val_end": pd.Timestamp("2024-05-01"),
        "test_start": pd.Timestamp("2024-06-01"),
        "test_end": pd.Timestamp("2026-05-01"),
    },
}

FEATURES = [
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_6",
    "lag_12",
    "rolling_mean_3",
    "rolling_mean_6",
    "rolling_mean_12",
    "rolling_std_3",
    "rolling_std_6",
    "rolling_std_12",
    "change_1",
    "change_3",
    "change_12",
    "month",
    "quarter",
]

assert len(FEATURES) == 16

# Controlled candidate set. These are deliberately modest for the monthly
# sample size and CPU-only environment.
XGB_CONFIGS = {
    "XGB_C1": dict(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.03,
        min_child_weight=3,
        subsample=0.90,
        colsample_bytree=0.90,
        reg_alpha=0.0,
        reg_lambda=1.0,
    ),
    "XGB_C2": dict(
        n_estimators=500,
        max_depth=2,
        learning_rate=0.03,
        min_child_weight=2,
        subsample=0.90,
        colsample_bytree=1.00,
        reg_alpha=0.0,
        reg_lambda=1.0,
    ),
    "XGB_C3": dict(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.02,
        min_child_weight=5,
        subsample=1.00,
        colsample_bytree=0.80,
        reg_alpha=0.0,
        reg_lambda=1.0,
    ),
}

LGB_CONFIGS = {
    "LGB_C1": dict(
        n_estimators=300,
        num_leaves=15,
        max_depth=-1,
        learning_rate=0.03,
        min_child_samples=15,
        subsample=0.90,
        subsample_freq=1,
        colsample_bytree=0.90,
        reg_alpha=0.0,
        reg_lambda=1.0,
    ),
    "LGB_C2": dict(
        n_estimators=500,
        num_leaves=7,
        max_depth=-1,
        learning_rate=0.03,
        min_child_samples=10,
        subsample=0.90,
        subsample_freq=1,
        colsample_bytree=1.00,
        reg_alpha=0.0,
        reg_lambda=1.0,
    ),
    "LGB_C3": dict(
        n_estimators=300,
        num_leaves=31,
        max_depth=-1,
        learning_rate=0.02,
        min_child_samples=20,
        subsample=1.00,
        subsample_freq=0,
        colsample_bytree=0.80,
        reg_alpha=0.0,
        reg_lambda=1.0,
    ),
}

MODEL_CONFIGS = {}
MODEL_CONFIGS.update({("XGBoost", k): v for k, v in XGB_CONFIGS.items()})
MODEL_CONFIGS.update({("LightGBM", k): v for k, v in LGB_CONFIGS.items()})


# ---------------------------------------------------------------------------
# Data loading and validation
# ---------------------------------------------------------------------------

def _find_date_column(df: pd.DataFrame) -> str:
    for c in ["Date", "date", "Month", "month", "period", "Period"]:
        if c in df.columns:
            return c
    raise AssertionError(
        f"Could not identify date column. Available columns: {list(df.columns)}"
    )


def _find_value_column(df: pd.DataFrame, dataset: str) -> str:
    for c in VALUE_CANDIDATES[dataset]:
        if c in df.columns:
            return c
    raise AssertionError(
        f"{dataset}: could not identify value column. Available columns: {list(df.columns)}"
    )


def load_long(path: Path, dataset: str) -> pd.DataFrame:
    assert path.exists(), f"Missing input file: {path}"

    df = pd.read_csv(path)
    required = ["DataSeries"]
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"{dataset}: missing columns {missing}"

    date_col = _find_date_column(df)
    value_col = _find_value_column(df, dataset)

    out = df[["DataSeries", date_col, value_col]].copy()
    out.columns = ["series", "date", "value"]

    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["value"] = pd.to_numeric(out["value"], errors="coerce")

    assert out["date"].notna().all(), f"{dataset}: invalid dates detected"
    assert out["value"].notna().all(), f"{dataset}: missing/non-numeric values detected"
    assert np.isfinite(out["value"]).all(), f"{dataset}: non-finite values detected"
    assert (out["value"] > 0).all(), f"{dataset}: non-positive values detected"

    # Canonical material-name normalization.
    # The raw/interim price dataset preserves the official source names,
    # while the CMIDO research pipeline uses shorter canonical names.
    # Do NOT modify the source CSV; normalize only inside the model pipeline.
    SERIES_NORMALIZATION = {
        "RO1_PRICE": {
            "Cement In Bulk (Ordinary Portland Cement)": "Cement",
            "Concreting Sand": "Concreting Sand",
            "Granite (20mm Aggregate)": "Granite",
            "Ready Mixed Concrete": "Ready Mixed Concrete",
            "Steel Reinforcement Bars (16-32mm High Tensile)": "Steel Reinforcement Bars",
        },
        "RO1_DEMAND": {
            "Cement": "Cement",
            "Granite": "Granite",
            "Ready Mixed Concrete": "Ready Mixed Concrete",
            "Ready-Mixed Concrete": "Ready Mixed Concrete",
            "Steel Reinforcement Bars": "Steel Reinforcement Bars",
        },
    }

    raw_series = sorted(out["series"].unique().tolist())
    mapping = SERIES_NORMALIZATION[dataset]

    missing_mappings = [s for s in raw_series if s not in mapping]
    assert not missing_mappings, (
        f"{dataset}: unmapped source series detected: {missing_mappings}"
    )

    out["series_source"] = out["series"]
    out["series"] = out["series"].map(mapping)

    assert out["series"].notna().all(), (
        f"{dataset}: canonical series normalization produced missing values"
    )

    out = out.sort_values(["series", "date"]).reset_index(drop=True)

    actual_series = sorted(out["series"].unique().tolist())
    expected_series = sorted(EXPECTED_SERIES[dataset])
    assert actual_series == expected_series, (
        f"{dataset}: canonical series mismatch.\n"
        f"Expected: {expected_series}\nActual:   {actual_series}"
    )

    # Preserve a source-name audit so the normalization is fully traceable.
    source_pairs = out[["series_source", "series"]].drop_duplicates()
    assert len(source_pairs) == len(raw_series), (
        f"{dataset}: unexpected source-to-canonical mapping cardinality"
    )

    for s in expected_series:
        g = out.loc[out["series"] == s, "date"].sort_values()
        assert g.is_monotonic_increasing, f"{dataset}/{s}: date order failed"
        assert g.duplicated().sum() == 0, f"{dataset}/{s}: duplicate dates"

    return out


# ---------------------------------------------------------------------------
# Leakage-safe feature construction
# ---------------------------------------------------------------------------

def build_feature_frame(series_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build one row per forecast origin t.

    Every historical feature is explicitly shifted so the latest observation
    available to the model is y(t-1). Calendar features describe the target
    month t+h and are known in advance.
    """
    s = series_df.sort_values("date").set_index("date")["value"].astype(float)

    f = pd.DataFrame(index=s.index)

    f["lag_1"] = s.shift(1)
    f["lag_2"] = s.shift(2)
    f["lag_3"] = s.shift(3)
    f["lag_6"] = s.shift(6)
    f["lag_12"] = s.shift(12)

    shifted = s.shift(1)

    f["rolling_mean_3"] = shifted.rolling(3).mean()
    f["rolling_mean_6"] = shifted.rolling(6).mean()
    f["rolling_mean_12"] = shifted.rolling(12).mean()

    f["rolling_std_3"] = shifted.rolling(3).std(ddof=1)
    f["rolling_std_6"] = shifted.rolling(6).std(ddof=1)
    f["rolling_std_12"] = shifted.rolling(12).std(ddof=1)

    # Changes are based only on historical observations through t-1.
    f["change_1"] = s.shift(1).pct_change(1)
    f["change_3"] = s.shift(1).pct_change(3)
    f["change_12"] = s.shift(1).pct_change(12)

    f = f.replace([np.inf, -np.inf], np.nan)

    # Target calendar is known before forecasting and therefore does not leak.
    # These are populated later for each requested horizon.
    return f


def make_origin_dataset(
    series_df: pd.DataFrame,
    horizon: int,
) -> pd.DataFrame:
    """
    Return rows indexed by forecast origin:
        X(t) -> y(t+h)

    Training eligibility at origin t is enforced later as target_date <= t.
    """
    base = series_df.sort_values("date").set_index("date")["value"].astype(float)
    f = build_feature_frame(series_df)

    target = base.shift(-horizon).rename("target")
    target_date = pd.Series(
        base.index,
        index=base.index,
        name="target_date",
    ).shift(-horizon)

    out = f.copy()
    out["target"] = target
    out["target_date"] = target_date
    out["origin"] = out.index

    # Target calendar is known in advance.
    target_month = pd.to_datetime(out["target_date"]).dt.month
    target_quarter = pd.to_datetime(out["target_date"]).dt.quarter
    out["month"] = target_month
    out["quarter"] = target_quarter

    out = out.dropna(subset=FEATURES + ["target", "target_date"]).copy()
    out = out.reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# Model factories
# ---------------------------------------------------------------------------

def make_model(
    family: str,
    config_id: str,
    quantile: float,
):
    params = dict(MODEL_CONFIGS[(family, config_id)])

    if family == "XGBoost":
        params.update(
            objective="reg:quantileerror",
            quantile_alpha=float(quantile),
            tree_method="hist",
            random_state=SEED,
            n_jobs=-1,
            verbosity=0,
        )
        return XGBRegressor(**params)

    if family == "LightGBM":
        params.update(
            objective="quantile",
            alpha=float(quantile),
            random_state=SEED,
            n_jobs=-1,
            verbosity=-1,
        )
        return LGBMRegressor(**params)

    raise ValueError(f"Unknown model family: {family}")


def fit_quantile_bundle(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    family: str,
    config_id: str,
) -> Dict[float, object]:
    models = {}
    for q in QUANTILES:
        model = make_model(family, config_id, q)
        model.fit(X_train, y_train)
        models[q] = model
    return models


def predict_quantile_bundle(
    models: Dict[float, object],
    X_pred: pd.DataFrame,
) -> np.ndarray:
    pred = np.column_stack(
        [np.asarray(models[q].predict(X_pred), dtype=float) for q in QUANTILES]
    )
    return pred


# ---------------------------------------------------------------------------
# Quantile handling and metrics
# ---------------------------------------------------------------------------

def monotone_rearrangement(pred: np.ndarray) -> np.ndarray:
    """
    Non-parametric quantile rearrangement.

    This is decided as the frozen quantile-crossing repair rule for the
    probabilistic ML pipeline and is applied identically to validation/test.
    """
    return np.sort(pred, axis=1)


def crossing_mask(pred: np.ndarray) -> np.ndarray:
    return np.any(np.diff(pred, axis=1) < 0, axis=1)


def pinball_loss(y: np.ndarray, pred: np.ndarray, q: float) -> np.ndarray:
    e = y - pred
    return np.maximum(q * e, (q - 1.0) * e)


def winkler_interval(
    y: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    alpha: float = 0.20,
) -> np.ndarray:
    width = upper - lower
    score = width.copy()

    below = y < lower
    above = y > upper

    score[below] += (2.0 / alpha) * (lower[below] - y[below])
    score[above] += (2.0 / alpha) * (y[above] - upper[above])
    return score


def safe_mean(x: Iterable[float]) -> float:
    a = np.asarray(list(x), dtype=float)
    return float(np.nanmean(a)) if a.size else np.nan


def metric_row(
    y: np.ndarray,
    pred_raw: np.ndarray,
    pred_repaired: np.ndarray,
    dataset: str,
    series: str,
    family: str,
    config_id: str,
    horizon: int,
    split: str,
    origin_count: int,
) -> Dict:
    qs = list(QUANTILES)

    qraw = {q: pred_raw[:, i] for i, q in enumerate(qs)}
    q = {q: pred_repaired[:, i] for i, q in enumerate(qs)}

    median = q[0.50]
    lo50 = q[0.25]
    hi50 = q[0.75]
    lo80 = q[0.10]
    hi80 = q[0.90]

    abs_err = np.abs(y - median)
    sq_err = (y - median) ** 2

    pinballs = [
        pinball_loss(y, q[qv], qv).mean()
        for qv in qs
    ]

    cov50 = float(np.mean((y >= lo50) & (y <= hi50)))
    cov80 = float(np.mean((y >= lo80) & (y <= hi80)))

    width50 = float(np.mean(hi50 - lo50))
    width80 = float(np.mean(hi80 - lo80))

    crossing = crossing_mask(pred_raw)

    return {
        "dataset": dataset,
        "series": series,
        "model_family": family,
        "config_id": config_id,
        "horizon": horizon,
        "split": split,
        "n_origins": origin_count,
        "MAE": float(np.mean(abs_err)),
        "RMSE": float(np.sqrt(np.mean(sq_err))),
        "Pinball_q10": pinballs[0],
        "Pinball_q25": pinballs[1],
        "Pinball_q50": pinballs[2],
        "Pinball_q75": pinballs[3],
        "Pinball_q90": pinballs[4],
        "Mean_Pinball": float(np.mean(pinballs)),
        "Coverage_50": cov50,
        "Coverage_80": cov80,
        "Coverage_Error_50": abs(cov50 - 0.50),
        "Coverage_Error_80": abs(cov80 - 0.80),
        "Width_50": width50,
        "Width_80": width80,
        "Winkler_80": float(np.mean(winkler_interval(y, lo80, hi80, alpha=0.20))),
        "Raw_Crossing_Rate": float(np.mean(crossing)),
        "Raw_Crossing_Count": int(np.sum(crossing)),
    }


# ---------------------------------------------------------------------------
# Rolling-origin validation
# ---------------------------------------------------------------------------

def validation_origins(
    origin_dataset: pd.DataFrame,
    dataset: str,
    horizon: int,
) -> pd.DataFrame:
    spec = SPLITS[dataset]

    # The validation forecast origin must itself be in the validation period,
    # while target_date must also remain inside the validation period.
    m = (
        (origin_dataset["origin"] >= spec["val_start"])
        & (origin_dataset["origin"] <= spec["val_end"])
        & (origin_dataset["target_date"] >= spec["val_start"])
        & (origin_dataset["target_date"] <= spec["val_end"])
    )

    out = origin_dataset.loc[m].sort_values("origin").copy()
    return out


def train_predict_at_origin(
    origin_table: pd.DataFrame,
    origin: pd.Timestamp,
    family: str,
    config_id: str,
) -> Tuple[np.ndarray, float, int]:
    """
    Fit only on rows whose target has become observable by the forecast origin.

    For a forecast at origin t and horizon h:
        training rows satisfy target_date <= t.
    """
    train = origin_table.loc[
        (origin_table["target_date"] <= origin)
        & (origin_table["origin"] < origin)
    ].copy()

    current = origin_table.loc[origin_table["origin"] == origin].copy()

    assert len(current) == 1, f"Expected one forecast row at {origin}, got {len(current)}"

    min_train = 60
    assert len(train) >= min_train, (
        f"Insufficient training rows at {origin}: {len(train)} < {min_train}"
    )

    X_train = train[FEATURES]
    y_train = train["target"].astype(float)

    X_pred = current[FEATURES]

    models = fit_quantile_bundle(X_train, y_train, family, config_id)
    pred = predict_quantile_bundle(models, X_pred)

    actual = float(current["target"].iloc[0])
    return pred[0], actual, len(train)


def run_candidate_validation(
    dataset: str,
    df: pd.DataFrame,
    family: str,
    config_id: str,
    horizon: int,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Return:
      forecast rows and one aggregate metric row.
    """
    forecasts = []
    origins_used = []

    for series in EXPECTED_SERIES[dataset]:
        sdf = df.loc[df["series"] == series, ["series", "date", "value"]].copy()
        origin_table = make_origin_dataset(sdf, horizon)
        val = validation_origins(origin_table, dataset, horizon)

        assert len(val) > 0, f"No validation origins for {dataset}/{series}/h{horizon}"

        for _, r in val.iterrows():
            origin = pd.Timestamp(r["origin"])
            pred_raw, actual, ntrain = train_predict_at_origin(
                origin_table, origin, family, config_id
            )
            pred_rep = monotone_rearrangement(pred_raw.reshape(1, -1))[0]

            row = {
                "dataset": dataset,
                "series": series,
                "model_family": family,
                "config_id": config_id,
                "horizon": horizon,
                "split": "validation",
                "origin": origin,
                "target_date": pd.Timestamp(r["target_date"]),
                "actual": actual,
                "train_rows": ntrain,
            }
            for i, q in enumerate(QUANTILES):
                row[f"q{int(q*100):02d}_raw"] = float(pred_raw[i])
                row[f"q{int(q*100):02d}"] = float(pred_rep[i])
            forecasts.append(row)
            origins_used.append((origin, actual, pred_raw, pred_rep))

        arr_actual = np.asarray([x[1] for x in origins_used], dtype=float)
        arr_raw = np.vstack([x[2] for x in origins_used])
        arr_rep = np.vstack([x[3] for x in origins_used])

        metrics = metric_row(
            arr_actual,
            arr_raw,
            arr_rep,
            dataset,
            series,
            family,
            config_id,
            horizon,
            "validation",
            len(origins_used),
        )
        return forecasts, [metrics]

    raise RuntimeError("Unreachable")


# ---------------------------------------------------------------------------
# More efficient series-level runner
# ---------------------------------------------------------------------------

def evaluate_candidate(
    dataset: str,
    series: str,
    df: pd.DataFrame,
    family: str,
    config_id: str,
    horizon: int,
) -> Tuple[List[Dict], Dict]:
    sdf = df.loc[df["series"] == series, ["series", "date", "value"]].copy()
    origin_table = make_origin_dataset(sdf, horizon)
    val = validation_origins(origin_table, dataset, horizon)

    # Target-based validation membership is horizon-specific. The validation
    # period contains 24 calendar origins, but the final h-1 origins cannot
    # be used because their targets would fall beyond the validation window.
    expected_origins_by_horizon = {
        1: 23,
        3: 21,
        6: 18,
        12: 12,
    }
    expected_origins = expected_origins_by_horizon[horizon]

    assert len(val) == expected_origins, (
        f"{dataset}/{series}/h{horizon}: expected {expected_origins} "
        f"horizon-valid validation origins, found {len(val)}"
    )

    forecasts = []
    actuals = []
    raw_preds = []
    repaired_preds = []

    for _, r in val.iterrows():
        origin = pd.Timestamp(r["origin"])

        pred_raw, actual, ntrain = train_predict_at_origin(
            origin_table, origin, family, config_id
        )
        pred_rep = monotone_rearrangement(pred_raw.reshape(1, -1))[0]

        row = {
            "dataset": dataset,
            "series": series,
            "model_family": family,
            "config_id": config_id,
            "horizon": horizon,
            "split": "validation",
            "origin": origin,
            "target_date": pd.Timestamp(r["target_date"]),
            "actual": actual,
            "train_rows": ntrain,
        }

        for i, q in enumerate(QUANTILES):
            row[f"q{int(q*100):02d}_raw"] = float(pred_raw[i])
            row[f"q{int(q*100):02d}"] = float(pred_rep[i])

        forecasts.append(row)
        actuals.append(actual)
        raw_preds.append(pred_raw)
        repaired_preds.append(pred_rep)

    actuals = np.asarray(actuals, dtype=float)
    raw_preds = np.asarray(raw_preds, dtype=float)
    repaired_preds = np.asarray(repaired_preds, dtype=float)

    metrics = metric_row(
        actuals,
        raw_preds,
        repaired_preds,
        dataset,
        series,
        family,
        config_id,
        horizon,
        "validation",
        len(actuals),
    )
    return forecasts, metrics


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def select_primary_model(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Primary selection at h=3, independently for each dataset/series.

    Ordering:
      1. Mean pinball loss ASC
      2. Winkler-80 ASC
      3. MAE ASC
      4. Coverage error at 80% ASC
    """
    primary = metrics_df.loc[
        metrics_df["horizon"] == PRIMARY_HORIZON
    ].copy()

    assert len(primary) == 9 * 6, (
        f"Expected 54 h3 candidate rows, found {len(primary)}"
    )
    assert primary["n_origins"].eq(21).all(), (
        "Primary h=3 selection candidates must all use 21 "
        "target-valid validation origins."
    )

    primary = primary.sort_values(
        [
            "dataset",
            "series",
            "Mean_Pinball",
            "Winkler_80",
            "MAE",
            "Coverage_Error_80",
            "model_family",
            "config_id",
        ],
        ascending=[
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
        ],
    )

    selected = (
        primary.groupby(["dataset", "series"], as_index=False)
        .first()
        .reset_index(drop=True)
    )

    assert len(selected) == 9, (
        f"Expected one selected ML configuration per series (9), found {len(selected)}"
    )

    return selected


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------

CHECKPOINT_DIR = (
    ROOT / "results" / "forecasting" / "probabilistic_ml" / "checkpoints_26c2"
)
PHASE_A_DIR = CHECKPOINT_DIR / "phase_a_candidates"
PHASE_B_DIR = CHECKPOINT_DIR / "phase_b_frozen"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
PHASE_A_DIR.mkdir(parents=True, exist_ok=True)
PHASE_B_DIR.mkdir(parents=True, exist_ok=True)


def atomic_to_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a CSV atomically so an interruption cannot leave a partial file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def candidate_key(dataset: str, series: str, family: str, config_id: str) -> str:
    safe = (
        f"{dataset}__{series}__{family}__{config_id}"
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )
    return safe


def phase_a_paths(
    dataset: str,
    series: str,
    family: str,
    config_id: str,
) -> Tuple[Path, Path]:
    key = candidate_key(dataset, series, family, config_id)
    return (
        PHASE_A_DIR / f"{key}__forecasts.csv",
        PHASE_A_DIR / f"{key}__metrics.csv",
    )


def phase_b_paths(
    dataset: str,
    series: str,
    family: str,
    config_id: str,
    horizon: int,
) -> Tuple[Path, Path]:
    key = candidate_key(dataset, series, family, config_id)
    return (
        PHASE_B_DIR / f"{key}__h{horizon}__forecasts.csv",
        PHASE_B_DIR / f"{key}__h{horizon}__metrics.csv",
    )


def load_checkpoint_pair(
    forecast_path: Path,
    metric_path: Path,
) -> Tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """
    A checkpoint is considered complete only when BOTH forecast and metric
    files exist and contain data. This prevents an interrupted write from
    being mistaken for a completed job.
    """
    if not (forecast_path.exists() and metric_path.exists()):
        return None, None

    try:
        fc = pd.read_csv(forecast_path)
        mt = pd.read_csv(metric_path)
        if fc.empty or mt.empty:
            return None, None
        return fc, mt
    except Exception:
        return None, None


def save_checkpoint_pair(
    forecasts: List[Dict],
    metric: Dict,
    forecast_path: Path,
    metric_path: Path,
) -> None:
    fc_df = pd.DataFrame(forecasts)
    mt_df = pd.DataFrame([metric])

    # Forecasts first; both writes are atomic.
    atomic_to_csv(fc_df, forecast_path)
    atomic_to_csv(mt_df, metric_path)


def phase_a_checkpoint_status(
    candidates: List[Tuple[str, str]],
) -> Tuple[List[Dict], List[Dict], set]:
    """Load all complete Phase-A candidate checkpoints."""
    loaded_forecasts: List[Dict] = []
    loaded_metrics: List[Dict] = []
    completed = set()

    for dataset, series in [
        (d, s)
        for d in ["RO1_PRICE", "RO1_DEMAND"]
        for s in EXPECTED_SERIES[d]
    ]:
        for family, config_id in candidates:
            fp, mp = phase_a_paths(dataset, series, family, config_id)
            fc, mt = load_checkpoint_pair(fp, mp)

            if fc is None or mt is None:
                continue

            # Validate the checkpoint before trusting it.
            assert len(mt) == 1, f"Invalid Phase-A metric checkpoint: {mp}"
            assert int(mt["horizon"].iloc[0]) == PRIMARY_HORIZON
            assert int(mt["n_origins"].iloc[0]) == 21
            assert len(fc) == 21, f"Invalid Phase-A forecast checkpoint: {fp}"
            assert fc["split"].eq("validation").all()
            assert fc["horizon"].eq(PRIMARY_HORIZON).all()

            key = (dataset, series, family, config_id)
            completed.add(key)
            loaded_forecasts.extend(fc.to_dict("records"))
            loaded_metrics.extend(mt.to_dict("records"))

    return loaded_forecasts, loaded_metrics, completed


def phase_b_checkpoint_status(
    selected_keys: Dict[Tuple[str, str], Tuple[str, str]],
) -> Tuple[List[Dict], List[Dict], set]:
    """Load complete Phase-B frozen winner checkpoints."""
    loaded_forecasts: List[Dict] = []
    loaded_metrics: List[Dict] = []
    completed = set()

    for dataset, series in [
        (d, s)
        for d in ["RO1_PRICE", "RO1_DEMAND"]
        for s in EXPECTED_SERIES[d]
    ]:
        family, config_id = selected_keys[(dataset, series)]

        for horizon in HORIZONS:
            fp, mp = phase_b_paths(
                dataset, series, family, config_id, horizon
            )
            fc, mt = load_checkpoint_pair(fp, mp)

            if fc is None or mt is None:
                continue

            expected_n = {1: 23, 3: 21, 6: 18, 12: 12}[horizon]
            assert len(mt) == 1, f"Invalid Phase-B metric checkpoint: {mp}"
            assert int(mt["horizon"].iloc[0]) == horizon
            assert int(mt["n_origins"].iloc[0]) == expected_n
            assert len(fc) == expected_n, (
                f"Invalid Phase-B forecast checkpoint: {fp}"
            )
            assert fc["split"].eq("validation").all()
            assert fc["horizon"].eq(horizon).all()

            key = (dataset, series, family, config_id, horizon)
            completed.add(key)
            loaded_forecasts.extend(fc.to_dict("records"))
            loaded_metrics.extend(mt.to_dict("records"))

    return loaded_forecasts, loaded_metrics, completed


def clean_incomplete_checkpoint_pairs(directory: Path) -> None:
    """
    Remove only orphaned checkpoint files where the paired file is absent.
    Complete pairs are never deleted.
    """
    for path in directory.glob("*.csv"):
        stem = path.name
        if "__forecasts.csv" in stem:
            pair = directory / stem.replace("__forecasts.csv", "__metrics.csv")
        elif "__metrics.csv" in stem:
            pair = directory / stem.replace("__metrics.csv", "__forecasts.csv")
        else:
            continue

        if not pair.exists():
            try:
                path.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    t0 = time.time()
    warnings.filterwarnings(
        "ignore",
        message=".*does not have valid feature names.*",
    )

    print("=" * 78)
    print("CMIDO — STEP 26C.2: PROBABILISTIC ML FORECASTING DEVELOPMENT")
    print("=" * 78)
    print("Test data are not used by this script.")
    print(f"Primary horizon: h={PRIMARY_HORIZON}")
    print(f"Quantiles: {QUANTILES}")
    print(f"Features: {len(FEATURES)}")
    print("Cross-material features: DISABLED")
    print("External features: DISABLED")
    print("Conformal calibration: DISABLED")
    print("Target transformation: LEVEL SCALE")
    print("Checkpointing: ENABLED")
    print(f"Checkpoint directory: {CHECKPOINT_DIR}")
    print()

    # Clean only incomplete/orphaned checkpoint pairs. Complete work is kept.
    clean_incomplete_checkpoint_pairs(PHASE_A_DIR)
    clean_incomplete_checkpoint_pairs(PHASE_B_DIR)

    price = load_long(PRICE_PATH, "RO1_PRICE")
    demand = load_long(DEMAND_PATH, "RO1_DEMAND")

    print(
        f"RO1_PRICE: {len(price)} rows, "
        f"{price['series'].nunique()} canonical series, "
        f"{price['date'].min():%Y-%m} to {price['date'].max():%Y-%m}"
    )
    print("RO1_PRICE source→canonical series normalization: PASS")
    print(
        f"RO1_DEMAND: {len(demand)} rows, "
        f"{demand['series'].nunique()} canonical series, "
        f"{demand['date'].min():%Y-%m} to {demand['date'].max():%Y-%m}"
    )
    print("RO1_DEMAND source→canonical series normalization: PASS")

    datasets = {
        "RO1_PRICE": price,
        "RO1_DEMAND": demand,
    }

    candidates = [
        ("XGBoost", "XGB_C1"),
        ("XGBoost", "XGB_C2"),
        ("XGBoost", "XGB_C3"),
        ("LightGBM", "LGB_C1"),
        ("LightGBM", "LGB_C2"),
        ("LightGBM", "LGB_C3"),
    ]

    # ----------------------------------------------------------------------
    # Phase A — candidate validation with resumable checkpoints
    # ----------------------------------------------------------------------

    print()
    print("-" * 78)
    print("PHASE A — PRIMARY-HORIZON CANDIDATE VALIDATION (h=3)")
    print("-" * 78)

    all_forecasts, all_metrics, completed_a = phase_a_checkpoint_status(
        candidates
    )

    total_candidate_jobs = 9 * len(candidates)
    already_done = len(completed_a)

    if already_done:
        print(
            f"RESUME: {already_done}/{total_candidate_jobs} complete "
            f"candidate jobs loaded from checkpoints."
        )
    else:
        print("No completed Phase-A checkpoints found. Starting from candidate 1.")

    job = 0

    for dataset, df in datasets.items():
        for series in EXPECTED_SERIES[dataset]:
            for family, config_id in candidates:
                job += 1
                key = (dataset, series, family, config_id)

                if key in completed_a:
                    print(
                        f"[{job:02d}/{total_candidate_jobs}] "
                        f"{dataset} | {series} | {family} | {config_id} "
                        f"| CHECKPOINT LOADED"
                    )
                    continue

                print(
                    f"[{job:02d}/{total_candidate_jobs}] "
                    f"{dataset} | {series} | {family} | {config_id}"
                )

                fc, mt = evaluate_candidate(
                    dataset=dataset,
                    series=series,
                    df=df,
                    family=family,
                    config_id=config_id,
                    horizon=PRIMARY_HORIZON,
                )

                assert len(fc) == 21
                assert mt["n_origins"] == 21

                fp, mp = phase_a_paths(
                    dataset, series, family, config_id
                )
                save_checkpoint_pair(fc, mt, fp, mp)

                all_forecasts.extend(fc)
                all_metrics.append(mt)
                completed_a.add(key)

                print(f"    CHECKPOINT SAVED → {fp.name}")

    metrics_df = pd.DataFrame(all_metrics)

    assert len(metrics_df) == 54, (
        f"Expected 54 candidate h3 metric rows, found {len(metrics_df)}"
    )
    assert metrics_df["n_origins"].eq(21).all(), (
        "Primary h=3 candidate validation must contain exactly 21 "
        "target-valid origins per series/configuration."
    )

    # Validate that all candidate forecast sets are present and complete.
    forecast_df_a = pd.DataFrame(all_forecasts)
    assert len(forecast_df_a) == 54 * 21, (
        f"Expected {54*21} Phase-A forecasts, found {len(forecast_df_a)}"
    )
    assert forecast_df_a["split"].eq("validation").all()
    assert forecast_df_a["horizon"].eq(PRIMARY_HORIZON).all()

    selected = select_primary_model(metrics_df)

    print()
    print("-" * 78)
    print("PRIMARY-HORIZON MODEL SELECTION")
    print("-" * 78)

    for _, r in selected.sort_values(["dataset", "series"]).iterrows():
        print(
            f"{r['dataset']:10s} | {r['series']:25s} | "
            f"{r['model_family']:9s} | {r['config_id']:7s} | "
            f"Pinball={r['Mean_Pinball']:.6f} | "
            f"Winkler80={r['Winkler_80']:.6f}"
        )

    selected_keys = {
        (r["dataset"], r["series"]): (r["model_family"], r["config_id"])
        for _, r in selected.iterrows()
    }

    # Save selection immediately so the selection itself survives interruption.
    selection_checkpoint = CHECKPOINT_DIR / "primary_h3_selection.csv"
    atomic_to_csv(
        selected.sort_values(["dataset", "series"]).reset_index(drop=True),
        selection_checkpoint,
    )
    print(f"Selection checkpoint saved → {selection_checkpoint}")

    # ----------------------------------------------------------------------
    # Phase B — frozen winning configuration across all horizons
    # ----------------------------------------------------------------------

    print()
    print("-" * 78)
    print("PHASE B — FROZEN WINNERS ACROSS h=1,3,6,12")
    print("-" * 78)

    phase_b_fc, phase_b_mt, completed_b = phase_b_checkpoint_status(
        selected_keys
    )

    # Reuse h=3 forecasts/metrics from Phase A for the selected winners.
    selected_h3_fc = [
        r for r in all_forecasts
        if selected_keys[(r["dataset"], r["series"])]
        == (r["model_family"], r["config_id"])
    ]
    selected_h3_mt = [
        r for r in all_metrics
        if selected_keys[(r["dataset"], r["series"])]
        == (r["model_family"], r["config_id"])
    ]

    # Phase B checkpoint set is authoritative for h=1/3/6/12 except that
    # h=3 can safely reuse the completed Phase-A winner.
    frozen_forecasts = []
    frozen_metrics = []

    for dataset, series in [
        (d, s)
        for d in ["RO1_PRICE", "RO1_DEMAND"]
        for s in EXPECTED_SERIES[d]
    ]:
        family, config_id = selected_keys[(dataset, series)]

        # Add h=3 from Phase A.
        h3_fc = [
            r for r in selected_h3_fc
            if r["dataset"] == dataset
            and r["series"] == series
            and int(r["horizon"]) == 3
        ]
        h3_mt = [
            r for r in selected_h3_mt
            if r["dataset"] == dataset
            and r["series"] == series
            and int(r["horizon"]) == 3
        ]

        assert len(h3_fc) == 21
        assert len(h3_mt) == 1
        frozen_forecasts.extend(h3_fc)
        frozen_metrics.extend(h3_mt)

        for horizon in HORIZONS:
            if horizon == PRIMARY_HORIZON:
                continue

            bkey = (dataset, series, family, config_id, horizon)

            if bkey in completed_b:
                print(
                    f"{dataset} | {series} | frozen "
                    f"{family}/{config_id} | h={horizon} | CHECKPOINT LOADED"
                )
                loaded_fc = [
                    r for r in phase_b_fc
                    if r["dataset"] == dataset
                    and r["series"] == series
                    and int(r["horizon"]) == horizon
                    and r["model_family"] == family
                    and r["config_id"] == config_id
                ]
                loaded_mt = [
                    r for r in phase_b_mt
                    if r["dataset"] == dataset
                    and r["series"] == series
                    and int(r["horizon"]) == horizon
                    and r["model_family"] == family
                    and r["config_id"] == config_id
                ]
                frozen_forecasts.extend(loaded_fc)
                frozen_metrics.extend(loaded_mt)
                continue

            print(
                f"{dataset} | {series} | frozen "
                f"{family}/{config_id} | h={horizon}"
            )

            fc, mt = evaluate_candidate(
                dataset=dataset,
                series=series,
                df=datasets[dataset],
                family=family,
                config_id=config_id,
                horizon=horizon,
            )

            expected_n = {1: 23, 6: 18, 12: 12}[horizon]
            assert len(fc) == expected_n
            assert mt["n_origins"] == expected_n

            fp, mp = phase_b_paths(
                dataset, series, family, config_id, horizon
            )
            save_checkpoint_pair(fc, mt, fp, mp)

            frozen_forecasts.extend(fc)
            frozen_metrics.append(mt)
            completed_b.add(bkey)

            print(f"    CHECKPOINT SAVED → {fp.name}")

    forecasts_df = pd.DataFrame(frozen_forecasts)
    frozen_metrics_df = pd.DataFrame(frozen_metrics)

    # ----------------------------------------------------------------------
    # Audits
    # ----------------------------------------------------------------------

    print()
    print("-" * 78)
    print("AUDITS")
    print("-" * 78)

    assert set(forecasts_df["dataset"]) == {"RO1_PRICE", "RO1_DEMAND"}
    assert set(forecasts_df["horizon"]) == set(HORIZONS)
    assert forecasts_df["split"].eq("validation").all()
    assert forecasts_df["origin"].notna().all()
    assert forecasts_df["target_date"].notna().all()

    expected_origins_by_horizon = {1: 23, 3: 21, 6: 18, 12: 12}
    expected_forecast_rows = 9 * sum(expected_origins_by_horizon.values())

    assert len(forecasts_df) == expected_forecast_rows, (
        f"Expected {expected_forecast_rows} frozen validation forecasts, "
        f"found {len(forecasts_df)}"
    )

    expected_metric_rows = 9 * 4
    assert len(frozen_metrics_df) == expected_metric_rows, (
        f"Expected {expected_metric_rows} frozen validation metric rows, "
        f"found {len(frozen_metrics_df)}"
    )

    coverage = (
        frozen_metrics_df.groupby(["dataset", "series"])["horizon"]
        .nunique()
    )
    assert coverage.eq(4).all()

    for _, r in frozen_metrics_df.iterrows():
        expected_n = expected_origins_by_horizon[int(r["horizon"])]
        assert int(r["n_origins"]) == expected_n

    # Primary selection must remain identical across all evaluated horizons.
    for _, r in selected.iterrows():
        subset = frozen_metrics_df.loc[
            (frozen_metrics_df["dataset"] == r["dataset"])
            & (frozen_metrics_df["series"] == r["series"])
        ]
        assert subset["model_family"].eq(r["model_family"]).all()
        assert subset["config_id"].eq(r["config_id"]).all()

    # Quantile order after repair must always be monotone.
    qcols = [f"q{int(q*100):02d}" for q in QUANTILES]
    repaired = forecasts_df[qcols].to_numpy(dtype=float)
    assert np.all(np.diff(repaired, axis=1) >= -1e-12), (
        "Quantile crossing remains after monotone rearrangement."
    )

    raw_qcols = [f"q{int(q*100):02d}_raw" for q in QUANTILES]
    raw = forecasts_df[raw_qcols].to_numpy(dtype=float)
    raw_cross = np.any(np.diff(raw, axis=1) < 0, axis=1)

    crossing_audit = (
        forecasts_df.assign(raw_crossing=raw_cross)
        .groupby(
            ["dataset", "series", "model_family", "config_id", "horizon"],
            as_index=False,
        )
        .agg(
            n_forecasts=("raw_crossing", "size"),
            raw_crossing_count=("raw_crossing", "sum"),
            raw_crossing_rate=("raw_crossing", "mean"),
        )
    )

    # Target membership audit.
    for dataset, df in datasets.items():
        spec = SPLITS[dataset]
        for series in EXPECTED_SERIES[dataset]:
            for h in HORIZONS:
                subset = forecasts_df.loc[
                    (forecasts_df["dataset"] == dataset)
                    & (forecasts_df["series"] == series)
                    & (forecasts_df["horizon"] == h)
                ]
                expected_n = expected_origins_by_horizon[h]
                assert len(subset) == expected_n
                assert subset["origin"].between(
                    spec["val_start"], spec["val_end"]
                ).all()
                assert subset["target_date"].between(
                    spec["val_start"], spec["val_end"]
                ).all()
                assert (subset["target_date"] > subset["origin"]).all()

    # No test-period origin or target can appear in validation output.
    for dataset, spec in SPLITS.items():
        assert not forecasts_df.loc[
            forecasts_df["dataset"] == dataset, "origin"
        ].between(spec["test_start"], spec["test_end"]).any()

        assert not forecasts_df.loc[
            forecasts_df["dataset"] == dataset, "target_date"
        ].between(spec["test_start"], spec["test_end"]).any()

    # ----------------------------------------------------------------------
    # Save final outputs
    # ----------------------------------------------------------------------

    forecasts_df = forecasts_df.sort_values(
        ["dataset", "series", "horizon", "origin"]
    ).reset_index(drop=True)

    frozen_metrics_df = frozen_metrics_df.sort_values(
        ["dataset", "series", "horizon"]
    ).reset_index(drop=True)

    selected_out = selected.sort_values(
        ["dataset", "series"]
    ).reset_index(drop=True)

    primary_out = selected_out[
        [
            "dataset",
            "series",
            "model_family",
            "config_id",
            "horizon",
            "Mean_Pinball",
            "Winkler_80",
            "MAE",
            "RMSE",
            "Coverage_50",
            "Coverage_80",
            "Coverage_Error_80",
            "Raw_Crossing_Rate",
        ]
    ].copy()

    forecasts_path = OUT_DIR / "RO1_step26c2_validation_forecasts.csv"
    metrics_path = OUT_DIR / "RO1_step26c2_validation_metrics.csv"
    selection_path = OUT_DIR / "RO1_step26c2_model_selection.csv"
    primary_path = OUT_DIR / "RO1_step26c2_primary_h3_selection.csv"
    crossing_path = OUT_DIR / "RO1_step26c2_quantile_crossing_audit.csv"
    summary_path = OUT_DIR / "RO1_step26c2_run_summary.txt"

    forecasts_df.to_csv(forecasts_path, index=False)
    frozen_metrics_df.to_csv(metrics_path, index=False)
    selected_out.to_csv(selection_path, index=False)
    primary_out.to_csv(primary_path, index=False)
    crossing_audit.to_csv(crossing_path, index=False)

    elapsed = time.time() - t0

    summary = {
        "step": "26C.2",
        "status": "PASSED",
        "purpose": "Probabilistic ML forecasting development and validation",
        "datasets": {
            "RO1_PRICE": {
                "rows": int(len(price)),
                "series": EXPECTED_SERIES["RO1_PRICE"],
                "unit": EXPECTED_UNITS["RO1_PRICE"],
                "source_series_normalization": (
                    "official source names mapped to CMIDO canonical material names"
                ),
            },
            "RO1_DEMAND": {
                "rows": int(len(demand)),
                "series": EXPECTED_SERIES["RO1_DEMAND"],
                "unit": EXPECTED_UNITS["RO1_DEMAND"],
                "source_series_normalization": (
                    "official source names mapped to CMIDO canonical material names"
                ),
            },
        },
        "horizons": list(HORIZONS),
        "primary_horizon": PRIMARY_HORIZON,
        "quantiles": list(QUANTILES),
        "features": FEATURES,
        "cross_material_features": False,
        "external_features": False,
        "target_transformation": "level",
        "conformal_calibration": False,
        "candidate_models": [
            {"family": f, "config": c}
            for f, c in candidates
        ],
        "selection": {
            "split": "validation_only",
            "horizon": PRIMARY_HORIZON,
            "primary_metric": "Mean_Pinball",
            "tie_breakers": [
                "Winkler_80",
                "MAE",
                "Coverage_Error_80",
            ],
        },
        "validation_origins_by_horizon": {
            "h1": 23,
            "h3": 21,
            "h6": 18,
            "h12": 12,
        },
        "quantile_crossing": {
            "raw_audit": True,
            "repair": "monotone_rearrangement_sort",
            "applied_to_validation": True,
            "test_rule": "freeze_identical_rule_for_26c4",
        },
        "checkpointing": {
            "enabled": True,
            "phase_a_per_candidate": True,
            "phase_b_per_series_horizon": True,
            "resume_supported": True,
        },
        "expected_phase_a_metric_rows": 54,
        "actual_phase_a_metric_rows": int(len(metrics_df)),
        "expected_phase_a_forecast_rows": 54 * 21,
        "actual_phase_a_forecast_rows": int(len(forecast_df_a)),
        "expected_validation_forecast_rows": expected_forecast_rows,
        "actual_validation_forecast_rows": int(len(forecasts_df)),
        "expected_frozen_metric_rows": expected_metric_rows,
        "actual_frozen_metric_rows": int(len(frozen_metrics_df)),
        "test_used": False,
        "conformal_used": False,
        "elapsed_seconds": round(elapsed, 2),
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, indent=2))

    print()
    print("=" * 78)
    print("ALL STEP 26C.2 ASSERTIONS: PASS")
    print("=" * 78)
    print(f"Phase-A candidate metrics : {len(metrics_df)}")
    print(f"Phase-A candidate forecasts: {len(forecast_df_a)}")
    print(f"Frozen validation forecasts: {len(forecasts_df)}")
    print(f"Frozen metrics             : {len(frozen_metrics_df)}")
    print(f"Selected series            : {len(selected_out)}")
    print(f"Raw crossing rows          : {int(raw_cross.sum())} / {len(raw_cross)}")
    print()
    print(f"Saved: {forecasts_path}")
    print(f"Saved: {metrics_path}")
    print(f"Saved: {selection_path}")
    print(f"Saved: {primary_path}")
    print(f"Saved: {crossing_path}")
    print(f"Saved: {summary_path}")
    print()
    print(f"Elapsed time: {elapsed/60:.2f} minutes")
    print("Step 26C.2 COMPLETE — ML validation layer established.")
    print("No test-period data were used.")
    print("No conformal calibration was performed.")
    print("Checkpointing remains available for safe future reruns/resumption.")
    print("=" * 78)


if __name__ == "__main__":
    main()
