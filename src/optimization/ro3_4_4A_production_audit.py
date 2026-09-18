from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCEN_DIR = ROOT / "results" / "RO3" / "scenario_generation"
PARETO_DIR = ROOT / "results" / "RO3" / "pareto"
OUT = ROOT / "results" / "RO3" / "audits"
OUT.mkdir(parents=True, exist_ok=True)

MATERIALS = ["Cement", "Granite", "Ready Mixed Concrete", "Steel Reinforcement Bars"]
H_MONTH = 0.025
ALPHA = 0.95
TOL = 1e-5

def empirical_cvar(values, alpha):
    values = np.asarray(values, dtype=float)
    return float(min(
        eta + np.mean(np.maximum(values - eta, 0.0)) / (1.0 - alpha)
        for eta in np.unique(values)
    ))

def main(n, origin):
    tag = pd.Timestamp(origin).strftime("%Y%m%d")
    scen = pd.read_csv(SCEN_DIR / f"RO3_step32_scenarios_{n}.csv")
    scen["forecast_origin"] = pd.to_datetime(scen["forecast_origin"])
    scen["period"] = pd.to_datetime(scen["period"])
    scen = scen[
        (scen["forecast_origin"] == pd.Timestamp(origin))
        & scen["material"].isin(MATERIALS)
    ].copy()

    pareto = pd.read_csv(PARETO_DIR / f"RO3_pareto_N{n}_{tag}.csv")
    dec = pd.read_csv(PARETO_DIR / f"RO3_pareto_N{n}_{tag}_decisions.csv")

    checks = []
    def add(name, passed, detail=""):
        checks.append({"check": name, "pass": bool(passed), "detail": detail})

    add("pareto_nonempty", len(pareto) > 0, f"rows={len(pareto)}")
    add("decisions_nonempty", len(dec) > 0, f"rows={len(dec)}")
    add("q_finite_nonnegative",
        np.isfinite(dec["q"]).all() and (dec["q"] >= -TOL).all())

    computed = []

    for pid in sorted(dec["pareto_id"].unique()):
        qdf = dec[dec["pareto_id"] == pid]
        q = {(r.material, int(r.month_ahead)): max(0.0, float(r.q))
             for r in qdf.itertuples()}

        add(f"s{pid}_complete_q_grid", len(q) == 48, str(len(q)))

        # IMPORTANT: aggregate material-level outcomes into one observation
        # per scenario before calculating Z1, Z2 and CVaR(Z2).
        scenario_costs = {}
        scenario_shorts = {}

        for (mat, w), g in scen.groupby(["material", "scenario_id"], sort=False):
            g = g.sort_values("month_ahead")
            L = max(0.0, float(g["total_duration_days"].iloc[0]))

            arrival = {}
            for s in range(1, 13):
                a = (pd.Timestamp(origin) + pd.DateOffset(months=s)
                     + pd.to_timedelta(L, unit="D"))
                arrival[s] = next((
                    t for t in range(1, 13)
                    if (pd.Timestamp(origin) + pd.DateOffset(months=t)
                        <= a < pd.Timestamp(origin) + pd.DateOffset(months=t+1))
                ), None)

            add(f"s{pid}_no_repeated_availability_{mat}_{w}",
                len([x for x in arrival.values() if x is not None]) <= 12)

            inv = 0.0
            cost = 0.0
            short = 0.0

            for t, r in zip(range(1, 13), g.itertuples()):
                available = sum(
                    q.get((mat, s), 0.0)
                    for s in range(1, 13)
                    if arrival[s] == t
                )
                d = float(r.demand)
                p = float(r.price)

                net = inv + available
                u = min(net, d)
                z = d - u
                inv = net - u

                if inv < -TOL:
                    raise AssertionError("negative inventory")
                if z < -TOL or z > d + TOL:
                    raise AssertionError("invalid shortage")

                cost += p * q.get((mat, t), 0.0) + H_MONTH * p * inv
                short += z

            scenario_costs[w] = scenario_costs.get(w, 0.0) + cost
            scenario_shorts[w] = scenario_shorts.get(w, 0.0) + short

        add(f"s{pid}_scenario_count",
            len(scenario_costs) == n and len(scenario_shorts) == n,
            f"cost={len(scenario_costs)}, shortage={len(scenario_shorts)}, expected={n}")

        scenario_ids = sorted(scenario_costs)
        costs = np.asarray([scenario_costs[w] for w in scenario_ids], dtype=float)
        shorts = np.asarray([scenario_shorts[w] for w in scenario_ids], dtype=float)

        add(f"s{pid}_scenario_costs_finite_nonnegative",
            np.isfinite(costs).all() and (costs >= -TOL).all())
        add(f"s{pid}_scenario_shortages_finite_nonnegative",
            np.isfinite(shorts).all() and (shorts >= -TOL).all())

        z1 = float(costs.mean())
        z2 = float(shorts.mean())
        z3 = empirical_cvar(shorts, ALPHA)

        saved = pareto[pareto["pareto_id"] == pid].iloc[0]

        add(f"s{pid}_Z1_consistent",
            abs(z1 - float(saved.Z1)) <= 1e-3 * max(1.0, abs(z1)),
            f"{z1} vs {float(saved.Z1)}")
        add(f"s{pid}_Z2_consistent",
            abs(z2 - float(saved.Z2)) <= 1e-6 * max(1.0, abs(z2)),
            f"{z2} vs {float(saved.Z2)}")
        add(f"s{pid}_Z3_consistent",
            abs(z3 - float(saved.Z3)) <= 1e-6 * max(1.0, abs(z3)),
            f"{z3} vs {float(saved.Z3)}")

        computed.append((pid, z1, z2, z3))

    for i, a in enumerate(computed):
        dominated = False
        for j, b in enumerate(computed):
            if i == j:
                continue
            if (all(b[k] <= a[k] + TOL for k in range(1, 4))
                    and any(b[k] < a[k] - TOL for k in range(1, 4))):
                dominated = True
                break
        add(f"s{a[0]}_nondominated", not dominated)

    audit_path = OUT / f"RO3_step34_4A_audit_N{n}_{tag}_corrected.csv"
    pd.DataFrame(checks).to_csv(audit_path, index=False)

    passed = sum(x["pass"] for x in checks)
    total = len(checks)
    status = "RO3_4_4A_PASS" if passed == total else "RO3_4_4A_HOLD_FOR_REVIEW"

    status_path = OUT / f"RO3_step34_4A_status_N{n}_{tag}_corrected.txt"
    status_path.write_text(
        f"STATUS: {status}\nCHECKS: {passed}/{total}\n", encoding="utf-8"
    )

    print("=" * 78)
    print("RO3.4.4A CORRECTED PRODUCTION PARETO DECISION AUDIT")
    print("=" * 78)
    print(f"Origin: {origin} | N={n}")
    print(f"Checks passed: {passed}/{total}")
    print(f"STATUS: {status}")
    print(f"Audit: {audit_path}")
    print(f"Status: {status_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--origin", default="2022-07-01")
    args = parser.parse_args()
    main(args.n, args.origin)
