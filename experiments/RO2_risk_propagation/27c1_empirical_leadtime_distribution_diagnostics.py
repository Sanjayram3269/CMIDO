from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "raw" / "RO2_Data LeadTime.xlsx"
OUT = ROOT / "results" / "RO2" / "data_audit"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 92)
print("CMIDO — RO2 STEP 27C.1 EMPIRICAL LEAD-TIME DISTRIBUTION DIAGNOSTICS")
print("=" * 92)
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

raw = pd.read_excel(SOURCE, sheet_name="Raw data", header=1)
raw.columns = [str(c).strip() for c in raw.columns]

# Recreate the conservative 27B.4 observation view directly from raw.
def get(name):
    return raw[name].map(clean) if name in raw.columns else pd.Series(np.nan, index=raw.index)

df = pd.DataFrame({
    "PR": get("Nomor PR"),
    "PO": get("Nomor PO"),
    "SR": get("Nomor SR"),
    "Status": get("Status"),
    "Item": get("Item Of"),
    "Short": get("Short Text"),
    "Type": get("Barang/Jasa"),
})
for name, source in {
    "Internal": "Total Leadtime Internal Kom Teknik",
    "PO_GR_DN": "PO - GR 103/101 (DN)",
    "Total_DN": "Total Hari Kerja All (DN)",
}.items():
    df[name] = get(source).map(num)

# Deduplicate exact PR-PO observation units conservatively.
df["_pair_key"] = df["PR"].fillna("<NA>") + "||" + df["PO"].fillna("<NA>")
df["_dup_pair"] = df["_pair_key"].duplicated(keep="first")

# Conservative total-duration sample and component sample.
closed = df["Status"].eq("Closed")
valid_internal = df["Internal"].notna() & (df["Internal"] > 0)
valid_total = df["Total_DN"].notna() & (df["Total_DN"] > 0)
valid_component = df["PO_GR_DN"].notna() & (df["PO_GR_DN"] > 0)

df["admissible_total"] = closed & valid_internal & valid_total & (~df["_dup_pair"])
df["admissible_component"] = df["admissible_total"] & valid_component

total = df.loc[df["admissible_total"], "Total_DN"].astype(float)
internal = df.loc[df["admissible_total"], "Internal"].astype(float)
component = df.loc[df["admissible_component"], "PO_GR_DN"].astype(float)

# Only 55 total and 37 component observations are admissible under 27B.4.
print("1. LOCKED EMPIRICAL SAMPLES")
print(f"  Total procurement-process duration: n={len(total)}")
print(f"  Internal procurement duration:      n={len(internal)}")
print(f"  PO-GR/DN duration component:        n={len(component)}")
print()

# ---------------------------------------------------------------------
def describe(name, x):
    q = np.quantile(x, [0, .01, .05, .10, .25, .50, .75, .90, .95, .99, 1])
    print(f"{name}")
    print(f"  n={len(x)}")
    print(f"  min={q[0]:.3f}, q01={q[1]:.3f}, q05={q[2]:.3f}, q10={q[3]:.3f}")
    print(f"  q25={q[4]:.3f}, median={q[5]:.3f}, q75={q[6]:.3f}, q90={q[7]:.3f}")
    print(f"  q95={q[8]:.3f}, q99={q[9]:.3f}, max={q[10]:.3f}")
    print(f"  mean={np.mean(x):.3f}, std={np.std(x, ddof=1):.3f}, CV={np.std(x,ddof=1)/np.mean(x):.3f}")
    print(f"  skew={stats.skew(x, bias=False):.3f}, excess_kurtosis={stats.kurtosis(x, fisher=True, bias=False):.3f}")
    print(f"  IQR={np.quantile(x,.75)-np.quantile(x,.25):.3f}")
    print()

print("2. DISTRIBUTIONAL DESCRIPTIVES")
describe("TOTAL PROCUREMENT-PROCESS DURATION (DN)", total)
describe("INTERNAL PROCUREMENT DURATION", internal)
describe("PO-GR / DN DURATION COMPONENT", component)

# ---------------------------------------------------------------------
print("3. OUTLIER / EXTREME-VALUE DIAGNOSTICS")
for name, x in [
    ("Total_DN", total),
    ("Internal", internal),
    ("PO_GR_DN", component),
]:
    q1, q3 = np.quantile(x, [.25, .75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    flags = x[(x < lo) | (x > hi)]
    print(f"  {name}: Tukey fences [{lo:.3f}, {hi:.3f}], flags={len(flags)}")
    if len(flags):
        print(f"    values={sorted(flags.tolist())}")
print("  Rule: extreme observations are flagged, not automatically deleted.")
print()

# ---------------------------------------------------------------------
print("4. NON-GAUSSIAN / TAIL EVIDENCE")
for name, x in [("Total_DN", total), ("Internal", internal), ("PO_GR_DN", component)]:
    jb = stats.jarque_bera(x)
    print(f"  {name}: Jarque-Bera statistic={jb.statistic:.4f}, p={jb.pvalue:.6g}")
print("  These tests are diagnostic only; they do not select the final distribution.")
print()

# ---------------------------------------------------------------------
print("5. EMPIRICAL QUANTILE STABILITY VIA BOOTSTRAP")
rng = np.random.default_rng(20260909)
B = 5000
quantiles = np.array([.50, .75, .90, .95, .99])
boot_rows = []

for name, x in [("Total_DN", total.to_numpy()), ("Internal", internal.to_numpy()), ("PO_GR_DN", component.to_numpy())]:
    boot = np.empty((B, len(quantiles)))
    for b in range(B):
        sample = rng.choice(x, size=len(x), replace=True)
        boot[b] = np.quantile(sample, quantiles)
    for j, q in enumerate(quantiles):
        ci = np.quantile(boot[:, j], [.025, .975])
        boot_rows.append({
            "variable": name,
            "quantile": q,
            "point_estimate": np.quantile(x, q),
            "bootstrap_ci_low": ci[0],
            "bootstrap_ci_high": ci[1],
        })
    print(f"  {name}: bootstrap {B} resamples complete.")
print()

boot_df = pd.DataFrame(boot_rows)
print("  Bootstrap interval table:")
print(boot_df.to_string(index=False))
print()

# ---------------------------------------------------------------------
print("6. COMPONENT DEPENDENCE: INTERNAL vs PO-GR/DN")
paired = df.loc[df["admissible_component"], ["Internal", "PO_GR_DN", "Total_DN"]].dropna()
print(f"  paired component observations: n={len(paired)}")
if len(paired) >= 5:
    pearson = stats.pearsonr(paired["Internal"], paired["PO_GR_DN"])
    spearman = stats.spearmanr(paired["Internal"], paired["PO_GR_DN"])
    print(f"  Pearson r={pearson.statistic:.4f}, p={pearson.pvalue:.6g}")
    print(f"  Spearman rho={spearman.statistic:.4f}, p={spearman.pvalue:.6g}")
    print(f"  median internal={paired['Internal'].median():.3f}")
    print(f"  median PO-GR/DN={paired['PO_GR_DN'].median():.3f}")
    print(f"  median sum={paired['Internal'].median()+paired['PO_GR_DN'].median():.3f}")
    print(f"  median observed total among paired={paired['Total_DN'].median():.3f}")
else:
    pearson = spearman = None
    print("  insufficient paired observations")
print()

# ---------------------------------------------------------------------
print("7. COMPONENT-SUM CONSISTENCY")
paired["sum_components"] = paired["Internal"] + paired["PO_GR_DN"]
paired["reconstruction_error"] = paired["sum_components"] - paired["Total_DN"]
print(f"  mean component sum: {paired['sum_components'].mean():.3f}")
print(f"  median component sum: {paired['sum_components'].median():.3f}")
print(f"  median reconstruction error: {paired['reconstruction_error'].median():.3f}")
print(f"  max abs reconstruction error: {paired['reconstruction_error'].abs().max():.3f}")
print(f"  exact reconstructions: {(paired['reconstruction_error'].abs()<1e-9).sum()}/{len(paired)}")
print()

# ---------------------------------------------------------------------
print("8. SAMPLE-SIZE / REPRESENTATION LIMITATIONS")
print("  Total duration n=55: adequate for empirical quantiles and bootstrap diagnostics,")
print("  but small for highly parameterized distributional models.")
print("  PO-GR/DN n=37: useful for empirical component characterization, but too small")
print("  to justify a complex conditional supplier-risk model.")
print("  Therefore the default candidate representation should remain empirical/non-parametric")
print("  unless later validation demonstrates a simple parametric model is superior.")
print()

# ---------------------------------------------------------------------
print("9. TEMPORAL STRUCTURE CHECK")
# There is no reliable start/requisition date in this Raw sheet, only PO date, and one
# source-quality anomaly. We therefore do not run a time-series drift test here.
print("  No formal temporal drift test is performed at 27C.1 because Raw data does not")
print("  provide a clean complete procurement-start date and contains one source-quality")
print("  date anomaly. Avoid manufacturing chronology.")
print()

# ---------------------------------------------------------------------
print("=" * 92)
print("27C.1 SCIENTIFIC DECISION")
print("=" * 92)
print("EMPIRICAL DISTRIBUTION IS THE PRIMARY RO2 UNCERTAINTY REPRESENTATION CANDIDATE.")
print()
print("Rationale:")
print("  • modest sample sizes (55 total; 37 component)")
print("  • positive durations with evident right-tail/extreme observations")
print("  • strong component reconstruction evidence")
print("  • no supplier identity or explicit receipt-date semantics")
print("  • insufficient evidence to justify a complex conditional distribution model")
print("  • empirical quantiles + bootstrap provide transparent uncertainty without")
print("    imposing Gaussian assumptions")
print()
print("NEXT GATE: 27C.2 — compare empirical distribution against a small, pre-specified")
print("set of simple positive-support parametric candidates using bootstrap/out-of-sample")
print("logic. Do NOT fit or select a distribution in 27C.1.")
print()

# Save outputs.
boot_path = OUT / "RO2_step27c1_bootstrap_quantiles.csv"
boot_df.to_csv(boot_path, index=False)

pair_path = OUT / "RO2_step27c1_component_pairs.csv"
paired.to_csv(pair_path, index=False)

summary = pd.DataFrame([
    {"variable":"Total_DN","n":len(total),"mean":total.mean(),"median":total.median(),"std":total.std(ddof=1),"cv":total.std(ddof=1)/total.mean(),"skew":stats.skew(total,bias=False),"excess_kurtosis":stats.kurtosis(total,fisher=True,bias=False)},
    {"variable":"Internal","n":len(internal),"mean":internal.mean(),"median":internal.median(),"std":internal.std(ddof=1),"cv":internal.std(ddof=1)/internal.mean(),"skew":stats.skew(internal,bias=False),"excess_kurtosis":stats.kurtosis(internal,fisher=True,bias=False)},
    {"variable":"PO_GR_DN","n":len(component),"mean":component.mean(),"median":component.median(),"std":component.std(ddof=1),"cv":component.std(ddof=1)/component.mean(),"skew":stats.skew(component,bias=False),"excess_kurtosis":stats.kurtosis(component,fisher=True,bias=False)},
])
summary_path = OUT / "RO2_step27c1_distribution_summary.csv"
summary.to_csv(summary_path, index=False)

decision_path = OUT / "RO2_step27c1_distribution_diagnostic_decision.txt"
decision_path.write_text(
    "RO2 STEP 27C.1\n"
    "Primary candidate uncertainty representation: empirical/non-parametric.\n"
    "No distribution was fitted or selected at this stage.\n"
    "Sample sizes: total duration n=55; PO-GR/DN component n=37.\n"
    "The final representation must preserve positive support and right-tail behaviour "
    "without imposing Gaussian assumptions. Parametric candidates may be compared in 27C.2.\n",
    encoding="utf-8",
)

print("Saved:")
print(f"  {boot_path}")
print(f"  {pair_path}")
print(f"  {summary_path}")
print(f"  {decision_path}")
print()
print("STEP 27C.1 COMPLETE")
