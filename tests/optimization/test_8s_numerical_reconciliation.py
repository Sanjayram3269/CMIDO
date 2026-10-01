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
        "T5_T6_controller_descriptives.csv",
        "T6_RO3_ablation.csv",
    ]
    missing = [x for x in required if not (q / x).exists()]
    assert not missing, f"Missing frozen 8Q sources: {missing}"
