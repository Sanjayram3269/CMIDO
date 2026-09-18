CMIDO RO2 Step 27D.1 — Propagation Result Audit & Sensitivity Analysis v1.0

Purpose

Step 27D.1 audits the already-computed RO2 Step 27D propagation outputs before they are scientifically frozen.

This step is an audit and sensitivity stage, not a model-development stage.

The primary RO2 propagation remains:

RO1 validation CQR demand quantiles + 37-row joint empirical procurement-process-duration pairs + exact calendar-month overlap + Monte Carlo propagation.

The duration variable must continue to be called procurement-process duration, not supplier-specific lead time.

Inputs

From:

results/RO2/propagation/

RO2_step27d_propagation_summary.csv

RO2_step27d_service_risk_curve.csv

RO2_step27d_joint_vs_independent_sensitivity.csv

RO2_step27d_audit.csv

RO2_step27d_run_config.json

Audit questions

A. Distribution sanity

For each material and forecast origin, inspect:

mean

median / q50

q75

q90

q95

q99

min / max

Monte Carlo standard error of the mean

Required properties:

finite values

non-negative demand exposure

q50 <= q75 <= q90 <= q95 <= q99

q50 should equal the reported median within numerical tolerance

Monte Carlo standard error should be small relative to the mean unless the exposure itself is near zero.

B. Service-risk monotonicity

For each material/origin:

inventory threshold must be non-decreasing

shortage probability must be non-increasing as inventory threshold rises

service level must be non-decreasing

The empirical threshold rule in Step 27D is retained. The audit must not interpret the resulting values as calibrated real-world service probabilities.

C. Joint versus independent duration sensitivity

Compare:

joint_duration_primary

against:

independent_duration_sensitivity.

For q50, q75, q90, q95 and q99 calculate:

absolute difference

percentage difference

material/origin summaries

maximum absolute percentage difference.

Interpretation rule:

Do not claim that joint sampling proves statistical dependence. It preserves the observed pairing of the 37 procurement-process records. Independent sampling is a sensitivity analysis representing a different structural assumption.

D. Monte Carlo stability

The original Step 27D run uses 10,000 draws.

27D.1 performs a deterministic bootstrap-of-the-generated-exposure diagnostic using the saved Monte Carlo exposure summaries only where the required raw draw files are available. If raw draws are not available, it reports that direct MC stability cannot be independently recomputed from the summary CSVs and does not manufacture a stability claim.

E. Structural / methodological checks

Audit that:

all four demand materials are present;

both joint and independent representations are present;

source horizons are exactly 1, 3, 6 and 12;

duration pair n is 37;

MC n is 10,000;

no test forecasts are declared as used;

terminology remains procurement-process duration;

no horizon >12 is implied;

the primary representation remains joint duration.

F. Decision for scientific lock

27D.1 should produce one of:

PASS_FOR_27D_LOCK

PASS_WITH_RECORDED_CAVEATS

HOLD_FOR_REVIEW

A pass does not mean the underlying data become supplier-specific lead-time evidence.

Important interpretation boundary

RO2 currently supports uncertainty propagation from probabilistic demand into an observed procurement-process-duration distribution.

It does not establish:

supplier-specific lead-time distributions,

supplier disruption probabilities,

historical shortage labels,

causal dependence between demand and procurement duration,

calibrated operational service levels against realized future outcomes.

Those remain explicit data limitations.

Required outputs

Write to:

results/RO2/propagation_audit/

RO2_step27d1_distribution_audit.csv

RO2_step27d1_service_risk_audit.csv

RO2_step27d1_joint_independent_audit.csv

RO2_step27d1_structural_audit.csv

RO2_step27d1_decision.txt

RO2_step27d1_summary.json

Freeze rule

Do not proceed to RO3 optimization from 27D merely because the script executes.

RO3 may use the 27D propagation layer only after 27D.1 is reviewed and the resulting caveats are explicitly carried into the optimization specification.