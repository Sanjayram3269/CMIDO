from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
import pyomo.environ as pyo

ROOT = Path(r"D:\CMIDO")
FORECAST = ROOT / "results" / "forecasting" / "probabilistic_calibration" / "RO1_step26c3_validation_forecasts.csv"
PRICE_RAW = ROOT / "data" / "raw" / "ConstructionMaterialMarketPricesMonthly.csv"
DEMAND_RAW = ROOT / "data" / "raw" / "DemandForConstructionMaterialsMonthly.csv"
OUT = ROOT / "results" / "RO3" / "ablation" / "O2"
OUT.mkdir(parents=True, exist_ok=True)

ORIGINS = pd.to_datetime([
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
    "2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"
])
MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
H = 12
EPS_POINTS = 9
HOLDING_RATE = 0.025
DURATION_DAYS = 49

PRICE_MAP = {
    "Cement": "Cement In Bulk (Ordinary Portland Cement)",
    "Granite": "Granite (20mm Aggregate)",
    "Ready Mixed Concrete": "Ready Mixed Concrete",
    "Steel Reinforcement Bars": "Steel Reinforcement Bars (16-32mm High Tensile)",
}
DEMAND_MAP = {
    "Cement": "Cement",
    "Granite": "Granite",
    "Ready Mixed Concrete": "Ready-Mixed Concrete",
    "Steel Reinforcement Bars": "Steel Reinforcement Bars",
}

def month_start(x):
    return pd.Timestamp(x).to_period("M").to_timestamp()

def load_wide(path):
    return pd.read_csv(path)

def wide_series(df, label_col, label, date_parser):
    row = df.loc[df[label_col].astype(str).str.strip() == label]
    if row.empty:
        raise ValueError(f"Missing series: {label}")
    row = row.iloc[0]
    vals = {}
    for c in df.columns:
        if c == label_col:
            continue
        try:
            d = date_parser(str(c))
        except Exception:
            continue
        if d is not None:
            v = pd.to_numeric(row[c], errors="coerce")
            if pd.notna(v):
                vals[month_start(d)] = float(v)
    s = pd.Series(vals).sort_index()
    if s.empty:
        raise ValueError(f"No date values for {label}")
    return s

def parse_ymon(c):
    return pd.to_datetime(str(c), format="%Y%b", errors="coerce")

def load_actuals():
    pdf = load_wide(PRICE_RAW)
    ddf = load_wide(DEMAND_RAW)
    price_label = pdf.columns[0]
    demand_label = ddf.columns[0]
    P, D = {}, {}
    for m in MATERIALS:
        P[m] = wide_series(pdf, price_label, PRICE_MAP[m], parse_ymon)
        D[m] = wide_series(ddf, demand_label, DEMAND_MAP[m], parse_ymon)
    return P, D

def load_forecasts():
    f = pd.read_csv(FORECAST)
    f["forecast_origin"] = pd.to_datetime(f["forecast_origin"])
    f["target_date"] = pd.to_datetime(f["target_date"])
    f["series"] = f["series"].astype(str)
    f["dataset"] = f["dataset"].astype(str).str.upper()
    keep = f[
        f["forecast_origin"].isin(ORIGINS) &
        f["series"].isin(MATERIALS) &
        f["dataset"].isin(["RO1_DEMAND","RO1_PRICE"])
    ].copy()
    return keep

def interp_quantile(rows, qcol, h):
    x = rows["horizon"].astype(float).to_numpy()
    y = rows[qcol].astype(float).to_numpy()
    order = np.argsort(x)
    x, y = x[order], y[order]
    if h < x.min() or h > x.max():
        raise ValueError(f"Extrapolation requested at h={h}")
    return float(np.interp(h, x, y))

def get_q50(f, origin, material, dataset):
    r = f[
        (f["forecast_origin"] == origin) &
        (f["series"] == material) &
        (f["dataset"] == dataset)
    ].copy()
    if set(r["horizon"].astype(int)) != {1,3,6,12}:
        raise ValueError(f"Missing source horizons: {origin} {material} {dataset}")
    out = []
    for h in range(1, H+1):
        out.append(interp_quantile(r, "q50", h))
    return np.maximum(np.asarray(out, dtype=float), 0.0)

def arrival_index(t, dates):
    # Month-start decision at dates[t], plus 49 days.
    # Recognize the order in the first monthly period whose month-start
    # is on or after the actual arrival date.
    arr = dates[t] + pd.Timedelta(days=DURATION_DAYS)
    candidates = np.where(dates >= arr)[0]
    return int(candidates[0]) if len(candidates) else None

def useful_order_indices(dates):
    out = []
    for t in range(H):
        if arrival_index(t, dates) is not None:
            out.append(t)
    return out

def simulate(q, demand, price, dates):
    q = np.asarray(q, dtype=float)
    inv = 0.0
    rows = []
    for t in range(H):
        arr = 0.0
        for j in range(H):
            if j < t and arrival_index(j, dates) == t:
                arr += q[j]
        available = inv + arr
        shortage = max(0.0, demand[t] - available)
        inv = max(0.0, available - demand[t])
        procurement_cost = q[t] * price[t]
        holding_cost = HOLDING_RATE * inv * price[t]
        rows.append({
            "period": dates[t],
            "demand": demand[t],
            "price": price[t],
            "order_qty": q[t],
            "arrival_qty": arr,
            "shortage": shortage,
            "ending_inventory": inv,
            "procurement_cost": procurement_cost,
            "holding_cost": holding_cost,
        })
    ledger = pd.DataFrame(rows)
    return ledger

def build_model(demand, price, dates, objective):
    total_d = float(np.sum(demand))
    m = pyo.ConcreteModel()
    m.T = pyo.RangeSet(0, H-1)

    useful = set(useful_order_indices(dates))

    def q_bounds(m, t):
        ti = int(t)
        if ti not in useful:
            return (0.0, 0.0)
        return (0.0, total_d)

    m.q = pyo.Var(m.T, bounds=q_bounds, initialize=0.0)
    m.I = pyo.Var(m.T, bounds=(0.0, total_d), initialize=0.0)
    m.z = pyo.Var(m.T, bounds=(0.0, total_d), initialize=0.0)

    def bal(m, t):
        t = int(t)
        arr = sum(m.q[j] for j in range(H) if j < t and arrival_index(j, dates) == t)
        prev = 0.0 if t == 0 else m.I[t-1]
        return m.I[t] == prev + arr - float(demand[t]) + m.z[t]
    m.balance = pyo.Constraint(m.T, rule=bal)

    z1 = sum(m.q[t] * float(price[t]) + HOLDING_RATE * m.I[t] * float(price[t]) for t in range(H))
    z2 = sum(m.z[t] for t in range(H))
    m.Z1 = pyo.Expression(expr=z1)
    m.Z2 = pyo.Expression(expr=z2)
    m.obj = pyo.Objective(expr=m.Z1 if objective == "z1" else m.Z2, sense=pyo.minimize)
    return m

def solve_anchor(demand, price, dates, objective, eps=None):
    m = build_model(demand, price, dates, objective)
    if eps is not None:
        m.eps = pyo.Constraint(expr=m.Z2 <= float(eps) + 1e-7)
    solver = pyo.SolverFactory("highs")
    res = solver.solve(m, tee=False)
    term = str(res.solver.termination_condition).lower()
    if "optimal" not in term:
        raise RuntimeError(f"Solver did not return optimal: {term}")
    q_vals = []
    for t in range(H):
        v = m.q[t].value
        # HiGHS/Pyomo may omit a value for a variable fixed at its
        # initialized bound during presolve. Such a variable is known
        # to be zero by construction, so recover that deterministic value.
        if v is None:
            if t not in useful_order_indices(dates):
                v = 0.0
            else:
                raise RuntimeError(f"Solver returned no value for economically active q[{t}]")
        q_vals.append(float(v))
    q = np.asarray(q_vals, dtype=float)
    if not np.all(np.isfinite(q)):
        raise RuntimeError("Non-finite q returned")
    ledger = simulate(q, demand, price, dates)
    return q, float(ledger["procurement_cost"].sum() + ledger["holding_cost"].sum()), float(ledger["shortage"].sum())

def nondominated(df):
    keep = []
    vals = df[["Z1","Z2"]].to_numpy(float)
    for i in range(len(df)):
        a = vals[i]
        dominated = False
        for j in range(len(df)):
            if i == j:
                continue
            b = vals[j]
            if np.all(b <= a + 1e-8) and np.any(b < a - 1e-8):
                dominated = True
                break
        if not dominated:
            keep.append(i)
    return df.iloc[keep].copy().reset_index(drop=True)

def select_utopia(df):
    z1min, z1max = df.Z1.min(), df.Z1.max()
    z2min, z2max = df.Z2.min(), df.Z2.max()
    d1 = np.zeros(len(df)) if z1max == z1min else (df.Z1-z1min)/(z1max-z1min)
    d2 = np.zeros(len(df)) if z2max == z2min else (df.Z2-z2min)/(z2max-z2min)
    d = np.sqrt(d1*d1+d2*d2)
    idx = np.lexsort((df.Z2.to_numpy(), df.Z1.to_numpy(), d))[0]
    out = df.iloc[int(idx)].copy()
    out["utopia_distance"] = float(d[int(idx)])
    return out

def main():
    P, D = load_actuals()
    f = load_forecasts()

    all_obj = []
    all_dec = []
    all_eval = []

    for oi, origin in enumerate(ORIGINS, 1):
        dates = pd.date_range(origin + pd.offsets.MonthBegin(1), periods=H, freq="MS")
        for material in MATERIALS:
            demand = get_q50(f, origin, material, "RO1_DEMAND")
            price = get_q50(f, origin, material, "RO1_PRICE")

            q_z1, z1_min, z2_at_z1 = solve_anchor(demand, price, dates, "z1")
            q_z2, z1_at_z2, z2_min = solve_anchor(demand, price, dates, "z2")

            eps_grid = np.linspace(z2_min, z2_at_z1, EPS_POINTS)
            candidates = [
                ("anchor_z1", q_z1, z1_min, z2_at_z1),
                ("anchor_z2", q_z2, z1_at_z2, z2_min),
            ]

            for k, eps in enumerate(eps_grid, 1):
                q, z1, z2 = solve_anchor(demand, price, dates, "z1", eps=eps)
                candidates.append((f"eps_{k:02d}", q, z1, z2))

            seen = set()
            records = []
            for label, q, z1, z2 in candidates:
                key = tuple(np.round(q, 8))
                if key in seen:
                    continue
                seen.add(key)
                records.append({
                    "forecast_origin": origin.date().isoformat(),
                    "material": material,
                    "candidate": label,
                    "Z1": z1,
                    "Z2": z2,
                    "q_vector": json.dumps(q.tolist()),
                })
            cdf = nondominated(pd.DataFrame(records))
            selected = select_utopia(cdf)

            for _, r in cdf.iterrows():
                d1 = 0.0 if cdf.Z1.max() == cdf.Z1.min() else (
                    (float(r.Z1) - float(cdf.Z1.min()))
                    / (float(cdf.Z1.max()) - float(cdf.Z1.min()))
                )
                d2 = 0.0 if cdf.Z2.max() == cdf.Z2.min() else (
                    (float(r.Z2) - float(cdf.Z2.min()))
                    / (float(cdf.Z2.max()) - float(cdf.Z2.min()))
                )
                all_obj.append({
                    "forecast_origin": r["forecast_origin"],
                    "material": material,
                    "candidate": r["candidate"],
                    "Z1": r["Z1"],
                    "Z2": r["Z2"],
                    "selected": int(r["candidate"] == selected["candidate"]),
                    "utopia_distance": float(math.sqrt(d1*d1 + d2*d2)),
                })

            qsel = np.array(json.loads(selected["q_vector"]), dtype=float)
            led = simulate(qsel, demand, price, dates)

            actual_d = np.array([float(D[material].get(month_start(d), np.nan)) for d in dates])
            actual_p = np.array([float(P[material].get(month_start(d), np.nan)) for d in dates])
            if np.any(~np.isfinite(actual_d)) or np.any(~np.isfinite(actual_p)):
                raise RuntimeError(f"Missing realized evaluation data: {origin} {material}")

            ev = simulate(qsel, actual_d, actual_p, dates)
            ev.insert(0, "forecast_origin", origin.date().isoformat())
            ev.insert(1, "material", material)
            all_eval.append(ev)

            for t, d in enumerate(qsel, 1):
                all_dec.append({
                    "forecast_origin": origin.date().isoformat(),
                    "material": material,
                    "period": dates[t-1],
                    "order_qty": d,
                    "selected_candidate": selected["candidate"],
                    "optimization_Z1": float(selected["Z1"]),
                    "optimization_Z2": float(selected["Z2"]),
                })

        print(f"[{oi:02d}/{len(ORIGINS)}] {origin.date()} complete")

    obj = pd.DataFrame(all_obj)
    dec = pd.DataFrame(all_dec)
    ev = pd.concat(all_eval, ignore_index=True)

    obj.to_csv(OUT/"O2_pareto_solutions.csv", index=False)
    dec.to_csv(OUT/"O2_selected_decisions.csv", index=False)
    ev.to_csv(OUT/"O2_realized_evaluation_ledger.csv", index=False)

    summary = ev.groupby(["forecast_origin","material"]).agg(
        realized_cost=("procurement_cost", lambda x: float(x.sum()) + float(ev.loc[x.index,"holding_cost"].sum())),
        shortage=("shortage","sum"),
        service=("shortage", lambda x: 1.0 - float(x.sum())/max(float(ev.loc[x.index,"demand"].sum()),1e-12)),
        procurement_qty=("order_qty","sum"),
        procurement_events=("order_qty", lambda x: int((x > 1e-8).sum())),
        ending_inventory=("ending_inventory","last"),
    ).reset_index()
    summary.to_csv(OUT/"O2_realized_evaluation_summary.csv", index=False)

    manifest = {
        "controller": "O2",
        "status": "EXECUTION_COMPLETE",
        "origins": [x.date().isoformat() for x in ORIGINS],
        "materials": MATERIALS,
        "horizon_months": H,
        "epsilon_points": EPS_POINTS,
        "holding_rate_monthly": HOLDING_RATE,
        "deterministic_duration_days": DURATION_DAYS,
        "policy_selection": "normalized_distance_to_utopia",
        "q_upper_bound": "total_forecast_demand",
        "late_horizon_orders_fixed_zero": True,
    }
    (OUT/"O2_run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nO2 CORRECTED RUN COMPLETE — PRESOLVE-SAFE VARIABLE EXTRACTION")
    print(f"Pareto rows: {len(obj)}")
    print(f"Evaluation rows: {len(ev)}")
    print(f"Cases: {len(summary)}")
    print(f"Outputs: {OUT}")

if __name__ == "__main__":
    main()
