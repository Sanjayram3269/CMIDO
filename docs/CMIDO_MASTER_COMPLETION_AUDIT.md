# CMIDO — Master Completion & Evidence Audit

**Audit date:** 2026-10-01  
**Repository:** `Sanjayram3269/CMIDO`  
**Audited branch:** `main`  
**Audited HEAD:** `735f779445397549fa34cda2e92cf134ca82e563`  
**Purpose:** Establish one authoritative end-to-end status record before the final UI upgrade, real-data validation, table/figure repair, repository freeze, supervisor demonstration, and journal manuscript finalization.

---

## 1. Audit principle

CMIDO is not considered complete merely because code exists or a local test passes. A stage is complete only when its implementation, focused tests, empirical outputs, documentation, provenance, and research interpretation are sufficiently traceable for the final paper.

The final evidence chain is:

```text
Claim
  ↓
Research objective
  ↓
Dataset + provenance
  ↓
Experiment configuration
  ↓
Execution
  ↓
Raw / derived result
  ↓
Statistical analysis
  ↓
Table / figure
  ↓
Paper statement
```

The project must preserve the distinction between observed (`OBS`), derived (`DER`), estimated (`EST`), and scenario-generated (`SCN`) quantities.

---

## 2. Current research identity

### Research title

**An Uncertainty-Aware Machine Learning and Multi-Objective Optimization Framework for Resilient Construction Material Procurement**

### Central research question

> Can predictive uncertainty be propagated through supply and lead-time uncertainty to produce measurably better construction-material procurement decisions?

### Scientific pipeline

```text
Historical / Observed Data
        ↓
Probabilistic Price & Demand Forecasting (RO1)
        ↓
Predictive Uncertainty
        ↓
Supply / Lead-Time Uncertainty
        ↓
Joint Uncertainty Propagation (RO2)
        ↓
Shortage / Service-Risk Distribution
        ↓
Multi-Objective Procurement Optimization (RO3)
        ↓
Quantity + Timing + Supplier Allocation + Safety Stock
        ↓
Cost–Service–Resilience Trade-offs
        ↓
Ablation + Stress Testing + Robustness Evaluation
        ↓
Decision-Level Validation
```

The intended contribution is the controlled, uncertainty-preserving **forecast → uncertainty → risk → decision** handoff, not a claim that forecasting, risk modelling, supplier selection, or optimization is individually novel.

---

# 3. Authoritative status legend

| Status | Meaning |
|---|---|
| **DONE** | Implementation and evidence are sufficiently present; only final freeze/packaging may remain. |
| **SUBSTANTIALLY DONE** | Core implementation exists, but final empirical verification, evidence packaging, or paper-level audit remains. |
| **VERIFY** | Evidence exists, but a current full-regression or end-to-end run must be executed and recorded before the stage can be frozen. |
| **PARTIAL** | Some components exist, but a material part of the planned stage is still missing. |
| **OPEN** | Planned work is not yet demonstrated in the current repository. |
| **BLOCKED** | Cannot be frozen until a named dependency is resolved. |

---

# 4. Master phase status

## 4.1 Research phases

| Phase | Scope | Current status | Remaining action |
|---|---|---|---|
| 1 | Research definition, gaps, RO1/RO2/RO3, hypotheses, provenance rules | **DONE** | Freeze wording in manuscript/specification |
| 2 | RO1 probabilistic forecasting | **SUBSTANTIALLY DONE** | Final empirical rerun + calibration/evidence/table audit |
| 3 | RO2 joint uncertainty propagation | **SUBSTANTIALLY DONE** | Final real-data validation + evidence/table audit |
| 4 | RO3 procurement optimization | **SUBSTANTIALLY DONE** | Final baseline/ablation/stress evidence + decision-value audit |
| 5 | Construction engineering foundation | **DONE** | Regression freeze |
| 6 | 7C + 7D construction integration | **DONE** | Regression freeze |
| 7 | 7E cross-domain integration | **SUBSTANTIALLY DONE** | Final integration/E2E verification |

## 4.2 8-series working roadmap

The project work after the construction/research foundation was tracked in the working 8A–8R roadmap used during development. The current repository README still contains an older coarse Phase 8/9/10/11 roadmap, so the 8A–8R labels below are the authoritative working labels for this completion audit.

| Stage | Intended scope | Current assessment | Evidence / remaining work |
|---|---|---|---|
| **8A** | Research-engineering/evidence foundation | **SUBSTANTIALLY DONE** | Core research infrastructure exists; final evidence freeze required |
| **8B** | Experiment/evaluation infrastructure | **SUBSTANTIALLY DONE** | Experiment definitions, runners, metrics and outputs exist; final rerun required |
| **8C** | RO1/RO2/RO3 evidence strengthening | **SUBSTANTIALLY DONE** | Empirical artifacts exist; final claim concordance required |
| **8D** | Controlled comparisons / robustness infrastructure | **SUBSTANTIALLY DONE** | Baseline, ablation and stress-test artifacts exist; final paper tables required |
| **8E** | Reproducibility/audit hardening | **SUBSTANTIALLY DONE** | Metadata/provenance infrastructure exists; one-command final verification remains |
| **8F** | Integrated construction/research validation | **SUBSTANTIALLY DONE** | Integration modules and tests exist; full E2E run remains |
| **8G** | Final empirical infrastructure hardening | **SUBSTANTIALLY DONE** | Current repository contains mature RO outputs; final freeze remains |
| **8H** | Canonical data/provenance work | **DONE / VERIFY** | Real-data audit artifacts exist; verify final provenance manifest |
| **8I** | Real-data normalization / admissible modelling views | **DONE / VERIFY** | RO2 raw schema, semantic audit, integrity audit and admissible modelling view exist; rerun/freeze |
| **8J** | Real-data experiment execution | **VERIFY / BLOCKED UNTIL GREEN** | Real-data execution infrastructure and results exist. Historical project checkpoint recorded 70 passed / 2 failed around a `duration` vs `duration_days` mismatch; current code contains a compatibility helper and must be rerun before declaring the stage frozen. |
| **8K** | Statistical analysis / evidence | **SUBSTANTIALLY DONE** | Statistical/evidence artifacts exist; final claim/table concordance and rerun required |
| **8L** | Interactive research dashboard | **DONE** | `apps/cmido_dashboard.py`, dashboard documentation, view-model work and dashboard contract tests exist |
| **8M** | Baselines / ablation completion | **SUBSTANTIALLY DONE / VERIFY** | Baseline and ablation outputs exist in RO3; must be consolidated into final evidence tables and rerun where required |
| **8N** | Final integrated evidence package | **PARTIAL / VERIFY** | Individual evidence exists, but a single frozen concordance package is still required |
| **8O** | Research/evidence packaging | **PARTIAL** | Final paper-facing evidence index, assumptions, limitations and provenance map remain |
| **8P** | Real-data dashboard demonstration | **OPEN / VERIFY** | Dashboard is implemented, but full real-data workflow must be demonstrated end-to-end and captured as a reproducible run |
| **8Q** | Automated/frozen tables and figures | **PARTIAL** | Results/tables/figures exist, but final source-of-truth generation and number reconciliation remain |
| **8R** | Reproducibility + final artifact package | **OPEN** | Final one-command verification, manifest, frozen outputs and release checklist remain |

## 4.3 Phase 9 — final research/journal completion

**Current status: OPEN.**

Phase 9 begins only after the empirical and artifact layers are frozen. It includes:

1. final research narrative;
2. final methods wording;
3. final results tables;
4. final figures and captions;
5. limitations and threats to validity;
6. reproducibility statement/package;
7. manuscript claim-to-evidence audit;
8. supervisor review/demo package;
9. journal-ready manuscript and supplementary material;
10. repository freeze/tag/archive.

---

# 5. What is already strong

## 5.1 Research architecture

The repository already defines a coherent uncertainty-aware procurement pipeline with RO1, RO2 and RO3. The scientific handoff is explicit rather than being a collection of unrelated ML and optimization modules.

## 5.2 RO1

The project contains probabilistic forecasting infrastructure for price and demand, including point forecasts, quantile/predictive information, evaluation metrics, calibration-oriented analysis, and experiment outputs.

Required final checks:

- forecast-origin discipline;
- no temporal leakage;
- calibration;
- coverage;
- sharpness;
- temporal/material stability;
- baseline comparison;
- final table/figure reconciliation.

## 5.3 RO2

The project contains joint uncertainty propagation infrastructure and substantial data-audit artifacts. The repository explicitly distinguishes observed, derived, estimated and scenario-generated quantities.

Required final checks:

- admissible data view frozen;
- duration/lead-time semantics explicitly documented;
- no unsupported interpretation of proxy variables;
- Monte Carlo/propagation configuration frozen;
- shortage/service-risk outputs reconciled with paper tables.

## 5.4 RO3

The project contains procurement optimization, baselines, ablation and stress/sensitivity outputs, including duration sensitivity artifacts.

Required final checks:

- deterministic/component baselines frozen;
- Pareto analysis frozen;
- ablation comparisons frozen;
- stress tests frozen;
- decision-level incremental value demonstrated rather than assumed;
- all reported numbers generated from frozen result sources.

## 5.5 Construction engineering layer

The deterministic construction layer includes project models, quantities/materials, time-phased demand, CPM, resources, procurement feasibility, delay simulation, schedule impact, risk context and cross-domain integration.

This layer should be preserved and reused rather than duplicated in the frontend.

## 5.6 Dashboard

The 8L dashboard is implemented as a Streamlit control surface over the tested CMIDO engines. Current dashboard work includes project overview, schedule/CPM, materials/resources, risk/scenarios, experiment lab, research evidence and project graph functionality.

The dashboard is **not** the final product state yet. It is the functional 8L baseline that will be upgraded into the final decision-intelligence interface after this audit.

---

# 6. Important unresolved verification items

## 6.1 8J green baseline

A historical project checkpoint recorded 70 passed / 2 failed due to a `duration` versus `duration_days` schema mismatch. The current repository contains `_activity_duration()` compatibility handling in `src/construction/experiments/dataset.py`, but this is not sufficient to claim a green frozen stage without actually executing the current full suite.

**Action:** run the complete test suite and the real-data experiment path on the current HEAD. Record exact counts and failures.

## 6.2 Full E2E path

Domain and dashboard contract tests exist, but these do not by themselves prove the full user journey:

```text
install environment
→ load real data/project
→ validate inputs
→ run RO1
→ propagate RO2
→ execute RO3
→ generate evidence
→ load results into dashboard
→ inspect decision views
→ export/freeze tables/figures
```

**Action:** create an explicit E2E test protocol and execute it on frozen inputs.

## 6.3 Table source-of-truth

The repository contains many results and table/figure artifacts. Before the manuscript is frozen, every final table must have a machine-traceable source and generation path.

**Action:** build a table concordance and regenerate final tables from source results.

## 6.4 Figure source-of-truth

The same rule applies to figures.

**Action:** map every manuscript figure to its dataset, experiment, result file and generation script.

## 6.5 Paper claim concordance

No final scientific claim should remain disconnected from an experiment/result/statistical test.

**Action:** create `docs/CMIDO_EVIDENCE_CONCORDANCE.md` after the phase audit.

## 6.6 Reproducibility freeze

The final state needs a manifest containing:

- repository commit SHA;
- Python/environment versions;
- dependency lock/version information;
- dataset identifiers/hashes where possible;
- experiment configuration;
- seeds;
- result paths;
- table/figure generation paths;
- test command and exact outcome.

---

# 7. Final work order — do not reorder

```text
CURRENT
  ↓
1. COMPLETE THIS AUDIT
  ↓
2. VERIFY 8J + FULL REGRESSION
  ↓
3. COMPLETE / FREEZE 8M–8R EVIDENCE WORK
  ↓
4. BUILD CLAIM → RESULT → TABLE/FIGURE CONCORDANCE
  ↓
5. UPGRADE THE UI END-TO-END
  ↓
6. RUN REAL-DATA END-TO-END WORKFLOW
  ↓
7. FIX / REGENERATE TABLES AND FIGURES
  ↓
8. RUN FINAL STATISTICAL + CLAIM AUDIT
  ↓
9. FREEZE CODE / DATA / RESULTS / FIGURES / TABLES
  ↓
10. PREPARE SUPERVISOR MESSAGE + GMEET DEMO
  ↓
11. FINALIZE JOURNAL MANUSCRIPT + SUPPLEMENTARY PACKAGE
  ↓
12. TAG / ARCHIVE FINAL CMIDO RELEASE
```

No cosmetic UI work should be used to hide an unresolved empirical or evidence issue.

---

# 8. Definition of “paper-ready”

CMIDO will be considered paper-ready only when all of the following are true:

- [ ] research question and contribution are frozen;
- [ ] RO1 evidence is frozen;
- [ ] RO2 evidence is frozen;
- [ ] RO3 evidence is frozen;
- [ ] baselines are frozen;
- [ ] ablations are frozen;
- [ ] stress tests are frozen;
- [ ] statistical analysis is frozen;
- [ ] all data provenance is documented;
- [ ] all assumptions are documented;
- [ ] all limitations are documented;
- [ ] all tables are regenerated from source results;
- [ ] all figures are regenerated from source results;
- [ ] every major claim maps to evidence;
- [ ] complete regression suite is green;
- [ ] real-data E2E workflow is green;
- [ ] dashboard E2E workflow is green;
- [ ] reproducibility package is executable;
- [ ] final repository state is frozen;
- [ ] manuscript and supplementary artifacts match the frozen repository.

---

# 9. Current conclusion

CMIDO is **not finished yet**, but the project is at the correct transition point: the core research/engineering system and functional dashboard exist, and the remaining work is primarily **verification, evidence consolidation, product-quality UI, real-data end-to-end validation, table/figure reconciliation, reproducibility, and final publication packaging**.

The most important immediate technical gate is the **current full regression + real-data execution on HEAD `735f779...`**, especially because an earlier 8J checkpoint had the `duration`/`duration_days` failure mode. Until that is rerun successfully, 8J and all dependent final stages must remain unfrozen.

This document is the master status record for the final CMIDO completion cycle.
