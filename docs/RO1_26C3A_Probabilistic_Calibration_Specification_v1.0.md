CMIDO — RO1 Step 26C.3-A

Probabilistic Calibration & Conformal Prediction — Formal Specification and Contract

Status: DESIGN / CONTRACT
Step: 26C.3-A
Parent: 26C.2 Probabilistic ML Forecasting
Purpose: Calibrate frozen probabilistic ML prediction intervals without retraining or reselecting the forecasting models.

1. Scientific objective

Evaluate whether conformal calibration improves the empirical reliability of the frozen probabilistic ML forecasts from Step 26C.2.

Primary question:

Does conformal calibration reduce empirical coverage error of the frozen probabilistic ML intervals while retaining competitive interval sharpness?

This step is a calibration experiment, not a new forecasting-model selection experiment.

2. Frozen inputs

Step 26C.2 is frozen before calibration.

Forecasting models

Use only the nine validation-selected winners from 26C.2:

Target

Series

Frozen model

Price

Cement

LightGBM C1

Price

Concreting Sand

XGBoost C2

Price

Granite

XGBoost C3

Price

Ready Mixed Concrete

XGBoost C2

Price

Steel Reinforcement Bars

XGBoost C2

Demand

Cement

XGBoost C3

Demand

Granite

LightGBM C3

Demand

Ready Mixed Concrete

XGBoost C2

Demand

Steel Reinforcement Bars

XGBoost C3

No additional model selection is permitted.

Horizons

1 month

3 months

6 months

12 months

Primary horizon: 3 months.

Quantiles

q10

q25

q50

q75

q90

3. Forecast processing order

The exact processing order is frozen:

Generate raw ML quantile predictions.

Apply the already-defined monotone quantile repair from 26C.2.

Construct central prediction intervals.

Estimate conformal calibration adjustments using calibration data only.

Apply the frozen adjustment to the prediction interval.

Evaluate against the subsequently observed target.

Conformal calibration must NOT be applied before quantile repair.

4. Prediction intervals

50% interval

[
I_{50,t} =
[\hat Q_{0.25,t}, \hat Q_{0.75,t}]
]

Nominal coverage:

[
1-\alpha=0.50
]

80% interval

[
I_{80,t} =
[\hat Q_{0.10,t}, \hat Q_{0.90,t}]
]

Nominal coverage:

[
1-\alpha=0.80
]

The q50 prediction remains the point forecast.

5. Conformal method

Primary method: Conformalized Quantile Regression (CQR).

For a calibrated interval with lower endpoint L and upper endpoint U and observed value y:

[
S_t = \max(L_t-y_t,; y_t-U_t,; 0)
]

For a target miscoverage level alpha, calculate the finite-sample conformal quantile from calibration scores.

For calibration quantile q_alpha:

[
L^{cal}t = L_t-q\alpha
]

[
U^{cal}t = U_t+q\alpha
]

The same procedure is performed independently for the 50% and 80% intervals.

6. Critical time-series restriction

Standard split-conformal finite-sample coverage results rely on exchangeability. Construction-material time series are temporally dependent and non-stationary.

Therefore this project MUST NOT claim unconditional finite-sample iid/exchangeability coverage for the time-series application.

Instead, 26C.3 evaluates empirical time-aware calibration under chronological forecasting.

Calibration information must satisfy:

[
t_{calibration}<t_{forecast}<t_{target}
]

No future observation may influence an earlier interval.

7. Primary calibration protocol

Use a frozen validation-derived calibration layer.

Calibration source

Use only forecast errors/scores available before the final test evaluation.

The calibration layer is estimated from the validation history generated using the frozen 26C.2 winner.

Test rule

The complete test period remains untouched for calibration.

No test observation may be used to estimate, tune, or alter the conformal adjustment before reporting the primary test result.

This creates a clean experiment:

Validation
    ↓
Conformal calibration rule frozen
    ↓
Untouched test
    ↓
Final evaluation

8. Horizon-specific calibration

Calibration is performed separately for every:

dataset/target

material series

forecast horizon

interval level

Therefore calibration cells are:

[
9\ series \times 4\ horizons \times 2\ intervals
=72
]

No pooling across unrelated materials or target units is allowed in the primary analysis.

Example:

Cement price, 3-month horizon, 80% interval

has its own calibration score distribution.

9. Small-sample rule

The available validation origins decrease with forecast horizon.

Expected target-valid validation origins are:

h=1: 23

h=3: 21

h=6: 18

h=12: 12

Because h=12 has a small calibration sample, the project must NOT hide this limitation.

Primary implementation rule:

minimum calibration observations: 10

if fewer than 10 valid scores exist, calibration is marked unavailable rather than fabricated.

For h=12, results must therefore be explicitly flagged as small-sample calibration results.

No artificial observations, bootstrapped pseudo-history, or synthetic residuals are allowed to increase calibration sample size.

10. Calibration quantile rule

For n calibration scores and target miscoverage alpha, use the finite-sample conformal order-statistic rule:

[
k=\left\lceil (n+1)(1-\alpha)\right\rceil
]

with the rank capped at n.

The calibration adjustment is the k-th smallest conformity score.

The implementation must record:

n calibration scores

alpha

selected rank k

calibration quantile

minimum/maximum score

resulting interval width.

11. Non-negativity constraint

All targets in the empirical RO1 datasets are strictly positive.

Therefore calibrated lower bounds must be constrained to the physically meaningful domain:

[
L^{cal}t=\max(0,L_t-q\alpha)
]

Upper bounds remain:

[
U^{cal}t=U_t+q\alpha
]

This is a reporting/domain constraint, not a modification of the conformity-score calculation.

12. Comparators

Three forecasting interval versions must be retained:

A. Raw probabilistic ML

Frozen 26C.2 intervals after monotone quantile repair.

B. CQR-calibrated probabilistic ML

Frozen 26C.2 intervals plus conformal calibration.

C. Conventional probabilistic baseline

Frozen 26B.1 selected ETS/SARIMA probabilistic baseline.

No comparator may be reselected using the test period.

13. Metrics

Primary

50% coverage error

[
CE_{50}=|\widehat{Coverage}_{50}-0.50|
]

80% coverage error

[
CE_{80}=|\widehat{Coverage}_{80}-0.80|
]

Secondary

empirical coverage

mean interval width

median interval width

Winkler score

pinball loss

MAE of q50

RMSE of q50

Coverage and width must always be reported together.

A wider interval that achieves higher coverage is NOT automatically considered better.

14. Primary hypothesis

H3

Conformal calibration reduces empirical coverage error of probabilistic ML forecasts relative to uncalibrated ML forecasts while maintaining competitive interval sharpness.

The hypothesis does NOT assert that CQR will improve point accuracy.

15. Statistical comparison

For the primary h=3 test results:

Compare:

[
ML_{raw} \quad vs \quad ML_{CQR}
]

using paired forecast-level observations.

Primary comparison:

absolute coverage error is summarized at series level;

interval-score/Winkler and width differences are evaluated pairwise;

confidence intervals should be obtained using a block/bootstrap approach appropriate for temporal dependence.

Do not treat overlapping multi-step forecast errors as independent observations.

The statistical comparison is secondary to the descriptive calibration results if sample size is insufficient.

16. Required audits

The implementation must verify:

Data integrity

exactly 9 series

exactly 4 horizons

required q10/q25/q50/q75/q90 columns

no duplicated forecast-origin/series/horizon records

Temporal integrity

calibration timestamps precede forecast targets

no target is used to calibrate its own interval

no future calibration leakage

test data absent from calibration fitting

Quantile integrity

q10 ≤ q25 ≤ q50 ≤ q75 ≤ q90 after repair

lower ≤ upper for both intervals

Calibration integrity

calibration n recorded

rank k recorded

calibration adjustment non-negative

unavailable cells explicitly flagged

no synthetic calibration observations

Evaluation integrity

raw ML and CQR use identical target observations

same forecast origins

same horizons

test evaluation is frozen

17. Required output tables

The implementation must produce at minimum:

RO1_step26c3_calibration_scores.csv

RO1_step26c3_calibration_parameters.csv

RO1_step26c3_validation_forecasts.csv

RO1_step26c3_validation_metrics.csv

RO1_step26c3_test_forecasts.csv

RO1_step26c3_test_metrics.csv

RO1_step26c3_comparison.csv

RO1_step26c3_audit.csv

RO1_step26c3_run_summary.txt

All outputs must identify:

dataset

material/series

horizon

forecast origin

target date

nominal interval

lower bound

upper bound

actual value

calibration sample size

conformal adjustment

coverage indicator

interval width

Winkler score.

18. Reproducibility

The run must record:

source specification version

26C.2 model-selection fingerprint

code version/hash where available

random seed where applicable

calibration method

alpha values

minimum calibration sample

horizon list

series list

execution timestamp.

Conformal calibration itself is deterministic once the calibration scores are fixed.

19. Explicit exclusions

26C.3 must NOT:

retrain the 26C.2 models

change the selected XGBoost/LightGBM winners

use test observations to calibrate

use random train/test splitting

pool different material units in the primary calibration

fabricate calibration observations

claim iid finite-sample coverage for dependent time series

optimize conformal parameters against test results

silently discard poor-coverage intervals

replace the probabilistic forecasting model with a conformal-only model.

20. Scientific interpretation rule

The desired outcome is NOT simply:

“CQR gives higher coverage.”

A successful result requires a useful calibration–sharpness trade-off:

[
\text{lower coverage error}
+
\text{acceptable interval width}
]

If CQR reaches nominal coverage only by producing excessively wide intervals, this must be reported as a calibration trade-off rather than unconditional improvement.

21. Contract assertions

The implementation must terminate with PASS only if:

9 series are present.

4 horizons are present.

q10/q25/q50/q75/q90 are present.

quantile monotonicity holds after repair.

calibration is horizon-specific.

calibration uses only permitted historical information.

minimum calibration rule is enforced.

test observations are absent from calibration fitting.

50% and 80% interval calculations are valid.

raw and calibrated forecasts use identical test targets.

all calibration parameters are reproducible.

unavailable small-sample cells are explicitly flagged.

no synthetic observations are introduced.

all required audit fields are present.

Final status:

26C.3-A CONTRACT PASS

only after all assertions pass.

22. Methodological note for publication

CQR was originally developed to combine quantile regression with conformal calibration and obtain adaptive prediction intervals. Its classical finite-sample guarantee depends on exchangeability. Because this project uses temporally dependent construction-material series, the empirical time-series calibration results must be presented without overstating that classical iid guarantee.

The project therefore distinguishes:

statistical calibration procedure
from
empirical time-series coverage performance.

This distinction is mandatory in the final paper.

23. Frozen research role

26C.3 is an uncertainty-calibration layer within RO1.

It does not replace the central CMIDO contribution.

The resulting calibrated predictive intervals/distributions become inputs to the downstream:

Predict → Propagate → Decide → Evaluate

pipeline, where demand and supply uncertainty will subsequently be propagated into shortage/service risk and procurement decisions.