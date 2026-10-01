# CMIDO — Evidence Concordance

**Status:** Working audit scaffold  
**Purpose:** Map every paper-level claim to its research objective, dataset, experiment, result, statistical analysis, table/figure, and manuscript location.

This document becomes mandatory before the final repository/manuscript freeze.

---

## 1. Claim-to-evidence chain

```text
Paper claim
   ↓
Research objective (RO1 / RO2 / RO3)
   ↓
Dataset + provenance
   ↓
Experiment ID / configuration
   ↓
Seed / evaluation population
   ↓
Raw or derived result
   ↓
Statistical analysis
   ↓
Table / figure
   ↓
Manuscript section
```

---

## 2. Evidence rules

1. No numerical claim without a traceable result source.
2. No table number should be manually maintained when it can be generated from frozen results.
3. No figure should be manually edited in a way that changes quantitative content.
4. Every uncertainty quantity must retain provenance (`OBS`, `DER`, `EST`, `SCN`).
5. Baselines must use the same evaluation population and clearly documented information set.
6. Ablation claims must identify the component removed and the resulting change.
7. Stress-test claims must identify the stress condition and its parameterization.
8. Statistical claims must identify the test, population, effect size where applicable, and uncertainty interval where applicable.
9. Dashboard values must trace back to the same frozen result sources as the paper.
10. Final manuscript values must be regenerated after the final empirical freeze.

---

## 3. Research-objective map

| Objective | Core question | Required evidence |
|---|---|---|
| RO1 | Can probabilistic price/demand forecasts retain useful calibrated uncertainty? | Forecast metrics, calibration, coverage, sharpness, temporal/material stability, baseline comparisons |
| RO2 | What changes when demand uncertainty is propagated jointly with supply/process-duration uncertainty? | Propagation configuration, shortage/service distributions, sensitivity/stress tests, provenance audit |
| RO3 | Does uncertainty-aware information improve procurement decisions? | Baselines, optimization/Pareto outputs, ablations, stress tests, decision-level metrics |

---

## 4. Master claim register

| Claim ID | Draft claim | RO | Dataset | Experiment | Result source | Statistical evidence | Table | Figure | Manuscript section | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| C-RO1-001 | TBD | RO1 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OPEN |
| C-RO1-002 | TBD | RO1 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OPEN |
| C-RO2-001 | TBD | RO2 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OPEN |
| C-RO2-002 | TBD | RO2 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | OPEN |
| C-RO3-001 | TBD | RO3 | TBD | TBD | TBD | TBD | TBD | TBD | OPEN |
| C-RO3-002 | TBD | RO3 | TBD | TBD | TBD | TBD | TBD | TBD | OPEN |
| C-INT-001 | TBD | RO1→RO2→RO3 | TBD | TBD | TBD | TBD | TBD | TBD | OPEN |
| C-ROB-001 | TBD | RO2/RO3 | TBD | TBD | TBD | TBD | TBD | TBD | OPEN |

---

## 5. Final table register

| Table ID | Purpose | Source result(s) | Generation script | Last generated commit | Paper section | Status |
|---|---|---|---|---|---|---|
| T1 | RO1 main forecasting comparison | TBD | TBD | TBD | TBD | OPEN |
| T2 | RO1 calibration/uncertainty evidence | TBD | TBD | TBD | TBD | OPEN |
| T3 | RO2 propagation main result | TBD | TBD | TBD | TBD | OPEN |
| T4 | RO2 sensitivity/stress | TBD | TBD | TBD | TBD | OPEN |
| T5 | RO3 baseline comparison | TBD | TBD | TBD | TBD | OPEN |
| T6 | RO3 ablation | TBD | TBD | TBD | TBD | OPEN |
| T7 | RO3 stress/robustness | TBD | TBD | TBD | TBD | OPEN |
| T8 | Integrated decision-value evidence | TBD | TBD | TBD | TBD | OPEN |

---

## 6. Final figure register

| Figure ID | Purpose | Source result(s) | Generation script | Last generated commit | Paper section | Status |
|---|---|---|---|---|---|---|
| F1 | RO1 forecast / uncertainty visualization | TBD | TBD | TBD | TBD | OPEN |
| F2 | RO1 calibration diagnostic | TBD | TBD | TBD | TBD | OPEN |
| F3 | RO2 shortage/service-risk distribution | TBD | TBD | TBD | TBD | OPEN |
| F4 | RO2 uncertainty propagation / sensitivity | TBD | TBD | TBD | TBD | OPEN |
| F5 | RO3 Pareto frontier | TBD | TBD | TBD | TBD | OPEN |
| F6 | RO3 baseline/ablation comparison | TBD | TBD | TBD | TBD | OPEN |
| F7 | Integrated forecast→uncertainty→risk→decision pipeline | TBD | TBD | TBD | TBD | OPEN |

---

## 7. E2E demonstration register

| Demo step | Input | Engine | Expected output | Evidence path | Status |
|---|---|---|---|---|---|
| D1 | Frozen dataset/project | Ingestion + validation | Validated modelling input | TBD | OPEN |
| D2 | Validated RO1 data | Forecasting | Point + predictive uncertainty | TBD | OPEN |
| D3 | RO1 uncertainty + supply/process duration | RO2 propagation | Shortage/service-risk distribution | TBD | OPEN |
| D4 | RO2 risk + procurement inputs | RO3 optimization | Procurement decisions/Pareto set | TBD | OPEN |
| D5 | Frozen outputs | Dashboard | Decision-intelligence views | TBD | OPEN |
| D6 | Frozen outputs | Table/figure generation | Publication artifacts | TBD | OPEN |

---

## 8. Freeze checklist

- [ ] Every final claim has an evidence row.
- [ ] Every numerical claim has a result source.
- [ ] Every result has a dataset and configuration.
- [ ] Every statistical statement identifies its analysis.
- [ ] Every final table is reproducible.
- [ ] Every final figure is reproducible.
- [ ] Dashboard values agree with frozen result sources.
- [ ] Manuscript and supplementary files match frozen values.
- [ ] Final commit SHA is recorded.
- [ ] Final environment/dependency information is recorded.
- [ ] Final dataset/provenance manifest is recorded.
