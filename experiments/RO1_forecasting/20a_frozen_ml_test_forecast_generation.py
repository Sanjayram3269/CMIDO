"""
CMIDO — RO1 Step 26C.3-D-A
Frozen Probabilistic ML Test Forecast Generation

Purpose
-------
Generate the untouched test-period probabilistic forecasts using ONLY the
nine model-family/configuration winners frozen in Step 26C.2.

This script is intentionally separate from model selection and calibration.

Rules
-----
1. No model/configuration selection.
2. No conformal calibration.
3. No test-based hyperparameter tuning.
4. No random train/test split.
5. Training at each test origin uses only observations whose target is
   observable by that origin.
6. The same 16 leakage-safe features and frozen model configurations used
   in 26C.2 are used here.
7. Quantile crossing is repaired using the exact frozen monotone
   rearrangement rule from 26C.2.
8. Test forecasts are saved for later frozen CQR application.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, List
import hashlib
import json
import time
import warnings

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor


# ============================================================================
# PATHS
# ============================================================================

ROOT = Path(r"D:\CMIDO")

PRICE_PATH = ROOT / "data" / "interim" / "RO1_price_long.csv"
DEMAND_PATH = ROOT / "data" / "interim" / "RO1_demand_long.csv"

OUT_DIR = ROOT / "results" / "forecasting" / "probabilistic_ml"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_DIR = OUT_DIR / "checkpoints_26c3d_test"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = OUT_DIR / "RO1_step26c2_test_forecasts.csv"
SUMMARY_PATH = OUT_DIR / "RO1_step26c2_test_forecast_generation_summary.txt"
AUDIT_PATH = OUT_DIR / "RO1_step26c2_test_forecast_generation_audit.csv"

SEED = 2601

HORIZONS = (1, 3, 6, 12)
QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90)

EXPECTED_ORIGINS = {
    1: 23,
    3: 21,
    6: 18,
    12: 12,
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
    "lag_1", "lag_2", "lag_3", "lag_6", "lag_12",
    "rolling_mean_3", "rolling_mean_6", "rolling_mean_12",
    "rolling_std_3", "rolling_std_6", "rolling_std_12",
    "change_1", "change_3", "change_12",
    "month", "quarter",
]

# Exact frozen winners from 26C.2.
FROZEN_WINNERS = {
    ("RO1_PRICE", "Cement"): ("LightGBM", "LGB_C1"),
    ("RO1_PRICE", "Concreting Sand"): ("XGBoost", "XGB_C2"),
    ("RO1_PRICE", "Granite"): ("XGBoost", "XGB_C3"),
    ("RO1_PRICE", "Ready Mixed Concrete"): ("XGBoost", "XGB_C2"),
    ("RO1_PRICE", "Steel Reinforcement Bars"): ("XGBoost", "XGB_C2"),
    ("RO1_DEMAND", "Cement"): ("XGBoost", "XGB_C3"),
    ("RO1_DEMAND", "Granite"): ("LightGBM", "LGB_C3"),
    ("RO1_DEMAND", "Ready Mixed Concrete"): ("XGBoost", "XGB_C2"),
    ("RO1_DEMAND", "Steel Reinforcement Bars"): ("XGBoost", "XGB_C3"),
}

XGB_CONFIGS = {
    "XGB_C1": dict(
        n_estimators=300, max_depth=3, learning_rate=0.03,
        min_child_weight=3, subsample=0.90, colsample_bytree=0.90,
        reg_alpha=0.0, reg_lambda=1.0,
    ),
    "XGB_C2": dict(
        n_estimators=500, max_depth=2, learning_rate=0.03,
        min_child_weight=2, subsample=0.90, colsample_bytree=1.00,
        reg_alpha=0.0, reg_lambda=1.0,
    ),
    "XGB_C3": dict(
        n_estimators=300, max_depth=4, learning_rate=0.02,
        min_child_weight=5, subsample=1.00, colsample_bytree=0.80,
        reg_alpha=0.0, reg_lambda=1.0,
    ),
}

LGB_CONFIGS = {
    "LGB_C1": dict(
        n_estimators=300, num_leaves=15, max_depth=-1,
        learning_rate=0.03, min_child_samples=15,
        subsample=0.90, subsample_freq=1, colsample_bytree=0.90,
        reg_alpha=0.0, reg_lambda=1.0,
    ),
    "LGB_C2": dict(
        n_estimators=500, num_leaves=7, max_depth=-1,
        learning_rate=0.03, min_child_samples=10,
        subsample=0.90, subsample_freq=1, colsample_bytree=1.00,
        reg_alpha=0.0, reg_lambda=1.0,
    ),
    "LGB_C3": dict(
        n_estimators=300, num_leaves=31, max_depth=-1,
        learning_rate=0.02, min_child_samples=20,
        subsample=1.00, subsample_freq=0, colsample_bytree=0.80,
        reg_alpha=0.0, reg_lambda=1.0,
    ),
}

MODEL_CONFIGS = {}
MODEL_CONFIGS.update({("XGBoost", k): v for k, v in XGB_CONFIGS.items()})
MODEL_CONFIGS.update({("LightGBM", k): v for k, v in LGB_CONFIGS.items()})


# ============================================================================
# UTILITIES
# ============================================================================

def find_date_column(df: pd.DataFrame) -> str:
    for c in ["Date", "date", "Month", "month", "period", "Period"]:
        if c in df.columns:
            return c
    raise AssertionError(f"No date column found: {list(df.columns)}")


def find_value_column(df: pd.DataFrame, dataset: str) -> str:
    for c in VALUE_CANDIDATES[dataset]:
        if c in df.columns:
            return c
    raise AssertionError(f"No value column found for {dataset}")


def load_long(path: Path, dataset: str) -> pd.DataFrame:
    assert path.exists(), f"Missing input: {path}"
    df = pd.read_csv(path)

    assert "DataSeries" in df.columns, f"{dataset}: missing DataSeries"

    date_col = find_date_column(df)
    value_col = find_value_column(df, dataset)

    out = df[["DataSeries", date_col, value_col]].copy()
    out.columns = ["series_source", "date", "value"]

    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["value"] = pd.to_numeric(out["value"], errors="coerce")

    assert out["date"].notna().all()
    assert out["value"].notna().all()
    assert np.isfinite(out["value"]).all()
    assert (out["value"] > 0).all()

    mapping = {
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

    raw = sorted(out["series_source"].unique())
    missing = [x for x in raw if x not in mapping[dataset]]
    assert not missing, f"{dataset}: unmapped source series: {missing}"

    out["series"] = out["series_source"].map(mapping[dataset])
    out = out.sort_values(["series", "date"]).reset_index(drop=True)

    assert sorted(out["series"].unique()) == sorted(EXPECTED_SERIES[dataset])

    return out


def build_feature_frame(series_df: pd.DataFrame) -> pd.DataFrame:
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

    f["change_1"] = s.shift(1).pct_change(1)
    f["change_3"] = s.shift(1).pct_change(3)
    f["change_12"] = s.shift(1).pct_change(12)

    return f.replace([np.inf, -np.inf], np.nan)


def make_origin_dataset(series_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    base = series_df.sort_values("date").set_index("date")["value"].astype(float)
    f = build_feature_frame(series_df)

    target = base.shift(-horizon).rename("target")
    target_date = pd.Series(base.index, index=base.index).shift(-horizon)
    target_date.name = "target_date"

    out = f.copy()
    out["target"] = target
    out["target_date"] = target_date
    out["origin"] = out.index

    out["month"] = pd.to_datetime(out["target_date"]).dt.month
    out["quarter"] = pd.to_datetime(out["target_date"]).dt.quarter

    return out.dropna(subset=FEATURES + ["target", "target_date"]).reset_index(drop=True)


def make_model(family: str, config_id: str, quantile: float):
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


def fit_bundle(X: pd.DataFrame, y: pd.Series, family: str, config_id: str):
    models = {}
    for q in QUANTILES:
        model = make_model(family, config_id, q)
        model.fit(X, y)
        models[q] = model
    return models


def predict_bundle(models, X: pd.DataFrame) -> np.ndarray:
    return np.column_stack(
        [np.asarray(models[q].predict(X), dtype=float) for q in QUANTILES]
    )


def monotone_rearrangement(pred: np.ndarray) -> np.ndarray:
    return np.sort(pred, axis=1)


def target_valid_test_origins(origin_table: pd.DataFrame, dataset: str, horizon: int):
    spec = SPLITS[dataset]
    mask = (
        (origin_table["origin"] >= spec["test_start"])
        & (origin_table["origin"] <= spec["test_end"])
        & (origin_table["target_date"] >= spec["test_start"])
        & (origin_table["target_date"] <= spec["test_end"])
    )
    out = origin_table.loc[mask].sort_values("origin").copy()

    assert len(out) == EXPECTED_ORIGINS[horizon], (
        f"{dataset}/h{horizon}: expected {EXPECTED_ORIGINS[horizon]} "
        f"test origins, found {len(out)}"
    )
    return out


def train_predict_at_origin(
    origin_table: pd.DataFrame,
    origin: pd.Timestamp,
    family: str,
    config_id: str,
):
    # EXACT temporal eligibility used in 26C.2:
    # target must already be observable and training origin must precede t.
    train = origin_table.loc[
        (origin_table["target_date"] <= origin)
        & (origin_table["origin"] < origin)
    ].copy()

    current = origin_table.loc[
        origin_table["origin"] == origin
    ].copy()

    assert len(current) == 1
    assert len(train) >= 60, (
        f"Insufficient training rows at {origin}: {len(train)}"
    )

    X_train = train[FEATURES]
    y_train = train["target"].astype(float)
    X_pred = current[FEATURES]

    models = fit_bundle(
        X_train,
        y_train,
        family,
        config_id,
    )

    pred_raw = predict_bundle(models, X_pred)[0]
    actual = float(current["target"].iloc[0])

    return pred_raw, actual, len(train)


def checkpoint_path(dataset, series, family, config_id, horizon):
    safe = (
        f"{dataset}__{series}__{family}__{config_id}__h{horizon}"
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )
    return CHECKPOINT_DIR / f"{safe}.csv"


def generate_job(dataset, series, df, family, config_id, horizon):
    sdf = df.loc[
        df["series"] == series,
        ["series", "date", "value"],
    ].copy()

    origin_table = make_origin_dataset(
        sdf,
        horizon,
    )

    test_origins = target_valid_test_origins(
        origin_table,
        dataset,
        horizon,
    )

    rows = []

    for _, r in test_origins.iterrows():

        origin = pd.Timestamp(r["origin"])

        pred_raw, actual, ntrain = train_predict_at_origin(
            origin_table,
            origin,
            family,
            config_id,
        )

        pred_repaired = monotone_rearrangement(
            pred_raw.reshape(1, -1)
        )[0]

        row = {
            "dataset": dataset,
            "series": series,
            "model_family": family,
            "config_id": config_id,
            "horizon": horizon,
            "split": "test",
            "origin": origin,
            "target_date": pd.Timestamp(r["target_date"]),
            "actual": actual,
            "train_rows": ntrain,
        }

        for i, q in enumerate(QUANTILES):
            qname = f"q{int(q * 100):02d}"
            row[f"{qname}_raw"] = float(pred_raw[i])
            row[qname] = float(pred_repaired[i])

        rows.append(row)

    out = pd.DataFrame(rows)

    assert len(out) == EXPECTED_ORIGINS[horizon]
    assert out["split"].eq("test").all()

    return out


def load_checkpoint(path: Path):
    if not path.exists():
        return None

    try:
        df = pd.read_csv(path)
        if df.empty:
            return None

        required = [
            "dataset", "series", "model_family", "config_id",
            "horizon", "split", "origin", "target_date", "actual",
            "q10_raw", "q25_raw", "q50_raw", "q75_raw", "q90_raw",
            "q10", "q25", "q50", "q75", "q90",
        ]

        if any(c not in df.columns for c in required):
            return None

        assert df["split"].eq("test").all()
        assert len(df) == EXPECTED_ORIGINS[int(df["horizon"].iloc[0])]

        return df

    except Exception:
        return None


def save_checkpoint(df: pd.DataFrame, path: Path):
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def audit_results(df: pd.DataFrame):
    audits = []

    def add(name, detail):
        audits.append({
            "audit": name,
            "status": "PASS",
            "detail": detail,
        })

    expected_rows = 9 * sum(EXPECTED_ORIGINS.values())

    assert len(df) == expected_rows
    add("forecast_row_count", f"{expected_rows} test forecasts generated.")

    assert set(
        zip(df["dataset"], df["series"])
    ) == set(FROZEN_WINNERS)
    add("nine_frozen_series", "Exactly nine frozen series present.")

    assert set(df["horizon"].astype(int)) == set(HORIZONS)
    add("horizon_coverage", "h=1,3,6,12 present.")

    assert df["split"].eq("test").all()
    add("split_label", "All rows are test forecasts.")

    assert (
        pd.to_datetime(df["target_date"])
        > pd.to_datetime(df["origin"])
    ).all()
    add("chronology", "Every target occurs after its forecast origin.")

    for dataset, spec in SPLITS.items():

        subset = df[df["dataset"] == dataset]

        assert not subset["origin"].between(
            spec["dev_end"], spec["val_end"]
        ).any()

        assert subset["origin"].between(
            spec["test_start"], spec["test_end"]
        ).all()

        assert subset["target_date"].between(
            spec["test_start"], spec["test_end"]
        ).all()

    add(
        "test_window",
        "All origins and targets lie within the frozen test windows.",
    )

    key = [
        "dataset", "series", "horizon",
        "origin", "target_date",
    ]

    assert not df.duplicated(key).any()
    add("duplicate_check", "No duplicate test forecast keys.")

    qraw = df[
        ["q10_raw", "q25_raw", "q50_raw", "q75_raw", "q90_raw"]
    ].to_numpy(float)

    qrep = df[
        ["q10", "q25", "q50", "q75", "q90"]
    ].to_numpy(float)

    raw_cross = np.any(np.diff(qraw, axis=1) < 0, axis=1)

    assert np.all(np.diff(qrep, axis=1) >= -1e-12)
    add(
        "quantile_repair",
        f"All repaired quantiles monotone; raw crossing rows={int(raw_cross.sum())}.",
    )

    # Verify frozen winner mapping.
    for key_pair, expected in FROZEN_WINNERS.items():
        sub = df[
            (df["dataset"] == key_pair[0])
            & (df["series"] == key_pair[1])
        ]
        assert sub["model_family"].eq(expected[0]).all()
        assert sub["config_id"].eq(expected[1]).all()

    add(
        "frozen_model_identity",
        "Every test forecast uses the exact 26C.2 frozen winner.",
    )

    # Explicitly verify that no validation rows leaked into this file.
    assert not df["target_date"].isin(
        pd.to_datetime(df["target_date"]).loc[
            pd.to_datetime(df["target_date"]).between(
                pd.Timestamp("2022-06-01"),
                pd.Timestamp("2024-06-30"),
            )
        ]
    ).any()
    add(
        "validation_target_isolation",
        "No validation-period target is present in test output.",
    )

    return pd.DataFrame(audits)


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ============================================================================
# MAIN
# ============================================================================

def main():

    t0 = time.time()

    warnings.filterwarnings(
        "ignore",
        message=".*does not have valid feature names.*",
    )

    print("=" * 78)
    print("CMIDO — STEP 26C.3-D-A")
    print("FROZEN PROBABILISTIC ML TEST FORECAST GENERATION")
    print("=" * 78)
    print("Model selection: DISABLED")
    print("Hyperparameter tuning: DISABLED")
    print("Conformal calibration: DISABLED")
    print("Test-based calibration: DISABLED")
    print("Random split: DISABLED")
    print("Frozen quantile repair: monotone rearrangement")
    print()

    price = load_long(PRICE_PATH, "RO1_PRICE")
    demand = load_long(DEMAND_PATH, "RO1_DEMAND")

    print(
        f"RO1_PRICE: {len(price)} rows, "
        f"{price['series'].nunique()} series, "
        f"{price['date'].min():%Y-%m} to {price['date'].max():%Y-%m}"
    )

    print(
        f"RO1_DEMAND: {len(demand)} rows, "
        f"{demand['series'].nunique()} series, "
        f"{demand['date'].min():%Y-%m} to {demand['date'].max():%Y-%m}"
    )

    datasets = {
        "RO1_PRICE": price,
        "RO1_DEMAND": demand,
    }

    all_rows = []

    total_jobs = 9 * 4
    job = 0

    for dataset, series in [
        (d, s)
        for d in ["RO1_PRICE", "RO1_DEMAND"]
        for s in EXPECTED_SERIES[d]
    ]:

        family, config_id = FROZEN_WINNERS[
            (dataset, series)
        ]

        for horizon in HORIZONS:

            job += 1

            path = checkpoint_path(
                dataset,
                series,
                family,
                config_id,
                horizon,
            )

            cached = load_checkpoint(path)

            if cached is not None:
                print(
                    f"[{job:02d}/{total_jobs}] "
                    f"{dataset} | {series} | "
                    f"{family}/{config_id} | h={horizon} | "
                    f"CHECKPOINT LOADED"
                )
                all_rows.append(cached)
                continue

            print(
                f"[{job:02d}/{total_jobs}] "
                f"{dataset} | {series} | "
                f"{family}/{config_id} | h={horizon}"
            )

            result = generate_job(
                dataset,
                series,
                datasets[dataset],
                family,
                config_id,
                horizon,
            )

            save_checkpoint(result, path)

            print(
                f"    CHECKPOINT SAVED → {path.name}"
            )

            all_rows.append(result)

    forecasts = pd.concat(
        all_rows,
        ignore_index=True,
    )

    forecasts["origin"] = pd.to_datetime(
        forecasts["origin"]
    )
    forecasts["target_date"] = pd.to_datetime(
        forecasts["target_date"]
    )

    forecasts = forecasts.sort_values(
        ["dataset", "series", "horizon", "origin"]
    ).reset_index(drop=True)

    print()
    print("-" * 78)
    print("AUDITS")
    print("-" * 78)

    audit_df = audit_results(
        forecasts
    )

    audit_df.to_csv(
        AUDIT_PATH,
        index=False,
    )

    # Save the test forecast file consumed by Step 26C.3-D.
    forecasts.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    elapsed = time.time() - t0

    summary = {
        "step": "26C.3-D-A",
        "status": "PASSED",
        "purpose": "Generate frozen 26C.2 winner forecasts on untouched test data",
        "model_selection": False,
        "hyperparameter_tuning": False,
        "conformal_calibration": False,
        "test_based_calibration": False,
        "random_split": False,
        "quantile_repair": "monotone_rearrangement_sort",
        "horizons": list(HORIZONS),
        "expected_origins_by_horizon": EXPECTED_ORIGINS,
        "expected_forecast_rows": 9 * sum(EXPECTED_ORIGINS.values()),
        "actual_forecast_rows": int(len(forecasts)),
        "frozen_winners": {
            f"{k[0]}::{k[1]}": {
                "model_family": v[0],
                "config_id": v[1],
            }
            for k, v in FROZEN_WINNERS.items()
        },
        "output": str(OUTPUT_PATH),
        "audit": str(AUDIT_PATH),
        "elapsed_seconds": round(elapsed, 2),
    }

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 78)
    print("ALL STEP 26C.3-D-A ASSERTIONS: PASS")
    print("=" * 78)
    print(f"Test forecast rows: {len(forecasts)}")
    print(f"Expected rows     : {9 * sum(EXPECTED_ORIGINS.values())}")
    print("Frozen winners    : 9")
    print("Model reselection : NO")
    print("Test calibration  : NO")
    print("Conformal         : NO")
    print()
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Saved: {AUDIT_PATH}")
    print(f"Saved: {SUMMARY_PATH}")
    print()
    print(f"Elapsed: {elapsed / 60:.2f} minutes")
    print("=" * 78)


if __name__ == "__main__":
    main()
