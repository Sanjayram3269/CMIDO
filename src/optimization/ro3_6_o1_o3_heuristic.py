from pathlib import Path
import json, math
import numpy as np
import pandas as pd

ROOT=Path(r"D:\CMIDO")
RAW=ROOT/"data"/"raw"
FORECAST=ROOT/"results"/"forecasting"/"probabilistic_calibration"/"RO1_step26c3_validation_forecasts.csv"
OUT=ROOT/"results"/"RO3"/"ablation"/"O1_O3"
OUT.mkdir(parents=True,exist_ok=True)

ORIGINS=pd.to_datetime([
"2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
"2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"])
MATS=["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
PRICE_MAP={
"Cement":"Cement In Bulk (Ordinary Portland Cement)",
"Steel Reinforcement Bars":"Steel Reinforcement Bars (16-32mm High Tensile)",
"Granite":"Granite (20mm Aggregate)",
"Ready Mixed Concrete":"Ready Mixed Concrete"}
DEMAND_MAP={
"Cement":"Cement","Steel Reinforcement Bars":"Steel Reinforcement Bars",
"Granite":"Granite","Ready Mixed Concrete":"Ready-Mixed Concrete"}
SOURCE_H=[1,3,6,12]
LEAD_DAYS=49
HOLD_RATE=0.025

def raw_long(path):
    x=pd.read_csv(path)
    c=x.columns[0]
    z=x.melt(id_vars=[c],var_name="raw_date",value_name="value").rename(columns={c:"raw_material"})
    z["date"]=pd.to_datetime(z.raw_date.astype(str),format="%Y%b",errors="coerce")
    z["value"]=pd.to_numeric(z.value,errors="coerce")
    return z.dropna(subset=["date"])

def interp_quantile(rows,h,q):
    a=rows.sort_values("horizon")
    return float(np.interp(h,SOURCE_H,a[q].to_numpy(dtype=float)))

def main():
    f=pd.read_csv(FORECAST)
    f["forecast_origin"]=pd.to_datetime(f.forecast_origin)
    f["target_date"]=pd.to_datetime(f.target_date)

    d=raw_long(RAW/"DemandForConstructionMaterialsMonthly.csv")
    p=raw_long(RAW/"ConstructionMaterialMarketPricesMonthly.csv")

    led=[]; summaries=[]
    for origin in ORIGINS:
        for mat in MATS:
            dates=pd.date_range(origin+pd.offsets.MonthBegin(1),periods=12,freq="MS")
            fd=f[(f.dataset=="RO1_DEMAND")&f.series.eq(mat)&f.forecast_origin.eq(origin)&f.horizon.isin(SOURCE_H)].copy()
            fp=f[(f.dataset=="RO1_PRICE")&f.series.eq(mat)&f.forecast_origin.eq(origin)&f.horizon.isin(SOURCE_H)].copy()
            if len(fd)!=4 or len(fp)!=4:
                raise RuntimeError(f"Incomplete source horizons for {mat} {origin.date()}: demand={len(fd)} price={len(fp)}")
            demand_rows=d[(d.raw_material==DEMAND_MAP[mat])&d.date.isin(dates)].set_index("date")
            price_rows=p[(p.raw_material==PRICE_MAP[mat])&p.date.isin(dates)].set_index("date")
            if len(demand_rows)!=12 or len(price_rows)!=12:
                raise RuntimeError(f"Incomplete realization for {mat} {origin.date()}")

            for controller in ["O1","O3"]:
                inventory=0.0
                orders=[]
                total_proc=total_hold=total_short=0.0
                total_qty=0.0
                events=0
                for h,date in enumerate(dates,1):
                    # Realize only orders that have actually arrived by this
                    # monthly decision date.
                    arrived=[o for o in orders if o["arrival_date"]<=date and not o["received"]]
                    received_qty=sum(o["qty"] for o in arrived)
                    for o in arrived: o["received"]=True
                    inventory += received_qty

                    q50=interp_quantile(fd,h,"q50")
                    q90=interp_quantile(fd,h,"q90")
                    target=q50 if controller=="O1" else q90
                    order_qty=max(0.0,target-inventory)

                    if order_qty>0:
                        events+=1
                        arrival=date+pd.Timedelta(days=LEAD_DAYS)
                        orders.append({"arrival_date":arrival,"qty":order_qty,"received":False})
                    actual_d=float(demand_rows.loc[date,"value"])
                    price=float(price_rows.loc[date,"value"])
                    short=max(0.0,actual_d-inventory)
                    ending=max(0.0,inventory-actual_d)
                    proc=order_qty*price
                    hold=HOLD_RATE*ending*price

                    total_proc+=proc; total_hold+=hold; total_short+=short
                    total_qty+=order_qty
                    led.append({
                        "controller":controller,"forecast_origin":origin.strftime("%Y-%m-%d"),
                        "material":mat,"period":date.strftime("%Y-%m-%d"),"month_ahead":h,
                        "forecast_q50":q50,"forecast_q90":q90,"target":target,
                        "opening_inventory":inventory,"order_quantity":order_qty,
                        "order_arrival_date":(date+pd.Timedelta(days=LEAD_DAYS)).strftime("%Y-%m-%d"),
                        "realized_demand":actual_d,"realized_price":price,
                        "ending_inventory":ending,"shortage_quantity":short,
                        "procurement_cost":proc,"holding_cost":hold})
                    inventory=ending

                summaries.append({
                    "controller":controller,"forecast_origin":origin.strftime("%Y-%m-%d"),
                    "material":mat,"procurement_cost":total_proc,
                    "holding_cost":total_hold,"procurement_holding_cost":total_proc+total_hold,
                    "total_shortage":total_short,"total_procurement_quantity":total_qty,
                    "mean_ending_inventory":float(np.mean([r["ending_inventory"] for r in led if r["controller"]==controller and r["forecast_origin"]==origin.strftime("%Y-%m-%d") and r["material"]==mat])),
                    "procurement_events":events,
                })

    ledger=pd.DataFrame(led)
    sm=pd.DataFrame(summaries)
    origin=sm.groupby(["controller","forecast_origin"],as_index=False).agg(
        procurement_holding_cost=("procurement_holding_cost","sum"),
        total_shortage=("total_shortage","sum"),
        total_procurement_quantity=("total_procurement_quantity","sum"),
        mean_ending_inventory=("mean_ending_inventory","mean"),
        procurement_events=("procurement_events","sum"))
    realized_d=ledger.groupby(["controller","forecast_origin"])["realized_demand"].sum().reset_index(name="total_realized_demand")
    origin=origin.merge(realized_d,on=["controller","forecast_origin"])
    origin["service_level"]=1-origin["total_shortage"]/origin["total_realized_demand"]

    ledger.to_csv(OUT/"RO3_step36_O1_O3_monthly_ledger.csv",index=False)
    sm.to_csv(OUT/"RO3_step36_O1_O3_material_summary.csv",index=False)
    origin.to_csv(OUT/"RO3_step36_O1_O3_origin_summary.csv",index=False)

    manifest={"controllers":["O1","O3"],"origins":11,"materials":4,"months_per_origin":12,
              "lead_time_days":LEAD_DAYS,"holding_rate_monthly":HOLD_RATE,
              "forecast_source":str(FORECAST),"status":"EXECUTION_COMPLETE"}
    (OUT/"RO3_step36_O1_O3_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("="*78); print("CMIDO RO3.6 — O1/O3 HEURISTIC EXECUTION")
    print("="*78)
    print(origin.groupby("controller")[["procurement_holding_cost","total_shortage","service_level"]].agg(["mean","median"]).to_string())
    print(f"\nRows ledger: {len(ledger)}")
    print("STATUS: EXECUTION_COMPLETE")
    print(f"Outputs: {OUT}")
    print("="*78)

if __name__=="__main__": main()
