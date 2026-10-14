# CMIDO — Evidence Concordance

**Status:** finalized against frozen artifact state for the current review draft.
**Purpose:** Map every paper-level claim to its research objective, dataset, experiment, result, statistical
analysis, table/figure, and manuscript location.

This document is the authoritative claim-to-evidence register for the current manuscript draft. It was completed
from the frozen 8Q/8R/8S artifact chain and the existing evidence package docs. It is not a submission claim; open
research-side items are recorded in §11 and the package README.

---

## 1. Claim-to-evidence chain

```text
Paper claim
   ↓
Research objective (RO1 / RO2 / RO3)
   ↓
Dataset + provenance
   ↓
Experiment ID / configuration
   ↓
Seed / evaluation population
   ↓
Raw or derived result
   ↓
Statistical analysis
   ↓
Table / figure
   ↓
Manuscript section
```

---

## 2. Evidence rules

1. No numerical claim without a traceable result source.
2. No table number is maintained by hand when it can be generated from frozen results.
3. No figure is edited in a way that changes quantitative content.
4. Every uncertainty quantity retains provenance (`OBS`, `DER`, `EST`, `SCN`).
5. Baselines use the same evaluation population and clearly documented information set.
6. Ablation claims identify the component removed and the resulting change.
7. Stress-test claims identify the stress condition and its parameterization.
8. Statistical claims identify the test, population, effect size where applicable, and uncertainty interval where
   applicable.
9. Dashboard values must trace back to the same frozen result sources as the paper.
10. Final manuscript values must be regenerated after the final empirical freeze.

---

## 3. Research-objective map

| Objective | Core question | Required evidence |
|---|---|---|
| RO1 | Can probabilistic price/demand forecasts retain useful calibrated uncertainty? | Forecast metrics, calibration, coverage, sharpness, temporal/material stability, baseline comparisons |
| RO2 | What changes when demand uncertainty is propagated jointly with supply/process-duration uncertainty? | Propagation configuration, shortage/service distributions, sensitivity/stress tests, provenance audit |
| RO3 | Does uncertainty-aware information improve procurement decisions? | Baselines, optimization/Pareto outputs, ablations, stress tests, decision-level metrics |

---

## 4. Master claim register

All claims below are bound to the frozen publication artifact chain: 8Q tables, 8R figures, 8S reconciliation,
and the 8M/8N/8O/8P evidence package manifests. Claims are drafted for the current review draft; they are not
framed as universal superiority.

| Claim ID | Draft claim | RO | Dataset | Experiment | Result source | Statistical evidence | Table | Figure | Manuscript section | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| C-RO1-001 | Retaining predictive uncertainty produces calibrated forecast outputs for the frozen RO1 evaluation design | RO1 | OBS price/demand (Singapore activity) | RO1 rolling-origin backtesting | `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv` → T1 | per-horizon coverage/width/Winkler + prequential metrics | T1 | F1 | §5, §9.1 | DONE-for-draft |
| C-RO1-002 | Point accuracy and uncertainty quality are reported separately; no model is claimed universally best | RO1 | OBS price/demand | RO1 rolling-origin backtesting | T1 + `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv` | calibration/coverage reporting discipline | T1 | F1 | §5, §9.1, §10 | DONE-for-draft |
| C-RO2-001 | Joint propagation changes shortage/service-risk estimates under the documented admissible representation | RO2 | OBS + EST/SCN duration, RO1 quantiles | RO2 diffusion/aggregation over common scenarios | `results/RO2/propagation/RO2_step27d_propagation_summary.csv` → T3, `results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv` → T2, `results/RO2/propagation/RO2_step27d_service_risk_curve.csv` → T3 | propagation summary + service-risk curve | T2, T3 | F2, F3 | §6, §9.2 | DONE-for-draft |
| C-RO2-002 | Conclusions are sensitive to the joint/independent propagation assumption | RO2 | OBS + EST/SCN duration, RO1 quantiles | RO2 sensitivity analysis | `results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv` → T3 | joint/independent sensitivity | T3 | F4 | §6, §9.2 | DONE-for-draft |
| C-RO3-001 | RO3 optimization produces cost/shortage/service trade-offs under the frozen formulation | RO3 | OBS + SCN scenario, RO1/RO2 inputs | RO3 multi-origin N=2500 optimization | `results/RO3/multi_origin/RO3_step35_*_N2500.csv`, `results/RO3/ablation/final_comparison/RO3_step36_controller_descriptive_statistics.csv` → T5_T6 | controller descriptives, multi-origin Pareto summary | T5_T6 | F5 | §7, §9.3 | DONE-for-draft |
| C-RO3-002 | Controlled contrasts show measurable differences among O1/O2/O3/O4 under the declared design | RO3 | OBS + SCN scenario, common realizations | RO3.6 11-origin paired ablation | `results/RO3/ablation/final_comparison/RO3_step36_statistical_pairwise_comparisons.csv` → T5, `results/RO3/ablation/final_comparison/RO3_step36_primary_ablation_results.csv` → T6 | paired bootstrap + BH correction | T5, T6 | F6 | §7, §9.3, §9.4, §10 | DONE-for-draft |
| C-INT-001 | The forecast → uncertainty → risk → decision chain is empirically represented in the frozen artifacts; it is not claimed universally superior | RO1→RO2→RO3 | OBS/EST/SCN mix | integrated pipeline | T1, T2, T3, T5, T5_T6, T6 + multi-origin artifacts | integrated evidence registration | T1, T2, T3, T5, T5_T6, T6 | F1, F2, F3, F4, F5, F6 | §9.6, §10, §12 | DONE-for-draft |
| C-ROB-001 | Performance varies under declared stress/robustness settings | RO2/RO3 | SCN stress, SCN holding-rate sensitivity | RO3.7/RO3.8 stress/robustness | `results/RO3/ablation/RO3_7_stress/RO3_step37_stress_summary.csv`, `results/RO3/ablation/RO3_8_robustness/RO3_step38_holding_rate_summary.csv` | stress/robustness descriptive contrasts | supplementary | supplementary | §9.5, §12 | DONE-for-draft (supplementary wording pending) |

---

## 5. Final table register

| Table ID | Purpose | Source result(s) | Generation script | Last generated commit | Paper section | Status |
|---|---|---|---|---|---|---|
| T1 | RO1 main forecasting comparison | `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv` | `src/optimization/cmido_8q_publication_artifacts.py` | `29b0ed3` | §5, §9.1 | FINAL for draft |
| T2 | RO2 joint propagation summary / tail comparison | `results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv`, `results/RO2/distribution/RO2_step27c3_tail_comparison.csv` | `src/optimization/cmido_8q_publication_artifacts.py` | `29b0ed3` | §6, §9.2 | FINAL for draft |
| T3 | RO2 propagation main result / service-risk curve / joint-independent sensitivity | `results/RO2/propagation/RO2_step27d_propagation_summary.csv`, `results/RO2/propagation/RO2_step27d_service_risk_curve.csv`, `results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv` | `src/optimization/cmido_8q_publication_artifacts.py` | `29b0ed3` | §6, §9.2 | FINAL for draft |
| T4 | RO2 sensitivity/stress | supplementary RO3.7/RO3.8 artifacts | not generated as a manuscript table in this draft | n/a | §9.5, §12 | SUPPLEMENTS-PENDING |
| T5 | RO3 baseline comparison | `results/RO3/ablation/final_comparison/RO3_step36_statistical_pairwise_comparisons.csv` | `src/optimization/cmido_8q_publication_artifacts.py` | `29b0ed3` | §7, §9.3 | FINAL for draft |
| T6 | RO3 ablation | `results/RO3/ablation/final_comparison/RO3_step36_primary_ablation_results.csv` | `src/optimization/cmido_8q_publication_artifacts.py` | `29b0ed3` | §7, §9.4 | FINAL for draft |
| T5_T6 | RO3 controller descriptives | `results/RO3/ablation/final_comparison/RO3_step36_controller_descriptive_statistics.csv` | `src/optimization/cmido_8q_publication_artifacts.py` | `29b0ed3` | §7, §9.3 | FINAL for draft |
| T8 | Integrated decision-value evidence | combined RO1/RO2/RO3 evidence | n/a (evidence integration, not a generated table) | `29b0ed3` | §9.6 | EVIDENCE-REGISTERED |

Notes:

- T1 is a calibrated-forecast-facing projection of the broader `RO1_step26c3_validation_metrics.csv` source; it
  drops the `raw_*` columns and retains the prequential-calibrated columns. Shared numeric values are identical.
- T5 is a publication-facing projection of `RO3_step36_statistical_pairwise_comparisons.csv`; shared numeric values
  are identical. The source retains extra per-contrast columns.
- T6 and T5_T6 share their full schema and values with their source files.
- T4 is not generated as a manuscript-bound table in this draft; RO3.7/RO3.8 summaries exist as supplementary CSV
  evidence.

---

## 6. Final figure register

| Figure ID | Purpose | Source result(s) | Generation script | Last generated commit | Paper section | Status |
|---|---|---|---|---|---|---|
| F1 | RO1 forecast / uncertainty visualization | `results/8Q_publication_artifacts/T1_RO1_validation_metrics.csv` | `src/optimization/cmido_8r_publication_figures.py` | `29b0ed3` | §5, §9.1 | FINAL for draft |
| F2 | RO2 tail behaviour by representation | `results/8Q_publication_artifacts/T2_RO2_tail_comparison.csv` | `src/optimization/cmido_8r_publication_figures.py` | `29b0ed3` | §6, §9.2 | FINAL for draft |
| F3 | RO2 propagated demand tail | `results/8Q_publication_artifacts/T3_RO2_propagation_summary.csv` | `src/optimization/cmido_8r_publication_figures.py` | `29b0ed3` | §6, §9.2 | FINAL for draft |
| F4 | RO2 joint/independent sensitivity | `results/8Q_publication_artifacts/T3_RO2_joint_independent_sensitivity.csv` | `src/optimization/cmido_8r_publication_figures.py` | `29b0ed3` | §6, §9.2 | FINAL for draft |
| F5 | RO3 controller descriptives | `results/8Q_publication_artifacts/T5_T6_controller_descriptives.csv` | `src/optimization/cmido_8r_publication_figures.py` | `29b0ed3` | §7, §9.3 | FINAL for draft |
| F6 | RO3 ablation effects | `results/8Q_publication_artifacts/T6_RO3_ablation.csv` | `src/optimization/cmido_8r_publication_figures.py` | `29b0ed3` | §7, §9.4 | FINAL for draft |
| F7 | Integrated forecast → uncertainty → risk → decision pipeline | conceptual diagram, no separate generated figure file in this draft | n/a | n/a | §1, §9.6 | DIAGRAM-PENDING |

Notes:

- Every figure is generated from a frozen 8Q table and reconciled by 8S. No manuscript-bound figure is generated
  from raw results directly.
- F7, if added, must accurately represent the implemented pipeline and not overstate integration level.

---

## 7. E2E demonstration register

| Demo step | Input | Engine | Expected output | Evidence path | Status |
|---|---|---|---|---|---|
| D1 | Frozen dataset/project | Ingestion + validation | Validated modelling input | `results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv` | VERIFIED |
| D2 | Validated RO1 data | Forecasting | Point + predictive uncertainty | `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv` | VERIFIED |
| D3 | RO1 uncertainty + supply/process duration | RO2 propagation | Shortage/service-risk distribution | `results/RO2/propagation/` + audits | VERIFIED |
| D4 | RO2 risk + procurement inputs | RO3 optimization | Procurement decisions/Pareto set | `results/RO3/multi_origin/` | VERIFIED for N=2500 |
| D5 | Frozen outputs | Dashboard | Decision-intelligence views | `apps/cmido_dashboard.py` + 8P manifest | VERIFIED (8P gate) |
| D6 | Frozen outputs | Table/figure generation | Publication artifacts | `results/8Q_publication_artifacts/`, `results/8R_publication_figures/` | VERIFIED (8Q/8R/8S) |

---

## 8. Unavailable / open items register

This register is explicit. Each item below is recorded, not fabricated.

1. **RO3 scenario-count convergence.** The RO3.3 primary 500→1000 transition failed: 142 failed comparisons,
   max relative change 0.1765. The recorded decision is `RO3_3_EVALUATE_2500`. The 1,000-scenario raw ledger
   replay reproduces the same 142-comparison failure fingerprint, so the recorded failure is recovered, not
   invented. Convergence is an evaluated property of the run, not yet a passed gate.
   This session: recomputed all 9 8Q SHA-256 source hashes and all 6 8R SHA-256 source hashes; every one matches
   the corresponding manifest. SHA-256 fingerprints are no longer an open item for the publication chain.
2. **Five decision-level artifacts registered but not present in the registry:** `RO3_O2_SELECTED_DECISIONS`,
   `RO3_O2_REALIZED_EVALUATION_SUMMARY`, `RO3_O4_REALIZED_EVALUATION_LEDGER`, `RO3_MULTI_ORIGIN_SUMMARY`,
   `RO3_DECISION_SENSITIVITY`. Their dashboards show explicit unavailable states. Partial substitutes exist and are
   documented in the package limitations.
3. **`RO1_PRIMARY_H3_SUMMARY` and `EVIDENCE_8P_MANIFEST`** are registered in the dashboard artifact registry but
   are not yet adapted into dashboard evidence bundles. Their dashboard pages render explicit unavailable states.
   Source files for the five decision-level artifacts were located on disk and are documented below.
4. **Reported SHA-256 fingerprints** for the publication chain are verified this session against recomputed source
   and artifact hashes; all 9 8Q source hashes and all 6 8R source hashes match the manifests. Legacy fingerprints
   outside that chain were not recomputed.
5. **Unregistered-file presence checks** are existence-only.
6. **Observed-stream dates/authorship/software versions** are unavailable.
7. **Additional master-spec stress scenarios** have no recorded results; none were fabricated.
8. **Simulated/derived/scenario results** are never presented as observed real-world outcomes.

---

## 9. Freeze checklist

- [x] Every final claim has an evidence row.
- [x] Every numerical claim has a result source.
- [x] Every result has a dataset and configuration.
- [x] Every statistical statement identifies its analysis.
- [x] Every final table is reproducible from the declared script.
- [x] Every final figure is reproducible from the declared script.
- [x] Dashboard values agree with frozen result sources where applicable.
- [ ] Manuscript and supplementary files match frozen values. **PARTIAL — draft written; final figure T7 not generated.**
- [x] Final commit SHA is recorded.
- [x] Final environment/dependency information is recorded.
- [x] Final dataset/provenance manifest is recorded.

---

## 10. What changed in this completion pass

- RO3.3 convergence failure fingerprint recovered from the on-disk 1,000-scenario ledger and matched to the
  historical `RO3_step33_summary.json` failure.
- SHA reconciliation recomputed and extended this session: all 9 8Q source hashes and all 6 8R source hashes match the manifests after
  regeneration.
- Concordance completed from the frozen artifact chain; no manuscript-bound claim was left without a source path
  except where explicitly marked unavailable or pending.
- Limitations register updated to reflect the recovered convergence fingerprint and the decision-level artifacts’
  partial substitutes.

---

## 11. Remaining open items before professor meeting / paper finalization1. Resolve or explicitly scope the RO3.3 convergence path (2,500 then 5,000 evaluation, per spec) if scenario-count
   convergence is to be claimed passed. Do not relax the documented thresholds or claim passed status without the
   required run.
   2. Decide whether the five decision-level artifacts can be legitimately integrated from the existing on-disk sources
   located this session, or remain explicitly unavailable with documented substitutes. The candidate sources exist:
   `results/RO3/ablation/O2/O2_selected_decisions.csv` (48,800 bytes),
   `results/RO3/ablation/O2/O2_realized_evaluation_summary.csv` (4,998 bytes),
   `results/RO3/ablation/O4_single_origin/O4_single_origin_realized_evaluation_ledger.csv` (5,046 bytes),
   `results/RO3/multi_origin/RO3_step35_origin_summary_N2500.csv` (2,130 bytes),
   `results/RO3/decision_sensitivity/RO3_step33B_corrected_summary_20220701.csv` (641 bytes).
   These are candidate substitutes, not decision-gated publication artifacts; each must be mapped to its intended
   registry schema before integration.
   3. Complete T4 as a manuscript-bound table only if the supplementary RO3.7/RO3.8 wording is finalized.
   4. Decide whether F7 is added as a conceptual diagram and keep it accurate to the implemented pipeline.
   5. Finalize the bibliography from traceable literature only; do not invent citations. The current draft does not
   contain inline citations; the reference list is intentionally not written until the literature is screened.
   6. Remove or qualify any claim that currently outruns the evidence status above.

<!-- End of concordance. -->
