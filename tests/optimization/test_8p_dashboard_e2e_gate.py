from src.optimization.cmido_8p_dashboard_e2e_gate import project_root, run_gate


def test_8p_gate_resolves_repo_root():
    root = project_root()
    assert (root / "apps").exists()
    assert (root / "results").exists()


def test_8p_gate_covers_dashboard_and_research_sources():
    result = run_gate(project_root())
    assert result["stage"] == "8P"
    assert result["checks_total"] >= 20
    names = {row["check"] for row in result["checks"]}
    assert "dashboard_exists" in names
    assert "ro1_source_exists" in names
    assert "ro2_source_exists" in names
    assert "ro3_source_exists" in names
    assert "ablation_source_exists" in names
    assert result["interactive_smoke_required"] is True


def test_8p_gate_has_no_recompute_side_effects():
    result = run_gate(project_root())
    assert all(isinstance(row["passed"], bool) for row in result["checks"])
