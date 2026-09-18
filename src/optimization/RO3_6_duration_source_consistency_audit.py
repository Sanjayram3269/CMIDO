from pathlib import Path
import pandas as pd

ROOT=Path(r"D:\CMIDO")
RO2=ROOT/"results"/"RO2"/"data_audit"/"RO2_step27b4_admissible_modelling_view.csv"
x=pd.read_csv(RO2)
paired=x[
    x["admissible_component"].astype(bool)
    & pd.to_numeric(x["Internal_num"],errors="coerce").notna()
    & pd.to_numeric(x["PODN_num"],errors="coerce").notna()
    & pd.to_numeric(x["TotalDN_num"],errors="coerce").notna()
]["TotalDN_num"].astype(float)

assert len(paired)==37
q50=float(paired.quantile(.5, interpolation="linear"))
q75=float(paired.quantile(.75, interpolation="linear"))
q90=float(paired.quantile(.9, interpolation="linear"))
q95=float(paired.quantile(.95, interpolation="linear"))

# Verify that 47 and 49 days induce exactly the same monthly availability
# mapping for the 11 locked origins and 12 monthly decision periods.
origins=pd.to_datetime([
"2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
"2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"
])
same=True
diffs=[]
for o in origins:
    periods=[o+pd.DateOffset(months=i) for i in range(12)]
    for j,t in enumerate(periods):
        a47=t+pd.Timedelta(days=47)
        a49=t+pd.Timedelta(days=49)
        m47=next((k for k,p in enumerate(periods) if p>=a47),None)
        m49=next((k for k,p in enumerate(periods) if p>=a49),None)
        if m47!=m49:
            same=False
            diffs.append((o,t,m47,m49))

print("RO3.6 DURATION-SOURCE CONSISTENCY AUDIT")
print("="*60)
print(f"Locked paired duration n: {len(paired)}")
print(f"P50: {q50:.6g} days")
print(f"P75: {q75:.6g} days")
print(f"P90: {q90:.6g} days")
print(f"P95: {q95:.6g} days")
print(f"Previously documented benchmark: 49 days")
print(f"47 vs 49 monthly availability mapping identical: {same}")
print(f"Mapping differences: {len(diffs)}")
if diffs:
    print(diffs[:10])
print()
print("DECISION:")
if q50==47 and same:
    print("CORRECTED_REFERENCE_47_DAYS_NO_REOPTIMIZATION_REQUIRED")
else:
    print("HOLD_FOR_REVIEW")
