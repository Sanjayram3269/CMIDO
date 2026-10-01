# CMIDO — Paper-Facing Evidence Package (8O)

**Status:** IMPLEMENTED / AWAITING LOCAL GATE  
**Purpose:** Bind the verified technical evidence to the provenance, assumptions, limitations, validity constraints, experiment identities, and publication-facing source map required for the final manuscript.

## 1. Scope

8O does not create new empirical results. It packages the existing RO1, RO2, RO3, 8M, and 8N evidence so that manuscript claims can be written against explicit, auditable sources.

## 2. Provenance classes

| Class | Meaning in CMIDO |
|---|---|
| OBS | Directly observed/raw dataset quantity |
| DER | Deterministically derived from observed or frozen inputs |
| EST | Estimated/model-generated quantity |
| SCN | Scenario-generated quantity used for simulation/stress analysis |

The distinction must be retained in manuscript tables, figures, dashboard views, and supplementary material.

## 3. Core source map

| Domain | Authoritative source | Evidence role |
|---|---|---|
| RO1 | `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv` | Frozen calibrated forecast representation |
| RO2 data | `results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv` | Admissible duration/process representation |
| RO2 propagation | `results/RO2/propagation/` and audit/convergence families | Joint uncertainty propagation |
| RO3 scenarios | `results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv` | Primary stochastic evaluation scenarios |
| RO3 optimization | `results/RO3/multi_origin/` | Multi-origin procurement decisions/Pareto evidence |
| RO3 baseline/ablation | `results/RO3/ablation/final_comparison/` | Controlled O1/O2/O3/O4 evidence |
| RO3 stress | `results/RO3/ablation/RO3_7_stress/` | Declared stress conditions |
| RO3 robustness | `results/RO3/ablation/RO3_8_robustness/` | Holding-rate sensitivity/robustness |
| 8M gate | `results/RO3/ablation/8M_gate/CMIDO_8M_GATE_MANIFEST.json` | Verified controlled-evidence gate |
| 8N gate | `results/8N_integrated_evidence/CMIDO_8N_INTEGRATED_EVIDENCE_MANIFEST.json` | Verified cross-domain source gate |

## 4. Experiment identity

### RO3.6 controlled ablation

Four arms:

- O1 — deterministic q50 + heuristic
- O2 — deterministic q50 + formal optimization
- O3 — probabilistic q90 + heuristic
- O4 — probabilistic + formal uncertainty-aware optimization

Common design:

- 11 locked forecast origins
- 4 common materials
- 12 realized months per origin/material
- common realized demand and price paths
- origin-level inferential unit
- paired bootstrap uncertainty
- BH multiplicity correction

### Interpretation boundary

The controlled experiment is an attribution study. It may establish empirical differences among the predefined configurations, but it does not by itself establish broad causal or population-level superiority beyond the declared evaluation design.

## 5. Assumptions requiring explicit manuscript disclosure

1. The selected RO1 predictive representation is treated as the frozen input to downstream decision experiments.
2. The RO2 admissible duration representation is used according to its documented semantic role; it must not be relabeled as supplier-specific historical lead time unless independently supported.
3. Scenario-generated uncertainty is distinguished from direct observation.
4. The RO3.6 comparison uses paired forecast origins rather than treating monthly observations within an origin as independent replicates.
5. O1/O3 are intentionally transparent heuristic benchmarks, not state-of-the-art heuristic optimizers.
6. O2 is a deterministic ablation of the formal optimization pipeline rather than an independently developed optimization method.
7. O4 realized-policy evaluation and O4 stochastic optimization objectives are distinct analytical layers and must not be conflated.
8. Any final manuscript aggregation must preserve the exact evaluation population and frozen controller/configuration.

## 6. Threats to validity

### Construct validity
Forecast uncertainty, process duration, shortage, service, and resilience are represented through operational variables and model constructs. Their correspondence to real-world procurement phenomena must be documented rather than assumed.

### Internal validity
Temporal leakage, outcome-based parameter tuning, inconsistent evaluation populations, and post-hoc origin removal would undermine attribution. The frozen controller and common-realization gates are designed to constrain these risks.

### Statistical validity
The 11 origins are repeated temporal cases. Small-sample paired inference should therefore be reported with uncertainty intervals and multiple-comparison control, without overstating population-level generalization.

### External validity
The empirical data environment is construction-material activity in Singapore and the construction logistics benchmark used by the project. Results should not be presented as automatically representative of all geographies, contractors, suppliers, materials, or market regimes.

### Implementation validity
Artifact-producing scripts should remain executable from a clean checkout. Hard-coded local filesystem assumptions are considered reproducibility defects and should be removed before 8R freeze.

## 7. Limitations register

| Limitation | Affected area | Manuscript treatment |
|---|---|---|
| Data geography and domain | RO1/RO2/RO3 | State evaluation environment and avoid universal claims |
| Proxy/semantic limitations in process-duration data | RO2 | Preserve documented construct semantics |
| Finite number of forecast origins | RO1/RO3 | Report temporal evaluation population explicitly |
| Benchmark/controller design | RO3.6 | Describe O1/O2/O3 as controlled attribution arms |
| Scenario assumptions | RO2/RO3 | Separate SCN evidence from OBS evidence |
| Computational budget | RO3 | Report scenario size, solver/tolerance and sensitivity runs |
| Final publication artifacts not yet frozen | 8Q | No final manuscript number until regeneration |

## 8. Claim register

| Claim ID | Supported evidence | Claim boundary | Status |
|---|---|---|---|
| C1 | RO1 forecast source + calibration analyses | State measured forecasting/calibration outcomes for the declared evaluation design | READY |
| C2 | RO2 admissible view + propagation audits | State observed propagation effects under the documented modelling representation | READY |
| C3 | RO3 multi-origin + Pareto outputs | State empirical optimization outcomes for the frozen RO3 formulation | READY |
| C4 | 8M paired O1/O2/O3/O4 evidence | State observed incremental contrasts across the locked 11-origin design | VERIFIED |
| C5 | RO3.7/RO3.8 stress/robustness | State variation under declared stress/sensitivity settings | READY |
| C6 | RO1 + RO2 + RO3 + 8N | State whether the integrated pipeline is supported by the combined evidence, with explicit scope | READY-AFTER-8Q |

## 9. Publication source policy

Every final table or figure must carry an internal source tuple:

```text
artifact_id
→ source result path(s)
→ experiment/configuration
→ dataset/provenance
→ generation script
→ generation commit
→ rounding/unit convention
```

8O establishes the semantic package. 8Q will generate and numerically reconcile the publication artifacts.

## 10. Reproducibility policy

Before final freeze:

- no result-producing script may depend on a developer-specific absolute path;
- configuration values must be explicit;
- seeds must be recorded;
- result paths must be stable;
- artifact hashes should be recorded where practical;
- final regression and E2E commands must be documented.

## 11. 8O gate

The 8O gate checks:

1. the 8N integrated evidence package exists;
2. the 8M gate manifest exists and is green;
3. the principal RO1/RO2/RO3 source artifacts exist;
4. the assumptions/limitations/claim registers exist in this package;
5. no required source mapping is left as a placeholder for the currently defined scope.

The stage remains unfrozen until the local gate is executed successfully.

## 12. Downstream sequence

```text
8M  ✅ verified
8N  ✅ verified
8O  → paper-facing evidence package
8P  → real-data dashboard E2E
8Q  → tables + figures
8R  → reproducibility/freeze
Phase 9 → manuscript + supplementary package
```
