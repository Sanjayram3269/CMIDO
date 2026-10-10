"""CMIDO 10A.2-B — Central Artifact Registry.

One authoritative catalogue of every research artifact that the
dashboard may consume.  No hard-coded result paths should appear
elsewhere in the Streamlit application.

Only REAL files or explicitly optional future slots are registered.
Artifact IDs that do not correspond to existing repository files are
marked ``required=False``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


# ------------------------------------------------------------------
# Artifact type taxonomy
# ------------------------------------------------------------------

class ArtifactType(str, Enum):
    """File-level artifact taxonomy."""
    CSV = "CSV"
    JSON = "JSON"
    TEXT = "TEXT"
    PNG = "PNG"


# ------------------------------------------------------------------
# Research component
# ------------------------------------------------------------------

class ResearchComponent(str, Enum):
    """Which research objective / stage produced this artifact."""
    RO1 = "RO1"
    RO2 = "RO2"
    RO3 = "RO3"
    ABLATION = "ABLATION"
    REAL_DATA = "REAL_DATA"
    PUBLICATION = "PUBLICATION"
    RECONCILIATION = "RECONCILIATION"
    GATE = "GATE"


# ------------------------------------------------------------------
# Loading policy
# ------------------------------------------------------------------

class LoadingPolicy(str, Enum):
    """Whether an artifact is safe for dashboard ingestion."""
    SAFE = "SAFE"               # summary / curated — load normally
    METADATA_ONLY = "METADATA"  # small JSON metadata — load normally
    HEADER_ONLY = "HEADER"      # read only header + row-count
    NEVER = "NEVER"             # too large — never auto-load


# ------------------------------------------------------------------
# Single registry entry
# ------------------------------------------------------------------

@dataclass(frozen=True)
class ArtifactEntry:
    """Describes one dashboard-relevant research artifact."""
    artifact_id: str
    name: str
    component: ResearchComponent
    relative_path: str
    artifact_type: ArtifactType
    loading_policy: LoadingPolicy
    required: bool
    description: str
    expected_columns: tuple[str, ...] = ()
    provenance_class: str = ""
    evidence_role: str = ""
    max_safe_bytes: int = 5_000_000  # 5 MB default safety cap


# ------------------------------------------------------------------
# The Registry
# ------------------------------------------------------------------

# fmt: off
ARTIFACT_REGISTRY: tuple[ArtifactEntry, ...] = (

    # ── RO1 — Forecasting ─────────────────────────────────────────
    ArtifactEntry(
        artifact_id="RO1_VALIDATION_METRICS",
        name="RO1 Validation Metrics (publication T1)",
        component=ResearchComponent.RO1,
        relative_path="results/8Q_publication_artifacts/T1_RO1_validation_metrics.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=True,
        description="Per-series per-horizon probabilistic forecast validation metrics.",
        expected_columns=(
            "dataset", "series", "horizon",
            "mae_q50", "rmse_q50",
            "prequential_coverage_50", "prequential_coverage_80",
            "prequential_winkler_50", "prequential_winkler_80",
        ),
        provenance_class="DER",
        evidence_role="RO1 forecasting performance evidence",
    ),
    ArtifactEntry(
        artifact_id="RO1_VALIDATION_FORECASTS",
        name="RO1 Validation Forecasts (probabilistic)",
        component=ResearchComponent.RO1,
        relative_path="results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Per-origin probabilistic forecast quantiles, prediction intervals and calibration flags.",
        expected_columns=(
            "dataset", "series", "horizon", "forecast_origin", "target_date",
            "actual", "q10", "q25", "q50", "q75", "q90",
            "raw_lower_50", "raw_upper_50", "raw_lower_80", "raw_upper_80",
            "calibrated_lower_50", "calibrated_upper_50",
            "calibrated_lower_80", "calibrated_upper_80",
            "calibration_available_50", "calibration_available_80",
        ),
        provenance_class="EST",
        evidence_role="RO1 probabilistic forecast evidence",
        max_safe_bytes=500_000,
    ),
    ArtifactEntry(
        artifact_id="RO1_CALIBRATION_SCORES",
        name="RO1 Calibration Scores",
        component=ResearchComponent.RO1,
        relative_path="results/forecasting/probabilistic_calibration/RO1_step26c3_calibration_scores.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Per-origin calibration scores for probabilistic forecasts.",
        expected_columns=(),
        provenance_class="DER",
        evidence_role="RO1 calibration evidence",
        max_safe_bytes=200_000,
    ),
    ArtifactEntry(
        artifact_id="RO1_PRIMARY_H3_SUMMARY",
        name="RO1 Primary h=3 Summary",
        component=ResearchComponent.RO1,
        relative_path="results/forecasting/probabilistic_calibration/RO1_step26c3_primary_h3_summary.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Primary horizon-3 calibration summary.",
        provenance_class="DER",
        evidence_role="RO1 primary calibration",
    ),
    ArtifactEntry(
        artifact_id="RO1_PAIRED_BOOTSTRAP",
        name="RO1 Paired Bootstrap Results",
        component=ResearchComponent.RO1,
        relative_path="results/forecasting/probabilistic_calibration/analysis_26c3f/RO1_step26c3f_paired_bootstrap_results.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Paired bootstrap statistical comparison of probabilistic methods.",
        provenance_class="EST",
        evidence_role="RO1 statistical evidence",
    ),
    ArtifactEntry(
        artifact_id="RO1_FINAL_INTEGRITY",
        name="RO1 Final Integrity Audit",
        component=ResearchComponent.RO1,
        relative_path="results/forecasting/final_probabilistic_comparison/RO1_step26c3h_final_integrity_audit.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Final RO1 integrity audit (pass/fail gate).",
        provenance_class="DER",
        evidence_role="RO1 integrity gate",
    ),

    ArtifactEntry(
        artifact_id="RO1_TEST_METRICS",
        name="RO1 Held-Out Test-Split Probabilistic Metrics",
        component=ResearchComponent.RO1,
        relative_path="results/forecasting/probabilistic_calibration/RO1_step26c3_test_metrics.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Held-out test-split point, pinball, coverage, width and Winkler scores (raw vs CQR).",
        expected_columns=(
            "dataset", "series", "horizon", "n_test",
            "pinball_q10", "pinball_q25", "pinball_q50", "pinball_q75", "pinball_q90",
        ),
        provenance_class="DER",
        evidence_role="RO1 test-split probabilistic score evidence",
        max_safe_bytes=200_000,
    ),
    ArtifactEntry(
        artifact_id="RO1_BASELINE_METRICS",
        name="RO1 Naive Baseline Test Metrics",
        component=ResearchComponent.RO1,
        relative_path="results/forecasting/baselines/RO1_step23_test_metrics.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Naive / SeasonalNaive test-split point metrics including sMAPE and MAPE.",
        expected_columns=(
            "dataset", "split", "series", "horizon", "model", "n_forecasts",
            "MAE", "RMSE", "sMAPE_percent", "MAPE_percent",
        ),
        provenance_class="DER",
        evidence_role="RO1 baseline sMAPE evidence",
        max_safe_bytes=200_000,
    ),

    # ── RO2 — Uncertainty ─────────────────────────────────────────
    ArtifactEntry(
        artifact_id="RO2_JOINT_PROPAGATION",
        name="RO2 Joint Propagation Summary (publication T2)",
        component=ResearchComponent.RO2,
        relative_path="results/8Q_publication_artifacts/T2_RO2_joint_propagation_summary.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=True,
        description="Joint uncertainty-propagation summary table.",
        expected_columns=(
            "input_rows", "paired_n",
            "pearson_r", "spearman_rho",
            "independence_assumption_supported",
            "decision",
        ),
        provenance_class="DER",
        evidence_role="RO2 joint propagation evidence",
    ),
    ArtifactEntry(
        artifact_id="RO2_TAIL_COMPARISON",
        name="RO2 Tail Comparison (publication T2)",
        component=ResearchComponent.RO2,
        relative_path="results/8Q_publication_artifacts/T2_RO2_tail_comparison.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=True,
        description="Joint vs independent tail quantile comparison.",
        provenance_class="DER",
        evidence_role="RO2 tail comparison evidence",
    ),
    ArtifactEntry(
        artifact_id="RO2_SERVICE_RISK",
        name="RO2 Service-Risk Curve (publication T3)",
        component=ResearchComponent.RO2,
        relative_path="results/8Q_publication_artifacts/T3_RO2_service_risk_curve.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Service-level vs shortage-risk curve from propagation.",
        provenance_class="SCN",
        evidence_role="RO2 service risk",
    ),
    ArtifactEntry(
        artifact_id="RO2_SENSITIVITY",
        name="RO2 Joint-Independent Sensitivity (publication T3)",
        component=ResearchComponent.RO2,
        relative_path="results/8Q_publication_artifacts/T3_RO2_joint_independent_sensitivity.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Joint vs independent sensitivity analysis.",
        provenance_class="SCN",
        evidence_role="RO2 sensitivity evidence",
    ),
    ArtifactEntry(
        artifact_id="RO2_PROPAGATION_CONFIG",
        name="RO2 Propagation Run Configuration (27D)",
        component=ResearchComponent.RO2,
        relative_path="results/RO2/propagation/RO2_step27d_run_config.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Step 27D run configuration: seed, Monte Carlo draws, duration-pair count, materials and horizons.",
        provenance_class="DER",
        evidence_role="RO2 propagation run configuration",
        max_safe_bytes=100_000,
    ),
    ArtifactEntry(
        artifact_id="RO2_PROPAGATION_SUMMARY",
        name="RO2 Demand-During-Duration Propagation Summary (27D)",
        component=ResearchComponent.RO2,
        relative_path="results/RO2/propagation/RO2_step27d_propagation_summary.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Per material/origin demand-during-duration quantiles under joint and independent duration representations.",
        expected_columns=(
            "material", "forecast_origin", "representation", "mc_n",
            "mean_demand_during_duration", "median_demand_during_duration",
            "q50", "q75", "q90", "q95", "q99",
        ),
        provenance_class="DER",
        evidence_role="RO2 demand-during-duration quantile evidence",
        max_safe_bytes=500_000,
    ),
    ArtifactEntry(
        artifact_id="RO2_DISTRIBUTION_DECISION",
        name="RO2 Provisional Distribution Selection Decision (27C.2)",
        component=ResearchComponent.RO2,
        relative_path="results/RO2/distribution_selection/RO2_step27c2_provisional_distribution_decision.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Empirical versus parametric selection decision per duration component (IS80 scoring).",
        expected_columns=(
            "variable", "recommended_status", "empirical_IS80",
            "best_parametric_candidate", "best_parametric_IS80",
        ),
        provenance_class="DER",
        evidence_role="RO2 duration-distribution selection evidence",
        max_safe_bytes=100_000,
    ),
    ArtifactEntry(
        artifact_id="RO2_DURATION_OBSERVED_STATS",
        name="RO2 Observed Procurement-Process Duration Statistics (27B)",
        component=ResearchComponent.RO2,
        relative_path="results/RO2/data_audit/RO2_step27b_leadtime_distribution.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Observed SLA/duration column statistics from procurement source records (procurement-process duration, not supplier-specific lead time).",
        expected_columns=(
            "sheet", "leadtime_column", "n_source_rows", "n_numeric",
            "n_missing_or_unparseable", "median", "mean", "q05", "q95", "max",
        ),
        provenance_class="OBS",
        evidence_role="RO2 observed duration-distribution evidence",
        max_safe_bytes=100_000,
    ),
    ArtifactEntry(
        artifact_id="RO2_PROPAGATION_AUDIT",
        name="RO2 Propagation Audit Summary (27D.1)",
        component=ResearchComponent.RO2,
        relative_path="results/RO2/propagation_audit/RO2_step27d1_summary.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Structural, distribution and service-risk audit result gating the joint-propagation claim.",
        provenance_class="DER",
        evidence_role="RO2 propagation audit gate",
        max_safe_bytes=100_000,
    ),
    ArtifactEntry(
        artifact_id="RO2_CONVERGENCE_SUMMARY",
        name="RO2 Nested Convergence Summary (27D.4)",
        component=ResearchComponent.RO2,
        relative_path="results/RO2/propagation_convergence_nested/RO2_step27d4_summary.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Nested common-random-number convergence evidence supporting the Monte Carlo draw lock.",
        provenance_class="DER",
        evidence_role="RO2 Monte Carlo convergence evidence",
        max_safe_bytes=100_000,
    ),
    ArtifactEntry(
        artifact_id="RO2_FINAL_AUDIT",
        name="RO2 Final Audit Summary",
        component=ResearchComponent.RO2,
        relative_path="results/RO2/final_audit/RO2_FINAL_AUDIT_SUMMARY.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="RO2 final audit / lock gate result.",
        provenance_class="DER",
        evidence_role="RO2 integrity gate",
    ),

    # ── RO3 — Optimization ────────────────────────────────────────
    ArtifactEntry(
        artifact_id="RO3_BASELINE_COMPARISON",
        name="RO3 Baseline Comparison (publication T5)",
        component=ResearchComponent.RO3,
        relative_path="results/8Q_publication_artifacts/T5_RO3_baseline_comparison.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=True,
        description="Controller pairwise comparison: cost, shortage, service.",
        expected_columns=(
            "comparison", "contrast", "metric",
            "newer_mean", "base_mean", "mean_difference_newer_minus_base",
            "bootstrap_ci95_lower", "bootstrap_ci95_upper",
            "wilcoxon_p_raw", "significant_bh_0_05",
        ),
        provenance_class="EST",
        evidence_role="RO3 optimisation evidence",
    ),
    ArtifactEntry(
        artifact_id="RO3_ABLATION",
        name="RO3 Ablation (publication T6)",
        component=ResearchComponent.RO3,
        relative_path="results/8Q_publication_artifacts/T6_RO3_ablation.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=True,
        description="Ablation study: incremental value of each component.",
        expected_columns=(
            "comparison", "contrast", "metric",
            "relative_mean_difference",
            "significant_bh_0_05",
        ),
        provenance_class="EST",
        evidence_role="RO3 ablation evidence",
    ),
    ArtifactEntry(
        artifact_id="RO3_CONTROLLER_DESCRIPTIVES",
        name="RO3 Controller Descriptives (publication T5/T6)",
        component=ResearchComponent.RO3,
        relative_path="results/8Q_publication_artifacts/T5_T6_controller_descriptives.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Descriptive statistics per controller across origins.",
        provenance_class="DER",
        evidence_role="RO3 controller summary",
    ),
    ArtifactEntry(
        artifact_id="RO3_STRESS_SUMMARY",
        name="RO3 Stress Test Summary",
        component=ResearchComponent.RO3,
        relative_path="results/RO3/ablation/RO3_7_stress/RO3_step37_stress_summary.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Stress-test summary across factor perturbations.",
        provenance_class="SCN",
        evidence_role="RO3 stress testing",
    ),
    ArtifactEntry(
        artifact_id="RO3_ROBUSTNESS_SUMMARY",
        name="RO3 Robustness Holding-Rate Summary",
        component=ResearchComponent.RO3,
        relative_path="results/RO3/ablation/RO3_8_robustness/RO3_step38_holding_rate_summary.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Robustness analysis: holding-rate sensitivity summary.",
        provenance_class="SCN",
        evidence_role="RO3 robustness evidence",
    ),
    ArtifactEntry(
        artifact_id="RO3_CONVERGENCE_SUMMARY",
        name="RO3 Convergence Summary",
        component=ResearchComponent.RO3,
        relative_path="results/RO3/scenario_convergence/RO3_step33_summary.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Scenario-count convergence summary for optimisation.",
        provenance_class="DER",
        evidence_role="RO3 convergence evidence",
    ),
    ArtifactEntry(
        artifact_id="RO3_FINAL_AUDIT",
        name="RO3 Final Experimental Integrity Audit",
        component=ResearchComponent.RO3,
        relative_path="results/RO3/ablation/RO3_9_final_audit/RO3_step39_final_experimental_integrity_audit.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Final RO3 experimental integrity gate checks.",
        provenance_class="DER",
        evidence_role="RO3 integrity gate",
    ),

    # ── Large raw scenario files — NEVER load ─────────────────────
    ArtifactEntry(
        artifact_id="RO3_SCENARIOS_2500_RAW",
        name="RO3 Raw Scenarios N=2500 (BLOCKED)",
        component=ResearchComponent.RO3,
        relative_path="results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.NEVER,
        required=False,
        description="RAW scenario ledger ~161 MB. NEVER auto-load in dashboard.",
        provenance_class="SCN",
        evidence_role="raw experiment ledger",
        max_safe_bytes=0,
    ),
    ArtifactEntry(
        artifact_id="RO3_SCENARIOS_5000_RAW",
        name="RO3 Raw Scenarios N=5000 (BLOCKED)",
        component=ResearchComponent.RO3,
        relative_path="results/RO3/scenario_generation/RO3_step32_scenarios_5000.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.NEVER,
        required=False,
        description="RAW scenario ledger ~323 MB. NEVER auto-load in dashboard.",
        provenance_class="SCN",
        evidence_role="raw experiment ledger",
        max_safe_bytes=0,
    ),

    # ── Real-Data Evidence ────────────────────────────────────────
    ArtifactEntry(
        artifact_id="REAL_9A_CANONICAL",
        name="9A Canonical Real-Data Dataset",
        component=ResearchComponent.REAL_DATA,
        relative_path="results/9A_real_data_generalization/CMIDO_9A_CANONICAL_DATASET.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Canonical SUCCESS-derived real-data fixture.",
        provenance_class="OBS",
        evidence_role="real-data generalization",
    ),
    ArtifactEntry(
        artifact_id="REAL_9A_INGESTION_AUDIT",
        name="9A Ingestion Audit",
        component=ResearchComponent.REAL_DATA,
        relative_path="results/9A_real_data_generalization/CMIDO_9A_INGESTION_AUDIT.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Audit of SUCCESS data ingestion.",
        provenance_class="DER",
        evidence_role="real-data ingestion quality",
    ),
    ArtifactEntry(
        artifact_id="REAL_9A_MANIFEST",
        name="9A Generalization Manifest",
        component=ResearchComponent.REAL_DATA,
        relative_path="results/9A_real_data_generalization/CMIDO_9A_REAL_DATA_GENERALIZATION_MANIFEST.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="9A real-data generalization gate manifest.",
        provenance_class="DER",
        evidence_role="9A gate result",
    ),
    ArtifactEntry(
        artifact_id="REAL_9B_PSLIB_AUDIT",
        name="9B PSLIB Audit",
        component=ResearchComponent.REAL_DATA,
        relative_path="results/9B_real_project_e2e/CMIDO_9B_PSLIB_AUDIT.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="PSLIB project-data audit.",
        provenance_class="OBS",
        evidence_role="PSLIB data quality",
    ),
    ArtifactEntry(
        artifact_id="REAL_9B_MANIFEST",
        name="9B Real Project E2E Manifest",
        component=ResearchComponent.REAL_DATA,
        relative_path="results/9B_real_project_e2e/CMIDO_9B_REAL_PROJECT_E2E_MANIFEST.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="9B real-project end-to-end gate manifest.",
        provenance_class="DER",
        evidence_role="9B gate result",
    ),

    # ── Publication / Reconciliation ──────────────────────────────
    ArtifactEntry(
        artifact_id="EVIDENCE_8Q_MANIFEST",
        name="8Q Publication Artifact Manifest",
        component=ResearchComponent.PUBLICATION,
        relative_path="results/8Q_publication_artifacts/CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Publication-artifact gate manifest.",
        provenance_class="DER",
        evidence_role="publication readiness",
    ),
    ArtifactEntry(
        artifact_id="EVIDENCE_8R_CONCORDANCE",
        name="8R Figure Concordance",
        component=ResearchComponent.PUBLICATION,
        relative_path="results/8R_publication_figures/CMIDO_8R_FIGURE_CONCORDANCE.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Figure-to-table concordance mapping.",
        provenance_class="DER",
        evidence_role="figure traceability",
    ),
    ArtifactEntry(
        artifact_id="EVIDENCE_8S_RECONCILIATION",
        name="8S Numerical Reconciliation Audit",
        component=ResearchComponent.RECONCILIATION,
        relative_path="results/8S_numerical_reconciliation/CMIDO_8S_RECONCILIATION_AUDIT.csv",
        artifact_type=ArtifactType.CSV,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Numerical reconciliation between pipeline stages.",
        expected_columns=("check", "passed", "detail"),
        provenance_class="DER",
        evidence_role="numerical integrity",
    ),
    ArtifactEntry(
        artifact_id="EVIDENCE_8P_MANIFEST",
        name="8P Dashboard E2E Manifest",
        component=ResearchComponent.GATE,
        relative_path="results/8P_dashboard_e2e/CMIDO_8P_DASHBOARD_E2E_MANIFEST.json",
        artifact_type=ArtifactType.JSON,
        loading_policy=LoadingPolicy.SAFE,
        required=False,
        description="Dashboard end-to-end gate manifest.",
        provenance_class="DER",
        evidence_role="dashboard gate",
    ),
)
# fmt: on


# ------------------------------------------------------------------
# Lookup helpers
# ------------------------------------------------------------------

def get_entry(artifact_id: str) -> ArtifactEntry | None:
    """Return the registry entry for *artifact_id*, or ``None``."""
    for entry in ARTIFACT_REGISTRY:
        if entry.artifact_id == artifact_id:
            return entry
    return None


def get_required_ids() -> list[str]:
    """Return IDs of all required artifacts."""
    return [e.artifact_id for e in ARTIFACT_REGISTRY if e.required]


def get_safe_ids() -> list[str]:
    """Return IDs of all artifacts whose loading policy is SAFE."""
    return [
        e.artifact_id
        for e in ARTIFACT_REGISTRY
        if e.loading_policy == LoadingPolicy.SAFE
    ]


def get_blocked_ids() -> list[str]:
    """Return IDs of all artifacts blocked from loading."""
    return [
        e.artifact_id
        for e in ARTIFACT_REGISTRY
        if e.loading_policy == LoadingPolicy.NEVER
    ]
