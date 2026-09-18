CMIDO RO3.3 — Corrected Scenario-Set Convergence Specification v1.1

Purpose

Determine the smallest RO3 stochastic scenario-set size giving stable uncertainty and propagation quantities using the actual frozen RO3.2 scenario schema.

Frozen scenario ladder

100, 250, 500, 1000, 2500, 5000 scenarios.

Primary transition: 500 → 1000.

Actual RO3.2 schema

scenario_id, forecast_origin, material, period, month_ahead, demand, price, internal_duration_days, podn_duration_days, total_duration_days, scenario_set_size, stream_id.

Metrics

For every material/origin and scenario size:

mean and q90 demand

mean and q90 price

mean and q90 internal duration

mean and q90 PODN duration

mean and q90 total duration

mean, q90, q95 and q99 demand-during-procurement-duration exposure.

Exposure is a propagation diagnostic, not an optimization decision.

Convergence

For consecutive sizes:
relative_change = abs(B-A) / max(abs(A), 1e-12)

Primary 500→1000 thresholds:

means ≤ 1%

q90 metrics ≤ 2%

q95 exposure ≤ 2%

q99 exposure ≤ 5%

If the primary gate passes, candidate lock is 1000. Otherwise evaluate 2500, then 5000 if required.

Passing RO3.3 establishes convergence of the scenario representation and propagation diagnostics, not optimizer/Pareto-frontier convergence. A later decision-level optimization sensitivity audit remains required.