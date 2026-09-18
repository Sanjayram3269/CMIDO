CMIDO RO3.5 — Multi-Origin Procurement Optimization Specification v1.0

1. Purpose

RO3.5 evaluates whether the frozen CMIDO procurement optimization framework produces stable and interpretable procurement trade-offs across the 11 forecast origins common to the locked RO1 demand and RO1 price validation sets.

This is a multi-origin generalization/robustness experiment. It does not modify the RO3.4.3 mathematical formulation, parameter registry, scenario-generation mechanism, solver, or primary objective definitions.

2. Locked design

Forecast origins: the exact 11-origin intersection locked in RO3 Step 3.2:
2022-07-01 through 2023-05-01, monthly.

Scenario count: N=2,500 primary.

Scenario sensitivity: N=5,000 is retained separately and is not rerun in RO3.5 unless explicitly requested.

Materials: Cement, Granite, Ready Mixed Concrete, Steel Reinforcement Bars.

Horizon: 12 monthly periods after each forecast origin.

Scenario source: RO3.2 nested scenario files.

Optimization: corrected RO3.4.4 production epsilon-constraint optimizer.

Solver: HiGHS through Pyomo.

Primary objectives:
Z1 = expected procurement + holding cost
Z2 = expected total shortage quantity
Z3 = CVaR_0.95(total shortage quantity)

Pareto extraction: nondominance filtering over feasible epsilon-constraint solutions.

Epsilon grid: 3x3 for this multi-origin production run, matching the validated RO3.3B production sensitivity configuration.

Initial inventory: 0.

Open orders: 0.

Monthly holding rate: 2.5%.

No supplier-specific disruption probability, capacity, MOQ, fixed ordering cost, or delay penalty is introduced.

3. Locked origins

2022-07-01

2022-08-01

2022-09-01

2022-10-01

2022-11-01

2022-12-01

2023-01-01

2023-02-01

2023-03-01

2023-04-01

2023-05-01

4. Execution principle

Each origin is solved independently using only the scenario rows associated with that origin. The optimizer code must remain identical across origins. A failure at one origin must not be silently skipped: the run should record the failure and stop the aggregate completion gate unless the failure is explicitly classified and resolved.

5. Required outputs

For each origin:

Pareto objective CSV

Pareto decision CSV

optimizer manifest

execution record

Aggregate:

one cross-origin Pareto summary

one cross-origin decision summary

one run manifest

one audit report

6. Cross-origin evaluation

The aggregate analysis should report:

Pareto cardinality by origin

Z1, Z2, Z3 ranges and medians

solver runtime

feasibility status

procurement quantity totals by Pareto solution

shortage and CVaR ranges

whether the number of nondominated solutions is stable across origins

No claim of statistical significance is made from origin-to-origin variation alone. These origins are rolling forecast origins and are treated as repeated temporal evaluation cases.

7. Integrity gates

PASS requires:

all 11 locked origins are present;

every origin has exactly 2,500 scenarios per material;

four materials are present;

each origin has the complete 12-month horizon;

the optimizer reports optimal termination for every anchor and epsilon solve;

every origin produces a non-empty Pareto set;

objective values are finite and non-negative;

reported Z3 equals independently reconstructed empirical CVaR;

output files are unique by origin;

aggregate counts equal the sum of successful origin runs.

8. Scientific interpretation

RO3.5 is not itself the baseline comparison or final performance claim. It establishes the temporal robustness of the decision framework before controlled baseline/ablation experiments.

If the results vary materially across origins, that is a research finding rather than an implementation failure unless an integrity gate fails.

9. Known limitations retained

Procurement duration is an empirical procurement-process duration proxy, not supplier-specific lead time.

The 37 paired duration observations do not establish a causal or universal dependence structure.

RO1 supplies marginal horizon-wise predictive quantiles rather than a fully joint future demand path.

The monthly optimization uses a discrete calendar-month arrival convention.

No Indian-project generalization is claimed from the Singapore/auxiliary datasets.