# CMIDO

## Uncertainty-Aware Construction Material Procurement and Decision Intelligence

**CMIDO** is a research and research-engineering framework for studying how predictive uncertainty can be propagated from construction-material forecasting through supply and lead-time uncertainty into procurement decisions, while also providing a deterministic construction-project decision layer for schedule, resource, procurement, risk, and scenario analysis.

> **Research title:** *An Uncertainty-Aware Machine Learning and Multi-Objective Optimization Framework for Resilient Construction Material Procurement*

> **Core scientific question:** Can predictive uncertainty be converted into better construction-material procurement decisions?

The project is intentionally decision-centric. It is not merely a forecasting model, risk model, or optimization algorithm. The central chain is:

```text
Observed Data
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

---

# 1. Research Identity

CMIDO is built around three scientific pillars:

### Pillar 1 — Predict

Produce probabilistic forecasts for construction-material price and demand rather than retaining only point forecasts.

### Pillar 2 — Propagate

Propagate demand uncertainty jointly with supply-side and lead-time uncertainty into shortage and service-risk estimates.

### Pillar 3 — Decide

Convert uncertainty and risk information into procurement decisions involving quantity, timing, supplier allocation, and safety stock through multi-objective optimization.

The intended contribution is the **forecast-to-decision handoff**: predictive uncertainty remains decision-active instead of being discarded after forecasting.

---

# 2. Research Problem

Construction-material procurement operates under interacting uncertainties:

- material prices change over time;
- material demand is uncertain;
- supplier delivery performance and lead times can vary;
- disruptions can reduce or delay supply;
- procurement quantities affect inventory and shortage exposure;
- procurement policies create cost, service, and resilience trade-offs.

The project does **not** claim that forecasting, supply-chain risk modelling, stochastic procurement, supplier selection, or multi-objective optimization individually do not exist.

The research focus is narrower:

> **Whether empirically grounded predictive uncertainty can be retained and propagated through supply uncertainty into procurement decisions, and whether that integration produces measurable decision value.**

---

# 3. Research Gaps

## G1 — Predictive uncertainty propagation

Probabilistic and interval forecasting exists in the literature. The research gap concerns whether calibrated predictive distributions are carried forward into construction-material procurement decisions rather than reduced to point estimates.

## G2 — Joint demand–supply / lead-time propagation

Demand uncertainty and supply-side uncertainty have each been studied in construction and supply-chain research. CMIDO studies their joint propagation into shortage and service risk.

```text
Demand Distribution
        +
Lead-Time Distribution
        +
Disruption / Partial-Delivery Uncertainty
        ↓
Demand During Uncertain Lead Time
        ↓
Available Material Distribution
        ↓
Shortage Distribution
        ↓
Service Probability
        ↓
Procurement Decision
```

## G3 — Decision-level incremental validation

The final contribution is not assumed from architecture alone. Controlled experiments isolate the value of deterministic forecasting, predictive uncertainty, supply-risk propagation, formal optimization, and their integration.

---

# 4. Research Objectives

| Objective | Purpose | Main question |
|---|---|---|
| **RO1** | Probabilistic forecasting | Do probabilistic models improve predictive accuracy, calibration, and uncertainty representation for construction-material price and demand? |
| **RO2** | Joint uncertainty propagation | How does joint demand + supply/lead-time uncertainty change shortage/service-risk estimates? |
| **RO3** | Procurement optimization | Does integrated uncertainty information improve cost–service–resilience trade-offs? |

The repository contains corresponding RO1/RO2/RO3 specifications, implementation artifacts, experiments, audits, results, and research-control documents.

---

# 5. Data Architecture

CMIDO separates empirical environments instead of forcing incompatible datasets into a single table.

## Dataset A — Singapore construction-material prices

Primary empirical environment for RO1 price forecasting. Monthly observations are used, with coverage identified from January 1999 onward through available 2026 data and source-quality flags retained where applicable.

## Dataset B — Singapore construction-material demand

Primary empirical environment for RO1 demand forecasting, with monthly observations and coverage identified through May 2026.

## Dataset C — SUCCESS construction logistics benchmark

Operational construction benchmark for RO2/RO3. Relevant information includes construction sites, suppliers, material demand, demand periods, origin/destination relationships, distance, travel time, and truck/capacity information.

**Critical data-integrity rule:** SUCCESS travel time must not automatically be renamed historical supplier-specific procurement lead time. Static supplier/catalog lead times must likewise not be presented as observed historical delivery times.

## Dataset D — Auxiliary variables

Potential auxiliary information includes economically relevant commodity, producer-price, transport/fuel, or supplier/product information only where construct, geography, temporal meaning, and decision relevance are defensible.

---

# 6. Data Provenance Rules

Every variable uses one of four provenance labels:

| Label | Meaning |
|---|---|
| **OBS** | Directly observed empirical quantity |
| **DER** | Derived/calculated quantity |
| **EST** | Statistically or analytically estimated quantity |
| **SCN** | Explicit scenario-generated assumption |

These labels must never be silently interchanged.

A cross-dataset join is allowed only when construct, unit, temporal meaning, geographic interpretation, and entity linkage are defensible. Otherwise datasets remain separate experimental environments.

---

# 7. RO1 — Probabilistic Forecasting

RO1 produces predictive information for construction-material price and demand.

```text
Historical Observations
        ↓
Information Set at Decision Time t
        ↓
Forecasting Models
        ↓
Point Forecasts + Quantiles
+ Prediction Intervals
+ Predictive Samples / Distributions
        ↓
Calibration & Accuracy Evaluation
        ↓
Decision-Active Predictive Uncertainty
```

The information set obeys a **forecast-origin lock**: only information available at the forecasting origin may enter features. Future observations must not leak into feature construction.

Representative evaluation dimensions include MAE, RMSE, sMAPE where appropriate, pinball loss, CRPS where supported, prediction-interval coverage, sharpness, and calibration diagnostics.

The downstream objective is not simply a better forecast score; the predictive distribution must remain usable by RO2 and RO3.

---

# 8. RO2 — Joint Uncertainty Propagation

RO2 converts predictive demand uncertainty and operational supply uncertainty into shortage/service-risk information.

```text
RO1 Predictive Demand
        +
Procurement-Process / Supply Duration Uncertainty
        ↓
Demand During Uncertain Lead/Process Duration
        ↓
Supply / Delivery Representation
        ↓
Shortage Distribution
        ↓
Shortage Probability
        ↓
Service Level
```

The primary propagation approach is probabilistic simulation / Monte Carlo propagation, with analytical checks where appropriate.

A key methodological constraint is that the SUCCESS benchmark must not be described as providing historical supplier-specific material lead times when the source does not establish that construct. Where direct historical evidence is unavailable, the representation is explicitly marked as an estimate, scenario, or procurement-duration proxy.

The repository contains RO2 propagation specifications, audit specifications, implementation code, validation outputs, and result summaries.

---

# 9. RO3 — Multi-Objective Procurement Optimization

RO3 consumes uncertainty-aware information and turns it into procurement decisions.

Core decision variables include:

```text
q(i,s,t)  = procurement quantity
y(i,s,t)  = order activation
ss(i,t)   = safety stock
```

The procurement policy represents quantity, timing, supplier allocation, and safety stock.

The principal trade-off structure is:

- procurement / inventory cost;
- service / shortage performance;
- resilience / risk exposure.

Pareto analysis and controlled comparisons are used so the research does not depend only on one arbitrary weighted score.

---

# 10. Controlled Research Evaluation

A strong CMIDO result must establish incremental value rather than simply report the final pipeline.

```text
Point / deterministic information
            vs
Probabilistic predictive information

Deterministic supply representation
            vs
Supply uncertainty

Demand-only uncertainty
            vs
Joint demand + supply uncertainty

Conventional procurement
            vs
Formal deterministic optimization

Component-wise pipeline
            vs
Integrated uncertainty-aware optimization
```

The repository contains controlled-baseline and ablation specifications, including the 2×2 comparison framework and controller-freeze/preflight artifacts.

---

# 11. Robustness and Stress Testing

The final research claim must not depend on one nominal scenario. Stress/robustness evaluation is intended to examine changed operating conditions, including combinations of demand stress, supply-duration stress, defensible disruption assumptions, capacity constraints, cost changes, service requirements, and uncertainty intensity.

---

# 12. Construction Decision-Intelligence Layer

Alongside RO1–RO3, CMIDO contains a deterministic construction-project engineering layer. It makes the framework operationally interpretable at project level.

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
Integrated Decision Context
   ↓
Uncertainty / Risk Context
   ↓
Future Cross-Domain Decision Layer
```

This construction layer is deterministic at its current stage. It is not presented as the probabilistic RO1–RO3 research model itself; it provides a structured project-level engineering environment that exposes schedule, resource, procurement, and risk relationships.

---

# 13. Construction Engineering Modules

### `src/construction/models/`

Project-domain representations for activities, dependencies, materials, suppliers, resources, projects, calendars, and progress.

### `src/construction/quantity/`

Activity-material requirements, aggregate demand, time-phased demand, procurement feasibility, and demand reporting.

### `src/construction/scheduling/`

Deterministic CPM functionality: graph construction, topological ordering, forward pass, backward pass, float, critical path, and critical/non-critical classification.

### `src/construction/simulation/`

Baseline schedules, activity-delay simulation, schedule-impact propagation, float analysis, and scenario reporting. Scenario simulation preserves the original project input.

### Resource layer

Resource requirements, availability, allocation, shortages, affected activities, and time-phased resource information.

### Procurement layer

Supplier-capacity and lead-time feasibility against time-phased material requirements. Feasibility is deliberately distinguished from optimization.

### Integration layer

#### 7C-A — Project Context

Integrates baseline project, CPM schedule, activities, and material information.

#### 7C-B — Resource + Procurement Context

Integrates baseline scheduling with resource availability and procurement feasibility.

#### 7C-C — Decision Context

Combines project, resource/procurement, delay scenarios, schedule impact, project-level impact, and deterministic decision status. A non-critical delay absorbed by available float does not automatically become a project delay.

---

# 14. 7D — Uncertainty / Risk Context

The 7D layer introduces structured construction-risk representation without treating deterministic risk records as probabilistic predictions.

```text
src/construction/uncertainty/
├── risk.py
├── scenario.py
├── context.py
└── __init__.py
```

Current risk categories include **SCHEDULE, RESOURCE, PROCUREMENT, COST, QUALITY, SAFETY**. Risk records contain validated identity, type, description, severity, probability, impact days, and optional activity/material linkage.

A risk targeting an activity can reuse the schedule-impact engine to propagate its deterministic impact through the project network.

The integrated 7D context exposes baseline duration, critical path, normalized risks, risk summary, deterministic scenarios, and aggregated project impact.

**Important:** 7D is not claimed to be Monte Carlo risk prediction. Probabilistic research uncertainty belongs to the RO1–RO3 research pipeline. The construction 7D layer provides controlled project-risk representation and a deterministic scenario bridge.

---

# 15. Current Implementation Status

| Area | Status |
|---|---|
| Research master specification | Present |
| RO1 specification/artifacts | Present |
| RO2 propagation + audit artifacts | Present |
| RO3 optimization + controlled evaluation artifacts | Present |
| Construction domain models | Implemented |
| Quantity/material engine | Implemented |
| CPM scheduling | Implemented |
| Delay simulation | Implemented |
| Resource analysis | Implemented |
| Procurement feasibility | Implemented |
| 7C-A project context | Implemented |
| 7C-B resource/procurement context | Implemented |
| 7C-C decision context | Implemented |
| 7D uncertainty/risk context | Implemented |
| 7E | Next implementation stage |
| Backend/API serving layer | Planned |
| Frontend | Planned |
| End-to-end application integration | Planned |
| Final research evaluation/reporting package | Ongoing / to be consolidated |

At the latest local checkpoint before this README update, the construction test suite was green with **249 passing tests**. New work must preserve that green baseline.

---

# 16. End-to-End Roadmap

The project is developed in controlled stages rather than building a frontend first and retrofitting research logic later.

## Stage 1 — Research specification and evidence control

Research identity, G1–G3, RO1–RO3, RQs, hypotheses, data provenance, dataset compatibility, and experimental controls.

## Stage 2 — RO1

Data preparation, forecast-origin controls, baseline forecasting, probabilistic forecasting, calibration, predictive-distribution outputs, evaluation, and audit artifacts.

## Stage 3 — RO2

Supply/process-duration representation, demand-duration propagation, joint uncertainty propagation, shortage/service-risk estimation, validation/audit, and sensitivity analysis.

## Stage 4 — RO3

Procurement decision model, objectives, constraints, optimization, Pareto decision layer, deterministic/component-wise baselines, controlled ablations, and stress/robustness evaluation.

## Stage 5 — Construction decision engine

Completed through the current 7D checkpoint: project representation, quantity/material engine, CPM, resources, procurement feasibility, schedule simulation, 7C-A, 7C-B, 7C-C, and 7D uncertainty/risk context.

## Stage 6 — 7E and higher integration

Connect the existing contexts without duplicating domain logic. The exact 7E contract will be defined against the repository architecture before implementation.

```text
7C-A Project Context
        +
7C-B Resource / Procurement Context
        +
7C-C Decision Context
        +
7D Uncertainty / Risk Context
        ↓
7E Cross-Domain Integration
        ↓
Application / API-ready Decision Model
```

## Stage 7 — Backend

Project ingestion, validation, analysis endpoints, scenario execution, decision-context retrieval, risk/scenario APIs, appropriate experiment/result access, and reproducible execution. The backend must call domain engines rather than duplicate calculations.

## Stage 8 — Frontend

Planned views: project overview, CPM/critical path, activity schedule, resource availability/shortages, procurement feasibility, delay scenarios, risk register, uncertainty/scenario impact, integrated decision dashboard, and appropriate research-result visualization.

The frontend is a presentation layer, not a second implementation of engineering logic.

## Stage 9 — End-to-End Validation and Research Packaging

Unit/integration tests, API tests, frontend integration tests, reproducibility checks, experiment manifests, final tables/figures, ablations, stress tests, limitations, provenance audit, and manuscript-ready research narrative.

---

# 17. Reproducibility Principles

1. **Deterministic core logic remains deterministic.**
2. **Scenario simulation does not silently mutate source project data.**
3. **OBS, DER, EST, and SCN values remain distinguishable.**
4. **Future information cannot leak into forecasting features.**
5. **Dataset constructs are never renamed merely to fit a desired model.**
6. **Existing engines are reused instead of duplicated in integration layers.**
7. **Every major component has an evaluation path.**
8. **Research claims require controlled comparisons, not architecture diagrams alone.**
9. **Every new stage must preserve all previously passing tests.**
10. **Research artifacts, code, experiments, and reported results remain traceable.**

---

# 18. Repository Structure

```text
CMIDO/
│
├── docs/                  # Research specifications, audits and control documents
├── data/                  # Data/project assets
├── environment/           # Environment/configuration assets
├── experiments/           # Experiment definitions and execution artifacts
├── figures/               # Research figures
├── results/               # Experimental outputs and audits
├── tables/                # Research tables
│
├── src/
│   ├── forecasting/       # RO1 forecasting
│   ├── propagation/       # RO2 propagation
│   ├── supply_risk/       # Supply/lead-time risk
│   ├── optimization/      # RO3 procurement optimization
│   ├── uncertainty/       # Research uncertainty utilities
│   ├── evaluation/        # Evaluation infrastructure
│   ├── data/              # Data processing utilities
│   ├── utils/             # Shared utilities
│   │
│   └── construction/      # Construction decision-intelligence layer
│       ├── models/
│       ├── quantity/
│       ├── scheduling/
│       ├── simulation/
│       ├── uncertainty/
│       ├── validation/
│       └── integration/
│
├── tests/                 # Automated tests
└── pyproject.toml         # Python project configuration
```

---

# 19. Architectural Separation

CMIDO intentionally separates three levels.

### Research layer

RO1–RO3 answer scientific questions using empirical data, probabilistic forecasting, uncertainty propagation, optimization, controlled ablations, and robustness evaluation.

### Engineering decision layer

Construction modules provide deterministic project-level representations of schedule, quantity, resource, procurement, delay, and risk relationships.

### Application layer

The future backend/frontend exposes validated engineering and research capabilities without duplicating domain logic.

This separation supports both scientific traceability and software maintainability.

---

# 20. Scientific Guardrails

CMIDO should not make unsupported claims that:

- probabilistic construction forecasting is itself new;
- no prior work combines uncertainty and procurement;
- SUCCESS contains historical supplier-specific lead times unless the data establish that construct;
- a deterministic scenario engine is a probabilistic risk predictor;
- a single optimization run proves superiority;
- a model is superior without controlled baselines and appropriate evaluation;
- incompatible datasets can be merged simply because a variable is needed.

The final novelty claim remains conditional on a formal database-level systematic literature review, consistent with the research master specification.

---

# 21. Development Workflow

From the repository root:

```powershell
.venv\Scripts\Activate.ps1
python -m pytest -q
git status
git log --oneline -15
```

Every implementation stage follows:

```text
Define contract
    ↓
Implement domain logic
    ↓
Write focused tests
    ↓
Run focused tests
    ↓
Run complete suite
    ↓
Inspect git diff/status
    ↓
Commit
    ↓
Push
```

A new stage is not accepted merely because its own tests pass; the full regression suite must remain green.

---

# 22. Research-to-Application Vision

```text
                    CMIDO
                      │
        ┌─────────────┴─────────────┐
        │                           │
   RESEARCH ENGINE             PROJECT ENGINE
        │                           │
       RO1                    Schedule / CPM
        │                    Quantity / Materials
       RO2                    Resources
        │                    Procurement
       RO3                    Delay Simulation
        │                    Risk / Uncertainty
        └─────────────┬─────────────┘
                      │
              CROSS-DOMAIN LAYER
                      │
              Decision Context
                      │
                 Backend API
                      │
                Web Frontend
                      │
            Human Decision Support
```

The system supports human decision-making rather than replacing human judgement. Outputs should expose assumptions, uncertainty, constraints, trade-offs, and scenario consequences.

---

# 23. What Makes the Framework Scientifically Defensible

The intended strength of CMIDO is not the number of modules alone. It comes from the chain of evidence:

```text
Research Gap
   ↓
Research Objective
   ↓
Research Question
   ↓
Hypothesis
   ↓
Data Provenance
   ↓
Controlled Method
   ↓
Calibrated Uncertainty
   ↓
Propagation
   ↓
Optimization
   ↓
Ablation
   ↓
Stress / Robustness
   ↓
Decision-Level Evaluation
   ↓
Limitations + Reproducibility
```

Every major claim should be traceable through that chain.

---

# 24. Next Development Rule

The repository is currently at a clean checkpoint after the 7D uncertainty/risk integration. The next implementation stage is **7E**.

Before implementing 7E, its exact contract will be defined against the existing architecture. The objective is to extend CMIDO without breaking the currently validated layers.

**Current rule: preserve the green baseline, reuse existing engines, avoid duplicated logic, and make every new integration testable.**
