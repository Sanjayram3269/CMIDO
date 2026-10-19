"""Phase E — optimizer / Pareto-front convergence audit (read-only).

What this executes
------------------
Only checks that the repository actually prescribes:

* **RO3.5 §7 integrity gates** (feasibility, non-empty Pareto, finite and
  non-negative objectives, complete scenario/horizon structure, reported Z3
  equal to an independently reconstructed empirical CVaR) are executed by
  ``src/optimization/ro3_5_multi_origin_audit.py``; this audit reads that
  fresh result.
* **RO3.3B frozen decision-sensitivity design** — the frozen optimizer
  configuration, Pareto cardinality, 3-D hypervolume, decision-level
  sensitivity and objective ranges for N ∈ {1000, 2500, 5000} at origin
  2022-07-01.
* **Master specification §26** — hypervolume is the primary Pareto-frontier
  metric; non-dominated count and spread are secondary.
* **RO3.6 freeze specification** — "Pareto-frontier / hypervolume metrics
  where applicable".

Hypervolume is *recomputed from the frozen Pareto files* with the frozen
normalization range and reference point, using the frozen implementation
imported from ``CMIDO_RO3_3B_decision_sensitivity`` (no re-implementation, no
optimizer re-run — ``pyomo``/HiGHS is not installed in this environment and
the frozen design records ``optimizer_rerun: false``).

Nothing is written outside ``smoke_evidence/``. Frozen result files are never
modified, and RO3.3 scenario-count convergence is only *read* to confirm it
keeps its own FAIL/UNRESOLVED verdict.

Acceptance criteria
-------------------
Where the repository prescribes a threshold, the check is PASS/FAIL.
Where it prescribes only a measurement, the outcome is REPORTED.
Where no criterion exists at all (e.g. decision-level materiality
thresholds, which ``ro3_4_formulation_audit.py`` records as
"NOT YET FROZEN"), the outcome is NOT PRESCRIBED — never an invented pass.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import sys

import numpy as np
import pandas as pd

# Console-safe output of the symbols used in check details (≈, §, …).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - best effort
        pass

ROOT = pathlib.Path.cwd()
sys.path.insert(0, str(ROOT))

OUT = ROOT / "smoke_evidence" / "optimizer_pareto_convergence_audit.json"
PARETO = ROOT / "results" / "RO3" / "pareto"
DECISION = ROOT / "results" / "RO3" / "decision_sensitivity"
MULTI = ROOT / "results" / "RO3" / "multi_origin"
RO33 = ROOT / "results" / "RO3" / "scenario_convergence"

ORIGIN = "2022-07-01"
NS = [1000, 2500, 5000]
PAIRS = [(1000, 2500), (2500, 5000), (1000, 5000)]

REC: dict = {
    "stage": "OPTIMIZER_PARETO_CONVERGENCE",
    "started_utc": datetime.datetime.now(datetime.UTC).isoformat(),
    "scope": (
        "Optimizer/Pareto-frontier convergence — separate from RO3.3 "
        "scenario-count convergence, which is untouched by this audit."
    ),
    "checks": [],
    "measurements": {},
}


def record(name: str, status: str, detail: str) -> None:
    assert status in {"PASS", "FAIL", "REPORTED", "NOT PRESCRIBED", "BLOCKED"}
    REC["checks"].append({"check": name, "status": status, "detail": detail})
    print(f"[{status}] {name}: {detail}", flush=True)


def main() -> int:
    # ------------------------------------------------------------------
    # 1. Frozen optimizer configuration across N
    # ------------------------------------------------------------------
    manifests = {}
    for n in NS:
        path = PARETO / f"RO3_pareto_N{n}_{pd.Timestamp(ORIGIN).strftime('%Y%m%d')}_manifest.json"
        if not path.exists():
            record("frozen_optimizer_manifest_present", "FAIL", f"missing {path.name}")
            return 1
        manifests[n] = json.loads(path.read_text(encoding="utf-8"))

    models = {manifests[n]["model"] for n in NS}
    solvers = {manifests[n]["solver"] for n in NS}
    alphas = {manifests[n]["alpha"] for n in NS}
    holdings = {manifests[n]["monthly_holding_rate"] for n in NS}
    grids = {manifests[n]["epsilon_levels"] for n in NS}
    REC["measurements"]["frozen_configuration"] = {
        "model_ids": sorted(models),
        "solvers": sorted(solvers),
        "alpha": sorted(alphas),
        "monthly_holding_rate": sorted(holdings),
        "epsilon_levels": sorted(grids),
        "scenario_counts": NS,
        "origin": ORIGIN,
    }
    frozen_ok = len(models) == 1 and len(solvers) == 1 and len(alphas) == 1 and len(holdings) == 1 and grids == {3}
    record(
        "frozen_objectives_constraints_solver_identical_across_N",
        "PASS" if frozen_ok else "FAIL",
        json.dumps(REC["measurements"]["frozen_configuration"]),
    )

    solves = {n: manifests[n]["feasible_epsilon_solves"] for n in NS}
    counts = {n: manifests[n]["pareto_count"] for n in NS}
    REC["measurements"]["feasible_epsilon_solves"] = solves
    REC["measurements"]["pareto_cardinality"] = counts
    record(
        "epsilon_grid_fully_solved",
        "PASS" if all(v == 9 for v in solves.values()) else "FAIL",
        f"feasible epsilon solves per N (3x3 grid => 9): {solves}",
    )

    # ------------------------------------------------------------------
    # 2. Hypervolume recomputed from the frozen fronts (Master spec §26)
    # ------------------------------------------------------------------
    from src.optimization.CMIDO_RO3_3B_decision_sensitivity import (
        OBJECTIVES,
        hypervolume_3d,
        load_results,
        normalize_frontiers,
    )

    results = {n: load_results(n, ORIGIN) for n in NS}
    normalized, lo, hi = normalize_frontiers(results)

    step33b_manifest = json.loads(
        (DECISION / f"RO3_step33B_manifest_{pd.Timestamp(ORIGIN).strftime('%Y%m%d')}.json").read_text(
            encoding="utf-8"
        )
    )
    ref = np.asarray(step33b_manifest["hypervolume_reference"], dtype=float)
    rec_min = {k: float(v) for k, v in step33b_manifest["normalization_min"].items()}
    rec_max = {k: float(v) for k, v in step33b_manifest["normalization_max"].items()}

    norm_ok = all(
        np.isclose(lo[k], rec_min[k], rtol=1e-12, atol=1e-6)
        and np.isclose(hi[k], rec_max[k], rtol=1e-12, atol=1e-6)
        for k in OBJECTIVES
    )
    record(
        "frozen_normalization_matches_recorded_manifest",
        "PASS" if norm_ok else "FAIL",
        f"recomputed min={ {k: round(lo[k], 6) for k in OBJECTIVES} } "
        f"max={ {k: round(hi[k], 6) for k in OBJECTIVES} }",
    )

    recomputed = {}
    for n, pnorm in normalized.items():
        recomputed[n] = float(
            hypervolume_3d(pnorm[["Z1_norm", "Z2_norm", "Z3_norm"]].to_numpy(), ref)
        )

    recorded = pd.read_csv(
        DECISION / f"RO3_step33B_hypervolume_{pd.Timestamp(ORIGIN).strftime('%Y%m%d')}.csv"
    )
    recorded_map = {int(r.N): float(r.hypervolume_3d_normalized) for r in recorded.itertuples()}
    hv_delta = {n: abs(recomputed[n] - recorded_map[n]) for n in NS}
    hv_ok = all(d <= 1e-9 for d in hv_delta.values())
    REC["measurements"]["hypervolume_recomputed"] = recomputed
    REC["measurements"]["hypervolume_recorded"] = recorded_map
    REC["measurements"]["hypervolume_abs_delta"] = hv_delta
    record(
        "hypervolume_reconciles_with_recorded_RO3_3B",
        "PASS" if hv_ok else "FAIL",
        f"recomputed={recomputed} recorded={recorded_map} max|delta|={max(hv_delta.values()):.3e}",
    )

    hv_move = {
        "1000_to_2500_rel": (recomputed[2500] - recomputed[1000]) / recomputed[1000],
        "2500_to_5000_rel": (recomputed[5000] - recomputed[2500]) / recomputed[2500],
        "1000_to_5000_rel": (recomputed[5000] - recomputed[1000]) / recomputed[1000],
    }
    REC["measurements"]["hypervolume_relative_movement"] = hv_move
    record(
        "hypervolume_movement_across_scenario_counts",
        "REPORTED",
        json.dumps({k: round(v, 6) for k, v in hv_move.items()})
        + " — no acceptance threshold for hypervolume movement is prescribed in the repository",
    )

    # ------------------------------------------------------------------
    # 3. Pareto-front stability (cardinality + non-emptiness)
    # ------------------------------------------------------------------
    card_ok = all(counts[n] > 0 for n in NS)
    record(
        "pareto_set_nonempty_at_every_N",
        "PASS" if card_ok else "FAIL",
        f"cardinality={counts} (RO3.5 §7 requires a non-empty Pareto set)",
    )
    record(
        "pareto_cardinality_stability_across_N",
        "REPORTED",
        f"cardinality identical across N: {len(set(counts.values())) == 1} ({counts}); "
        "RO3.3B prescribes reporting cardinality, not a stability threshold",
    )

    # RO3.5 audit (freshly executed) — the prescribed integrity gates.
    audit_path = MULTI / "RO3_step35_final_audit_N2500.csv"
    audit = pd.read_csv(audit_path)
    audit_passed = int(audit["passed"].astype(bool).sum())
    audit_total = len(audit)
    cvaR_rows = audit[audit["check"].str.startswith("Z3_consistent_pareto_")]
    REC["measurements"]["ro3_5_integrity_audit"] = {
        "path": str(audit_path.relative_to(ROOT)),
        "checks_passed": audit_passed,
        "checks_total": audit_total,
        "cvar_reconstruction_checks": int(len(cvaR_rows)),
        "cvar_reconstruction_passed": int(cvaR_rows["passed"].astype(bool).sum()),
        "origins": sorted(audit["forecast_origin"].astype(str).unique().tolist()),
    }
    record(
        "ro3_5_integrity_gates",
        "PASS" if audit_passed == audit_total else "FAIL",
        f"{audit_passed}/{audit_total} including "
        f"{int(cvaR_rows['passed'].astype(bool).sum())}/{len(cvaR_rows)} "
        "independent CVaR reconstructions (Z3 consistency)",
    )

    # ------------------------------------------------------------------
    # 4. Feasibility evidence from the frozen execution records
    # ------------------------------------------------------------------
    execution = []
    for path in sorted(MULTI.glob("execution_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        stdout = doc.get("stdout", "") or ""
        m_solves = re.search(r"Feasible epsilon solves:\s*(\d+)", stdout)
        m_nd = re.search(r"Computed nondominated solutions:\s*(\d+)", stdout)
        execution.append(
            {
                "origin": doc.get("forecast_origin"),
                "return_code": doc.get("return_code"),
                "scenario_count": doc.get("scenario_count"),
                "feasible_epsilon_solves": int(m_solves.group(1)) if m_solves else None,
                "nondominated_solutions": int(m_nd.group(1)) if m_nd else None,
            }
        )
    feasible_ok = (
        len(execution) == 11
        and all(e["return_code"] == 0 for e in execution)
        and all((e["feasible_epsilon_solves"] or 0) == 9 for e in execution)
        and all((e["nondominated_solutions"] or 0) > 0 for e in execution)
    )
    REC["measurements"]["execution_records"] = execution
    record(
        "optimizer_feasibility_all_locked_origins",
        "PASS" if feasible_ok else "FAIL",
        f"{len(execution)} execution records; return codes and feasible-solve counts: "
        + json.dumps(
            [
                [e["origin"], e["return_code"], e["feasible_epsilon_solves"], e["nondominated_solutions"]]
                for e in execution
            ]
        ),
    )
    record(
        "solver_termination_wording",
        "REPORTED",
        "Frozen execution records report 'Feasible epsilon solves: 9' and return_code 0; "
        "they do not print the literal solver termination token, so the RO3.5 §7 "
        "'optimal termination' gate is evidenced by solve counts + return codes + the "
        "Z3 reconstruction checks rather than by a stored termination string.",
    )

    # ------------------------------------------------------------------
    # 5. Objective movement (Z1 / Z2 / Z3 across N)
    # ------------------------------------------------------------------
    obj = pd.read_csv(
        DECISION / f"RO3_step33B_objective_summary_{pd.Timestamp(ORIGIN).strftime('%Y%m%d')}.csv"
    )
    movement = {}
    for objective in OBJECTIVES:
        sub = obj[obj.objective == objective].set_index("N")
        movement[objective] = {}
        for a, b in PAIRS:
            row = {}
            for stat in ("min", "median", "max", "mean"):
                va, vb = float(sub.loc[a, stat]), float(sub.loc[b, stat])
                row[stat] = (vb - va) / va if va else None
            movement[objective][f"{a}_vs_{b}"] = {k: (None if v is None else round(v, 6)) for k, v in row.items()}
    REC["measurements"]["objective_relative_movement"] = movement
    max_move = max(
        abs(v)
        for per_obj in movement.values()
        for per_pair in per_obj.values()
        for v in per_pair.values()
        if v is not None
    )
    record(
        "objective_movement_across_scenario_counts",
        "REPORTED",
        f"max |relative change| over min/median/max/mean for Z1/Z2/Z3 = {max_move:.6f}; "
        "no optimizer/Pareto objective-movement acceptance threshold is prescribed "
        "(decision-level materiality thresholds are recorded as NOT YET FROZEN in "
        "src/optimization/ro3_4_formulation_audit.py)",
    )

    # ------------------------------------------------------------------
    # 6. Decision stability (frozen corrected primary metric)
    # ------------------------------------------------------------------
    corrected = pd.read_csv(
        DECISION / f"RO3_step33B_corrected_summary_{pd.Timestamp(ORIGIN).strftime('%Y%m%d')}.csv"
    )
    decision_rows = [
        {
            "pair": f"{int(r.N_A)}_vs_{int(r.N_B)}",
            "matched_solutions": int(r.matched_solutions),
            "mean_objective_distance": float(r.mean_objective_distance),
            "max_objective_distance": float(r.max_objective_distance),
            "primary_total_procurement_normalized_difference_mean": float(
                r.mean_total_procurement_normalized_difference
            ),
            "primary_total_procurement_normalized_difference_max": float(
                r.max_total_procurement_normalized_difference
            ),
        }
        for r in corrected.itertuples()
    ]
    REC["measurements"]["decision_stability"] = decision_rows
    record(
        "decision_stability_measured",
        "REPORTED",
        json.dumps(decision_rows),
    )
    record(
        "decision_level_materiality_threshold",
        "NOT PRESCRIBED",
        "Frozen decision-level materiality thresholds do not exist "
        "(ro3_4_formulation_audit.py: 'Decision-level materiality thresholds: NOT YET FROZEN'; "
        "RO3.3B preflight lists 'freeze decision-level materiality thresholds' as still required), "
        "so decision stability is reported as a measurement and no pass is claimed.",
    )
    record(
        "uncorrected_relative_quantity_metric_unusable",
        "REPORTED",
        "RO3_step33B_pairwise_sensitivity_*.csv reports mean_relative_quantity_difference "
        "≈ 1.94e+08 for the 1000-vs pairs (near-zero denominators); the corrected zero-safe "
        "metric in RO3_step33B_corrected_summary_*.csv is the usable one.",
    )

    # ------------------------------------------------------------------
    # 7. Separation from RO3.3 scenario-count convergence
    # ------------------------------------------------------------------
    verdicts = {}
    for name in ("RO3_step33_decision.txt", "RO3_step33A_decision.txt"):
        path = RO33 / name
        verdicts[name] = path.read_text(encoding="utf-8").strip() if path.exists() else "MISSING"
    REC["measurements"]["ro3_3_verdicts_read_only"] = verdicts
    unchanged = all(v not in {"", "MISSING"} for v in verdicts.values())
    record(
        "ro3_3_scenario_count_verdict_untouched",
        "PASS" if unchanged else "FAIL",
        "read-only confirmation: " + json.dumps(verdicts),
    )

    # ------------------------------------------------------------------
    REC["finished_utc"] = datetime.datetime.now(datetime.UTC).isoformat()
    counts: dict[str, int] = {}
    for c in REC["checks"]:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    REC["summary"] = counts
    OUT.write_text(json.dumps(REC, indent=1), encoding="utf-8")
    print("\nSUMMARY:", json.dumps(counts))
    print("WROTE", OUT)
    return 0 if counts.get("FAIL", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
