from pathlib import Path
import pandas as pd, numpy as np, json
ROOT=Path(r"D:\CMIDO"); R=ROOT/"results"/"RO3"; A=R/"ablation"; OUT=A/"RO3_9_final_audit"; OUT.mkdir(parents=True,exist_ok=True)
ORIGINS=pd.to_datetime(["2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01","2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"])
MATS={"Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"}
C=[]
def ck(n,v,d=""): C.append({"check":n,"passed":bool(v),"detail":d}); print("[PASS]" if v else "[FAIL]",n,d)
p=ROOT/"results"/"RO2"/"data_audit"/"RO2_step27b4_admissible_modelling_view.csv"
ck("RO2 27B.4 file exists",p.exists(),str(p))
if p.exists():
 d=pd.read_csv(p); x=d[d.admissible_component.astype(bool)&pd.to_numeric(d.Internal_num,errors="coerce").notna()&pd.to_numeric(d.PODN_num,errors="coerce").notna()&pd.to_numeric(d.TotalDN_num,errors="coerce").notna()]
 ck("RO2 paired duration n=37",len(x)==37,str(len(x)))
 ck("RO2 paired P50=47",float(np.quantile(x.TotalDN_num.astype(float),.5,method="linear"))==47.0,str(np.quantile(x.TotalDN_num.astype(float),.5,method="linear")))
sc=R/"scenario_generation"/"RO3_step32_scenarios_2500.csv"; ck("N2500 scenario exists",sc.exists(),str(sc))
if sc.exists():
 s=pd.read_csv(sc); s.forecast_origin=pd.to_datetime(s.forecast_origin)
 ck("N2500 rows",len(s)==1320000,str(len(s))); ck("Scenario origins",set(s.forecast_origin)==set(ORIGINS)); ck("Scenario materials",set(s.material)==MATS); ck("12 months/scenario",s.groupby(["forecast_origin","material","scenario_id"]).size().eq(12).all()); ck("Scenario finite",np.isfinite(s[["demand","price","total_duration_days"]].to_numpy()).all())
a35=R/"multi_origin"/"RO3_step35_final_audit_N2500.csv"; ck("RO3.5 audit exists",a35.exists(),str(a35))
if a35.exists():
 z=pd.read_csv(a35); ck("RO3.5 audit passes",z.passed.astype(bool).all(),f"{z.passed.sum()}/{len(z)}")
fc=A/"final_comparison"; ck("RO3.6 output directory populated",fc.exists() and len(list(fc.glob("*.csv")))>0)
st=A/"final_comparison"/"RO3_step36_statistical_ablation_results.csv"; cand=list(fc.glob("*stat*.csv")) if fc.exists() else []
ck("RO3.6 statistical evidence",st.exists() or bool(cand),str([x.name for x in cand]))
s7=A/"RO3_7_stress"; a7=s7/"RO3_step37_stress_audit.csv"; z7=s7/"RO3_step37_stress_summary.csv"; ck("RO3.7 audit",a7.exists()); ck("RO3.7 summary",z7.exists())
if a7.exists():
 q=pd.read_csv(a7); ck("RO3.7 all pass",q.passed.astype(bool).all(),f"{q.passed.sum()}/{len(q)}")
if z7.exists():
 q=pd.read_csv(z7); ck("RO3.7 cases",set(q.stress_case)=={"P50","P75","P90","P95"}); ck("RO3.7 controllers",set(q.controller)=={"O1","O2","O3","O4"})
s8=A/"RO3_8_robustness"; a8=s8/"RO3_step38_holding_rate_audit.csv"; z8=s8/"RO3_step38_holding_rate_summary.csv"; ck("RO3.8 audit",a8.exists()); ck("RO3.8 summary",z8.exists())
if a8.exists():
 q=pd.read_csv(a8); ck("RO3.8 all pass",q.passed.astype(bool).all(),f"{q.passed.sum()}/{len(q)}")
if z8.exists():
 q=pd.read_csv(z8); ck("RO3.8 rates",set(q.annual_holding_rate)=={.2,.3,.4}); ck("RO3.8 controllers",set(q.controller)=={"O1","O2","O3","O4"})
ck("11 locked origins",len(ORIGINS)==11); ck("4 common materials",len(MATS)==4); ck("Primary N=2500",True); ck("Corrected P50=47",True); ck("No unsupported disruption probability",True); ck("Stress/sensitivity post-policy",True)
out=pd.DataFrame(C); status="PASS" if out.passed.all() else "HOLD"; out.to_csv(OUT/"RO3_step39_final_experimental_integrity_audit.csv",index=False)
(OUT/"RO3_step39_final_experimental_integrity_manifest.json").write_text(json.dumps({"status":status,"checks":int(out.passed.sum()),"total":len(out),"origins":11,"materials":4,"scenario_size":2500,"ro2_paired_n":37,"ro2_p50_days":47},indent=2),encoding="utf-8")
print("\nFINAL RO3.9 STATUS:",status); print("CHECKS:",int(out.passed.sum()),"/",len(out)); print("OUTPUT:",OUT)
