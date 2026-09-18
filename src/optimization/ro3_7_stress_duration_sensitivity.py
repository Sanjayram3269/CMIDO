from pathlib import Path
import pandas as pd, numpy as np, ast, re

ROOT=Path(r"D:\CMIDO")
ABL=ROOT/"results"/"RO3"/"ablation"
O1O3=ABL/"O1_O3"; O2DIR=ABL/"O2"; O4=ABL/"O4_multi_origin"
OUT=ABL/"RO3_7_stress"; OUT.mkdir(parents=True,exist_ok=True)
MATERIALS=["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
ORIGINS=pd.to_datetime(["2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01","2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"])
CASES={"P50":47.0,"P75":70.0,"P90":82.4,"P95":98.8}

def parse_q(x):
    try:
        a=np.asarray(ast.literal_eval(str(x)),float)
        if len(a)==12:return a
    except: pass
    nums=re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",str(x))
    if len(nums)>=12:return np.asarray(nums[:12],float)
    raise ValueError("bad q")

def load_realized():
    d=pd.read_csv(O1O3/"RO3_step36_O1_O3_monthly_ledger.csv")
    d["forecast_origin"]=pd.to_datetime(d.forecast_origin); d["period"]=pd.to_datetime(d.period)
    return d[d.controller=="O1"].copy()

def ledger_to_q(d, controller, col):
    d=d.copy()
    d["forecast_origin"]=pd.to_datetime(d.forecast_origin); d["period"]=pd.to_datetime(d.period)
    d=d[d.controller==controller].copy()
    out=[]
    for (o,m),g in d.groupby(["forecast_origin","material"]):
        g=g.sort_values("month_ahead")
        assert len(g)==12
        out.append((o,m,pd.to_numeric(g[col],errors="coerce").to_numpy(float)))
    assert len(out)==44
    return out

def load_o1o3():
    d=pd.read_csv(O1O3/"RO3_step36_O1_O3_monthly_ledger.csv")
    return ledger_to_q(d,"O1","order_quantity"),ledger_to_q(d,"O3","order_quantity")

def load_o2():
    # O2_selected_decisions is the authoritative selected-policy q vector
    # for the deterministic optimization arm.
    p=O2DIR/"O2_selected_decisions.csv"
    d=pd.read_csv(p)
    required={"forecast_origin","material","period","order_qty"}
    assert required.issubset(d.columns), f"Missing O2 columns: {required-set(d.columns)}"
    d["forecast_origin"]=pd.to_datetime(d.forecast_origin); d["period"]=pd.to_datetime(d.period)
    out=[]
    for (o,m),g in d.groupby(["forecast_origin","material"]):
        g=g.sort_values("period")
        assert len(g)==12
        out.append((o,m,pd.to_numeric(g.order_qty,errors="coerce").to_numpy(float)))
    assert len(out)==44
    return out

def load_o4():
    out=[]
    for o in ORIGINS:
        for m in MATERIALS:
            p=O4/f"O4_{o:%Y-%m-%d}_{m.replace(' ','_')}_pareto.csv"
            d=pd.read_csv(p); s=d[d.selected.astype(bool)]
            assert len(s)==1
            out.append((o,m,parse_q(s.iloc[0].q)))
    assert len(out)==44
    return out

def simulate(qs,realized,duration,controller):
    rows=[]
    for o,m,q in qs:
        sub=realized[(realized.forecast_origin==o)&(realized.material==m)].sort_values("period")
        assert len(sub)==12
        inv=0.
        for j,(_,r) in enumerate(sub.iterrows()):
            period=pd.Timestamp(r.period); avail=0.
            for s in range(j+1):
                op=pd.Timestamp(sub.iloc[s].period)
                if period >= op+pd.Timedelta(days=duration): avail+=q[s]
            dem=float(r.realized_demand); price=float(r.realized_price); order=float(q[j])
            net=inv+avail; shortage=max(0.,dem-max(0.,net)); ending=max(0.,net-dem)
            rows.append(dict(controller=controller,stress_case=None,duration_days=duration,
                forecast_origin=o,material=m,period=period,month_ahead=j+1,
                realized_demand=dem,realized_price=price,order_quantity=order,
                ending_inventory=ending,shortage_quantity=shortage,
                procurement_cost=order*price,holding_cost=.025*price*ending))
            inv=ending
    return pd.DataFrame(rows)

def main():
    print("CMIDO RO3.7 — CONTROLLED STRESS / DURATION SENSITIVITY v2")
    realized=load_realized()
    o1,o3=load_o1o3(); o2=load_o2(); o4=load_o4()
    print("Loaded policies:",len(o1),len(o2),len(o3),len(o4))
    all_led=[]
    for label,L in CASES.items():
        for c,qs in [("O1",o1),("O2",o2),("O3",o3),("O4",o4)]:
            x=simulate(qs,realized,L,c); x.stress_case=label; all_led.append(x)
    led=pd.concat(all_led,ignore_index=True)
    origin=led.groupby(["controller","stress_case","duration_days","forecast_origin"],as_index=False).agg(
        procurement_cost=("procurement_cost","sum"),holding_cost=("holding_cost","sum"),
        shortage=("shortage_quantity","sum"),demand=("realized_demand","sum"),
        procurement_quantity=("order_quantity","sum"),mean_ending_inventory=("ending_inventory","mean"),
        procurement_events=("order_quantity",lambda x:int((x>1e-9).sum())))
    origin["cost"]=origin.procurement_cost+origin.holding_cost
    origin["service"]=1-origin.shortage/origin.demand
    summary=origin.groupby(["controller","stress_case","duration_days"],as_index=False).agg(
        n_origins=("forecast_origin","nunique"),mean_cost=("cost","mean"),median_cost=("cost","median"),
        mean_shortage=("shortage","mean"),median_shortage=("shortage","median"),
        mean_service=("service","mean"),median_service=("service","median"),
        mean_inventory=("mean_ending_inventory","mean"),mean_procurement_quantity=("procurement_quantity","mean"),
        mean_events=("procurement_events","mean"))
    base=origin[origin.stress_case=="P50"].set_index(["controller","forecast_origin"])
    ch=[]
    for label in ["P75","P90","P95"]:
        cur=origin[origin.stress_case==label].set_index(["controller","forecast_origin"])
        for c in ["O1","O2","O3","O4"]:
            for metric in ["cost","shortage","service","mean_ending_inventory"]:
                dd=cur.loc[c,metric]-base.loc[c,metric]
                ch.append(dict(controller=c,comparison=f"{label}_vs_P50",metric=metric,
                    mean_difference=dd.mean(),median_difference=dd.median(),min_difference=dd.min(),max_difference=dd.max()))
    ch=pd.DataFrame(ch)
    checks=[]
    def ck(n,v,d=""):
        checks.append((n,bool(v),d)); print("[PASS]" if v else "[FAIL]",n,d)
    ck("44 policies per controller",all(len(q)==44 for q in [o1,o2,o3,o4]))
    ck("Four stress cases",set(led.stress_case)==set(CASES))
    ck("11 origins/controller/case",origin.groupby(["controller","stress_case"]).forecast_origin.nunique().eq(11).all())
    ck("12 months/material-origin-case",led.groupby(["controller","stress_case","forecast_origin","material"]).size().eq(12).all())
    ck("Finite primary metrics",np.isfinite(origin[["cost","shortage","service"]].to_numpy()).all())
    ck("Service in [0,1]",((origin.service>=0)&(origin.service<=1)).all())
    ck("Nonnegative quantities",(led[["order_quantity","ending_inventory","shortage_quantity"]]>=-1e-9).all().all())
    ck("Same realized demand",led.groupby(["controller","stress_case","forecast_origin","material","month_ahead"]).realized_demand.nunique().max()==1)
    ck("Same realized price",led.groupby(["controller","stress_case","forecast_origin","material","month_ahead"]).realized_price.nunique().max()==1)
    ck("P50 duration=47",CASES["P50"]==47)
    audit=pd.DataFrame(checks,columns=["check","passed","detail"])
    status="PASS" if audit.passed.all() else "HOLD"
    led.to_csv(OUT/"RO3_step37_stress_monthly_ledger.csv",index=False); origin.to_csv(OUT/"RO3_step37_stress_origin_results.csv",index=False)
    summary.to_csv(OUT/"RO3_step37_stress_summary.csv",index=False); ch.to_csv(OUT/"RO3_step37_stress_paired_changes.csv",index=False)
    audit.to_csv(OUT/"RO3_step37_stress_audit.csv",index=False)
    print("\nSUMMARY"); print(summary.to_string(index=False))
    print("\nPAIRED CHANGES VS P50"); print(ch.to_string(index=False))
    print("\nCHECKS:",int(audit.passed.sum()),"/",len(audit),"STATUS:",status)
    print("OUTPUT:",OUT)

if __name__=="__main__": main()
