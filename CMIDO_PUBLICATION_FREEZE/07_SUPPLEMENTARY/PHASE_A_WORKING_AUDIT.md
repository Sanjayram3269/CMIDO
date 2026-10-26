# CMIDO — Final Research Closure: Working Audit and Work Queue

**Purpose:** Record the pre-packaging inventory and dependency-ordered work queue before
regenerating or committing any research artifact.

**Scope note:** This document is Phase A of the requested final research-closure workflow. It is
a working audit, not a completion claim. It does not change scientific results, thresholds, or the
frozen dashboard implementation.

## 1. Repository state (verified this session)

- Repository root: `D:/CMIDO`
- Branch: `main`
- HEAD: `c100b477ed8b79e8cdf1384ecfddd80b136adb78`
- `origin/main`: same SHA
- `HEAD == origin/main`: yes (after a fresh fetch this session)
- Tracked working tree at start of this session: clean
- Pre-existing untracked artifacts preserved: yes (15 `??` entries, including `results/8N`–`9B`,
  `results/RO3/ablation/8M_gate/`, `9A_repository_inventory.csv`, scratch fixtures, and `package-lock.json`)

Starting freeze checkpoint: `c100b477`.

## 2. Existing manuscript and literature-review materials

- No final journal manuscript file exists yet in `docs/` or anywhere else in the repository.
- The closest existing manuscript-facing sources are the 8-series documentation:
  - `docs/CMIDO_8O_PAPER_EVIDENCE_PACKAGE.md` — paper-facing evidence package, provenance, assumptions,
    limitations, threats, claim register, publication-source policy, reproducibility policy.
  - `docs/CMIDO_EVIDENCE_CONCORDANCE.md` — claim/table/figure scaffold with most cells still `TBD`/`OPEN`.
- Existing specification and audit documents are available and should inform wording:
  - `docs/CMIDO_MASTER_COMPLETION_AUDIT.md`
  - `docs/CMIDO_8N_INTEGRATED_EVIDENCE.md`
  - `docs/CMIDO_8S_NUMERICAL_RECONCILIATION.md`
  - `docs/CMIDO_8R_PUBLICATION_FIGURE_RECONCILIATION.md`
  - `docs/CMIDO_RO3_3_Scenario_Convergence_Specification_v1.0.md`
  - `docs/CMIDO_RO3_6_Controller_Freeze_Specification_v1.0.md`
  - `docs/CMIDO_RO2_27D_Propagation_Specification_v1.0.md`
  - `docs/RO1_26C3A_Probabilistic_Calibration_Specification_v1.0.md`
  - `docs/CMIDO_RO3_5_Multi_O...cification_v1.0.md` (working spec for RO3.5 controller/selections)
  - `docs/CMIDO_10A_DASHBOARD_DATA_CONTRACT.md`
- No `.docx` manuscript exists in the repo.

Conclusion: **no editable manuscript draft currently exists that should be preserved.** A manuscript
must be created from the frozen evidence and existing documentation, not from a prior draft.

## 3. Existing figures and tables

### Publication figures (on disk)

`results/8R_publication_figures/` contains 6 PNGs:

- `F1_RO1_calibration_coverage.png`
- `F2_RO2_tail_comparison.png`
- `F3_RO2_propagation_tail.png`
- `F4_RO2_joint_independent_sensitivity.png`
- `F5_RO3_controller_descriptives.png`
- `F6_RO3_ablation_effects.png`

All 6 exist and are non-empty on this disk. No figure editorial tool is present in the repo;
the practical deliverable format is the PNG plus the 8R concordance.

### Publication tables (on disk)

`results/8Q_publication_artifacts/` contains 9 tables:

- `T1_RO1_validation_metrics.csv`
- `T2_RO2_joint_propagation_summary.csv`
- `T2_RO2_tail_comparison.csv`
- `T3_RO2_propagation_summary.csv`
- `T3_RO2_service_risk_curve.csv`
- `T3_RO2_joint_independent_sensitivity.csv`
- `T5_RO3_baseline_comparison.csv`
- `T5_T6_controller_descriptives.csv`
- `T6_RO3_ablation.csv`

### Other large table collections (do not conflate with publication tables)

- `tables/` contains 24 files, all `RO1_*` exploratory/descriptive artifacts. They are **not** the
  8Q publication table set. The publication tables live in `results/8Q_publication_artifacts/`.
- `figures/` contains 27 time-series/EDA PNGs (ACF/seasonality/levels). These are upstream figures,
  not the 8R publication figure set.

## 4. Source artifacts inventoried

### RO1

- `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv` — exists, non-empty.
- `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv` — exists, non-empty,
  36 data rows, 24 columns.

### RO2

- `results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv` — exists, non-empty.
- `results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv` — exists, 1 row, 21 columns.
- `results/RO2/distribution/RO2_step27c3_tail_comparison.csv` — exists, 15 rows, 5 columns.
- `results/RO2/propagation/RO2_step27d_propagation_summary.csv` — exists, 96 rows, 14 columns.
- `results/RO2/propagation/RO2_step27d_service_risk_curve.csv` — exists, 240 rows, 6 columns.
- `results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv` — exists, 240 rows, 7 columns.
- `results/RO2/propagation_convergence_nested/RO2_step27d4_summary.json` — exists, non-empty.

### RO3

- `results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv` — exists, non-empty.
- `results/RO3/scenario_convergence/RO3_step33_summary.json` — exists, non-empty.
- `results/RO3/multi_origin/RO3_step35_*_N2500.csv` — decision/pareto/origin/audit artifacts exist.
- `results/RO3/ablation/final_comparison/` — 15 source CSVs for the controlled ablation/8M gate.
- `results/RO3/ablation/8M_gate/` — 8M manifest + audit.
- `results/RO3/ablation/RO3_7_stress/` — stress artifacts exist.
- `results/RO3/ablation/RO3_8_robustness/` — holding-rate sensitivity artifacts exist.

## 5. Evidence package status (regenerated this session)

The following local gates were executed this session and recorded with exit status:

- 8M: PASS (20/20)
- 8N: PASS (13/13)
- 8O: PASS (17/17)
- 8P: PASS (3/3 pytest)
- 8Q: PASS (31/31)
- 8R: PASS (28/28)
- 8S: PASS (81/81)

Full construction + optimization regression: 1059 passed, exit 0.

So the 8M/8N/8O/8P/8Q/8R/8S publication artifact chain is internally consistent on the current disk,
using the declared manifest checks and value/schema reconciliation checks. 8S is the stronger
table-to-source + figure-to-source reconciliation; it passes.

## 6. What exists, what is stale, what can be regenerated, what needs more evidence

### Exists and current

- Frozen 8Q/8R/8S artifact chain and manifests.
- Frozen 8M/8N/8O/8P evidence artifacts and manifests.
- Source RO1/RO2/RO3 result files referenced by those manifests.
- Dashboard roadmap frozen at Phase 10A.15.
- Concordance scaffolding docs, including `CMIDO_EVIDENCE_CONCORDANCE.md`.
- `CMIDO_8O_PAPER_EVIDENCE_PACKAGE.md` as a usable manuscript evidence backbone.

### Stale only in the weak sense

- `docs/CMIDO_EVIDENCE_CONCORDANCE.md` still has `TBD`/`OPEN` labels for many claim/table/figure slots.
  Those labels are accurate today: they reflect that the final manuscript claim-to-evidence mapping has
  not been written out. The underlying numeric artifacts are current.
- No final manuscript text exists to reconcile against.

### Can be regenerated

- 8Q tables can be regenerated from their declared source CSVs via
  `src/optimization/cmido_8q_publication_artifacts.py`.
- 8R figures can be regenerated from the 8Q tables via
  `src/optimization/cmido_8r_publication_figures.py`.
- 8S reconciliation can be rerun after 8Q/8R.
- The final package manifest can be regenerated from the repo + result manifests.

### Needs more evidence or remains conditional

- A complete editable manuscript does not exist yet.
- No rendered review PDF exists yet. This environment does not currently expose a confirmed
  manuscript-to-PDF toolchain, so the review copy may be delivered as markdown plus the figures/tables
  until a PDF path is established.
- The five decision-level registration gaps and two registered-but-unadapted artifacts remain open
  research-side items.
- RO3 500→1,000 convergence failure remains open; the next required evaluation per the convergence spec
  is 2,500, then 5,000. This is not resolved here.
- RO3 stress/robustness results exist, but the concordance's T7 slot and the manuscript's stress/robustness
  statements still need to be written and checked against `RO3_step37_*` and `RO3_step38_*`.
- No new results were generated for the additional master-spec stress scenarios; those remain unrun.

## 7. Work queue (dependency order)

1. **Establish the source-of-truth numeric backbone.** Use 8Q + 8R + 8S as the frozen tables/figures and
   their manifest-based reconciliation. Do not hand-copy numbers into prose.
2. **Write the editable manuscript** from the existing 8O package + concordance scaffold + source result
   files. Build every numerical claim from `results/8Q_publication_artifacts/` and the underlying source
   CSVs. Keep OBS/DER/EST/SCN explicit.
3. **Complete the evidence concordance** so that every manuscript-bound claim/table/figure is either filled
   from frozen artifacts or explicitly marked unavailable with the reason and owner.
4. **Produce the package folder** `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/` with README, manuscript,
   figures, tables, supplementary evidence, audits, reproducibility notes, and the professor-review message.
5. **Run the final verification** against the frozen artifacts: tables present, figures present,
   manuscript claims traceable, package files non-empty, git state clean/synced.
6. **Commit and push only intended files** for this research-closure work. Keep the dashboard-freeze commit
   untouched.
7. **Do not claim journal-submission readiness** unless the evidence and reproducibility gates support it.

Immediate next action: write the editable manuscript source under the package folder, then complete the
concordance from the frozen artifacts before any “review draft” label is applied.

<!-- Internal todo sync -->
<!-- Phase A complete; Phases B and C re-executed this session and recorded here. -->
<!-- Next: Phase D manuscript writing. -->
