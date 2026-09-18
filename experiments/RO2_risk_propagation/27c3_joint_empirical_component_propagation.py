"""
CMIDO — RO2 Step 27C.3
Joint Empirical Component Propagation + Bootstrap Stability

Purpose
-------
Preserve the observed pairing between:
    Internal procurement duration
    PO -> GR/DN duration

and quantify whether independently sampling the two marginal distributions
materially changes the propagated total-duration tail.

This is a diagnostic/uncertainty-representation step only.
It does NOT create supplier-specific lead-time labels, disruption labels,
or perform procurement optimization.

Input
-----
RO2_step27b4_admissible_modelling_view.csv
Locked numeric columns: Internal_num, PODN_num, TotalDN_num

Outputs
-------
results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv
results/RO2/distribution/RO2_step27c3_tail_comparison.csv
results/RO2/distribution/RO2_step27c3_dependence_bootstrap.csv
results/RO2/distribution/RO2_step27c3_bootstrap_quantiles.csv
results/RO2/distribution/RO2_step27c3_decision.txt
"""

from __future__ import annotations

from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr


SEED = 20260909
B = 10000
BOOT = 10000
TAIL_QS = [0.50, 0.75, 0.90, 0.95, 0.99]

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "results" / "RO2" / "data_audit" / "RO2_step27b4_admissible_modelling_view.csv"
OUTDIR = ROOT / "results" / "RO2" / "distribution"
OUTDIR.mkdir(parents=True, exist_ok=True)


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")


def qtable(x: np.ndarray) -> dict:
    return {f"q{int(q*100):02d}": float(np.quantile(x, q)) for q in TAIL_QS}


def bootstrap_quantiles(x: np.ndarray, name: str, rng: np.random.Generator) -> pd.DataFrame:
    n = len(x)
    idx = rng.integers(0, n, size=(BOOT, n))
    samples = x[idx]
    rows = []
    for q in TAIL_QS:
        vals = np.quantile(samples, q, axis=1)
        rows.append({
            "representation": name,
            "quantile": q,
            "estimate": float(np.quantile(x, q)),
            "bootstrap_mean": float(vals.mean()),
            "ci_2_5": float(np.quantile(vals, 0.025)),
            "ci_97_5": float(np.quantile(vals, 0.975)),
        })
    return pd.DataFrame(rows)


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Input not found:\n{INPUT}\n\n"
            "Copy the locked 27B.4 admissible modelling view into the project "
            "results/RO2/data_audit/ folder before running."
        )

    df = pd.read_csv(INPUT)

    # ------------------------------------------------------------------
    # LOCKED 27B.4 INPUT CONTRACT
    # ------------------------------------------------------------------
    # 27B.4 already established the admissible modelling view.  This step
    # MUST reproduce those integrity rules rather than inventing a new
    # filtering rule after seeing the 27C.3 results.
    #
    # Locked numeric fields:
    #   Internal_num : internal procurement-process duration
    #   PODN_num     : PO -> GR/DN observed component
    #   TotalDN_num  : observed total duration
    #
    # Locked identifiers:
    #   PR, PO, SR, Status
    required_locked_columns = [
        "PR", "PO", "SR", "Status",
        "Internal_num", "PODN_num", "TotalDN_num"
    ]
    missing = [c for c in required_locked_columns if c not in df.columns]
    if missing:
        raise KeyError(
            "The 27B.4 admissible modelling view does not match the locked "
            f"schema. Missing columns: {missing}. Available columns: "
            f"{list(df.columns)}"
        )

    internal_col = "Internal_num"
    po_gr_col = "PODN_num"
    total_col = "TotalDN_num"

    work = df.copy()

    # Numeric conversion is only type normalization; it is not a new
    # admissibility decision.
    for c in [internal_col, po_gr_col, total_col]:
        work[c] = pd.to_numeric(work[c], errors="coerce")

    # ------------------------------------------------------------------
    # Reapply the PRE-EXISTING 27B.4 integrity rules.
    # ------------------------------------------------------------------
    # 1) Retain rows with an actual PR and PO for the PR-PO observation view.
    # 2) Exclude the known source-quality anomaly represented by the malformed
    #    row (missing PR / PO='1' / 1900-01-01 source date) if those fields
    #    are available in the locked view.
    # 3) Deduplicate repeated PR-PO observations using the same identifiers.
    #
    # These rules are established before the component analysis and therefore
    # are not chosen to improve the 27C.3 result.
    admissible = work[
        work["PR"].notna()
        & work["PO"].notna()
        & (work["PO"].astype(str).str.strip() != "1")
    ].copy()

    before_dedup = len(admissible)
    duplicate_mask = admissible.duplicated(
        subset=["PR", "PO", "SR", "Status", "Internal_num",
                "PODN_num", "TotalDN_num"],
        keep="first",
    )
    duplicate_rows_removed = int(duplicate_mask.sum())
    admissible = admissible.loc[~duplicate_mask].copy()

    # 4) Conservative component sample: both observed components and the
    #    observed total must be positive.
    paired = admissible.dropna(
        subset=[internal_col, po_gr_col, total_col]
    ).copy()
    paired = paired[
        (paired[internal_col] > 0)
        & (paired[po_gr_col] > 0)
        & (paired[total_col] > 0)
    ].copy()

    # 5) Reproduce the locked 27B.4 component-sample size.
    #    If this is not exactly 37, stop rather than silently changing rules.
    if len(paired) != 37:
        raise AssertionError(
            "27B.4 component-sample contract failed: expected exactly 37 "
            f"paired observations after the locked admissibility/deduplication "
            f"rules, but obtained {len(paired)}. "
            "Do not proceed until the input or 27B.4 decision is reconciled."
        )

    x = paired[internal_col].to_numpy(float)
    y = paired[po_gr_col].to_numpy(float)
    observed_total = paired[total_col].to_numpy(float)
    paired_sum = x + y

    n = len(paired)
    if n < 20:
        raise ValueError(f"Only n={n} paired observations available; 20 is the minimum diagnostic threshold.")

    rng = np.random.default_rng(SEED)

    # ------------------------------------------------------------
    # 1. Exact reconstruction audit
    # ------------------------------------------------------------
    reconstruction_error = paired_sum - observed_total
    exact = np.isclose(reconstruction_error, 0.0, atol=1e-9)

    # With the locked 27B.4 component view, reconstruction should be exact.
    # Treat any remaining mismatch as a hard review condition.
    if not np.all(exact):
        bad_rows = paired.loc[~exact, ["PR", "PO", "SR", "Status",
                                       internal_col, po_gr_col, total_col]].copy()
        bad_rows["reconstruction_error_days"] = reconstruction_error[~exact]
        bad_path = OUTDIR / "RO2_step27c3_reconstruction_exceptions.csv"
        bad_rows.to_csv(bad_path, index=False)
        raise AssertionError(
            "Locked 27B.4 component reconstruction is not exact. "
            f"{len(bad_rows)} exception(s) written to {bad_path}. "
            "27C.3 is stopped; do not reinterpret the component mapping."
        )

    # ------------------------------------------------------------
    # 2. Dependence diagnostics + bootstrap CIs
    # ------------------------------------------------------------
    pearson_r, pearson_p = pearsonr(x, y)
    spearman_rho, spearman_p = spearmanr(x, y)

    boot_r = np.empty(BOOT)
    boot_rho = np.empty(BOOT)

    for b in range(BOOT):
        idx = rng.integers(0, n, n)
        xb = x[idx]
        yb = y[idx]

        if np.std(xb) == 0 or np.std(yb) == 0:
            boot_r[b] = np.nan
        else:
            boot_r[b] = np.corrcoef(xb, yb)[0, 1]

        boot_rho[b] = spearmanr(xb, yb).statistic

    dependence = pd.DataFrame([
        {
            "measure": "Pearson_r",
            "estimate": pearson_r,
            "p_value": pearson_p,
            "bootstrap_ci_2_5": np.nanpercentile(boot_r, 2.5),
            "bootstrap_ci_97_5": np.nanpercentile(boot_r, 97.5),
            "n": n,
        },
        {
            "measure": "Spearman_rho",
            "estimate": spearman_rho,
            "p_value": spearman_p,
            "bootstrap_ci_2_5": np.nanpercentile(boot_rho, 2.5),
            "bootstrap_ci_97_5": np.nanpercentile(boot_rho, 97.5),
            "n": n,
        },
    ])
    dependence.to_csv(
        OUTDIR / "RO2_step27c3_dependence_bootstrap.csv", index=False
    )

    # ------------------------------------------------------------
    # 3. Propagation representations
    #
    # Joint empirical:
    #   resample observed (x,y) pairs together.
    #
    # Independent marginals:
    #   sample x and y independently from their observed marginals.
    # ------------------------------------------------------------
    # One large Monte Carlo sample from each representation.
    joint_idx = rng.integers(0, n, B)
    joint_total = x[joint_idx] + y[joint_idx]

    indep_x = x[rng.integers(0, n, B)]
    indep_y = y[rng.integers(0, n, B)]
    independent_total = indep_x + indep_y

    # ------------------------------------------------------------
    # 4. Tail comparison
    # ------------------------------------------------------------
    rows = []
    for q in TAIL_QS:
        obs_q = float(np.quantile(observed_total, q))
        joint_q = float(np.quantile(joint_total, q))
        indep_q = float(np.quantile(independent_total, q))

        rows.extend([
            {
                "quantile": q,
                "representation": "Observed paired total",
                "quantile_days": obs_q,
                "difference_vs_observed": 0.0,
                "relative_difference_pct": 0.0,
            },
            {
                "quantile": q,
                "representation": "Joint empirical components",
                "quantile_days": joint_q,
                "difference_vs_observed": joint_q - obs_q,
                "relative_difference_pct": 100 * (joint_q - obs_q) / obs_q,
            },
            {
                "quantile": q,
                "representation": "Independent marginal components",
                "quantile_days": indep_q,
                "difference_vs_observed": indep_q - obs_q,
                "relative_difference_pct": 100 * (indep_q - obs_q) / obs_q,
            },
        ])

    tail = pd.DataFrame(rows)

    # Add direct independent-vs-joint comparison.
    direct = []
    for q in TAIL_QS:
        jq = float(np.quantile(joint_total, q))
        iq = float(np.quantile(independent_total, q))
        direct.append({
            "quantile": q,
            "joint_days": jq,
            "independent_days": iq,
            "independent_minus_joint_days": iq - jq,
            "independent_vs_joint_pct": 100 * (iq - jq) / jq,
        })
    direct_df = pd.DataFrame(direct)

    tail.to_csv(OUTDIR / "RO2_step27c3_tail_comparison.csv", index=False)

    # ------------------------------------------------------------
    # 5. Bootstrap stability of the joint and independent tails
    # ------------------------------------------------------------
    # Bootstrap paired observations. For each bootstrap sample:
    #   A = paired sum
    #   B = independently re-paired marginal draws
    #
    # This quantifies sampling uncertainty in the comparison itself.
    boot_rows = []
    for q in TAIL_QS:
        joint_boot = np.empty(BOOT)
        indep_boot = np.empty(BOOT)

        for b in range(BOOT):
            idx = rng.integers(0, n, n)
            xb = x[idx]
            yb = y[idx]

            joint_boot[b] = np.quantile(xb + yb, q)

            # Independent resampling from the bootstrap marginals.
            ix = rng.integers(0, n, n)
            iy = rng.integers(0, n, n)
            indep_boot[b] = np.quantile(xb[ix] + yb[iy], q)

        diff = indep_boot - joint_boot

        boot_rows.append({
            "quantile": q,
            "joint_point_estimate": float(np.quantile(joint_total, q)),
            "independent_point_estimate": float(np.quantile(independent_total, q)),
            "independent_minus_joint_estimate": float(np.quantile(independent_total, q) - np.quantile(joint_total, q)),
            "bootstrap_diff_mean": float(diff.mean()),
            "bootstrap_diff_ci_2_5": float(np.quantile(diff, 0.025)),
            "bootstrap_diff_ci_97_5": float(np.quantile(diff, 0.975)),
            "bootstrap_probability_independent_gt_joint": float(np.mean(diff > 0)),
            "n_paired": n,
        })

    boot_df = pd.DataFrame(boot_rows)
    boot_df.to_csv(
        OUTDIR / "RO2_step27c3_bootstrap_quantiles.csv", index=False
    )

    # ------------------------------------------------------------
    # 6. Summary + conservative decision rule
    # ------------------------------------------------------------
    max_abs_reconstruction = float(np.max(np.abs(reconstruction_error)))
    exact_rate = float(np.mean(exact))

    q95_row = direct_df.loc[direct_df["quantile"] == 0.95].iloc[0]
    q99_row = direct_df.loc[direct_df["quantile"] == 0.99].iloc[0]

    # We do NOT declare dependence solely from a p-value.
    ci_excludes_zero = (
        dependence.loc[dependence["measure"] == "Spearman_rho", "bootstrap_ci_2_5"].iloc[0] > 0
        or
        dependence.loc[dependence["measure"] == "Spearman_rho", "bootstrap_ci_97_5"].iloc[0] < 0
    )

    tail_material = (
        abs(float(q95_row["independent_vs_joint_pct"])) >= 5
        or abs(float(q99_row["independent_vs_joint_pct"])) >= 5
    )

    if exact_rate != 1.0:
        decision = "REVIEW_COMPONENT_MAPPING"
        rationale = (
            "The locked 27B.4 component sample failed exact reconstruction. "
            "This branch should not normally be reached because the script stops "
            "at the reconstruction audit."
        )
    elif tail_material:
        decision = "JOINT_EMPIRICAL_PRIMARY"
        rationale = (
            "The locked 27B.4 component pairs reconstruct the observed total "
            "exactly, and independent marginal sampling materially changes at "
            "least one upper-tail quantile. Preserve the observed pairing."
        )
    else:
        decision = "JOINT_EMPIRICAL_PRIMARY_WITH_SENSITIVITY"
        rationale = (
            "The locked 27B.4 component pairs reconstruct the observed total "
            "exactly. Independent marginal sampling does not materially change "
            "the tested upper tails, but the paired representation remains "
            "preferable because it is directly observed and avoids an unsupported "
            "independence assumption."
        )

    summary = pd.DataFrame([
        {
            "input_rows": len(df),
            "admissible_pr_po_rows_before_dedup": before_dedup,
            "duplicate_rows_removed": duplicate_rows_removed,
            "paired_n": n,
            "internal_column": internal_col,
            "po_gr_column": po_gr_col,
            "total_column": total_col,
            "exact_reconstruction_rate": exact_rate,
            "max_abs_reconstruction_error_days": max_abs_reconstruction,
            "pearson_r": pearson_r,
            "pearson_p": pearson_p,
            "spearman_rho": spearman_rho,
            "spearman_p": spearman_p,
            "spearman_bootstrap_ci_2_5": dependence.loc[dependence["measure"] == "Spearman_rho", "bootstrap_ci_2_5"].iloc[0],
            "spearman_bootstrap_ci_97_5": dependence.loc[dependence["measure"] == "Spearman_rho", "bootstrap_ci_97_5"].iloc[0],
            "independence_assumption_supported": not ci_excludes_zero,
            "q95_independent_minus_joint_days": float(q95_row["independent_minus_joint_days"]),
            "q95_independent_vs_joint_pct": float(q95_row["independent_vs_joint_pct"]),
            "q99_independent_minus_joint_days": float(q99_row["independent_minus_joint_days"]),
            "q99_independent_vs_joint_pct": float(q99_row["independent_vs_joint_pct"]),
            "decision": decision,
        }
    ])
    summary.to_csv(
        OUTDIR / "RO2_step27c3_joint_propagation_summary.csv", index=False
    )

    decision_text = f"""CMIDO RO2 STEP 27C.3 — JOINT EMPIRICAL COMPONENT PROPAGATION
================================================================

Input
-----
{INPUT}

Input/integrity audit
---------------------
Input rows: {len(df)}
Admissible PR-PO rows before deduplication: {before_dedup}
Duplicate rows removed: {duplicate_rows_removed}
Locked paired component rows: {n}

Resolved columns
----------------
Internal: {internal_col}
PO-GR/DN: {po_gr_col}
Total: {total_col}

Reconstruction audit
--------------------
Exact reconstruction rate: {exact_rate:.6f}
Maximum absolute reconstruction error: {max_abs_reconstruction:.6f} days

Dependence diagnostics
----------------------
Pearson r = {pearson_r:.6f}, p = {pearson_p:.6f}
Spearman rho = {spearman_rho:.6f}, p = {spearman_p:.6f}
Spearman bootstrap 95% CI =
    [{dependence.loc[dependence["measure"] == "Spearman_rho", "bootstrap_ci_2_5"].iloc[0]:.6f},
     {dependence.loc[dependence["measure"] == "Spearman_rho", "bootstrap_ci_97_5"].iloc[0]:.6f}]

Important interpretation:
A non-significant dependence test is NOT treated as proof of independence.
The primary representation is chosen from the observed data structure and
propagation consequences, not from a p-value alone.

Upper-tail comparison
---------------------
q95 independent vs joint:
    difference = {q95_row["independent_minus_joint_days"]:.3f} days
    relative   = {q95_row["independent_vs_joint_pct"]:.3f} %

q99 independent vs joint:
    difference = {q99_row["independent_minus_joint_days"]:.3f} days
    relative   = {q99_row["independent_vs_joint_pct"]:.3f} %

Decision
--------
{decision}

Rationale
---------
{rationale}

Scientific interpretation
--------------------------
The 37 paired component observations are retained as a joint empirical
uncertainty representation when component-level propagation is required.
This avoids inventing supplier-specific lead-time distributions and avoids
an unsupported independence assumption between procurement-process stages.

The separate 55-observation total-duration empirical distribution remains
the primary direct representation when only total procurement-process
duration is required.

This step is diagnostic only. It does not establish supplier-specific
construction-material lead time, disruption probability, or historical
shortage labels.
"""

    (OUTDIR / "RO2_step27c3_decision.txt").write_text(
        decision_text, encoding="utf-8"
    )

    # ------------------------------------------------------------
    # 7. Console report
    # ------------------------------------------------------------
    print("=" * 78)
    print("CMIDO RO2 STEP 27C.3 — JOINT EMPIRICAL COMPONENT PROPAGATION")
    print("=" * 78)
    print(f"Input: {INPUT}")
    print(f"Input rows: {len(df)}")
    print(f"Admissible PR-PO rows before deduplication: {before_dedup}")
    print(f"Duplicate rows removed: {duplicate_rows_removed}")
    print(f"Locked paired n: {n}")
    print(f"Exact reconstruction rate: {exact_rate:.4f}")
    print(f"Max abs reconstruction error: {max_abs_reconstruction:.4f} days")
    print()
    print(f"Pearson r={pearson_r:.4f}, p={pearson_p:.4f}")
    print(f"Spearman rho={spearman_rho:.4f}, p={spearman_p:.4f}")
    print(
        "Spearman bootstrap 95% CI: "
        f"[{dependence.loc[dependence['measure']=='Spearman_rho','bootstrap_ci_2_5'].iloc[0]:.4f}, "
        f"{dependence.loc[dependence['measure']=='Spearman_rho','bootstrap_ci_97_5'].iloc[0]:.4f}]"
    )
    print()
    print("TAIL COMPARISON")
    print(direct_df.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print()
    print("DECISION:", decision)
    print(rationale)
    print()
    print("Outputs:")
    for p in sorted(OUTDIR.glob("RO2_step27c3_*")):
        print(" -", p)
    print()
    print("STEP 27C.3 COMPLETE")


if __name__ == "__main__":
    main()
