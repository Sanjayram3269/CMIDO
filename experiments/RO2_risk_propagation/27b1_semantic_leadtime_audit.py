from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(r"D:\CMIDO")
SOURCE = ROOT / "data" / "raw" / "RO2_Data LeadTime.xlsx"
OUT = ROOT / "results" / "RO2" / "data_audit"
OUT.mkdir(parents=True, exist_ok=True)

DETAIL = OUT / "RO2_step27b1_semantic_detail.csv"
LEAD = OUT / "RO2_step27b1_leadtime_candidates.csv"
DATES = OUT / "RO2_step27b1_date_semantics.csv"
SUMMARY = OUT / "RO2_step27b1_semantic_audit_summary.txt"

def clean(c):
    return re.sub(r"\s+", " ", str(c).strip())

def norm(c):
    return re.sub(r"[^a-z0-9]+", "", clean(c).lower())

def find_cols(df, patterns):
    out=[]
    for c in df.columns:
        n=norm(c)
        if any(p in n for p in patterns):
            out.append(c)
    return out

def numeric(s):
    s=s.astype("string").str.strip()
    x=s.str.extract(r"([-+]?\d+(?:[.,]\d+)?)", expand=False)
    return pd.to_numeric(x.str.replace(",", ".", regex=False), errors="coerce")

def parse_dates(s):
    # Handle Excel datetime/date values and common Indonesian text dates.
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, errors="coerce")
    return pd.to_datetime(s, errors="coerce", dayfirst=True)

if not SOURCE.exists():
    raise FileNotFoundError(SOURCE)

xls=pd.ExcelFile(SOURCE)
detail=[]
lead=[]
date_rows=[]

print("="*90)
print("CMIDO — RO2 STEP 27B.1 SEMANTIC LEAD-TIME AUDIT")
print("="*90)
print(f"Source: {SOURCE}")
print("Read-only. No modelling, imputation, merging, or source modification.")
print()

for sheet in xls.sheet_names:
    df=pd.read_excel(SOURCE, sheet_name=sheet)
    df.columns=[clean(c) for c in df.columns]
    df=df.dropna(axis=1, how="all")

    print(f"[{sheet}] {len(df)} rows x {len(df.columns)} cols")

    for c in df.columns:
        n=norm(c)
        role=[]
        if any(x in n for x in ["supplier","vendor"]): role.append("SUPPLIER")
        if any(x in n for x in ["materialnumber","materialno","materialcode"]): role.append("MATERIAL_ID")
        if n in ["pr","prno","prnumber"] or "prnumber" in n: role.append("PR_ID")
        if n in ["po","pono","ponumber"] or "ponumber" in n: role.append("PO_ID")
        if any(x in n for x in ["tanggalpo","podate","purchaseorderdate"]): role.append("PO_DATE")
        if any(x in n for x in ["requisitiondate","tanggalrequisition"]): role.append("REQUISITION_DATE")
        if any(x in n for x in ["releasedate","tanggalrelease"]): role.append("RELEASE_DATE")
        if "totalleadtimeninternal" in n or "totalleadtimen" in n or "totalleadtimeinternal" in n:
            role.append("INTERNAL_LEADTIME")
        if "totalleadtime" in n:
            role.append("LEADTIME")
        if "realisasisla" in n or "dayssla" in n:
            role.append("REALIZED_SLA")
        if "standardsla" in n:
            role.append("STANDARD_SLA")
        if any(x in n for x in ["pogr","goodsreceipt","grdate","tanggalterima","tglterima","receiveddate","receiptdate","arrivaldate","deliverydate"]):
            role.append("RECEIPT_DELIVERY")
        if "totalharikerjaalldn" in n: role.append("TOTAL_WORKDAYS_DN")
        if "totalharikerjaallln" in n: role.append("TOTAL_WORKDAYS_LN")
        if role:
            nonmissing=int(df[c].notna().sum())
            detail.append({
                "sheet":sheet,"column":c,"roles":";".join(sorted(set(role))),
                "rows":len(df),"nonmissing":nonmissing,
                "missing":len(df)-nonmissing,
                "unique_nonmissing":int(df[c].dropna().nunique())
            })

    # Print only semantically important columns.
    important=[r for r in detail if r["sheet"]==sheet]
    if important:
        print("  identified fields:")
        for r in important:
            print(f"    {r['column']} -> {r['roles']} (nonmissing {r['nonmissing']}/{r['rows']})")

    # Candidate lead-time variables: explicit names, not fuzzy SLA labels only.
    candidate_cols=[]
    for c in df.columns:
        n=norm(c)
        if any(x in n for x in [
            "totalleadtime","leadtimeinternal","realisasisla","dayssla",
            "totalslarealisasidays","totalharikerjaalldn","totalharikerjaallln",
            "totalbulanall"
        ]):
            candidate_cols.append(c)

    for c in candidate_cols:
        x=numeric(df[c])
        v=x.dropna()
        lead.append({
            "sheet":sheet,"column":c,"n_rows":len(df),"n_numeric":len(v),
            "missing_or_unparseable":len(df)-len(v),
            "min":float(v.min()) if len(v) else np.nan,
            "q25":float(v.quantile(.25)) if len(v) else np.nan,
            "median":float(v.median()) if len(v) else np.nan,
            "mean":float(v.mean()) if len(v) else np.nan,
            "q75":float(v.quantile(.75)) if len(v) else np.nan,
            "q95":float(v.quantile(.95)) if len(v) else np.nan,
            "max":float(v.max()) if len(v) else np.nan,
            "zero_count":int((v==0).sum()) if len(v) else 0,
            "negative_count":int((v<0).sum()) if len(v) else 0
        })

    # Date fields and explicit date-derived durations.
    parsed={}
    for c in df.columns:
        n=norm(c)
        if any(x in n for x in [
            "date","tanggal","tgl","delivery","receipt","received","arrival","pogr","gr"
        ]):
            p=parse_dates(df[c])
            if p.notna().sum()>=2:
                parsed[c]=p
                date_rows.append({
                    "sheet":sheet,"column":c,"n_parseable":int(p.notna().sum()),
                    "min_date":str(p.min()),"max_date":str(p.max())
                })

    # Exact requisition -> PO duration where both fields exist.
    req=None; po=None
    for c in df.columns:
        n=norm(c)
        if req is None and ("requisitiondate" in n or "tanggalrequisition" in n):
            req=c
        if po is None and ("tanggalpo" in n or n in ["podate","purchaseorderdate"]):
            po=c
    if req and po:
        r=parse_dates(df[req]); p=parse_dates(df[po])
        d=(p-r).dt.days
        v=d.dropna()
        if len(v):
            lead.append({
                "sheet":sheet,
                "column":f"DERIVED: {req} -> {po} calendar_days",
                "n_rows":len(df),"n_numeric":len(v),
                "missing_or_unparseable":len(df)-len(v),
                "min":float(v.min()),"q25":float(v.quantile(.25)),
                "median":float(v.median()),"mean":float(v.mean()),
                "q75":float(v.quantile(.75)),"q95":float(v.quantile(.95)),
                "max":float(v.max()),"zero_count":int((v==0).sum()),
                "negative_count":int((v<0).sum())
            })
            print(f"  DERIVED {req} -> {po}: n={len(v)}, median={v.median():.2f}, min={v.min()}, max={v.max()}")

    # PO -> GR/receipt duration if BOTH explicit date fields exist.
    order_date=None; receipt_date=None
    for c in parsed:
        n=norm(c)
        if order_date is None and ("tanggalpo" in n or n in ["podate","purchaseorderdate"]):
            order_date=c
        if receipt_date is None and any(x in n for x in [
            "deliverydate","receiveddate","receiptdate","arrivaldate",
            "tanggalterima","tglterima","grdate"
        ]):
            receipt_date=c
    if order_date and receipt_date:
        d=(parsed[receipt_date]-parsed[order_date]).dt.days
        v=d.dropna()
        print(f"  PO -> receipt/delivery candidate: {order_date} -> {receipt_date}, n={len(v)}, median={v.median() if len(v) else np.nan}")
        lead.append({
            "sheet":sheet,
            "column":f"DERIVED: {order_date} -> {receipt_date} calendar_days",
            "n_rows":len(df),"n_numeric":len(v),
            "missing_or_unparseable":len(df)-len(v),
            "min":float(v.min()) if len(v) else np.nan,
            "q25":float(v.quantile(.25)) if len(v) else np.nan,
            "median":float(v.median()) if len(v) else np.nan,
            "mean":float(v.mean()) if len(v) else np.nan,
            "q75":float(v.quantile(.75)) if len(v) else np.nan,
            "q95":float(v.quantile(.95)) if len(v) else np.nan,
            "max":float(v.max()) if len(v) else np.nan,
            "zero_count":int((v==0).sum()) if len(v) else 0,
            "negative_count":int((v<0).sum()) if len(v) else 0
        })

print()
print("="*90)
print("RAW DATA — EXACT FIELD CHECK")
print("="*90)

raw=frames_raw=None
raw=pd.read_excel(SOURCE, sheet_name="Raw data")
raw.columns=[clean(c) for c in raw.columns]
raw=raw.dropna(axis=1, how="all")
print("Columns:")
for c in raw.columns:
    print(" ",c)

print("\nFirst 5 records:")
print(raw.head(5).to_string(index=False))

print("\nExact candidate fields in Raw data:")
for c in raw.columns:
    n=norm(c)
    if any(x in n for x in [
        "leadtime","pogr","gr","tanggalpo","supplier","vendor",
        "material","pr","status","totalharikerja","totalbulan"
    ]):
        print(" ",c)

audit_df=pd.DataFrame(detail)
lead_df=pd.DataFrame(lead)
date_df=pd.DataFrame(date_rows)

audit_df.to_csv(DETAIL,index=False)
lead_df.to_csv(LEAD,index=False)
date_df.to_csv(DATES,index=False)

supplier_cols=audit_df.loc[audit_df.roles.str.contains("SUPPLIER",na=False),"column"].unique().tolist()
material_cols=audit_df.loc[audit_df.roles.str.contains("MATERIAL_ID",na=False),"column"].unique().tolist()
internal_cols=audit_df.loc[audit_df.roles.str.contains("INTERNAL_LEADTIME",na=False),"column"].unique().tolist()
receipt_cols=audit_df.loc[audit_df.roles.str.contains("RECEIPT_DELIVERY",na=False),"column"].unique().tolist()

summary=f"""CMIDO — RO2 STEP 27B.1 SEMANTIC AUDIT
============================================================
Source: {SOURCE}

Supplier/vendor identifier fields:
{supplier_cols}

Material identifier fields:
{material_cols}

Internal lead-time fields:
{internal_cols}

Receipt/delivery date-like fields:
{receipt_cols}

Interpretation:
- Supplier delivery lead time is admissible ONLY if an observed supplier-linked
  order/receipt or delivery construct is established.
- Internal procurement duration may be used as a separate uncertainty component.
- SLA target values are not realized lead time.
- Alternative Rata-rata/V1/Future sheets are not independent observations.

Recommended status after this audit:
"""

if internal_cols and not supplier_cols and not receipt_cols:
    summary += "EMPIRICAL INTERNAL PROCUREMENT-TIME DATA; NOT SUPPLIER DELIVERY LEAD TIME.\n"
elif internal_cols and receipt_cols:
    summary += "INTERNAL PROCUREMENT TIME EXISTS; RECEIPT/DELIVERY FIELDS REQUIRE SEMANTIC VALIDATION.\n"
else:
    summary += "INSUFFICIENT EVIDENCE FOR PRIMARY LEAD-TIME MODEL.\n"

summary += f"""
Outputs:
{DETAIL}
{LEAD}
{DATES}
{SUMMARY}
"""
SUMMARY.write_text(summary,encoding="utf-8")

print()
print("="*90)
print("27B.1 PRELIMINARY DECISION")
print("="*90)
if internal_cols and not supplier_cols and not receipt_cols:
    print("EMPIRICAL INTERNAL PROCUREMENT-TIME DATA; NOT SUPPLIER DELIVERY LEAD TIME.")
elif internal_cols and receipt_cols:
    print("INTERNAL PROCUREMENT TIME EXISTS; RECEIPT/DELIVERY FIELDS REQUIRE SEMANTIC VALIDATION.")
else:
    print("INSUFFICIENT EVIDENCE FOR PRIMARY LEAD-TIME MODEL.")

print("\nSaved:")
for p in [DETAIL,LEAD,DATES,SUMMARY]:
    print(" ",p)
print("\nSTEP 27B.1 COMPLETE")
