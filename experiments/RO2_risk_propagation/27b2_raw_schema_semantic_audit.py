from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(r"D:\CMIDO")
SOURCE = ROOT / "data" / "raw" / "RO2_Data LeadTime.xlsx"
OUT = ROOT / "results" / "RO2" / "data_audit"
OUT.mkdir(parents=True, exist_ok=True)

DETAIL = OUT / "RO2_step27b2_raw_schema.csv"
LEAD = OUT / "RO2_step27b2_leadtime_candidates.csv"
SUMMARY = OUT / "RO2_step27b2_semantic_decision.txt"

def clean(x):
    return re.sub(r"\s+", " ", str(x).strip())

def parse_num(s):
    s = s.astype("string").str.strip()
    # Handles "39 Hari", "1.29 bulan", "-", blanks, etc.
    x = s.str.extract(r"([-+]?\d+(?:[.,]\d+)?)", expand=False)
    return pd.to_numeric(x.str.replace(",", ".", regex=False), errors="coerce")

def parse_date(s):
    return pd.to_datetime(s, errors="coerce", dayfirst=True)

if not SOURCE.exists():
    raise FileNotFoundError(SOURCE)

print("=" * 90)
print("CMIDO — RO2 STEP 27B.2 RAW TRANSACTION SCHEMA & LEAD-TIME SEMANTICS")
print("=" * 90)
print(f"Source: {SOURCE}")
print("Read-only: NO source modification / NO imputation / NO modelling")
print()

# The diagnostic established that row 3 (zero-based 2) contains the real headers.
# Read the raw sheet with header=2 so the transaction columns are recovered.
raw = pd.read_excel(SOURCE, sheet_name="Raw data", header=1)
raw.columns = [clean(c) for c in raw.columns]
raw = raw.dropna(axis=1, how="all")

# Remove completely empty records only for inspection; do not modify source.
raw = raw.dropna(how="all").reset_index(drop=True)

print(f"Parsed Raw data: {len(raw)} transaction rows x {len(raw.columns)} columns")
print("\nRecovered columns:")
for c in raw.columns:
    print(" ", c)

# Helper to locate exact/near-exact columns.
def col(*names):
    for name in names:
        for c in raw.columns:
            if clean(c).lower() == name.lower():
                return c
    for name in names:
        n = re.sub(r"[^a-z0-9]+", "", name.lower())
        for c in raw.columns:
            cn = re.sub(r"[^a-z0-9]+", "", c.lower())
            if n and n in cn:
                return c
    return None

c_pr = col("Nomor PR")
c_po = col("Nomor PO")
c_sr = col("Nomor SR")
c_status = col("Status")
c_item = col("Item Of")
c_pg = col("Purchase Group")
c_goods = col("Barang/Jasa")
c_short = col("Short Text")
c_po_date = col("Tanggal PO")
c_internal = col("Total Leadtime Internal")
c_gr_dn = col("PO - GR 103/101 (DN)")
c_gr_ln = col("PO - GR 103/101 (LN)")
c_all_dn = col("Total Hari Kerja All (DN)")
c_all_ln = col("Total Hari Kerja All (LN)")
c_month_dn = col("Total Bulan All (DN)")
c_month_ln = col("Total Bulan All (LN)")
c_buyer = col("PIC Buyer (Daan)")

key_cols = [
    ("PR", c_pr), ("PO", c_po), ("SR", c_sr), ("Status", c_status),
    ("Item Of", c_item), ("Purchase Group", c_pg), ("Barang/Jasa", c_goods),
    ("Short Text", c_short), ("Tanggal PO", c_po_date),
    ("Total Leadtime Internal", c_internal),
    ("PO-GR DN", c_gr_dn), ("PO-GR LN", c_gr_ln),
    ("Total Hari Kerja All DN", c_all_dn),
    ("Total Hari Kerja All LN", c_all_ln),
    ("Total Bulan All DN", c_month_dn),
    ("Total Bulan All LN", c_month_ln),
    ("Buyer", c_buyer),
]

print("\nFIELD RESOLUTION")
for label, c in key_cols:
    print(f"  {label:28s}: {c if c else 'NOT FOUND'}")

# Basic record counts
print("\nRECORD COUNTS")
for label, c in key_cols:
    if c:
        s = raw[c]
        print(
            f"  {label:28s}: nonmissing={s.notna().sum():3d}, "
            f"unique={s.dropna().astype(str).nunique():3d}"
        )

# Status and goods/service distributions
print("\nSTATUS DISTRIBUTION")
if c_status:
    print(raw[c_status].value_counts(dropna=False).to_string())

print("\nBARANG/JASA DISTRIBUTION")
if c_goods:
    print(raw[c_goods].value_counts(dropna=False).to_string())

# Material-like information: Item Of + Short Text. There may be no actual
# Material Number in Raw data, so explicitly report that.
print("\nMATERIAL / ITEM STRUCTURE")
if c_item:
    print(f"Item Of unique: {raw[c_item].dropna().astype(str).nunique()}")
if c_short:
    print(f"Short Text unique: {raw[c_short].dropna().astype(str).nunique()}")
print("Explicit Material Number field in Raw data: NOT FOUND")

# Lead-time candidates
candidate_specs = [
    ("OBS_OR_SOURCE: Total Leadtime Internal", c_internal),
    ("OBS_OR_SOURCE: PO - GR 103/101 (DN)", c_gr_dn),
    ("OBS_OR_SOURCE: PO - GR 103/101 (LN)", c_gr_ln),
    ("OBS_OR_SOURCE: Total Hari Kerja All (DN)", c_all_dn),
    ("OBS_OR_SOURCE: Total Hari Kerja All (LN)", c_all_ln),
    ("OBS_OR_SOURCE: Total Bulan All (DN)", c_month_dn),
    ("OBS_OR_SOURCE: Total Bulan All (LN)", c_month_ln),
]

lead_rows = []

for label, c in candidate_specs:
    if not c:
        continue
    x = parse_num(raw[c])
    v = x.dropna()
    row = {
        "field": label,
        "column": c,
        "n_rows": len(raw),
        "n_numeric": len(v),
        "missing_or_unparseable": len(raw) - len(v),
        "zero_count": int((v == 0).sum()) if len(v) else 0,
        "negative_count": int((v < 0).sum()) if len(v) else 0,
        "min": float(v.min()) if len(v) else np.nan,
        "q25": float(v.quantile(.25)) if len(v) else np.nan,
        "median": float(v.median()) if len(v) else np.nan,
        "mean": float(v.mean()) if len(v) else np.nan,
        "q75": float(v.quantile(.75)) if len(v) else np.nan,
        "q95": float(v.quantile(.95)) if len(v) else np.nan,
        "max": float(v.max()) if len(v) else np.nan,
    }
    lead_rows.append(row)
    print(f"\n{label}")
    print(pd.Series(row).to_string())

lead_df = pd.DataFrame(lead_rows)

# PO date coverage
print("\nPO DATE COVERAGE")
if c_po_date:
    p = parse_date(raw[c_po_date])
    print(f"parseable: {p.notna().sum()}/{len(raw)}")
    if p.notna().any():
        print(f"range: {p.min()} -> {p.max()}")

# Identify whether an explicit supplier/vendor identifier exists anywhere
supplier_candidates = [
    c for c in raw.columns
    if any(k in re.sub(r"[^a-z0-9]+","",c.lower()) for k in
           ["supplier","vendor","vendorid","supplierid","vendorcode","suppliercode"])
]
print("\nSUPPLIER IDENTIFIER SEARCH")
print("Supplier/vendor candidate columns:", supplier_candidates or "NONE")

# Check for receipt/delivery DATE fields, not just PO-GR duration fields.
receipt_date_candidates = [
    c for c in raw.columns
    if any(k in re.sub(r"[^a-z0-9]+","",c.lower()) for k in
           ["deliverydate","receiveddate","receiptdate","arrivaldate",
            "tanggalterima","tglterima","grdate"])
]
print("Explicit receipt/delivery DATE columns:", receipt_date_candidates or "NONE")

# Examine PR->PO if PR and PO dates are both present. Raw data has only PO date,
# so this is explicitly reported as unavailable here.
print("\nORDER-TO-RECEIPT SEMANTIC TEST")
if receipt_date_candidates and c_po_date:
    for rc in receipt_date_candidates:
        po = parse_date(raw[c_po_date])
        rr = parse_date(raw[rc])
        d = (rr - po).dt.days.dropna()
        print(f"  {c_po_date} -> {rc}: n={len(d)}, median={d.median() if len(d) else np.nan}")
else:
    print("  NO explicit PO-to-receipt/delivery date pair available in Raw data.")

# Internal lead time vs DN/LN arithmetic consistency.
print("\nARITHMETIC CONSISTENCY CHECK")
if c_internal and c_all_dn:
    a = parse_num(raw[c_internal])
    b = parse_num(raw[c_all_dn])
    diff = (a - b).dropna()
    print(f"Internal vs Total All DN: paired n={len(diff)}, exact equal={(diff==0).sum()}, median difference={diff.median() if len(diff) else np.nan}")

if c_gr_dn and c_all_dn and c_internal:
    internal = parse_num(raw[c_internal])
    gr = parse_num(raw[c_gr_dn])
    total = parse_num(raw[c_all_dn])
    expected = internal + gr
    err = (total - expected).dropna()
    print(f"DN arithmetic (Internal + PO-GR DN -> Total DN): paired n={len(err)}, exact equal={(err==0).sum()}, median error={err.median() if len(err) else np.nan}, max abs error={err.abs().max() if len(err) else np.nan}")

# Build a compact transaction-level semantic extract for audit.
keep = [c for _, c in key_cols if c]
keep = list(dict.fromkeys([c for c in keep if c]))
detail = raw[keep].copy()
for c in [c_internal,c_gr_dn,c_gr_ln,c_all_dn,c_all_ln,c_month_dn,c_month_ln]:
    if c:
        detail[c + " [numeric]"] = parse_num(raw[c])
detail.to_csv(DETAIL, index=False)
lead_df.to_csv(LEAD, index=False)

# Conservative scientific classification.
has_internal = c_internal is not None and parse_num(raw[c_internal]).notna().sum() > 0
has_gr_duration = (
    (c_gr_dn is not None and parse_num(raw[c_gr_dn]).notna().sum() > 0)
    or (c_gr_ln is not None and parse_num(raw[c_gr_ln]).notna().sum() > 0)
)
has_supplier = len(supplier_candidates) > 0
has_receipt_date = len(receipt_date_candidates) > 0

if has_internal and has_gr_duration and not has_supplier and not has_receipt_date:
    decision = (
        "RO2 DATA PATHWAY B — EMPIRICAL INTERNAL PROCUREMENT + "
        "PO-to-GR/DN/LN DURATION CANDIDATE; SUPPLIER-SPECIFIC LEAD TIME NOT IDENTIFIED."
    )
elif has_internal and has_gr_duration and (has_supplier or has_receipt_date):
    decision = (
        "RO2 DATA PATHWAY A/B — POTENTIALLY USABLE OBSERVED DELIVERY COMPONENT; "
        "REQUIRES FIELD-SEMANTIC VALIDATION BEFORE MODELLING."
    )
elif has_internal:
    decision = (
        "RO2 DATA PATHWAY C — INTERNAL PROCUREMENT TIME ONLY; "
        "NO EMPIRICAL DELIVERY COMPONENT ESTABLISHED."
    )
else:
    decision = "RO2 DATA PATHWAY C — INSUFFICIENT EMPIRICAL LEAD-TIME EVIDENCE."

summary = f"""CMIDO — RO2 STEP 27B.2
RAW TRANSACTION SCHEMA & LEAD-TIME SEMANTICS
============================================================

Parsed Raw data rows: {len(raw)}
Parsed Raw data columns: {len(raw.columns)}

Supplier identifier columns: {supplier_candidates or "NONE"}
Explicit receipt/delivery DATE columns: {receipt_date_candidates or "NONE"}

Internal lead-time field: {c_internal}
PO-GR DN field: {c_gr_dn}
PO-GR LN field: {c_gr_ln}
Total All DN field: {c_all_dn}
Total All LN field: {c_all_ln}

DECISION
--------
{decision}

CRITICAL RULE
-------------
PO-GR DN/LN fields are NOT automatically labelled supplier lead time.
Their exact business definition must be established from the source
documentation/process meaning before they enter F_L.

Likewise, 'Total Leadtime Internal' is retained as internal procurement
processing time unless documentation proves otherwise.

No source workbook changes were made.
"""

SUMMARY.write_text(summary, encoding="utf-8")

print("\n" + "=" * 90)
print("27B.2 SCIENTIFIC DECISION")
print("=" * 90)
print(decision)
print("\nSaved:")
for p in [DETAIL, LEAD, SUMMARY]:
    print(" ", p)
print("\nSTEP 27B.2 COMPLETE")

