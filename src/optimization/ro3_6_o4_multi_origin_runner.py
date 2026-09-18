from pathlib import Path
import json, time, gc
import numpy as np
import pandas as pd
import pyomo.environ as pyo

ROOT=Path(r"D:\CMIDO")
SCEN=ROOT/"results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv"
OUT=ROOT/"results/RO3/ablation/O4_multi_origin"
MATS=["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
ORIGINS=pd.date_range("2022-07-01","2023-05-01",freq="MS")
N=2500; H=12; LEVELS=5; ALPHA=.95; HOLD=.025; EPS=1e-7

def cvar(v):
    v=np.asarray(v,float)
    return float(min(e+np.mean(np.maximum(v-e,0))/(1-ALPHA) for e in np.unique(v)))

def load():
    d=pd.read_csv(SCEN,usecols=["forecast_origin","material","scenario_id","month_ahead","demand","price","total_duration_days","scenario_set_size"])
    d.forecast_origin=pd.to_datetime(d.forecast_origin)
    return d[d.scenario_set_size.eq(N)&d.forecast_origin.isin(ORIGINS)]

def prep(g):
    g=g.sort_values(["scenario_id","month_ahead"])
    if len(g)!=N*H or g.scenario_id.nunique()!=N: raise ValueError("invalid scenario structure")
    D=g.pivot(index="scenario_id",columns="month_ahead",values="demand").loc[:,range(1,H+1)].to_numpy(float)
    P=g.pivot(index="scenario_id",columns="month_ahead",values="price").loc[:,range(1,H+1)].to_numpy(float)
    L=g.drop_duplicates("scenario_id").set_index("scenario_id").total_duration_days.to_numpy(float)
    return D,P,L

def arrival(L,origin):
    base=pd.Timestamp(origin)
    months=[base+pd.DateOffset(months=i) for i in range(1,H+1)]
    md=np.array([x.to_datetime64() for x in months])
    A=np.zeros((N,H,H),dtype=np.int8)
    for s in range(H):
        arr=(months[s]+pd.to_timedelta(L,unit="D")).to_numpy(dtype="datetime64[ns]")
        k=np.searchsorted(md,arr,side="left")
        r=np.flatnonzero(k<H)
        A[r,s,k[r]]=1
    return A

def solve(D,P,A,obj,e2=None,e3=None):
    # Same single-material LP structure as the audited O4 formulation.
    m=pyo.ConcreteModel(); m.T=pyo.RangeSet(1,H); m.W=pyo.RangeSet(0,N-1)
    m.q=pyo.Var(m.T,domain=pyo.NonNegativeReals); m.I=pyo.Var(m.T,m.W,domain=pyo.NonNegativeReals)
    m.z=pyo.Var(m.T,m.W,domain=pyo.NonNegativeReals); m.eta=pyo.Var(domain=pyo.Reals); m.xi=pyo.Var(m.W,domain=pyo.NonNegativeReals)
    m.cap=pyo.Constraint(m.T,m.W,rule=lambda x,t,w:x.z[t,w]<=float(D[w,t-1]))
    m.inv=pyo.Constraint(m.T,m.W,rule=lambda x,t,w:x.I[t,w]==(0 if t==1 else x.I[t-1,w])+sum(int(A[w,s-1,t-1])*x.q[s] for s in range(1,H+1))-float(D[w,t-1])+x.z[t,w])
    m.cost=pyo.Expression(m.W,rule=lambda x,w:sum(float(P[w,t-1])*x.q[t]+HOLD*float(P[w,t-1])*x.I[t,w] for t in range(1,H+1)))
    m.S=pyo.Expression(m.W,rule=lambda x,w:sum(x.z[t,w] for t in range(1,H+1)))
    m.link=pyo.Constraint(m.W,rule=lambda x,w:x.xi[w]>=x.S[w]-x.eta)
    m.Z1=pyo.Expression(expr=sum(m.cost[w] for w in m.W)/N); m.Z2=pyo.Expression(expr=sum(m.S[w] for w in m.W)/N)
    m.Z3=pyo.Expression(expr=m.eta+sum(m.xi[w] for w in m.W)/(N*(1-ALPHA)))
    if e2 is not None:m.e2=pyo.Constraint(expr=m.Z2<=float(e2)+EPS)
    if e3 is not None:m.e3=pyo.Constraint(expr=m.Z3<=float(e3)+EPS)
    m.obj=pyo.Objective(expr={"Z1":m.Z1,"Z2":m.Z2,"Z3":m.Z3}[obj],sense=pyo.minimize)
    r=pyo.SolverFactory("highs").solve(m,tee=False)
    if str(r.solver.termination_condition)!="optimal": return None
    q=np.array([float(pyo.value(m.q[t])) for t in range(1,H+1)])
    S=np.zeros(N); C=np.zeros(N)
    for w in range(N):
        inv=0.
        for t in range(H):
            av=np.dot(A[w,:,t],q); net=inv+av; sh=max(0.,D[w,t]-net); inv=max(0.,net-D[w,t])
            S[w]+=sh; C[w]+=q[t]*P[w,t]+HOLD*P[w,t]*inv
    return {"Z1":float(C.mean()),"Z2":float(S.mean()),"Z3":cvar(S),"q":q.tolist()}

def one(D,P,L,A):
    anc={k:solve(D,P,A,k) for k in ("Z1","Z2","Z3")}
    if any(v is None for v in anc.values()): raise RuntimeError("anchor failure")
    e2=np.linspace(anc["Z2"]["Z2"],anc["Z1"]["Z2"],LEVELS)
    e3=np.linspace(anc["Z3"]["Z3"],anc["Z1"]["Z3"],LEVELS)
    rec=[]
    for i,a in enumerate(e2,1):
        for j,b in enumerate(e3,1):
            v=solve(D,P,A,"Z1",a,b)
            if v:v["candidate_id"]=f"eps_{i:02d}_{j:02d}";rec.append(v)
    for k,v in anc.items():
        x=v.copy();x["candidate_id"]=f"anchor_{k}";rec.append(x)
    uniq={tuple(round(x[k],8) for k in ("Z1","Z2","Z3")):x for x in rec}; vals=list(uniq.values())
    par=[a for a in vals if not any(all(b[k]<=a[k]+1e-7 for k in ("Z1","Z2","Z3")) and any(b[k]<a[k]-1e-7 for k in ("Z1","Z2","Z3")) for b in vals if b is not a)]
    z=np.array([[x["Z1"],x["Z2"],x["Z3"]] for x in par]); lo=z.min(0); sc=np.where(z.max(0)-lo>1e-12,z.max(0)-lo,1)
    dist=np.sqrt(np.sum(((z-lo)/sc)**2,axis=1)); ix=int(np.argmin(dist))
    return par,par[ix],float(dist[ix])

def output_path(o,m):
    return OUT/f"O4_{o.strftime('%Y-%m-%d')}_{m.replace(' ','_')}_pareto.csv"

def main():
    print("CMIDO O4 — FAST RESUME")
    print("Existing successful material-origin outputs are preserved and skipped.")
    print("Only missing cases will be optimized.")
    d=load(); rows=[]
    for oi,o in enumerate(ORIGINS,1):
        print(f"\n[{oi}/11] {o.date()}",flush=True)
        for mi,m in enumerate(MATS,1):
            f=output_path(o,m)
            if f.exists():
                try:
                    old=pd.read_csv(f)
                    print(f"  [{mi}/4] {m}: SKIP existing ({len(old)} Pareto)",flush=True)
                    rows.append({"origin":str(o.date()),"material":m,"status":"EXISTING","pareto":len(old)})
                    continue
                except Exception: pass
            print(f"  [{mi}/4] {m}: RUN",flush=True); t=time.perf_counter()
            D,P,L=prep(d[(d.material==m)&(d.forecast_origin==o)]); A=arrival(L,o)
            par,sel,dist=one(D,P,L,A)
            for r in par:r.update(forecast_origin=str(o.date()),material=m,selected=int(r["candidate_id"]==sel["candidate_id"]),selection_distance=dist if r["candidate_id"]==sel["candidate_id"] else np.nan)
            pd.DataFrame(par).to_csv(f,index=False)
            e=time.perf_counter()-t
            print(f"    PASS | Pareto={len(par)} | selected={sel['candidate_id']} | {e/60:.2f} min",flush=True)
            rows.append({"origin":str(o.date()),"material":m,"status":"PASS","pareto":len(par),"selected":sel["candidate_id"],"minutes":round(e/60,2)})
            pd.DataFrame(rows).to_csv(OUT/"O4_fast_resume_progress.csv",index=False);gc.collect()
    pd.DataFrame(rows).to_csv(OUT/"O4_fast_resume_progress.csv",index=False)
    print("\nO4 FAST RESUME COMPLETE")
    print(OUT/"O4_fast_resume_progress.csv")

if __name__=="__main__":main()
