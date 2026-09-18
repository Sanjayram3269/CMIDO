"""
CMIDO — RO2 Step 27D
Demand–Procurement-Duration Uncertainty Propagation

Frozen contract:
    docs/CMIDO_RO2_27D_Propagation_Specification_v1.0.md

Primary:
    RO1 validation CQR probabilistic demand quantiles
    + RO2 37-row joint empirical procurement-duration pairs
    + calendar-month overlap
    + 10,000 Monte Carlo draws

Important:
    This is NOT supplier-specific lead-time modelling.
    It is procurement-process-duration uncertainty propagation.
"""

from __future__ import annotations

from pathlib import Path
import json
import hashlib
from datetime import datetime

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

RO1_VALIDATION = (
    ROOT / "results" / "forecasting" / "probabilistic_calibration"
    / "RO1_step26c3_validation_forecasts.csv"
)
RO2_COMPONENTS = (
    ROOT / "results" / "RO2" / "data_audit"
    / "RO2_step27b4_admissible_modelling_view.csv"
)
OUT_DIR = ROOT / "results" / "RO2" / "propagation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 2701
N_MC = 10_000
DURATION_SAMPLE_N = 37

DEMAND_MATERIALS = {
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
}

SOURCE_HORIZONS = (1, 3, 6, 12)
INTERPOLATED_HORIZONS = tuple(range(1, 13))
QUANTILES = np.array([0.10, 0.25, 0.50, 0.75, 0.90])
TAIL_QUANTILES = np.array([0.50, 0.75, 0.90, 0.95, 0.99])


def resolve_col(df: pd.DataFrame, names: list[str]) -> str:
    for name in names:
        if name in df.columns:
            return name
    raise KeyError(f"None of {names} found. Available: {list(df.columns)}")


def load_ro1_validation() -> pd.DataFrame:
    if not RO1_VALIDATION.exists():
        raise FileNotFoundError(f"Missing frozen RO1 validation forecasts:\n{RO1_VALIDATION}")

    df = pd.read_csv(RO1_VALIDATION)

    dataset_col = resolve_col(df, ["dataset"])
    series_col = resolve_col(df, ["series", "material"])
    origin_col = resolve_col(df, ["forecast_origin"])
    target_col = resolve_col(df, ["target_date"])
    horizon_col = resolve_col(df, ["horizon"])

    required = ["q10", "q25", "q50", "q75", "q90"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing RO1 probabilistic quantiles: {missing}")

    out = df.rename(
        columns={
            dataset_col: "dataset",
            series_col: "series",
            origin_col: "forecast_origin",
            target_col: "target_date",
            horizon_col: "horizon",
        }
    ).copy()

    out["forecast_origin"] = pd.to_datetime(out["forecast_origin"])
    out["target_date"] = pd.to_datetime(out["target_date"])
    out["horizon"] = pd.to_numeric(out["horizon"], errors="raise").astype(int)

    out = out[out["dataset"].eq("RO1_DEMAND")].copy()
    out = out[out["series"].isin(DEMAND_MATERIALS)].copy()

    for q in ["q10", "q25", "q50", "q75", "q90"]:
        out[q] = pd.to_numeric(out[q], errors="coerce")

    if out.empty:
        raise AssertionError("No RO1_DEMAND validation records found.")

    return out


def load_ro2_components() -> pd.DataFrame:
    if not RO2_COMPONENTS.exists():
        raise FileNotFoundError(f"Missing locked 27B.4 modelling view:\n{RO2_COMPONENTS}")

    df = pd.read_csv(RO2_COMPONENTS)

    required = ["PR", "PO", "SR", "Status", "Internal_num", "PODN_num", "TotalDN_num"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"27B.4 schema mismatch. Missing: {missing}")

    work = df.copy()
    for c in ["Internal_num", "PODN_num", "TotalDN_num"]:
        work[c] = pd.to_numeric(work[c], errors="coerce")

    # Reproduce the locked 27B.4 integrity rules.
    work = work[
        work["PR"].notna()
        & work["PO"].notna()
        & (work["PO"].astype(str).str.strip() != "1")
    ].copy()

    work = work.loc[
        ~work.duplicated(
            subset=["PR", "PO", "SR", "Status", "Internal_num", "PODN_num", "TotalDN_num"],
            keep="first",
        )
    ].copy()

    paired = work.dropna(
        subset=["Internal_num", "PODN_num", "TotalDN_num"]
    ).copy()

    paired = paired[
        (paired["Internal_num"] > 0)
        & (paired["PODN_num"] > 0)
        & (paired["TotalDN_num"] > 0)
    ].copy()

    if len(paired) != DURATION_SAMPLE_N:
        raise AssertionError(
            f"Expected locked 27B.4 paired n={DURATION_SAMPLE_N}, found {len(paired)}."
        )

    reconstruction = paired["Internal_num"] + paired["PODN_num"] - paired["TotalDN_num"]
    if not np.isclose(reconstruction, 0).all():
        raise AssertionError("27B.4 component reconstruction failed in 27D.")

    return paired


def interpolate_quantiles(records: pd.DataFrame, material: str, origin: pd.Timestamp) -> dict[int, np.ndarray]:
    sub = records[
        (records["series"] == material)
        & (records["forecast_origin"] == origin)
    ].copy()

    sub = sub[sub["horizon"].isin(SOURCE_HORIZONS)].copy()

    # Exactly one record per source horizon is required.
    counts = sub.groupby("horizon").size()
    if set(counts.index) != set(SOURCE_HORIZONS) or not (counts == 1).all():
        raise AssertionError(
            f"{material} / {origin.date()} does not have exactly one record "
            f"for each source horizon {SOURCE_HORIZONS}. Counts={counts.to_dict()}"
        )

    sub = sub.sort_values("horizon")
    hs = sub["horizon"].to_numpy(float)

    result = {}
    for h in INTERPOLATED_HORIZONS:
        qvals = np.array(
            [
                np.interp(
                    h,
                    hs,
                    sub[f"q{int(q * 100)}"].to_numpy(float),
                )
                for q in QUANTILES
            ],
            dtype=float,
        )

        if not np.isfinite(qvals).all():
            raise AssertionError(f"Non-finite interpolated quantiles at h={h}.")
        if np.any(qvals < 0):
            # Demand is physically non-negative; do not permit negative
            # interpolated predictive quantiles.
            qvals = np.maximum(qvals, 0.0)

        # Monotone quantile repair, deterministic and identical for all runs.
        qvals = np.maximum.accumulate(qvals)

        if not np.all(np.diff(qvals) >= -1e-12):
            raise AssertionError("Quantile monotonicity failed after repair.")

        result[h] = qvals

    return result


def sample_from_quantiles(qgrid: np.ndarray, uniforms: np.ndarray) -> np.ndarray:
    """Piecewise-linear inverse CDF over q=.10,.25,.50,.75,.90.

    Tails outside [.10,.90] are linearly extended using the nearest available
    quantile segment, then bounded below at zero. This is deliberately
    documented rather than silently treating q10/q90 as hard distribution
    limits.
    """
    q = QUANTILES

    out = np.empty_like(uniforms, dtype=float)

    lo = uniforms < q[0]
    hi = uniforms > q[-1]
    mid = ~(lo | hi)

    if np.any(mid):
        out[mid] = np.interp(uniforms[mid], q, qgrid)

    # Lower tail: extend q10 toward probability zero using the first segment.
    slope_lo = (qgrid[1] - qgrid[0]) / (q[1] - q[0])
    out[lo] = qgrid[0] + (uniforms[lo] - q[0]) * slope_lo

    # Upper tail: extend q90 using the last segment.
    slope_hi = (qgrid[-1] - qgrid[-2]) / (q[-1] - q[-2])
    out[hi] = qgrid[-1] + (uniforms[hi] - q[-1]) * slope_hi

    return np.maximum(out, 0.0)


def month_days(ts: pd.Timestamp) -> int:
    next_month = ts + pd.offsets.MonthBegin(1)
    return int((next_month - ts).days)


def overlap_weights(start_month: pd.Timestamp, duration_days: int) -> list[tuple[int, float]]:
    """Return (forecast-month horizon, calendar fraction covered).

    start_month is the first future calendar month available to RO1.
    """
    if duration_days <= 0:
        raise ValueError("Duration must be positive.")

    remaining = int(duration_days)
    current = pd.Timestamp(start_month).replace(day=1)
    h = 1
    result = []

    while remaining > 0 and h <= 12:
        days = month_days(current)
        covered = min(remaining, days)
        result.append((h, covered / days))
        remaining -= covered
        current = current + pd.offsets.MonthBegin(1)
        h += 1

    if remaining > 0:
        raise AssertionError(
            "Duration exceeds the 12-month RO1 propagation horizon. "
            "No extrapolation is permitted."
        )

    return result


def duration_summary(duration_pairs: pd.DataFrame) -> dict:
    total = duration_pairs["TotalDN_num"].to_numpy(float)
    return {
        "n": int(len(total)),
        "q50": float(np.quantile(total, .50)),
        "q75": float(np.quantile(total, .75)),
        "q90": float(np.quantile(total, .90)),
        "q95": float(np.quantile(total, .95)),
        "q99": float(np.quantile(total, .99)),
        "mean": float(np.mean(total)),
        "max": float(np.max(total)),
    }


def propagate_one(material: str, origin: pd.Timestamp, ro1: pd.DataFrame,
                   duration_pairs: pd.DataFrame, rng: np.random.Generator) -> dict:
    qgrids = interpolate_quantiles(ro1, material, origin)

    internal = duration_pairs["Internal_num"].to_numpy(float)
    component = duration_pairs["PODN_num"].to_numpy(float)

    # Primary: jointly resample observed component pairs.
    idx = rng.integers(0, len(duration_pairs), N_MC)
    durations = internal[idx] + component[idx]

    # Future demand begins in the first month after the forecast origin.
    start_month = origin + pd.offsets.MonthBegin(1)

    demand_exposure = np.zeros(N_MC, dtype=float)

    # Independent monthly marginal draws are used because RO1 does not provide
    # a full joint future-path distribution. This is an explicit limitation.
    for h, weight in overlap_weights(start_month, int(np.ceil(np.max(durations)))):
        uniforms = rng.random(N_MC)
        monthly_demand = sample_from_quantiles(qgrids[h], uniforms)

        # A draw with duration shorter than this month receives zero weight;
        # otherwise use exact calendar overlap for that duration.
        month_start = start_month + pd.offsets.MonthBegin(h - 1)
        days_in_month = month_days(month_start)

        # Vectorized exact overlap for each sampled duration.
        elapsed_before = sum(
            month_days(start_month + pd.offsets.MonthBegin(k - 1))
            for k in range(1, h)
        )
        covered_days = np.clip(durations - elapsed_before, 0, days_in_month)
        frac = covered_days / days_in_month

        demand_exposure += monthly_demand * frac

    # Independent-duration sensitivity with the same demand-generation design.
    ix = rng.integers(0, len(internal), N_MC)
    iy = rng.integers(0, len(component), N_MC)
    independent_durations = internal[ix] + component[iy]

    independent_exposure = np.zeros(N_MC, dtype=float)

    for h in range(1, 13):
        month_start = start_month + pd.offsets.MonthBegin(h - 1)
        days_in_month = month_days(month_start)
        elapsed_before = sum(
            month_days(start_month + pd.offsets.MonthBegin(k - 1))
            for k in range(1, h)
        )

        covered_days = np.clip(independent_durations - elapsed_before, 0, days_in_month)
        frac = covered_days / days_in_month

        if np.any(frac > 0):
            uniforms = rng.random(N_MC)
            monthly_demand = sample_from_quantiles(qgrids[h], uniforms)
            independent_exposure += monthly_demand * frac

    def summarize(x: np.ndarray, label: str) -> dict:
        return {
            "material": material,
            "forecast_origin": origin,
            "representation": label,
            "mc_n": N_MC,
            "mean_demand_during_duration": float(np.mean(x)),
            "median_demand_during_duration": float(np.median(x)),
            "q50": float(np.quantile(x, .50)),
            "q75": float(np.quantile(x, .75)),
            "q90": float(np.quantile(x, .90)),
            "q95": float(np.quantile(x, .95)),
            "q99": float(np.quantile(x, .99)),
            "mc_se_mean": float(np.std(x, ddof=1) / np.sqrt(N_MC)),
            "min": float(np.min(x)),
            "max": float(np.max(x)),
        }

    primary = summarize(demand_exposure, "joint_duration_primary")
    sensitivity = summarize(independent_exposure, "independent_duration_sensitivity")

    # Inventory/service-risk curve. Thresholds are deliberately empirical:
    # q50/q75/q90/q95/q99 of the primary exposure distribution.
    thresholds = np.quantile(demand_exposure, TAIL_QUANTILES)
    risk_rows = []
    for threshold in thresholds:
        shortage = demand_exposure > threshold
        risk_rows.append({
            "material": material,
            "forecast_origin": origin,
            "representation": "joint_duration_primary",
            "inventory_threshold": float(threshold),
            "shortage_probability": float(np.mean(shortage)),
            "service_level": float(np.mean(~shortage)),
        })

    return {
        "summary": [primary, sensitivity],
        "risk": risk_rows,
        "duration_draws": durations,
        "primary_exposure": demand_exposure,
        "independent_exposure": independent_exposure,
    }


def main() -> None:
    print("=" * 80)
    print("CMIDO RO2 STEP 27D — DEMAND–PROCUREMENT-DURATION PROPAGATION")
    print("=" * 80)

    ro1 = load_ro1_validation()
    durations = load_ro2_components()

    print(f"RO1 validation demand rows: {len(ro1)}")
    print(f"RO2 locked paired duration rows: {len(durations)}")
    print(f"Materials: {sorted(ro1['series'].unique())}")
    print(f"Source horizons: {SOURCE_HORIZONS}")
    print(f"Monte Carlo draws per material/origin: {N_MC}")

    # Frozen validation origins are only those with all four source horizons
    # available for the given material.
    origin_sets = {}
    for material in sorted(DEMAND_MATERIALS):
        subset = ro1[ro1["series"] == material]
        counts = subset.groupby("forecast_origin")["horizon"].nunique()
        origin_sets[material] = list(counts[counts == 4].index)

    if any(len(v) == 0 for v in origin_sets.values()):
        raise AssertionError(f"At least one material has no complete four-horizon origins: {origin_sets}")

    rng = np.random.default_rng(SEED)

    summary_rows = []
    risk_rows = []
    audit_rows = []
    sensitivity_rows = []

    for material in sorted(DEMAND_MATERIALS):
        origins = origin_sets[material]
        print(f"\n[{material}] complete validation origins: {len(origins)}")

        for origin in origins:
            result = propagate_one(material, pd.Timestamp(origin), ro1, durations, rng)

            summary_rows.extend(result["summary"])
            risk_rows.extend(result["risk"])

            primary = result["primary_exposure"]
            independent = result["independent_exposure"]

            for q in TAIL_QUANTILES:
                jq = float(np.quantile(primary, q))
                iq = float(np.quantile(independent, q))
                sensitivity_rows.append({
                    "material": material,
                    "forecast_origin": origin,
                    "quantile": q,
                    "joint_duration_days_q50_q99_distribution": jq,
                    "independent_duration_sensitivity": iq,
                    "independent_minus_joint": iq - jq,
                    "independent_vs_joint_pct": 100 * (iq - jq) / jq if jq else np.nan,
                })

            audit_rows.append({
                "material": material,
                "forecast_origin": origin,
                "source_horizons_present": "1,3,6,12",
                "duration_pair_n": len(durations),
                "mc_n": N_MC,
                "all_primary_finite": bool(np.isfinite(primary).all()),
                "all_primary_nonnegative": bool((primary >= 0).all()),
                "all_independent_finite": bool(np.isfinite(independent).all()),
                "all_independent_nonnegative": bool((independent >= 0).all()),
            })

    summary = pd.DataFrame(summary_rows)
    risk = pd.DataFrame(risk_rows)
    sensitivity = pd.DataFrame(sensitivity_rows)
    audit = pd.DataFrame(audit_rows)

    # Contract assertions.
    assert set(summary["material"]) == DEMAND_MATERIALS
    assert set(summary["representation"]) == {
        "joint_duration_primary",
        "independent_duration_sensitivity",
    }
    assert audit["duration_pair_n"].eq(DURATION_SAMPLE_N).all()
    assert audit["all_primary_finite"].all()
    assert audit["all_primary_nonnegative"].all()
    assert audit["all_independent_finite"].all()
    assert audit["all_independent_nonnegative"].all()
    assert risk["shortage_probability"].between(0, 1).all()
    assert risk["service_level"].between(0, 1).all()

    summary_path = OUT_DIR / "RO2_step27d_propagation_summary.csv"
    risk_path = OUT_DIR / "RO2_step27d_service_risk_curve.csv"
    sens_path = OUT_DIR / "RO2_step27d_joint_vs_independent_sensitivity.csv"
    audit_path = OUT_DIR / "RO2_step27d_audit.csv"

    summary.to_csv(summary_path, index=False)
    risk.to_csv(risk_path, index=False)
    sensitivity.to_csv(sens_path, index=False)
    audit.to_csv(audit_path, index=False)

    config = {
        "step": "27D",
        "specification": "CMIDO_RO2_27D_Propagation_Specification_v1.0",
        "seed": SEED,
        "mc_draws": N_MC,
        "duration_pair_n": DURATION_SAMPLE_N,
        "source_horizons": SOURCE_HORIZONS,
        "interpolated_horizons": INTERPOLATED_HORIZONS,
        "materials": sorted(DEMAND_MATERIALS),
        "primary": "RO1 validation CQR quantiles + joint empirical RO2 duration pairs",
        "duration_terminology": "procurement-process duration",
        "test_data_used": False,
        "execution_utc": datetime.utcnow().isoformat() + "Z",
    }
    config_path = OUT_DIR / "RO2_step27d_run_config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    print("\nFINAL ASSERTIONS")
    print("RO1 demand-only filtering: PASS")
    print("Four source horizons per propagated origin: PASS")
    print("RO2 paired duration n=37: PASS")
    print("Non-negative finite Monte Carlo outputs: PASS")
    print("Service-risk probabilities in [0,1]: PASS")
    print("No RO1 test forecasts used: PASS")
    print("\nOutputs:")
    for p in [summary_path, risk_path, sens_path, audit_path, config_path]:
        print(" -", p)
    print("\nALL STEP 27D ASSERTIONS: PASS")


if __name__ == "__main__":
    main()
