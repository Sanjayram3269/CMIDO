"""
CMIDO — RO2 Step 27D.1
Propagation Result Audit & Sensitivity Analysis

Consumes saved Step 27D CSV/JSON outputs.
Does not regenerate demand forecasts and does not use RO1 test forecasts.

Run from:
    D:\CMIDO

Command:
    python src\propagation\27d1_propagation_result_audit.py
"""

from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
IN_DIR = ROOT / "results" / "RO2" / "propagation"
OUT_DIR = ROOT / "results" / "RO2" / "propagation_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY = IN_DIR / "RO2_step27d_propagation_summary.csv"
RISK = IN_DIR / "RO2_step27d_service_risk_curve.csv"
SENS = IN_DIR / "RO2_step27d_joint_vs_independent_sensitivity.csv"
AUDIT = IN_DIR / "RO2_step27d_audit.csv"
CONFIG = IN_DIR / "RO2_step27d_run_config.json"

MATERIALS = {
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
}
REQUIRED_QS = ["q50", "q75", "q90", "q95", "q99"]


def require_files() -> None:
    missing = [str(p) for p in [SUMMARY, RISK, SENS, AUDIT, CONFIG] if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing Step 27D outputs:\n" + "\n".join(missing)
        )


def load_inputs():
    require_files()
    summary = pd.read_csv(SUMMARY)
    risk = pd.read_csv(RISK)
    sens = pd.read_csv(SENS)
    audit = pd.read_csv(AUDIT)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    return summary, risk, sens, audit, config


def distribution_audit(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []

    required = {
        "material", "forecast_origin", "representation", "mc_n",
        "mean_demand_during_duration", "median_demand_during_duration",
        "q50", "q75", "q90", "q95", "q99", "mc_se_mean", "min", "max"
    }
    missing = required - set(summary.columns)
    if missing:
        raise AssertionError(f"Summary schema missing: {sorted(missing)}")

    for _, r in summary.iterrows():
        vals = [float(r[q]) for q in REQUIRED_QS]
        finite = np.isfinite(vals + [
            float(r["mean_demand_during_duration"]),
            float(r["median_demand_during_duration"]),
            float(r["mc_se_mean"]),
            float(r["min"]),
            float(r["max"]),
        ]).all()
        nonnegative = all(v >= -1e-12 for v in vals) and float(r["min"]) >= -1e-12
        ordered = all(vals[i] <= vals[i + 1] + 1e-10 for i in range(len(vals) - 1))
        median_match = abs(
            float(r["median_demand_during_duration"]) - float(r["q50"])
        ) <= max(1e-8, 1e-6 * max(1.0, abs(float(r["q50"]))))

        mean = float(r["mean_demand_during_duration"])
        mc_se = float(r["mc_se_mean"])
        relative_mc_se = np.nan if abs(mean) < 1e-12 else abs(mc_se / mean)

        rows.append({
            "material": r["material"],
            "forecast_origin": r["forecast_origin"],
            "representation": r["representation"],
            "mc_n": int(r["mc_n"]),
            "finite": bool(finite),
            "nonnegative": bool(nonnegative),
            "quantiles_ordered": bool(ordered),
            "median_matches_q50": bool(median_match),
            "relative_mc_se_mean": float(relative_mc_se) if np.isfinite(relative_mc_se) else np.nan,
            "mean": mean,
            "q50": float(r["q50"]),
            "q75": float(r["q75"]),
            "q90": float(r["q90"]),
            "q95": float(r["q95"]),
            "q99": float(r["q99"]),
            "min": float(r["min"]),
            "max": float(r["max"]),
        })

    return pd.DataFrame(rows)


def service_risk_audit(risk: pd.DataFrame) -> pd.DataFrame:
    required = {
        "material", "forecast_origin", "representation",
        "inventory_threshold", "shortage_probability", "service_level"
    }
    missing = required - set(risk.columns)
    if missing:
        raise AssertionError(f"Risk schema missing: {sorted(missing)}")

    rows = []
    for (material, origin), g in risk.groupby(["material", "forecast_origin"], sort=False):
        g = g.sort_values("inventory_threshold")
        thresholds = g["inventory_threshold"].to_numpy(float)
        shortage = g["shortage_probability"].to_numpy(float)
        service = g["service_level"].to_numpy(float)

        threshold_ok = np.all(np.diff(thresholds) >= -1e-10)
        shortage_ok = np.all(np.diff(shortage) <= 1e-10)
        service_ok = np.all(np.diff(service) >= -1e-10)
        bounds_ok = (
            np.isfinite(thresholds).all()
            and np.isfinite(shortage).all()
            and np.isfinite(service).all()
            and ((shortage >= -1e-12) & (shortage <= 1 + 1e-12)).all()
            and ((service >= -1e-12) & (service <= 1 + 1e-12)).all()
        )

        rows.append({
            "material": material,
            "forecast_origin": origin,
            "n_thresholds": len(g),
            "threshold_monotone": bool(threshold_ok),
            "shortage_probability_nonincreasing": bool(shortage_ok),
            "service_level_nondecreasing": bool(service_ok),
            "probability_bounds_ok": bool(bounds_ok),
            "min_shortage_probability": float(np.min(shortage)),
            "max_shortage_probability": float(np.max(shortage)),
            "min_service_level": float(np.min(service)),
            "max_service_level": float(np.max(service)),
        })

    return pd.DataFrame(rows)


def joint_independent_audit(sens: pd.DataFrame) -> pd.DataFrame:
    required = {
        "material", "forecast_origin", "quantile",
        "joint_duration_days_q50_q99_distribution",
        "independent_duration_sensitivity",
        "independent_minus_joint",
        "independent_vs_joint_pct",
    }
    missing = required - set(sens.columns)
    if missing:
        raise AssertionError(f"Sensitivity schema missing: {sorted(missing)}")

    s = sens.copy()
    s["abs_pct_difference"] = s["independent_vs_joint_pct"].abs()

    # Summary at material level across origins and requested quantiles.
    rows = []
    for material, g in s.groupby("material", sort=True):
        rows.append({
            "material": material,
            "n_comparisons": len(g),
            "mean_abs_pct_difference": float(g["abs_pct_difference"].mean()),
            "median_abs_pct_difference": float(g["abs_pct_difference"].median()),
            "max_abs_pct_difference": float(g["abs_pct_difference"].max()),
            "mean_independent_minus_joint": float(g["independent_minus_joint"].mean()),
        })

    return pd.DataFrame(rows)


def structural_audit(
    summary: pd.DataFrame,
    risk: pd.DataFrame,
    sens: pd.DataFrame,
    audit: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:

    representations = set(summary["representation"].dropna().astype(str))
    materials = set(summary["material"].dropna().astype(str))

    source_horizons = tuple(config.get("source_horizons", []))
    interpolated = tuple(config.get("interpolated_horizons", []))

    checks = [
        ("four_materials_present", materials == MATERIALS),
        (
            "both_duration_representations_present",
            representations == {
                "joint_duration_primary",
                "independent_duration_sensitivity",
            },
        ),
        ("source_horizons_1_3_6_12", source_horizons == (1, 3, 6, 12)),
        ("interpolated_horizons_1_to_12", interpolated == tuple(range(1, 13))),
        ("duration_pair_n_37", audit["duration_pair_n"].astype(int).eq(37).all()),
        ("mc_n_10000", summary["mc_n"].astype(int).eq(10000).all()),
        ("all_primary_finite", audit["all_primary_finite"].astype(bool).all()),
        ("all_primary_nonnegative", audit["all_primary_nonnegative"].astype(bool).all()),
        ("all_independent_finite", audit["all_independent_finite"].astype(bool).all()),
        ("all_independent_nonnegative", audit["all_independent_nonnegative"].astype(bool).all()),
        (
            "primary_is_joint_duration",
            config.get("primary", "").startswith("RO1 validation CQR")
            and "joint empirical RO2 duration pairs" in config.get("primary", ""),
        ),
        (
            "procurement_process_duration_terminology",
            config.get("duration_terminology") == "procurement-process duration",
        ),
        ("test_data_declared_unused", config.get("test_data_used") is False),
    ]

    return pd.DataFrame(
        [{"check": name, "pass": bool(ok)} for name, ok in checks]
    )


def main() -> None:
    print("=" * 80)
    print("CMIDO RO2 STEP 27D.1 — PROPAGATION RESULT AUDIT")
    print("=" * 80)

    summary, risk, sens, audit, config = load_inputs()

    print(f"Summary rows: {len(summary)}")
    print(f"Risk rows: {len(risk)}")
    print(f"Sensitivity rows: {len(sens)}")
    print(f"Audit rows: {len(audit)}")

    dist = distribution_audit(summary)
    risk_a = service_risk_audit(risk)
    ji = joint_independent_audit(sens)
    structural = structural_audit(summary, risk, sens, audit, config)

    dist_ok = bool(
        dist["finite"].all()
        and dist["nonnegative"].all()
        and dist["quantiles_ordered"].all()
        and dist["median_matches_q50"].all()
    )
    risk_ok = bool(
        risk_a["threshold_monotone"].all()
        and risk_a["shortage_probability_nonincreasing"].all()
        and risk_a["service_level_nondecreasing"].all()
        and risk_a["probability_bounds_ok"].all()
    )
    structural_ok = bool(structural["pass"].all())

    # 27D.1 deliberately does not invent an MC-stability claim because
    # Step 27D saved summaries, not the 10,000 raw exposure draws.
    mc_stability_status = "NOT_RECOMPUTABLE_FROM_SUMMARY_OUTPUTS"

    if structural_ok and dist_ok and risk_ok:
        decision = "PASS_WITH_RECORDED_CAVEATS"
    else:
        decision = "HOLD_FOR_REVIEW"

    dist.to_csv(
        OUT_DIR / "RO2_step27d1_distribution_audit.csv", index=False
    )
    risk_a.to_csv(
        OUT_DIR / "RO2_step27d1_service_risk_audit.csv", index=False
    )
    ji.to_csv(
        OUT_DIR / "RO2_step27d1_joint_independent_audit.csv", index=False
    )
    structural.to_csv(
        OUT_DIR / "RO2_step27d1_structural_audit.csv", index=False
    )

    summary_json = {
        "step": "27D.1",
        "decision": decision,
        "distribution_checks_pass": dist_ok,
        "service_risk_checks_pass": risk_ok,
        "structural_checks_pass": structural_ok,
        "mc_stability_status": mc_stability_status,
        "interpretation": (
            "Joint duration sampling preserves observed pairing in the "
            "37-row procurement-process-duration sample; it does not prove "
            "statistical dependence or supplier-specific lead-time behavior."
        ),
        "test_data_used": False,
        "primary_representation": "joint_duration_primary",
    }

    (OUT_DIR / "RO2_step27d1_summary.json").write_text(
        json.dumps(summary_json, indent=2), encoding="utf-8"
    )

    caveats = [
        "27D.1 is an audit/sensitivity stage; it does not create new observations.",
        "The duration variable remains procurement-process duration, not supplier-specific lead time.",
        "Joint resampling preserves observed component pairing but does not prove dependence.",
        "Independent duration sampling is sensitivity analysis.",
        "Direct Monte Carlo stability cannot be recomputed from the saved summary CSVs because raw 10,000-draw exposure vectors were not persisted.",
        "RO2 does not establish supplier-specific disruption probabilities or historical shortage labels.",
        "Do not proceed to final RO3 optimization lock until this decision and caveats are reviewed.",
    ]
    (OUT_DIR / "RO2_step27d1_decision.txt").write_text(
        "DECISION: " + decision + "\n\n" + "\n".join("- " + x for x in caveats) + "\n",
        encoding="utf-8",
    )

    print("\nCHECKS")
    print("Distribution:", "PASS" if dist_ok else "HOLD")
    print("Service-risk monotonicity:", "PASS" if risk_ok else "HOLD")
    print("Structural contract:", "PASS" if structural_ok else "HOLD")
    print("Monte Carlo stability:", mc_stability_status)
    print("\nDECISION:", decision)
    print("\nOutputs:")
    for p in sorted(OUT_DIR.iterdir()):
        if p.is_file() and p.name.startswith("RO2_step27d1_"):
            print(" -", p)
    print("\n27D.1 audit complete.")


if __name__ == "__main__":
    main()
