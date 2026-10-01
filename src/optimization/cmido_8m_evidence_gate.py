"""
CMIDO 8M — Baseline / Ablation Evidence Gate

This module turns the existing RO3.6 controlled O1/O2/O3/O4 artifacts into
an explicit, reproducible completion gate for the 8M stage.

It does not retune controllers or recompute scientific outcomes. It checks
that the frozen configuration, common evaluation population, realized ledger,
paired statistical evidence, and source manifests are all present and
internally consistent.

The default project root is resolved from this file so the module is portable
across machines; CMIDO_ROOT may be used to override it.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ORIGINS = pd.to_datetime(
    [
        "2022-07-01",
        "2022-08-01",
        "2022-09-01",
        "2022-10-01",
        "2022-11-01",
        "2022-12-01",
        "2023-01-01",
        "2023-02-01",
        "2023-03-01",
        "2023-04-01",
        "2023-05-01",
    ]
)
MATERIALS = {
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
}
CONTROLLERS = {"O1", "O2", "O3", "O4"}


def project_root() -> Path:
    override = os.getenv("CMIDO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def paths(root: Path) -> dict[str, Path]:
    base = root / "results" / "RO3" / "ablation"
    final = base / "final_comparison"
    return {
        "base": base,
        "final": final,
        "controller_manifest": base / "RO3_step36_controller_freeze_manifest.json",
        "controller_audit": base / "RO3_step36_controller_input_audit.csv",
        "common_manifest": final / "RO3_step36_common_evaluation_manifest.json",
        "common_audit": final / "RO3_step36_common_evaluation_audit.csv",
        "origin": final / "RO3_step36_origin_level_results.csv",
        "material": final / "RO3_step36_material_level_results.csv",
        "descriptive": final / "RO3_step36_controller_descriptive_statistics.csv",
        "primary": final / "RO3_step36_primary_ablation_results.csv",
        "pairwise": final / "RO3_step36_statistical_pairwise_comparisons.csv",
        "audit": final / "RO3_step36_statistical_analysis_audit.csv",
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_gate(root: Path | None = None) -> dict:
    root = (root or project_root()).resolve()
    p = paths(root)
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    # Frozen methodological package.
    check(
        "controller_freeze_manifest_exists",
        p["controller_manifest"].exists(),
        str(p["controller_manifest"]),
    )
    if p["controller_manifest"].exists():
        manifest = json.loads(p["controller_manifest"].read_text(encoding="utf-8"))
        check(
            "controller_contract_matches",
            manifest.get("O1") == "q50 demand heuristic replenishment"
            and manifest.get("O2") == "deterministic q50 optimization"
            and manifest.get("O3") == "q90 demand heuristic replenishment"
            and manifest.get("O4") == "probabilistic CMIDO optimization",
        )

    # Core result artifacts.
    for key in ("origin", "material", "descriptive", "primary", "pairwise", "audit"):
        check(f"{key}_artifact_exists", p[key].exists(), str(p[key]))

    if p["origin"].exists():
        origin = pd.read_csv(p["origin"])
        origin["forecast_origin"] = pd.to_datetime(origin["forecast_origin"], errors="coerce")
        check(
            "four_controllers_present",
            set(origin["controller"]) == CONTROLLERS,
            sorted(origin["controller"].unique()),
        )
        check(
            "eleven_origins_per_controller",
            origin.groupby("controller")["forecast_origin"].nunique().eq(11).all(),
        )
        check(
            "exact_locked_origin_intersection",
            set(origin["forecast_origin"].dropna().unique()) == set(ORIGINS),
        )
        check(
            "origin_metrics_finite",
            np.isfinite(
                origin[
                    [
                        "realized_procurement_holding_cost",
                        "realized_total_shortage",
                        "realized_service_level",
                        "realized_total_procurement_quantity",
                        "realized_mean_ending_inventory",
                        "realized_procurement_events",
                        "realized_shortage_cvar95_monthly",
                    ]
                ].to_numpy()
            ).all(),
        )

    if p["material"].exists():
        material = pd.read_csv(p["material"])
        material["forecast_origin"] = pd.to_datetime(material["forecast_origin"], errors="coerce")
        check(
            "four_materials_present",
            set(material["material"]) == MATERIALS,
            sorted(material["material"].unique()),
        )

    if p["primary"].exists():
        primary = pd.read_csv(p["primary"])
        check("four_primary_metrics_per_contrast", len(primary) == 20, str(len(primary)))
        check(
            "primary_bh_values_present",
            primary["wilcoxon_q_bh"].notna().all(),
        )
        check(
            "primary_bootstrap_bounds_present",
            np.isfinite(
                primary[["bootstrap_ci95_lower", "bootstrap_ci95_upper"]].to_numpy()
            ).all(),
        )

    if p["audit"].exists():
        audit = pd.read_csv(p["audit"])
        check(
            "statistical_audit_all_pass",
            audit["passed"].astype(bool).all(),
            f'{int(audit["passed"].astype(bool).sum())}/{len(audit)}',
        )

    if p["pairwise"].exists():
        pairwise = pd.read_csv(p["pairwise"])
        check(
            "five_planned_contrasts_present",
            set(pairwise["comparison"]) == {
                "O2_vs_O1",
                "O3_vs_O1",
                "O4_vs_O2",
                "O4_vs_O3",
                "O4_vs_O1",
            },
        )

    if p["common_manifest"].exists():
        common_manifest = json.loads(p["common_manifest"].read_text(encoding="utf-8"))
        check(
            "common_manifest_pass",
            common_manifest.get("status") == "PASS",
        )

    if p["common_audit"].exists():
        common_audit = pd.read_csv(p["common_audit"])
        check(
            "common_evaluation_audit_all_pass",
            common_audit["passed"].astype(bool).all(),
            f'{int(common_audit["passed"].astype(bool).sum())}/{len(common_audit)}',
        )

    status = "PASS" if checks and all(x["passed"] for x in checks) else "HOLD"
    manifest = {
        "stage": "8M",
        "status": status,
        "project_root": str(root),
        "controllers": sorted(CONTROLLERS),
        "locked_origins": [d.strftime("%Y-%m-%d") for d in ORIGINS],
        "common_materials": sorted(MATERIALS),
        "inferential_unit": "forecast_origin",
        "checks_passed": int(sum(x["passed"] for x in checks)),
        "checks_total": len(checks),
        "source_artifacts": {
            key: {
                "path": str(path.relative_to(root)) if path.exists() else str(path),
                "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
            }
            for key, path in p.items()
            if key not in {"base", "final"}
        },
    }
    return {"manifest": manifest, "checks": checks}


def main() -> int:
    root = project_root()
    result = run_gate(root)
    out_dir = root / "results" / "RO3" / "ablation" / "8M_gate"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "CMIDO_8M_GATE_MANIFEST.json").write_text(
        json.dumps(result["manifest"], indent=2), encoding="utf-8"
    )
    pd.DataFrame(result["checks"]).to_csv(
        out_dir / "CMIDO_8M_GATE_AUDIT.csv", index=False
    )

    print("=" * 78)
    print("CMIDO 8M — BASELINE / ABLATION EVIDENCE GATE")
    print("=" * 78)
    for row in result["checks"]:
        print(
            f"[{'PASS' if row['passed'] else 'FAIL'}] "
            f"{row['check']}"
            + (f" — {row['detail']}" if row["detail"] else "")
        )
    print("=" * 78)
    print(
        f"STATUS: {result['manifest']['status']} "
        f"({result['manifest']['checks_passed']}/{result['manifest']['checks_total']})"
    )
    print(f"OUTPUT: {out_dir}")
    print("=" * 78)

    return 0 if result["manifest"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
