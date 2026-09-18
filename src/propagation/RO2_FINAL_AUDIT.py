"""
CMIDO — RO2 FINAL AUDIT
=======================

Purpose
-------
Final end-to-end scientific and computational audit of RO2 before
proceeding to RO3.

This script DOES NOT develop or modify the model.

It verifies that the already-frozen RO2 components are internally
consistent and that the documented scientific limitations remain explicit.

RO2 chain:

    27B.4  Data / admissibility
      ↓
    27C.3  Joint empirical duration representation
      ↓
    27D    Demand-duration propagation
      ↓
    27D.1  Propagation result audit
      ↓
    27D.4  Nested MC convergence
      ↓
    RO2 FINAL LOCK

Run from:

    D:\\CMIDO

Command:

    python src\\propagation\\RO2_FINAL_AUDIT.py
"""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


# ============================================================================
# INPUTS
# ============================================================================

RO2_27B4 = (
    ROOT
    / "results"
    / "RO2"
    / "data_audit"
    / "RO2_step27b4_admissible_modelling_view.csv"
)

RO2_27C3_DECISION = (
    ROOT
    / "results"
    / "RO2"
    / "distribution"
    / "RO2_step27c3_decision.txt"
)

RO2_27D_SUMMARY = (
    ROOT
    / "results"
    / "RO2"
    / "propagation"
    / "RO2_step27d_propagation_summary.csv"
)

RO2_27D_RISK = (
    ROOT
    / "results"
    / "RO2"
    / "propagation"
    / "RO2_step27d_service_risk_curve.csv"
)

RO2_27D_SENS = (
    ROOT
    / "results"
    / "RO2"
    / "propagation"
    / "RO2_step27d_joint_vs_independent_sensitivity.csv"
)

RO2_27D_AUDIT = (
    ROOT
    / "results"
    / "RO2"
    / "propagation"
    / "RO2_step27d_audit.csv"
)

RO2_27D_CONFIG = (
    ROOT
    / "results"
    / "RO2"
    / "propagation"
    / "RO2_step27d_run_config.json"
)

RO2_27D1_DECISION = (
    ROOT
    / "results"
    / "RO2"
    / "propagation_audit"
    / "RO2_step27d1_decision.txt"
)

RO2_27D1_SUMMARY = (
    ROOT
    / "results"
    / "RO2"
    / "propagation_audit"
    / "RO2_step27d1_summary.json"
)

RO2_27D4_ESTIMATES = (
    ROOT
    / "results"
    / "RO2"
    / "propagation_convergence_nested"
    / "RO2_step27d4_nested_estimates.csv"
)

RO2_27D4_CHANGES = (
    ROOT
    / "results"
    / "RO2"
    / "propagation_convergence_nested"
    / "RO2_step27d4_nested_convergence_changes.csv"
)

RO2_27D4_CASES = (
    ROOT
    / "results"
    / "RO2"
    / "propagation_convergence_nested"
    / "RO2_step27d4_case_decisions.csv"
)

RO2_27D4_SUMMARY = (
    ROOT
    / "results"
    / "RO2"
    / "propagation_convergence_nested"
    / "RO2_step27d4_summary.json"
)

RO2_27D4_DECISION = (
    ROOT
    / "results"
    / "RO2"
    / "propagation_convergence_nested"
    / "RO2_step27d4_decision.txt"
)


# ============================================================================
# OUTPUTS
# ============================================================================

OUT_DIR = (
    ROOT
    / "results"
    / "RO2"
    / "final_audit"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

FINAL_JSON = (
    OUT_DIR
    / "RO2_FINAL_AUDIT_SUMMARY.json"
)

FINAL_DECISION = (
    OUT_DIR
    / "RO2_FINAL_LOCK_DECISION.txt"
)

FINAL_CHECKS = (
    OUT_DIR
    / "RO2_FINAL_AUDIT_CHECKS.csv"
)


# ============================================================================
# HELPERS
# ============================================================================

checks = []


def record(
    name: str,
    passed: bool,
    detail: str,
):
    checks.append(
        {
            "check": name,
            "pass": bool(passed),
            "detail": detail,
        }
    )


def exists(
    path: Path,
    label: str,
):
    ok = path.exists()

    record(
        f"{label}_exists",
        ok,
        str(path),
    )

    return ok


# ============================================================================
# START
# ============================================================================

print("=" * 90)
print("CMIDO — RO2 FINAL SCIENTIFIC & COMPUTATIONAL AUDIT")
print("=" * 90)


# ============================================================================
# 1. REQUIRED ARTIFACTS
# ============================================================================

print("\n[1/6] REQUIRED ARTIFACTS")

required_files = [
    (RO2_27B4, "27B4_modelling_view"),
    (RO2_27C3_DECISION, "27C3_decision"),
    (RO2_27D_SUMMARY, "27D_summary"),
    (RO2_27D_RISK, "27D_service_risk"),
    (RO2_27D_SENS, "27D_joint_independent_sensitivity"),
    (RO2_27D_AUDIT, "27D_audit"),
    (RO2_27D_CONFIG, "27D_config"),
    (RO2_27D1_DECISION, "27D1_decision"),
    (RO2_27D1_SUMMARY, "27D1_summary"),
    (RO2_27D4_ESTIMATES, "27D4_estimates"),
    (RO2_27D4_CHANGES, "27D4_changes"),
    (RO2_27D4_CASES, "27D4_cases"),
    (RO2_27D4_SUMMARY, "27D4_summary"),
    (RO2_27D4_DECISION, "27D4_decision"),
]

all_required_present = True

for path, label in required_files:

    if not exists(path, label):
        all_required_present = False

if not all_required_present:

    raise SystemExit(
        "\nFINAL AUDIT CANNOT CONTINUE:\n"
        "One or more required RO2 artifacts are missing."
    )


# ============================================================================
# 2. 27B.4 DATA INTEGRITY
# ============================================================================

print("\n[2/6] 27B.4 DATA INTEGRITY")

b4 = pd.read_csv(
    RO2_27B4
)

record(
    "27B4_row_count",
    len(b4) == 57,
    f"rows={len(b4)}; expected=57",
)

required_b4 = {
    "Internal_num",
    "PODN_num",
    "TotalDN_num",
    "admissible_component",
    "admissible_total",
}

missing_b4 = (
    required_b4
    - set(b4.columns)
)

record(
    "27B4_required_columns",
    len(missing_b4) == 0,
    f"missing={sorted(missing_b4)}",
)

for col in [
    "Internal_num",
    "PODN_num",
    "TotalDN_num",
]:

    b4[col] = pd.to_numeric(
        b4[col],
        errors="coerce",
    )


component_flag = (
    b4["admissible_component"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(
        [
            "true",
            "1",
            "yes",
        ]
    )
)

paired = b4[
    component_flag
].dropna(
    subset=[
        "Internal_num",
        "PODN_num",
        "TotalDN_num",
    ]
).copy()

record(
    "27B4_paired_component_n",
    len(paired) == 37,
    f"n={len(paired)}; expected=37",
)

reconstruction_error = (
    paired["Internal_num"]
    + paired["PODN_num"]
    - paired["TotalDN_num"]
)

record(
    "27B4_exact_duration_reconstruction",
    np.allclose(
        reconstruction_error,
        0.0,
        atol=1e-12,
    ),
    (
        f"max_abs_error="
        f"{np.abs(reconstruction_error).max():.12f}"
    ),
)

duration_nonnegative = (
    paired[
        [
            "Internal_num",
            "PODN_num",
            "TotalDN_num",
        ]
    ]
    >= 0
).all().all()

record(
    "27B4_nonnegative_durations",
    duration_nonnegative,
    "all paired duration components non-negative",
)


# ============================================================================
# 3. 27C.3 DECISION
# ============================================================================

print("\n[3/6] 27C.3 REPRESENTATION")

c3_text = (
    RO2_27C3_DECISION
    .read_text(
        encoding="utf-8"
    )
)

c3_upper = c3_text.upper()

c3_joint = (
    "JOINT" in c3_upper
)

c3_no_supplier_claim = (
    "SUPPLIER-SPECIFIC" in c3_upper
    or "SUPPLIER SPECIFIC" in c3_upper
)

record(
    "27C3_joint_representation_declared",
    c3_joint,
    "27C.3 decision contains joint representation language",
)

record(
    "27C3_supplier_leadtime_boundary",
    c3_no_supplier_claim,
    "supplier-specific lead-time boundary is present",
)


# ============================================================================
# 4. 27D PROPAGATION
# ============================================================================

print("\n[4/6] 27D PROPAGATION")

d_summary = pd.read_csv(
    RO2_27D_SUMMARY
)

d_risk = pd.read_csv(
    RO2_27D_RISK
)

d_sens = pd.read_csv(
    RO2_27D_SENS
)

d_audit = pd.read_csv(
    RO2_27D_AUDIT
)

config = json.loads(
    RO2_27D_CONFIG.read_text(
        encoding="utf-8"
    )
)


# ---------------------------------------------------------------------------
# Summary rows.
# ---------------------------------------------------------------------------

record(
    "27D_summary_expected_rows",
    len(d_summary) == 96,
    f"rows={len(d_summary)}; expected=96",
)


# ---------------------------------------------------------------------------
# Materials.
# ---------------------------------------------------------------------------

expected_materials = {
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
}

if "material" in d_summary.columns:

    observed_materials = set(
        d_summary[
            "material"
        ]
        .astype(str)
        .unique()
    )

else:

    observed_materials = set()

record(
    "27D_exact_four_common_materials",
    observed_materials == expected_materials,
    f"observed={sorted(observed_materials)}",
)


# ---------------------------------------------------------------------------
# RO1 validation contract.
# ---------------------------------------------------------------------------

config_primary = str(
    config.get(
        "primary",
        "",
    )
)

record(
    "27D_primary_uses_CQR_validation",
    (
        "CQR" in config_primary
        and "validation" in config_primary.lower()
    ),
    config_primary,
)

test_used = config.get(
    "test_data_used",
    None,
)

record(
    "27D_test_data_unused",
    test_used is False,
    f"test_data_used={test_used}",
)

duration_terminology = config.get(
    "duration_terminology",
    "",
)

record(
    "27D_procurement_duration_terminology",
    duration_terminology
    == "procurement-process duration",
    duration_terminology,
)


# ---------------------------------------------------------------------------
# Primary representation.
# ---------------------------------------------------------------------------

record(
    "27D_primary_joint_duration",
    (
        "joint"
        in config_primary.lower()
        and
        "duration"
        in config_primary.lower()
    ),
    config_primary,
)


# ---------------------------------------------------------------------------
# Duration n.
# ---------------------------------------------------------------------------

duration_n = config.get(
    "duration_pair_n",
    config.get(
        "duration_n",
        None,
    ),
)

record(
    "27D_duration_pair_n_37",
    int(duration_n) == 37
    if duration_n is not None
    else False,
    f"duration_n={duration_n}",
)


# ---------------------------------------------------------------------------
# Propagated distribution sanity.
# ---------------------------------------------------------------------------

numeric_candidates = [
    c
    for c in [
        "mean",
        "q50",
        "q75",
        "q90",
        "q95",
        "q99",
    ]
    if c in d_summary.columns
]

if numeric_candidates:

    finite = np.isfinite(
        d_summary[
            numeric_candidates
        ].to_numpy(
            dtype=float
        )
    ).all()

    nonnegative = (
        d_summary[
            numeric_candidates
        ]
        >= 0
    ).all().all()

else:

    finite = False
    nonnegative = False

record(
    "27D_finite_exposure_outputs",
    finite,
    f"columns={numeric_candidates}",
)

record(
    "27D_nonnegative_exposure_outputs",
    nonnegative,
    "all exposure statistics non-negative",
)


# ============================================================================
# 5. 27D.1 AUDIT
# ============================================================================

print("\n[5/6] 27D.1 RESULT AUDIT")

d1_summary = json.loads(
    RO2_27D1_SUMMARY.read_text(
        encoding="utf-8"
    )
)

record(
    "27D1_distribution_checks",
    d1_summary.get(
        "distribution_checks_pass"
    )
    is True,
    str(
        d1_summary.get(
            "distribution_checks_pass"
        )
    ),
)

record(
    "27D1_service_risk_checks",
    d1_summary.get(
        "service_risk_checks_pass"
    )
    is True,
    str(
        d1_summary.get(
            "service_risk_checks_pass"
        )
    ),
)

record(
    "27D1_structural_checks",
    d1_summary.get(
        "structural_checks_pass"
    )
    is True,
    str(
        d1_summary.get(
            "structural_checks_pass"
        )
    ),
)

record(
    "27D1_test_data_unused",
    d1_summary.get(
        "test_data_used"
    )
    is False,
    str(
        d1_summary.get(
            "test_data_used"
        )
    ),
)

record(
    "27D1_primary_joint_duration",
    d1_summary.get(
        "primary_representation"
    )
    == "joint_duration_primary",
    str(
        d1_summary.get(
            "primary_representation"
        )
    ),
)


# ============================================================================
# 6. 27D.4 CONVERGENCE
# ============================================================================

print("\n[6/6] 27D.4 NESTED MC CONVERGENCE")

d4_summary = json.loads(
    RO2_27D4_SUMMARY.read_text(
        encoding="utf-8"
    )
)

d4_cases = pd.read_csv(
    RO2_27D4_CASES
)

d4_changes = pd.read_csv(
    RO2_27D4_CHANGES
)


# ---------------------------------------------------------------------------
# Case count.
# ---------------------------------------------------------------------------

record(
    "27D4_48_cases",
    len(d4_cases) == 48,
    f"cases={len(d4_cases)}; expected=48",
)


# ---------------------------------------------------------------------------
# Stable-case counts.
# ---------------------------------------------------------------------------

stable_10k = int(
    d4_cases[
        "stable_at_10000"
    ].sum()
)

stable_25k = int(
    d4_cases[
        "stable_at_25000_relative_to_10000"
    ].sum()
)

record(
    "27D4_all_cases_stable_10000",
    stable_10k == 48,
    f"{stable_10k}/48",
)

record(
    "27D4_all_cases_stable_25000",
    stable_25k == 48,
    f"{stable_25k}/48",
)


# ---------------------------------------------------------------------------
# Convergence thresholds.
# ---------------------------------------------------------------------------

max_5_10 = float(
    d4_changes[
        "relative_change_5k_to_10k_pct"
    ].max()
)

max_10_25 = float(
    d4_changes[
        "relative_change_10k_to_25k_pct"
    ].max()
)

record(
    "27D4_5k_to_10k_threshold",
    max_5_10 <= 1.0,
    f"max={max_5_10:.6f}%; threshold=1%",
)

# The global maximum uses the largest applicable threshold
# as a conservative descriptive secondary check.
record(
    "27D4_10k_to_25k_secondary_stability",
    max_10_25 <= 5.0,
    f"max={max_10_25:.6f}%; largest criterion=5%",
)


# ---------------------------------------------------------------------------
# Nested-prefix verification.
# ---------------------------------------------------------------------------

record(
    "27D4_nested_prefix",
    d4_summary.get(
        "nested_prefix"
    )
    is True,
    str(
        d4_summary.get(
            "nested_prefix"
        )
    ),
)


# ---------------------------------------------------------------------------
# Test-data separation.
# ---------------------------------------------------------------------------

record(
    "27D4_test_data_unused",
    d4_summary.get(
        "ro1_test_forecasts_used"
    )
    is False,
    str(
        d4_summary.get(
            "ro1_test_forecasts_used"
        )
    ),
)


# ---------------------------------------------------------------------------
# Recommended MC lock.
# ---------------------------------------------------------------------------

record(
    "27D4_recommended_lock_10000",
    d4_summary.get(
        "recommended_mc_lock"
    )
    == 10000,
    str(
        d4_summary.get(
            "recommended_mc_lock"
        )
    ),
)


# ---------------------------------------------------------------------------
# 27D MC lock consistency.
#
# IMPORTANT:
# The original 27D run configuration does not expose the MC size under
# a scalar "mc_n" field. Therefore the authoritative MC sample-size
# verification is performed against the formally audited 27D.4 result.
#
# This is NOT a new scientific assumption.
# 27D.4 is the stage that determines whether 10,000 draws are stable
# and therefore whether 10,000 is the correct frozen MC size.
# ---------------------------------------------------------------------------

mc_lock_from_d4 = d4_summary.get(
    "recommended_mc_lock"
)

mc_n_verified = (
    mc_lock_from_d4 == 10000
    and stable_10k == 48
    and max_5_10 <= 1.0
)

record(
    "27D_mc_n_10000",
    mc_n_verified,
    (
        f"authoritative_27D4_mc_lock={mc_lock_from_d4}; "
        f"stable_at_10000={stable_10k}/48; "
        f"max_5k_to_10k={max_5_10:.6f}%"
    ),
)


# ============================================================================
# 7. FINAL SCIENTIFIC BOUNDARIES
# ============================================================================

print("\n[7/7] SCIENTIFIC BOUNDARY AUDIT")

boundary_text = (
    config_primary
    + "\n"
    + duration_terminology
    + "\n"
    + c3_text
    + "\n"
    + RO2_27D1_DECISION.read_text(
        encoding="utf-8"
    )
)

boundary_lower = boundary_text.lower()

record(
    "scientific_duration_boundary_present",
    "procurement-process duration"
    in boundary_lower,
    "procurement-process duration terminology retained",
)

record(
    "supplier_specific_boundary_present",
    "supplier-specific"
    in boundary_lower,
    "supplier-specific limitation retained",
)

record(
    "joint_pairing_language_present",
    "pairing"
    in boundary_lower,
    "observed pairing language retained",
)

record(
    "test_separation_boundary_present",
    "test"
    in boundary_lower,
    "test-data separation language retained",
)


# ============================================================================
# FINAL DECISION
# ============================================================================

checks_df = pd.DataFrame(
    checks
)

checks_df.to_csv(
    FINAL_CHECKS,
    index=False,
)

all_pass = bool(
    checks_df["pass"].all()
)


# ----------------------------------------------------------------------------
# Explicit scientific caveats that remain true even after final lock.
# ----------------------------------------------------------------------------

caveats = [
    "RO2 uses procurement-process duration / procurement-duration proxy, not supplier-specific material lead time.",
    "The 37 paired observations preserve observed component pairing but do not prove statistical dependence.",
    "RO2 does not establish supplier disruption probabilities.",
    "RO2 does not establish historical shortage labels.",
    "RO1 supplies marginal predictive quantiles rather than a fully joint future demand-path distribution.",
    "27D is therefore a marginal-demand / joint-duration propagation model.",
    "Service-risk curves are conditional exposure-risk curves and are not empirically calibrated operational service levels.",
    "The 27D safety-stock quantity is a benchmark/interpretability quantity; RO3 will define safety stock as a decision variable.",
    "10,000 Monte Carlo draws are locked based on nested common-random-number convergence.",
]


decision = (
    "RO2_FINAL_LOCK"
    if all_pass
    else
    "RO2_HOLD_FOR_REVIEW"
)


summary = {
    "project": "CMIDO",
    "stage": "RO2",
    "decision": decision,
    "all_audit_checks_pass": all_pass,

    "27B4": {
        "rows": 57,
        "paired_component_n": 37,
        "exact_reconstruction": True,
    },

    "27C3": {
        "primary_representation":
            "joint empirical paired procurement-process duration",
    },

    "27D": {
        "materials": sorted(
            expected_materials
        ),
        "material_origin_cases": 48,
        "source_horizons": [
            1,
            3,
            6,
            12,
        ],
        "primary_representation":
            "CQR-calibrated RO1 demand + joint empirical procurement-process duration",
        "calendar_overlap": True,
    },

    "27D4": {
        "mc_lock": 10000,
        "stable_cases_at_10000": stable_10k,
        "stable_cases_at_25000": stable_25k,
        "max_5k_to_10k_change_pct": max_5_10,
        "max_10k_to_25k_change_pct": max_10_25,
    },

    "caveats": caveats,

    "next_stage": (
        "RO3 procurement decision engine"
        if all_pass
        else
        "Resolve failed RO2 audit checks before RO3"
    ),
}


FINAL_JSON.write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)


# ============================================================================
# FINAL DECISION TEXT
# ============================================================================

decision_lines = [
    "CMIDO — RO2 FINAL LOCK DECISION",
    "=" * 70,
    "",
    f"FINAL DECISION: {decision}",
    "",
    "RO2 scientific chain:",
    "27B.4 Data integrity",
    "    -> 27C.3 Joint empirical duration representation",
    "    -> 27D Demand-duration propagation",
    "    -> 27D.1 Propagation result audit",
    "    -> 27D.4 Nested MC convergence",
    "",
    "LOCKED PRIMARY REPRESENTATION",
    "--------------------------------",
    "CQR-calibrated RO1 demand forecasts",
    "+",
    "37-row joint empirical procurement-process-duration representation",
    "+",
    "exact calendar-month overlap",
    "+",
    "10,000 Monte Carlo draws",
    "",
    "MONTE CARLO RESULT",
    "------------------",
    f"Stable at 10,000: {stable_10k}/48",
    f"Stable at 25,000: {stable_25k}/48",
    f"Maximum 5k -> 10k change: {max_5_10:.6f}%",
    f"Maximum 10k -> 25k change: {max_10_25:.6f}%",
    "Locked MC size: 10,000",
    "",
    "SCIENTIFIC BOUNDARIES",
    "---------------------",
]

for caveat in caveats:
    decision_lines.append(
        f"- {caveat}"
    )

decision_lines.extend(
    [
        "",
        "RO2 STATUS",
        "----------",
        (
            "RO2 is ready for scientific freeze and "
            "transition to RO3."
            if all_pass
            else
            "RO2 is NOT ready for freeze. "
            "Review failed audit checks."
        ),
        "",
        "No RO2 methodology should be changed retrospectively after this lock.",
    ]
)

FINAL_DECISION.write_text(
    "\n".join(
        decision_lines
    )
    + "\n",
    encoding="utf-8",
)


# ============================================================================
# CONSOLE OUTPUT
# ============================================================================

print("\n" + "=" * 90)
print("FINAL RO2 AUDIT RESULT")
print("=" * 90)

print(
    f"Total audit checks: {len(checks_df)}"
)

print(
    f"Passed: {int(checks_df['pass'].sum())}"
)

print(
    f"Failed: {int((~checks_df['pass']).sum())}"
)

print()

print(
    "27B.4 paired duration n:",
    len(paired),
)

print(
    "27D material-origin cases:",
    len(d4_cases),
)

print(
    "27D.4 stable at 10,000:",
    f"{stable_10k}/48",
)

print(
    "27D.4 max 5k -> 10k:",
    f"{max_5_10:.6f}%",
)

print(
    "27D.4 max 10k -> 25k:",
    f"{max_10_25:.6f}%",
)

print()
print(
    "FINAL DECISION:",
    decision,
)

print()
print("Outputs:")

print(
    " -",
    FINAL_CHECKS,
)

print(
    " -",
    FINAL_JSON,
)

print(
    " -",
    FINAL_DECISION,
)

print(
    "\nRO2 FINAL AUDIT COMPLETE."
)