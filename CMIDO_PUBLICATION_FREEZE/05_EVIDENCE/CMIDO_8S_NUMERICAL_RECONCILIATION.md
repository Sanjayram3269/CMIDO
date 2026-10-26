# CMIDO 8S — Full Numerical / Source Reconciliation

## Purpose

8S is the final evidence-consistency gate between the authoritative RO1/RO2/RO3 source artifacts, the frozen 8Q publication tables, and the 8R publication figures.

It does **not** recompute scientific results, alter source values, or replace a source artifact. It verifies that publication-facing artifacts remain numerically and structurally faithful to their frozen upstream evidence.

## Checks

- 8Q and 8R manifests exist and report PASS.
- Each frozen 8Q table exists and has the expected row count.
- Publication-table schemas exactly match their authoritative upstream CSV schemas.
- Publication-table values exactly match their upstream CSV values after CSV parsing.
- 8Q manifest SHA-256 entries match the authoritative source files.
- RO3 contains exactly O1/O2/O3/O4 with 11 origins each.
- RO3 controller evidence contains the frozen realized service-level metric used by F5.
- RO2 sensitivity contains 4 materials × 12 forecast origins × 5 quantiles = 240 rows.
- 8R contains exactly six publication figures and references exactly the six intended 8Q source tables.
- Every 8R source hash matches the current source table and every declared figure file exists.

## Interpretation

A PASS means the publication artifact chain is internally consistent at the file/value/schema level. It does not by itself establish external scientific validity, causal validity, or manuscript correctness; those remain subject to the documented methodology, assumptions, limitations, and peer review.

## Output

The executable gate writes:

- `results/8S_numerical_reconciliation/CMIDO_8S_RECONCILIATION_MANIFEST.json`
- `results/8S_numerical_reconciliation/CMIDO_8S_RECONCILIATION_AUDIT.csv`

The 8S gate should be run after 8Q and 8R are regenerated and before the final repository/reproducibility freeze.
