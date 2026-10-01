# CMIDO 9A — Real-Data Ingestion and Generalization

## Purpose

9A establishes the controlled boundary between an external civil-project dataset and the frozen CMIDO research pipeline. It does **not** change the 8M–8S publication evidence package and does **not** change the dashboard UI.

## What 9A proves

- External CSV bundles can be ingested through an explicit mapping contract.
- Project, activity, and dependency tables are mapped into the existing CMIDO 8I normalization layer.
- Duration units can be normalized explicitly from hours, days, or weeks into CMIDO day values.
- Required structure and dependency references are validated before downstream use.
- Invalid source records are surfaced with table and 1-based source-row information; they are never silently discarded.
- Source row counts and mapping provenance are retained in the canonical dataset metadata.
- A SHA-256 fingerprint is produced for deterministic dataset identity.
- Re-ingesting the same source with the same mapping produces the same fingerprint.
- A machine-readable ingestion audit is generated.

## Explicit non-goals

9A does not claim that an arbitrary unknown dataset can be accepted without a schema/mapping decision. CMIDO must not invent construction semantics from ambiguous columns. A new real civil dataset must therefore be accompanied by an explicit mapping file and any required unit decisions.

9A currently provides a CSV-bundle adapter. The same canonical boundary can be extended to other source formats without changing the downstream CMIDO experiment contract.

## Current fixture

`examples/9A_real_data/` contains a small civil-project-shaped fixture used only to prove the adapter and gate. It is **not** a substitute for the user's actual civil-project dataset.

The fixture contains:

- `project.csv`
- `activities.csv`
- `dependencies.csv`
- `mapping.json`

## Gate

Run:

```powershell
cd D:\CMIDO
git checkout main
git pull --ff-only origin main
python -m src.optimization.cmido_9a_real_data_generalization_gate
pytest -q
```

Expected 9A result is `STATUS: PASS`, followed by the full regression suite remaining green.

## Real-project workflow

1. Place the source tables in a controlled project-data directory.
2. Define the source-to-CMIDO mappings explicitly.
3. Declare units instead of relying on implicit conversion.
4. Run the 9A ingestion gate.
5. Inspect the rejected-record report if the gate stops.
6. Inspect the canonical dataset and ingestion audit.
7. Only after ingestion passes should the real dataset be sent into the existing RO1 → RO2 → RO3 pipeline.
8. Preserve the original source files and mapping file alongside the resulting fingerprint for reproducibility.

## Research integrity rule

The 9A layer is an adapter, not a data generator. Missing project semantics, activity relationships, units, or material definitions must be supplied by the dataset owner or documented mapping decision. The system must not fabricate them.
