# CMIDO — Final Research Package

**Status:** review draft being assembled.
**Repository:** `Sanjayram3269/CMIDO`
**Branch:** `main`
**Frozen dashboard checkpoint:** `c100b477ed8b79e8cdf1384ecfddd80b136adb78`
**Packaging session:** 2026-10-14
**Intended use:** supervisor review, not an automatic submission claim.

This folder is the one consolidated, reproducible research package for the CMIDO work completed so far.
It brings together the finalized manuscript, publication-quality tables and figures, supplementary evidence,
source concordance, reproducibility instructions, and a supervisor-review message.

## What this package is

- An **evidence-backed draft manuscript** for:
  *An Uncertainty-Aware Machine Learning and Multi-Objective Optimization Framework for Resilient
  Construction Material Procurement*
- The **frozen publication tables** and **frozen publication figures** that support it.
- The **evidence, statistical, and numerical audit reports** behind those artifacts.
- A **reproducibility statement** with the exact commands, environment snapshot, and source/result manifest.
- A **supervisor-review message** and demo outline.

## What this package is not

- It is **not** a claim that the work is journal-submission-ready.
- It does **not** contain fabricated experiments, invented citations, or invented numerical results.
- It does **not** resolve open research-side issues silently; those are listed explicitly.

## How to read this package

Start with the draft manuscript in `01_MANUSCRIPT/`, then use the table/figure inventory in
`02_FIGURES/` and `03_TABLES/`, then the evidence and audit material in `05_EVIDENCE_AND_AUDITS/`,
then the reproducibility instructions in `06_REPRODUCIBILITY/`. The supervisor-review message is in
`07_PROFESSOR_REVIEW/`.

## Top-level contents

- `00_README_AND_STATUS/` — this README plus working audit and verification notes.
- `01_MANUSCRIPT/` — editable manuscript source plus review copy.
- `02_FIGURES/` — publication figures and captions.
- `03_TABLES/` — publication tables as CSV plus formatted versions.
- `04_SUPPLEMENTARY/` — supplementary results and methodological detail.
- `05_EVIDENCE_AND_AUDITS/` — evidence, statistical, and numerical audit reports.
- `06_REPRODUCIBILITY/` — environment info, seeds, reproduction commands, source/result manifest.
- `07_PROFESSOR_REVIEW/` — supervisor message and demo outline.

## Source-of-truth rule

Every number in the manuscript and in the formatted tables/figures must trace to a frozen result file, not
to prose. The frozen sources used for this package are:

- `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv`
- `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv`
- `results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv`
- `results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv`
- `results/RO2/distribution/RO2_step27c3_tail_comparison.csv`
- `results/RO2/propagation/RO2_step27d_propagation_summary.csv`
- `results/RO2/propagation/RO2_step27d_service_risk_curve.csv`
- `results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv`
- `results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv`
- `results/RO3/multi_origin/` (decisions, Pareto, origin summary, audit)
- `results/RO3/ablation/final_comparison/` (controlled ablation source CSVs)
- `results/RO3/ablation/RO3_7_stress/` (stress artifacts)
- `results/RO3/ablation/RO3_8_robustness/` (robustness artifacts)
- `results/RO3/scenario_convergence/RO3_step33_summary.json`
- `results/RO2/propagation_convergence_nested/RO2_step27d4_summary.json`

The publication-facing artifacts derived from those sources are:

- `results/8Q_publication_artifacts/*.csv` — 9 publication tables
- `results/8R_publication_figures/*.png` — 6 publication figures

## Validation summary this session

- 8M: PASS (20/20)
- 8N: PASS (13/13)
- 8O: PASS (17/17)
- 8P: PASS (3/3)
- 8Q: PASS (31/31)
- 8R: PASS (28/28)
- 8S: PASS (81/81)
- Full construction + optimization regression: 1059 passed, exit 0

## Remaining open research items

These are recorded, not fixed, in this package:

1. Five decision-level artifacts are registered but not present in the artifact inventory:
   `RO3_O2_SELECTED_DECISIONS`, `RO3_O2_REALIZED_EVALUATION_SUMMARY`, `RO3_O4_REALIZED_EVALUATION_LEDGER`,
   `RO3_MULTI_ORIGIN_SUMMARY`, `RO3_DECISION_SENSITIVITY`.
2. `RO1_PRIMARY_H3_SUMMARY` and `EVIDENCE_8P_MANIFEST` are registered but not adapted into evidence bundles.
3. Reported SHA-256 fingerprints have not been recomputed and verified on this session’s disk.
4. Presence checks for unregistered files are existence-only.
5. RO3 500→1,000 scenario convergence failed; the recorded next evaluation is 2,500, then 5,000.
6. Observed-stream dates, authorship, and software-version metadata are unavailable.
7. Additional master-spec stress scenarios have no recorded results.
8. Simulated/derived/scenario results are never presented as observed real-world outcomes.

## Stop condition

This package is intended as a supervisor-review draft. It stops at the review-draft boundary unless and
until the remaining open research items are resolved and the evidence/reproducibility gates are verified as
supporting a submission claim.
