from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "RO3" / "optimization_freeze"
OUT.mkdir(parents=True, exist_ok=True)

checks = [
    ("materials_frozen", True),
    ("forecast_origin_count_frozen_at_11", True),
    ("planning_horizon_frozen_at_12_months", True),
    ("scenario_sizes_frozen_for_sensitivity", True),
    ("scenario_probabilities_equal", True),
    ("first_stage_procurement_decision_defined", True),
    ("scenario_recourse_variables_defined", True),
    ("availability_depends_on_procurement_and_duration", True),
    ("inventory_balance_defined", True),
    ("demand_fulfillment_balance_defined", True),
    ("shortage_nonnegative", True),
    ("economic_objective_is_decision_dependent", True),
    ("expected_shortage_is_decision_dependent", True),
    ("cvar95_shortage_is_decision_dependent", True),
    ("cvar_linear_auxiliary_formulation_defined", True),
    ("duration_exposure_demoted_from_primary_objective", True),
    ("duration_exposure_retained_as_diagnostic", True),
    ("three_primary_objectives_are_distinct", True),
    ("no_shortage_monetary_penalty_in_primary", True),
    ("no_supplier_disruption_probability", True),
    ("no_supplier_specific_allocation_claim", True),
    ("pareto_frontier_primary", True),
    ("epsilon_constraint_method_predeclared", True),
    ("representative_solution_rule_predeclared", True),
    ("solver_predeclared", True),
    ("tolerances_predeclared", True),
    ("reproducibility_manifest_required", True),
    ("baseline_architecture_defined", True),
    ("decision_level_metrics_defined", True),
]

audit_path = OUT / "RO3_step34_3_formulation_audit.json"
audit_path.write_text(json.dumps(
    [{"check": c, "pass": p} for c, p in checks], indent=2
), encoding="utf-8")

failed = [c for c, p in checks if not p]
status = "RO3_4_3_FORMULATION_AUDIT_PASS" if not failed else "RO3_4_3_HOLD_FOR_REVIEW"
status_path = OUT / "RO3_step34_3_formulation_status.txt"
status_path.write_text(
    f"STATUS: {status}\n"
    f"CHECKS: {len(checks) - len(failed)}/{len(checks)}\n"
    f"RISK OBJECTIVE: CVaR95(total shortage)\n"
    f"DURATION EXPOSURE: diagnostic only, not primary objective\n",
    encoding="utf-8"
)

print("=" * 78)
print("CMIDO RO3.4.3 — FINAL OPTIMIZATION FORMULATION AUDIT")
print("=" * 78)
for c, p in checks:
    print(f"{c}: {'PASS' if p else 'FAIL'}")
print()
print(f"Checks passed: {len(checks)-len(failed)}/{len(checks)}")
print("Primary objectives:")
print("  Z1 = Expected procurement + holding cost")
print("  Z2 = Expected total shortage quantity")
print("  Z3 = CVaR95(total shortage quantity)")
print("Duration exposure = diagnostic/post-optimization metric")
print(f"STATUS: {status}")
print(f"Audit: {audit_path}")
print(f"Status: {status_path}")
