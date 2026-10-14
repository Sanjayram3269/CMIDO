from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_8t_f7_generator_contract():
    text = (ROOT / "src/optimization/cmido_8t_f7_pipeline_figure.py").read_text(encoding="utf-8")
    required = [
        "CMIDO 8T",
        "F7_CMIDO_integrated_pipeline.png",
        "CMIDO_8T_F7_MANIFEST.json",
        "CMIDO_8T_F7_AUDIT.csv",
        "supplier-specific lead time NOT inferred",
        "dpi=300",
        "sha256",
        "provenance",
    ]
    for element in required:
        assert element in text, element


def test_8t_f7_has_no_data_derived_claims():
    """The conceptual diagram must not embed quantitative results."""
    from src.optimization.cmido_8t_f7_pipeline_figure import LEFT_COLUMN, RIGHT_COLUMN, LEGEND

    labels = [label for _, label in LEFT_COLUMN + RIGHT_COLUMN] + [text for _, text in LEGEND]
    import re

    offenders = [x for x in labels if re.search(r"\d+\.\d+|\b\d{3,}\b", x)]
    assert offenders == [], offenders
    assert len(LEFT_COLUMN) + len(RIGHT_COLUMN) == 12
    assert len(LEGEND) == 6


def test_8t_f7_generate_writes_figure_and_manifest():
    from src.optimization.cmido_8t_f7_pipeline_figure import generate

    manifest, checks = generate(ROOT)
    assert manifest["status"] == "PASS", manifest
    assert manifest["figure"] == "F7_CMIDO_integrated_pipeline.png"
    assert manifest["sha256"]
    assert manifest["source_kind"].startswith("conceptual diagram")
    fig_path = ROOT / manifest["figure_path"]
    assert fig_path.exists()
    out = ROOT / "results/8T_f7_diagram"
    assert (out / "CMIDO_8T_F7_MANIFEST.json").exists()
    assert (out / "CMIDO_8T_F7_AUDIT.csv").exists()
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]


def test_8t_f7_registered_in_figure_list():
    text = (ROOT / "deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/02_FIGURES/FIGURE_LIST.md").read_text(
        encoding="utf-8"
    )
    assert "F7_CMIDO_integrated_pipeline.png" in text
    assert "cmido_8t_f7_pipeline_figure.py" in text
