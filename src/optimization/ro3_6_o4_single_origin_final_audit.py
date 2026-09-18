from pathlib import Path
import json, math
import numpy as np
import pandas as pd

ROOT = Path(r"D:\CMIDO")
SCEN = ROOT / "results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv"
OUT = ROOT / "results/RO3/ablation/O4_single_origin"
PARETO = OUT / "O4_single_origin_pareto.csv"
DEC = OUT / "O4_single_origin_selected_decisions.csv"
EVAL = OUT / "O4_single_origin_realized_evaluation_ledger.csv"
SUMMARY = OUT / "O4_single_origin_realized_evaluation_summary.csv"

ORIGIN = pd.Timestamp("2022-07-01")
MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
H = 12
N = 2500
HOLD = 0.025
ALPHA = 0.95
TOL = 1e-6

def cvar(x, alpha=ALPHA):
    x=np.asarray(x,float)
    var=np.quantile(x,alpha,method="linear")
    return float(var + np.mean(np.maximum(x-var,0))/(1-alpha))

def month_start(x):
    return pd.Timestamp(x).to_period("M").to_timestamp()

def arrival_month(decision_date, duration_days):
    arr=pd.Timestamp(decision_date)+pd.Timedelta(days=float(duration_days))
    return month_start(arr) if arr.day == 1 else month_start(arr)+pd.offsets.MonthBegin(1)

def audit():
    checks=[]
    def ck(name, cond, detail=""):
        checks.append((name,bool(cond),detail))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    required=[SCEN,PARETO,DEC,EVAL,SUMMARY]
    for f in required:
        ck(f"file exists: {f.name}", f.exists())
    if not all(f.exists() for f in required):
        print("STATUS: HOLD")
        return

    s=pd.read_csv(SCEN)
    s["forecast_origin"]=pd.to_datetime(s["forecast_origin"])
    s["period"]=pd.to_datetime(s["period"])
    s=s[(s.forecast_origin==ORIGIN)&s.material.isin(MATERIALS)&(s.scenario_set_size==N)].copy()
    pareto=pd.read_csv(PARETO)
    dec=pd.read_csv(DEC)
    ev=pd.read_csv(EVAL)
    summ=pd.read_csv(SUMMARY)
    ev["period"]=pd.to_datetime(ev["period"])
    dec["period"]=pd.to_datetime(dec["period"])

    # Structural
    ck("scenario rows", len(s)==N*H*len(MATERIALS), str(len(s)))
    ck("scenario materials", set(s.material)==set(MATERIALS))
    # Long-format scenario schema: one scenario_id is intentionally repeated
    # across its 12 monthly rows. Uniqueness is therefore checked at the
    # scenario-month level, and each scenario must contain exactly H months.
    scenario_month_dup = s.duplicated(["material","scenario_id","month_ahead"]).any()
    counts = s.groupby(["material","scenario_id"]).size()
    ck("scenario-month IDs unique",
       not scenario_month_dup)
    ck("each scenario has exactly 12 monthly records",
       counts.eq(H).all(),
       f"min={counts.min()}, max={counts.max()}, scenarios={len(counts)}")
    ck("month-ahead complete", sorted(s.month_ahead.unique())==list(range(1,H+1)))
    ck("scenario values finite", np.isfinite(s[["demand","price","total_duration_days"]].to_numpy(float)).all())
    ck("scenario nonnegative", (s[["demand","price"]].to_numpy(float)>=0).all())
    ck("duration positive", (s.total_duration_days.to_numpy(float)>0).all())

    # Pareto/selection
    ck("pareto materials complete", set(pareto.material)==set(MATERIALS))
    counts=pareto.groupby("material").size()
    ck("pareto count >=1", (counts>0).all(), counts.to_dict())
    ck("exactly one selected/material", pareto.groupby("material")["selected"].sum().eq(1).all())
    ck("selected candidate exists in Pareto", set(
        dec.groupby("material").selected_candidate.first()
    ) <= set(pareto.candidate))
    ck("decision rows", len(dec)==len(MATERIALS)*H, str(len(dec)))
    ck("decision periods complete", dec.groupby("material").period.nunique().eq(H).all())
    ck("decision quantities finite/nonnegative",
       np.isfinite(dec.order_qty).all() and (dec.order_qty>=-TOL).all())
    ck("one selected candidate per material",
       dec.groupby("material").selected_candidate.nunique().eq(1).all())

    # Recompute scenario objectives from selected q.
    objective_ok=True
    objective_rows=[]
    for m in MATERIALS:
        g=s[s.material==m].sort_values(["scenario_id","month_ahead"])
        d=g.pivot(index="scenario_id",columns="month_ahead",values="demand").loc[:,range(1,H+1)].to_numpy(float)
        p=g.pivot(index="scenario_id",columns="month_ahead",values="price").loc[:,range(1,H+1)].to_numpy(float)
        L=g.pivot(index="scenario_id",columns="month_ahead",values="total_duration_days").loc[:,range(1,H+1)].to_numpy(float)
        q=dec[dec.material==m].sort_values("period").order_qty.to_numpy(float)

        shorts=[]; costs=[]
        periods=pd.date_range(ORIGIN+pd.offsets.MonthBegin(1), periods=H, freq="MS")
        for w in range(N):
            inv=0.0; ztot=0.0; cost=0.0
            for t in range(H):
                arr=0.0
                for j in range(t):
                    if arrival_month(periods[j],L[w,j]) <= periods[t]:
                        arr += q[j]
                short=max(0.0,d[w,t]-inv-arr)
                inv=max(0.0,inv+arr-d[w,t])
                cost += q[t]*p[w,t] + HOLD*inv*p[w,t]
                ztot += short
            shorts.append(ztot); costs.append(cost)

        z1=float(np.mean(costs)); z2=float(np.mean(shorts)); z3=cvar(shorts)
        row=pareto[(pareto.material==m)&(pareto.selected==1)].iloc[0]
        objective_rows.append((m,z1,z2,z3,float(row.Z1),float(row.Z2),float(row.Z3)))
        ok=all(abs(a-b)<=TOL*max(1,abs(b)) for a,b in zip((z1,z2,z3),(row.Z1,row.Z2,row.Z3)))
        objective_ok &= ok
        ck(f"objective reconstruction: {m}", ok,
           f"recomputed=({z1:.6f},{z2:.6f},{z3:.6f})")

    ck("all selected stochastic objectives reconstruct", objective_ok)

    # Pareto nondomination among recorded Pareto candidates, per material.
    pareto_ok=True
    for m in MATERIALS:
        g=pareto[pareto.material==m].copy()
        v=g[["Z1","Z2","Z3"]].to_numpy(float)
        for i in range(len(v)):
            dominated=False
            for j in range(len(v)):
                if i==j: continue
                if np.all(v[j] <= v[i]+1e-8) and np.any(v[j] < v[i]-1e-8):
                    dominated=True
                    break
            if dominated:
                pareto_ok=False
                break
        ck(f"nondominated recorded Pareto: {m}", not dominated)
    ck("all recorded Pareto sets nondominated", pareto_ok)

    # Realized evaluation reconciliation.
    ev_ok=True
    for m in MATERIALS:
        g=ev[ev.material==m].sort_values("period")
        ck(f"realized ledger rows: {m}", len(g)==H)
        pc=float(g.procurement_cost.sum())
        hc=float(g.holding_cost.sum())
        sh=float(g.shortage.sum())
        qty=float(g.order_qty.sum())
        expected=summ[summ.material==m].iloc[0]
        ok=(abs(pc+hc-float(expected.realized_cost))<=1e-5*max(1,abs(pc+hc))
            and abs(sh-float(expected.shortage))<=1e-5*max(1,abs(sh))
            and abs(qty-float(expected.procurement_qty))<=1e-5*max(1,abs(qty)))
        ev_ok &= ok
        ck(f"realized summary reconciliation: {m}", ok)

    ck("all realized ledgers reconcile to summary", ev_ok)
    ck("realized service within [0,1]", ((summ.service>=-TOL)&(summ.service<=1+TOL)).all())

    audit=pd.DataFrame(checks,columns=["check","passed","detail"])
    audit.to_csv(OUT/"O4_single_origin_final_audit.csv",index=False)
    passed=int(audit.passed.sum())
    total=len(audit)
    status="O4_SINGLE_ORIGIN_PASS" if passed==total else "O4_SINGLE_ORIGIN_HOLD"
    print(f"\nCHECKS PASSED: {passed}/{total}")
    print(f"STATUS: {status}")
    print(f"AUDIT: {OUT/'O4_single_origin_final_audit.csv'}")

if __name__=="__main__":
    audit()
