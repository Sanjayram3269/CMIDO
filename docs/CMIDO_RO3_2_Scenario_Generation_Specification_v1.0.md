CMIDO RO3.2 — Scenario Generation Specification v1.0

1. Purpose

RO3.2 converts the frozen uncertainty representations from RO1 and RO2 into
reproducible stochastic procurement scenarios for the RO3 decision engine.

Canonical chain:

RO1 probabilistic prediction → RO2 uncertainty propagation → RO3 scenario generation → procurement decision

RO3.2 does not optimize procurement decisions. It only constructs the
uncertainty scenarios that later optimization will consume.

2. Scientific role

For scenario ω:

[
\omega = {D_{i,t,\omega}, P_{i,t,\omega}, L_\omega}
]

where:

(D_{i,t,\omega}): demand realization for material i and future month t;

(P_{i,t,\omega}): price realization for material i and future month t;

(L_\omega): procurement-process duration realization.

The duration representation is the empirical paired RO2 procurement-process
duration sample. It must not be described as supplier-specific material lead
time.

RO1 provides marginal horizon-wise predictive quantiles rather than a fully
joint future demand-path distribution. Therefore RO3.2 is explicitly described
as:

marginal-demand scenario generation with joint procurement-duration sampling.

3. Frozen input artifacts

RO1

Primary file:

results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv

Required fields:

dataset

series

horizon

forecast_origin

target_date

q10

q25

q50

q75

q90

Development uses validation forecasts only. RO1 test forecasts are prohibited.

Demand dataset:

RO1_DEMAND

Price dataset:

RO1_PRICE

Common procurement material set:

Cement

Granite

Ready Mixed Concrete

Steel Reinforcement Bars

Concreting Sand is not included in the common demand/price scenario set because
the available RO1 demand dataset does not contain a corresponding demand series.

RO2

Primary file:

results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv

Required fields:

Internal_num

PODN_num

TotalDN_num

admissible_component

The primary duration sample is the 37 admissible paired observations.

4. Quantile representation

RO1 provides q10, q25, q50, q75 and q90 at horizons 1, 3, 6 and 12 months.

For intermediate horizons 2, 4–5, 7–11, values are obtained by
piecewise-linear interpolation across the four observed source horizons
1, 3, 6 and 12.

No extrapolation outside months 1–12 is permitted.

The interpolation is performed independently for each:

dataset,

material,

forecast origin,

quantile.

Quantile ordering must satisfy:

[
q_{10}\le q_{25}\le q_{50}\le q_{75}\le q_{90}
]

If raw quantiles violate ordering, the generator stops. RO1's calibrated
artifact is expected to have already undergone monotone quantile handling;
RO3.2 must not silently repair a new violation.

5. Tail representation

Only q10–q90 are available in the frozen RO1 scenario input.

Therefore the base scenario generator samples the truncated predictive
representation over the probability interval [0.10, 0.90] using
piecewise-linear inverse-quantile interpolation.

This is intentional: RO3.2 must not invent unobserved q0/q100 tails.

Tail uncertainty outside this central predictive representation is reserved
for later RO3 stress testing and robustness analysis.

This distinction must be retained in reporting.

6. Demand generation

For every material, forecast origin and future month:

obtain/interpolate q10, q25, q50, q75, q90;

draw (U_D\sim Uniform(0.10,0.90));

evaluate the piecewise-linear inverse quantile function;

enforce non-negativity by max(value, 0).

The same demand realization must be reproducible from the recorded scenario
seed/stream.

Because RO1 supplies marginal horizon-wise distributions, monthly demand
draws are not claimed to form a statistically learned joint future demand
trajectory.

7. Price generation

For the same material, forecast origin and future month:

obtain/interpolate q10, q25, q50, q75, q90 from RO1_PRICE;

draw (U_P\sim Uniform(0.10,0.90));

evaluate the piecewise-linear inverse quantile function;

enforce non-negativity.

No synthetic price tails are created.

8. Procurement-process duration generation

For every scenario, sample one row from the 37 paired RO2 observations.

The sampled row supplies:

internal duration;

PO/GR duration;

total duration.

The pairing must be preserved:

[
Total_\omega = Internal_\omega + PODN_\omega
]

The generator must never sample the two components independently in the
primary scenario set.

The duration is a procurement-process-duration representation, not a
supplier-specific lead-time distribution.

9. Calendar representation

The future planning period is represented by calendar months.

The scenario file records total duration in days. Later propagation/optimization
may convert this duration to monthly exposure using exact calendar overlap.

RO3.2 itself does not invent additional lead-time semantics.

10. Scenario count and convergence

RO3.2 supports nested scenario sets:

100

250

500

1,000

2,500

5,000

A smaller 100-scenario run is the mandatory structural audit run.

The scenario generator uses nested common random numbers. A single deterministic
master stream is generated for the maximum requested scenario count and smaller
sets are prefixes of that stream.

Thus:

[
S_{100}\subset S_{250}\subset S_{500}\subset S_{1000}
\subset S_{2500}\subset S_{5000}
]

The final scenario count is not locked by RO3.2. RO3.3 performs scenario-count
convergence and decision-stability analysis.

11. Common random numbers

The generator maintains deterministic scenario streams by stable material and
forecast-origin identifiers.

Demand uniforms, price uniforms and duration row selections are generated
from reproducible stream positions.

Competing decision models in RO3 must consume the same scenario set.

This avoids giving different optimization methods different random realizations.

12. Scenario origin selection

Only forecast origins having complete source horizons:

1, 3, 6 and 12 months

for the required material and dataset are eligible for the base scenario set.

A forecast origin is retained only when all four source horizons are present
for both demand and price.

No missing source horizon is filled from test data.

13. Required output schema

RO3_step32_scenarios.csv

Required columns:

scenario_id

forecast_origin

material

period

month_ahead

demand

price

internal_duration_days

podn_duration_days

total_duration_days

scenario_set_size

stream_id

14. Audit requirements

The implementation must verify:

exactly four common procurement materials;

only RO1_DEMAND and RO1_PRICE are used;

only validation forecasts are used;

all target periods are after the forecast origin;

source horizons are exactly 1, 3, 6 and 12;

no extrapolation outside 1–12 months;

q10 ≤ q25 ≤ q50 ≤ q75 ≤ q90;

demand and price are finite and non-negative;

duration observations are positive and finite;

the 37-row paired duration sample is preserved;

total duration equals internal + PO/GR duration;

scenario IDs are unique within a scenario set;

repeated execution with the same configuration is deterministic;

nested scenario prefixes are identical across requested scenario sizes;

no RO1 test rows are used.

15. Mandatory 100-scenario audit

Before full scenario generation, run:

python src/optimization/ro3_scenario_generator.py --n-scenarios 100

The run must terminate with a PASS/FAIL decision.

The 100-scenario run is a structural validation run, not the final scenario-count
selection.

16. Scientific limitations retained

RO3.2 does not establish:

supplier-specific lead-time distributions;

supplier disruption probabilities;

historical shortage labels;

a fully joint future demand process;

true predictive tails beyond q10–q90.

These limitations are not implementation failures. They define the admissible
interpretation of the public-data experiment.

17. Lock status

RO3.2 is an implementation specification.

The final scenario count remains UNLOCKED until RO3.3.

The stochastic procurement model remains UNLOCKED until the scenario
generator passes its structural and reproducibility audit and RO2's outstanding
final-audit check is resolved.