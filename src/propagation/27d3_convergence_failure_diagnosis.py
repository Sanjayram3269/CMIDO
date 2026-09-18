"""
CMIDO — RO2 Step 27D.3
Monte Carlo Convergence Failure Diagnosis

Run from:
    D:/CMIDO

Command:
    python src/propagation/27d3_convergence_failure_diagnosis.py

Diagnostic only. Reads Step 27D.2 outputs; does not rerun propagation.
"""

from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
IN_DIR = ROOT / "results" / "RO2" / "propagation_convergence"
OUT_DIR = ROOT / "results" / "RO2" / "propagation_convergence_diagnosis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHANGES = IN_DIR / "RO2_step27d2_convergence_changes.csv"
STABILITY = IN_DIR / "RO2_step27d2_stability_summary.csv"

CRITERIA = {
    "mean": 1.0,
    "q90": 2.0,
    "q95": 2.0,
    "q99": 5.0,
}

PRIMARY_TRANSITION = (5000, 10000)
DIAGNOSTIC_TRANSITION = (10000, 25000)

MATERIALS = [
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
]


def require_inputs():
    for p in [CHANGES, STABILITY]:
        if not p.exists():
            raise FileNotFoundError(p)


def classify_failure(failed_stats: list[str]) -> str:
    s = set(failed_stats)

    if "mean" in s:
        if s - {"mean"}:
            return "MULTIPLE_REGIMES"
        return "CENTRAL_OR_MEAN"

    if "q90" in s:
        return "MID_TAIL"

    if s and s.issubset({"q95", "q99"}):
        return "TAIL_LOCALIZED"

    return "NO_FAILURE"


def main():
    print("=" * 80)
    print("CMIDO RO2 STEP 27D.3 — CONVERGENCE FAILURE DIAGNOSIS")
    print("=" * 80)

    require_inputs()

    changes = pd.read_csv(CHANGES)
    stability = pd.read_csv(STABILITY)

    required = {
        "material",
        "forecast_origin",
        "from_mc_n",
        "to_mc_n",
        "statistic",
        "previous_value",
        "current_value",
        "absolute_change",
        "relative_change_pct",
    }
    missing = required - set(changes.columns)
    if missing:
        raise AssertionError(f"Missing change columns: {sorted(missing)}")

    # Primary 5k -> 10k diagnostic matrix.
    primary = changes[
        (changes["from_mc_n"] == PRIMARY_TRANSITION[0])
        & (changes["to_mc_n"] == PRIMARY_TRANSITION[1])
        & (changes["statistic"].isin(CRITERIA))
    ].copy()

    # 10k -> 25k diagnostic matrix.
    diagnostic = changes[
        (changes["from_mc_n"] == DIAGNOSTIC_TRANSITION[0])
        & (changes["to_mc_n"] == DIAGNOSTIC_TRANSITION[1])
        & (changes["statistic"].isin(CRITERIA))
    ].copy()

    if len(primary) != 48 * len(CRITERIA):
        raise AssertionError(
            f"Expected {48 * len(CRITERIA)} primary rows, found {len(primary)}"
        )

    # Determine failed statistics per material/origin.
    failure_rows = []

    for (material, origin), g in primary.groupby(
        ["material", "forecast_origin"], sort=True
    ):
        failed = []
        metrics = {}

        for stat, threshold in CRITERIA.items():
            row = g[g["statistic"].eq(stat)]
            if len(row) != 1:
                raise AssertionError(
                    f"Expected one row for {material}/{origin}/{stat}"
                )

            pct = float(row["relative_change_pct"].iloc[0])
            metrics[f"{stat}_pct_5k_to_10k"] = pct
            metrics[f"{stat}_pass"] = pct <= threshold

            if pct > threshold:
                failed.append(stat)

        failure_rows.append({
            "material": material,
            "forecast_origin": origin,
            "failed_statistics": ",".join(failed) if failed else "",
            "failure_class": classify_failure(failed),
            "case_stable_at_10000": len(failed) == 0,
            **metrics,
        })

    failure_detail = pd.DataFrame(failure_rows)

    # Add 10k -> 25k diagnostics for every material/origin/statistic.
    dwide = diagnostic.pivot_table(
        index=["material", "forecast_origin"],
        columns="statistic",
        values=["relative_change_pct", "absolute_change"],
        aggfunc="first",
    )

    dwide.columns = [
        f"{a}_{b}_10k_to_25k"
        for a, b in dwide.columns
    ]
    dwide = dwide.reset_index()

    failure_detail = failure_detail.merge(
        dwide,
        on=["material", "forecast_origin"],
        how="left",
        validate="one_to_one",
    )

    # Material-level summary.
    material_rows = []

    for material in MATERIALS:
        g = failure_detail[
            failure_detail["material"].eq(material)
        ].copy()

        failed_cases = ~g["case_stable_at_10000"]
        failure_count = int(failed_cases.sum())

        row = {
            "material": material,
            "n_cases": len(g),
            "n_failed_cases": failure_count,
            "failure_rate_pct": 100 * failure_count / len(g),
        }

        for stat in CRITERIA:
            col = f"{stat}_pass"
            row[f"{stat}_failure_count"] = int((~g[col]).sum())
            row[f"{stat}_failure_rate_pct"] = (
                100 * int((~g[col]).sum()) / len(g)
            )

            pct_col = f"{stat}_pct_5k_to_10k"
            row[f"{stat}_median_pct"] = float(g[pct_col].median())
            row[f"{stat}_p90_pct"] = float(g[pct_col].quantile(0.90))
            row[f"{stat}_max_pct"] = float(g[pct_col].max())

        row["max_any_stat_pct"] = float(
            g[[f"{s}_pct_5k_to_10k" for s in CRITERIA]].max().max()
        )

        material_rows.append(row)

    material_summary = pd.DataFrame(material_rows)

    # Failure class counts.
    class_summary = (
        failure_detail["failure_class"]
        .value_counts()
        .rename_axis("failure_class")
        .reset_index(name="n_cases")
    )
    class_summary["pct_cases"] = (
        100 * class_summary["n_cases"] / len(failure_detail)
    )

    # Compare 10k -> 25k changes in the cases that failed at 10k.
    failing = failure_detail[
        ~failure_detail["case_stable_at_10000"]
    ].copy()

    # For each failing case, evaluate whether 25k reduces the corresponding
    # statistic's change relative to the threshold. This is diagnostic only.
    diagnostic_rows = []

    for _, r in failing.iterrows():
        failed_stats = [
            s for s in CRITERIA
            if not bool(r[f"{s}_pass"])
        ]

        for stat in failed_stats:
            c = f"relative_change_pct_{stat}_10k_to_25k"
            val = r.get(c, np.nan)

            diagnostic_rows.append({
                "material": r["material"],
                "forecast_origin": r["forecast_origin"],
                "failed_statistic_at_10000": stat,
                "change_5k_to_10k_pct": r[f"{stat}_pct_5k_to_10k"],
                "change_10k_to_25k_pct": val,
                "threshold_pct": CRITERIA[stat],
                "10k_to_25k_below_threshold": (
                    bool(val <= CRITERIA[stat])
                    if np.isfinite(val) else False
                ),
            })

    diagnostic_summary = pd.DataFrame(diagnostic_rows)

    # Study-level facts.
    n_cases = len(failure_detail)
    n_stable = int(failure_detail["case_stable_at_10000"].sum())

    # Which statistic is most responsible?
    failure_counts = {
        stat: int((~failure_detail[f"{stat}_pass"]).sum())
        for stat in CRITERIA
    }

    dominant_stat = max(failure_counts, key=failure_counts.get)

    max_primary = float(
        primary["relative_change_pct"].max()
    )
    max_diagnostic = float(
        diagnostic["relative_change_pct"].max()
    )

    # No MC lock is made here.
    decision = "DIAGNOSTIC_COMPLETE_HOLD_FOR_MC_LOCK"

    # Persist outputs.
    failure_detail.to_csv(
        OUT_DIR / "RO2_step27d3_case_failure_detail.csv",
        index=False,
    )
    material_summary.to_csv(
        OUT_DIR / "RO2_step27d3_material_summary.csv",
        index=False,
    )
    class_summary.to_csv(
        OUT_DIR / "RO2_step27d3_failure_class_summary.csv",
        index=False,
    )
    diagnostic_summary.to_csv(
        OUT_DIR / "RO2_step27d3_failed_case_10k_to_25k.csv",
        index=False,
    )

    summary = {
        "step": "27D.3",
        "decision": decision,
        "n_material_origin_cases": n_cases,
        "n_stable_at_10000": n_stable,
        "n_failed_at_10000": n_cases - n_stable,
        "stable_rate_pct": 100 * n_stable / n_cases,
        "failure_counts_by_statistic": failure_counts,
        "dominant_failure_statistic": dominant_stat,
        "max_5k_to_10k_relative_change_pct": max_primary,
        "max_10k_to_25k_relative_change_pct": max_diagnostic,
        "note": (
            "This step diagnoses aggregate convergence patterns only. "
            "Raw Monte Carlo exposure vectors were not persisted by 27D, "
            "so exact individual simulated-draw causes cannot be identified."
        ),
        "test_data_used": False,
        "primary_representation": "joint_duration_primary",
    }

    (OUT_DIR / "RO2_step27d3_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    lines = [
        f"DECISION: {decision}",
        "",
        f"Material-origin cases: {n_cases}",
        f"Stable at 10,000: {n_stable}",
        f"Failed at 10,000: {n_cases - n_stable}",
        f"Stable rate: {100 * n_stable / n_cases:.2f}%",
        "",
        "Failure counts by statistic:",
    ]

    for stat, count in failure_counts.items():
        lines.append(f"- {stat}: {count}/{n_cases}")

    lines += [
        "",
        f"Dominant failure statistic: {dominant_stat}",
        f"Maximum 5k -> 10k relative change: {max_primary:.6f}%",
        f"Maximum 10k -> 25k relative change: {max_diagnostic:.6f}%",
        "",
        "No MC lock is made by 27D.3.",
        "27D.3 is diagnostic only.",
        "No RO1 test forecasts were used.",
        "Procurement-process duration terminology retained.",
    ]

    (OUT_DIR / "RO2_step27d3_decision.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("\nDIAGNOSTIC RESULTS")
    print(f"Material-origin cases: {n_cases}")
    print(f"Stable at 10,000: {n_stable}/{n_cases}")
    print(f"Failed at 10,000: {n_cases - n_stable}/{n_cases}")

    print("\nFailure counts:")
    for stat, count in failure_counts.items():
        print(f"  {stat:>4}: {count}/{n_cases}")

    print(f"\nDominant failure statistic: {dominant_stat}")
    print(
        "Maximum 5k -> 10k relative change:",
        f"{max_primary:.6f}%",
    )
    print(
        "Maximum 10k -> 25k relative change:",
        f"{max_diagnostic:.6f}%",
    )

    print("\nDecision:", decision)
    print("\nOutputs:")
    for p in sorted(OUT_DIR.iterdir()):
        if p.is_file():
            print(" -", p)

    print("\n27D.3 diagnostic complete.")


if __name__ == "__main__":
    main()
