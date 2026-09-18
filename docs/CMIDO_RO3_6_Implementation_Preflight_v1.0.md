RO3.6 Implementation Preflight v1.0

Before implementing or executing O1–O4, resolve these frozen-input contracts.

A. Forecast inputs

Identify the exact existing files/columns for:

point forecasts for each of the 4 common materials;

calibrated probabilistic demand forecasts;

price forecasts if price is required by the decision policy.

B. Evaluation realization

Identify the exact held-out realized demand/price data corresponding to each of the 11 forecast origins. The evaluation realization must occur after each forecast origin and must not be used for fitting/tuning.

C. Duration

Use the already established RO2 procurement-process duration representation. Do not relabel it as supplier-specific lead time.

D. O1/O3 heuristic contract

Freeze one simple heuristic and one uncertainty-protection rule before looking at test results. Record all parameters in a registry.

E. O2 contract

Construct deterministic demand scenarios from the frozen point forecasts while keeping the optimization structure otherwise comparable to O4.

F. O4 contract

Reuse the audited RO3.5 CMIDO results where the evaluation design permits. Do not rerun O4 merely to make a new comparison unless a compatibility audit shows it is necessary.

G. Stop condition

If the existing artifacts do not support a fair common-realization comparison, stop implementation and report the missing evidence rather than inventing it.