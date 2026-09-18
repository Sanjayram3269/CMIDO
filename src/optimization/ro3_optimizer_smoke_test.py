from __future__ import annotations
from pathlib import Path
import argparse, json, hashlib
import pandas as pd
import pyomo.environ as pyo

ROOT = Path(__file__).resolve().parents[2]
SCEN_DIR = ROOT / "results" / "RO3" / "scenario_generation"
OUT = ROOT / "results" / "RO3" / "optimization_runs"
OUT.mkdir(parents=True, exist_ok=True)

MATERIALS = ["Cement", "Granite", "Ready Mixed Concrete", "Steel Reinforcement Bars"]
ALPHA = 0.95
H_MONTH = 0.025

def load_scenarios(n, origin, material):
    path = SCEN_DIR / f"RO3_step32_scenarios_{n}.csv"
    df = pd.read_csv(path)
    df["forecast_origin"] = pd.to_datetime(df["forecast_origin"])
    df["period"] = pd.to_datetime(df["period"])
    df = df[(df.forecast_origin == pd.Timestamp(origin)) & (df.material == material)].copy()
    if df.empty:
        raise ValueError("No scenarios found for requested origin/material.")
    df = df.sort_values(["scenario_id", "month_ahead"]).reset_index(drop=True)
    return df

def build_model(df):
    periods = sorted(df["month_ahead"].unique().tolist())
    scenarios = sorted(df["scenario_id"].unique().tolist())
    demand = {(int(r.scenario_id), int(r.month_ahead)): float(r.demand) for r in df.itertuples()}
    price = {(int(r.scenario_id), int(r.month_ahead)): float(r.price) for r in df.itertuples()}
    # Duration is scenario-specific in the generated scenario table.
    duration = {int(r.scenario_id): float(r.total_duration_days) for r in df.drop_duplicates("scenario_id").itertuples()}

    # Frozen calendar availability convention for procurement:
    # an order becomes available in the calendar month containing its
    # sampled arrival date. The full order quantity becomes available once.
    import calendar
    origin = pd.Timestamp(df["forecast_origin"].iloc[0])

    def month_start(k):
        return origin + pd.DateOffset(months=k)

    def month_end(k):
        return month_start(k+1)

    avail = {}
    for w in scenarios:
        L = max(0.0, duration[w])
        for s in periods:
            order_start = month_start(s)
            arrival = order_start + pd.to_timedelta(L, unit="D")
            # Procurement availability is assigned to the calendar month in
            # which the order arrives. Once assigned, it is not re-added in
            # later months. This preserves the full order quantity and avoids
            # both repeated counting and artificial loss of quantity.
            arrival_month = None
            for t in periods:
                ts, te = month_start(t), month_end(t)
                if ts <= arrival < te:
                    arrival_month = t
                    break
            for t in periods:
                avail[w, s, t] = 1.0 if arrival_month == t else 0.0


    m = pyo.ConcreteModel()
    m.T = pyo.Set(initialize=periods, ordered=True)
    m.W = pyo.Set(initialize=scenarios, ordered=True)

    m.q = pyo.Var(m.T, domain=pyo.NonNegativeReals)
    m.I = pyo.Var(m.T, m.W, domain=pyo.NonNegativeReals)
    m.u = pyo.Var(m.T, m.W, domain=pyo.NonNegativeReals)
    m.z = pyo.Var(m.T, m.W, domain=pyo.NonNegativeReals)
    m.eta = pyo.Var(domain=pyo.Reals)
    m.xi = pyo.Var(m.W, domain=pyo.NonNegativeReals)

    def fulfilled_rule(mm,t,w):
        return mm.u[t,w] + mm.z[t,w] == demand[(w,t)]
    m.fulfilled = pyo.Constraint(m.T, m.W, rule=fulfilled_rule)

    def inv_rule(mm,t,w):
        prev = 0 if t == periods[0] else mm.I[periods[periods.index(t)-1],w]
        available = sum(avail[w,s,t] * mm.q[s] for s in periods)
        return mm.I[t,w] == prev + available - mm.u[t,w]
    m.inventory = pyo.Constraint(m.T, m.W, rule=inv_rule)

    def c_rule(mm,w):
        return sum(price[(w,t)] * mm.q[t] + H_MONTH * price[(w,t)] * mm.I[t,w] for t in periods)
    m.cost = pyo.Expression(m.W, rule=c_rule)

    m.shortage = pyo.Expression(m.W, rule=lambda mm,w: sum(mm.z[t,w] for t in periods))

    m.cvar_link = pyo.Constraint(m.W, rule=lambda mm,w: mm.xi[w] >= mm.shortage[w] - mm.eta)

    # Scalarization only for smoke test. The scientific Pareto procedure is
    # epsilon-constraint and is implemented separately after this gate.
    m.obj = pyo.Objective(
        expr=(sum(m.cost[w] for w in m.W)/len(scenarios))
             + 1e6*(sum(m.shortage[w] for w in m.W)/len(scenarios))
             + 1e6*(m.eta + (1/(1-ALPHA))*sum(m.xi[w] for w in m.W)/len(scenarios)),
        sense=pyo.minimize
    )
    return m

def smoke(n=100, origin="2022-07-01", material="Cement"):
    df = load_scenarios(n, origin, material)
    # Keep a tiny deterministic prefix for the build gate.
    keep = sorted(df.scenario_id.unique())[:5]
    df = df[df.scenario_id.isin(keep)].copy()
    model = build_model(df)
    solver = pyo.SolverFactory("highs")
    res = solver.solve(model, tee=False)
    tc = str(res.solver.termination_condition)
    if tc != "optimal":
        raise RuntimeError(f"Solver did not return optimal: {tc}")

    vals = {"termination": tc,
            "n_scenarios": len(keep),
            "material": material,
            "origin": origin,
            "q": [float(pyo.value(model.q[t])) for t in model.T],
            "expected_shortage": float(pyo.value(sum(model.shortage[w] for w in model.W)/len(keep))),
            "cvar95": float(pyo.value(model.eta + (1/(1-ALPHA))*sum(model.xi[w] for w in model.W)/len(keep)))}
    vals["cvar_ge_expected_shortage"] = vals["cvar95"] + 1e-8 >= vals["expected_shortage"]
    if not vals["cvar_ge_expected_shortage"]:
        raise AssertionError("CVaR must be >= expected shortage in this construction.")
    raw = json.dumps(vals, sort_keys=True).encode()
    vals["run_hash"] = hashlib.sha256(raw).hexdigest()
    out = OUT / "RO3_step34_4_smoke_result.json"
    out.write_text(json.dumps(vals, indent=2), encoding="utf-8")
    print("RO3.4.4 SMOKE TEST")
    print("termination:", tc)
    print("scenarios:", len(keep))
    print("expected shortage:", vals["expected_shortage"])
    print("CVaR95 shortage:", vals["cvar95"])
    print("CVaR >= expected shortage:", vals["cvar_ge_expected_shortage"])
    print("result:", out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--origin", default="2022-07-01")
    ap.add_argument("--material", default="Cement")
    args = ap.parse_args()
    smoke(args.n, args.origin, args.material)
