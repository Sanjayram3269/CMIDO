CMIDO --- FINAL RESEARCH MASTER SPECIFICATION v1.0

Working title:
An Uncertainty-Aware Machine Learning and Multi-Objective Optimization
Framework for Resilient Construction Material Procurement

Project identity: Decision-centric uncertainty propagation for
resilient construction-material procurement.

Status: Research architecture, mathematical formulation, data
architecture, and experimental design frozen for implementation
planning.
Critical caveat: the three candidate research gaps are provisionally
frozen from the current evidence audit, but the final novelty claim
remains conditional on formal database-level systematic
literature-review screening.

1. Research identity

1.1 Central scientific question

Can predictive uncertainty be converted into better
construction-material procurement decisions?

The project is not primarily an exercise in developing a new forecasting
algorithm or a new optimization algorithm. Its scientific focus is the
decision-centric propagation of predictive uncertainty from
construction-material forecasting through supply-risk modelling into
procurement optimization.

1.2 Core chain

Observed data
    ↓
Predictive intelligence
    ↓
Probabilistic price and demand forecasts
    ↓
Supply / lead-time uncertainty
    ↓
Joint uncertainty propagation
    ↓
Shortage / service-risk distribution
    ↓
Multi-objective procurement optimization
    ↓
Quantity + timing + supplier allocation + safety stock
    ↓
Realized / simulated cost–service–resilience outcomes
    ↓
Ablation + stress + robustness evaluation

1.3 Three scientific pillars

Pillar 1 --- Predict

Probabilistic forecasting of construction-material price and demand.

Pillar 2 --- Propagate

Jointly propagate demand uncertainty with supply/lead-time uncertainty
into shortage and service risk.

Pillar 3 --- Decide

Convert the resulting uncertainty and risk information into procurement
quantity, timing, supplier-allocation, and safety-stock decisions
through multi-objective optimization.

2. Problem statement

Construction-material procurement decisions are made under several
interacting uncertainties. Material prices vary over time; material
demand/consumption is uncertain; supplier delivery performance and lead
times may vary; disruptions can reduce or delay supply; and procurement
decisions affect inventory, shortage, excess material, cost, and
project-service outcomes.

Existing research contains substantial work on construction-material
price forecasting, demand forecasting, construction supply-chain risk,
uncertain lead times, stochastic/robust procurement, supplier selection,
and multi-objective optimization. These are not individually claimed as
novel by CMIDO.

The research problem is narrower:

Predictive information is not necessarily retained and propagated in
a decision-active form from forecasting through supply uncertainty and
into construction-material procurement decisions.

The study therefore asks whether predictive distributions, rather than
only point forecasts, create measurable incremental value when
transformed into shortage/service risk and consumed by a procurement
decision model.

3. Research aim

To develop and evaluate an uncertainty-aware machine-learning and
multi-objective optimization framework that propagates predictive
construction-material price and demand uncertainty together with
supply/lead-time uncertainty into procurement decisions, with the
objective of improving cost--service--resilience trade-offs.

4. Research gaps

G1 --- Predictive uncertainty propagation

Refined gap

Although construction-material price and demand forecasting increasingly
incorporates probabilistic or interval-based prediction, and procurement
studies increasingly incorporate uncertainty, the direct propagation of
empirically calibrated predictive distributions into downstream
construction-material procurement decisions remains insufficiently
established.

Scientific question

Does retaining predictive uncertainty from construction-material price
and demand forecasting improve procurement decisions compared with
equivalent point forecasts?

Boundary

Do not claim that probabilistic construction forecasting does not
exist. The gap concerns the forecast-to-decision handoff.

G2 --- Joint demand--supply/lead-time propagation into shortage/service risk

Refined gap

Existing construction procurement studies model demand uncertainty and
supply-side uncertainty, including lead-time variability and disruption,
in various forms. Their joint propagation into a decision-dependent
shortage/service-risk distribution remains insufficiently established.

Scientific mechanism

Demand distribution
       +
Lead-time distribution
       +
Disruption / partial-delivery uncertainty
       ↓
Demand during uncertain lead time
       ↓
Available-material distribution
       ↓
Shortage distribution
       ↓
Service probability
       ↓
Procurement decision

This is not a separate shortage classifier. Shortage is primarily
treated as a derived consequence of interacting uncertainties.

G3 --- Decision-level incremental validation

Refined gap

Whether predictive uncertainty creates additional procurement decision
value is not sufficiently isolated through controlled component-level
and decision-level comparisons.

Scientific question

How much of the final procurement improvement comes from forecasting
uncertainty, formal optimization, and their integration?

This gap is tested through controlled ablation rather than assumed.

5. Research objectives

RO1 --- Probabilistic forecasting

To develop and evaluate probabilistic forecasting models for
construction-material price and demand, producing calibrated
predictive distributions for downstream procurement decision-making.

RQ1

To what extent do probabilistic machine-learning forecasting models
improve predictive accuracy, calibration and uncertainty
representation for construction-material price and demand compared
with statistical and point-forecast baselines?

H1

Probabilistic ML forecasting models provide superior or more
informative predictive performance and uncertainty calibration than
deterministic statistical and point-forecast baselines for
construction-material price and demand.

RO2 --- Joint uncertainty propagation

To develop a joint uncertainty-propagation mechanism that combines
predictive demand uncertainty with supplier/lead-time uncertainty to
quantify construction-material shortage and service risk.

RQ2

How does jointly propagating demand and supply/lead-time uncertainty
affect construction-material shortage and service-risk estimates
compared with deterministic, demand-only and supply-only
representations?

H2

Joint propagation of predictive demand uncertainty and
supply/lead-time uncertainty produces materially different and more
reliable shortage/service-risk estimates than deterministic or
single-source uncertainty representations.

RO3 --- Procurement decision optimization

To develop and evaluate an uncertainty-aware multi-objective
construction-material procurement optimization framework that converts
predictive and supply-risk information into procurement quantity,
timing, supplier-allocation and safety-stock decisions.

RQ3

Does integrating predictive uncertainty and joint supply-risk
information into procurement optimization produce superior
cost--service--resilience trade-offs compared with deterministic and
component-wise procurement approaches?

H3

Procurement policies using probabilistic predictive information and
joint supply-risk propagation achieve more favorable
cost--service--resilience trade-offs than deterministic and
component-wise alternatives under normal and stressed conditions.

6. Gap → objective → RQ → method alignment

Gap                        Objective   RQ          Main method        Main output             Main
evaluation

G1 Predictive uncertainty  RO1         RQ1         Statistical + ML   Price/demand predictive MAE, RMSE,
propagation                                        point +            distributions           sMAPE,
probabilistic                              pinball, CRPS,
forecasting                                PICP,
sharpness

G2 Joint                   RO2         RQ2         Probabilistic      Shortage/service-risk   Risk
demand--supply/lead-time                           supply             distribution            estimates,
propagation                                        representation +                           shortage
Monte                                      probability,
Carlo/analytical                           expected
propagation                                shortage,
service

No major component should exist without an objective and evaluation
path.

7. Scope

7.1 Domain

Construction-material procurement and associated construction
supply-chain decisions.

7.2 Primary forecasting environment

Singapore construction-material market data are the primary empirical
environment for price and demand forecasting.

The study must not be described as an Indian empirical model unless
compatible Indian project/procurement data are obtained.

7.3 Operational procurement environment

The SUCCESS construction logistics dataset is used as an operational
construction benchmark/simulation environment.

It provides construction sites, suppliers, material demand,
transport/logistics structure, distances/travel times and truck/capacity
information.

7.4 Explicit data limitation

SUCCESS travel time must not be relabelled as historical procurement
lead time.

Likewise, static supplier/catalog lead times must not be represented as
realized historical delivery lead times.

7.5 Data integration rule

Datasets are not merged merely because a mathematical variable is
missing.

A cross-dataset join is admissible only when:

construct is compatible,

unit is compatible,

temporal meaning is compatible,

geographic interpretation is compatible,

entity linkage is defensible.

Otherwise the datasets remain separate experimental environments.

8. Data provenance taxonomy

Every variable receives one of four labels.

Label   Definition           Interpretation

OBS     Directly observed    Empirical observation
DER     Derived              Calculated from observed/estimated quantities
EST     Estimated            Statistically or analytically estimated
SCN     Scenario-generated   Explicit experimental assumption

Hard rule

OBS, DER, EST and SCN must never be silently interchanged.

9. Data architecture

Dataset A --- Singapore construction-material prices

Role: Primary empirical RO1 dataset.

Core variable:

[ P_{i,t} ]

Status:

OBS

Resolution:

Monthly.

Coverage currently identified:

January 1999 onward through the available 2026 data.

COVID-period data-quality flags must be retained where the source
indicates unchanged/assumed prices.

Dataset B --- Singapore construction-material demand

Role: Primary empirical RO1 dataset.

Core variable:

[ D_{i,t} ]

Status:

OBS

Resolution:

Monthly.

Coverage currently identified:

January 1999 through May 2026.

Dataset C --- SUCCESS construction logistics

Role: Operational construction benchmark for RO2/RO3.

Relevant fields include:

construction sites,

supplier information,

material demand,

weekly material-demand periods,

origin/destination,

distance,

travel time,

truck capacity.

Use:

construction network structure,

supplier/site relationships,

operational demand,

transport/logistics constraints,

scenario/simulation environment.

Do not represent it as a complete historical procurement-order/delivery
dataset.

Dataset D --- Auxiliary data

Potential auxiliary sources:

economically relevant commodity indicators,

producer-price indicators,

transport/fuel indicators,

static supplier/product catalog information.

Use only when the construct, geography, temporal meaning and
causal/decision relevance are defensible.

10. Data-status audit

Variable                                Current status            Main role

Material price (P)                      OBS                       RO1
Material demand (D)                     OBS                       RO1
Predictive price distribution (F^P)    DER/EST                   RO1 → RO3
Predictive demand distribution (F^D)   DER/EST                   RO1 → RO2/RO3
Supplier identity                       OBS                       RO3
Site identity                           OBS                       RO3
Material demand in SUCCESS              OBS                       RO3
Distance                                OBS                       RO3
Travel time                             OBS                       operational/logistics
Truck capacity                          OBS                       RO3
Supplier capacity                       DER/EST/SCN               RO3
MOQ                                     EST/SCN unless verified   RO3
Procurement lead time                   OPEN / EST / SCN          RO2
Disruption probability                  OPEN / EST / SCN          RO2
Partial delivery (\eta{=tex})         EST/SCN                   RO2
Historical inventory                    OPEN                      RO3
Historical purchase price               OPEN                      RO3
Historical shortage                     OPEN                      RO2
Shortage probability                    DER                       RO2/RO3
Service level                           DER                       RO2/RO3
Safety-stock benchmark                  DER                       RO3
Risk exposure                           DER/EST                   RO3
Cost parameters                         EST/SCN where necessary   RO3

11. Theoretical methodology

Stage 1 --- Information layer

At decision time (t):

[ X_t = {X_t^P,X_t^D,X_t^E,X_t^S,X_t^L,X_t^I,X_t^C} ]

Only information available by time (t) may be used.

No future observations may enter feature construction.

Stage 2 --- Price forecasting

For material (i):

[ P_{i,t+h}\mid {=tex}X_t\sim {=tex}F^P_{i,t+h} ]

The model produces:

point estimate,

quantiles,

prediction intervals,

predictive samples/distribution.

Stage 3 --- Demand forecasting

[ D_{i,t+h}\mid {=tex}X_t\sim {=tex}F^D_{i,t+h} ]

The predictive distribution, not only the point forecast, is retained
for downstream use.

Stage 4 --- Supply uncertainty

Lead time:

[ L_{i,s,t}\mid {=tex}X_t^S\sim {=tex}F^L_{i,s,t} ]

Disruption:

[ Z_{i,s,t}\in{=tex}{0,1} ]

[ P(Z_{i,s,t}=1\mid {=tex}X_t^S)=p^{dis}_{i,s,t} ]

Partial delivery:

[ \eta{=tex}_{i,s,t}\in[0,1]{=tex}]

with:

(1): full delivery,

(0<\eta{=tex}<1): partial delivery,

(0): complete failure.

If credible historical disruption labels are unavailable, no artificial
disruption classifier is trained.

12. Mathematical formulation

12.1 Sets

[ i\in {=tex}I ]

materials.

[ s\in {=tex}S_i ]

eligible suppliers.

[ t\in {=tex}T ]

procurement periods.

[ \omega{=tex}\in{=tex}\Omega{=tex} ]

uncertainty scenarios.

[ h\in {=tex}H ]

forecast horizons, provisionally:

[ H={1,3,6,12}. ]

12.2 Decision variables

Procurement quantity:

[ q_{i,s,t}\ge0{=tex} ]

Order activation:

[ y_{i,s,t}\in{=tex}{0,1} ]

Safety stock:

[ ss_{i,t}\ge0{=tex}. ]

Core decision vector:

[ \mathbf{x}{=tex}=(q,y,ss). ]

Supplier allocation is derived from (q).

12.3 Demand during uncertain lead time

[
D^{LT}{i,s,t}\ =\ \sum{=tex}{\tau{=tex}=t}^{t+L_{i,s,t}-1}D_{i,\tau{=tex}}.
]

Thus:

[ D^{LT}{i,s,t}\sim {=tex}F^{LT}{i,s,t}. ]

Primary implementation:

Monte Carlo propagation.

Demand and lead-time dependence must not automatically be assumed
independent. Dependence is tested where data permit.

12.4 Delivery

For scenario (\omega{=tex}):

[ A^\omega{=tex}{i,s,t+L^\omega{=tex}{i,s,t}} =
\eta{=tex}^\omega{=tex}{i,s,t}q{i,s,t}. ]

12.5 Inventory balance

[ I^\omega{=tex}{i,t} = I^\omega{=tex}{i,t-1} + \sum{=tex}s
A^\omega{=tex}{i,s,t} -u^\omega{=tex}_{i,t} ]

with:

[ I^\omega{=tex}_{i,t}\ge0{=tex}. ]

12.6 Shortage

[
u^\omega{=tex}{i,t}+z^\omega{=tex}{i,t}=D^\omega{=tex}_{i,t}
]

and therefore:

[
z^\omega{=tex}{i,t}\ =\ \max{=tex}(0,D^\omega{=tex}{i,t}-A^\omega{=tex}_{i,t})
]

under the relevant available-supply definition.

12.7 Shortage probability

[ R^{short}{i,t} = P(z{i,t}>0) ]

with Monte Carlo estimator:

[
\hat {=tex}R^{short}{i,t}\ =\ \frac{1}{M}{=tex}\ \sum{=tex}{m=1}^{M}
\mathbf 1{=tex}(z^{(m)}_{i,t}>0). ]

Service level:

[ SL_{i,t}=1-R^{short}_{i,t}. ]

12.8 Safety-stock benchmark

Let:

[ G_{i,t}(x)=P(D^{LT}_{i,t}\le {=tex}x). ]

Then:

[ SS^{bench}{i,t} = G^{-1}{i,t}(1-\epsilon{=tex}_i) -
E[D^{LT}_{i,t}]. ]

This is a benchmark/interpretability formulation.

It is not imposed as an equality on the optimized safety-stock
decision:

[ ss_{i,t}\neq {=tex}SS^{bench}_{i,t} ]

by necessity.

13. Procurement constraints

Where supported by the data:

Supplier capacity

[ q_{i,s,t}\le {=tex}Cap_{i,s,t}y_{i,s,t}. ]

Minimum order quantity

[ q_{i,s,t}\ge {=tex}MOQ_{i,s}y_{i,s,t}. ]

Storage

[ I^\omega{=tex}_{i,t}\le {=tex}Cap_i^{storage}. ]

Budget

A defensible deterministic, stochastic, robust or chance-constrained
budget representation will be selected according to the final decision
environment.

Material fulfillment

[
u^\omega{=tex}{i,t}+z^\omega{=tex}{i,t}=D^\omega{=tex}_{i,t}.
]

Non-negativity

[ q,I,ss,u,z\ge0{=tex}. ]

14. Objective formulation

Scenario total cost:

[ C^\omega{=tex}{total} = C^\omega{=tex}{proc} +
C^\omega{=tex}{hold} + C^\omega{=tex}{order} +
C^\omega{=tex}{short} + C^\omega{=tex}{delay} +
C^\omega{=tex}_{excess}. ]

Procurement cost:

[
C^\omega{=tex}{proc}\ =\ \sum{=tex}{i,s,t}P^\omega{=tex}{i,t}q{i,s,t}.
]

Holding cost:

[
C^\omega{=tex}{hold}\ =\ \sum{=tex}{i,t}h_iI^\omega{=tex}_{i,t}.
]

Ordering cost:

[ C^\omega{=tex}{order} = \sum{=tex}{i,s,t}K_{i,s}y_{i,s,t}.
]

Shortage cost:

[
C^\omega{=tex}{short}\ =\ \sum{=tex}{i,t}c_i^{short}z^\omega{=tex}_{i,t}.
]

Expected total cost:

[ f_1(\mathbf{x}{=tex}) =
\sum{=tex}{\omega{=tex}\in{=tex}\Omega{=tex}}\pi{=tex}\omega {=tex}C^\omega{=tex}_{total}.
]

Shortage objective:

[ f_2(\mathbf{x}{=tex}) =
E\left[\sum_{i,t}z^\omega_{i,t}\right]{=tex}. ]

Supply-risk exposure:

[ f_3(\mathbf{x}{=tex}) = E\left[
\sum_{i,s,t}r^\omega_{i,s,t}q_{i,s,t}
\right]{=tex}. ]

Primary CMIDO problem:

[ \boxed{
\min_{\mathbf{x}}
\left[
f_1(\mathbf{x}),
f_2(\mathbf{x}),
f_3(\mathbf{x})
\right]
}{=tex} ]

subject to the procurement constraints.

15. Pareto decision layer

The primary output is a Pareto set:

[ \mathcal {=tex}P= {x\in{=tex}\mathcal {=tex}X:
\nexists {=tex}x'\in{=tex}\mathcal {=tex}X
\text{ dominating }{=tex}x}. ]

This avoids arbitrary weights such as 50/50 cost/risk.

Scalarization may be used as a computational alternative or sensitivity
analysis, but the primary conceptual result remains the Pareto
trade-off.

Secondary risk-sensitive extensions such as CVaR may be tested only
after the core model is validated.

16. Forecasting methodology

Price model candidates

Representative baselines:

seasonal naive,

ETS,

ARIMA/SARIMA where appropriate,

gradient boosting,

XGBoost/LightGBM,

sequence/deep models only where justified by data,

probabilistic/quantile/conformal extensions.

Demand model candidates

Representative baselines:

seasonal naive/statistical,

ARIMA/SARIMA where appropriate,

gradient boosting,

XGBoost/LightGBM,

sequence models only when justified,

probabilistic extensions.

The research does not use a model zoo merely to maximize the number
of algorithms.

Model selection must be justified by:

literature,

data characteristics,

computational cost,

forecasting role,

fairness of comparison.

17. Forecast validation

Random train/test splitting is prohibited for the primary time-series
experiments.

Use:

Expanding-window rolling-origin backtesting.

Provisional Singapore split, regenerated from final admissible data:

training: earliest available period → approximately May 2022,

validation: June 2022 → May 2024,

final test: June 2024 → May 2026.

Exact dates are generated from the final cleaned dataset rather than
hard-coded.

Forecast horizons:

[ 1,3,6,12 ]

months.

Primary tactical horizon:

[ 3\text{ months}{=tex} ]

unless final application analysis justifies another horizon.

18. Forecast evaluation

Point accuracy

MAE

RMSE

sMAPE where appropriate.

Probabilistic quality

Pinball loss,

CRPS where supported,

prediction interval coverage,

interval width/sharpness,

calibration.

Where appropriate, use Diebold--Mariano testing for forecast comparison.

The conclusion must distinguish:

point accuracy

from:

uncertainty quality.

19. RO2 uncertainty-propagation experiments

Compare:

R0 --- deterministic

[ D=\hat {=tex}D,\quad {=tex}L=E[L] ]

R1 --- demand uncertainty only

[ D\sim {=tex}F^D,\quad {=tex}L=E[L] ]

R2 --- supply/lead-time uncertainty only

[ D=\hat {=tex}D,\quad {=tex}L\sim {=tex}F^L ]

R3 --- joint uncertainty

[ D\sim {=tex}F^D,\quad {=tex}L\sim {=tex}F^L ]

with disruption/partial-delivery uncertainty where defensible.

Compare:

expected shortage,

shortage probability,

service level,

risk calibration/quality where ground truth exists,

sensitivity to dependence assumptions.

20. RO3 controlled ablation

Four primary decision configurations:

Model                   Predictive information  Decision engine

A                   Conventional/point      Heuristic

B                   Conventional/point      Formal deterministic
optimization

C                   Probabilistic           Heuristic

Interpretation:

B − A: optimization contribution,

C − A: predictive-uncertainty contribution,

D − B: incremental value of uncertainty-aware optimization,

D − A: total integrated contribution.

This directly tests G3.

21. Decision-level evaluation

For each policy evaluate:

[ Cost ]

[ Shortage ]

[ ServiceLevel ]

[ Excess/WasteRelatedOutcome ]

[ Delay ]

[ RiskExposure ]

and, where appropriate:

supplier concentration,

inventory,

resilience degradation under stress.

Forecast accuracy alone cannot establish procurement value.

22. Common-random-number evaluation

When comparing policies in simulation, use the same uncertainty
realizations across A/B/C/D.

Example:

Scenario 001 → A, B, C, D
Scenario 002 → A, B, C, D
Scenario 003 → A, B, C, D
...

This creates paired counterfactual comparisons and reduces Monte Carlo
noise in policy differences.

23. Stress testing

Test at least:

price shock,

demand surge,

lead-time inflation,

supplier disruption,

compound disruption.

Generic stress transformations include:

[ D^{stress}=(1+\delta{=tex}_D)D ]

[ L^{stress}=(1+\delta{=tex}_L)L ]

[ P^{stress}=(1+\delta{=tex}_P)P. ]

Disruption severity must be historically calibrated where possible.
Otherwise the scenario is explicitly labelled SCN.

24. Sensitivity and robustness

Vary:

price volatility,

demand uncertainty,

disruption probability,

lead-time variability,

supplier capacity,

MOQ,

storage capacity,

holding cost,

shortage penalty,

delay cost,

budget,

risk tolerance,

uncertainty representation,

stress severity.

Test robustness to:

forecasting model choice,

predictive distribution representation,

demand/lead-time dependence,

scenario generation,

parameter assumptions.

25. Statistical decision comparison

Use paired/block-based inference appropriate to the simulation
structure.

Potential tools:

paired bootstrap confidence intervals,

block bootstrap where temporal dependence matters,

Wilcoxon signed-rank where appropriate,

effect sizes,

confidence intervals.

Do not report only percentage improvement.

Report:

[ \Delta {=tex}= Metric_{CMIDO}-Metric_{baseline} ]

with uncertainty estimates and effect sizes where possible.

26. Pareto-frontier evaluation

Primary:

Hypervolume

Secondary:

number of non-dominated solutions,

spacing/diversity,

frontier coverage where meaningful.

Do not select a single "best" solution without specifying the decision
preference or showing the trade-off.

27. Reproducibility requirements

The final implementation must preserve:

dataset versions,

source URLs/references,

preprocessing rules,

feature definitions,

train/validation/test timestamps,

random seeds,

scenario seeds,

model configurations,

hyperparameter-selection rules,

optimization parameters,

cost/risk assumptions,

scenario definitions,

software/library versions,

experiment configuration files,

raw-to-derived data lineage.

Every result must be reproducible from a documented configuration.

28. Leakage controls

The following are mandatory:

No random temporal split for forecasting.

No future price/demand values in features.

No future-derived normalization statistics.

No future supplier outcomes in decision-time features.

Rolling feature engineering must respect timestamps.

Hyperparameter selection must not use final test data.

Scenario calibration must use only information legitimately
available for the relevant experiment.

Cross-dataset joins must not create false historical entity
relationships.

29. What CMIDO is NOT

The study will not claim novelty for:

XGBoost,

LSTM/GRU,

transformers,

probabilistic forecasting alone,

ML + optimization alone,

stochastic optimization alone,

robust optimization alone,

MOO alone,

supplier selection alone,

disruption modelling alone,

reinforcement learning alone,

waste prediction alone.

These are established methodological families.

The contribution is the specific decision-centric uncertainty
propagation and controlled demonstration of incremental decision
value, subject to final SLR confirmation.

30. Waste/excess-material treatment

Waste is not a separate ML target in the core CMIDO model.

The preferred representation is:

excess material / excess inventory as a procurement outcome and
economic/environmental consequence.

This avoids introducing a second predictive problem without sufficient
project-specific waste data.

If the final data contain strong waste observations, a secondary waste
analysis may be considered, but it is not required for the core
scientific contribution.

31. Expected contribution structure

Contribution 1 --- Predictive uncertainty handoff

A framework for retaining probabilistic construction-material price and
demand forecasts as decision-active information rather than collapsing
them immediately to point estimates.

Contribution 2 --- Joint uncertainty-to-shortage propagation

A mechanism that transforms demand uncertainty together with
supply/lead-time uncertainty into shortage/service-risk information.

Contribution 3 --- Decision-level incremental validation

A controlled A/B/C/D evaluation isolating the contributions of
forecasting uncertainty, optimization, and their integration.

Supporting contribution

Stress and robustness analysis showing when uncertainty-aware policies
retain or lose their advantage.

These are candidate contributions, not "first-ever" claims, until
the formal SLR is completed.

32. Limitations that must be stated

The principal limitation is the absence, in the currently established
public data, of one complete longitudinal construction procurement
dataset containing price, order quantity, supplier, order date, actual
delivery date, realized lead time, inventory, shortage, and disruption
together.

Therefore the study uses:

empirical construction-market forecasting + construction operational
benchmarking + explicitly labelled estimated/scenario-based supply
uncertainty.

The study must not present scenario-generated supply uncertainty as
historical observation.

A project-level procurement dataset obtained from an industry partner or
academic data-sharing request would strengthen RO2/RO3 but is not a
dependency for executing the current architecture.

33. Final evidence/novelty wording

Safe wording

CMIDO investigates whether empirically calibrated predictive
uncertainty from construction-material price and demand forecasting,
when jointly propagated with supply and lead-time uncertainty into
decision-dependent shortage risk, can improve multi-objective
procurement decisions relative to deterministic and component-wise
alternatives.

Prohibited wording before final SLR

Do not write:

"first framework,"

"first study,"

"no previous study has...",

"novel for the first time,"

"state of the art,"

"unique."

unless the formal systematic literature review directly supports the
statement.

34. Final system architecture

┌───────────────────────────────────────────────┐
│              DATA / EVIDENCE LAYER            │
│                                               │
│ Price │ Demand │ Suppliers │ Sites │ Logistics│
│ Inventory │ Economics │ External context      │
└───────────────────────┬───────────────────────┘
                        ↓
┌───────────────────────────────────────────────┐
│          PREDICTIVE INTELLIGENCE               │
│                                               │
│ Probabilistic Price Forecast  F(P)            │
│ Probabilistic Demand Forecast F(D)            │
└───────────────────────┬───────────────────────┘
                        ↓
┌───────────────────────────────────────────────┐
│          SUPPLY UNCERTAINTY LAYER              │
│                                               │
│ Lead-time distribution F(L)                   │
│ Disruption probability P(Z)                   │
│ Partial-delivery factor η                     │
└───────────────────────┬───────────────────────┘
                        ↓
┌───────────────────────────────────────────────┐
│         UNCERTAINTY PROPAGATION                │
│                                               │
│ Demand + Lead Time + Supply State             │
│                 ↓                             │
│ Demand During Lead Time                       │
│                 ↓                             │
│ Shortage / Service-Risk Distribution           │
└───────────────────────┬───────────────────────┘
                        ↓
┌───────────────────────────────────────────────┐
│       MULTI-OBJECTIVE DECISION ENGINE          │
│                                               │
│ Cost │ Shortage │ Supply Risk                 │
│                                               │
│ Decisions: q, y, ss                            │
│ Quantity │ Timing │ Supplier Allocation        │
│ Safety Stock                                  │
└───────────────────────┬───────────────────────┘
                        ↓
┌───────────────────────────────────────────────┐
│          PARETO DECISION LAYER                 │
│                                               │
│ Cost ↔ Service ↔ Resilience                   │
└───────────────────────┬───────────────────────┘
                        ↓
┌───────────────────────────────────────────────┐
│          DECISION EVALUATION                  │
│                                               │
│ A/B/C/D Ablation                              │
│ Normal Conditions                             │
│ Stress Conditions                             │
│ Sensitivity + Robustness                      │
└───────────────────────────────────────────────┘

35. End-to-end experiment map

Experiment 1 --- Predictive intelligence

Input: Singapore empirical price + demand.

Compare: statistical → ML point → probabilistic.

Output: calibrated (F^P,F^D).

Answers: RQ1 / H1.

Experiment 2 --- Risk propagation

Input: (F^D) + supply/lead-time uncertainty.

Compare: deterministic → demand-only → supply-only → joint.

Output: shortage/service-risk distribution.

Answers: RQ2 / H2.

Experiment 3 --- Procurement decisions

Input: predictive distributions + operational construction
environment.

Compare: A/B/C/D.

Output: procurement policies and realized/simulated outcomes.

Answers: RQ3 / H3.

Experiment 4 --- Resilience

Apply:

price shocks,

demand surges,

lead-time inflation,

disruptions,

compound shocks.

Output: policy degradation and resilience.

36. Complete research logic

G1 ──→ RO1 ──→ RQ1 ──→ H1
 │
 │ probabilistic prediction
 ↓
F(P), F(D)
 │
 ↓
G2 ──→ RO2 ──→ RQ2 ──→ H2
 │
 │ joint uncertainty propagation
 ↓
Shortage / Service Risk
 │
 ↓
G3 ──→ RO3 ──→ RQ3 ──→ H3
 │
 │ decision-level evaluation
 ↓
Procurement Policy
 │
 ↓
Cost – Service – Resilience
 │
 ↓
Stress + Robustness

37. Implementation gate

No coding begins until the following are satisfied:

Formal SLR screening supports/refines G1--G3.

Research scope is defined.

RO1--RO3 are aligned.

RQ1--RQ3 are aligned.

H1--H3 are aligned.

The theoretical architecture is defined.

Core decision variables are defined.

Shortage computation is defined.

Safety-stock benchmark is defined.

Primary objective formulation is defined.

Dataset architecture is defined.

No-Frankenstein data rule is defined.

Temporal leakage controls are defined.

Baseline/ablation structure is defined.

Stress/robustness design is defined.

Reproducibility requirements are defined.

Evaluation metrics map to research objectives.

Exact empirical/scenario parameter values are established from
final admissible data.

Final solver/model choices are selected after data inspection.

38. Final research workflow

SYSTEMATIC LITERATURE REVIEW
             ↓
Final gap confirmation
             ↓
Scope/data admissibility confirmation
             ↓
RO1–RO3 / RQ1–RQ3 / H1–H3
             ↓
Theoretical framework
             ↓
Mathematical formulation
             ↓
Final dataset audit
             ↓
Data preprocessing specification
             ↓
Model implementation
             ↓
Rolling-origin forecasting
             ↓
Uncertainty calibration
             ↓
Joint uncertainty propagation
             ↓
Procurement optimization
             ↓
A/B/C/D ablation
             ↓
Stress testing
             ↓
Robustness/sensitivity
             ↓
Statistical evaluation
             ↓
Results
             ↓
Scientific interpretation
             ↓
Conclusions / contributions / limitations

39. Single source of truth

This specification supersedes earlier conflicting architectural
elements, particularly the earlier concept of a separate
waste-prediction stream.

The canonical CMIDO structure is:

[ \boxed{
\text{Predict}
\rightarrow
\text{Propagate}
\rightarrow
\text{Decide}
\rightarrow
\text{Evaluate}
}{=tex} ]

with:

[ \boxed{
F^P,F^D
\rightarrow
F^{D^{LT}}
\rightarrow
F^{Shortage}
\rightarrow
\text{Stochastic MOO}
\rightarrow
(q^*,y^*,ss^*)
}{=tex} ]

The project is now ready to move from research design into
implementation planning, but not yet into coding until the final
SLR/data gates above are satisfied.

Canonical freeze statement

CMIDO is an uncertainty-aware, decision-centric
construction-material procurement framework in which probabilistic
price and demand forecasts are retained as predictive distributions,
jointly propagated with supply/lead-time uncertainty to obtain
shortage and service-risk information, and consumed by a
multi-objective procurement optimizer that determines quantity,
timing, supplier allocation and safety stock. Its scientific value is
evaluated through controlled component-level and decision-level
comparisons under normal and stressed operating conditions.