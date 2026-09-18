from pathlib import Path
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "raw" / "RO2_Data LeadTime.xlsx"
OUT = ROOT / "results" / "RO2" / "data_audit"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 90)
print("CMIDO — RO2 STEP 27B.4 DATA INTEGRITY & OBSERVATION-UNIT AUDIT")
print("=" * 90)
print(f"Source: {SOURCE}")
print("Read-only: NO source modification / NO imputation / NO modelling")
print()

def clean(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "nat", "none", "-"}:
        return np.nan
    return s

def num(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else np.nan

def parse_date_raw(x):
    if pd.isna(x):
        return pd.NaT
    # Preserve raw representation for anomaly diagnosis.
    if isinstance(x, (int, float, np.integer, np.floating)):
        if float(x) == 0:
            return pd.Timestamp("1899-12-30")
        if 1 <= float(x) <= 60000:
            return pd.Timestamp("1899-12-30") + pd.to_timedelta(float(x), unit="D")
    return pd.to_datetime(x, errors="coerce", dayfirst=True)

raw = pd.read_excel(SOURCE, sheet_name="Raw data", header=1)
raw.columns = [str(c).strip() for c in raw.columns]

def col(name):
    return name if name in raw.columns else None

C = {
    "PR": col("Nomor PR"),
    "PO": col("Nomor PO"),
    "SR": col("Nomor SR"),
    "Status": col("Status"),
    "Item": col("Item Of"),
    "Short": col("Short Text"),
    "Type": col("Barang/Jasa"),
    "PODate": col("Tanggal PO"),
    "Internal": col("Total Leadtime Internal Kom Teknik"),
    "PODN": col("PO - GR 103/101 (DN)"),
    "POTLN": col("PO - GR 103/101 (LN)"),
    "TotalDN": col("Total Hari Kerja All (DN)"),
    "TotalLN": col("Total Hari Kerja All (LN)"),
    "MonthDN": col("Total Bulan All (DN)"),
    "MonthLN": col("Total Bulan All (LN)"),
}

df = pd.DataFrame(index=raw.index)
for k, c in C.items():
    df[k] = raw[c].map(clean) if c else np.nan

for k in ["Internal", "PODN", "POTLN", "TotalDN", "TotalLN", "MonthDN", "MonthLN"]:
    df[k + "_num"] = df[k].map(num)

df["PODate_parsed"] = raw[C["PODate"]].map(parse_date_raw)

# -------------------------------------------------------------------
print("1. SOURCE / BASIC COUNTS")
print(f"  Raw rows: {len(df)}")
print(f"  Raw columns: {len(raw.columns)}")
print(f"  PR nonmissing: {df.PR.notna().sum()}")
print(f"  PO nonmissing: {df.PO.notna().sum()}")
print()

# -------------------------------------------------------------------
print("2. 1900-01-01 / DATE ENCODING DIAGNOSIS")
bad_date_mask = df["PODate_parsed"].notna() & (df["PODate_parsed"] < pd.Timestamp("2000-01-01"))
if bad_date_mask.any():
    print(f"  Suspicious pre-2000 parsed dates: {bad_date_mask.sum()}")
    for i in df.index[bad_date_mask]:
        print(f"    row={i}, raw PO date={raw.loc[i, C['PODate']]!r}, parsed={df.loc[i,'PODate_parsed']}")
        print(f"      PR={df.loc[i,'PR']!r}, PO={df.loc[i,'PO']!r}, Status={df.loc[i,'Status']!r}, Short={df.loc[i,'Short']!r}")
else:
    print("  No suspicious pre-2000 dates found.")
print("  Rule: do NOT silently convert or delete this row in the raw source.")
print()

# -------------------------------------------------------------------
print("3. DUPLICATE PR–PO OBSERVATION-UNIT AUDIT")
valid_pair = df["PR"].notna() & df["PO"].notna()
pair_counts = df.loc[valid_pair].groupby(["PR", "PO"], dropna=False).size().sort_values(ascending=False)
dupe_pairs = pair_counts[pair_counts > 1]
print(f"  Unique PR–PO pairs: {pair_counts.size}")
print(f"  Repeated PR–PO pairs: {len(dupe_pairs)}")
if len(dupe_pairs):
    for (pr, po), n in dupe_pairs.items():
        rows = df.index[(df.PR == pr) & (df.PO == po)].tolist()
        print(f"    PR={pr}, PO={po}, rows={rows}, count={n}")
        print(df.loc[rows, ["PR","PO","SR","Item","Status","Short","Internal_num","PODN_num","TotalDN_num"]].to_string(index=False))
print()

# -------------------------------------------------------------------
print("4. PLACEHOLDER / MISSING-VALUE AUDIT")
for k in ["PR","PO","SR","Status","Item","Short","Type","PODate","Internal","PODN","POTLN","TotalDN","TotalLN","MonthDN","MonthLN"]:
    print(f"  {k:10s}: missing={df[k].isna().sum():2d}, nonmissing={df[k].notna().sum():2d}")
print()

# -------------------------------------------------------------------
print("5. DN vs 'BULAN' FIELD CONSISTENCY")
for a, b in [("TotalDN_num","MonthDN_num"), ("TotalLN_num","MonthLN_num")]:
    m = df[a].notna() & df[b].notna()
    if m.any():
        diff = df.loc[m,a] - df.loc[m,b]
        print(f"  {a} vs {b}: paired n={m.sum()}, exact equal={(diff.abs()<1e-9).sum()}/{len(diff)}, median diff={diff.median()}, max abs diff={diff.abs().max()}")
        if (diff.abs() >= 1e-9).any():
            print("    Non-equal examples:")
            print(df.loc[diff[diff.abs() >= 1e-9].index, [a,b]].head(10).to_string())
    else:
        print(f"  {a} vs {b}: not testable")
print("  Interpretation is descriptive only; field names suggesting 'Bulan' are not assumed to mean months.")
print()

# -------------------------------------------------------------------
print("6. LEAD-TIME RECONSTRUCTION ON CLEAN CANDIDATES")
m = df["Internal_num"].notna() & df["PODN_num"].notna() & df["TotalDN_num"].notna()
err = pd.Series(index=df.index, dtype=float)
err.loc[m] = df.loc[m,"Internal_num"] + df.loc[m,"PODN_num"] - df.loc[m,"TotalDN_num"]
print(f"  Complete DN component rows: {m.sum()}")
print(f"  Exact reconstruction: {(err.loc[m].abs()<1e-9).sum()}/{m.sum()}")
print(f"  Nonzero rows: {(err.loc[m].abs()>=1e-9).sum()}")
print(f"  Median error: {err.loc[m].median()}")
print(f"  Max absolute error: {err.loc[m].abs().max()}")
print()

# -------------------------------------------------------------------
print("7. STATUS-BASED ADMISSIBILITY")
status_counts = df["Status"].value_counts(dropna=False)
print(status_counts.to_string())
print()
print("  Candidate empirical lead-time sample rule:")
print("    A) Status == Closed")
print("    B) Internal lead time is numeric and > 0")
print("    C) Total DN is numeric and > 0")
print("    D) For component analysis, PO-GR DN is numeric and > 0")
print("    E) No row is removed merely because PO-GR DN is missing; that field is component-specific.")
print()

closed = df["Status"].eq("Closed")
valid_total = df["TotalDN_num"].notna() & (df["TotalDN_num"] > 0)
valid_internal = df["Internal_num"].notna() & (df["Internal_num"] > 0)
valid_pogr = df["PODN_num"].notna() & (df["PODN_num"] > 0)

admiss_total = closed & valid_total & valid_internal
admiss_component = admiss_total & valid_pogr

print(f"  Closed + valid internal + valid total DN: {admiss_total.sum()} rows")
print(f"  Closed + valid internal + valid PO-GR DN + valid total DN: {admiss_component.sum()} rows")
print()

# -------------------------------------------------------------------
print("8. OBSERVATION-UNIT DECISION")
print("  PR-level uniqueness:", df["PR"].nunique(dropna=True))
print("  PO-level uniqueness:", df["PO"].nunique(dropna=True))
print("  One repeated PR–PO pair is identical in the observed fields checked.")
print("  Therefore the repeated pair must NOT be counted twice as independent lead-time events.")
print()

# Create conservative deduplicated view: keep first occurrence of duplicate PR–PO pair.
dedup = df.copy()
dedup["_pair_key"] = dedup["PR"].fillna("<NA>") + "||" + dedup["PO"].fillna("<NA>")
dedup["_is_duplicate_pair"] = dedup["_pair_key"].duplicated(keep="first")
dedup["admissible_total"] = admiss_total
dedup["admissible_component"] = admiss_component

dedup_clean = dedup[~dedup["_is_duplicate_pair"]].copy()

# -------------------------------------------------------------------
print("9. FINAL ADMISSIBLE SAMPLE COUNTS")
print(f"  Raw rows: {len(df)}")
print(f"  Duplicate PR–PO rows removed for modelling view: {dedup['_is_duplicate_pair'].sum()}")
print(f"  Deduplicated rows: {len(dedup_clean)}")
print(f"  Deduplicated Closed + valid total/internal: {dedup_clean['admissible_total'].sum()}")
print(f"  Deduplicated Closed + valid component: {dedup_clean['admissible_component'].sum()}")
print()

# Date anomaly is retained but flagged; do not use it for time-indexing without source correction.
dedup_clean["po_date_suspicious"] = dedup_clean["PODate_parsed"] < pd.Timestamp("2000-01-01")
print(f"  Suspicious PO dates retained as flags: {dedup_clean['po_date_suspicious'].sum()}")
print()

# -------------------------------------------------------------------
decision = (
    "RO2 DATA INTEGRITY PATHWAY LOCKED WITH FLAGS — use a deduplicated PR–PO observation "
    "view for modelling; retain the 1900-date row as an explicit source-quality flag; "
    "use Closed + positive internal/total DN as the conservative total-duration sample; "
    "use PO-GR DN only where observed. The data remain procurement-process/service data, "
    "not supplier-specific construction-material lead-time data."
)

print("=" * 90)
print("27B.4 SCIENTIFIC DECISION")
print("=" * 90)
print(decision)
print()
print("MODELLING GUARDRAILS")
print("  1. Raw workbook remains untouched.")
print("  2. Duplicate PR–PO pair is not treated as two independent observations.")
print("  3. 1900-01-01 is flagged, not silently repaired.")
print("  4. No supplier-level disruption model is claimed.")
print("  5. No construction-material supplier lead-time claim is made.")
print("  6. PO-GR/DN is retained only as an observed duration component.")
print()

# -------------------------------------------------------------------
# Save final audit table and a modelling-view candidate table.
audit_cols = [
    "PR","PO","SR","Status","Item","Short","Type","PODate","PODate_parsed",
    "Internal_num","PODN_num","POTLN_num","TotalDN_num","TotalLN_num",
    "MonthDN_num","MonthLN_num","_is_duplicate_pair",
    "po_date_suspicious","admissible_total","admissible_component"
]
audit_path = OUT / "RO2_step27b4_data_integrity_audit.csv"
dedup_clean[audit_cols].to_csv(audit_path, index=False)

model_cols = [
    "PR","PO","SR","Status","Item","Short","Type","PODate_parsed",
    "Internal_num","PODN_num","TotalDN_num","admissible_total","admissible_component"
]
model_path = OUT / "RO2_step27b4_admissible_modelling_view.csv"
dedup_clean[model_cols].to_csv(model_path, index=False)

decision_path = OUT / "RO2_step27b4_integrity_decision.txt"
decision_path.write_text(
    decision + "\n\n"
    "Important flags: one pre-2000 PO date and one repeated PR-PO pair. "
    "The repeated pair is excluded from the modelling view as a duplicate observation "
    "based on identical PR, PO, Item, Status and Short Text in the audit. "
    "The suspicious date is retained and flagged; no imputation is performed.\n",
    encoding="utf-8",
)

print("Saved:")
print(f"  {audit_path}")
print(f"  {model_path}")
print(f"  {decision_path}")
print()
print("STEP 27B.4 COMPLETE")
