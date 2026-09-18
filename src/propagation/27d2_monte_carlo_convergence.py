"""
CMIDO — RO2 Step 27D.2
Monte Carlo Convergence & Tail Stability Audit

Run from:
    D:\CMIDO

Command:
    python src\propagation\27d2_monte_carlo_convergence.py

This intentionally reruns the frozen 27D propagation calculation at
multiple Monte Carlo sample sizes. It does not use RO1 test forecasts.
"""

from __future__ import annotations

from pathlib import Path
import json
import hashlib
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

OUT_DIR = ROOT / "results" / "RO2" / "propagation_convergence"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MC_SIZES = (1_000, 2_500, 5_000, 10_000, 25_000)
REFERENCE_N = 10_000

MATERIALS = {
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
}

SOURCE_HORIZONS = (1, 3, 6, 12)
ALL_HORIZONS = tuple(range(1, 13))
QUANTILES = np.array([0.10, 0.25, 0.50, 0.75, 0.90])
SUMMARY_QUANTILES = ("q50", "q75", "q90", "q95", "q99")

DURATION_N = 37
BASE_SEED = 2702


def resolve_col(df: pd.DataFrame, names: list[str]) -> str:
    for name in names:
        if name in df.columns:
            return name
    raise KeyError(f"None of {names} found. Available={list(df.columns)}")


def load_ro1() -> pd.DataFrame:
    if not RO1_VALIDATION.exists():
        raise FileNotFoundError(RO1_VALIDATION)

    df = pd.read_csv(RO1_VALIDATION)

    dataset_col = resolve_col(df, ["dataset"])
    series_col = resolve_col(df, ["series", "material"])
    origin_col = resolve_col(df, ["forecast_origin"])
    target_col = resolve_col(df, ["target_date"])
    horizon_col = resolve_col(df, ["horizon"])

    required = ["q10", "q25", "q50", "q75", "q90"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing RO1 quantiles: {missing}")

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

    out = out[out["dataset"].eq("RO1_DEMAND")]
    out = out[out["series"].isin(MATERIALS)].copy()

    if out.empty:
        raise AssertionError("No RO1 demand validation data found.")

    for q in ["q10", "q25", "q50", "q75", "q90"]:
        out[q] = pd.to_numeric(out[q], errors="raise")

    return out


def load_duration_pairs() -> pd.DataFrame:
    if not RO2_COMPONENTS.exists():
        raise FileNotFoundError(RO2_COMPONENTS)

    df = pd.read_csv(RO2_COMPONENTS)
    required = [
        "PR", "PO", "SR", "Status",
        "Internal_num", "PODN_num", "TotalDN_num",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing 27B.4 fields: {missing}")

    work = df.copy()

    for c in ["Internal_num", "PODN_num", "TotalDN_num"]:
        work[c] = pd.to_numeric(work[c], errors="coerce")

    work = work[
        work["PR"].notna()
        & work["PO"].notna()
        & (work["PO"].astype(str).str.strip() != "1")
    ].copy()

    work = work.loc[
        ~work.duplicated(
            subset=[
                "PR", "PO", "SR", "Status",
                "Internal_num", "PODN_num", "TotalDN_num",
            ],
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

    if len(paired) != DURATION_N:
        raise AssertionError(
            f"Expected 37 paired duration rows, found {len(paired)}"
        )

    reconstruction = (
        paired["Internal_num"] + paired["PODN_num"] - paired["TotalDN_num"]
    )

    if not np.isclose(reconstruction, 0).all():
        raise AssertionError("27B.4 component reconstruction failed.")

    return paired


def interpolate_quantiles(records: pd.DataFrame, material: str, origin: pd.Timestamp):
    sub = records[
        (records["series"] == material)
        & (records["forecast_origin"] == origin)
        & (records["horizon"].isin(SOURCE_HORIZONS))
    ].copy()

    counts = sub.groupby("horizon").size()

    if set(counts.index) != set(SOURCE_HORIZONS) or not (counts == 1).all():
        raise AssertionError(
            f"{material}/{origin.date()} missing/duplicate source horizons: "
            f"{counts.to_dict()}"
        )

    sub = sub.sort_values("horizon")
    hs = sub["horizon"].to_numpy(float)

    result = {}
    for h in ALL_HORIZONS:
        vals = np.array(
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

        if not np.isfinite(vals).all():
            raise AssertionError("Non-finite interpolated quantile.")

        vals = np.maximum(vals, 0.0)
        vals = np.maximum.accumulate(vals)

        if not np.all(np.diff(vals) >= -1e-12):
            raise AssertionError("Quantile repair failed.")

        result[h] = vals

    return result


def month_days(ts: pd.Timestamp) -> int:
    ts = pd.Timestamp(ts).replace(day=1)
    return int((ts + pd.offsets.MonthBegin(1) - ts).days)


def sample_from_quantiles(qgrid: np.ndarray, uniforms: np.ndarray) -> np.ndarray:
    q = QUANTILES
    out = np.empty_like(uniforms, dtype=float)

    lo = uniforms < q[0]
    hi = uniforms > q[-1]
    mid = ~(lo | hi)

    if np.any(mid):
        out[mid] = np.interp(uniforms[mid], q, qgrid)

    slope_lo = (qgrid[1] - qgrid[0]) / (q[1] - q[0])
    out[lo] = qgrid[0] + (uniforms[lo] - q[0]) * slope_lo

    slope_hi = (qgrid[-1] - qgrid[-2]) / (q[-1] - q[-2])
    out[hi] = qgrid[-1] + (uniforms[hi] - q[-1]) * slope_hi

    return np.maximum(out, 0.0)


def duration_draws(
    durations: pd.DataFrame,
    n: int,
    seed: int,
):
    rng = np.random.default_rng(seed)
    ix = rng.integers(0, len(durations), n)
    return (
        durations.iloc[ix]["TotalDN_num"].to_numpy(dtype=float)
    )


def propagate(
    qgrid: dict[int, np.ndarray],
    durations: pd.DataFrame,
    origin: pd.Timestamp,
    n: int,
    seed: int,
):
    # One deterministic stream per N/material/origin.
    rng = np.random.default_rng(seed)

    ix = rng.integers(0, len(durations), n)
    duration = durations.iloc[ix]["TotalDN_num"].to_numpy(float)

    start_month = pd.Timestamp(origin) + pd.offsets.MonthBegin(1)
    exposure = np.zeros(n, dtype=float)

    for h in ALL_HORIZONS:
        month_start = start_month + pd.offsets.MonthBegin(h - 1)
        days = month_days(month_start)

        elapsed = 0
        for k in range(1, h):
            elapsed += month_days(
                start_month + pd.offsets.MonthBegin(k - 1)
            )

        covered = np.clip(duration - elapsed, 0, days)
        frac = covered / days

        uniforms = rng.random(n)
        demand = sample_from_quantiles(qgrid[h], uniforms)

        exposure += demand * frac

    stats = {
        "mean": float(np.mean(exposure)),
        "q50": float(np.quantile(exposure, 0.50)),
        "q75": float(np.quantile(exposure, 0.75)),
        "q90": float(np.quantile(exposure, 0.90)),
        "q95": float(np.quantile(exposure, 0.95)),
        "q99": float(np.quantile(exposure, 0.99)),
        "mc_se_mean": float(
            np.std(exposure, ddof=1) / np.sqrt(n)
        ),
        "min": float(np.min(exposure)),
        "max": float(np.max(exposure)),
    }

    return stats


def stable_relative_change(current: float, previous: float) -> float:
    return 100.0 * abs(current - previous) / max(abs(current), 1e-12)


def main() -> None:
    print("=" * 80)
    print("CMIDO RO2 STEP 27D.2 — MONTE CARLO CONVERGENCE")
    print("=" * 80)

    ro1 = load_ro1()
    durations = load_duration_pairs()

    origin_sets = {}
    for material in sorted(MATERIALS):
        sub = ro1[ro1["series"] == material]
        counts = sub.groupby("forecast_origin")["horizon"].nunique()
        origins = list(counts[counts == 4].index)
        if not origins:
            raise AssertionError(
                f"No complete validation origins for {material}"
            )
        origin_sets[material] = origins

    print(f"RO1 validation rows: {len(ro1)}")
    print(f"RO2 paired duration rows: {len(durations)}")
    print(f"MC sizes: {MC_SIZES}")

    long_rows = []

    for material in sorted(MATERIALS):
        print(
            f"\n[{material}] complete origins: "
            f"{len(origin_sets[material])}"
        )

        for origin in origin_sets[material]:
            qgrid = interpolate_quantiles(
                ro1, material, pd.Timestamp(origin)
            )

            # Stable seed identity independent of Python's process hash.
            key = f"{BASE_SEED}|{material}|{pd.Timestamp(origin).date()}"
            seed_base = int.from_bytes(
                hashlib.sha256(key.encode("utf-8")).digest()[:8],
                "little",
            ) % (2**32 - 1)

            for n in MC_SIZES:
                # Distinct, reproducible stream for each sample size.
                seed = (seed_base + 1000003 * n) % (2**32 - 1)

                stats = propagate(
                    qgrid=qgrid,
                    durations=durations,
                    origin=pd.Timestamp(origin),
                    n=n,
                    seed=seed,
                )

                row = {
                    "material": material,
                    "forecast_origin": pd.Timestamp(origin),
                    "representation": "joint_duration_primary",
                    "mc_n": n,
                    **stats,
                }
                long_rows.append(row)

    long_df = pd.DataFrame(long_rows)
    long_df.to_csv(
        OUT_DIR / "RO2_step27d2_convergence_long.csv",
        index=False,
    )

    change_rows = []

    for (material, origin), g in long_df.groupby(
        ["material", "forecast_origin"], sort=False
    ):
        g = g.sort_values("mc_n")

        previous = None
        for _, row in g.iterrows():
            if previous is None:
                previous = row
                continue

            for stat in ["mean", "q50", "q75", "q90", "q95", "q99"]:
                current_value = float(row[stat])
                previous_value = float(previous[stat])

                change_rows.append({
                    "material": material,
                    "forecast_origin": origin,
                    "from_mc_n": int(previous["mc_n"]),
                    "to_mc_n": int(row["mc_n"]),
                    "statistic": stat,
                    "previous_value": previous_value,
                    "current_value": current_value,
                    "absolute_change": abs(current_value - previous_value),
                    "relative_change_pct": stable_relative_change(
                        current_value, previous_value
                    ),
                })

            previous = row

    changes = pd.DataFrame(change_rows)
    changes.to_csv(
        OUT_DIR / "RO2_step27d2_convergence_changes.csv",
        index=False,
    )

    # Reference stability: 5,000 -> 10,000.
    ref_changes = changes[
        (changes["from_mc_n"] == 5000)
        & (changes["to_mc_n"] == 10000)
    ].copy()

    criteria = {
        "mean": 1.0,
        "q90": 2.0,
        "q95": 2.0,
        "q99": 5.0,
    }

    stability_rows = []

    for (material, origin), g in ref_changes.groupby(
        ["material", "forecast_origin"], sort=False
    ):
        metric_pass = {}
        for stat, threshold in criteria.items():
            val = float(
                g.loc[g["statistic"].eq(stat), "relative_change_pct"].iloc[0]
            )
            metric_pass[stat] = val <= threshold

        stable = all(metric_pass.values())

        stability_rows.append({
            "material": material,
            "forecast_origin": origin,
            "mean_5000_to_10000_pct": float(
                g.loc[g["statistic"].eq("mean"), "relative_change_pct"].iloc[0]
            ),
            "q90_5000_to_10000_pct": float(
                g.loc[g["statistic"].eq("q90"), "relative_change_pct"].iloc[0]
            ),
            "q95_5000_to_10000_pct": float(
                g.loc[g["statistic"].eq("q95"), "relative_change_pct"].iloc[0]
            ),
            "q99_5000_to_10000_pct": float(
                g.loc[g["statistic"].eq("q99"), "relative_change_pct"].iloc[0]
            ),
            "mean_pass": metric_pass["mean"],
            "q90_pass": metric_pass["q90"],
            "q95_pass": metric_pass["q95"],
            "q99_pass": metric_pass["q99"],
            "tail_stable_at_10000": stable,
        })

    stability = pd.DataFrame(stability_rows)
    stability.to_csv(
        OUT_DIR / "RO2_step27d2_stability_summary.csv",
        index=False,
    )

    # Study-level lock decision.
    all_10000_stable = bool(stability["tail_stable_at_10000"].all())

    # Additional diagnostic: maximum 10k -> 25k changes.
    diag = changes[
        (changes["from_mc_n"] == 10000)
        & (changes["to_mc_n"] == 25000)
    ]

    max_diag = (
        float(diag["relative_change_pct"].max())
        if not diag.empty else float("nan")
    )

    if all_10000_stable:
        lock_n = REFERENCE_N
        decision = "PASS"
    else:
        # Check whether 10k->25k is small enough under the same criteria.
        # This is a diagnostic only; later optimization must use a single lock N.
        # We conservatively require all relevant 10k->25k changes to meet
        # the corresponding thresholds before recommending 25k.
        stable_25k = True
        for stat, threshold in criteria.items():
            gg = diag[diag["statistic"].eq(stat)]
            if gg.empty or not (gg["relative_change_pct"] <= threshold).all():
                stable_25k = False
                break

        if stable_25k:
            lock_n = 25000
            decision = "PASS_25000_REQUIRED"
        else:
            lock_n = None
            decision = "HOLD_FOR_REVIEW"

    summary = {
        "step": "27D.2",
        "decision": decision,
        "recommended_mc_lock": lock_n,
        "reference_n": REFERENCE_N,
        "mc_sizes_evaluated": list(MC_SIZES),
        "all_48_material_origin_cases_stable_at_10000": all_10000_stable,
        "max_10000_to_25000_relative_change_pct": max_diag,
        "criteria_pct": {
            "mean": 1.0,
            "q90": 2.0,
            "q95": 2.0,
            "q99": 5.0,
        },
        "test_data_used": False,
        "primary_representation": "joint_duration_primary",
        "duration_terminology": "procurement-process duration",
        "duration_pair_n": DURATION_N,
    }

    (OUT_DIR / "RO2_step27d2_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    decision_text = [
        f"DECISION: {decision}",
        f"RECOMMENDED_MC_LOCK: {lock_n}",
        "",
        "Criteria for 5,000 -> 10,000:",
        "- mean <= 1%",
        "- q90 <= 2%",
        "- q95 <= 2%",
        "- q99 <= 5%",
        "",
        f"All primary material/origin cases stable at 10,000: "
        f"{all_10000_stable}",
        f"Maximum 10,000 -> 25,000 relative change observed: "
        f"{max_diag:.6f}%",
        "",
        "Interpretation:",
        "- This is numerical Monte Carlo stability only.",
        "- It does not establish supplier-specific lead time.",
        "- It does not establish disruption probabilities.",
        "- Joint duration sampling preserves observed pairing; it does not prove dependence.",
        "- No RO1 test forecasts were used.",
    ]

    (OUT_DIR / "RO2_step27d2_decision.txt").write_text(
        "\n".join(decision_text) + "\n",
        encoding="utf-8",
    )

    print("\nCONVERGENCE RESULTS")
    print(f"Material/origin cases: {len(stability)}")
    print(
        "Stable at 10,000:",
        int(stability["tail_stable_at_10000"].sum()),
        "/",
        len(stability),
    )
    print(
        "Max 10,000 -> 25,000 relative change:",
        f"{max_diag:.6f}%",
    )

    print("\nDECISION:", decision)
    print("Recommended MC lock:", lock_n)

    print("\nOutputs:")
    for p in [
        OUT_DIR / "RO2_step27d2_convergence_long.csv",
        OUT_DIR / "RO2_step27d2_convergence_changes.csv",
        OUT_DIR / "RO2_step27d2_stability_summary.csv",
        OUT_DIR / "RO2_step27d2_decision.txt",
        OUT_DIR / "RO2_step27d2_summary.json",
    ]:
        print(" -", p)

    print("\n27D.2 convergence audit complete.")


if __name__ == "__main__":
    main()
