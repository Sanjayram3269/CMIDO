"""
CMIDO 8O — Paper-facing evidence package gate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


def project_root() -> Path:
    override = os.getenv("CMIDO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def run_gate(root: Path | None = None) -> dict:
    root = (root or project_root()).resolve()
    checks: list[dict] = []

    def ck(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    pkg = root / "docs/CMIDO_8O_PAPER_EVIDENCE_PACKAGE.md"
    evidence = root / "docs/CMIDO_8N_INTEGRATED_EVIDENCE.md"
    gate8m = root / "results/RO3/ablation/8M_gate/CMIDO_8M_GATE_MANIFEST.json"
    gate8n = root / "results/8N_integrated_evidence/CMIDO_8N_INTEGRATED_EVIDENCE_MANIFEST.json"

    ro1 = root / "results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv"
    ro2 = root / "results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv"
    ro3 = root / "results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv"

    ck("8o_package_exists", pkg.exists(), str(pkg))
    ck("8n_package_exists", evidence.exists(), str(evidence))
    ck("8m_manifest_exists", gate8m.exists(), str(gate8m))
    ck("8n_manifest_exists", gate8n.exists(), str(gate8n))

    for name, path in [("ro1_source", ro1), ("ro2_source", ro2), ("ro3_source", ro3)]:
        ck(f"{name}_exists", path.exists(), str(path))

    if gate8m.exists():
        m = json.loads(gate8m.read_text(encoding="utf-8"))
        ck("8m_status_pass", m.get("status") == "PASS", str(m.get("status")))

    if gate8n.exists():
        m = json.loads(gate8n.read_text(encoding="utf-8"))
        ck("8n_status_pass", m.get("status") == "PASS", str(m.get("status")))

    if pkg.exists():
        text = pkg.read_text(encoding="utf-8")
        for marker in [
            "## 3. Core source map",
            "## 4. Experiment identity",
            "## 5. Assumptions requiring explicit manuscript disclosure",
            "## 6. Threats to validity",
            "## 7. Limitations register",
            "## 8. Claim register",
            "## 9. Publication source policy",
            "## 10. Reproducibility policy",
        ]:
            ck(f"package_contains_{marker[3:].lower().replace(' ', '_')}", marker in text)

    status = "PASS" if checks and all(row["passed"] for row in checks) else "HOLD"
    return {
        "stage": "8O",
        "status": status,
        "checks_passed": sum(row["passed"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
    }


def main() -> int:
    root = project_root()
    result = run_gate(root)
    out = root / "results/8O_paper_evidence"
    out.mkdir(parents=True, exist_ok=True)
    (out / "CMIDO_8O_PAPER_EVIDENCE_MANIFEST.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    pd.DataFrame(result["checks"]).to_csv(
        out / "CMIDO_8O_PAPER_EVIDENCE_AUDIT.csv", index=False
    )

    print("=" * 78)
    print("CMIDO 8O — PAPER-FACING EVIDENCE PACKAGE GATE")
    print("=" * 78)
    for row in result["checks"]:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = f" — {row['detail']}" if row["detail"] else ""
        print(f"[{marker}] {row['check']}{suffix}")
    print("=" * 78)
    print(f"STATUS: {result['status']} ({result['checks_passed']}/{result['checks_total']})")
    print(f"OUTPUT: {out}")
    print("=" * 78)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
