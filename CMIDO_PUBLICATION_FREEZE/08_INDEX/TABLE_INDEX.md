# CMIDO — Publication Table Index

Generated 2026-10-26 from the frozen package copy in `CMIDO_PUBLICATION_FREEZE/03_TABLES/`.
Counts and hashes below are computed from the actual files in this folder, not from historical reports.

Canonical location in the package: `03_TABLES/` (copied byte-identical from
`deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/03_TABLES/`).

The duplicate copies under `results/8Q_publication_artifacts/` were deliberately **not** copied:
all 10 table CSVs were verified byte-identical to the canonical set on 2026-10-26.
The 8Q generator, audit and manifest are mirrored at `05_EVIDENCE/figure_table_audits/`.

## Table inventory (10 tables)

| File | Bytes | SHA-256 |
|---|---|---|
| `T1_RO1_validation_metrics.csv` | 7,350 | `053804dbd125e3d912197c70c08c1a196a868af24da5adec5bbf255c7b08ae7e` |
| `T2_RO2_joint_propagation_summary.csv` | 692 | `649672c7f92660fb47f2f8e81c21e1dd91fd96443614d8d44034c5ce4ba69b2e` |
| `T2_RO2_tail_comparison.csv` | 1,017 | `461330c6b88c5fbe05de8404f5945e1de6753bd974e1bcca6c1c2c9b7ce7123d` |
| `T3_RO2_joint_independent_sensitivity.csv` | 25,557 | `63d5815be6a822a6a0707f07063a0836cf0e835c02ebb2dc70dbdca24d6d4119` |
| `T3_RO2_propagation_summary.csv` | 23,589 | `207778c4c4d85279997d4210850273d0f12f386fd2b8fc6ed4709e1af0a93ade` |
| `T3_RO2_service_risk_curve.csv` | 18,763 | `26a2cba21d870a0c443b7dcbfe12ce27e2a8976d54bb1b0dab3ff63f012e1a10` |
| `T4_RO3_stress_robustness.csv` | 6,238 | `99c7eb5c462b988581b11075b65a071ddd8c6c47e8e20b2d07444f3f5367a1e4` |
| `T5_RO3_baseline_comparison.csv` | 7,884 | `8f0069cc477a6ac527c0968a4e904ab4b3799416c7df1b6a51c62aac4a0a5980` |
| `T5_T6_controller_descriptives.csv` | 2,258 | `1fb35b6882e843cc565bb37692e6701eae84d90f9057762c3be59cb3ebbc13bf` |
| `T6_RO3_ablation.csv` | 5,295 | `60020d489e39bd76ef9c7d66fde99e4d90684d0f8bff703412b0d10207ec5eb3` |

Note: two tables share a numeric label prefix by design — `T2_RO2_joint_propagation_summary.csv` and
`T2_RO2_tail_comparison.csv` are both "Table T2" family evidence, and `T5_RO3_baseline_comparison.csv` /
`T5_T6_controller_descriptives.csv` / `T6_RO3_ablation.csv` carry the T5/T6 split used by the manuscript.
The labels are the repository's own; no table was renamed for this package.

## Provenance detail (from the repository's authoritative `TABLE_LIST.md`, copied verbatim)

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

### T4 — RO3 stress and robustness

- File: `results/8Q_publication_artifacts/T4_RO3_stress_robustness.csv`
- Upstream sources: `results/RO3/ablation/RO3_7_stress/RO3_step37_stress_summary.csv` (16 rows) and
  `results/RO3/ablation/RO3_8_robustness/RO3_step38_holding_rate_summary.csv` (12 rows).
- Scope: controller-level outcomes under four declared duration-stress cases (P50/P75/P90/P95) and three declared
  annual holding-rate cases (H20/H30/H40), aligned into one table with an explicit `scenario_family`,
  `scenario_case` and `parameter_name`/`parameter_value` pair.
- Note: this is a relabel-and-concatenate projection of two frozen upstream summaries; no value is recomputed.
  Both upstream SHA-256 hashes are recorded in the 8Q manifest and reconciled by 8S.
- Manuscript section: §9.5 and §12.

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

