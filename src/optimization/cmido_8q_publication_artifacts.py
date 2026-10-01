"""CMIDO 8Q publication artifact generator.

All publication tables are copied/selected from frozen source artifacts.
No scientific values are recomputed or fabricated here.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pandas as pd


def project_root() -> Path:
    override = os.getenv("CMIDO_ROOT")
    return Path(override).expanduser().resolve() if override else Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def generate(root: Path | None = None):
    root = (root or project_root()).resolve()
    out = root / "results/8Q_publication_artifacts"
    out.mkdir(parents=True, exist_ok=True)
    checks, artifacts = [], []

    def ck(name, ok, detail=""):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    def copy_source(name, source, required=None):
        ck(f"{name}_source_exists", source.exists(), str(source))
        if not source.exists():
            return None
        df = pd.read_csv(source)
        if required:
            ck(f"{name}_required_columns", required <= set(df.columns))
            if not required <= set(df.columns):
                return None
        return df

    fc = root / "results/RO3/ablation/final_comparison"
    pairwise = copy_source("T5_pairwise", fc / "RO3_step36_statistical_pairwise_comparisons.csv", {
        "comparison","contrast","metric","n_origins","newer_mean","base_mean",
        "mean_difference_newer_minus_base","bootstrap_ci95_lower","bootstrap_ci95_upper",
        "wilcoxon_q_bh"
    })
    if pairwise is not None:
        cols = ["comparison","contrast","metric","n_origins","newer_mean","base_mean",
                "mean_difference_newer_minus_base","bootstrap_ci95_lower","bootstrap_ci95_upper",
                "wilcoxon_p_raw","wilcoxon_q_bh","significant_bh_0_05"]
        missing = [c for c in cols if c not in pairwise.columns]
        ck("T5_output_columns_available", not missing, ", ".join(missing))
        if not missing:
            t5 = pairwise[cols].copy()
            t5["n_origins"] = pd.to_numeric(t5["n_origins"], errors="coerce").astype("Int64")
            t5.to_csv(out / "T5_RO3_baseline_comparison.csv", index=False)
            ck("T5_exactly_five_planned_contrasts", set(t5.comparison) == {"O2_vs_O1","O3_vs_O1","O4_vs_O2","O4_vs_O3","O4_vs_O1"})
            ck("T5_all_origins_equal_eleven", set(t5.n_origins.dropna()) == {11})
            artifacts.append(("T5_RO3_baseline_comparison.csv", fc / "RO3_step36_statistical_pairwise_comparisons.csv", "RO3_step36_statistical_pairwise_comparisons.csv"))

    primary_path = fc / "RO3_step36_primary_ablation_results.csv"
    primary = copy_source("T6_primary", primary_path, {"comparison","contrast","metric","n_origins","newer_mean","base_mean","mean_difference_newer_minus_base","bootstrap_ci95_lower","bootstrap_ci95_upper","wilcoxon_q_bh"})
    if primary is not None:
        primary.to_csv(out / "T6_RO3_ablation.csv", index=False)
        ck("T6_expected_primary_rows", len(primary) == 20, str(len(primary)))
        nums = ["newer_mean","base_mean","mean_difference_newer_minus_base","bootstrap_ci95_lower","bootstrap_ci95_upper","wilcoxon_q_bh"]
        ck("T6_no_nan_primary_values", not primary[nums].isna().any().any())
        artifacts.append(("T6_RO3_ablation.csv", primary_path, "RO3_step36_primary_ablation_results.csv"))

    desc_path = fc / "RO3_step36_controller_descriptive_statistics.csv"
    desc = copy_source("T5_T6_descriptive", desc_path)
    if desc is not None:
        ck("T5_T6_four_controllers", set(desc.controller) == {"O1","O2","O3","O4"})
        ck("T5_T6_descriptive_rows", len(desc) == 4, str(len(desc)))
        desc.to_csv(out / "T5_T6_controller_descriptives.csv", index=False)
        artifacts.append(("T5_T6_controller_descriptives.csv", desc_path, "RO3_step36_controller_descriptive_statistics.csv"))

    ro1_path = root / "results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv"
    ro1 = copy_source("T1_RO1_validation_metrics", ro1_path, {
        "dataset","series","horizon","n_raw","n_calibrated_50","n_calibrated_80","mae_q50","rmse_q50",
        "prequential_coverage_50","prequential_coverage_80","prequential_coverage_error_50","prequential_coverage_error_80",
        "prequential_mean_width_50","prequential_mean_width_80","prequential_winkler_50","prequential_winkler_80"
    })
    if ro1 is not None:
        cols = ["dataset","series","horizon","n_raw","n_calibrated_50","n_calibrated_80","mae_q50","rmse_q50",
                "prequential_coverage_50","prequential_coverage_80","prequential_coverage_error_50","prequential_coverage_error_80",
                "prequential_mean_width_50","prequential_mean_width_80","prequential_winkler_50","prequential_winkler_80"]
        t1 = ro1[cols].copy()
        t1.to_csv(out / "T1_RO1_validation_metrics.csv", index=False)
        ck("T1_RO1_expected_rows", len(t1) == 36, str(len(t1)))
        ck("T1_RO1_no_nan_primary_values", not t1[["mae_q50","rmse_q50","prequential_coverage_50","prequential_coverage_80","prequential_mean_width_50","prequential_mean_width_80","prequential_winkler_50","prequential_winkler_80"]].isna().any().any())
        artifacts.append(("T1_RO1_validation_metrics.csv", ro1_path, "RO1_step26c3_validation_metrics.csv"))

    dist = root / "results/RO2/distribution"
    joint_path = dist / "RO2_step27c3_joint_propagation_summary.csv"
    joint = copy_source("T2_RO2_joint_summary", joint_path, {"paired_n","pearson_r","pearson_p","spearman_rho","spearman_p","spearman_bootstrap_ci_2_5","spearman_bootstrap_ci_97_5","q95_independent_minus_joint_days","q95_independent_vs_joint_pct","q99_independent_minus_joint_days","q99_independent_vs_joint_pct","decision"})
    if joint is not None:
        joint.to_csv(out / "T2_RO2_joint_propagation_summary.csv", index=False)
        ck("T2_RO2_joint_single_summary_row", len(joint) == 1, str(len(joint)))
        artifacts.append(("T2_RO2_joint_propagation_summary.csv", joint_path, "RO2_step27c3_joint_propagation_summary.csv"))

    tail_path = dist / "RO2_step27c3_tail_comparison.csv"
    tail = copy_source("T2_RO2_tail", tail_path, {"quantile","representation","quantile_days","difference_vs_observed","relative_difference_pct"})
    if tail is not None:
        tail.to_csv(out / "T2_RO2_tail_comparison.csv", index=False)
        ck("T2_RO2_tail_expected_rows", len(tail) == 15, str(len(tail)))
        artifacts.append(("T2_RO2_tail_comparison.csv", tail_path, "RO2_step27c3_tail_comparison.csv"))

    prop = root / "results/RO2/propagation"
    prop_path = prop / "RO2_step27d_propagation_summary.csv"
    prop_df = copy_source("T3_RO2_propagation_summary", prop_path, {"material","forecast_origin","representation","mc_n","mean_demand_during_duration","median_demand_during_duration","q50","q75","q90","q95","q99","mc_se_mean","min","max"})
    if prop_df is not None:
        t3 = prop_df[prop_df.representation.isin(["joint_duration_primary","independent_duration_sensitivity"])].copy()
        t3.to_csv(out / "T3_RO2_propagation_summary.csv", index=False)
        ck("T3_RO2_propagation_expected_rows", len(t3) == 96, str(len(t3)))
        ck("T3_RO2_propagation_two_representations", set(t3.representation) == {"joint_duration_primary","independent_duration_sensitivity"})
        artifacts.append(("T3_RO2_propagation_summary.csv", prop_path, "RO2_step27d_propagation_summary.csv"))

    risk_path = prop / "RO2_step27d_service_risk_curve.csv"
    risk = copy_source("T3_RO2_service_risk", risk_path)
    if risk is not None:
        ck("T3_RO2_service_risk_nonempty", not risk.empty, str(len(risk)))
        if not risk.empty:
            risk.to_csv(out / "T3_RO2_service_risk_curve.csv", index=False)
            artifacts.append(("T3_RO2_service_risk_curve.csv", risk_path, "RO2_step27d_service_risk_curve.csv"))

    sens_path = prop / "RO2_step27d_joint_vs_independent_sensitivity.csv"
    sens = copy_source("T3_RO2_sensitivity", sens_path, {"material","forecast_origin","quantile","joint_duration_days_q50_q99_distribution","independent_duration_sensitivity","independent_minus_joint","independent_vs_joint_pct"})
    if sens is not None:
        sens.to_csv(out / "T3_RO2_joint_independent_sensitivity.csv", index=False)
        ck("T3_RO2_sensitivity_expected_rows", len(sens) == 240, str(len(sens)))
        artifacts.append(("T3_RO2_joint_independent_sensitivity.csv", sens_path, "RO2_step27d_joint_vs_independent_sensitivity.csv"))

    manifest = {
        "stage":"8Q", "status":"PASS" if checks and all(x["passed"] for x in checks) else "HOLD",
        "root":str(root), "checks_passed":sum(x["passed"] for x in checks), "checks_total":len(checks),
        "artifacts":[{"artifact":a,"source_path":str(s.relative_to(root)),"source_sha256":sha256(s),"source_name":n,"generation_script":"src/optimization/cmido_8q_publication_artifacts.py"} for a,s,n in artifacts]
    }
    (out / "CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
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
