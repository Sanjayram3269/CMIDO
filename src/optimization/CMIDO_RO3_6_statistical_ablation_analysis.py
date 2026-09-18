from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(r"D:\CMIDO")
IN = ROOT / "results" / "RO3" / "ablation" / "final_comparison"
OUT = IN

PRIMARY = [
    "realized_procurement_holding_cost",
    "realized_total_shortage",
    "realized_service_level",
    "realized_shortage_cvar95_monthly",
]
SECONDARY = [
    "realized_total_procurement_quantity",
    "realized_mean_ending_inventory",
    "realized_procurement_events",
]

PAIRS = [
    ("O2","O1","Optimization under deterministic information"),
    ("O3","O1","Probabilistic information under heuristic control"),
    ("O4","O2","Incremental uncertainty under optimization"),
    ("O4","O3","Incremental optimization under probabilistic information"),
    ("O4","O1","Integrated O4 versus deterministic heuristic"),
]

# Direction: lower is desirable for cost/shortage/CVaR/quantity/inventory/events;
# higher is desirable for service.
LOWER = set(PRIMARY + [SECONDARY[0], SECONDARY[1], SECONDARY[2]])

def load():
    p = IN / "RO3_step36_origin_level_results.csv"
    if not p.exists():
        raise FileNotFoundError(p)
    df = pd.read_csv(p)
    df["forecast_origin"] = pd.to_datetime(df["forecast_origin"])
    return df

def bootstrap_mean_diff(d, reps=10000, seed=20260916):
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(reps, len(d)))
    means = d[idx].mean(axis=1)
    return float(d.mean()), float(np.quantile(means,.025)), float(np.quantile(means,.975))

def effect_size_z(d):
    # Rank-biserial style paired effect: proportion positive vs negative,
    # excluding exact zeros. Sign is interpreted on raw (newer-base) difference.
    d = np.asarray(d, float)
    nz = d[np.abs(d)>1e-12]
    if len(nz)==0:
        return 0.0
    return float((np.sum(nz>0)-np.sum(nz<0))/len(nz))

def main():
    print("CMIDO RO3.6 — STATISTICAL ABLATION ANALYSIS")
    print("="*70)

    df = load()
    assert set(df.controller)=={"O1","O2","O3","O4"}
    assert df.groupby("controller").forecast_origin.nunique().eq(11).all()

    desc_rows=[]
    for ctrl,g in df.groupby("controller"):
        row={"controller":ctrl,"n_origins":g.forecast_origin.nunique()}
        for m in PRIMARY+SECONDARY:
            row[m+"_mean"]=g[m].mean()
            row[m+"_median"]=g[m].median()
            row[m+"_std"]=g[m].std(ddof=1)
        desc_rows.append(row)
    desc=pd.DataFrame(desc_rows)

    comparison_rows=[]
    bootstrap_rows=[]
    origin_rows=[]

    for newer,base,label in PAIRS:
        a=df[df.controller==newer].set_index("forecast_origin")
        b=df[df.controller==base].set_index("forecast_origin")
        common=a.index.intersection(b.index)
        for m in PRIMARY+SECONDARY:
            d=(a.loc[common,m]-b.loc[common,m]).to_numpy(float)
            mean,lo,hi=bootstrap_mean_diff(d)
            try:
                if np.all(np.abs(d)<1e-12):
                    p=1.0
                else:
                    p=float(wilcoxon(d, zero_method="wilcox", alternative="two-sided", method="auto").pvalue)
            except Exception:
                p=np.nan

            improved = int(np.sum(d < -1e-12)) if m in LOWER else int(np.sum(d > 1e-12))
            worsened = int(np.sum(d > 1e-12)) if m in LOWER else int(np.sum(d < -1e-12))
            ties = len(d)-improved-worsened

            base_mean=float(b.loc[common,m].mean())
            rel=np.nan if abs(base_mean)<1e-12 else float(mean/base_mean)

            comparison_rows.append({
                "comparison":f"{newer}_vs_{base}",
                "contrast":label,
                "metric":m,
                "n_origins":len(d),
                "newer_mean":float(a.loc[common,m].mean()),
                "base_mean":base_mean,
                "mean_difference_newer_minus_base":mean,
                "relative_mean_difference":rel,
                "bootstrap_ci95_lower":lo,
                "bootstrap_ci95_upper":hi,
                "wilcoxon_p_raw":p,
                "improved_count":improved,
                "worsened_count":worsened,
                "tie_count":ties,
                "rank_biserial_sign":effect_size_z(d)
            })

            for origin,x,y,z in zip(common,a.loc[common,m],b.loc[common,m],d):
                origin_rows.append({
                    "comparison":f"{newer}_vs_{base}",
                    "metric":m,
                    "forecast_origin":origin,
                    "newer_value":float(x),
                    "base_value":float(y),
                    "difference":float(z)
                })

    comp=pd.DataFrame(comparison_rows)

    # Benjamini-Hochberg FDR across all non-null Wilcoxon p-values.
    pvals=comp["wilcoxon_p_raw"].to_numpy(float)
    order=np.argsort(np.where(np.isnan(pvals),np.inf,pvals))
    q=np.full(len(pvals),np.nan)
    valid=[i for i in order if np.isfinite(pvals[i])]
    prev=1.0
    for rank,i in reversed(list(enumerate(valid, start=1))):
        val=min(prev, pvals[i]*len(valid)/rank)
        q[i]=val
        prev=val
    comp["wilcoxon_q_bh"]=q
    comp["significant_bh_0_05"]=comp.wilcoxon_q_bh < .05

    # Compact primary-only results.
    primary=comp[comp.metric.isin(PRIMARY)].copy()

    # Incremental-value summary at the level of each contrast.
    iv=[]
    for contrast in [
        ("O2","O1","optimization_value_deterministic"),
        ("O3","O1","uncertainty_value_heuristic"),
        ("O4","O2","incremental_uncertainty_with_optimization"),
        ("O4","O3","incremental_optimization_with_uncertainty"),
        ("O4","O1","integrated_difference"),
    ]:
        newer,base,name=contrast
        for m in PRIMARY:
            r=comp[(comp.comparison==f"{newer}_vs_{base}")&(comp.metric==m)].iloc[0]
            iv.append({
                "ablation_contrast":name,
                "metric":m,
                "mean_difference":r.mean_difference_newer_minus_base,
                "ci95_lower":r.bootstrap_ci95_lower,
                "ci95_upper":r.bootstrap_ci95_upper,
                "wilcoxon_q_bh":r.wilcoxon_q_bh,
                "improved_origins":r.improved_count,
                "worsened_origins":r.worsened_count,
                "ties":r.tie_count
            })
    iv=pd.DataFrame(iv)

    # Integrity.
    checks=[]
    def ck(name,cond,detail=""):
        checks.append({"check":name,"passed":bool(cond),"detail":detail})
        print("[PASS]" if cond else "[FAIL]",name,detail)

    ck("11 origins per controller", df.groupby("controller").forecast_origin.nunique().eq(11).all())
    ck("Primary metrics finite", np.isfinite(df[PRIMARY].to_numpy()).all())
    ck("Secondary metrics finite", np.isfinite(df[SECONDARY].to_numpy()).all())
    ck("All five contrasts represented", len(comp.comparison.unique())==5)
    ck("All primary contrast rows", len(primary)==20, str(len(primary)))
    ck("Bootstrap CIs finite", np.isfinite(comp[["bootstrap_ci95_lower","bootstrap_ci95_upper"]].to_numpy()).all())
    ck("No undefined relative baseline in primary", np.isfinite(primary.relative_mean_difference).all())
    ck("BH correction complete", primary.wilcoxon_q_bh.notna().all())

    audit=pd.DataFrame(checks)
    status="PASS" if audit.passed.all() else "HOLD"

    desc.to_csv(OUT/"RO3_step36_controller_descriptive_statistics.csv",index=False)
    comp.to_csv(OUT/"RO3_step36_statistical_pairwise_comparisons.csv",index=False)
    primary.to_csv(OUT/"RO3_step36_primary_ablation_results.csv",index=False)
    iv.to_csv(OUT/"RO3_step36_incremental_value_summary.csv",index=False)
    pd.DataFrame(origin_rows).to_csv(OUT/"RO3_step36_origin_paired_differences.csv",index=False)
    audit.to_csv(OUT/"RO3_step36_statistical_analysis_audit.csv",index=False)

    print("\nPRIMARY RESULTS")
    print(primary[[
        "comparison","metric","newer_mean","base_mean",
        "mean_difference_newer_minus_base",
        "bootstrap_ci95_lower","bootstrap_ci95_upper",
        "wilcoxon_q_bh","improved_count","worsened_count"
    ]].to_string(index=False))

    print("\nCONTROLLER DESCRIPTIVES")
    print(desc.to_string(index=False))

    print("\nCHECKS PASSED:",int(audit.passed.sum()),"/",len(audit))
    print("STATUS:",status)
    print("OUTPUT:",OUT)

if __name__=="__main__":
    main()
