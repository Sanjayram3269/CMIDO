from pathlib import Path
import json
import numpy as np
import pandas as pd
from pyomo.environ import ConcreteModel, Var, Objective, Constraint, NonNegativeReals, minimize, SolverFactory, value

ROOT=Path(r"D:\CMIDO")
RAW=ROOT/"data"/"raw"
FORECAST=ROOT/"results"/"forecasting"/"probabilistic_calibration"/"RO1_step26c3_validation_forecasts.csv"
OUT=ROOT/"results"/"RO3"/"ablation"/"O2"
OUT.mkdir(parents=True,exist_ok=True)

ORIGINS=pd.to_datetime(["2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01","2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"])
MATS=["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
PRICE_MAP={"Cement":"Cement In Bulk (Ordinary Portland Cement)","Steel Reinforcement Bars":"Steel Reinforcement Bars (16-32mm High Tensile)","Granite":"Granite (20mm Aggregate)","Ready Mixed Concrete":"Ready Mixed Concrete"}
DEMAND_MAP={"Cement":"Cement","Steel Reinforcement Bars":"Steel Reinforcement Bars","Granite":"Granite","Ready Mixed Concrete":"Ready-Mixed Concrete"}
H=[1,3,6,12]; LEAD=49; HOLD=.025

def raw_long(path):
    x=pd.read_csv(path); c=x.columns[0]
    z=x.melt(id_vars=[c],var_name="raw_date",value_name="value").rename(columns={c:"raw_material"})
    z["date"]=pd.to_datetime(z.raw_date.astype(str),format="%Y%b",errors="coerce")
    z["value"]=pd.to_numeric(z.value,errors="coerce")
    return z.dropna(subset=["date"])

def qinterp(rows,h,col):
    a=rows.sort_values("horizon")
    return float(np.interp(h,H,a[col].to_numpy(float)))

def solve(demand,price):
    m=ConcreteModel()
    T=range(1,13)
    m.q=Var(T,domain=NonNegativeReals)
    m.I=Var(T,domain=NonNegativeReals)
    m.z=Var(T,domain=NonNegativeReals)
    # 49 days from a month-start places the order in the first decision
    # month at/after arrival: t-2 for t>=3.
    def bal(mm,t):
        arrivals=mm.q[t-2] if t>=3 else 0
        prev=mm.I[t-1] if t>1 else 0
        return mm.I[t] == prev + arrivals - demand[t-1] + mm.z[t]
    m.balance=Constraint(T,rule=bal)
    m.obj=Objective(expr=sum(m.q[t]*price[t-1]+HOLD*m.I[t]*price[t-1] for t in T),sense=minimize)
    res=SolverFactory("highs").solve(m)
    if str(res.solver.termination_condition).lower()!="optimal":
        raise RuntimeError(f"HiGHS did not return optimal: {res.solver.termination_condition}")
    return {t:float(value(m.q[t])) for t in T},{t:float(value(m.I[t])) for t in T},{t:float(value(m.z[t])) for t in T},float(value(m.obj))

def main():
    f=pd.read_csv(FORECAST); f["forecast_origin"]=pd.to_datetime(f.forecast_origin)
    demand_raw=raw_long(RAW/"DemandForConstructionMaterialsMonthly.csv")
    price_raw=raw_long(RAW/"ConstructionMaterialMarketPricesMonthly.csv")
    rows=[]; sums=[]; diag=[]
    for origin in ORIGINS:
      for mat in MATS:
        dates=pd.date_range(origin+pd.offsets.MonthBegin(1),periods=12,freq="MS")
        fd=f[(f.dataset=="RO1_DEMAND")&f.series.eq(mat)&f.forecast_origin.eq(origin)&f.horizon.isin(H)]
        fp=f[(f.dataset=="RO1_PRICE")&f.series.eq(mat)&f.forecast_origin.eq(origin)&f.horizon.isin(H)]
        if len(fd)!=4 or len(fp)!=4: raise RuntimeError(f"Missing horizons {origin} {mat}")
        dh=[qinterp(fd,h,"q50") for h in range(1,13)]
        ph=[qinterp(fp,h,"q50") for h in range(1,13)]
        q,I,z,opt=solve(dh,ph)
        rd=demand_raw[(demand_raw.raw_material==DEMAND_MAP[mat])&demand_raw.date.isin(dates)].set_index("date")
        rp=price_raw[(price_raw.raw_material==PRICE_MAP[mat])&price_raw.date.isin(dates)].set_index("date")
        inv=0.; total_proc=total_hold=total_short=0.; total_qty=0.; events=0
        orders=[]
        for t,date in enumerate(dates,1):
            arrived=[o for o in orders if o["arrival"]<=date and not o["received"]]
            inv+=sum(o["qty"] for o in arrived)
            for o in arrived:o["received"]=True
            qty=q[t]
            if qty>1e-9: events+=1; orders.append({"arrival":date+pd.Timedelta(days=LEAD),"qty":qty,"received":False})
            actual=float(rd.loc[date,"value"]); rpv=float(rp.loc[date,"value"])
            short=max(0.,actual-inv); end=max(0.,inv-actual)
            pc=qty*rpv; hc=HOLD*end*rpv
            rows.append({"controller":"O2","forecast_origin":origin.strftime("%Y-%m-%d"),"material":mat,"period":date.strftime("%Y-%m-%d"),"month_ahead":t,
              "forecast_q50_demand":dh[t-1],"forecast_q50_price":ph[t-1],"optimized_order_quantity":qty,
              "optimized_planned_inventory":I[t],"optimized_planned_shortage":z[t],
              "realized_demand":actual,"realized_price":rpv,"ending_inventory":end,"shortage_quantity":short,
              "procurement_cost":pc,"holding_cost":hc,"order_arrival_date":(date+pd.Timedelta(days=LEAD)).strftime("%Y-%m-%d")})
            inv=end; total_proc+=pc; total_hold+=hc; total_short+=short; total_qty+=qty
        sums.append({"controller":"O2","forecast_origin":origin.strftime("%Y-%m-%d"),"material":mat,
          "deterministic_objective":opt,"realized_procurement_holding_cost":total_proc+total_hold,
          "realized_total_shortage":total_short,"realized_procurement_quantity":total_qty,
          "realized_mean_ending_inventory":float(np.mean([r["ending_inventory"] for r in rows if r["forecast_origin"]==origin.strftime("%Y-%m-%d") and r["material"]==mat])),
          "realized_procurement_events":events})
        diag.append({"forecast_origin":origin.strftime("%Y-%m-%d"),"material":mat,"deterministic_objective":opt,
          "planned_shortage":sum(z.values()),"planned_procurement":sum(q.values())})
    ledger=pd.DataFrame(rows); sm=pd.DataFrame(sums); dg=pd.DataFrame(diag)
    org=sm.groupby(["controller","forecast_origin"],as_index=False).agg(
      deterministic_objective=("deterministic_objective","sum"),procurement_holding_cost=("realized_procurement_holding_cost","sum"),
      total_shortage=("realized_total_shortage","sum"),total_procurement_quantity=("realized_procurement_quantity","sum"),
      mean_ending_inventory=("realized_mean_ending_inventory","mean"),procurement_events=("realized_procurement_events","sum"))
    totald=ledger.groupby(["controller","forecast_origin"]).realized_demand.sum().reset_index(name="total_realized_demand")
    org=org.merge(totald,on=["controller","forecast_origin"]); org["service_level"]=1-org.total_shortage/org.total_realized_demand
    ledger.to_csv(OUT/"RO3_step36_O2_monthly_ledger.csv",index=False); sm.to_csv(OUT/"RO3_step36_O2_material_summary.csv",index=False)
    org.to_csv(OUT/"RO3_step36_O2_origin_summary.csv",index=False); dg.to_csv(OUT/"RO3_step36_O2_solver_diagnostics.csv",index=False)
    manifest={"controller":"O2","origins":11,"materials":4,"horizon":12,"lead_days":49,"holding_rate":HOLD,"objective":"deterministic procurement + holding cost","solver":"HiGHS","status":"EXECUTION_COMPLETE"}
    (OUT/"RO3_step36_O2_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("="*78); print("CMIDO RO3.6 — O2 DETERMINISTIC OPTIMIZATION")
    print("="*78); print(org.groupby("controller")[["procurement_holding_cost","total_shortage","service_level"]].agg(["mean","median"]).to_string())
    print(f"\nOptimization cases: {len(diag)} | Ledger rows: {len(ledger)}"); print("STATUS: EXECUTION_COMPLETE"); print(f"Outputs: {OUT}"); print("="*78)

if __name__=="__main__": main()
