CMIDO RO3.6 — Controlled Baseline / Ablation Controller Freeze Specification v1.0

1. Purpose

Freeze the decision rules for the four controlled ablation arms before any outcome-based tuning:

O1: deterministic forecast + heuristic

O2: deterministic forecast + formal optimization

O3: probabilistic forecast + uncertainty-protected heuristic

O4: probabilistic forecast + formal uncertainty-aware optimization (CMIDO)

The rules below are predeclared and must not be changed after evaluation results are inspected.

2. Common evaluation contract

Evaluation cases:

11 locked forecast origins: 2022-07-01 through 2023-05-01

4 materials: Cement, Granite, Ready Mixed Concrete, Steel Reinforcement Bars

12 monthly realized periods after each origin

Same realized demand and price observations for every arm

No use of realized evaluation observations to choose model/controller parameters

Initial inventory = 0

Open orders = 0

The realized evaluation layer is the raw historical Singapore monthly demand/price data validated by RO3.6.

3. Forecast information

Deterministic arms use the median point forecast q50 from the frozen RO1 calibrated probabilistic forecast.

Probabilistic arms use the frozen calibrated predictive quantiles q10, q25, q50, q75, q90 from RO1.

For a 12-month evaluation horizon, the corresponding horizon-specific forecast is used for each month-ahead. No test/evaluation actual is used in forecasting.

4. O1 — Deterministic + heuristic

Rule

At each monthly decision period t, order the deterministic expected requirement for that month:

q_t = max(0, Dhat_t - I_t)

where:

Dhat_t = frozen RO1 q50 demand forecast for month t

I_t = on-hand inventory at the decision point

q_t = procurement quantity

Arrival is governed by the same frozen procurement-duration/availability convention used in the controlled experiment.

No safety stock is added.

No shortage penalty is used.

No price optimization is performed.

This is intentionally a simple transparent deterministic benchmark: forecast-driven replenishment without formal optimization or uncertainty protection.

5. O2 — Deterministic + formal optimization

Use the same deterministic q50 demand and q50 price forecasts as O1.

Use the frozen RO3 optimization formulation, but replace stochastic demand/price inputs with their q50 deterministic values and use the deterministic duration convention frozen for the ablation.

Primary objectives remain the deterministic counterparts of:

procurement + holding cost

total shortage quantity

shortage-tail criterion only where a deterministic equivalent is mathematically defined

No probabilistic demand/price scenarios are supplied to O2.

The optimizer formulation, constraints, initial state, tolerances, and decision horizon must otherwise remain identical to the compatible O4 implementation.

6. O3 — Probabilistic + heuristic

Use the same replenishment heuristic as O1, but add one predeclared uncertainty-protection rule.

Protection rule

Set target inventory for month t to the upper predictive quantile q90:

Target_t = q90_t

Then:

q_t = max(0, Target_t - I_t)

Thus O3 differs from O1 only in the forecast quantity used for protection:

O1 target = q50

O3 target = q90

No optimization, price arbitrage, supplier allocation, or post-hoc tuning is permitted.

The q90 rule is selected a priori as a transparent service-oriented upper predictive target, not calibrated against the evaluation outcomes.

7. O4 — Probabilistic + optimization

O4 is the audited CMIDO controller.

Use:

probabilistic demand scenarios from RO1

probabilistic price scenarios from RO1

joint empirical procurement-duration uncertainty from RO2

N=2500 primary scenario set

N=5000 sensitivity scenario set

frozen RO3.4 formulation

frozen RO3.4 parameters

Pareto/epsilon-constraint decision framework

primary objectives:
Z1 = expected procurement + holding cost
Z2 = expected total shortage quantity
Z3 = CVaR_0.95(total shortage quantity)

No outcome-based tuning is permitted.

8. Common execution restrictions

All four arms must:

use identical origins and realized evaluation periods;

use the same four material definitions and units;

use the same initial state;

use the same procurement-arrival convention wherever a controlled comparison requires it;

avoid using evaluation actuals for model/controller selection;

retain all results before any aggregate comparison;

report origin-level results before pooled summaries.

9. Primary scientific contrasts

The ablation is interpreted through controlled contrasts:

A. O2 vs O1:
formal optimization value under deterministic information.

B. O3 vs O1:
value of adding predictive uncertainty protection to a transparent heuristic.

C. O4 vs O2:
value of propagating uncertainty into formal optimization.

D. O4 vs O3:
value of formal optimization beyond uncertainty-aware heuristic protection.

E. O4 vs O1:
integrated end-to-end decision value.

10. Metrics

Primary:

total procurement + holding cost

total shortage quantity

CVaR95 shortage

service level

Secondary:

procurement quantity

average inventory

number of procurement events

procurement-duration exposure

Pareto-frontier / hypervolume metrics where applicable

Comparisons must retain the 11 origin-level paired observations.

11. Freeze rule

This specification is a methodological lock.

After results are generated:

controller rules must not be altered;

q50/q90 choice must not be tuned;

no origin may be removed because of unfavorable performance;

no metric may be selectively omitted;

any implementation incompatibility must be documented and resolved before looking at comparative outcomes.

12. Important limitation

O2 is a deterministic ablation of the stochastic optimizer, not a separate independently optimized research contribution.

O1/O3 are deliberately simple controller benchmarks. Their purpose is controlled attribution, not state-of-the-art heuristic optimization.

13. Status

RO3.6 evaluation-realization gate: PASS.

Controller rules: FROZEN BEFORE OUTCOME EVALUATION.