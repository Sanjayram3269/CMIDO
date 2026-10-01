# CMIDO 9B — Empirical Real-Project End-to-End Evidence

## Purpose

9B moves CMIDO beyond the controlled 9A fixture boundary onto public empirical construction data. It validates two observed evidence streams:

1. PSLIB / DSLIB v3.4 — an empirical project workbook used for baseline scheduling, risk analysis, resources, and project control.
2. SUCCESS construction-logistics dataset — public construction-site, material-demand, supplier, transport, truck, and consolidation-centre records.

## Selected empirical project

`C2025-02 Urban Road.xlsx` is the initial project. Its workbook contains Baseline Schedule, Resources, Risk Analysis, Project Control - TP1, TP2, TP3, and Agenda.

The adapter preserves source semantics. Baseline task durations are explicitly converted to integer CMIDO days. Precedence tokens such as `3SS` are parsed into an observed predecessor ID plus relationship type. Risk fields remain labelled as observed source values and are not silently assigned a unit or probability distribution.

## Logistics evidence

The SUCCESS bundle is retained separately because it does not contain a common project identifier with PSLIB. CMIDO therefore does not claim that a PSLIB project is the same physical project as a SUCCESS construction site. The datasets are complementary empirical evidence streams, not an artificially joined project.

The logistics gate verifies all seven public CSV tables, expected headers, documented row counts, date/numeric validity, and source SHA-256 fingerprints. The source DOI is `10.5281/zenodo.1249519`.

## Provenance rules

- `OBS`: directly represented in the public source.
- `DER`: deterministic transformation performed by CMIDO.
- `EST`: estimated/modelled quantity; must be labelled before use.
- `SCN`: controlled scenario quantity.

No missing cross-dataset relationship is fabricated.

## Execution

Run `python -m src.optimization.cmido_9b_real_project_e2e_gate` from the repository root, followed by `pytest -q tests/optimization/test_9b_real_project_e2e_gate.py`.

The gate writes a manifest, canonical PSLIB project, real-project experiment output, PSLIB audit, and logistics audit under `results/9B_real_project_e2e/`.

## Research boundary

9B is evidence of real-data ingestion and execution, not a claim that the two public datasets form one observed end-to-end procurement project. RO1/RO2/RO3 integration must use a documented mapping or remain separate. This boundary is deliberate and protects manuscript validity.

## Source references

- PSLIB / DSLIB v3.4: Batselier & Vanhoucke (2015), Construction and evaluation framework for a real-life project database, International Journal of Project Management, 33(3), 697–710. The current repository release contains 231 empirical projects.
- SUCCESS construction-logistics dataset: Zenodo DOI `10.5281/zenodo.1249519`.