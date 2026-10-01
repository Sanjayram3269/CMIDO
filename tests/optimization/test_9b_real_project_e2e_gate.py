from pathlib import Path

from src.optimization.cmido_9b_real_project_e2e_gate import run_gate


def test_9b_real_project_e2e_gate_passes():
    result = run_gate(Path(".").resolve())
    assert result["status"] == "PASS"
    assert result["checks_passed"] == result["checks_total"]
