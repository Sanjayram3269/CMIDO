"""
CMIDO 8Q — Publication artifact generator.

Generates publication-ready CSV tables directly from frozen result sources.
No scientific values are hard-coded. The script also emits a manifest and
reconciliation audit so every generated table has an auditable source path.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd


def project_root() -> Path:
    override = os.getenv("CMIDO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def generate(root: Path | None = None) -> dict:
    root = (root or project_root()).resolve()
    out = root / "results/8Q_publication_artifacts"
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    artifacts = []

    def ck(name, ok, detail=""):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    fc = root / "results/RO3/ablation/final_comparison"
    pairwise = fc / "RO3_step36_statistical_pairwise_comparisons.csv"
    primary = fc / "RO3_step36_primary_ablation_results.csv"
    desc = fc / "RO3_step36_controller_descriptive_statistics.csv"

    ck("T5_pairwise_source_exists", pairwise.exists(), str(pairwise))
    ck("T6_primary_source_exists", primary.exists(), str(primary))
    ck("T5_T6_descriptive_source_exists", desc.exists(), str(desc))

    if pairwise.exists():
        df = pd.read_csv(pairwise)
        required = {
            "comparison", "contrast", "metric", "n_origins", "newer_mean",
            "base_mean", "mean_difference_newer_minus_base",
            "bootstrap_ci95_lower", "bootstrap_ci95_upper", "wilcoxon_q_bh",
        }
        ck("T5_required_columns", required <= set(df.columns))
        if required <= set(df.columns):
            t5 = df.copy()
            t5["n_origins"] = pd.to_numeric(t5["n_origins"], errors="coerce").astype("Int64")
            columns = [
                "comparison", "contrast", "metric", "n_origins", "newer_mean",
                "base_mean", "mean_difference_newer_minus_base",
                "bootstrap_ci95_lower", "bootstrap_ci95_upper", "wilcoxon_p_raw",
                "wilcoxon_q_bh", "significant_bh_0_05",
            ]
            missing_optional = [col for col in columns if col not in t5.columns]
            ck("T5_output_columns_available", not missing_optional, ", ".join(missing_optional))
            if not missing_optional:
                t5 = t5[columns]
                t5.to_csv(out / "T5_RO3_baseline_comparison.csv", index=False)
                ck("T5_exactly_five_planned_contrasts", set(t5["comparison"]) == {
                    "O2_vs_O1", "O3_vs_O1", "O4_vs_O2", "O4_vs_O3", "O4_vs_O1"
                })
                ck("T5_all_origins_equal_eleven", set(t5["n_origins"].dropna()) == {11})
                artifacts.append(("T5_RO3_baseline_comparison.csv", pairwise, "RO3_step36_statistical_pairwise_comparisons.csv"))

    if primary.exists():
        df = pd.read_csv(primary)
        required = {
            "comparison", "contrast", "metric", "n_origins", "newer_mean",
            "base_mean", "mean_difference_newer_minus_base",
            "bootstrap_ci95_lower", "bootstrap_ci95_upper", "wilcoxon_q_bh",
        }
        ck("T6_required_columns", required <= set(df.columns))
        if required <= set(df.columns):
            t6 = df.copy()
            t6.to_csv(out / "T6_RO3_ablation.csv", index=False)
            ck("T6_expected_primary_rows", len(t6) == 20, str(len(t6)))
            numeric = [
                "newer_mean", "base_mean", "mean_difference_newer_minus_base",
                "bootstrap_ci95_lower", "bootstrap_ci95_upper", "wilcoxon_q_bh",
            ]
            ck("T6_no_nan_primary_values", not t6[numeric].isna().any().any())
            artifacts.append(("T6_RO3_ablation.csv", primary, "RO3_step36_primary_ablation_results.csv"))

    if desc.exists():
        df = pd.read_csv(desc)
        ck("T5_T6_four_controllers", set(df["controller"]) == {"O1", "O2", "O3", "O4"})
        ck("T5_T6_descriptive_rows", len(df) == 4, str(len(df)))
        df.to_csv(out / "T5_T6_controller_descriptives.csv", index=False)
        artifacts.append(("T5_T6_controller_descriptives.csv", desc, "RO3_step36_controller_descriptive_statistics.csv"))

    manifest = {
        "stage": "8Q",
        "status": "PASS" if checks and all(x["passed"] for x in checks) else "HOLD",
        "root": str(root),
        "artifacts": [
            {
                "artifact": artifact,
                "source_path": str(source.relative_to(root)),
                "source_sha256": sha256(source),
                "source_name": source_name,
                "generation_script": "src/optimization/cmido_8q_publication_artifacts.py",
            }
            for artifact, source, source_name in artifacts
        ],
        "checks_passed": sum(x["passed"] for x in checks),
        "checks_total": len(checks),
    }
    (out / "CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    pd.DataFrame(checks).to_csv(out / "CMIDO_8Q_PUBLICATION_ARTIFACT_AUDIT.csv", index=False)
    return manifest, checks


def main() -> int:
    manifest, checks = generate()
    print("=" * 78)
    print("CMIDO 8Q — PUBLICATION ARTIFACT GENERATOR")
    print("=" * 78)
    for row in checks:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = f" — {row['detail']}" if row["detail"] else ""
        print(f"[{marker}] {row['check']}{suffix}")
    print("=" * 78)
    print(f"STATUS: {manifest['status']} ({manifest['checks_passed']}/{manifest['checks_total']})")
    print(f"OUTPUT: {manifest['root']}/results/8Q_publication_artifacts")
    print("=" * 78)
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
