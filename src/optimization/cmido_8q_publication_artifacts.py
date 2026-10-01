"""
CMIDO 8Q — Publication artifact generator.

Generates publication-ready CSV tables directly from frozen result sources.
No scientific values are hard-coded. The script also emits a manifest and
reconciliation audit so every generated table has an auditable source path.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd


def project_root() -> Path:
    override = os.getenv("CMIDO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def generate(root: Path | None = None) -> dict:
    root = (root or project_root()).resolve()
    out = root / "results/8Q_publication_artifacts"
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    artifacts = []

    def ck(name, ok, detail=""):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    fc = root / "results/RO3/ablation/final_comparison"
    pairwise = fc / "RO3_step36_statistical_pairwise_comparisons.csv"
    primary = fc / "RO3_step36_primary_ablation_results.csv"
    desc = fc / "RO3_step36_controller_descriptive_statistics.csv"

    ck("T5_pairwise_source_exists", pairwise.exists(), str(pairwise))
    ck("T6_primary_source_exists", primary.exists(), str(primary))
    ck("T5_T6_descriptive_source_exists", desc.exists(), str(desc))

    if pairwise.exists():
        df = pd.read_csv(pairwise)
        required = {
            "comparison", "contrast", "metric", "n_origins", "newer_mean",
            "base_mean", "mean_difference_newer_minus_base",
            "bootstrap_ci95_lower", "bootstrap_ci95_upper", "wilcoxon_q_bh",
        }
        ck("T5_required_columns", required <= set(df.columns))
        if required <= set(df.columns):
            t5 = df.copy()
            t5["n_origins"] = pd.to_numeric(t5["n_origins"], errors="coerce").astype("Int64")
            columns = [
                "comparison", "contrast", "metric", "n_origins", "newer_mean",
                "base_mean", "mean_difference_newer_minus_base",
                "bootstrap_ci95_lower", "bootstrap_ci95_upper", "wilcoxon_p_raw",
                "wilcoxon_q_bh", "significant_bh_0_05",
            ]
            missing_optional = [col for col in columns if col not in t5.columns]
            ck("T5_output_columns_available", not missing_optional, ", ".join(missing_optional))
            if not missing_optional:
                t5 = t5[columns]
                t5.to_csv(out / "T5_RO3_baseline_comparison.csv", index=False)
                ck("T5_exactly_five_planned_contrasts", set(t5["comparison"]) == {
                    "O2_vs_O1", "O3_vs_O1", "O4_vs_O2", "O4_vs_O3", "O4_vs_O1"
                })
                ck("T5_all_origins_equal_eleven", set(t5["n_origins"].dropna()) == {11})
                artifacts.append(("T5_RO3_baseline_comparison.csv", pairwise, "RO3_step36_statistical_pairwise_comparisons.csv"))

    if primary.exists():
        df = pd.read_csv(primary)
        required = {
            "comparison", "contrast", "metric", "n_origins", "newer_mean",
            "base_mean", "mean_difference_newer_minus_base",
            "bootstrap_ci95_lower", "bootstrap_ci95_upper", "wilcoxon_q_bh",
        }
        ck("T6_required_columns", required <= set(df.columns))
        if required <= set(df.columns):
            t6 = df.copy()
            t6.to_csv(out / "T6_RO3_ablation.csv", index=False)
            ck("T6_expected_primary_rows", len(t6) == 20, str(len(t6)))
            numeric = [
                "newer_mean", "base_mean", "mean_difference_newer_minus_base",
                "bootstrap_ci95_lower", "bootstrap_ci95_upper", "wilcoxon_q_bh",
            ]
            ck("T6_no_nan_primary_values", not t6[numeric].isna().any().any())
            artifacts.append(("T6_RO3_ablation.csv", primary, "RO3_step36_primary_ablation_results.csv"))

    if desc.exists():
        df = pd.read_csv(desc)
        ck("T5_T6_four_controllers", set(df["controller"]) == {"O1", "O2", "O3", "O4"})
        ck("T5_T6_descriptive_rows", len(df) == 4, str(len(df)))
        df.to_csv(out / "T5_T6_controller_descriptives.csv", index=False)
        artifacts.append(("T5_T6_controller_descriptives.csv", desc, "RO3_step36_controller_descriptive_statistics.csv"))


    # RO1 final validation metrics.
    ro1_dir = root / "results/forecasting/probabilistic_calibration"
    ro1_metrics = ro1_dir / "RO1_step26c3_validation_metrics.csv"
    ck("T1_RO1_validation_metrics_source_exists", ro1_metrics.exists(), str(ro1_metrics))
    if ro1_metrics.exists():
        df = pd.read_csv(ro1_metrics)
        required = {
            "dataset", "series", "horizon", "n_raw", "n_calibrated_50",
            "n_calibrated_80", "mae_q50", "rmse_q50",
            "prequential_coverage_50", "prequential_coverage_80",
            "prequential_coverage_error_50", "prequential_coverage_error_80",
            "prequential_mean_width_50", "prequential_mean_width_80",
            "prequential_winkler_50", "prequential_winkler_80",
        }
        ck("T1_RO1_required_columns", required <= set(df.columns))
        if required <= set(df.columns):
            cols = [
                "dataset", "series", "horizon", "n_raw", "n_calibrated_50",
                "n_calibrated_80", "mae_q50", "rmse_q50",
                "prequential_coverage_50", "prequential_coverage_80",
                "prequential_coverage_error_50", "prequential_coverage_error_80",
                "prequential_mean_width_50", "prequential_mean_width_80",
                "prequential_winkler_50", "prequential_winkler_80",
            ]
            t1 = df[cols].copy()
            t1.to_csv(out / "T1_RO1_validation_metrics.csv", index=False)
            ck("T1_RO1_expected_rows", len(t1) == 32, str(len(t1)))
            ck("T1_RO1_no_nan_primary_values", not t1[[
                "mae_q50", "rmse_q50", "prequential_coverage_50",
                "prequential_coverage_80", "prequential_mean_width_50",
                "prequential_mean_width_80", "prequential_winkler_50",
                "prequential_winkler_80"
            ]].isna().any().any())
            artifacts.append(("T1_RO1_validation_metrics.csv", ro1_metrics,
                              "RO1_step26c3_validation_metrics.csv"))

    # RO2 joint-component dependence and tail evidence.
    ro2_dist = root / "results/RO2/distribution"
    ro2_joint = ro2_dist / "RO2_step27c3_joint_propagation_summary.csv"
    ro2_tail = ro2_dist / "RO2_step27c3_tail_comparison.csv"
    ck("T2_RO2_joint_summary_source_exists", ro2_joint.exists(), str(ro2_joint))
    ck("T2_RO2_tail_source_exists", ro2_tail.exists(), str(ro2_tail))
    if ro2_joint.exists():
        df = pd.read_csv(ro2_joint)
        required = {
            "paired_n", "pearson_r", "pearson_p", "spearman_rho",
            "spearman_p", "spearman_bootstrap_ci_2_5",
            "spearman_bootstrap_ci_97_5", "q95_independent_minus_joint_days",
            "q95_independent_vs_joint_pct", "q99_independent_minus_joint_days",
            "q99_independent_vs_joint_pct", "decision",
        }
        ck("T2_RO2_joint_required_columns", required <= set(df.columns))
        if required <= set(df.columns):
            df.to_csv(out / "T2_RO2_joint_propagation_summary.csv", index=False)
            ck("T2_RO2_joint_single_summary_row", len(df) == 1, str(len(df)))
            artifacts.append(("T2_RO2_joint_propagation_summary.csv", ro2_joint,
                              "RO2_step27c3_joint_propagation_summary.csv"))
    if ro2_tail.exists():
        df = pd.read_csv(ro2_tail)
        required = {"quantile", "representation", "quantile_days",
                    "difference_vs_observed", "relative_difference_pct"}
        ck("T2_RO2_tail_required_columns", required <= set(df.columns))
        if required <= set(df.columns):
            t2_tail = df.copy()
            t2_tail.to_csv(out / "T2_RO2_tail_comparison.csv", index=False)
            ck("T2_RO2_tail_expected_rows", len(t2_tail) == 15, str(len(t2_tail)))
            artifacts.append(("T2_RO2_tail_comparison.csv", ro2_tail,
                              "RO2_step27c3_tail_comparison.csv"))

    # RO2 demand/propagation evidence.
    ro2_prop = root / "results/RO2/propagation"
    ro2_summary = ro2_prop / "RO2_step27d_propagation_summary.csv"
    ro2_risk = ro2_prop / "RO2_step27d_service_risk_curve.csv"
    ro2_sens = ro2_prop / "RO2_step27d_joint_vs_independent_sensitivity.csv"
    ck("T3_RO2_propagation_summary_source_exists", ro2_summary.exists(), str(ro2_summary))
    ck("T3_RO2_service_risk_source_exists", ro2_risk.exists(), str(ro2_risk))
    ck("T3_RO2_joint_independent_sensitivity_source_exists", ro2_sens.exists(), str(ro2_sens))
    if ro2_summary.exists():
        df = pd.read_csv(ro2_summary)
        required = {
            "material", "forecast_origin", "representation", "mc_n",
            "mean_demand_during_duration", "median_demand_during_duration",
            "q50", "q75", "q90", "q95", "q99", "mc_se_mean", "min", "max"
        }
        ck("T3_RO2_propagation_required_columns", required <= set(df.columns))
        if required <= set(df.columns):
            t3 = df[df["representation"].isin(
                ["joint_duration_primary", "independent_duration_sensitivity"]
            )].copy()
            t3.to_csv(out / "T3_RO2_propagation_summary.csv", index=False)
            ck("T3_RO2_propagation_expected_rows", len(t3) == 96, str(len(t3)))
            ck("T3_RO2_propagation_two_representations",
               set(t3["representation"]) == {
                   "joint_duration_primary", "independent_duration_sensitivity"
               })
            artifacts.append(("T3_RO2_propagation_summary.csv", ro2_summary,
                              "RO2_step27d_propagation_summary.csv"))
    if ro2_risk.exists():
        df = pd.read_csv(ro2_risk)
        ck("T3_RO2_service_risk_nonempty", not df.empty, str(len(df)))
        if not df.empty:
            df.to_csv(out / "T3_RO2_service_risk_curve.csv", index=False)
            artifacts.append(("T3_RO2_service_risk_curve.csv", ro2_risk,
                              "RO2_step27d_service_risk_curve.csv"))
    if ro2_sens.exists():
        df = pd.read_csv(ro2_sens)
        required = {
            "material", "forecast_origin", "quantile",
            "joint_quantile_days", "independent_quantile_days",
        }
        ck("T3_RO2_sensitivity_required_columns", required <= set(df.columns))
        if required <= set(df.columns):
            df.to_csv(out / "T3_RO2_joint_independent_sensitivity.csv", index=False)
            artifacts.append(("T3_RO2_joint_independent_sensitivity.csv", ro2_sens,
                              "RO2_step27d_joint_vs_independent_sensitivity.csv"))

    manifest = {
        "stage": "8Q",
        "status": "PASS" if checks and all(x["passed"] for x in checks) else "HOLD",
        "root": str(root),
        "artifacts": [
            {
                "artifact": artifact,
                "source_path": str(source.relative_to(root)),
                "source_sha256": sha256(source),
                "source_name": source_name,
                "generation_script": "src/optimization/cmido_8q_publication_artifacts.py",
            }
            for artifact, source, source_name in artifacts
        ],
        "checks_passed": sum(x["passed"] for x in checks),
        "checks_total": len(checks),
    }
    (out / "CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    pd.DataFrame(checks).to_csv(out / "CMIDO_8Q_PUBLICATION_ARTIFACT_AUDIT.csv", index=False)
    return manifest, checks


def main() -> int:
    manifest, checks = generate()
    print("=" * 78)
    print("CMIDO 8Q — PUBLICATION ARTIFACT GENERATOR")
    print("=" * 78)
    for row in checks:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = f" — {row['detail']}" if row["detail"] else ""
        print(f"[{marker}] {row['check']}{suffix}")
    print("=" * 78)
    print(f"STATUS: {manifest['status']} ({manifest['checks_passed']}/{manifest['checks_total']})")
    print(f"OUTPUT: {manifest['root']}/results/8Q_publication_artifacts")
    print("=" * 78)
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
