from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(r"D:\CMIDO")
SCEN=ROOT/"results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv"
OUT=ROOT/"results/RO3/ablation/O4_multi_origin"
MATS=["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
ORIGINS=pd.date_range("2022-07-01","2023-05-01",freq="MS")
N=2500; H=12; TOL=1e-7

checks=[]
def ck(name,ok,detail=""):
    checks.append((name,bool(ok),detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"+(f" — {detail}" if detail else ""))

def dominates(a,b):
    ks=["Z1","Z2","Z3"]
    return all(a[k]<=b[k]+TOL for k in ks) and any(a[k]<b[k]-TOL for k in ks)

def main():
    print("CMIDO O4 — 11-ORIGIN FINAL AUDIT")
    ck("scenario file exists",SCEN.exists())
    if not SCEN.exists(): return
    progress=OUT/"O4_fast_resume_progress.csv"
    ck("resume progress exists",progress.exists())

    files=[]
    for o in ORIGINS:
        for mat in MATS:
            f=OUT/f"O4_{o.strftime('%Y-%m-%d')}_{mat.replace(' ','_')}_pareto.csv"
            files.append((o,mat,f))
            ck(f"Pareto file exists: {o.date()} | {mat}",f.exists())
    if not all(f.exists() for _,_,f in files):
        print("Missing result files; do not run optimization from this audit.")
        return

    s=pd.read_csv(SCEN,usecols=["forecast_origin","material","scenario_id","month_ahead","demand","price","total_duration_days","scenario_set_size"])
    s.forecast_origin=pd.to_datetime(s.forecast_origin)
    s=s[s.scenario_set_size.eq(N)&s.forecast_origin.isin(ORIGINS)&s.material.isin(MATS)]
    ck("scenario row count",len(s)==44*N*H,str(len(s)))
    ck("scenario origins exact",set(s.forecast_origin)==set(ORIGINS))
    ck("scenario materials exact",set(s.material)==set(MATS))
    ck("scenario-month uniqueness",not s.duplicated(["forecast_origin","material","scenario_id","month_ahead"]).any())
    counts=s.groupby(["forecast_origin","material","scenario_id"]).size()
    ck("each scenario has 12 months",counts.eq(H).all(),f"min={counts.min()}, max={counts.max()}, scenarios={len(counts)}")
    ck("month-ahead range 1..12",sorted(s.month_ahead.unique())==list(range(1,13)))
    ck("scenario values finite",np.isfinite(s[["demand","price","total_duration_days"]].to_numpy(float)).all())
    ck("demand/price nonnegative",(s[["demand","price"]].to_numpy(float)>=0).all())
    ck("duration positive",(s.total_duration_days.to_numpy(float)>0).all())

    allp=[]
    for o,mat,f in files:
        g=pd.read_csv(f); allp.append(g.assign(forecast_origin=o,material=mat))
        ck(f"Pareto nonempty: {o.date()} | {mat}",len(g)>0)
        req={"candidate_id","Z1","Z2","Z3","selected","q"}
        ck(f"required columns: {o.date()} | {mat}",req.issubset(g.columns))
        if not req.issubset(g.columns): continue
        ck(f"finite objectives: {o.date()} | {mat}",np.isfinite(g[["Z1","Z2","Z3"]].to_numpy(float)).all())
        ck(f"exactly one selected: {o.date()} | {mat}",int(g.selected.sum())==1,f"selected={int(g.selected.sum())}")
        qok=True
        for raw in g.q:
            try:
                q=np.asarray(json.loads(raw),float)
                if q.shape!=(H,) or not np.isfinite(q).all() or (q< -TOL).any(): qok=False; break
            except Exception: qok=False; break
        ck(f"12-month decision vector valid: {o.date()} | {mat}",qok)
        v=g[["Z1","Z2","Z3"]].to_numpy(float); nd=True
        for i in range(len(v)):
            ai=dict(zip(["Z1","Z2","Z3"],v[i]))
            if any(j!=i and dominates(dict(zip(["Z1","Z2","Z3"],v[j])),ai) for j in range(len(v))):
                nd=False; break
        ck(f"recorded Pareto nondominance: {o.date()} | {mat}",nd)

    P=pd.concat(allp,ignore_index=True)
    ck("44 result sets",P.groupby(["forecast_origin","material"]).ngroups==44)
    sel=P[P.selected.eq(1)]
    ck("44 selected policies",len(sel)==44)
    ck("selected distances finite",np.isfinite(sel.selection_distance.to_numpy(float)).all())
    ck("one selected candidate per case",sel.groupby(["forecast_origin","material"]).candidate_id.nunique().eq(1).all())

    if progress.exists():
        pr=pd.read_csv(progress)
        ck("progress contains 44 cases",len(pr)==44,str(len(pr)))
        ck("progress statuses complete",set(pr.status).issubset({"PASS","EXISTING"}) and len(pr)==44)

    audit=pd.DataFrame(checks,columns=["check","passed","detail"])
    path=OUT/"O4_multi_origin_final_audit.csv"; audit.to_csv(path,index=False)
    passed=int(audit.passed.sum()); total=len(audit)
    status="O4_MULTI_ORIGIN_PASS" if passed==total else "O4_MULTI_ORIGIN_HOLD"
    print(f"\nCHECKS PASSED: {passed}/{total}")
    print(f"STATUS: {status}")
    print(f"AUDIT: {path}")

if __name__=="__main__": main()
