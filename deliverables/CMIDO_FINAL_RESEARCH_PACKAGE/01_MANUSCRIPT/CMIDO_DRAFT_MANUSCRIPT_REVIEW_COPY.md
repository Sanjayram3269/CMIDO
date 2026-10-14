# CMIDO — Draft Manuscript Review Copy

**Status:** review copy derived from `CMIDO_DRAFT_MANUSCRIPT.md`.
**Repository:** `Sanjayram3269/CMIDO`, branch `main`.
**Frozen dashboard checkpoint:** `c100b477ed8b79e8cdf1384ecfddd80b136adb78`.
**Session packaged:** 2026-10-14.
**Intended use:** supervisor review, not a submission claim.

This review copy is prepared for reading and discussion. It is derived from the editable manuscript source in the
same folder. It is not a PDF; this environment does not currently expose a confirmed manuscript-to-PDF toolchain,
so the review copy is provided as markdown with explicit pointers to the frozen tables and figures.

---

## What this review copy contains

- The draft manuscript text.
- Explicit source pointers for every results section, so the reviewer can inspect the frozen artifact behind each
  claim.
- A summary of what is supported by the frozen evidence and what remains open.

---

## Source map for the review copy

### RO1

- Calibrated forecast representation:
  `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv`
- Forecast evaluation metrics:
  `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv`
- Publication table:
  `results/8Q_publication_artifacts/T1_RO1_validation_metrics.csv`
- Publication figure:
  `results/8R_publication_figures/F1_RO1_calibration_coverage.png`

### RO2

- Admissible modelling view:
  `results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv`
- Joint propagation summary:
  `results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv`
- Tail comparison:
  `results/RO2/distribution/RO2_step27c3_tail_comparison.csv`
- Propagation summary:
  `results/RO2/propagation/RO2_step27d_propagation_summary.csv`
- Service-risk curve:
  `results/RO2/propagation/RO2_step27d_service_risk_curve.csv`
- Joint/independent sensitivity:
  `results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv`
- Publication tables:
  `results/8Q_publication_artifacts/T2_RO2_joint_propagation_summary.csv`
  `results/8Q_publication_artifacts/T2_RO2_tail_comparison.csv`
  `results/8Q_publication_artifacts/T3_RO2_propagation_summary.csv`
  `results/8Q_publication_artifacts/T3_RO2_service_risk_curve.csv`
  `results/8Q_publication_artifacts/T3_RO2_joint_independent_sensitivity.csv`
- Publication figures:
  `results/8R_publication_figures/F2_RO2_tail_comparison.png`
  `results/8R_publication_figures/F3_RO2_propagation_tail.png`
  `results/8R_publication_figures/F4_RO2_joint_independent_sensitivity.png`
- Monte Carlo convergence evidence:
  `results/RO2/propagation_convergence_nested/RO2_step27d4_summary.json`

### RO3

- Primary scenario set:
  `results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv`
- Scenario convergence summary:
  `results/RO3/scenario_convergence/RO3_step33_summary.json`
- Multi-origin decisions/Pareto/origin/audit artifacts:
  `results/RO3/multi_origin/RO3_step35_*_N2500.csv`
- Controlled ablation sources:
  `results/RO3/ablation/final_comparison/RO3_step36_*.csv`
- Stress artifacts:
  `results/RO3/ablation/RO3_7_stress/RO3_step37_*.csv`
- Robustness artifacts:
  `results/RO3/ablation/RO3_8_robustness/RO3_step38_*.csv`
- Publication tables:
  `results/8Q_publication_artifacts/T4_RO3_stress_robustness.csv`
  `results/8Q_publication_artifacts/T5_RO3_baseline_comparison.csv`
  `results/8Q_publication_artifacts/T5_T6_controller_descriptives.csv`
  `results/8Q_publication_artifacts/T6_RO3_ablation.csv`
- Publication figures:
  `results/8R_publication_figures/F5_RO3_controller_descriptives.png`
  `results/8R_publication_figures/F6_RO3_ablation_effects.png`

---

## Review-copy summary of supported statements

The following statements are supported by the frozen artifacts in this packaging session:

- RO1 forecasts and calibration metrics exist and are reported in the publication table T1.
- RO2 propagation, tail, service-risk, and joint/independent sensitivity results exist and are reported in
  publication tables T2 and T3 and figures F2–F4.
- RO3 controlled contrasts O1/O2/O3/O4 exist and are reported in publication tables T5/T6 and figures F5–F6.
- Stress and robustness results exist and are reported in publication table T4 (§9.5), generated from the
  RO3.7/RO3.8 frozen summaries and reconciled by 8S.

The following are **not** claimed by this review copy:

- Universal superiority of any configuration.
- Supplier-specific historical lead-time behaviour from travel-time data.
- Scenario results as observed real-world outcomes.
- Resolution of the open decision-level evidence gaps or the failed 500→1,000 scenario convergence gate.

---

## What the reviewer should focus on

1. Whether the manuscript’s numerical claims match the 8Q tables and their declared source files.
2. Whether the uncertainty and multiplicity handling is described honestly and not overstated.
3. Whether the gaps between OBS/DER/EST/SCN are preserved in every relevant statement.
4. Whether the remaining open research items in the package README are acceptable for the current review stage.

---

## Next step

If the review is positive, the next steps are to finalize the claim-to-evidence concordance, produce a rendered
review copy in the preferred final format, and optionally move toward a submission package after the remaining open
research items are resolved. If the review identifies issues, the manuscript and concordance should be revised before
any submission claim is made.

<!-- End of review copy. -->
