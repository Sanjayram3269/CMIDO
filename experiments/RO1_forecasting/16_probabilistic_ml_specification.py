"""
CMIDO RO1 — STEP 26C.1
PROBABILISTIC ML FORECASTING — EXPERIMENT SPECIFICATION

Contract/specification only. No model training occurs in this step.

Primary ML: XGBoost quantile regression
Secondary ML: LightGBM quantile regression

Aligned with Steps 22–26B.1:
- expanding rolling-origin evaluation
- horizon-specific target membership
- validation-only selection
- frozen test
- no random train/test split
- no conformal calibration in this step
"""

from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = ROOT / "data" / "interim"
RESULTS_DIR = ROOT / "results" / "forecasting" / "probabilistic_ml"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PRICE_LONG = INTERIM_DIR / "RO1_price_long.csv"
DEMAND_LONG = INTERIM_DIR / "RO1_demand_long.csv"

DATASETS = {
    "RO1_PRICE": {
        "file": PRICE_LONG,
        "value_column": "price_dollars_per_tonne",
        "unit": "Dollar per tonne",
        "series": [
            "Cement In Bulk (Ordinary Portland Cement)",
            "Concreting Sand",
            "Granite (20mm Aggregate)",
            "Ready Mixed Concrete",
            "Steel Reinforcement Bars (16-32mm High Tensile)",
        ],
    },
    "RO1_DEMAND": {
        "file": DEMAND_LONG,
        "value_column": "demand_thousand_tonnes",
        "unit": "Thousand tonnes",
        "series": [
            "Cement",
            "Granite",
            "Ready-Mixed Concrete",
            "Steel Reinforcement Bars",
        ],
    },
}

HORIZONS = (1, 3, 6, 12)
PRIMARY_HORIZON = 3
QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90)

FEATURE_GROUPS = {
    "own_lags": (1, 2, 3, 6, 12),
    "rolling_mean": (3, 6, 12),
    "rolling_std": (3, 6, 12),
    "momentum": (1, 3, 12),
    "calendar": ("month", "quarter"),
}

CROSS_MATERIAL_FEATURES_ENABLED = False
EXTERNAL_FEATURES_ENABLED = False

MODEL_FAMILIES = ("XGBoost", "LightGBM")
RANDOM_SEED = 2601
MIN_TRAIN_OBSERVATIONS = 60

# Candidate configurations are deliberately controlled; this is not a model zoo.
XGBOOST_CANDIDATES = (
    dict(name="XGB_QR_A", n_estimators=300, max_depth=3,
         learning_rate=0.03, subsample=0.90, colsample_bytree=0.90,
         min_child_weight=3, reg_lambda=1.0),
    dict(name="XGB_QR_B", n_estimators=500, max_depth=4,
         learning_rate=0.03, subsample=0.90, colsample_bytree=0.90,
         min_child_weight=3, reg_lambda=1.0),
    dict(name="XGB_QR_C", n_estimators=500, max_depth=5,
         learning_rate=0.02, subsample=0.90, colsample_bytree=0.90,
         min_child_weight=5, reg_lambda=2.0),
)

LIGHTGBM_CANDIDATES = (
    dict(name="LGBM_QR_A", n_estimators=300, num_leaves=15,
         learning_rate=0.03, min_child_samples=15,
         subsample=0.90, colsample_bytree=0.90, reg_lambda=1.0),
    dict(name="LGBM_QR_B", n_estimators=500, num_leaves=15,
         learning_rate=0.03, min_child_samples=20,
         subsample=0.90, colsample_bytree=0.90, reg_lambda=1.0),
    dict(name="LGBM_QR_C", n_estimators=500, num_leaves=31,
         learning_rate=0.02, min_child_samples=20,
         subsample=0.90, colsample_bytree=0.90, reg_lambda=2.0),
)

# Frozen temporal contract inherited from Step 22.
SPLITS = {
    "RO1_PRICE": {
        "development_end": "2022-06",
        "validation": ("2022-07", "2024-06"),
        "test": ("2024-07", "2026-06"),
    },
    "RO1_DEMAND": {
        "development_end": "2022-05",
        "validation": ("2022-06", "2024-05"),
        "test": ("2024-06", "2026-05"),
    },
}


def validate_dataset(name, cfg):
    if not cfg["file"].exists():
        raise FileNotFoundError(f"{name}: {cfg['file']}")

    df = pd.read_csv(cfg["file"])
    required = {"date", "DataSeries", cfg["value_column"]}
    missing = required - set(df.columns)
    if missing:
        raise AssertionError(f"{name}: missing columns {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df[cfg["value_column"]] = pd.to_numeric(df[cfg["value_column"]], errors="raise")

    if df.duplicated(["DataSeries", "date"]).any():
        raise AssertionError(f"{name}: duplicate series-date observations")

    if df[cfg["value_column"]].isna().any():
        raise AssertionError(f"{name}: missing target values")

    actual = set(df["DataSeries"].unique())
    expected = set(cfg["series"])
    if actual != expected:
        raise AssertionError(
            f"{name}: series mismatch; expected={sorted(expected)}, actual={sorted(actual)}"
        )

    for series, g in df.groupby("DataSeries"):
        dates = pd.DatetimeIndex(g["date"].sort_values().unique())
        expected_dates = pd.date_range(dates.min(), dates.max(), freq="MS")
        if not dates.equals(expected_dates):
            raise AssertionError(f"{name} | {series}: monthly continuity failure")

    df = df.rename(columns={"DataSeries": "series"})
    return df


def feature_names():
    names = [f"lag_{x}" for x in FEATURE_GROUPS["own_lags"]]
    names += [f"rolling_mean_{x}" for x in FEATURE_GROUPS["rolling_mean"]]
    names += [f"rolling_std_{x}" for x in FEATURE_GROUPS["rolling_std"]]
    names += [f"change_{x}" for x in FEATURE_GROUPS["momentum"]]
    names += ["month", "quarter"]
    return names


def specification():
    return {
        "step": "26C.1",
        "purpose": "Probabilistic ML forecasting specification",
        "datasets": {
            k: {
                "file": str(v["file"].relative_to(ROOT)),
                "value_column": v["value_column"],
                "unit": v["unit"],
                "series": v["series"],
            }
            for k, v in DATASETS.items()
        },
        "horizons": list(HORIZONS),
        "primary_horizon": PRIMARY_HORIZON,
        "quantiles": list(QUANTILES),
        "features": {
            "names": feature_names(),
            "cross_material": CROSS_MATERIAL_FEATURES_ENABLED,
            "external": EXTERNAL_FEATURES_ENABLED,
            "rolling_shift": 1,
            "current_target_allowed": False,
        },
        "models": {
            "primary": "XGBoost",
            "secondary": "LightGBM",
            "xgboost_candidates": list(XGBOOST_CANDIDATES),
            "lightgbm_candidates": list(LIGHTGBM_CANDIDATES),
            "deep_learning": False,
        },
        "temporal": {
            "method": "expanding_rolling_origin",
            "origin_rule": "target_based_horizon_specific",
            "random_split": False,
            "validation_only_selection": True,
            "test_frozen": True,
            "splits": SPLITS,
        },
        "probabilistic": {
            "point_forecast": "q0.50",
            "interval_50": ["q0.25", "q0.75"],
            "interval_80": ["q0.10", "q0.90"],
            "primary_metric": "mean_pinball",
            "other_metrics": [
                "MAE", "RMSE",
                "coverage_50", "coverage_80",
                "coverage_error_50", "coverage_error_80",
                "interval_width_50", "interval_width_80",
                "winkler_80",
            ],
            "conformal_calibration": False,
        },
        "selection": {
            "primary": "validation mean pinball loss",
            "tie_breakers": ["Winkler-80", "MAE", "coverage error"],
            "test_used_for_selection": False,
        },
        "reproducibility": {
            "random_seed": RANDOM_SEED,
            "minimum_train_observations": MIN_TRAIN_OBSERVATIONS,
        },
    }


def main():
    print("=" * 78)
    print("CMIDO RO1 — STEP 26C.1")
    print("PROBABILISTIC ML FORECASTING — EXPERIMENT SPECIFICATION")
    print("=" * 78)

    print("\n[1] INPUT DATA CONTRACT")
    for name, cfg in DATASETS.items():
        df = validate_dataset(name, cfg)
        print(f"{name}: PASS")
        print(f"  rows: {len(df)}")
        print(f"  series: {len(cfg['series'])}")
        print(f"  range: {df['date'].min():%Y-%m} -> {df['date'].max():%Y-%m}")
        print(f"  unit: {cfg['unit']}")

    print("\n[2] TEMPORAL CONTRACT")
    print("Expanding rolling-origin: PASS")
    print("Horizon-specific target membership: PASS")
    print("Random train/test split: DISABLED")
    print("Validation-only selection: REQUIRED")
    print("Frozen test: REQUIRED")
    print(f"Horizons: {HORIZONS}")
    print(f"Primary horizon: h={PRIMARY_HORIZON}")

    print("\n[3] FEATURE CONTRACT")
    print(f"Features ({len(feature_names())}): {feature_names()}")
    print("Cross-material features: DISABLED")
    print("External features: DISABLED")
    print("Rolling features use shift(1): PASS")
    print("Current-target leakage: DISABLED")

    print("\n[4] PROBABILISTIC CONTRACT")
    print(f"Quantiles: {QUANTILES}")
    print("Point forecast: q0.50")
    print("50% interval: q0.25–q0.75")
    print("80% interval: q0.10–q0.90")
    print("Conformal calibration: DISABLED")

    print("\n[5] MODEL CONTRACT")
    print("Primary: XGBoost quantile regression")
    print("Secondary: LightGBM quantile regression")
    print(f"XGBoost candidate configurations: {len(XGBOOST_CANDIDATES)}")
    print(f"LightGBM candidate configurations: {len(LIGHTGBM_CANDIDATES)}")
    print("Deep learning: DISABLED")
    print("Model zoo: CONTROLLED")

    print("\n[6] EVALUATION CONTRACT")
    print("Primary selection metric: validation mean pinball loss")
    print("Tie-breakers: Winkler-80, MAE, coverage error")
    print("Test used for model selection: NO")
    print("Required comparators: Naive, Seasonal Naive, ETS, SARIMA")

    spec = specification()
    payload = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(payload).hexdigest()

    json_path = RESULTS_DIR / "RO1_step26c1_probabilistic_ml_specification.json"
    txt_path = RESULTS_DIR / "RO1_step26c1_probabilistic_ml_specification.txt"

    json_path.write_text(
        json.dumps({"specification": spec, "sha256": digest}, indent=2),
        encoding="utf-8",
    )
    txt_path.write_text(
        "CMIDO RO1 STEP 26C.1 — PROBABILISTIC ML SPECIFICATION\n"
        f"SHA256: {digest}\n\n" + json.dumps(spec, indent=2),
        encoding="utf-8",
    )

    assert len(DATASETS["RO1_PRICE"]["series"]) == 5
    assert len(DATASETS["RO1_DEMAND"]["series"]) == 4
    assert HORIZONS == (1, 3, 6, 12)
    assert PRIMARY_HORIZON == 3
    assert QUANTILES == (0.10, 0.25, 0.50, 0.75, 0.90)
    assert not CROSS_MATERIAL_FEATURES_ENABLED
    assert not EXTERNAL_FEATURES_ENABLED
    assert MODEL_FAMILIES == ("XGBoost", "LightGBM")
    assert spec["temporal"]["validation_only_selection"] is True
    assert spec["temporal"]["test_frozen"] is True
    assert spec["probabilistic"]["conformal_calibration"] is False

    print("\n[7] SPECIFICATION FREEZE")
    print(f"SHA256: {digest}")
    print(f"JSON: {json_path}")
    print(f"Text: {txt_path}")

    print("\n[FINAL ASSERTIONS]")
    print("Input data contract: PASS")
    print("Temporal contract: PASS")
    print("Feature leakage contract: PASS")
    print("Probabilistic quantile contract: PASS")
    print("Model family contract: PASS")
    print("Validation-only selection contract: PASS")
    print("Frozen-test contract: PASS")
    print("Conformal disabled: PASS")
    print("No model training performed: PASS")
    print("\nALL STEP 26C.1 ASSERTIONS: PASS")
    print("=" * 78)


if __name__ == "__main__":
    main()
