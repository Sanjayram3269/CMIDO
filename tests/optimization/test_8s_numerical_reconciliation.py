from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_8s_reconciliation_contract():
    text = (ROOT / "src/optimization/cmido_8s_numerical_reconciliation.py").read_text(encoding="utf-8")
    required = [
        "CMIDO 8S",
        "CMIDO_8S_RECONCILIATION_MANIFEST.json",
        "CMIDO_8S_RECONCILIATION_AUDIT.csv",
        "T1_RO1_validation_metrics.csv",
        "T3_RO2_joint_independent_sensitivity.csv",
        "T4_RO3_stress_robustness.csv",
        "combine_t4_sources",
        "manifest_secondary_hash_match",
        "T5_T6_controller_descriptives.csv",
        "T6_RO3_ablation.csv",
        "same_frame",
        "source_sha256",
    ]
    for element in required:
        assert element in text


def test_8s_required_frozen_sources_exist():
    q = ROOT / "results" / "8Q_publication_artifacts"
    required = [
        "CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json",
        "T1_RO1_validation_metrics.csv",
        "T2_RO2_joint_propagation_summary.csv",
        "T2_RO2_tail_comparison.csv",
        "T3_RO2_propagation_summary.csv",
        "T3_RO2_service_risk_curve.csv",
        "T3_RO2_joint_independent_sensitivity.csv",
        "T4_RO3_stress_robustness.csv",
        "T5_T6_controller_descriptives.csv",
        "T6_RO3_ablation.csv",
    ]
    missing = [x for x in required if not (q / x).exists()]
    assert not missing, f"Missing frozen 8Q sources: {missing}"


def test_8s_t4_dual_upstream_reconciliation():
    """T4 must reconcile against BOTH frozen upstreams (RO3.7 and RO3.8)."""
    from src.optimization.cmido_8s_numerical_reconciliation import SPECS, generate

    spec, rows = SPECS["T4_RO3_stress_robustness.csv"]
    assert isinstance(spec, tuple) and len(spec) == 2
    assert spec[0].endswith("RO3_step37_stress_summary.csv")
    assert spec[1].endswith("RO3_step38_holding_rate_summary.csv")
    assert rows == 28

    report, checks = generate()
    assert report["status"] == "PASS", report
    t4_names = {c["check"] for c in checks if c["check"].startswith("T4_RO3_stress_robustness")}
    for required in (
        "T4_RO3_stress_robustness.csv_row_count",
        "T4_RO3_stress_robustness.csv_schema_exact",
        "T4_RO3_stress_robustness.csv_values_exact",
        "T4_RO3_stress_robustness.csv_manifest_hash_match",
        "T4_RO3_stress_robustness.csv_manifest_secondary_hash_match",
    ):
        assert required in t4_names, required
