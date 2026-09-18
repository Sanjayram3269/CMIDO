"""
CMIDO RO3.3B — Decision-Level Scenario Sensitivity Runner
v1.1

Purpose:
Run the frozen RO3.4.4 production optimizer at N=1000, 2500, 5000
for a common forecast origin, then compare the resulting Pareto decision
sets at the decision level.

This script does NOT change the optimizer formulation. It calls the
already-frozen production optimizer as a subprocess.

Primary comparisons:
- objective ranges and normalized Pareto-frontier similarity
- 3D hypervolume using a common reference point
- Pareto cardinality
- decision-variable stability via nearest normalized objective matching
- procurement quantity differences for matched solutions

Important:
The current optimizer constructs an attainable epsilon grid from each
scenario set's own anchor ranges. Therefore this is a comparison of the
same frozen optimization procedure under different scenario counts, not
a claim that every N was evaluated on identical numeric epsilon bounds.
"""

from pathlib import Path
import argparse
import json
import subprocess
import sys
import shutil
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OPT = ROOT / "src" / "optimization" / "ro3_epsilon_pareto_optimizer.py"
PARETO = ROOT / "results" / "RO3" / "pareto"
DECISION = PARETO
OUT = ROOT / "results" / "RO3" / "decision_sensitivity"
OUT.mkdir(parents=True, exist_ok=True)

NS = [1000, 2500, 5000]
OBJECTIVES = ["Z1", "Z2", "Z3"]
ORIGIN_DEFAULT = "2022-07-01"


def run_optimizer(n, origin, levels):
    cmd = [
        sys.executable,
        str(OPT),
        "--n", str(n),
        "--origin", origin,
        "--epsilon-levels", str(levels),
    ]
    print("\n" + "=" * 78)
    print(f"RUNNING FROZEN OPTIMIZER: N={n} | origin={origin} | grid={levels}x{levels}")
    print("=" * 78)

    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Optimizer failed for N={n} with exit code {result.returncode}")


def load_results(n, origin):
    tag = pd.Timestamp(origin).strftime("%Y%m%d")
    stem = f"RO3_pareto_N{n}_{tag}"

    pareto_path = PARETO / f"{stem}.csv"
    decision_path = PARETO / f"{stem}_decisions.csv"

    if not pareto_path.exists() or not decision_path.exists():
        raise FileNotFoundError(f"Missing optimizer outputs for N={n}: {stem}")

    p = pd.read_csv(pareto_path)
    q = pd.read_csv(decision_path)

    required_p = {"pareto_id", "Z1", "Z2", "Z3", "scenario_count", "forecast_origin"}
    required_q = {"pareto_id", "material", "month_ahead", "q"}

    if not required_p.issubset(p.columns):
        raise ValueError(f"Pareto output missing columns: {required_p - set(p.columns)}")
    if not required_q.issubset(q.columns):
        raise ValueError(f"Decision output missing columns: {required_q - set(q.columns)}")

    if len(p) == 0:
        raise ValueError(f"No Pareto solutions for N={n}")

    return p, q, pareto_path, decision_path


def normalize_frontiers(results):
    all_points = pd.concat(
        [x[0][OBJECTIVES] for x in results.values()],
        ignore_index=True,
    )

    lo = all_points.min()
    hi = all_points.max()
    span = hi - lo
    span[span <= 0] = 1.0

    normalized = {}
    for n, (p, q, pp, qp) in results.items():
        a = p.copy()
        for obj in OBJECTIVES:
            a[obj + "_norm"] = (a[obj] - lo[obj]) / span[obj]
        normalized[n] = a

    return normalized, lo.to_dict(), hi.to_dict()


def hypervolume_3d(points, reference):
    """
    Exact 3D minimization hypervolume by x-slicing.

    points and reference are in normalized objective space.
    Only points strictly inside the reference box contribute.
    """
    pts = np.asarray(points, dtype=float)
    ref = np.asarray(reference, dtype=float)

    pts = pts[np.all(np.isfinite(pts), axis=1)]
    pts = pts[np.all(pts < ref, axis=1)]

    if len(pts) == 0:
        return 0.0

    # Remove dominated points first.
    keep = []
    for i, a in enumerate(pts):
        dominated = False
        for j, b in enumerate(pts):
            if i == j:
                continue
            if np.all(b <= a) and np.any(b < a):
                dominated = True
                break
        if not dominated:
            keep.append(a)

    pts = np.asarray(keep)
    xs = np.unique(np.r_[pts[:, 0], ref[0]])
    xs.sort()

    hv = 0.0

    for x0, x1 in zip(xs[:-1], xs[1:]):
        if x1 <= x0:
            continue

        active = pts[pts[:, 0] <= x0 + 1e-12]
        if len(active) == 0:
            continue

        yz = active[:, 1:3]
        yvals = np.unique(np.r_[yz[:, 0], ref[1]])
        yvals.sort()

        area = 0.0
        for y0, y1 in zip(yvals[:-1], yvals[1:]):
            if y1 <= y0:
                continue

            active_y = yz[yz[:, 0] <= y0 + 1e-12]
            if len(active_y) == 0:
                continue

            zmin = np.min(active_y[:, 1])
            if zmin < ref[2]:
                area += (y1 - y0) * (ref[2] - zmin)

        hv += (x1 - x0) * area

    return float(hv)


def decision_matrix(q):
    materials = [
        "Cement",
        "Granite",
        "Ready Mixed Concrete",
        "Steel Reinforcement Bars",
    ]
    periods = list(range(1, 13))
    idx = [(m, t) for m in materials for t in periods]

    out = {}
    for pid, g in q.groupby("pareto_id"):
        d = {(r.material, int(r.month_ahead)): float(r.q) for r in g.itertuples()}
        out[int(pid)] = np.asarray([d.get(k, 0.0) for k in idx], dtype=float)
    return out, idx


def nearest_frontier_matching(norm_a, q_a, norm_b, q_b):
    """
    Match each solution in A to its nearest solution in B in normalized
    objective space, then report decision-vector relative L1 difference.
    """
    rows = []

    for pid_a, va in norm_a.groupby("pareto_id"):
        x = va[["Z1_norm", "Z2_norm", "Z3_norm"]].iloc[0].to_numpy(float)

        best = None
        for pid_b, vb in norm_b.groupby("pareto_id"):
            y = vb[["Z1_norm", "Z2_norm", "Z3_norm"]].iloc[0].to_numpy(float)
            dist = float(np.linalg.norm(x - y))
            if best is None or dist < best[0]:
                best = (dist, int(pid_b), y)

        pid_b = best[1]
        qa = q_a[int(pid_a)]
        qb = q_b[pid_b]

        denom = np.maximum(np.abs(qa), 1e-9)
        rel_l1 = float(np.mean(np.abs(qa - qb) / denom))
        abs_l1 = float(np.mean(np.abs(qa - qb)))

        rows.append({
            "pareto_id_a": int(pid_a),
            "pareto_id_b": pid_b,
            "objective_distance_normalized": best[0],
            "mean_abs_quantity_difference": abs_l1,
            "mean_relative_quantity_difference": rel_l1,
        })

    return pd.DataFrame(rows)


def main(origin, levels):
    if not OPT.exists():
        raise FileNotFoundError(f"Frozen optimizer not found: {OPT}")

    results = {}

    for n in NS:
        run_optimizer(n, origin, levels)
        results[n] = load_results(n, origin)

    normalized, lo, hi = normalize_frontiers(results)

    # Scenario-count integrity.
    integrity = []
    for n, (p, q, _, _) in results.items():
        integrity.append({
            "N": n,
            "pareto_count": len(p),
            "scenario_count_values": sorted(p["scenario_count"].unique().tolist()),
            "origin_values": sorted(p["forecast_origin"].astype(str).unique().tolist()),
            "decision_rows": len(q),
        })

    # Common normalized reference point beyond all observed points.
    reference = np.array([1.05, 1.05, 1.05], dtype=float)

    hv_rows = []
    for n, pnorm in normalized.items():
        hv = hypervolume_3d(
            pnorm[["Z1_norm", "Z2_norm", "Z3_norm"]].to_numpy(),
            reference,
        )
        hv_rows.append({
            "N": n,
            "hypervolume_3d_normalized": hv,
            "pareto_count": len(pnorm),
        })

    # Pairwise frontier/decision matching.
    pair_rows = []
    pairs = [(1000, 2500), (2500, 5000), (1000, 5000)]

    q_mats = {}
    for n, (_, q, _, _) in results.items():
        q_mats[n], _ = decision_matrix(q)

    for a, b in pairs:
        matches = nearest_frontier_matching(
            normalized[a], q_mats[a],
            normalized[b], q_mats[b],
        )

        pair_rows.append({
            "N_A": a,
            "N_B": b,
            "mean_objective_distance": matches["objective_distance_normalized"].mean(),
            "max_objective_distance": matches["objective_distance_normalized"].max(),
            "mean_abs_quantity_difference": matches["mean_abs_quantity_difference"].mean(),
            "mean_relative_quantity_difference": matches["mean_relative_quantity_difference"].mean(),
            "max_relative_quantity_difference": matches["mean_relative_quantity_difference"].max(),
            "matched_solutions": len(matches),
        })

        matches.to_csv(
            OUT / f"RO3_step33B_matches_{a}_vs_{b}.csv",
            index=False,
        )

    # Objective summary.
    obj_rows = []
    for n, (p, _, _, _) in results.items():
        for obj in OBJECTIVES:
            obj_rows.append({
                "N": n,
                "objective": obj,
                "min": p[obj].min(),
                "median": p[obj].median(),
                "max": p[obj].max(),
                "mean": p[obj].mean(),
            })

    # Save all outputs.
    tag = pd.Timestamp(origin).strftime("%Y%m%d")
    pd.DataFrame(integrity).to_csv(
        OUT / f"RO3_step33B_integrity_{tag}.csv", index=False
    )
    pd.DataFrame(hv_rows).to_csv(
        OUT / f"RO3_step33B_hypervolume_{tag}.csv", index=False
    )
    pd.DataFrame(pair_rows).to_csv(
        OUT / f"RO3_step33B_pairwise_sensitivity_{tag}.csv", index=False
    )
    pd.DataFrame(obj_rows).to_csv(
        OUT / f"RO3_step33B_objective_summary_{tag}.csv", index=False
    )

    manifest = {
        "origin": origin,
        "scenario_counts": NS,
        "epsilon_levels": levels,
        "optimizer": str(OPT),
        "normalization_min": lo,
        "normalization_max": hi,
        "hypervolume_reference": reference.tolist(),
        "comparison_pairs": pairs,
        "note": (
            "Same frozen optimizer procedure was applied to each N. "
            "The optimizer internally derives epsilon bounds from each "
            "scenario set's anchor objective ranges; therefore frontier "
            "comparison is normalized across attainable ranges and is not "
            "an identical numeric epsilon grid comparison."
        ),
    }

    (OUT / f"RO3_step33B_manifest_{tag}.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 78)
    print("RO3.3B DECISION-LEVEL SCENARIO SENSITIVITY")
    print("=" * 78)
    print(pd.DataFrame(integrity).to_string(index=False))
    print("\nHypervolume:")
    print(pd.DataFrame(hv_rows).to_string(index=False))
    print("\nPairwise sensitivity:")
    print(pd.DataFrame(pair_rows).to_string(index=False))
    print("\nOutputs:")
    print(OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", default=ORIGIN_DEFAULT)
    ap.add_argument("--epsilon-levels", type=int, default=3)
    args = ap.parse_args()
    main(args.origin, args.epsilon_levels)
