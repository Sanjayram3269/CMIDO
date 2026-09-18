from pathlib import Path
import argparse
import time
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PARETO_DIR = ROOT / "results" / "RO3" / "pareto"
SCEN_DIR = ROOT / "results" / "RO3" / "scenario_generation"
OUT = ROOT / "results" / "RO3" / "multi_origin"

ORIGINS = [
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01",
    "2022-11-01","2022-12-01","2023-01-01","2023-02-01",
    "2023-03-01","2023-04-01","2023-05-01"
]
MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
HORIZONS = list(range(1,13))

def cvar95(x):
    x = np.asarray(x, dtype=float)
    a = 0.95
    vals = np.unique(x)
    return float(np.min(vals + np.mean(np.maximum(x[None,:]-vals[:,None],0),axis=1)/(1-a)))

def load_prepare(n, origin):
    path = SCEN_DIR / f"RO3_step32_scenarios_{n}.csv"
    use = ["forecast_origin","material","scenario_id","period","month_ahead",
           "demand","price","total_duration_days"]
    raw = pd.read_csv(path, usecols=use)
    raw["forecast_origin"] = pd.to_datetime(raw["forecast_origin"])
    raw["period"] = pd.to_datetime(raw["period"])
    sub = raw[raw["forecast_origin"].eq(pd.Timestamp(origin))].copy()

    checks = []
    counts = sub.groupby("material")["scenario_id"].nunique().reindex(MATERIALS,fill_value=0)
    checks.append(("scenario_count_each_material", bool((counts == n).all())))

    complete = True
    arrays = {}
    for m in MATERIALS:
        x = sub[sub.material.eq(m)].sort_values(["scenario_id","month_ahead"])
        ids = np.sort(x.scenario_id.unique())
        dem = x.pivot(index="scenario_id",columns="month_ahead",values="demand").reindex(index=ids,columns=HORIZONS).to_numpy(float)
        dur = x.drop_duplicates("scenario_id").set_index("scenario_id")["total_duration_days"].reindex(ids).to_numpy(float)
        if len(ids) != n or dem.shape != (n,12) or not np.isfinite(dem).all() or not np.isfinite(dur).all():
            complete = False
        arrays[m] = (ids,dem,dur)
    checks.append(("complete_12_month_horizon", complete))
    checks.append(("four_materials", set(sub.material.unique()) == set(MATERIALS)))
    return sub, arrays, checks

def reconstruct(arrays, q, origin):
    # Vectorized reconstruction following the production monthly-arrival convention.
    origin = pd.Timestamp(origin)
    ref_ids = arrays[MATERIALS[0]][0]
    total = np.zeros(len(ref_ids))
    for mi,m in enumerate(MATERIALS):
        ids, demand, duration = arrays[m]
        if not np.array_equal(ids, ref_ids):
            raise ValueError("Scenario IDs are not aligned across materials.")
        inv = np.zeros(len(ids))
        for t in range(12):
            available = np.zeros(len(ids))
            start = origin + pd.DateOffset(months=t+1)
            end = origin + pd.DateOffset(months=t+2)
            for s in range(12):
                arrival = origin + pd.DateOffset(months=s+1) + pd.to_timedelta(duration,unit="D")
                mask = (arrival >= start) & (arrival < end)
                available[mask] += q[mi,s]
            net = inv + available
            fulfilled = np.minimum(np.maximum(net,0), demand[:,t])
            total += demand[:,t] - fulfilled
            inv = net - fulfilled
    return total

def audit_origin(n, origin):
    tag = pd.Timestamp(origin).strftime("%Y%m%d")
    pp = PARETO_DIR / f"RO3_pareto_N{n}_{tag}.csv"
    dp = PARETO_DIR / f"RO3_pareto_N{n}_{tag}_decisions.csv"
    if not pp.exists() or not dp.exists():
        raise FileNotFoundError(f"Missing result files for {origin}")

    pf = pd.read_csv(pp)
    df = pd.read_csv(dp)
    checks = [
        ("pareto_nonempty", len(pf) > 0),
        ("finite_objectives", np.isfinite(pf[["Z1","Z2","Z3"]].to_numpy(float)).all()),
        ("nonnegative_objectives", (pf[["Z1","Z2","Z3"]] >= 0).all().all()),
        ("pareto_cardinality_le_9", len(pf) <= 9),
        ("decision_ids_aligned", set(df.pareto_id.unique()).issubset(set(pf.pareto_id.unique()))),
        ("decision_materials_complete", set(df.material.unique()) == set(MATERIALS)),
    ]

    sub, arrays, sc = load_prepare(n,origin)
    checks.extend(sc)

    for _,r in pf.iterrows():
        pid = int(r.pareto_id)
        d = df[df.pareto_id.eq(pid)]
        q = np.zeros((4,12))
        mi = {m:i for i,m in enumerate(MATERIALS)}
        for z in d.itertuples(index=False):
            q[mi[z.material],int(z.month_ahead)-1] = float(z.q)
        loss = reconstruct(arrays,q,origin)
        checks.append((f"Z3_consistent_pareto_{pid}", bool(np.isclose(cvar95(loss),float(r.Z3),rtol=1e-8,atol=1e-5))))
    return checks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n",type=int,default=2500)
    args = ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    t0=time.perf_counter()
    print("="*78)
    print("CMIDO RO3.5 — FINAL FAST MULTI-ORIGIN AUDIT")
    print("="*78)
    for i,o in enumerate(ORIGINS,1):
        st=time.perf_counter()
        checks=audit_origin(args.n,o)
        rows += [{"forecast_origin":o,"check":k,"passed":bool(v)} for k,v in checks]
        print(f"[{i:02d}/11] {o}: {sum(v for _,v in checks)}/{len(checks)} PASS ({time.perf_counter()-st:.2f}s)",flush=True)

    out=pd.DataFrame(rows)
    apath=OUT/f"RO3_step35_final_audit_N{args.n}.csv"
    spath=OUT/f"RO3_step35_status_N{args.n}.txt"
    out.to_csv(apath,index=False)
    passed=int(out.passed.sum()); total=len(out)
    status="RO3_5_PASS" if passed==total else "RO3_5_HOLD_FOR_REVIEW"
    spath.write_text(f"Checks passed: {passed}/{total}\nSTATUS: {status}\nRuntime seconds: {time.perf_counter()-t0:.3f}\n",encoding="utf-8")
    print("="*78)
    print(f"RO3.5 AUDIT: {passed}/{total} checks passed")
    print(f"STATUS: {status}")
    print(f"Audit: {apath}")
    if passed != total:
        print(out[~out.passed].to_string(index=False))

if __name__=="__main__":
    main()
