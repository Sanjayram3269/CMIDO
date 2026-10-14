# CMIDO — Publication Figures

This folder lists the publication figures used in the draft manuscript, with captions and source pointers.

All figures are generated from the frozen 8Q publication tables by
`src/optimization/cmido_8r_publication_figures.py`. The publication table-to-source reconciliation is recorded in
`results/8S_numerical_reconciliation/`.

## Figure inventory

### F1 — RO1 calibration coverage

- File: `results/8R_publication_figures/F1_RO1_calibration_coverage.png`
- Source table: `results/8Q_publication_artifacts/T1_RO1_validation_metrics.csv`
- Source source: `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv`
- Purpose: probabilistic forecast coverage evidence for the RO1 calibrated forecasts.
- Manuscript section: §5 and §9.1.

### F2 — RO2 tail comparison

- File: `results/8R_publication_figures/F2_RO2_tail_comparison.png`
- Source table: `results/8Q_publication_artifacts/T2_RO2_tail_comparison.csv`
- Source source: `results/RO2/distribution/RO2_step27c3_tail_comparison.csv`
- Purpose: tail behaviour by representation.
- Manuscript section: §6 and §9.2.

### F3 — RO2 propagated demand tail

- File: `results/8R_publication_figures/F3_RO2_propagation_tail.png`
- Source table: `results/8Q_publication_artifacts/T3_RO2_propagation_summary.csv`
- Source source: `results/RO2/propagation/RO2_step27d_propagation_summary.csv`
- Purpose: propagated demand/shortage/service behaviour over the evaluated population.
- Manuscript section: §6 and §9.2.

### F4 — RO2 joint versus independent sensitivity

- File: `results/8R_publication_figures/F4_RO2_joint_independent_sensitivity.png`
- Source table: `results/8Q_publication_artifacts/T3_RO2_joint_independent_sensitivity.csv`
- Source source: `results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv`
- Purpose: sensitivity to the joint versus independent propagation assumption.
- Manuscript section: §6 and §9.2.

### F5 — RO3 controller descriptives

- File: `results/8R_publication_figures/F5_RO3_controller_descriptives.png`
- Source table: `results/8Q_publication_artifacts/T5_T6_controller_descriptives.csv`
- Source source: `results/RO3/ablation/final_comparison/RO3_step36_controller_descriptive_statistics.csv`
- Purpose: controller-level descriptive evidence for O1/O2/O3/O4.
- Manuscript section: §7 and §9.3.

### F6 — RO3 ablation effects

- File: `results/8R_publication_figures/F6_RO3_ablation_effects.png`
- Source table: `results/8Q_publication_artifacts/T6_RO3_ablation.csv`
- Source source: `results/RO3/ablation/final_comparison/RO3_step36_primary_ablation_results.csv`
- Purpose: controlled ablation effects with bootstrap and multiplicity information.
- Manuscript section: §7 and §9.4.

## Format note

Publication figures are provided as PNGs at 300 DPI, generated from the frozen 8Q tables. Editable source figures
are not included in this package; the editable source is the 8Q table and the 8R generation script.

## Labeling discipline

Figures do not relabel scenario, estimated, or derived quantities as observed. Each figure’s caption and source
pointer should be read together with the provenance discussion in §4 and §11 of the manuscript.

<!-- End of figure list. -->
