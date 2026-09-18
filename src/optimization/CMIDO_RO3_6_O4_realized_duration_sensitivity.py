from pathlib import Path
import ast, re, json
import numpy as np
import pandas as pd

ROOT = Path(r"D:\CMIDO")
ABL = ROOT / "results" / "RO3" / "ablation"
O4DIR = ABL / "O4_multi_origin"
BASE = ABL / "final_comparison"
OUT = BASE / "o4_duration_sensitivity"
OUT.mkdir(parents=True, exist_ok=True)

MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
ORIGINS = pd.to_datetime([
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
    "2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"
])

def parse_q(x):
    s=str(x)
    try:
        v=ast.literal_eval(s)
        if isinstance(v,(list,tuple,np.ndarray)):
            a=np.asarray(v,float)
            if len(a)==12: return a
    except Exception:
        pass
    nums=re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",s)
    if len(nums)>=12: return np.asarray([float(v) for v in nums[:12]])
    raise ValueError("Could not parse 12-month q vector")

def load_selected():
    rows=[]
    for o in ORIGINS:
        for m in MATERIALS:
            p=O4DIR/f"O4_{o:%Y-%m-%d}_{m.replace(' ','_')}_pareto.csv"
            d=pd.read_csv(p)
            s=d[d.selected.astype(bool)]
            assert len(s)==1
            r=s.iloc[0]
            rows.append({"forecast_origin":o,"material":m,
                         "candidate_id":r.candidate_id,
                         "q":parse_q(r.q),
                         "Z1":float(r.Z1),"Z2":float(r.Z2),"Z3":float(r.Z3)})
    return pd.DataFrame(rows)

def load_realized():
    p=ABL/"O1_O3"/"RO3_step36_O1_O3_monthly_ledger.csv"
    d=pd.read_csv(p)
    d["forecast_origin"]=pd.to_datetime(d.forecast_origin)
    d["period"]=pd.to_datetime(d.period)
    return d[d.controller=="O1"].copy()

def load_duration_quantiles():
    # Frozen RO2 27B.4 paired component modelling view.
    # The stored 27B.4 file contains 57 rows overall. The locked paired
    # component sample is the subset with admissible_component=True and
    # finite Internal_num, PODN_num and TotalDN_num: n=37.
    # This is a procurement-process duration proxy, not supplier-specific
    # lead time.
    p=ROOT/"results"/"RO2"/"data_audit"/"RO2_step27b4_admissible_modelling_view.csv"
    d=pd.read_csv(p)
    paired=d[
        d["admissible_component"].astype(bool)
        & pd.to_numeric(d["Internal_num"],errors="coerce").notna()
        & pd.to_numeric(d["PODN_num"],errors="coerce").notna()
        & pd.to_numeric(d["TotalDN_num"],errors="coerce").notna()
    ].copy()

    assert len(paired)==37, f"Expected locked paired n=37; found {len(paired)}"

    # Use the observed paired TotalDN duration distribution for the
    # realized-duration sensitivity cases.
    x=pd.to_numeric(paired["TotalDN_num"],errors="coerce").to_numpy(float)
    assert np.isfinite(x).all()
    return {q:float(np.quantile(x,q,method="linear")) for q in [.50,.75,.90,.95]}

def eval_policy(selected, realized, duration_days):
    rows=[]
    for _,r in selected.iterrows():
        origin=pd.Timestamp(r.forecast_origin)
        mat=r.material
        q=np.asarray(r.q,float)
        g=realized[(realized.forecast_origin==origin)&(realized.material==mat)].sort_values("period")
        assert len(g)==12
        inv=0.0
        for j,(_,rr) in enumerate(g.iterrows()):
            period=pd.Timestamp(rr.period)
            demand=float(rr.realized_demand); price=float(rr.realized_price)
            available=0.0
            for s in range(j+1):
                order_period=pd.Timestamp(g.iloc[s].period)
                arr=order_period+pd.to_timedelta(duration_days,unit="D")
                if period>=arr:
                    available += q[s]
            net=inv+available
            shortage=max(0.0,demand-max(0.0,net))
            ending=max(0.0,net-demand)
            order=float(q[j])
            rows.append({
                "duration_case":duration_days,
                "forecast_origin":origin,"material":mat,
                "period":period,"month_ahead":j+1,
                "realized_demand":demand,"realized_price":price,
                "order_quantity":order,"ending_inventory":ending,
                "shortage_quantity":shortage,
                "procurement_cost":order*price,
                "holding_cost":0.025*price*ending
            })
            inv=ending
    return pd.DataFrame(rows)

def main():
    print("CMIDO RO3.6 — O4 REALIZED PROCUREMENT-DURATION SENSITIVITY")
    print("="*72)

    selected=load_selected()
    realized=load_realized()
    qs=load_duration_quantiles()
    print("Selected policies:",len(selected))
    print("Duration quantiles:",qs)

    # Frozen duration cases: median plus upper empirical quantiles.
    cases={
        "P50":qs[.50],
        "P75":qs[.75],
        "P90":qs[.90],
        "P95":qs[.95],
    }

    all_led=[]
    summaries=[]
    for label,L in cases.items():
        led=eval_policy(selected,realized,L)
        led["duration_label"]=label
        all_led.append(led)
        for o,g in led.groupby("forecast_origin"):
            summaries.append({
                "duration_label":label,"duration_days":L,
                "forecast_origin":o,
                "procurement_holding_cost":g.procurement_cost.sum()+g.holding_cost.sum(),
                "procurement_cost":g.procurement_cost.sum(),
                "holding_cost":g.holding_cost.sum(),
                "shortage":g.shortage_quantity.sum(),
                "demand":g.realized_demand.sum(),
                "service":1-g.shortage_quantity.sum()/g.realized_demand.sum(),
                "procurement_quantity":g.order_quantity.sum(),
                "mean_ending_inventory":g.ending_inventory.mean(),
                "procurement_events":int((g.order_quantity>1e-9).sum())
            })

    led=pd.concat(all_led,ignore_index=True)
    origin=pd.DataFrame(summaries)

    # Material-origin summary for traceability.
    material=led.groupby(["duration_label","duration_case","forecast_origin","material"],as_index=False).agg(
        procurement_cost=("procurement_cost","sum"),
        holding_cost=("holding_cost","sum"),
        shortage=("shortage_quantity","sum"),
        demand=("realized_demand","sum"),
        procurement_quantity=("order_quantity","sum"),
        mean_ending_inventory=("ending_inventory","mean"),
        procurement_events=("order_quantity",lambda x:int((x>1e-9).sum()))
    )
    material["procurement_holding_cost"]=material.procurement_cost+material.holding_cost
    material["service"]=1-material.shortage/material.demand

    desc=origin.groupby(["duration_label","duration_days"]).agg(
        n_origins=("forecast_origin","nunique"),
        mean_cost=("procurement_holding_cost","mean"),
        median_cost=("procurement_holding_cost","median"),
        mean_shortage=("shortage","mean"),
        median_shortage=("shortage","median"),
        mean_service=("service","mean"),
        median_service=("service","median"),
        mean_inventory=("mean_ending_inventory","mean"),
        mean_procurement_qty=("procurement_quantity","mean"),
        mean_events=("procurement_events","mean")
    ).reset_index()

    # Paired changes relative to P50.
    base=origin[origin.duration_label=="P50"].set_index("forecast_origin")
    rows=[]
    for label in ["P75","P90","P95"]:
        cur=origin[origin.duration_label==label].set_index("forecast_origin")
        for metric in ["procurement_holding_cost","shortage","service","mean_ending_inventory","procurement_quantity","procurement_events"]:
            d=cur[metric]-base[metric]
            rows.append({
                "comparison":f"{label}_vs_P50",
                "metric":metric,
                "n_origins":len(d),
                "mean_difference":d.mean(),
                "median_difference":d.median(),
                "min_difference":d.min(),
                "max_difference":d.max(),
                "all_origins_same_direction":bool((d>0).all() or (d<0).all() or (abs(d)<1e-12).all())
            })
    paired=pd.DataFrame(rows)

    checks=[]
    def ck(name,cond,detail=""):
        checks.append({"check":name,"passed":bool(cond),"detail":detail})
        print("[PASS]" if cond else "[FAIL]",name,detail)
    ck("44 selected O4 policies",len(selected)==44,str(len(selected)))
    ck("11 origins",selected.forecast_origin.nunique()==11)
    ck("4 materials",selected.material.nunique()==4)
    ck("37 duration observations",len(load_duration_quantiles())==4)
    ck("All four duration cases",set(origin.duration_label)==set(cases))
    ck("48? actually 44 origin-material policies per case",all(len(x)==44 for x in all_led))
    ck("12 monthly rows per policy-case",led.groupby(["duration_label","forecast_origin","material"]).size().eq(12).all())
    ck("Finite outputs",np.isfinite(led.select_dtypes("number").to_numpy()).all())
    ck("Nonnegative shortage/inventory/order",(led[["shortage_quantity","ending_inventory","order_quantity"]]>=-1e-9).all().all())
    ck("Service in [0,1]",((origin.service>=0)&(origin.service<=1)).all())

    audit=pd.DataFrame(checks)
    status="PASS" if audit.passed.all() else "HOLD"

    led.to_csv(OUT/"RO3_step36_O4_duration_sensitivity_ledger.csv",index=False)
    origin.to_csv(OUT/"RO3_step36_O4_duration_sensitivity_origin_results.csv",index=False)
    material.to_csv(OUT/"RO3_step36_O4_duration_sensitivity_material_results.csv",index=False)
    desc.to_csv(OUT/"RO3_step36_O4_duration_sensitivity_summary.csv",index=False)
    paired.to_csv(OUT/"RO3_step36_O4_duration_sensitivity_paired_changes.csv",index=False)
    audit.to_csv(OUT/"RO3_step36_O4_duration_sensitivity_audit.csv",index=False)

    print("\nSUMMARY")
    print(desc.to_string(index=False))
    print("\nPAIRED CHANGES VS P50")
    print(paired.to_string(index=False))
    print("\nCHECKS PASSED:",int(audit.passed.sum()),"/",len(audit))
    print("STATUS:",status)
    print("OUTPUT:",OUT)

if __name__=="__main__":
    main()
