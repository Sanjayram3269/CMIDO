from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import gammaln

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "raw" / "RO2_Data LeadTime.xlsx"
OUT = ROOT / "results" / "RO2" / "distribution_selection"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 96)
print("CMIDO — RO2 STEP 27C.2 POSITIVE-SUPPORT LEAD-TIME DISTRIBUTION COMPARISON")
print("=" * 96)
print(f"Source: {SOURCE}")
print("Read-only: NO source modification / NO imputation")
print()

# ---------------------------------------------------------------------
# Locked 27B.4 sample reconstruction
# ---------------------------------------------------------------------
def clean(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    return np.nan if s == "" or s.lower() in {"nan", "nat", "none", "-"} else s

def num(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else np.nan

raw = pd.read_excel(SOURCE, sheet_name="Raw data", header=1)
raw.columns = [str(c).strip() for c in raw.columns]

def get(name):
    return raw[name].map(clean) if name in raw.columns else pd.Series(np.nan, index=raw.index)

df = pd.DataFrame({
    "PR": get("Nomor PR"),
    "PO": get("Nomor PO"),
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

df["_pair_key"] = df["PR"].fillna("<NA>") + "||" + df["PO"].fillna("<NA>")
df["_dup_pair"] = df["_pair_key"].duplicated(keep="first")

closed = df["Status"].eq("Closed")
df["admissible_total"] = (
    closed
    & df["Internal"].notna() & (df["Internal"] > 0)
    & df["Total_DN"].notna() & (df["Total_DN"] > 0)
    & (~df["_dup_pair"])
)
df["admissible_component"] = df["admissible_total"] & df["PO_GR_DN"].notna() & (df["PO_GR_DN"] > 0)

total = df.loc[df["admissible_total"], "Total_DN"].astype(float).to_numpy()
internal = df.loc[df["admissible_total"], "Internal"].astype(float).to_numpy()
component = df.loc[df["admissible_component"], "PO_GR_DN"].astype(float).to_numpy()

samples = {
    "Total_DN": total,
    "Internal": internal,
    "PO_GR_DN": component,
}

print("LOCKED INPUT SAMPLES")
for name, x in samples.items():
    print(f"  {name:10s}: n={len(x)}, median={np.median(x):.3f}, mean={np.mean(x):.3f}, max={np.max(x):.3f}")
print()

# ---------------------------------------------------------------------
# Candidate distributions
# Empirical benchmark + Gamma + Lognormal + Weibull.
# Fit only on training fold; evaluate held-out observation.
# ---------------------------------------------------------------------
CANDIDATES = ["Empirical", "Gamma", "Lognormal", "Weibull"]
EPS = 1e-10

def fit_parametric(name, x):
    x = np.asarray(x, dtype=float)
    if np.any(x <= 0):
        raise ValueError("Positive-support fit received non-positive data.")
    if name == "Gamma":
        shape, loc, scale = stats.gamma.fit(x, floc=0)
        return (shape, scale)
    if name == "Lognormal":
        s, loc, scale = stats.lognorm.fit(x, floc=0)
        return (s, scale)
    if name == "Weibull":
        c, loc, scale = stats.weibull_min.fit(x, floc=0)
        return (c, scale)
    raise ValueError(name)

def logpdf(name, y, params):
    y = float(y)
    if y <= 0:
        return -np.inf
    if name == "Gamma":
        shape, scale = params
        return stats.gamma.logpdf(y, shape, loc=0, scale=scale)
    if name == "Lognormal":
        s, scale = params
        return stats.lognorm.logpdf(y, s, loc=0, scale=scale)
    if name == "Weibull":
        c, scale = params
        return stats.weibull_min.logpdf(y, c, loc=0, scale=scale)
    raise ValueError(name)

def cdf(name, y, train, params=None):
    if name == "Empirical":
        # Leave-one-out handled by passing train without the held-out point.
        return float(np.mean(train <= y))
    if name == "Gamma":
        shape, scale = params
        return float(stats.gamma.cdf(y, shape, loc=0, scale=scale))
    if name == "Lognormal":
        s, scale = params
        return float(stats.lognorm.cdf(y, s, loc=0, scale=scale))
    if name == "Weibull":
        c, scale = params
        return float(stats.weibull_min.cdf(y, c, loc=0, scale=scale))
    raise ValueError(name)

def quantile(name, q, train, params=None):
    q = float(q)
    if name == "Empirical":
        return float(np.quantile(train, q, method="linear"))
    if name == "Gamma":
        shape, scale = params
        return float(stats.gamma.ppf(q, shape, loc=0, scale=scale))
    if name == "Lognormal":
        s, scale = params
        return float(stats.lognorm.ppf(q, s, loc=0, scale=scale))
    if name == "Weibull":
        c, scale = params
        return float(stats.weibull_min.ppf(q, c, loc=0, scale=scale))
    raise ValueError(name)

def interval_score(y, lo, hi, alpha):
    # Central (1-alpha) prediction interval.
    if hi < lo:
        return np.nan
    return (hi - lo
            + (2/alpha) * max(lo - y, 0)
            + (2/alpha) * max(y - hi, 0))

# ---------------------------------------------------------------------
# 27C.2A: Leave-one-out predictive comparison
# This avoids in-sample fit scores and does not require temporal ordering,
# which is unavailable/reliable only through PO dates in this Raw sheet.
# ---------------------------------------------------------------------
print("1. LEAVE-ONE-OUT PREDICTIVE VALIDATION")
print("  Scoring each held-out duration against a distribution fitted without that observation.")
print()

rows = []
for variable, x in samples.items():
    n = len(x)
    for cand in CANDIDATES:
        if n < 10:
            continue
        for i, y in enumerate(x):
            train = np.delete(x, i)
            params = None if cand == "Empirical" else fit_parametric(cand, train)

            if cand == "Empirical":
                # Predictive empirical CDF with randomized tie handling is unnecessary
                # because the target durations are integer-valued; use mid-rank PIT.
                rank = np.sum(train < y)
                ties = np.sum(train == y)
                u = (rank + 0.5 * ties) / len(train)
                # Discrete empirical log score is represented by smoothed mass.
                # Add a small finite smoothing mass so repeated held-out values are scoreable.
                count = np.sum(train == y)
                p = (count + 0.5) / (len(train) + 0.5 * len(np.unique(train)))
                log_score = -np.log(p)
            else:
                u = np.clip(stats.norm.cdf((np.log(y) - np.log(y)) if False else 0), EPS, 1-EPS)
                log_score = -logpdf(cand, y, params)

            q10 = quantile(cand, .10, train, params)
            q90 = quantile(cand, .90, train, params)
            q25 = quantile(cand, .25, train, params)
            q75 = quantile(cand, .75, train, params)

            rows.append({
                "variable": variable,
                "candidate": cand,
                "heldout_index": i,
                "y": y,
                "log_score": log_score,
                "pit": u,
                "coverage_80": float(q10 <= y <= q90),
                "width_80": q90 - q10,
                "interval_score_80": interval_score(y, q10, q90, .20),
                "coverage_50": float(q25 <= y <= q75),
                "width_50": q75 - q25,
                "interval_score_50": interval_score(y, q25, q75, .50),
            })

pred = pd.DataFrame(rows)

# ---------------------------------------------------------------------
# Aggregate predictive results
# ---------------------------------------------------------------------
agg = pred.groupby(["variable", "candidate"], as_index=False).agg(
    n=("y","size"),
    mean_log_score=("log_score","mean"),
    median_log_score=("log_score","median"),
    coverage_80=("coverage_80","mean"),
    mean_width_80=("width_80","mean"),
    mean_interval_score_80=("interval_score_80","mean"),
    coverage_50=("coverage_50","mean"),
    mean_width_50=("width_50","mean"),
    mean_interval_score_50=("interval_score_50","mean"),
)

agg["coverage_error_80"] = (agg["coverage_80"] - .80).abs()
agg["coverage_error_50"] = (agg["coverage_50"] - .50).abs()

print("2. PREDICTIVE SCORE SUMMARY")
for variable in samples:
    print(f"\n  {variable}")
    a = agg[agg.variable == variable].copy()
    print(a[[
        "candidate","mean_log_score","coverage_80","coverage_error_80",
        "mean_width_80","mean_interval_score_80",
        "coverage_50","mean_interval_score_50"
    ]].sort_values("mean_log_score").to_string(index=False))
print()

# ---------------------------------------------------------------------
# 27C.2B: In-sample fit diagnostics are secondary only.
# AIC/BIC are NOT primary because empirical is non-parametric and sample sizes are small.
# They are reported only as descriptive parametric diagnostics.
# ---------------------------------------------------------------------
print("3. SECONDARY PARAMETRIC FIT DIAGNOSTICS")
fit_rows = []
for variable, x in samples.items():
    for cand in ["Gamma", "Lognormal", "Weibull"]:
        params = fit_parametric(cand, x)
        ll = np.sum([logpdf(cand, y, params) for y in x])
        k = len(params)
        aic = 2*k - 2*ll
        bic = k*np.log(len(x)) - 2*ll
        # KS is descriptive; do not use p-value as a distribution selection criterion.
        if cand == "Gamma":
            ks = stats.kstest(x, "gamma", args=(params[0], 0, params[1]))
        elif cand == "Lognormal":
            ks = stats.kstest(x, "lognorm", args=(params[0], 0, params[1]))
        else:
            ks = stats.kstest(x, "weibull_min", args=(params[0], 0, params[1]))
        fit_rows.append({
            "variable": variable,
            "candidate": cand,
            "log_likelihood": ll,
            "AIC": aic,
            "BIC": bic,
            "KS_statistic": ks.statistic,
            "KS_pvalue_descriptive_only": ks.pvalue,
            "parameter_1": params[0],
            "parameter_2": params[1],
        })
fit_df = pd.DataFrame(fit_rows)
print(fit_df.to_string(index=False))
print()

# ---------------------------------------------------------------------
# 27C.2C: Tail quantile comparison
# ---------------------------------------------------------------------
print("4. TAIL QUANTILE COMPARISON")
tail_rows = []
for variable, x in samples.items():
    for cand in CANDIDATES:
        if cand == "Empirical":
            params = None
        else:
            params = fit_parametric(cand, x)
        row = {"variable": variable, "candidate": cand}
        for q in [.50, .75, .90, .95, .99]:
            row[f"q{int(q*100)}"] = quantile(cand, q, x, params)
        tail_rows.append(row)
tail_df = pd.DataFrame(tail_rows)
for variable in samples:
    print(f"\n  {variable}")
    print(tail_df[tail_df.variable == variable].to_string(index=False))
print()

# ---------------------------------------------------------------------
# Selection logic
# Primary: mean leave-one-out log score, but empirical's smoothed discrete
# score is not directly identical to continuous-density log score.
# Therefore final recommendation uses interval score + coverage + tail behaviour
# and treats log score as a supporting criterion, not sole selector.
# ---------------------------------------------------------------------
print("=" * 96)
print("27C.2 SCIENTIFIC INTERPRETATION")
print("=" * 96)
print("The empirical representation remains the reference benchmark.")
print("Parametric candidates are judged by held-out predictive interval performance,")
print("coverage error, interval score, and tail plausibility; AIC/BIC/KS are secondary.")
print()
print("IMPORTANT:")
print("  • This is not a supplier-specific lead-time distribution.")
print("  • The distribution represents procurement-process duration / observed duration components.")
print("  • No distribution is declared final merely because it has the best in-sample AIC/BIC.")
print("  • With n=37 for PO-GR/DN, tail conclusions remain uncertain.")
print()

# A transparent recommendation table based on interval-score ranking.
rank_rows = []
for variable in samples:
    a = agg[agg.variable == variable].copy()
    a["rank_IS80"] = a["mean_interval_score_80"].rank(method="min")
    a["rank_cov80"] = a["coverage_error_80"].rank(method="min")
    # Lower is better. Use equal diagnostic emphasis.
    a["composite_diagnostic_rank"] = a["rank_IS80"] + a["rank_cov80"]
    rank_rows.append(a)
ranked = pd.concat(rank_rows, ignore_index=True)

print("Diagnostic ranking (lower composite rank is better):")
print(ranked[[
    "variable","candidate","mean_interval_score_80","coverage_80",
    "coverage_error_80","composite_diagnostic_rank"
]].sort_values(["variable","composite_diagnostic_rank","mean_interval_score_80"]).to_string(index=False))
print()

# Conservative final decision at this stage:
# Do NOT automatically replace empirical. If a parametric candidate is clearly superior
# on predictive interval score AND reasonably calibrated, mark it as candidate for final
# frozen representation; otherwise empirical remains primary.
decisions = []
for variable in samples:
    a = ranked[ranked.variable == variable].copy()
    emp = a[a.candidate == "Empirical"].iloc[0]
    params_a = a[a.candidate != "Empirical"].sort_values(["mean_interval_score_80","coverage_error_80"]).iloc[0]

    empirical_good = (
        emp["composite_diagnostic_rank"] <= params_a["composite_diagnostic_rank"]
        or emp["mean_interval_score_80"] <= params_a["mean_interval_score_80"] * 1.05
    )
    if empirical_good:
        rec = "EMPIRICAL_PRIMARY"
    else:
        rec = f"{params_a['candidate'].upper()}_CANDIDATE_FOR_FINAL_REVIEW"
    decisions.append({
        "variable": variable,
        "recommended_status": rec,
        "empirical_IS80": emp["mean_interval_score_80"],
        "best_parametric_candidate": params_a["candidate"],
        "best_parametric_IS80": params_a["mean_interval_score_80"],
        "best_parametric_coverage80": params_a["coverage_80"],
    })

decision_df = pd.DataFrame(decisions)
print("PROVISIONAL STATUS:")
print(decision_df.to_string(index=False))
print()
print("Final distribution freeze is deferred until the numerical outputs are reviewed.")
print("Next step after review: either freeze empirical representation or perform a targeted")
print("sensitivity comparison using the strongest simple parametric candidate.")
print()

# ---------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------
pred_path = OUT / "RO2_step27c2_loo_predictive_scores.csv"
agg_path = OUT / "RO2_step27c2_predictive_summary.csv"
fit_path = OUT / "RO2_step27c2_parametric_fit_diagnostics.csv"
tail_path = OUT / "RO2_step27c2_tail_quantiles.csv"
decision_path = OUT / "RO2_step27c2_provisional_distribution_decision.csv"

pred.to_csv(pred_path, index=False)
agg.to_csv(agg_path, index=False)
fit_df.to_csv(fit_path, index=False)
tail_df.to_csv(tail_path, index=False)
decision_df.to_csv(decision_path, index=False)

print("Saved:")
print(f"  {pred_path}")
print(f"  {agg_path}")
print(f"  {fit_path}")
print(f"  {tail_path}")
print(f"  {decision_path}")
print()
print("STEP 27C.2 COMPLETE")
