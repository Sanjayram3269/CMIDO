"""CMIDO 8S — full numerical/source reconciliation gate.

Reconciles the frozen 8Q publication tables and 8R figure concordance against
 their authoritative upstream artifacts. The gate checks values, row counts,
key cardinalities, required schemas, and figure-source mappings. It does not
recompute or alter scientific results.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

SPECS = {
    "T1_RO1_validation_metrics.csv": ("results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv", 36),
    "T2_RO2_joint_propagation_summary.csv": ("results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv", 1),
    "T2_RO2_tail_comparison.csv": ("results/RO2/distribution/RO2_step27c3_tail_comparison.csv", 15),
    "T3_RO2_propagation_summary.csv": ("results/RO2/propagation/RO2_step27d_propagation_summary.csv", 96),
    "T3_RO2_service_risk_curve.csv": ("results/RO2/propagation/RO2_step27d_service_risk_curve.csv", 240),
    "T3_RO2_joint_independent_sensitivity.csv": ("results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv", 240),
    "T5_T6_controller_descriptives.csv": ("results/RO3/ablation/final_comparison/RO3_step36_controller_descriptive_statistics.csv", 4),
    "T6_RO3_ablation.csv": ("results/RO3/ablation/final_comparison/RO3_step36_primary_ablation_results.csv", 20),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def same_frame(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    if list(a.columns) != list(b.columns) or a.shape != b.shape:
        return False
    return a.equals(b)


def generate(root: Path | None = None):
    root = (root or ROOT).resolve()
    q = root / "results/8Q_publication_artifacts"
    r = root / "results/8R_publication_figures"
    out = root / "results/8S_numerical_reconciliation"
    out.mkdir(parents=True, exist_ok=True)
    checks = []

    def ck(name: str, ok: bool, detail: str = ""):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    q_manifest = q / "CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json"
    r_manifest = r / "CMIDO_8R_FIGURE_CONCORDANCE.json"
    ck("8Q_manifest_exists", q_manifest.exists(), str(q_manifest))
    ck("8R_concordance_exists", r_manifest.exists(), str(r_manifest))

    q_entries = {}
    if q_manifest.exists():
        qm = json.loads(q_manifest.read_text(encoding="utf-8"))
        ck("8Q_manifest_status_pass", qm.get("status") == "PASS", str(qm.get("status")))
        q_entries = {x["artifact"]: x for x in qm.get("artifacts", [])}
        ck("8Q_manifest_artifact_count", len(q_entries) == 8, str(len(q_entries)))

    for filename, (upstream_rel, expected_rows) in SPECS.items():
        pub = q / filename
        upstream = root / upstream_rel
        ck(f"{filename}_publication_exists", pub.exists(), str(pub))
        ck(f"{filename}_upstream_exists", upstream.exists(), str(upstream))
        if pub.exists() and upstream.exists():
            a = pd.read_csv(pub)
            b = pd.read_csv(upstream)
            ck(f"{filename}_row_count", len(a) == expected_rows, f"{len(a)} expected {expected_rows}")
            ck(f"{filename}_schema_exact", list(a.columns) == list(b.columns))
            ck(f"{filename}_values_exact", same_frame(a, b))
            entry = q_entries.get(filename)
            ck(f"{filename}_manifest_hash_match", bool(entry) and entry.get("source_sha256") == sha256(upstream))

    # Frozen RO3 cardinality and controller invariants.
    desc = q / "T5_T6_controller_descriptives.csv"
    if desc.exists():
        df = pd.read_csv(desc)
        ck("RO3_four_controllers", set(df["controller"]) == {"O1", "O2", "O3", "O4"})
        ck("RO3_eleven_origins_each", set(df["n_origins"]) == {11})
        ck("RO3_service_level_metric_present", "realized_service_level_mean" in df.columns)

    sens = q / "T3_RO2_joint_independent_sensitivity.csv"
    if sens.exists():
        df = pd.read_csv(sens)
        ck("RO2_sensitivity_4_materials", df["material"].nunique() == 4)
        ck("RO2_sensitivity_12_origins", df["forecast_origin"].nunique() == 12)
        ck("RO2_sensitivity_5_quantiles", set(df["quantile"]) == {0.5, 0.75, 0.9, 0.95, 0.99})
        ck("RO2_sensitivity_4x12x5", len(df) == 4 * 12 * 5, str(len(df)))

    # 8R concordance must reference exactly the six frozen 8Q sources.
    if r_manifest.exists():
        rm = json.loads(r_manifest.read_text(encoding="utf-8"))
        ck("8R_manifest_status_pass", rm.get("status") == "PASS", str(rm.get("status")))
        figs = rm.get("figures", [])
        ck("8R_six_figures", len(figs) == 6, str(len(figs)))
        expected_sources = {
            "T1_RO1_validation_metrics.csv", "T2_RO2_tail_comparison.csv",
            "T3_RO2_propagation_summary.csv", "T3_RO2_joint_independent_sensitivity.csv",
            "T5_T6_controller_descriptives.csv", "T6_RO3_ablation.csv"
        }
        actual_sources = {Path(x["source"]).name for x in figs}
        ck("8R_sources_match_8Q", actual_sources == expected_sources)
        for x in figs:
            source = root / x["source"]
            ck(f"8R_{x['figure']}_source_hash_match", source.exists() and x.get("source_sha256") == sha256(source))
            ck(f"8R_{x['figure']}_figure_exists", (root / x["figure_path"]).exists())

    report = {
        "stage": "8S",
        "status": "PASS" if checks and all(x["passed"] for x in checks) else "HOLD",
        "checks_passed": sum(x["passed"] for x in checks),
        "checks_total": len(checks),
        "purpose": "Full numerical/source reconciliation for frozen 8Q publication tables and 8R figures.",
    }
    (out / "CMIDO_8S_RECONCILIATION_MANIFEST.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.DataFrame(checks).to_csv(out / "CMIDO_8S_RECONCILIATION_AUDIT.csv", index=False)
    return report, checks


def main() -> int:
    report, checks = generate()
    print("=" * 78)
    print("CMIDO 8S — FULL NUMERICAL / SOURCE RECONCILIATION GATE")
    print("=" * 78)
    for row in checks:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = f" — {row['detail']}" if row["detail"] else ""
        print(f"[{marker}] {row['check']}{suffix}")
    print("=" * 78)
    print(f"STATUS: {report['status']} ({report['checks_passed']}/{report['checks_total']})")
    print(f"OUTPUT: {ROOT / 'results/8S_numerical_reconciliation'}")
    print("=" * 78)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
