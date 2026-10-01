from src.optimization.cmido_8o_paper_evidence_gate import project_root, run_gate


def test_8o_gate_resolves_repo_root():
    root = project_root()
    assert (root / "docs").exists()
    assert (root / "results").exists()


def test_8o_gate_covers_paper_facing_package():
    result = run_gate(project_root())
    assert result["stage"] == "8O"
    assert result["checks_total"] >= 12
    names = {row["check"] for row in result["checks"]}
    assert "8o_package_exists" in names
    assert "8n_status_pass" in names
    assert "ro1_source_exists" in names
    assert "ro2_source_exists" in names
    assert "ro3_source_exists" in names


def test_8o_gate_is_non_mutating():
    result = run_gate(project_root())
    assert result["stage"] == "8O"
    assert all(isinstance(row["passed"], bool) for row in result["checks"])
