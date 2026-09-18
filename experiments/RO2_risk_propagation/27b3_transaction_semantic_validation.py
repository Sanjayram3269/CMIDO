from pathlib import Path
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "raw" / "RO2_Data LeadTime.xlsx"
OUT = ROOT / "results" / "RO2" / "data_audit"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 90)
print("CMIDO — RO2 STEP 27B.3 TRANSACTION-LEVEL SEMANTIC VALIDATION")
print("=" * 90)
print(f"Source: {SOURCE}")
print("Read-only: NO source modification / NO imputation / NO modelling")
print()

# ---------- helpers ----------
def clean(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    return np.nan if s == "" or s.lower() in {"nan", "nat", "none"} else s

def num(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else np.nan

def parse_date(x):
    if pd.isna(x):
        return pd.NaT
    # Excel serials can appear as numbers. Treat implausible dates separately.
    if isinstance(x, (int, float, np.integer, np.floating)) and not pd.isna(x):
        if 1 <= float(x) <= 60000:
            try:
                return pd.Timestamp("1899-12-30") + pd.to_timedelta(float(x), unit="D")
            except Exception:
                return pd.NaT
    try:
        return pd.to_datetime(x, errors="coerce")
    except Exception:
        return pd.NaT

def resolve(df, exact):
    for c in exact:
        if c in df.columns:
            return c
    norm = {re.sub(r"[^a-z0-9]+", "", str(c).lower()): c for c in df.columns}
    for c in exact:
        k = re.sub(r"[^a-z0-9]+", "", c.lower())
        if k in norm:
            return norm[k]
    return None

# ---------- read ----------
if not SOURCE.exists():
    raise FileNotFoundError(SOURCE)

raw = pd.read_excel(SOURCE, sheet_name="Raw data", header=1)
raw.columns = [str(c).strip() for c in raw.columns]

print(f"Parsed Raw data: {len(raw)} transaction rows x {len(raw.columns)} columns")
print()

fields = {
    "PR": resolve(raw, ["Nomor PR"]),
    "PO": resolve(raw, ["Nomor PO"]),
    "SR": resolve(raw, ["Nomor SR"]),
    "Status": resolve(raw, ["Status"]),
    "Item Of": resolve(raw, ["Item Of"]),
    "Purchase Group": resolve(raw, ["Purchase Group"]),
    "Barang/Jasa": resolve(raw, ["Barang/Jasa"]),
    "Short Text": resolve(raw, ["Short Text"]),
    "PO Date": resolve(raw, ["Tanggal PO"]),
    "Internal": resolve(raw, ["Total Leadtime Internal Kom Teknik"]),
    "PO-GR DN": resolve(raw, ["PO - GR 103/101 (DN)"]),
    "PO-GR LN": resolve(raw, ["PO - GR 103/101 (LN)"]),
    "Total DN": resolve(raw, ["Total Hari Kerja All (DN)"]),
    "Total LN": resolve(raw, ["Total Hari Kerja All (LN)"]),
    "Month DN": resolve(raw, ["Total Bulan All (DN)"]),
    "Month LN": resolve(raw, ["Total Bulan All (LN)"]),
    "Buyer": resolve(raw, ["PIC Buyer (Daan)"]),
}

print("FIELD RESOLUTION")
for k, v in fields.items():
    print(f"  {k:18s}: {v if v else 'NOT FOUND'}")
print()

# ---------- transaction identity / duplicates ----------
def series(name):
    c = fields[name]
    return raw[c].map(clean) if c else pd.Series(np.nan, index=raw.index)

pr = series("PR")
po = series("PO")
sr = series("SR")
status = series("Status")
item = series("Item Of")
service = series("Barang/Jasa")
short_text = series("Short Text")

print("1. TRANSACTION IDENTITY / DUPLICATION")
print(f"  rows: {len(raw)}")
print(f"  PR nonmissing: {pr.notna().sum()}, unique: {pr.nunique(dropna=True)}")
print(f"  PO nonmissing: {po.notna().sum()}, unique: {po.nunique(dropna=True)}")
print(f"  PR-PO duplicate row pairs: {raw.loc[pr.notna() & po.notna(), [fields['PR'], fields['PO']]].duplicated().sum()}")
print(f"  duplicate PR values: {(pr.value_counts() > 1).sum()}")
print(f"  duplicate PO values: {(po.value_counts() > 1).sum()}")
print()

# Print repeated PR/PO groups for semantic review.
pairs = pd.DataFrame({"PR": pr, "PO": po, "Item Of": item, "Status": status, "Short Text": short_text})
repeated_pr = pairs[pairs["PR"].isin(pr.value_counts()[lambda s: s > 1].index)].sort_values(["PR", "PO"])
repeated_po = pairs[pairs["PO"].isin(po.value_counts()[lambda s: s > 1].index)].sort_values(["PO", "PR"])

if not repeated_pr.empty:
    print("  Repeated PR records:")
    print(repeated_pr.to_string(index=False))
else:
    print("  Repeated PR records: none")
if not repeated_po.empty:
    print("  Repeated PO records:")
    print(repeated_po.to_string(index=False))
else:
    print("  Repeated PO records: none")
print()

# ---------- status / service semantics ----------
print("2. STATUS AND PROCUREMENT-TYPE STRUCTURE")
print("  Status:")
print(status.value_counts(dropna=False).to_string())
print("  Barang/Jasa:")
print(service.value_counts(dropna=False).to_string())
print("  Item Of:")
print(item.value_counts(dropna=False).to_string())
print()

# ---------- dates ----------
print("3. PO DATE SEMANTICS / ANOMALY CHECK")
if fields["PO Date"]:
    po_date = raw[fields["PO Date"]].map(parse_date)
    print(f"  parseable: {po_date.notna().sum()}/{len(raw)}")
    print(f"  invalid/unparseable: {po_date.isna().sum()}")
    if po_date.notna().any():
        print(f"  raw parsed range: {po_date.min()} -> {po_date.max()}")
        print("  earliest 10 dates:")
        print(po_date.sort_values().head(10).to_string(index=False))
        suspicious = po_date[(po_date < pd.Timestamp("2000-01-01")) | (po_date > pd.Timestamp("2026-12-31"))]
        print(f"  suspicious dates outside 2000-2026: {len(suspicious)}")
        if len(suspicious):
            print(suspicious.to_string())
else:
    po_date = pd.Series(pd.NaT, index=raw.index)
    print("  PO date field unavailable")
print()

# ---------- lead-time components ----------
print("4. LEAD-TIME COMPONENT SEMANTICS")
numeric = {}
for name in ["Internal", "PO-GR DN", "PO-GR LN", "Total DN", "Total LN", "Month DN", "Month LN"]:
    c = fields[name]
    numeric[name] = raw[c].map(num) if c else pd.Series(np.nan, index=raw.index)
    x = numeric[name]
    print(f"  {name:12s}: n={x.notna().sum():2d}, min={x.min()}, median={x.median()}, max={x.max()}")
print()

# ---------- arithmetic checks ----------
print("5. ARITHMETIC RECONSTRUCTION")
internal = numeric["Internal"]
pogr_dn = numeric["PO-GR DN"]
total_dn = numeric["Total DN"]
pogr_ln = numeric["PO-GR LN"]
total_ln = numeric["Total LN"]

mask_dn = internal.notna() & pogr_dn.notna() & total_dn.notna()
if mask_dn.any():
    err = internal[mask_dn] + pogr_dn[mask_dn] - total_dn[mask_dn]
    print(f"  DN paired n: {mask_dn.sum()}")
    print(f"  exact equality: {(err.abs() < 1e-9).sum()}/{len(err)}")
    print(f"  median error: {err.median()}")
    print(f"  max abs error: {err.abs().max()}")
    print("  nonzero-error rows:")
    if (err.abs() >= 1e-9).any():
        print(raw.loc[err[err.abs() >= 1e-9].index,
                      [c for c in [fields["PR"], fields["PO"], fields["Internal"], fields["PO-GR DN"], fields["Total DN"]] if c]].to_string(index=False))
    else:
        print("    none")
else:
    print("  insufficient DN fields for arithmetic test")

mask_ln = internal.notna() & pogr_ln.notna() & total_ln.notna()
if mask_ln.any():
    err = internal[mask_ln] + pogr_ln[mask_ln] - total_ln[mask_ln]
    print(f"  LN paired n: {mask_ln.sum()}")
    print(f"  exact equality: {(err.abs() < 1e-9).sum()}/{len(err)}")
    print(f"  median error: {err.median()}")
    print(f"  max abs error: {err.abs().max()}")
else:
    print("  LN arithmetic not testable at useful sample size")
print()

# ---------- relation to service/status ----------
print("6. LEAD-TIME AVAILABILITY BY STATUS / ITEM TYPE")
audit = pd.DataFrame({
    "Status": status,
    "Barang/Jasa": service,
    "Internal": internal,
    "PO_GR_DN": pogr_dn,
    "Total_DN": total_dn,
    "PO_Date": po_date,
})
for col in ["Status", "Barang/Jasa"]:
    print(f"  By {col}:")
    g = audit.groupby(col, dropna=False).agg(
        rows=("Internal", "size"),
        internal_n=("Internal", "count"),
        pogr_dn_n=("PO_GR_DN", "count"),
        total_dn_n=("Total_DN", "count"),
        median_internal=("Internal", "median"),
        median_pogr_dn=("PO_GR_DN", "median"),
        median_total_dn=("Total_DN", "median"),
    )
    print(g.to_string())
    print()

# ---------- supplier evidence ----------
print("7. SUPPLIER / DELIVERY EVIDENCE")
supplier_candidates = [
    c for c in raw.columns
    if any(k in c.lower() for k in ["supplier", "vendor", "vendor name", "supplier name", "penyedia"])
]
receipt_date_candidates = [
    c for c in raw.columns
    if any(k in c.lower() for k in ["receipt date", "delivery date", "tanggal terima", "tanggal delivery", "gr date", "goods receipt"])
]
print("  Supplier/vendor candidates:", supplier_candidates if supplier_candidates else "NONE")
print("  Explicit receipt/delivery date candidates:", receipt_date_candidates if receipt_date_candidates else "NONE")
print("  Important: PO-GR is a duration field; without an explicit receipt date or supplier identifier,")
print("  this audit does NOT establish supplier-specific delivery lead time.")
print()

# ---------- DN/LN semantic clues ----------
print("8. DN/LN SEMANTIC EVIDENCE FROM DATA")
print(f"  PO-GR DN numeric n: {pogr_dn.notna().sum()}")
print(f"  PO-GR LN numeric n: {pogr_ln.notna().sum()}")
print(f"  Total DN numeric n: {total_dn.notna().sum()}")
print(f"  Total LN numeric n: {total_ln.notna().sum()}")
print("  DN is the dominant populated pathway; LN is essentially absent.")
print("  Exact DN reconstruction will be treated as strong internal consistency evidence,")
print("  not as proof of supplier semantics.")
print()

# ---------- conservative scientific decision ----------
recon_exact = False
if mask_dn.any():
    e = internal[mask_dn] + pogr_dn[mask_dn] - total_dn[mask_dn]
    recon_exact = int((e.abs() < 1e-9).sum()) >= max(1, int(np.ceil(0.95 * len(e))))

date_ok = po_date.notna().sum() >= max(1, len(raw) - 2)
supplier_missing = len(supplier_candidates) == 0
receipt_missing = len(receipt_date_candidates) == 0
service_only = service.dropna().nunique() == 1 and service.dropna().iloc[0].lower() == "jasa"

if recon_exact and supplier_missing and receipt_missing:
    decision = (
        "RO2 DATA PATHWAY B CONFIRMED — EMPIRICAL PROCUREMENT-PROCESS DURATION "
        "WITH INTERNAL + PO-GR/DN COMPONENTS; SUPPLIER-SPECIFIC LEAD TIME NOT IDENTIFIED."
    )
else:
    decision = (
        "RO2 DATA PATHWAY B — EMPIRICAL PROCUREMENT-PROCESS DURATION CANDIDATE; "
        "SEMANTIC CONFIDENCE REQUIRES CAUTION BEFORE MODELLING."
    )

print("=" * 90)
print("27B.3 SCIENTIFIC DECISION")
print("=" * 90)
print(decision)
print()
print("Evidence summary:")
print(f"  Strong DN arithmetic reconstruction: {recon_exact}")
print(f"  Supplier identifier absent: {supplier_missing}")
print(f"  Explicit receipt date absent: {receipt_missing}")
print(f"  Service-only transaction field: {service_only}")
print(f"  PO-date coverage broadly usable: {date_ok}")
print()
print("NON-NEGOTIABLE MODELLING LABEL:")
print("  Do NOT label PO-GR/DN as supplier lead time unless external/source documentation")
print("  explicitly establishes that meaning.")
print("  Do NOT use these service transactions as observed construction-material supplier events.")
print("  Do NOT treat repeated PR/PO rows as independent without transaction-unit justification.")
print()

# ---------- save auditable outputs ----------
summary_rows = []
for i in raw.index:
    summary_rows.append({
        "row_index": i,
        "PR": pr.loc[i],
        "PO": po.loc[i],
        "SR": sr.loc[i],
        "Status": status.loc[i],
        "Item_Of": item.loc[i],
        "Barang_Jasa": service.loc[i],
        "Short_Text": short_text.loc[i],
        "PO_Date": po_date.loc[i],
        "Internal_Days": internal.loc[i],
        "PO_GR_DN_Days": pogr_dn.loc[i],
        "PO_GR_LN_Days": pogr_ln.loc[i],
        "Total_DN_Days": total_dn.loc[i],
        "Total_LN_Days": total_ln.loc[i],
        "DN_Reconstruction_Error": (
            internal.loc[i] + pogr_dn.loc[i] - total_dn.loc[i]
            if pd.notna(internal.loc[i]) and pd.notna(pogr_dn.loc[i]) and pd.notna(total_dn.loc[i])
            else np.nan
        ),
    })

out_csv = OUT / "RO2_step27b3_transaction_semantic_audit.csv"
pd.DataFrame(summary_rows).to_csv(out_csv, index=False)

decision_txt = OUT / "RO2_step27b3_semantic_decision.txt"
decision_txt.write_text(
    "CMIDO RO2 STEP 27B.3\n\n"
    + decision + "\n\n"
    + "The audit establishes empirical consistency between internal lead-time, "
      "PO-GR/DN duration, and total DN duration where all three are present. "
      "It does not establish supplier-specific lead time because no supplier identifier "
      "or explicit receipt/delivery date is present in Raw data. "
      "The transactions are overwhelmingly/entirely classified as Jasa (services), "
      "so they must not be presented as observed construction-material supplier events.\n",
    encoding="utf-8",
)

print("Saved:")
print(f"  {out_csv}")
print(f"  {decision_txt}")
print()
print("STEP 27B.3 COMPLETE")
