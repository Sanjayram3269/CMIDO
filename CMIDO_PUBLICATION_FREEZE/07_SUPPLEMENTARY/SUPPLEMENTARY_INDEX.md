# CMIDO — Supplementary Material Index

This folder indexes the supplementary material that accompanies the draft manuscript.

Supplementary material is provided for transparency and reproducibility. It does not add new scientific results
beyond the frozen artifacts used in the manuscript.

## Contents

- Source-of-truth pointers to the RO1, RO2, and RO3 result files.
- Pointers to the 8M/8N/8O/8P evidence manifests.
- Pointers to the 8Q/8R/8S publication artifact chain.
- Pointers to the stress/robustness supplementary artifacts.

## RO1 supplementary pointers

- Calibrated forecast representation:
  `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv`
- Forecast evaluation metrics:
  `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv`
- Publication table:
  `results/8Q_publication_artifacts/T1_RO1_validation_metrics.csv`
- Publication figure:
  `results/8R_publication_figures/F1_RO1_calibration_coverage.png`

## RO2 supplementary pointers

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
- Monte Carlo convergence evidence:
  `results/RO2/propagation_convergence_nested/RO2_step27d4_summary.json`

## RO3 supplementary pointers

- Primary scenario set:
  `results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv`
- Scenario convergence summary:
  `results/RO3/scenario_convergence/RO3_step33_summary.json`
- Multi-origin artifacts:
  `results/RO3/multi_origin/RO3_step35_*_N2500.csv`
- Controlled ablation sources:
  `results/RO3/ablation/final_comparison/RO3_step36_*.csv`
- Stress artifacts:
  `results/RO3/ablation/RO3_7_stress/RO3_step37_*.csv`
- Robustness artifacts:
  `results/RO3/ablation/RO3_8_robustness/RO3_step38_*.csv`
- Publication tables:
  `results/8Q_publication_artifacts/T5_RO3_baseline_comparison.csv`
  `results/8Q_publication_artifacts/T5_T6_controller_descriptives.csv`
  `results/8Q_publication_artifacts/T6_RO3_ablation.csv`
- Publication figures:
  `results/8R_publication_figures/F5_RO3_controller_descriptives.png`
  `results/8R_publication_figures/F6_RO3_ablation_effects.png`

## Evidence package pointers

- 8M gate:
  `results/RO3/ablation/8M_gate/CMIDO_8M_GATE_MANIFEST.json`
  `results/RO3/ablation/8M_gate/CMIDO_8M_GATE_AUDIT.csv`
- 8N integrated evidence:
  `results/8N_integrated_evidence/CMIDO_8N_INTEGRATED_EVIDENCE_MANIFEST.json`
  `results/8N_integrated_evidence/CMIDO_8N_INTEGRATED_EVIDENCE_AUDIT.csv`
- 8O paper-facing evidence package:
  `docs/CMIDO_8O_PAPER_EVIDENCE_PACKAGE.md`
  `results/8O_paper_evidence/CMIDO_8O_PAPER_EVIDENCE_MANIFEST.json`
  `results/8O_paper_evidence/CMIDO_8O_PAPER_EVIDENCE_AUDIT.csv`
- 8P dashboard e2e:
  `results/8P_dashboard_e2e/CMIDO_8P_DASHBOARD_E2E_MANIFEST.json`
  `results/8P_dashboard_e2e/CMIDO_8P_DASHBOARD_E2E_AUDIT.csv`
- 8Q publication artifacts:
  `results/8Q_publication_artifacts/CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json`
  `results/8Q_publication_artifacts/CMIDO_8Q_PUBLICATION_ARTIFACT_AUDIT.csv`
- 8R publication figures:
  `results/8R_publication_figures/CMIDO_8R_FIGURE_CONCORDANCE.json`
  `results/8R_publication_figures/CMIDO_8R_FIGURE_AUDIT.csv`
- 8S numerical reconciliation:
  `results/8S_numerical_reconciliation/CMIDO_8S_RECONCILIATION_MANIFEST.json`
  `results/8S_numerical_reconciliation/CMIDO_8S_RECONCILIATION_AUDIT.csv`

## Reproducibility pointer

Full reproducibility information is in `06_REPRODUCIBILITY/` and in
`results/CMIDO_FINAL_PACKAGE_MANIFEST.json`.

<!-- End of supplementary index. -->
