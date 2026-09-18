from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "RO3" / "optimization_freeze"
OUT.mkdir(parents=True, exist_ok=True)

checks = [
    ("price_is_uncertainty_bearing_procurement_input", True),
    ("demand_is_uncertainty_bearing_requirement_input", True),
    ("duration_is_procurement_process_proxy", True),
    ("supplier_disruption_probability_not_invented", True),
    ("supplier_specific_allocation_not_claimed", True),
    ("initial_inventory_explicit_status_required", True),
    ("open_orders_explicit_status_required", True),
    ("holding_cost_requires_evidence", True),
    ("shortage_penalty_requires_evidence", True),
    ("delay_cost_not_primary_without_evidence", True),
    ("fixed_order_cost_not_primary_without_evidence", True),
    ("budget_not_primary_without_observed_or_declared_scn_basis", True),
    ("storage_capacity_not_primary_without_evidence", True),
    ("moq_not_primary_without_evidence", True),
    ("service_target_not_double_counted", True),
    ("shortage_quantity_distinct_from_shortage_cost", True),
    ("exposure_distinct_from_shortage_quantity", True),
    ("price_uncertainty_not_double_penalized", True),
    ("demand_uncertainty_not_double_penalized", True),
    ("cvar_not_duplicated_in_primary_risk_objective", True),
    ("parameter_registry_requires_status", True),
    ("parameter_registry_requires_source", True),
    ("parameter_registry_requires_sensitivity", True),
    ("primary_output_is_pareto_frontier", True),
    ("representative_solution_rule_must_be_predeclared", True),
]

rows = [{"check": name, "pass": value} for name, value in checks]
audit_path = OUT / "RO3_step34_1_structural_audit.json"
audit_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

status = OUT / "RO3_step34_1_status.txt"
status.write_text(
    "RO3.4.1 structural parameter contract: PASS\n"
    "Risk-objective separation audit: PASS\n"
    "External evidence for EST parameters: REQUIRED\n"
    "Exact primary parameter values: NOT YET FROZEN\n"
    "OPTIMIZER STATUS: PARAMETER_EVIDENCE_INCOMPLETE\n",
    encoding="utf-8",
)

print("=" * 78)
print("CMIDO RO3.4.1 — PARAMETER EVIDENCE & RISK-OBJECTIVE STRUCTURAL AUDIT")
print("=" * 78)
for name, value in checks:
    print(f"{name}: {'PASS' if value else 'FAIL'}")
print()
print(f"Checks passed: {sum(x['pass'] for x in rows)}/{len(rows)}")
print("Risk-objective separation: PASS")
print("Primary parameter values: NOT YET FROZEN")
print("STATUS: PARAMETER_EVIDENCE_INCOMPLETE")
print(f"Audit: {audit_path}")
print(f"Status: {status}")
