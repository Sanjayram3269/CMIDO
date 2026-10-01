from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_8r_figure_generator_contract():
    text = (ROOT / "src/optimization/cmido_8r_publication_figures.py").read_text(encoding="utf-8")
    required = [
        "CMIDO 8R",
        "T1_RO1_validation_metrics.csv",
        "T2_RO2_tail_comparison.csv",
        "T3_RO2_propagation_summary.csv",
        "T3_RO2_joint_independent_sensitivity.csv",
        "T5_T6_controller_descriptives.csv",
        "T6_RO3_ablation.csv",
        "CMIDO_8R_FIGURE_CONCORDANCE.json",
        "source_sha256",
        "dpi=300",
    ]
    for element in required:
        assert element in text


def test_8r_frozen_8q_sources_exist():
    q = ROOT / "results" / "8Q_publication_artifacts"
    required = [
        "CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json",
        "T1_RO1_validation_metrics.csv",
        "T2_RO2_tail_comparison.csv",
        "T3_RO2_propagation_summary.csv",
        "T3_RO2_joint_independent_sensitivity.csv",
        "T5_T6_controller_descriptives.csv",
        "T6_RO3_ablation.csv",
    ]
    missing = [name for name in required if not (q / name).exists()]
    assert not missing, f"Missing frozen 8Q sources: {missing}"


def test_8r_figure_output_contract():
    text = (ROOT / "src/optimization/cmido_8r_publication_figures.py").read_text(encoding="utf-8")
    for figure_name in [
        "F1_RO1_calibration_coverage.png",
        "F2_RO2_tail_comparison.png",
        "F3_RO2_propagation_tail.png",
        "F4_RO2_joint_independent_sensitivity.png",
        "F5_RO3_controller_descriptives.png",
        "F6_RO3_ablation_effects.png",
    ]:
        assert figure_name in text
