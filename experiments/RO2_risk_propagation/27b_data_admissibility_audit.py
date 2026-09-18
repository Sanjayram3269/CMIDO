from __future__ import annotations

import re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"D:\CMIDO")
SOURCE = ROOT / "data" / "raw" / "RO2_Data LeadTime.xlsx"
OUT = ROOT / "results" / "RO2" / "data_audit"
OUT.mkdir(parents=True, exist_ok=True)

AUDIT = OUT / "RO2_step27b_data_audit.csv"
LEAD_OUT = OUT / "RO2_step27b_leadtime_distribution.csv"
MISS = OUT / "RO2_step27b_missingness.csv"
DUPS = OUT / "RO2_step27b_duplicates.csv"
DATES = OUT / "RO2_step27b_date_relationships.csv"
SUMMARY = OUT / "RO2_step27b_run_summary.txt"

def clean(x):
    return re.sub(r"\s+", " ", str(x).strip())

def hits(cols, terms):
    terms = [t.lower() for t in terms]
    return [clean(c) for c in cols if any(t in clean(c).lower() for t in terms)]

def num(s):
    s = s.astype("string").str.strip()
    x = s.str.extract(r"([-+]?\d+(?:[.,]\d+)?)", expand=False)
    return pd.to_numeric(x.str.replace(",", ".", regex=False), errors="coerce")

def dates(s):
    return pd.to_datetime(s, errors="coerce", dayfirst=True)

PROC = ["pr","po","procurement","requisition","release","status","purchasing",
        "material","sla","lead","delivery","receipt","received","arrival",
        "goods","gr","vendor","supplier"]
DATE = ["date","tanggal","tgl","delivery","receipt","received","arrival","po",
        "requisition","release","gr"]
SUP = ["supplier","vendor"]
MAT = ["material","material number","material no","material code","item","product"]
LEAD_TERMS = ["leadtime","lead time","lead_time","lead", "sla","days sla","realisasi sla",
        "total leadtime","total leadtime internal","total hari kerja",
        "total bulan","duration","procurement duration"]
DELIV = ["delivery","delivered","delivery date","received","receipt",
         "receipt date","arrival","arrival date","goods receipt","gr date",
         "po-gr","po gr","goods receipt","penerimaan","tanggal terima",
         "tgl terima","serah terima","gr 103","gr 101"]

if not SOURCE.exists():
    raise FileNotFoundError(f"Workbook not found: {SOURCE}")

print("="*80)
print("CMIDO — RO2 STEP 27B DATA ADMISSIBILITY & LEAD-TIME AUDIT")
print("="*80)
print(f"Source: {SOURCE}")
print("Read-only audit: NO modelling / NO imputation / NO merging / NO source modification\n")

xls = pd.ExcelFile(SOURCE)
print("Sheets:", xls.sheet_names)

audit, miss, lead, dup, date_rows = [], [], [], [], []
frames = {}

for sheet in xls.sheet_names:
    df = pd.read_excel(SOURCE, sheet_name=sheet)
    df.columns = [clean(c) for c in df.columns]
    df = df.dropna(axis=1, how="all")
    frames[sheet] = df

    proc = hits(df.columns, PROC)
    dc = hits(df.columns, DATE)
    sc = hits(df.columns, SUP)
    mc = hits(df.columns, MAT)
    lc = hits(df.columns, LEAD_TERMS)
    delc = hits(df.columns, DELIV)

    audit.append({
        "sheet": sheet, "rows": len(df), "columns": len(df.columns),
        "transaction_like": len(proc) >= 3,
        "procurement_fields": "; ".join(proc),
        "date_fields": "; ".join(dc),
        "supplier_fields": "; ".join(sc),
        "material_fields": "; ".join(mc),
        "leadtime_fields": "; ".join(lc),
        "delivery_receipt_like_fields": "; ".join(delc),
        "nonempty_cells": int(df.notna().sum().sum())
    })

    for c in df.columns:
        miss.append({
            "sheet": sheet, "column": c, "rows": len(df),
            "nonmissing": int(df[c].notna().sum()),
            "missing": int(df[c].isna().sum()),
            "missing_pct": float(df[c].isna().mean()*100),
            "dtype": str(df[c].dtype)
        })

    dup.append({"sheet":sheet,"key_type":"full_row",
                "key_columns":"<all columns>",
                "duplicate_rows":int(df.duplicated(keep=False).sum())})

    for key, pats in [
        ("PR", ["PR","PR Number","PR No"]),
        ("PO", ["PO","PO Number","PO No"]),
        ("Material", ["Material Number","Material No","Material"])
    ]:
        matches = [c for c in df.columns if any(p.lower()==c.lower() for p in pats)]
        if matches:
            c = matches[0]
            valid = df[c].dropna()
            dup.append({"sheet":sheet,"key_type":key,"key_columns":c,
                        "duplicate_rows":int(len(valid)-valid.nunique())})

    for c in lc:
        x = num(df[c]).dropna()
        lead.append({
            "sheet":sheet,"leadtime_column":c,
            "n_source_rows":len(df),"n_numeric":len(x),
            "n_missing_or_unparseable":len(df)-len(x),
            "n_zero":int((x==0).sum()) if len(x) else 0,
            "n_negative":int((x<0).sum()) if len(x) else 0,
            "min":float(x.min()) if len(x) else np.nan,
            "q01":float(x.quantile(.01)) if len(x) else np.nan,
            "q05":float(x.quantile(.05)) if len(x) else np.nan,
            "q25":float(x.quantile(.25)) if len(x) else np.nan,
            "median":float(x.median()) if len(x) else np.nan,
            "mean":float(x.mean()) if len(x) else np.nan,
            "q75":float(x.quantile(.75)) if len(x) else np.nan,
            "q95":float(x.quantile(.95)) if len(x) else np.nan,
            "q99":float(x.quantile(.99)) if len(x) else np.nan,
            "max":float(x.max()) if len(x) else np.nan,
            "std":float(x.std(ddof=1)) if len(x)>1 else np.nan
        })

    # Date semantics
    parsed = {}
    for c in dc:
        if any(t in c.lower() for t in LEAD_TERMS):
            continue
        p = dates(df[c])
        if p.notna().sum() >= 2:
            parsed[c] = p
            date_rows.append({
                "sheet":sheet,"date_column":c,
                "n_parseable":int(p.notna().sum()),
                "n_rows":len(df),
                "min_date":p.min(),"max_date":p.max()
            })

    print(f"\n[{sheet}] {len(df)} rows x {len(df.columns)} cols")
    print("  lead-time:", lc or "NONE")
    print("  supplier:", sc or "NONE")
    print("  material:", mc or "NONE")
    print("  delivery/receipt-like:", delc or "NONE")
    if parsed:
        print("  date fields:", list(parsed))

audit_df = pd.DataFrame(audit)
miss_df = pd.DataFrame(miss)
lead_df = pd.DataFrame(lead)
dup_df = pd.DataFrame(dup)
date_df = pd.DataFrame(date_rows)

audit_df.to_csv(AUDIT,index=False)
miss_df.to_csv(MISS,index=False)
lead_df.to_csv(LEAD_OUT,index=False)
dup_df.to_csv(DUPS,index=False)
date_df.to_csv(DATES,index=False)

supplier_found = bool(audit_df["supplier_fields"].replace("",np.nan).notna().any())
material_found = bool(audit_df["material_fields"].replace("",np.nan).notna().any())
delivery_like_found = bool(audit_df["delivery_receipt_like_fields"].replace("",np.nan).notna().any())
numeric_lead = bool(len(lead_df) and (lead_df["n_numeric"]>0).any())

transaction_sheets = audit_df.loc[audit_df.transaction_like,"sheet"].tolist()
lead_sheets = audit_df.loc[audit_df.leadtime_fields!="","sheet"].tolist()

if numeric_lead and not delivery_like_found:
    classification = (
        "EMPIRICAL INTERNAL PROCUREMENT LEAD-TIME CANDIDATE; "
        "SUPPLIER DELIVERY LEAD-TIME NOT ESTABLISHED"
    )
elif numeric_lead and delivery_like_found:
    classification = (
        "POTENTIALLY EMPIRICAL PROCUREMENT/DELIVERY LEAD-TIME DATA; "
        "SEMANTIC VALIDATION REQUIRED"
    )
else:
    classification = "SUPPORTING EVIDENCE ONLY — NO USABLE LEAD-TIME FIELD ESTABLISHED"

summary = f"""CMIDO — RO2 STEP 27B DATA ADMISSIBILITY & LEAD-TIME AUDIT
======================================================================
Source: {SOURCE}
Sheets: {len(xls.sheet_names)}
Transaction-like sheets: {transaction_sheets}
Lead-time candidate sheets: {lead_sheets}
Supplier fields found: {supplier_found}
Material fields found: {material_found}
Delivery/receipt-like fields found: {delivery_like_found}
Numeric lead-time candidate available: {numeric_lead}

PRELIMINARY CLASSIFICATION
--------------------------
{classification}

SCIENTIFIC CAUTION
------------------
Do NOT label 'Total Leadtime Internal', SLA, or internal process duration
as supplier delivery lead time unless the workbook documentation and
date semantics explicitly establish that meaning.

The source workbook was not modified. No imputation, merging, modelling,
or row deletion was performed.

OUTPUTS
-------
{AUDIT}
{LEAD_OUT}
{MISS}
{DUPS}
{DATES}
{SUMMARY}
"""
SUMMARY.write_text(summary,encoding="utf-8")

print("\n"+"="*80)
print("PRELIMINARY 27B CLASSIFICATION")
print("="*80)
print(classification)
print("\nSaved:")
for p in [AUDIT,LEAD_OUT,MISS,DUPS,DATES,SUMMARY]:
    print(" ",p)
print("\nSTEP 27B DATA AUDIT: COMPLETE")
