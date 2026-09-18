from pathlib import Path
import json
import numpy as np
import pandas as pd
import pyomo.environ as pyo

ROOT = Path(r"D:\CMIDO")
SCEN = ROOT / "results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv"
PRICE_RAW = ROOT / "data/raw/ConstructionMaterialMarketPricesMonthly.csv"
DEMAND_RAW = ROOT / "data/raw/DemandForConstructionMaterialsMonthly.csv"
OUT = ROOT / "results/RO3/ablation/O4_single_origin"
OUT.mkdir(parents=True, exist_ok=True)

ORIGIN = pd.Timestamp("2022-07-01")
MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
H = 12
N = 2500
HOLD = 0.025
ALPHA = 0.95
EPS_POINTS = 5

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

def parse_date(c):
    return pd.to_datetime(str(c), format="%Y%b", errors="coerce")

def load_wide(path):
    return pd.read_csv(path)

def wide_series(df, label, name):
    r = df.loc[df.iloc[:,0].astype(str).str.strip() == name]
    if r.empty:
        raise ValueError(f"Missing {name}")
    row = r.iloc[0]
    out={}
    for c in df.columns[1:]:
        d=parse_date(c)
        if pd.notna(d):
            v=pd.to_numeric(row[c], errors="coerce")
            if pd.notna(v): out[month_start(d)]=float(v)
    return pd.Series(out).sort_index()

def actuals():
    p=load_wide(PRICE_RAW); d=load_wide(DEMAND_RAW)
    P={m:wide_series(p,None,PRICE_MAP[m]) for m in MATERIALS}
    D={m:wide_series(d,None,DEMAND_MAP[m]) for m in MATERIALS}
    return P,D

def cvar(x, alpha=ALPHA):
    x=np.asarray(x,float)
    var=np.quantile(x,alpha,method="linear")
    return float(var + np.mean(np.maximum(x-var,0))/(1-alpha))

def arrival_month(decision_date, duration_days):
    arr=pd.Timestamp(decision_date)+pd.Timedelta(days=float(duration_days))
    return month_start(arr) if arr.day == 1 else month_start(arr)+pd.offsets.MonthBegin(1)

def load_scenarios():
    s=pd.read_csv(SCEN)
    s["forecast_origin"]=pd.to_datetime(s["forecast_origin"])
    s["period"]=pd.to_datetime(s["period"])
    s=s[(s.forecast_origin==ORIGIN)&s.material.isin(MATERIALS)&(s.scenario_set_size==N)].copy()
    expected_rows = N * H * len(MATERIALS)
    if len(s) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows for one origin, got {len(s)}")
    s=s.sort_values(["material","scenario_id","month_ahead"]).reset_index(drop=True)
    return s

def build(d, p, durations, prices, objective, eps=None):
    # Scenario arrays: [w,t]
    m=pyo.ConcreteModel()
    m.T=pyo.RangeSet(0,H-1)
    m.W=pyo.RangeSet(0,N-1)
    total_d=float(np.sum(d))
    m.q=pyo.Var(m.T,bounds=(0,total_d),initialize=0)
    m.I=pyo.Var(m.W,m.T,bounds=(0,total_d),initialize=0)
    m.z=pyo.Var(m.W,m.T,bounds=(0,total_d),initialize=0)

    def balance(m,w,t):
        t=int(t); w=int(w)
        arr=0
        for j in range(t):
            if durations[w,j] is not None:
                arr += m.q[j] if arrival_month(periods[j],durations[w,j]) <= periods[t] else 0
        prev=0 if t==0 else m.I[w,t-1]
        return m.I[w,t] == prev + arr - float(d[w,t]) + m.z[w,t]
    m.balance=pyo.Constraint(m.W,m.T,rule=balance)

    z1=(1/N)*sum(
        sum(m.q[t]*float(p[w,t]) + HOLD*m.I[w,t]*float(p[w,t]) for t in range(H))
        for w in range(N)
    )
    z2=(1/N)*sum(sum(m.z[w,t] for t in range(H)) for w in range(N))

    # RU CVaR epigraph on scenario total shortage.
    m.eta=pyo.Var(bounds=(0,total_d*H),initialize=0)
    m.xi=pyo.Var(m.W,bounds=(0,total_d*H),initialize=0)
    m.cvar_excess=pyo.Constraint(
        m.W,
        rule=lambda m,w: m.xi[w] >= sum(m.z[w,t] for t in range(H)) - m.eta
    )
    z3=m.eta + (1/(1-ALPHA))/N*sum(m.xi[w] for w in range(N))

    m.Z1=pyo.Expression(expr=z1)
    m.Z2=pyo.Expression(expr=z2)
    m.Z3=pyo.Expression(expr=z3)

    if eps is not None:
        m.eps=pyo.Constraint(expr=m.Z2 <= float(eps)+1e-6)

    target={"z1":m.Z1,"z2":m.Z2,"z3":m.Z3}[objective]
    m.obj=pyo.Objective(expr=target,sense=pyo.minimize)
    return m

def solve(d,p,durations,prices,objective,eps=None):
    m=build(d,p,durations,prices,objective,eps)
    res=pyo.SolverFactory("highs").solve(m,tee=False)
    term=str(res.solver.termination_condition).lower()
    if "optimal" not in term:
        raise RuntimeError(term)
    q=np.array([float(m.q[t].value or 0.0) for t in range(H)])
    # Reconstruct exact scenario state and objective from q.
    scenario_rows=[]
    total_short=[]
    z1s=[]
    for w in range(N):
        inv=0.; ztot=0.; cost=0.
        for t in range(H):
            arr=0.
            for j in range(t):
                if arrival_month(periods[j],durations[w,j]) <= periods[t]:
                    arr += q[j]
            short=max(0.,d[w,t]-inv-arr)
            inv=max(0.,inv+arr-d[w,t])
            cost += q[t]*p[w,t] + HOLD*inv*p[w,t]
            ztot += short
        total_short.append(ztot); z1s.append(cost)
    return q,float(np.mean(z1s)),float(np.mean(total_short)),cvar(total_short)

def nondom(df):
    v=df[["Z1","Z2","Z3"]].to_numpy(float); keep=[]
    for i in range(len(v)):
        dom=False
        for j in range(len(v)):
            if i==j: continue
            if np.all(v[j]<=v[i]+1e-8) and np.any(v[j]<v[i]-1e-8):
                dom=True; break
        if not dom: keep.append(i)
    return df.iloc[keep].reset_index(drop=True)

def select(df):
    ranges=df[["Z1","Z2","Z3"]].max()-df[["Z1","Z2","Z3"]].min()
    mins=df[["Z1","Z2","Z3"]].min()
    norm=(df[["Z1","Z2","Z3"]]-mins).divide(ranges.replace(0,1))
    dist=np.sqrt((norm**2).sum(axis=1))
    idx=int(np.lexsort((df.Z3.to_numpy(),df.Z2.to_numpy(),df.Z1.to_numpy(),dist.to_numpy()))[0])
    return df.iloc[idx],float(dist.iloc[idx])

def evaluate(q,actual_d,actual_p):
    inv=0.; rows=[]
    for t in range(H):
        arr=0.
        for j in range(t):
            if arrival_month(periods[j],49) <= periods[t]:
                arr+=q[j]
        short=max(0.,actual_d[t]-inv-arr)
        inv=max(0.,inv+arr-actual_d[t])
        pc=q[t]*actual_p[t]; hc=HOLD*inv*actual_p[t]
        rows.append([periods[t],q[t],arr,actual_d[t],actual_p[t],short,inv,pc,hc])
    return pd.DataFrame(rows,columns=["period","order_qty","arrival_qty","demand","price","shortage","ending_inventory","procurement_cost","holding_cost"])

def main():
    global periods
    periods=pd.date_range(ORIGIN+pd.offsets.MonthBegin(1),periods=H,freq="MS")
    s=load_scenarios()

    # Convert scenario file to [scenario, month] arrays for each material.
    # Single-origin run handles one material at a time, matching the audited RO3 formulation.
    Pact,Dact=actuals()
    all_pareto=[]; all_dec=[]; all_eval=[]

    for material in MATERIALS:
        g=s[s.material==material].sort_values(["scenario_id","month_ahead"])
        if len(g)!=N*H: raise ValueError(material)
        d=g.pivot(index="scenario_id",columns="month_ahead",values="demand").loc[:,range(1,H+1)].to_numpy(float)
        p=g.pivot(index="scenario_id",columns="month_ahead",values="price").loc[:,range(1,H+1)].to_numpy(float)
        durations=g.pivot(index="scenario_id",columns="month_ahead",values="total_duration_days").loc[:,range(1,H+1)].to_numpy(float)

        # Procurement duration is a scenario attribute; use the scenario's duration
        # for each order month. This preserves the generated material-specific stream.
        q1,z11,z21,z31=solve(d,p,durations,p,"z1")
        q2,z12,z22,z32=solve(d,p,durations,p,"z2")
        q3,z13,z23,z33=solve(d,p,durations,p,"z3")

        eps2=np.linspace(z22,z21,EPS_POINTS)
        candidates=[
            ("anchor_z1",q1,z11,z21,z31),
            ("anchor_z2",q2,z12,z22,z32),
            ("anchor_z3",q3,z13,z23,z33),
        ]
        for k,e in enumerate(eps2,1):
            q,z1,z2,z3=solve(d,p,durations,p,"z1",eps=e)
            candidates.append((f"eps_{k:02d}",q,z1,z2,z3))

        rec=[]; seen=set()
        for label,q,z1,z2,z3 in candidates:
            key=tuple(np.round(q,8))
            if key in seen: continue
            seen.add(key)
            rec.append({"forecast_origin":ORIGIN.date().isoformat(),"material":material,
                        "candidate":label,"Z1":z1,"Z2":z2,"Z3":z3,
                        "q_vector":json.dumps(q.tolist())})
        pdf=nondom(pd.DataFrame(rec))
        chosen,dist=select(pdf)
        for _,r in pdf.iterrows():
            all_pareto.append({**r.to_dict(),"selected":int(r.candidate==chosen.candidate)})
        qsel=np.array(json.loads(chosen.q_vector),float)

        ad=np.array([Dact[material].get(x,np.nan) for x in periods],float)
        ap=np.array([Pact[material].get(x,np.nan) for x in periods],float)
        ev=evaluate(qsel,ad,ap)
        ev.insert(0,"forecast_origin",ORIGIN.date().isoformat()); ev.insert(1,"material",material)
        all_eval.append(ev)
        for t,qv in enumerate(qsel):
            all_dec.append({"forecast_origin":ORIGIN.date().isoformat(),"material":material,
                            "period":periods[t],"order_qty":qv,
                            "selected_candidate":chosen.candidate,
                            "optimization_Z1":chosen.Z1,"optimization_Z2":chosen.Z2,"optimization_Z3":chosen.Z3})
        print(f"{material}: Pareto={len(pdf)}, selected={chosen.candidate}, distance={dist:.6f}")

    pd.DataFrame(all_pareto).to_csv(OUT/"O4_single_origin_pareto.csv",index=False)
    pd.DataFrame(all_dec).to_csv(OUT/"O4_single_origin_selected_decisions.csv",index=False)
    ev=pd.concat(all_eval,ignore_index=True)
    ev.to_csv(OUT/"O4_single_origin_realized_evaluation_ledger.csv",index=False)
    summary=ev.groupby("material").agg(
        realized_cost=("procurement_cost",lambda x:float(x.sum())+float(ev.loc[x.index,"holding_cost"].sum())),
        shortage=("shortage","sum"),
        procurement_qty=("order_qty","sum"),
        ending_inventory=("ending_inventory","last")
    ).reset_index()
    summary["service"]=1-summary.shortage/ev.groupby("material")["demand"].sum().to_numpy()
    summary.to_csv(OUT/"O4_single_origin_realized_evaluation_summary.csv",index=False)
    (OUT/"O4_single_origin_manifest.json").write_text(json.dumps({
        "origin":"2022-07-01","scenario_set_size":2500,"materials":MATERIALS,
        "horizon_months":12,"holding_rate_monthly":HOLD,
        "alpha_cvar":ALPHA,"epsilon_points":EPS_POINTS,
        "selection":"normalized_distance_to_utopia_3_objectives"
    },indent=2),encoding="utf-8")
    print("\nO4 SINGLE-ORIGIN RUN COMPLETE")

if __name__=="__main__":
    main()
