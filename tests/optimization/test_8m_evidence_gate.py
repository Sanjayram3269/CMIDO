from pathlib import Path

from src.optimization.cmido_8m_evidence_gate import project_root, run_gate


def test_8m_gate_resolves_repo_root():
    root = project_root()
    assert (root / "src").exists()
    assert (root / "results").exists()


def test_8m_gate_is_portable_and_non_mutating():
    root = project_root()
    before = sorted(p.relative_to(root).as_posix() for p in (root / "results" / "RO3" / "ablation").rglob("*") if p.is_file())
    result = run_gate(root)
    after = sorted(p.relative_to(root).as_posix() for p in (root / "results" / "RO3" / "ablation").rglob("*") if p.is_file())
    assert before == after
    assert result["manifest"]["stage"] == "8M"
    assert result["manifest"]["checks_total"] >= 10


def test_8m_gate_reports_existing_artifact_state():
    result = run_gate(project_root())
    names = {row["check"] for row in result["checks"]}
    assert "controller_freeze_manifest_exists" in names
    assert "origin_artifact_exists" in names
    assert "five_planned_contrasts_present" in names
