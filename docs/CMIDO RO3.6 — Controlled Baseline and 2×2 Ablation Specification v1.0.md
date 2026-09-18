CMIDO RO3.6 — Controlled Baseline and 2×2 Ablation Specification v1.0

1. Purpose

RO3.6 tests the incremental decision value of the CMIDO framework using a controlled 2×2 experimental design. The purpose is attribution: determine whether observed procurement improvements arise from predictive uncertainty, optimization, or their integration.

2. Experimental factors

Factor A — predictive representation:

Deterministic / point forecast

Probabilistic / predictive distribution

Factor B — decision mechanism:

Heuristic procurement policy

Formal multi-objective stochastic optimization

This produces four controlled configurations:

O1 — Deterministic + Heuristic
O2 — Deterministic + Optimization
O3 — Probabilistic + Heuristic
O4 — Probabilistic + Optimization = CMIDO

3. Scientific attribution

Comparisons:

O2 − O1: value of optimization under deterministic forecasts.

O3 − O1: value of probabilistic uncertainty under heuristic decisions.

O4 − O2: value of uncertainty-aware optimization relative to deterministic optimization.

O4 − O3: value of optimization when probabilistic information is available.

O4 vs all: integrated decision value.

No superiority claim is made until results are evaluated.

4. Common evaluation design

All four configurations must use:

the same 11 locked forecast origins;

the same four common materials;

the same 12-month decision horizon;

the same realized/held-out evaluation demand and price information available to the experiment;

identical initial inventory and open-order assumptions;

identical economic parameters where applicable;

identical reporting units.

The test period must not be used to fit forecasting models or tune decision parameters.

5. Critical methodological rule

RO3.6 is a decision-level experiment, not another forecasting benchmark.

For each origin, decisions are generated from information available at that origin. Performance is then evaluated against the corresponding future realized demand/price path under a common simulation/evaluation protocol.

Do not compare configurations using different realized demand paths.

6. O1 — Deterministic + Heuristic

Predeclared heuristic:

use the deterministic point forecast;

order the forecast demand requirement using the same monthly arrival convention;

no stochastic optimization;

no arbitrary shortage monetization;

policy parameters must be frozen before test evaluation.

A simple baseline should be used rather than a tuned policy that is effectively optimized to the test set.

7. O2 — Deterministic + Optimization

Use:

deterministic point forecast;

frozen RO3.4.3 procurement optimization structure;

uncertainty removed from the scenario representation;

no probabilistic demand or duration sampling in the primary O2 condition.

This isolates the value of formal optimization.

8. O3 — Probabilistic + Heuristic

Use:

calibrated RO1 predictive quantiles;

the same procurement heuristic as O1;

uncertainty converted into a predeclared procurement protection rule;

no formal multi-objective optimization.

The protection rule must be specified before test results are inspected. A suitable primary rule is a predictive service quantile of demand during procurement duration, with sensitivity to the selected service target.

9. O4 — CMIDO

Use the frozen production CMIDO pipeline:

probabilistic demand/price representation;

empirical procurement-duration uncertainty;

stochastic multi-objective optimization;

objectives Z1, Z2, Z3;

Pareto/epsilon-constraint decision layer.

Existing RO3.5 outputs should be reused where compatible rather than recomputing the optimization.

10. Evaluation metrics

Primary:

total procurement + holding cost;

total shortage quantity;

CVaR95 total shortage;

service level.

Secondary:

total procurement quantity;

average inventory;

number/timing of procurement events;

duration exposure diagnostic;

Pareto hypervolume where a Pareto set is available.

11. Statistical comparison

Treat the 11 forecast origins as repeated temporal evaluation cases.

For paired configuration comparisons:

paired differences by origin;

bootstrap confidence intervals;

effect sizes;

multiple-comparison correction for the planned pairwise contrasts.

Do not treat individual monthly observations within an origin as independent replicates.

12. Required outputs

configuration-level results for every origin;

origin × configuration summary;

paired comparison table;

effect-size/CI table;

aggregate decision metrics;

audit manifest;

final comparison figures.

13. Integrity gates

Before running the experiment:

verify exact 11-origin intersection;

verify no test forecasts are used for development;

freeze all heuristic/protection parameters;

verify O2 removes probabilistic uncertainty rather than changing unrelated model components;

verify O3 uses the same heuristic as O1;

verify O4 points to the already-audited CMIDO outputs;

verify common evaluation realization.

A failed gate means HOLD; do not silently proceed.

14. Important implementation constraint

This specification deliberately does not invent exact heuristic formulas, service targets, deterministic optimization inputs, or evaluation-realization construction beyond what is established in the frozen project artifacts. Those must be reconciled against the existing RO1/RO3 schemas before code is written.

15. Interpretation

RO3.6 should answer:

Does optimization add value?

Does probabilistic information add value?

Does combining them add value beyond either component alone?

The strongest result would be consistent incremental improvement of O4 across the paired origin-level metrics, but the study must report negative, mixed, or null results honestly.