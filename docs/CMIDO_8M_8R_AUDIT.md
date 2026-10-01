# CMIDO — 8M–8R Evidence-Based Audit

**Audit date:** 2026-10-01  
**Branch:** `main`  
**Purpose:** Correctly establish what is and is not present after 8L before implementing the remaining completion stages.

## Executive finding

The current `main` branch contains concrete implementation and commits through **8L**, followed by the documentation/audit commits created during the current completion cycle.

A repository commit search for the labels **8M, 8N, 8O, 8P, and 8Q** returned no matching implementation commits. A search for **8L** returns the actual dashboard implementation, dashboard contract tests, and dashboard documentation commits. Therefore, the later 8M–8R stages must **not** be marked as already implemented merely because they existed in the working roadmap or previous planning discussion.

This is an important correction to keep the journal evidence trail honest.

## Verified sequence

### 8J — Real-data execution

Verified implementation commits exist:

- `cf16143` — `feat: add 8J real dataset experiment runner`
- `5d6c16c` — `chore: export 8J real dataset execution APIs`
- `b5455cb` — `test: add 8J real dataset execution contracts`
- `8568e5e` — `fix: accept CMIDO duration_days in 8J dataset validation`
- `5154558` — `fix: normalize raw project datasets for 8J execution`

**Current status:** implementation exists; local full regression is now green at **340 passed, 0 failed**. A dedicated full real-data experiment run still needs to be executed and recorded before 8J is frozen as an empirical result stage.

### 8K — Statistical evidence

Verified implementation commits exist:

- `7c9f3ec` — `feat: add 8K statistical evidence analysis`
- `ea00dbc` — `test: add 8K statistical evidence contracts`
- `0a9859f` — `chore: export 8K statistical analysis APIs`
- `20dcd63` — `feat: integrate 8K statistics with real-data runner`
- `19e16b4` — `chore: export real-data 8K statistical runner`
- `8c56a8f` — `test: add 8K real-data statistical integration`

**Current status:** implementation + tests verified; final real-data execution, evidence reconciliation and manuscript table/figure freeze remain.

### 8L — Interactive research dashboard

Verified implementation commits exist:

- `8024ba1` — `feat: complete 8L interactive research dashboard`
- `4ca0514` — `test: strengthen 8L dashboard contracts`
- `4f70bfc` — `docs: document 8L interactive research dashboard`

The dashboard is therefore **genuinely implemented**, not merely planned. The current local regression confirms the dashboard contract suite is green as part of the **340/340** total.

## 8M

**Status: NOT IMPLEMENTED AS A DISTINCT REPOSITORY STAGE YET.**

The earlier working roadmap described 8M as the next evidence/baseline-ablation completion stage. However, there is no 8M-labelled implementation commit on `main`.

### Required 8M work

1. Inventory all existing baseline outputs.
2. Inventory all existing ablation outputs.
3. Define the exact comparison populations/configurations.
4. Identify any missing baseline/ablation runs.
5. Run missing real-data experiments.
6. Generate final machine-derived comparison tables.
7. Link every result to a claim in the evidence concordance.
8. Freeze the resulting evidence package.

**Gate:** no 8M completion claim until the above is executed and locally verified.

## 8N

**Status: NOT IMPLEMENTED AS A DISTINCT REPOSITORY STAGE YET.**

### Required 8N work

Build the integrated evidence package connecting:

```text
RO1 → RO2 → RO3
   +
baselines
   +
ablations
   +
stress tests
   +
statistical evidence
```

The package must identify the exact result artifacts and configurations used by each final claim.

## 8O

**Status: NOT IMPLEMENTED AS A DISTINCT REPOSITORY STAGE YET.**

### Required 8O work

Create the paper-facing evidence package:

- assumptions;
- data provenance;
- admissible modelling views;
- limitations;
- threats to validity;
- experiment registry;
- claim register;
- table register;
- figure register;
- reproducibility notes.

## 8P

**Status: NOT IMPLEMENTED AS A DISTINCT REPOSITORY STAGE YET.**

The dashboard exists, but that is not equivalent to an 8P real-data demonstration.

### Required 8P work

Execute and document:

```text
real dataset/project
→ validation
→ RO1
→ RO2
→ RO3
→ evidence/statistics
→ dashboard
→ decision interpretation
```

The run must be reproducible from a documented configuration and seed.

## 8Q

**Status: NOT IMPLEMENTED AS A DISTINCT REPOSITORY STAGE YET.**

### Required 8Q work

Create the final publication artifact generation layer:

- tables generated from frozen result sources;
- figures generated from frozen result sources;
- numerical reconciliation checks;
- consistent units and rounding;
- captions and interpretation;
- source metadata for every artifact.

## 8R

**Status: NOT IMPLEMENTED AS A DISTINCT REPOSITORY STAGE YET.**

### Required 8R work

Final reproducibility/freeze package:

- repository SHA;
- environment/dependency specification;
- dataset/provenance manifest;
- experiment configuration registry;
- seeds;
- result manifest;
- table/figure manifest;
- complete regression command and output;
- real-data E2E command and output;
- final release checklist.

## Current phase gate

The correct next stage is therefore **8M**, not UI redesign yet.

```text
340/340 local regression GREEN
        ↓
8J real-data execution verification
        ↓
8K evidence verification
        ↓
8M baseline + ablation completion
        ↓
8N integrated evidence
        ↓
8O paper evidence package
        ↓
8P real-data dashboard E2E
        ↓
8Q tables + figures
        ↓
8R reproducibility freeze
        ↓
UI finalization / product polish
        ↓
Phase 9 manuscript + supervisor review + submission
```

## Evidence policy

A roadmap label in conversation or planning notes is **not** treated as implementation evidence. Only repository code, tests, generated artifacts, commit history, and reproducible execution results can move a stage to DONE.

This document supersedes any earlier speculative classification of 8M–8R as already completed.
