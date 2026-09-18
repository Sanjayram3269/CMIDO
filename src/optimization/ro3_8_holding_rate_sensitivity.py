from pathlib import Path
import pandas as pd, numpy as np, ast, re

ROOT=Path(r"D:\CMIDO")
ABL=ROOT/"results"/"RO3"/"ablation"
O1O3=ABL/"O1_O3"; O2DIR=ABL/"O2"; O4=ABL/"O4_multi_origin"
OUT=ABL/"RO3_8_robustness"; OUT.mkdir(parents=True,exist_ok=True)

MATERIALS=["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
ORIGINS=pd.to_datetime(["2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01","2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"])
RATES={"H20":0.20/12,"H30":0.30/12,"H40":0.40/12}
DURATION=47.0

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

def load_o1o3():
    d=pd.read_csv(O1O3/"RO3_step36_O1_O3_monthly_ledger.csv")
    d["forecast_origin"]=pd.to_datetime(d.forecast_origin); d["period"]=pd.to_datetime(d.period)
    out={}
    for c in ["O1","O3"]:
        x=d[d.controller==c]
        qs=[]
        for (o,m),g in x.groupby(["forecast_origin","material"]):
            g=g.sort_values("month_ahead"); assert len(g)==12
            qs.append((o,m,g.order_quantity.to_numpy(float)))
        assert len(qs)==44; out[c]=qs
    return out

def load_o2():
    d=pd.read_csv(O2DIR/"O2_selected_decisions.csv")
    d["forecast_origin"]=pd.to_datetime(d.forecast_origin); d["period"]=pd.to_datetime(d.period)
    out=[]
    for (o,m),g in d.groupby(["forecast_origin","material"]):
        g=g.sort_values("period"); assert len(g)==12
        out.append((o,m,g.order_qty.to_numpy(float)))
    assert len(out)==44
    return out

def load_o4():
    out=[]
    for o in ORIGINS:
        for m in MATERIALS:
            p=O4/f"O4_{o:%Y-%m-%d}_{m.replace(' ','_')}_pareto.csv"
            d=pd.read_csv(p); s=d[d.selected.astype(bool)]; assert len(s)==1
            out.append((o,m,parse_q(s.iloc[0].q)))
    assert len(out)==44
    return out

def simulate(qs,realized,rate,controller):
    rows=[]
    for o,m,q in qs:
        sub=realized[(realized.forecast_origin==o)&(realized.material==m)].sort_values("period")
        assert len(sub)==12
        inv=0.
        for j,(_,r) in enumerate(sub.iterrows()):
            period=pd.Timestamp(r.period); available=0.
            for s in range(j+1):
                op=pd.Timestamp(sub.iloc[s].period)
                if period>=op+pd.Timedelta(days=DURATION): available+=q[s]
            dem=float(r.realized_demand); price=float(r.realized_price); order=float(q[j])
            net=inv+available; shortage=max(0.,dem-max(0.,net)); ending=max(0.,net-dem)
            rows.append(dict(controller=controller,holding_case=None,annual_holding_rate=rate*12,
                monthly_holding_rate=rate,forecast_origin=o,material=m,period=period,month_ahead=j+1,
                realized_demand=dem,realized_price=price,order_quantity=order,ending_inventory=ending,
                shortage_quantity=shortage,procurement_cost=order*price,holding_cost=rate*price*ending))
            inv=ending
    return pd.DataFrame(rows)

def main():
    print("CMIDO RO3.8 — ROBUSTNESS / HOLDING-RATE SENSITIVITY")
    realized=load_realized(); q=load_o1o3(); q["O2"]=load_o2(); q["O4"]=load_o4()
    print("Policies loaded:",{k:len(v) for k,v in q.items()})
    all_led=[]
    for label,rate in RATES.items():
        for c in ["O1","O2","O3","O4"]:
            x=simulate(q[c],realized,rate,c); x.holding_case=label; all_led.append(x)
    led=pd.concat(all_led,ignore_index=True)
    origin=led.groupby(["controller","holding_case","annual_holding_rate","forecast_origin"],as_index=False).agg(
        procurement_cost=("procurement_cost","sum"),holding_cost=("holding_cost","sum"),
        shortage=("shortage_quantity","sum"),demand=("realized_demand","sum"),
        procurement_quantity=("order_quantity","sum"),mean_ending_inventory=("ending_inventory","mean"),
        procurement_events=("order_quantity",lambda x:int((x>1e-9).sum())))
    origin["cost"]=origin.procurement_cost+origin.holding_cost
    origin["service"]=1-origin.shortage/origin.demand
    summary=origin.groupby(["controller","holding_case","annual_holding_rate"],as_index=False).agg(
        n_origins=("forecast_origin","nunique"),mean_cost=("cost","mean"),median_cost=("cost","median"),
        mean_shortage=("shortage","mean"),median_shortage=("shortage","median"),
        mean_service=("service","mean"),median_service=("service","median"),
        mean_inventory=("mean_ending_inventory","mean"),mean_procurement_quantity=("procurement_quantity","mean"),
        mean_events=("procurement_events","mean"))
    # Controller contrasts at each rate, origin-paired.
    contrasts=[]
    for case in RATES:
        wide=origin[origin.holding_case==case].pivot(index="forecast_origin",columns="controller")
        for c in ["O2","O3","O4"]:
            for metric in ["cost","shortage","service"]:
                dd=wide[(metric,c)]-wide[(metric,"O1")]
                contrasts.append(dict(holding_case=case,contrast=f"{c}_vs_O1",metric=metric,
                    mean_difference=dd.mean(),median_difference=dd.median(),
                    min_difference=dd.min(),max_difference=dd.max()))
    contrasts=pd.DataFrame(contrasts)
    base=origin[origin.holding_case=="H30"].set_index(["controller","forecast_origin"])
    sens=[]
    for case in ["H20","H40"]:
        cur=origin[origin.holding_case==case].set_index(["controller","forecast_origin"])
        for c in ["O1","O2","O3","O4"]:
            for metric in ["cost","shortage","service"]:
                dd=cur.loc[c,metric]-base.loc[c,metric]
                sens.append(dict(controller=c,comparison=f"{case}_vs_H30",metric=metric,
                    mean_difference=dd.mean(),median_difference=dd.median(),
                    min_difference=dd.min(),max_difference=dd.max()))
    sens=pd.DataFrame(sens)

    checks=[]
    def ck(n,v,d=""):
        checks.append((n,bool(v),d)); print("[PASS]" if v else "[FAIL]",n,d)
    ck("44 policies/controller",all(len(v)==44 for v in q.values()))
    ck("3 holding-rate cases",set(led.holding_case)==set(RATES))
    ck("11 origins/controller/case",origin.groupby(["controller","holding_case"]).forecast_origin.nunique().eq(11).all())
    ck("12 months/material-origin/case",led.groupby(["controller","holding_case","forecast_origin","material"]).size().eq(12).all())
    ck("Finite primary metrics",np.isfinite(origin[["cost","shortage","service"]].to_numpy()).all())
    ck("Service in [0,1]",((origin.service>=0)&(origin.service<=1)).all())
    ck("Nonnegative quantities",(led[["order_quantity","ending_inventory","shortage_quantity"]]>=-1e-9).all().all())
    ck("Same realized demand",led.groupby(["controller","holding_case","forecast_origin","material","month_ahead"]).realized_demand.nunique().max()==1)
    ck("Same realized price",led.groupby(["controller","holding_case","forecast_origin","material","month_ahead"]).realized_price.nunique().max()==1)
    ck("Orders unchanged across holding rates",led.groupby(["controller","forecast_origin","material","month_ahead"]).order_quantity.nunique().max()==1)
    ck("Shortage unchanged across holding rates",led.groupby(["controller","forecast_origin","material","month_ahead"]).shortage_quantity.nunique().max()==1)
    ck("Inventory unchanged across holding rates",led.groupby(["controller","forecast_origin","material","month_ahead"]).ending_inventory.nunique().max()==1)
    audit=pd.DataFrame(checks,columns=["check","passed","detail"])
    status="PASS" if audit.passed.all() else "HOLD"
    led.to_csv(OUT/"RO3_step38_holding_rate_monthly_ledger.csv",index=False)
    origin.to_csv(OUT/"RO3_step38_holding_rate_origin_results.csv",index=False)
    summary.to_csv(OUT/"RO3_step38_holding_rate_summary.csv",index=False)
    contrasts.to_csv(OUT/"RO3_step38_holding_rate_controller_contrasts.csv",index=False)
    sens.to_csv(OUT/"RO3_step38_holding_rate_sensitivity_vs_H30.csv",index=False)
    audit.to_csv(OUT/"RO3_step38_holding_rate_audit.csv",index=False)
    print("\nSUMMARY"); print(summary.to_string(index=False))
    print("\nCONTROLLER CONTRASTS VS O1"); print(contrasts.to_string(index=False))
    print("\nSENSITIVITY VS H30"); print(sens.to_string(index=False))
    print("\nCHECKS:",int(audit.passed.sum()),"/",len(audit),"STATUS:",status)
    print("OUTPUT:",OUT)

if __name__=="__main__": main()
