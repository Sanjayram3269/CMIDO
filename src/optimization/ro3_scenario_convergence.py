from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SCEN_DIR=ROOT/"results"/"RO3"/"scenario_generation"
OUT_DIR=ROOT/"results"/"RO3"/"scenario_convergence"
OUT_DIR.mkdir(parents=True,exist_ok=True)

SIZES=[100,250,500,1000,2500,5000]
MATERIALS=["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
ORIGINS=["2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01","2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"]
REQ=["scenario_id","forecast_origin","material","period","month_ahead","demand","price","internal_duration_days","podn_duration_days","total_duration_days","scenario_set_size","stream_id"]
NUM=["scenario_id","month_ahead","demand","price","internal_duration_days","podn_duration_days","total_duration_days","scenario_set_size"]
EPS=1e-12

def load(n):
    p=SCEN_DIR/f"RO3_step32_scenarios_{n}.csv"
    if not p.exists(): raise FileNotFoundError(p)
    print(f"[LOAD] {n:,} scenarios -> {p.name}",flush=True)
    d=pd.read_csv(p,usecols=REQ)
    if len(d)!=11*4*12*n: raise ValueError(f"{p.name}: bad row count {len(d)}")
    d["forecast_origin"]=pd.to_datetime(d["forecast_origin"]).dt.strftime("%Y-%m-%d")
    d["period"]=pd.to_datetime(d["period"])
    for c in NUM: d[c]=pd.to_numeric(d[c],errors="coerce")
    if sorted(d.forecast_origin.unique())!=ORIGINS: raise ValueError(f"{p.name}: origins changed")
    if sorted(d.material.unique())!=sorted(MATERIALS): raise ValueError(f"{p.name}: materials changed")
    if set(d.scenario_set_size.unique())!={n}: raise ValueError(f"{p.name}: scenario_set_size mismatch")
    if not np.isfinite(d[NUM].to_numpy()).all(): raise ValueError(f"{p.name}: non-finite values")
    if not d.month_ahead.between(1,12).all(): raise ValueError(f"{p.name}: invalid month_ahead")
    if not (d.internal_duration_days+d.podn_duration_days-d.total_duration_days).abs().le(1e-9).all():
        raise ValueError(f"{p.name}: duration reconstruction failure")
    c=d.groupby(["stream_id","scenario_id"],sort=False).month_ahead.agg(["count","nunique","min","max"])
    if not ((c["count"]==12)&(c["nunique"]==12)&(c["min"]==1)&(c["max"]==12)).all():
        raise ValueError(f"{p.name}: invalid scenario paths")
    print(f"[LOAD] {n:,}: validated {len(d):,} rows",flush=True)
    return d

def direct_metrics(d):
    g=d.groupby(["material","forecast_origin"],sort=True)
    out=[]
    for (mat,origin),x in g:
        out.extend([
            [mat,origin,"mean_demand",x.demand.mean()],
            [mat,origin,"mean_price",x.price.mean()],
            [mat,origin,"mean_internal_duration",x.internal_duration_days.mean()],
            [mat,origin,"mean_podn_duration",x.podn_duration_days.mean()],
            [mat,origin,"mean_total_duration",x.total_duration_days.mean()],
            [mat,origin,"q90_demand",x.demand.quantile(.90)],
            [mat,origin,"q90_price",x.price.quantile(.90)],
            [mat,origin,"q90_internal_duration",x.internal_duration_days.quantile(.90)],
            [mat,origin,"q90_podn_duration",x.podn_duration_days.quantile(.90)],
            [mat,origin,"q90_total_duration",x.total_duration_days.quantile(.90)],
        ])
    return pd.DataFrame(out,columns=["material","forecast_origin","metric","value"])

def exposure_metrics(d):
    # Vectorized exact calendar-day overlap.
    # Each row contributes demand weighted by the number of days of its month
    # covered by the procurement window [first_period, first_period+duration].
    key=["stream_id","scenario_id"]
    first=d[d.month_ahead==1][key+["period","total_duration_days"]].copy()
    first=first.rename(columns={"period":"start","total_duration_days":"duration"})
    x=d.merge(first,on=key,how="left",validate="many_to_one")
    x["end"]=x["start"]+pd.to_timedelta(x["duration"],unit="D")
    ms=x["period"].dt.to_period("M").dt.to_timestamp()
    me=(x["period"].dt.to_period("M")+1).dt.to_timestamp()
    a=pd.concat([x["start"],ms],axis=1).max(axis=1)
    b=pd.concat([x["end"],me],axis=1).min(axis=1)
    covered=((b-a).dt.total_seconds()/86400).clip(lower=0)
    mdays=(me-ms).dt.total_seconds()/86400
    x["weighted_demand"]=x["demand"]*covered/mdays
    e=x.groupby(key,sort=False).weighted_demand.sum().reset_index(name="exposure")
    meta=x[key+["material","forecast_origin"]].drop_duplicates(key)
    e=e.merge(meta,on=key,how="left",validate="one_to_one")
    g=e.groupby(["material","forecast_origin"],sort=True).exposure
    rows=[]
    for (mat,origin),z in g:
        rows.extend([
            [mat,origin,"mean_exposure",z.mean()],
            [mat,origin,"q90_exposure",z.quantile(.90)],
            [mat,origin,"q95_exposure",z.quantile(.95)],
            [mat,origin,"q99_exposure",z.quantile(.99)],
        ])
    return pd.DataFrame(rows,columns=["material","forecast_origin","metric","value"])

def main():
    data={}
    for n in SIZES:
        data[n]=load(n)

    print("[AUDIT] Checking nested scenario prefixes...",flush=True)
    compare_cols=["scenario_id","month_ahead","demand","price","internal_duration_days","podn_duration_days","total_duration_days"]
    for a,b in zip(SIZES[:-1],SIZES[1:]):
        da=data[a].sort_values(["stream_id","scenario_id","month_ahead"]).reset_index(drop=True)
        db=data[b].sort_values(["stream_id","scenario_id","month_ahead"]).reset_index(drop=True)
        for stream in da.stream_id.unique():
            xa=da[da.stream_id==stream].sort_values(["scenario_id","month_ahead"]).reset_index(drop=True)
            xb=db[db.stream_id==stream].sort_values(["scenario_id","month_ahead"]).reset_index(drop=True)
            if not xa[compare_cols].reset_index(drop=True).equals(xb.iloc[:len(xa)][compare_cols].reset_index(drop=True)):
                raise ValueError(f"Nested-prefix failure {a}->{b}, {stream}")
    print("[AUDIT] Nestedness PASS",flush=True)

    allm=[]
    for n in SIZES:
        print(f"[METRICS] Calculating {n:,}-scenario metrics...",flush=True)
        m=pd.concat([direct_metrics(data[n]),exposure_metrics(data[n])],ignore_index=True)
        m["n_scenarios"]=n
        allm.append(m)
        print(f"[METRICS] {n:,} complete",flush=True)
    ms=pd.concat(allm,ignore_index=True)

    thresholds={
        "mean_demand":.01,"mean_price":.01,"mean_internal_duration":.01,"mean_podn_duration":.01,"mean_total_duration":.01,
        "q90_demand":.02,"q90_price":.02,"q90_internal_duration":.02,"q90_podn_duration":.02,"q90_total_duration":.02,
        "mean_exposure":.01,"q90_exposure":.02,"q95_exposure":.02,"q99_exposure":.05}

    out=[]
    for a,b in zip(SIZES[:-1],SIZES[1:]):
        x=ms[ms.n_scenarios==a].set_index(["material","forecast_origin","metric"]).value
        y=ms[ms.n_scenarios==b].set_index(["material","forecast_origin","metric"]).value
        for idx in x.index:
            va,vb=float(x.loc[idx]),float(y.loc[idx])
            rel=abs(vb-va)/max(abs(va),EPS)
            metric=idx[2]
            out.append([idx[0],idx[1],metric,a,b,va,vb,rel,thresholds[metric],rel<=thresholds[metric]])
    comp=pd.DataFrame(out,columns=["material","forecast_origin","metric","n_from","n_to","value_from","value_to","relative_change","threshold","pass"])
    primary=comp[(comp.n_from==500)&(comp.n_to==1000)]
    later=comp[comp.n_from>=1000]
    pp=bool(primary["pass"].all())
    decision="RO3_3_LOCK_1000" if pp else "RO3_3_EVALUATE_2500"
    summary={"scenario_sizes":SIZES,"material_origin_cases":44,"primary_transition":"500_to_1000","primary_pass":pp,
             "primary_failed_comparisons":int((~primary["pass"]).sum()),"primary_max_relative_change":float(primary.relative_change.max()),
             "later_max_relative_change":float(later.relative_change.max()),"decision":decision,
             "optimization_level_convergence_required_later":True}
    ms.to_csv(OUT_DIR/"RO3_step33_convergence_metrics.csv",index=False)
    comp.to_csv(OUT_DIR/"RO3_step33_convergence_comparisons.csv",index=False)
    (OUT_DIR/"RO3_step33_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    (OUT_DIR/"RO3_step33_decision.txt").write_text(decision+"\n",encoding="utf-8")
    print("="*78); print("CMIDO RO3.3 — OPTIMIZED SCENARIO-SET CONVERGENCE"); print("="*78)
    print("Scenario sizes:",SIZES); print("Material-origin cases: 44")
    print("Primary 500 -> 1000:", "PASS" if pp else "FAIL")
    print("Primary failed comparisons:",int((~primary["pass"]).sum()))
    print(f"Primary max relative change: {primary.relative_change.max():.6f}")
    print(f"Later max relative change: {later.relative_change.max():.6f}")
    print("DECISION:",decision)

if __name__=="__main__": main()
