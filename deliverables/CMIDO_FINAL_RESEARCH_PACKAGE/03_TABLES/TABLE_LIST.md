# CMIDO — Publication Tables

This folder lists the publication tables used in the draft manuscript, with captions and source pointers.

All tables are generated from the frozen upstream result files by
`src/optimization/cmido_8q_publication_artifacts.py`. The table-to-source reconciliation is recorded in
`results/8S_numerical_reconciliation/`.

## Table inventory

### T1 — RO1 validation metrics

- File: `results/8Q_publication_artifacts/T1_RO1_validation_metrics.csv`
- Upstream source: `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv`
- Scope: dataset, series, horizon, sample sizes, point accuracy, and prequential-calibrated coverage/width/Winkler
  results.
- Note: this is a calibrated-forecast-facing projection of the broader upstream source. The upstream source also
  contains the raw coverage/width/Winkler columns; the publication table retains the prequential-calibrated columns.
- Manuscript section: §5 and §9.1.

### T2 — RO2 joint propagation summary

- File: `results/8Q_publication_artifacts/T2_RO2_joint_propagation_summary.csv`
- Upstream source: `results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv`
- Scope: joint propagation summary.
- Manuscript section: §6 and §9.2.

### T2 — RO2 tail comparison

- File: `results/8Q_publication_artifacts/T2_RO2_tail_comparison.csv`
- Upstream source: `results/RO2/distribution/RO2_step27c3_tail_comparison.csv`
- Scope: tail behaviour by representation.
- Manuscript section: §6 and §9.2.

### T3 — RO2 propagation summary

- File: `results/8Q_publication_artifacts/T3_RO2_propagation_summary.csv`
- Upstream source: `results/RO2/propagation/RO2_step27d_propagation_summary.csv`
- Scope: propagated demand/shortage/service behaviour over the evaluated population.
- Manuscript section: §6 and §9.2.

### T3 — RO2 service-risk curve

- File: `results/8Q_publication_artifacts/T3_RO2_service_risk_curve.csv`
- Upstream source: `results/RO2/propagation/RO2_step27d_service_risk_curve.csv`
- Scope: service-risk curve.
- Manuscript section: §6 and §9.2.

### T3 — RO2 joint versus independent sensitivity

- File: `results/8Q_publication_artifacts/T3_RO2_joint_independent_sensitivity.csv`
- Upstream source: `results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv`
- Scope: sensitivity to the joint versus independent propagation assumption.
- Manuscript section: §6 and §9.2.

### T5 — RO3 baseline comparison

- File: `results/8Q_publication_artifacts/T5_RO3_baseline_comparison.csv`
- Upstream source: `results/RO3/ablation/final_comparison/RO3_step36_statistical_pairwise_comparisons.csv`
- Scope: planed O1/O2/O3/O4 contrasts with bootstrap bounds and BH-corrected significance.
- Note: this is a publication-facing projection of the upstream source. The upstream source retains additional
  per-contrast columns such as relative mean difference, improve/worsen/tie counts, and rank-biserial sign.
- Manuscript section: §7 and §9.3.

### T5/T6 — RO3 controller descriptives

- File: `results/8Q_publication_artifacts/T5_T6_controller_descriptives.csv`
- Upstream source: `results/RO3/ablation/final_comparison/RO3_step36_controller_descriptive_statistics.csv`
- Scope: descriptive summaries for each controller across the 11 locked origins.
- Manuscript section: §7 and §9.3.

### T6 — RO3 ablation

- File: `results/8Q_publication_artifacts/T6_RO3_ablation.csv`
- Upstream source: `results/RO3/ablation/final_comparison/RO3_step36_primary_ablation_results.csv`
- Scope: ablation contrasts with relative change, bootstrap bounds, improved/worsened/tie counts, rank-biserial
  sign, and BH-corrected significance.
- Manuscript section: §7 and §9.4.

## Format note

Publication tables are provided as CSV. The formatted manuscript tables in the review copy are generated from these
CSV files; the CSV files are the source of truth.

<!-- End of table list. -->
