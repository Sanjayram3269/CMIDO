# CMIDO — Evidence, Statistical, and Numerical Audit Index

This folder indexes the audit reports behind the manuscript’s evidence chain.

The audit reports establish that the publication artifacts are internally consistent and traceable to their
declared sources.

## Audit index

### 8M controlled-evidence gate

- Manifest: `results/RO3/ablation/8M_gate/CMIDO_8M_GATE_MANIFEST.json`
- Audit: `results/RO3/ablation/8M_gate/CMIDO_8M_GATE_AUDIT.csv`
- Status: PASS (20/20)
- Purpose: verify the frozen controller/configuration and the controlled ablation artifact set.

### 8N integrated evidence gate

- Manifest: `results/8N_integrated_evidence/CMIDO_8N_INTEGRATED_EVIDENCE_MANIFEST.json`
- Audit: `results/8N_integrated_evidence/CMIDO_8N_INTEGRATED_EVIDENCE_AUDIT.csv`
- Status: PASS (13/13)
- Purpose: verify the key RO1/RO2/RO3 source artifacts and the 8M evidence package are present.

### 8O paper-facing evidence package gate

- Manifest: `results/8O_paper_evidence/CMIDO_8O_PAPER_EVIDENCE_MANIFEST.json`
- Audit: `results/8O_paper_evidence/CMIDO_8O_PAPER_EVIDENCE_AUDIT.csv`
- Status: PASS (17/17)
- Purpose: verify the paper-facing evidence package exists and contains the required provenance, assumptions,
  limitations, validity, and reproducibility material.

### 8P dashboard end-to-end gate

- Manifest: `results/8P_dashboard_e2e/CMIDO_8P_DASHBOARD_E2E_MANIFEST.json`
- Audit: `results/8P_dashboard_e2e/CMIDO_8P_DASHBOARD_E2E_AUDIT.csv`
- Status: PASS (20/20, plus 3 pytest checks)
- Purpose: verify the dashboard contains the required real-data experiment and evidence contract elements.

### 8Q publication artifact gate

- Manifest: `results/8Q_publication_artifacts/CMIDO_8Q_PUBLICATION_ARTIFACT_MANIFEST.json`
- Audit: `results/8Q_publication_artifacts/CMIDO_8Q_PUBLICATION_ARTIFACT_AUDIT.csv`
- Status: PASS (31/31)
- Purpose: verify each publication table exists, has the expected shape, and is generated from the declared source.

### 8R publication figure gate

- Concordance: `results/8R_publication_figures/CMIDO_8R_FIGURE_CONCORDANCE.json`
- Audit: `results/8R_publication_figures/CMIDO_8R_FIGURE_AUDIT.csv`
- Status: PASS (28/28)
- Purpose: verify each publication figure is generated from the declared 8Q source and has a recorded source hash.

### 8S numerical/source reconciliation

- Manifest: `results/8S_numerical_reconciliation/CMIDO_8S_RECONCILIATION_MANIFEST.json`
- Audit: `results/8S_numerical_reconciliation/CMIDO_8S_RECONCILIATION_AUDIT.csv`
- Status: PASS (81/81)
- Purpose: verify the publication tables/fingerprints match their declared sources and the figures match their
  declared 8Q sources.

## Statistical evidence notes

Statistical evidence is drawn from the RO3 controlled ablation source files and reconciled into the 8Q publication
tables. The relevant source files are:

- `results/RO3/ablation/final_comparison/RO3_step36_origin_level_results.csv`
- `results/RO3/ablation/final_comparison/RO3_step36_material_level_results.csv`
- `results/RO3/ablation/final_comparison/RO3_step36_controller_descriptive_statistics.csv`
- `results/RO3/ablation/final_comparison/RO3_step36_primary_ablation_results.csv`
- `results/RO3/ablation/final_comparison/RO3_step36_statistical_pairwise_comparisons.csv`
- `results/RO3/ablation/final_comparison/RO3_step36_statistical_analysis_audit.csv`

The statistical evidence uses origin-level contrasts with bootstrap uncertainty and Benjamini–Hochberg
multiplicity control.

## Numerical audit notes

8S is the stronger numeric gate. It confirms:

- each 8Q table exists and has the expected row count,
- each 8Q table schema matches its declared upstream source schema,
- each 8Q table values match its declared upstream source values under the generation script’s declared
  deterministic transformation,
- each 8Q manifest SHA-256 entry matches the declared source file,
- RO3 contains exactly O1/O2/O3/O4 with 11 origins each,
- RO2 sensitivity contains 240 rows as expected,
- the 8R figures match their declared 8Q sources and exist.

## What the audits do and do not establish

The audits establish internal consistency and source traceability for the publication artifact chain. They do not
establish external scientific validity, causal validity, or manuscript correctness beyond the documented
methodology, assumptions, limitations, and peer review.

<!-- End of evidence audit index. -->
