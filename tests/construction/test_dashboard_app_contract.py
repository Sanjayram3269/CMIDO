from pathlib import Path


def test_dashboard_app_exists_and_exposes_real_project_flow():
    path = Path("apps/cmido_dashboard.py")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "build_dashboard_data" in text
    assert "build_resource_dashboard" in text
    assert "analyze_schedule_impact" in text
    assert "build_uncertainty_context" in text
    assert "run_real_dataset_experiment" in text
    assert "build_statistical_analysis" in text
    assert "plotly" in text.lower()
    assert "file_uploader" in text
    assert "Run scenario" in text
    assert "Experiment Lab" in text
    assert "Research Evidence" in text
    assert "3D Project Graph" in text


def test_dashboard_exposes_research_evidence_controls():
    text = Path("apps/cmido_dashboard.py").read_text(encoding="utf-8")
    required_elements = [
        "Execute experiment",
        "Deterministic CMIDO scenarios",
        "mean_project_delay_confidence_interval",
        "delay_rate",
        "CMIDO Dashboard Experiment",
        "95% bootstrap CI",
    ]
    for element in required_elements:
        assert element in text


def test_dashboard_runtime_dependencies_are_declared():
    text = Path("requirements-dashboard.txt").read_text(encoding="utf-8")
    assert "streamlit" in text
    assert "plotly" in text
    assert "pandas" in text
