# CMIDO

## Uncertainty-Aware Construction Material Procurement & Decision Intelligence

**CMIDO** is a research-engineering framework for construction-material procurement that connects **probabilistic forecasting, uncertainty propagation, procurement optimization, and project-level construction decision intelligence**.

The central research idea is simple:

> **Do not stop at predicting what may happen. Preserve uncertainty and carry it forward until it changes a procurement decision.**

CMIDO is designed as both a research framework and an engineering system. The research pipeline targets uncertainty-aware construction-material procurement, while the construction decision layer provides a deterministic, testable environment for schedules, quantities, resources, procurement feasibility, delays, risks, and cross-domain decisions.

---

## 1. Research Identity

### Research title

**An Uncertainty-Aware Machine Learning and Multi-Objective Optimization Framework for Resilient Construction Material Procurement**

### Core scientific question

> **Can predictive uncertainty be propagated through supply and lead-time uncertainty to produce measurably better construction-material procurement decisions?**

### Core pipeline

```text
Historical / Observed Data
        ↓
Probabilistic Price & Demand Forecasting
        ↓
Predictive Uncertainty
        ↓
Supply / Lead-Time Uncertainty
        ↓
Joint Uncertainty Propagation
        ↓
Shortage / Service-Risk Distribution
        ↓
Multi-Objective Procurement Optimization
        ↓
Quantity + Timing + Supplier Allocation + Safety Stock
        ↓
Cost–Service–Resilience Trade-offs
        ↓
Ablation + Stress Testing + Robustness Evaluation
        ↓
Decision-Level Validation
```

The important scientific handoff is:

```text
Forecast → Uncertainty → Risk → Decision
```

rather than:

```text
Forecast → Point Estimate → Optimization
```

---

# 2. What CMIDO Is Trying to Contribute

Construction procurement involves several interacting sources of uncertainty:

- material prices change over time;
- future material demand is uncertain;
- supplier capacity can be constrained;
- delivery/process duration can vary;
- disruptions can reduce or delay supply;
- ordering too early can increase inventory/cost exposure;
- ordering too late can increase shortage/service risk;
- procurement policies therefore involve competing objectives.

CMIDO studies the **forecast-to-decision handoff**: whether predictive distributions can remain decision-active instead of being collapsed into a single point forecast before procurement optimization.

The project deliberately does **not** claim that forecasting, risk modelling, supplier selection, stochastic optimization, or multi-objective optimization are individually new. The research contribution is the controlled integration and empirical evaluation of these components for construction-material procurement, with explicit uncertainty provenance and decision-level validation.

---

# 3. Research Objectives

| Objective | Purpose | Main question |
|---|---|---|
| **RO1** | Probabilistic forecasting | Can construction-material price and demand be forecast accurately while retaining calibrated predictive uncertainty? |
| **RO2** | Joint uncertainty propagation | How does demand uncertainty combined with supply/lead-time uncertainty change shortage and service-risk estimates? |
| **RO3** | Procurement optimization | Does uncertainty-aware information improve cost–service–resilience procurement decisions? |

### RO1 → RO2 → RO3

```text
RO1
Probabilistic forecasts
        ↓
RO2
Joint demand + supply uncertainty
        ↓
RO3
Uncertainty-aware procurement decisions
```

A strong final result must demonstrate **incremental decision value**, not merely show that a sophisticated pipeline can be implemented.

---

# 4. Research Gaps Being Tested

## G1 — Predictive uncertainty propagation

Probabilistic forecasting already exists. CMIDO tests whether calibrated predictive distributions can be retained and propagated into construction procurement rather than discarded after forecasting.

## G2 — Joint demand and supply/lead-time uncertainty

Demand uncertainty and supply uncertainty have each been studied independently. CMIDO tests their joint effect on shortage and service risk.

## G3 — Decision-level incremental validation

The final claim is not assumed from the architecture. Controlled baselines, ablations, stress tests, and decision-level metrics are required to determine which components actually add value.

---

# 5. Experimental Data Architecture

CMIDO keeps datasets in separate empirical environments unless their constructs can be defensibly aligned.

### Dataset A — Singapore construction-material prices

Primary empirical environment for RO1 price forecasting. Monthly observations and source/provenance information are retained.

### Dataset B — Singapore construction-material demand

Primary empirical environment for RO1 demand forecasting, with monthly observations and explicit temporal coverage.

### Dataset C — SUCCESS construction logistics benchmark

Operational construction benchmark supporting RO2/RO3 experimentation. Relevant variables include construction sites, suppliers, material demand, demand periods, origin/destination relationships, distance, travel time, and transport/capacity information.

### Dataset D — Auxiliary variables

Potential economic, commodity, producer-price, transport/fuel, supplier, or product variables may be incorporated only when their construct, geography, temporal meaning, and decision relevance are defensible.

### Critical data-integrity rule

A variable must never be renamed simply because a desired model needs that variable.

For example:

```text
Observed travel time
        ≠ automatically
Historical supplier-specific procurement lead time
```

If a quantity is a proxy, estimate, or scenario assumption, it must remain labelled as such.

---

# 6. Provenance and Data Integrity

Every important variable should be traceable to one of four provenance classes:

| Label | Meaning |
|---|---|
| **OBS** | Directly observed empirical quantity |
| **DER** | Derived/calculated quantity |
| **EST** | Statistically or analytically estimated quantity |
| **SCN** | Explicit scenario-generated assumption |

Cross-dataset joins are allowed only when the following are defensible:

1. construct;
2. unit;
3. temporal meaning;
4. geographic interpretation;
5. entity linkage;
6. decision relevance.

If these conditions cannot be established, the datasets remain separate experimental environments.

---

# 7. RO1 — Probabilistic Forecasting

RO1 is responsible for producing predictive information for construction-material **price and demand**.

```text
Historical observations
        ↓
Information available at forecast origin t
        ↓
Forecasting models
        ↓
Point forecasts
+ Quantiles
+ Prediction intervals
+ Predictive samples / distributions
        ↓
Accuracy + Calibration + Sharpness
        ↓
Decision-active predictive uncertainty
```

## Forecast-origin discipline

Feature construction must obey an explicit information-set lock:

> Only information available at the forecast origin may enter the forecasting features.

Future observations must not leak into feature engineering, normalization, target construction, or model selection.

## Evaluation dimensions

Depending on the forecasting output, the evaluation should include appropriate combinations of:

- MAE;
- RMSE;
- sMAPE where appropriate;
- pinball loss;
- CRPS where supported;
- prediction-interval coverage;
- interval width / sharpness;
- calibration diagnostics;
- distributional quality;
- stability across time and material categories.

The purpose is not simply to minimize point error. RO1 must produce uncertainty information that RO2 can consume.

---

# 8. RO2 — Joint Uncertainty Propagation

RO2 connects predictive demand uncertainty with operational supply/process-duration uncertainty.

```text
RO1 predictive demand
          +
Supply / process-duration uncertainty
          +
Disruption / partial-delivery representation
          ↓
Demand during uncertain duration
          ↓
Available supply distribution
          ↓
Shortage distribution
          ↓
Shortage probability / service level
          ↓
Procurement-relevant risk information
```

The main propagation mechanism is probabilistic simulation / Monte Carlo propagation, supported by analytical checks where appropriate.

A key methodological rule is that the representation of supply duration must be honest about its source. When direct historical supplier-specific lead-time observations are unavailable, the framework must distinguish:

- observed data;
- estimated duration distributions;
- proxy variables;
- explicit scenario assumptions.

---

# 9. RO3 — Multi-Objective Procurement Optimization

RO3 converts uncertainty and risk information into procurement decisions.

Representative decision variables include:

```text
q(i,s,t)  = procurement quantity
 y(i,s,t) = order activation
ss(i,t)   = safety stock
```

The decision layer should support:

- quantity decisions;
- order timing;
- supplier allocation;
- safety-stock decisions;
- capacity constraints;
- inventory constraints;
- service requirements;
- procurement/inventory cost;
- shortage/service performance;
- resilience/risk exposure.

The research should emphasize **Pareto trade-offs** rather than relying only on one arbitrary weighted objective.

```text
             Service
                ▲
                │       Pareto-efficient
                │      ● ● ●
                │    ●
                │  ●
                └──────────────────► Cost / Risk
```

---

# 10. Controlled Evaluation Strategy

CMIDO must establish whether each major component contributes incremental value.

The core comparisons are:

```text
Point / deterministic forecasting
            vs
Probabilistic forecasting

Deterministic supply representation
            vs
Supply uncertainty

Demand-only uncertainty
            vs
Joint demand + supply uncertainty

Conventional procurement
            vs
Formal optimization

Component-wise pipeline
            vs
Integrated uncertainty-aware optimization
```

The evaluation should report not only objective values but also service, shortage, resilience, calibration, computational, and robustness metrics where applicable.

---

# 11. Robustness and Stress Testing

A strong research claim cannot depend on one nominal operating condition.

Stress tests should examine defensible variations such as:

- demand stress;
- supply-duration stress;
- disruption intensity;
- supplier-capacity constraints;
- procurement cost changes;
- service-level requirements;
- uncertainty intensity;
- combined demand/supply stress.

The purpose is to determine whether the observed decision behaviour remains stable when the environment changes.

---

# 12. Construction Decision-Intelligence Layer

Alongside RO1–RO3, CMIDO contains a deterministic construction-project engineering layer.

This layer gives the research framework an explicit project-level representation of:

- activities;
- dependencies;
- quantities;
- materials;
- schedules;
- resources;
- suppliers;
- procurement feasibility;
- delay scenarios;
- project impact;
- risk representation.

Its current role is **engineering decision infrastructure**, not a replacement for the probabilistic RO1–RO3 research pipeline.

```text
Project Data
    ↓
Validation / Domain Models
    ↓
Quantity & Material Requirements
    ↓
Time-Phased Demand
    ↓
CPM Scheduling
    ↓
Resource Analysis
    ↓
Procurement Feasibility
    ↓
Schedule-Impact Simulation
    ↓
7C Integration
    ↓
7D Risk / Uncertainty Context
    ↓
7E Cross-Domain Integration
```

---

# 13. Construction Engineering Architecture

```text
src/construction/
│
├── models/
│   ├── activity.py
│   ├── calendar.py
│   ├── dependency.py
│   ├── material.py
│   ├── progress.py
│   ├── project.py
│   ├── resource.py
│   └── supplier.py
│
├── quantity/
│   ├── demand_report.py
│   ├── procurement.py
│   ├── quantity_engine.py
│   └── time_phased.py
│
├── scheduling/
│   ├── graph.py
│   ├── topology.py
│   ├── forward_pass.py
│   ├── backward_pass.py
│   ├── float.py
│   ├── classification.py
│   └── critical_path.py
│
├── simulation/
│   ├── baseline.py
│   ├── delay.py
│   ├── float_analysis.py
│   ├── impact.py
│   └── scenario_report.py
│
├── uncertainty/
│   ├── risk.py
│   ├── scenario.py
│   └── context.py
│
├── integration/
│   ├── project_context.py
│   ├── resource_procurement.py
│   └── decision_context.py
│
├── resource_dashboard.py
├── resource_shortage.py
├── resource_allocation.py
├── resource_schedule_impact.py
├── time_phased_resources.py
├── time_phased_resource_integration.py
├── integrated_analysis.py
├── unified_dashboard.py
└── validation/
```

---

# 14. Construction Core — Implemented

## Quantity and material engine

The quantity layer validates activity-material mappings and computes:

- activity-level material requirements;
- aggregate material requirements;
- time-phased material demand;
- procurement feasibility;
- demand reports.

## CPM scheduling

The scheduling layer implements deterministic Critical Path Method analysis through:

- activity/dependency graph construction;
- topological ordering;
- forward pass;
- backward pass;
- early/late timing;
- float calculation;
- critical-path extraction;
- critical/non-critical classification.

## Delay simulation

The simulation layer can apply a deterministic activity delay without mutating the original project input, then compare baseline and scenario schedules.

It exposes:

- project duration before/after;
- project delay;
- critical path before/after;
- activity ES/EF changes;
- float changes;
- classification changes;
- affected activities.

## Resource analysis

The resource layer evaluates material/resource requirements against availability and identifies shortages and affected activities.

## Procurement feasibility

The procurement layer evaluates whether supplier capacity and lead time can support time-phased requirements.

**Feasibility is intentionally separated from optimization.** A feasible supplier allocation is not automatically claimed to be globally optimal.

---

# 15. 7C — Construction Integration

The 7C stage connects the deterministic construction domains without duplicating their underlying calculations.

## 7C-A — Project Context

Combines:

```text
Project
+ Schedule
+ Activities
+ Materials
```

The integration layer reuses the existing core analysis and scheduling engines.

## 7C-B — Resource + Procurement Context

Combines:

```text
Baseline CPM
+ Resource Availability
+ Material Requirements
+ Procurement Feasibility
```

It exposes the relationship between project schedule, available material resources, and supplier/procurement feasibility.

## 7C-C — Decision Context

Combines:

```text
Project Context
+ Resource / Procurement Context
+ Delay Scenarios
        ↓
Schedule Impact
        ↓
Project Impact
        ↓
Decision Status
```

Decision semantics are deliberately conservative:

- **FEASIBLE** — no scenario increases project duration;
- **PROJECT_DELAY** — at least one scenario increases project duration.

A delay that is completely absorbed by available activity float does not become a project-level delay.

---

# 16. 7D — Uncertainty / Risk Context

7D introduces structured project-risk representation while keeping deterministic scenario propagation separate from probabilistic research uncertainty.

```text
src/construction/uncertainty/
├── risk.py
├── scenario.py
├── context.py
└── __init__.py
```

### Current risk categories

- `SCHEDULE`
- `RESOURCE`
- `PROCUREMENT`
- `COST`
- `QUALITY`
- `SAFETY`

### Risk record

A validated risk can contain:

- risk ID;
- risk type;
- description;
- severity;
- probability field;
- impact days;
- optional activity ID;
- optional material ID.

### Important distinction

The 7D probability field is part of the **risk representation contract**. The current 7D deterministic scenario engine must not be described as Monte Carlo prediction.

When a risk targets an activity, its deterministic `impact_days` can be propagated through the existing schedule-impact engine.

The integrated context exposes:

- baseline project duration;
- baseline critical path;
- normalized risks;
- risk counts by type;
- severity counts;
- deterministic risk scenarios;
- aggregated project impact.

---

# 17. 7E — Next Integration Stage

7E is the next major construction-engineering stage.

It should **not** duplicate 7C or 7D calculations. Instead, it should create the cross-domain contract above them.

Target direction:

```text
7C-A Project Context
          +
7C-B Resource / Procurement Context
          +
7C-C Decision Context
          +
7D Risk / Uncertainty Context
          ↓
      7E Cross-Domain Context
          ↓
Unified Decision Model
```

The 7E contract should connect:

- project baseline;
- schedule state;
- resource state;
- procurement state;
- delay scenarios;
- risk scenarios;
- project-level impact;
- decision status;
- traceable scenario evidence.

The key architectural rule is **composition over duplication**: 7E should call existing deterministic domain engines and consume their contracts rather than recalculate them independently.

---

# 18. Backend Roadmap

After the domain and integration contracts stabilize, CMIDO can expose them through a backend/API layer.

Planned responsibilities:

- project ingestion;
- project validation;
- baseline analysis;
- CPM/schedule endpoints;
- resource endpoints;
- procurement-feasibility endpoints;
- delay-scenario execution;
- risk/scenario endpoints;
- integrated decision-context retrieval;
- experiment/result access where appropriate;
- reproducible execution metadata.

### Backend rule

The API must be a thin application layer over the tested domain engines.

```text
API
 ↓
Application / orchestration layer
 ↓
Existing domain engines
 ↓
Validated deterministic outputs
```

The backend must not become a second place where CPM, procurement, or risk calculations are independently implemented.

---

# 19. Frontend Roadmap

The frontend will be a decision-intelligence interface rather than a collection of unrelated charts.

Planned views include:

### Project overview

- project duration;
- project status;
- critical path;
- active constraints;
- decision summary.

### Schedule view

- activity network;
- Gantt-style schedule;
- critical/non-critical activities;
- float;
- delay scenario comparison.

### Resource view

- required quantity;
- available quantity;
- shortage quantity;
- affected activities;
- resource status.

### Procurement view

- supplier feasibility;
- capacity;
- lead time;
- required date;
- latest order date;
- procurement status.

### Risk / uncertainty view

- risk register;
- severity/type distribution;
- linked activity/material;
- scenario impact;
- project-level delay impact.

### Research view

Where appropriate, the application can expose:

- forecasting results;
- calibration diagnostics;
- shortage/service-risk distributions;
- optimization/Pareto results;
- ablation results;
- stress-test results.

The frontend remains a **presentation layer**. It should never reimplement engineering calculations in JavaScript/TypeScript.

---

# 20. Testing Philosophy

CMIDO is being built test-first at the domain-contract level.

The current construction codebase has a growing regression suite covering:

- scheduling;
- simulation;
- quantity/material logic;
- procurement feasibility;
- resource logic;
- 7C integration;
- 7D uncertainty/risk integration.

### Current checkpoint

**249 tests passed** at the latest completed 7D checkpoint.

The rule for every subsequent stage is:

```text
Existing green suite
        ↓
Add new stage
        ↓
Add focused tests
        ↓
Run full regression suite
        ↓
Only proceed with a green baseline
```

No later integration stage should be considered complete merely because its own tests pass while earlier behaviour is broken.

---

# 21. Reproducibility Principles

CMIDO follows these engineering/research rules:

1. **Deterministic core logic remains deterministic.**
2. **Scenario simulation must not silently mutate source project data.**
3. **OBS, DER, EST, and SCN provenance must remain distinguishable.**
4. **Forecasting features must obey forecast-origin information availability.**
5. **Dataset constructs must never be renamed to fit a desired hypothesis.**
6. **Existing domain engines are reused by integration layers.**
7. **Feasibility and optimization remain separate concepts.**
8. **Architecture alone is not evidence of research contribution.**
9. **Controlled comparisons are required for incremental claims.**
10. **Every new stage must preserve the previous regression suite.**
11. **Experiment configurations and reported outputs must be traceable.**
12. **Research claims must state assumptions and limitations explicitly.**

---

# 22. End-to-End Project Roadmap

CMIDO is intentionally being developed in layers.

## Phase 1 — Research definition

- research identity;
- research questions;
- research gaps;
- RO1/RO2/RO3;
- hypotheses;
- data/provenance rules;
- evaluation controls.

## Phase 2 — RO1

- data preparation;
- forecast-origin controls;
- deterministic baselines;
- probabilistic forecasting;
- uncertainty representation;
- calibration;
- forecasting evaluation;
- reproducibility/audit artifacts.

## Phase 3 — RO2

- supply/process-duration representation;
- demand-duration propagation;
- joint uncertainty simulation;
- shortage distribution;
- service probability;
- validation;
- sensitivity and audit controls.

## Phase 4 — RO3

- procurement decision variables;
- objective functions;
- constraints;
- optimization;
- Pareto analysis;
- deterministic/component baselines;
- controlled ablations;
- stress testing;
- robustness evaluation.

## Phase 5 — Construction engineering foundation

Completed core areas:

- project/domain models;
- quantity/material engine;
- time-phased demand;
- CPM scheduling;
- resource analysis;
- procurement feasibility;
- delay simulation;
- schedule-impact analysis;
- integrated construction analysis.

## Phase 6 — Construction integration

Completed:

- **7C-A** project context;
- **7C-B** resource/procurement context;
- **7C-C** decision context;
- **7D** uncertainty/risk context.

## Phase 7 — 7E

Next:

- cross-domain integration contract;
- unified construction decision context;
- scenario/risk/resource/procurement interaction;
- evidence/traceability across contexts;
- integration regression tests.

## Phase 8 — Backend

- API/application architecture;
- project ingestion;
- analysis endpoints;
- scenario execution;
- decision endpoints;
- experiment/result access;
- reproducibility metadata.

## Phase 9 — Frontend

- project dashboard;
- schedule/CPM interface;
- resource interface;
- procurement interface;
- scenario/risk interface;
- integrated decision dashboard;
- research-result visualization.

## Phase 10 — End-to-End Validation

- domain tests;
- integration tests;
- API tests;
- frontend integration tests;
- regression tests;
- reproducibility checks;
- data/provenance audit;
- failure-mode testing.

## Phase 11 — Final Research Package

- final experiments;
- ablation tables;
- stress-test tables;
- calibration plots;
- Pareto plots;
- decision-value comparisons;
- limitations;
- reproducibility package;
- manuscript figures/tables;
- final research narrative.

---

# 23. What “Strong” Means for CMIDO

The project should not be judged by the number of modules alone. Its strength should come from the chain of evidence.

A strong final CMIDO result should establish:

```text
1. The data are valid for the claimed construct.
             ↓
2. Forecasts are evaluated correctly.
             ↓
3. Predictive uncertainty is calibrated.
             ↓
4. Uncertainty is propagated without leakage.
             ↓
5. Supply uncertainty is represented honestly.
             ↓
6. Procurement decisions consume that uncertainty.
             ↓
7. Controlled baselines isolate incremental value.
             ↓
8. Stress tests examine robustness.
             ↓
9. Results are reproducible.
             ↓
10. Claims match the evidence actually produced.
```

This is more important than adding a large number of superficial features.

---

# 24. Repository Structure

```text
CMIDO/
├── data/                  # Project/data assets
├── docs/                  # Research specifications and documentation
├── environment/           # Environment/configuration assets
├── experiments/           # Experiment definitions and execution artifacts
├── figures/               # Research figures
├── results/               # Experimental outputs and audits
├── tables/                # Research tables
│
├── src/
│   └── construction/      # Current construction decision-intelligence layer
│       ├── models/
│       ├── quantity/
│       ├── scheduling/
│       ├── simulation/
│       ├── integration/
│       ├── uncertainty/
│       └── validation/
│
├── tests/
│   └── construction/      # Construction regression and integration tests
│
├── pyproject.toml
├── .gitignore
└── README.md
```

As the research and application layers mature, additional forecasting, propagation, optimization, backend, and frontend packages can be added without disturbing the existing construction-domain contracts.

---

# 25. Development Contract

Every new CMIDO stage follows the same discipline:

```text
Understand existing architecture
        ↓
Define contract
        ↓
Implement smallest correct layer
        ↓
Write focused tests
        ↓
Run full regression suite
        ↓
Inspect edge cases
        ↓
Commit only when green
        ↓
Document the stage
```

This prevents the project from becoming a collection of disconnected features.

---

# 26. Current State

At the current repository checkpoint:

- the construction domain foundation is implemented;
- CPM scheduling and critical-path analysis are implemented;
- quantity and time-phased material analysis are implemented;
- procurement feasibility is implemented;
- resource analysis is implemented;
- deterministic schedule-delay simulation is implemented;
- 7C-A, 7C-B, and 7C-C are implemented;
- 7D risk/uncertainty context is implemented;
- the regression suite has reached **249 passing tests** at the completed 7D checkpoint;
- the next construction stage is **7E cross-domain integration**;
- backend, frontend, and final end-to-end research packaging remain downstream stages.

The repository is therefore best understood as a **research + decision-engineering foundation that is being expanded toward a complete end-to-end construction procurement intelligence system**, rather than as a finished commercial application.

---

# 27. Final Architecture Vision

```text
                         CMIDO
                           │
          ┌────────────────┴────────────────┐
          │                                 │
   RESEARCH PIPELINE                 CONSTRUCTION ENGINE
          │                                 │
   ┌──────┼──────┐                 ┌────────┼─────────┐
   │      │      │                 │        │         │
  RO1    RO2    RO3              7C-A     7C-B      7C-C
   │      │      │                 │        │         │
Forecast  Joint  Multi-objective   Project  Resource  Decision
Uncertainty Propagation Procurement Context Procurement Context
   │      │      │                 │        │         │
   └──────┴──────┘                 └────────┼─────────┘
          │                                 │
          │                                7D
          │                         Risk / Uncertainty
          │                                 │
          └───────────────┬─────────────────┘
                          ↓
                         7E
                 Cross-Domain Integration
                          ↓
                  Unified Decision Model
                          ↓
                    Backend / API
                          ↓
                     Frontend UI
                          ↓
                End-to-End Validation
                          ↓
                Research Evidence Package
```

**CMIDO's long-term objective is not simply to predict construction-material behaviour. It is to build a traceable pipeline in which uncertainty survives from data and forecasting through risk propagation and finally changes an explicit procurement or project decision.**
