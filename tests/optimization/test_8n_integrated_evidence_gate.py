from pathlib import Path

from src.optimization.cmido_8n_integrated_evidence_gate import project_root, run_gate


def test_8n_gate_resolves_repo_root():
    root = project_root()
    assert (root / "results").exists()


def test_8n_gate_is_non_mutating():
    root = project_root()
    result = run_gate(root)
    assert result["stage"] == "8N"
    assert result["checks_total"] >= 10


def test_8n_gate_covers_all_research_domains():
    result = run_gate(project_root())
    names = {row["check"] for row in result["checks"]}
    assert "ro1_calibrated_forecasts_exist" in names
    assert "ro2_admissible_view_exists" in names
    assert "ro3_primary_scenario_set_exists" in names
    assert "8m_gate_status_pass" in names
