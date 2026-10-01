# CMIDO — Integrated Evidence Package (8N)

**Status:** IMPLEMENTED / AWAITING LOCAL GATE  
**Purpose:** Consolidate the existing RO1 → RO2 → RO3 evidence into one machine-readable, source-traceable research package without duplicating or manually re-entering scientific values.

## 1. Evidence chain

```text
RO1 forecasting
   ↓
validated predictive uncertainty
   ↓
RO2 joint propagation
   ↓
shortage / service-risk evidence
   ↓
RO3 procurement optimization
   ↓
baseline / ablation / stress evidence
   ↓
integrated decision-level evidence
```

Each evidence item records the research objective, dataset/provenance, experiment/result source, statistical support where available, and publication role.

## 2. Current source-of-truth inventory

### RO1
- Calibrated validation forecasts:
  `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv`
- Role: forecast point/distribution inputs consumed by downstream RO2/RO3 evidence.

### RO2
- Admissible modelling view:
  `results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv`
- Propagation result families:
  `results/RO2/propagation/`
  `results/RO2/propagation_audit/`
  `results/RO2/propagation_convergence/`
- Role: uncertainty propagation, duration/source semantics, shortage/service-risk evidence.

### RO3
- Primary scenario set:
  `results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv`
- Multi-origin optimization:
  `results/RO3/multi_origin/`
- Controlled baseline/ablation:
  `results/RO3/ablation/`
- RO3.6 final comparison:
  `results/RO3/ablation/final_comparison/`
- Stress/robustness:
  `results/RO3/ablation/RO3_7_stress/`
  `results/RO3/ablation/RO3_8_robustness/`

## 3. Integrated evidence registry

| Evidence ID | Objective | Evidence role | Primary source | Statistical support | Status |
|---|---|---|---|---|---|
| E-RO1-FORECAST | RO1 | Calibrated predictive forecast input | `RO1_step26c3_validation_forecasts.csv` | RO1 statistical/calibration artifacts | SOURCE-TRACEABLE |
| E-RO2-DURATION | RO2 | Admissible supply/process-duration modelling view | `RO2_step27b4_admissible_modelling_view.csv` | RO2 audit/propagation diagnostics | SOURCE-TRACEABLE |
| E-RO2-PROPAGATION | RO2 | Joint uncertainty propagation evidence | `results/RO2/propagation/` + audits | Propagation/convergence audits | SOURCE-TRACEABLE |
| E-RO3-OPTIMIZATION | RO3 | Multi-origin procurement decisions/Pareto evidence | `results/RO3/multi_origin/` | RO3 audit outputs | SOURCE-TRACEABLE |
| E-RO3-BASELINE | RO3 | Deterministic/probabilistic controlled baseline evidence | `results/RO3/ablation/final_comparison/` | RO3.6 paired analysis | VERIFIED-8M |
| E-RO3-STRESS | RO3 | Stress/robustness evidence | `results/RO3/ablation/RO3_7_stress/` + `RO3_8_robustness/` | Stress/robustness audits | SOURCE-TRACEABLE |
| E-INTEGRATED | RO1→RO2→RO3 | Forecast→uncertainty→risk→decision chain | Combined RO1/RO2/RO3 sources above | RO3.6 + RO2 diagnostics | SOURCE-TRACEABLE |

## 4. Claim register for 8N

These are evidence-backed *claim slots*. Final manuscript wording remains deliberately separate until Phase 9.

| Claim ID | Evidence basis | What can be stated after final audit | Status |
|---|---|---|---|
| C-RO1-001 | E-RO1-FORECAST | Report observed forecasting/calibration performance for the frozen RO1 evaluation design. | READY-FOR-AUDIT |
| C-RO2-001 | E-RO2-DURATION + E-RO2-PROPAGATION | Report how the frozen demand uncertainty and admissible duration representation propagate into shortage/service-risk outcomes. | READY-FOR-AUDIT |
| C-RO3-001 | E-RO3-OPTIMIZATION | Report RO3 procurement/Pareto outputs under the frozen optimization formulation. | READY-FOR-AUDIT |
| C-RO3-002 | E-RO3-BASELINE | Report incremental contrasts among O1/O2/O3/O4 without assuming that any configuration must dominate. | VERIFIED-8M |
| C-ROB-001 | E-RO3-STRESS | Report performance variation under the declared stress/robustness conditions. | READY-FOR-AUDIT |
| C-INT-001 | E-INTEGRATED | Report whether the complete forecast→uncertainty→risk→decision chain is empirically supported by the frozen evidence set. | READY-FOR-AUDIT |

## 5. Required publication mappings

The existing concordance scaffold remains the manuscript-facing register. 8N does not invent final table/figure numbers; it establishes authoritative source candidates that 8Q can bind to generated publication artifacts.

| Publication item | 8N source candidate | Next gate |
|---|---|---|
| T1 RO1 forecasting comparison | RO1 forecasting result tables | 8Q |
| T2 RO1 calibration/uncertainty | RO1 calibration artifacts | 8Q |
| T3 RO2 propagation | RO2 propagation result/audit files | 8Q |
| T4 RO2 sensitivity/stress | RO2 sensitivity/propagation diagnostics | 8Q |
| T5 RO3 baseline comparison | `RO3_step36_statistical_pairwise_comparisons.csv` | 8Q |
| T6 RO3 ablation | `RO3_step36_primary_ablation_results.csv` | 8Q |
| T7 RO3 stress/robustness | RO3.7/RO3.8 summary artifacts | 8Q |
| T8 integrated decision evidence | combined RO1/RO2/RO3 evidence | 8Q |
| F1–F7 | Same source-of-truth rule | 8Q |

## 6. 8N integrity rules

1. Source paths are references to frozen result artifacts, not copied numeric values.
2. Origin-level statistical inference remains the inferential unit for RO3.6.
3. Observed/derived/estimated/scenario provenance must remain explicit.
4. A manuscript statement may not outrun the evidence status of its source.
5. No result is promoted to a final paper number until 8Q regeneration and reconciliation.
6. Dashboard values must ultimately consume the same frozen sources.

## 7. 8N gate

The stage is locally verified by `src/optimization/cmido_8n_integrated_evidence_gate.py`.

Expected gate outcome:

```text
STATUS: PASS
```

The gate verifies that the key RO1/RO2/RO3 source artifacts exist, the 8M evidence package is green, and the integrated registry contains the required links.

## 8. Relationship to later stages

```text
8M  controlled baseline / ablation  → VERIFIED
8N  integrated evidence             → current gate
8O  paper-facing evidence package   → next
8P  real-data dashboard E2E
8Q  tables + figures
8R  reproducibility freeze
```
