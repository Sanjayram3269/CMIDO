"""CMIDO 8R — publication figure generator and reconciliation gate.

Generates publication-facing figures only from the frozen 8Q CSV artifacts.
The script never recomputes scientific statistics from raw data and writes a
machine-readable manifest linking each figure to its exact 8Q source table.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


FIGURES = {
    "F1_RO1_calibration": "T1_RO1_validation_metrics.csv",
    "F2_RO2_tail": "T2_RO2_tail_comparison.csv",
    "F3_RO2_propagation": "T3_RO2_propagation_summary.csv",
    "F4_RO2_sensitivity": "T3_RO2_joint_independent_sensitivity.csv",
    "F5_RO3_controllers": "T5_T6_controller_descriptives.csv",
    "F6_RO3_ablation": "T6_RO3_ablation.csv",
}


def project_root() -> Path:
    override = os.getenv("CMIDO_ROOT")
    return Path(override).expanduser().resolve() if override else Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def generate(root: Path | None = None):
    root = (root or project_root()).resolve()
    q = root / "results" / "8Q_publication_artifacts"
    out = root / "results" / "8R_publication_figures"
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    artifacts = []

    def ck(name: str, ok: bool, detail: str = ""):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    ck("8Q_manifest_exists", (q / "CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json").exists())
    for name, filename in FIGURES.items():
        source = q / filename
        ck(f"{name}_source_exists", source.exists(), str(source))

    if not all(x["passed"] for x in checks):
        return checks, artifacts, out

    df = pd.read_csv(q / FIGURES["F1_RO1_calibration"])
    required = {"series", "prequential_coverage_50", "prequential_coverage_80",
                "prequential_coverage_error_50", "prequential_coverage_error_80"}
    ck("F1_required_columns", required <= set(df.columns))
    if required <= set(df.columns):
        agg = df.groupby("series", as_index=False)[[
            "prequential_coverage_50", "prequential_coverage_80",
            "prequential_coverage_error_50", "prequential_coverage_error_80"
        ]].mean()
        fig, ax = plt.subplots(figsize=(8, 5))
        x = range(len(agg))
        ax.plot(x, agg["prequential_coverage_50"], marker="o", label="50% interval coverage")
        ax.plot(x, agg["prequential_coverage_80"], marker="o", label="80% interval coverage")
        ax.set_xticks(list(x), agg["series"], rotation=25, ha="right")
        ax.set_ylabel("Mean prequential coverage")
        ax.set_title("RO1 — Probabilistic forecast coverage")
        ax.legend()
        fig.tight_layout()
        path = out / "F1_RO1_calibration_coverage.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(("F1_RO1_calibration_coverage.png", q / FIGURES["F1_RO1_calibration"]))

    df = pd.read_csv(q / FIGURES["F2_RO2_tail"])
    required = {"quantile", "representation", "quantile_days"}
    ck("F2_required_columns", required <= set(df.columns))
    if required <= set(df.columns):
        fig, ax = plt.subplots(figsize=(8, 5))
        for rep, sub in df.groupby("representation"):
            sub = sub.sort_values("quantile")
            ax.plot(sub["quantile"], sub["quantile_days"], marker="o", label=str(rep))
        ax.set_xlabel("Quantile")
        ax.set_ylabel("Duration (days)")
        ax.set_title("RO2 — Tail behaviour by representation")
        ax.legend()
        fig.tight_layout()
        path = out / "F2_RO2_tail_comparison.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(("F2_RO2_tail_comparison.png", q / FIGURES["F2_RO2_tail"]))

    df = pd.read_csv(q / FIGURES["F3_RO2_propagation"])
    required = {"material", "representation", "q50", "q75", "q90", "q95", "q99"}
    ck("F3_required_columns", required <= set(df.columns))
    if required <= set(df.columns):
        agg = df.groupby(["material", "representation"], as_index=False)[["q50", "q75", "q90", "q95", "q99"]].mean()
        fig, ax = plt.subplots(figsize=(9, 5))
        labels = agg["material"] + " / " + agg["representation"]
        ax.plot(labels, agg["q95"], marker="o", label="q95")
        ax.plot(labels, agg["q99"], marker="o", label="q99")
        ax.tick_params(axis="x", rotation=55)
        ax.set_ylabel("Demand during duration")
        ax.set_title("RO2 — Propagated demand tail")
        ax.legend()
        fig.tight_layout()
        path = out / "F3_RO2_propagation_tail.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(("F3_RO2_propagation_tail.png", q / FIGURES["F3_RO2_propagation"]))

    df = pd.read_csv(q / FIGURES["F4_RO2_sensitivity"])
    required = {"material", "forecast_origin", "quantile", "independent_minus_joint", "independent_vs_joint_pct"}
    ck("F4_required_columns", required <= set(df.columns))
    ck("F4_expected_rows", len(df) == 240, str(len(df)))
    if required <= set(df.columns) and len(df) == 240:
        agg = df.groupby("quantile", as_index=False)[["independent_minus_joint", "independent_vs_joint_pct"]].mean()
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(agg["quantile"], agg["independent_vs_joint_pct"], marker="o")
        ax.axhline(0, linewidth=1)
        ax.set_xlabel("Quantile")
        ax.set_ylabel("Independent vs joint difference (%)")
        ax.set_title("RO2 — Joint versus independent sensitivity")
        fig.tight_layout()
        path = out / "F4_RO2_joint_independent_sensitivity.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(("F4_RO2_joint_independent_sensitivity.png", q / FIGURES["F4_RO2_sensitivity"]))

    # F5: controller-level descriptive evidence. The frozen artifact does not
    # contain a delay metric; use realized service level, an explicit primary
    # operational outcome already present in the source table.
    df = pd.read_csv(q / FIGURES["F5_RO3_controllers"])
    ck("F5_controller_rows", len(df) == 4, str(len(df)))
    ck("F5_controller_column", "controller" in df.columns)
    metric = "realized_service_level_mean"
    ck("F5_plot_metric_available", metric in df.columns, metric if metric in df.columns else "none")
    if len(df) == 4 and "controller" in df.columns and metric in df.columns:
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.bar(df["controller"], df[metric])
        ax.set_xlabel("Controller")
        ax.set_ylabel("Mean realized service level")
        ax.set_ylim(0, 1)
        ax.set_title("RO3 — Realized service-level comparison across controllers")
        fig.tight_layout()
        path = out / "F5_RO3_controller_descriptives.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(("F5_RO3_controller_descriptives.png", q / FIGURES["F5_RO3_controllers"]))

    df = pd.read_csv(q / FIGURES["F6_RO3_ablation"])
    required = {"comparison", "mean_difference_newer_minus_base"}
    ck("F6_required_columns", required <= set(df.columns))
    if required <= set(df.columns):
        fig, ax = plt.subplots(figsize=(9, 5))
        labels = df["comparison"].astype(str) + " / " + df.get("metric", pd.Series([""] * len(df))).astype(str)
        ax.bar(range(len(df)), df["mean_difference_newer_minus_base"])
        ax.set_xticks(range(len(df)), labels, rotation=65, ha="right")
        ax.set_ylabel("Mean difference (newer − base)")
        ax.set_title("RO3 — Controlled ablation effects")
        fig.tight_layout()
        path = out / "F6_RO3_ablation_effects.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(("F6_RO3_ablation_effects.png", q / FIGURES["F6_RO3_ablation"]))

    for figure, source in artifacts:
        ck(f"{figure}_generated", (out / figure).exists(), str(out / figure))
        ck(f"{figure}_source_hashable", source.exists())

    manifest = {
        "stage": "8R",
        "status": "PASS" if checks and all(x["passed"] for x in checks) else "HOLD",
        "checks_passed": sum(x["passed"] for x in checks),
        "checks_total": len(checks),
        "source_package": "results/8Q_publication_artifacts",
        "figures": [
            {"figure": f, "source": str(s.relative_to(root)), "source_sha256": sha256(s),
             "figure_path": str((out / f).relative_to(root)),
             "generation_script": "src/optimization/cmido_8r_publication_figures.py"}
            for f, s in artifacts
        ],
    }
    (out / "CMIDO_8R_FIGURE_CONCORDANCE.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pd.DataFrame(checks).to_csv(out / "CMIDO_8R_FIGURE_AUDIT.csv", index=False)
    return checks, artifacts, out


def main() -> int:
    checks, artifacts, out = generate()
    print("=" * 78)
    print("CMIDO 8R — PUBLICATION FIGURE + RECONCILIATION GATE")
    print("=" * 78)
    for row in checks:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = f" — {row['detail']}" if row["detail"] else ""
        print(f"[{marker}] {row['check']}{suffix}")
    passed = sum(x["passed"] for x in checks)
    print("=" * 78)
    print(f"STATUS: {'PASS' if checks and passed == len(checks) else 'HOLD'} ({passed}/{len(checks)})")
    print(f"OUTPUT: {out}")
    print("=" * 78)
    return 0 if checks and passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
