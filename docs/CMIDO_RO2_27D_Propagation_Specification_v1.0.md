CMIDO RO2 Step 27D — Demand–Procurement-Duration Uncertainty Propagation

Frozen Methodological Specification v1.0

1. Purpose

Step 27D is the bridge from RO1 probabilistic construction-material demand forecasts to RO2 empirically grounded procurement-process duration uncertainty.

The objective is to estimate the distribution of demand accrued during a procurement-process duration and derive decision-relevant shortage/service-risk quantities without claiming that the available RO2 data are supplier-specific material lead-time observations.

This step is propagation only. It does not perform procurement optimization, supplier disruption classification, or historical shortage classification.

2. Scientific question

How does probabilistic material-demand uncertainty combine with empirically observed procurement-process duration uncertainty to determine the distribution of demand exposure during procurement?

3. Inputs

RO1

Frozen probabilistic ML + CQR validation forecasts:

9 series total:

Price: 5 series

Demand: 4 series

Common demand materials:

Cement

Granite

Ready Mixed Concrete

Steel Reinforcement Bars

horizons available: 1, 3, 6, 12 months

quantiles: q10, q25, q50, q75, q90

validation forecasts are used for methodological development.

RO1 test forecasts remain untouched until a later frozen evaluation.

The RO1 probabilistic layer retains forecast origins, target dates, horizons and quantiles and prohibits test leakage.

RO2

Locked 27C.3 joint empirical procurement-duration representation:

37 paired component observations

Internal_num + PODN_num = TotalDN_num exactly for all 37 paired observations

joint empirical resampling of observed component pairs

55-observation empirical total-duration distribution remains the direct total-duration representation.

4. Terminology restriction

The duration variable is called:

procurement-process duration

or

procurement-duration proxy

throughout 27D.

It must NOT be described as historical supplier-specific construction-material lead time because supplier identity and explicit supplier delivery/receipt dates were not established in the source.

5. Core propagation problem

For material i, forecast origin t, and sampled procurement duration L:

\sum_{m=1}^{M}
w_m(L,t),D_{i,t+m}
]

where:

D is monthly material demand,

w_m is the fraction of month m covered by the procurement duration,

L is sampled from the RO2 joint empirical duration representation,

M is the number of future months intersected by L.

Because RO1 demand is monthly while RO2 duration is measured in days, the implementation uses calendar-month overlap weights rather than equating one monthly observation to one day.

6. Critical limitation: future demand-path dependence

RO1 provides marginal predictive quantiles at horizons 1, 3, 6 and 12 months. These are not, by themselves, a full joint predictive distribution for an entire future monthly demand path.

Therefore 27D must NOT claim that it has obtained a fully joint demand-path distribution.

For the primary propagation:

Interpolate each forecast quantile monotonically across available forecast horizons to obtain monthly marginal quantiles for horizons 1–12.

For each future month, sample demand from its interpolated marginal predictive quantile function.

Sample procurement duration by jointly resampling the 37 observed (Internal_num, PODN_num) pairs.

Apply calendar-month overlap weights to obtain demand accrued during the sampled duration.

Repeat Monte Carlo sampling.

This is explicitly a marginal-demand / joint-duration propagation model.

7. Quantile interpolation

Available RO1 horizons are 1, 3, 6 and 12 months.

For missing intermediate horizons 2, 4, 5, 7, 8, 9, 10 and 11, use linear interpolation separately for each quantile on the horizon axis.

No extrapolation is permitted outside 1–12 months.

After interpolation, enforce monotonicity across quantiles by deterministic sorting within each horizon.

This interpolation is a transparent engineering bridge, not a new forecasting model.

8. Demand sampling

For each future month:

construct the predictive quantile function from q10/q25/q50/q75/q90;

sample U ~ Uniform(0,1);

obtain demand by piecewise-linear interpolation of the quantile function;

constrain demand to >= 0.

No Gaussian assumption is imposed.

9. Procurement-duration sampling

Primary:

jointly sample observed (Internal_num, PODN_num) pairs from the 37-row empirical paired sample;

set total duration equal to the paired component sum.

Sensitivity:

independently sample Internal_num and PODN_num from their empirical marginals;

compare resulting demand-during-duration distribution against the joint representation.

The 55-row empirical total-duration representation may also be reported as a direct-duration sensitivity/reference, but it is not mixed with the component representation in the same draw.

10. Calendar overlap

For each forecast origin:

future month boundaries are determined using calendar-month offsets;

a sampled duration L starts immediately after the forecast origin;

each intersected future month receives weight equal to:
covered calendar days / total calendar days in that month.

Thus:

a 10-day duration consumes approximately 10/31 of the first future month's forecast demand;

a duration crossing two or more months receives partial/full/partial weights as appropriate.

This avoids a fixed 30-day-month approximation in the primary calculation.

11. Monte Carlo design

Primary:

10,000 Monte Carlo draws per material/origin/duration representation.

deterministic random seed.

no synthetic historical observations are added to the underlying datasets.

For computational reproducibility, all sampled quantities are generated from the frozen RO1 predictive quantiles and locked RO2 empirical observations.

12. Required outputs

For each material and forecast origin:

duration representation

duration draw summary

expected demand during procurement duration

q50, q75, q90, q95, q99 of demand during duration

probability of exceeding specified inventory thresholds where meaningful

service level for threshold values

Monte Carlo standard error / stability diagnostic.

Primary material-level aggregate outputs:

mean and median demand-during-duration

upper-tail quantiles

joint-vs-independent duration sensitivity

duration quantiles

sampled-duration / demand-exposure relationship.

13. Shortage-risk formulation

For an available inventory level A:

[
R_{short}(A)=P(D^{LT}>A)
]

and

[
SL(A)=P(D^{LT}\le A)=1-R_{short}(A)
]

27D reports these as conditional risk curves over a transparent grid of inventory thresholds.

No single arbitrary service-level target is imposed at this stage.

14. Safety-stock bridge

For a target service level 1-epsilon:

[
SS_\epsilon =
Q_{1-\epsilon}(D^{LT})-E[D^{LT}]
]

with a lower bound of zero.

This is a benchmark/interpretability quantity in 27D, not yet the final optimization decision variable.

RO3 may later choose safety stock directly as a decision variable.

15. Primary evaluation and sensitivities

Primary:

CQR-calibrated RO1 demand forecasts

joint empirical RO2 procurement-duration pairs

calendar overlap

10,000 Monte Carlo draws.

Sensitivity A:

raw/un-calibrated RO1 probabilistic demand where available.

Sensitivity B:

independent RO2 duration components.

Sensitivity C:

direct 55-observation total-duration empirical representation.

Sensitivity D:

Monte Carlo sample-size stability.

No test-period tuning is allowed.

16. Validation/test separation

27D development/validation must use RO1 validation forecasts and the locked RO2 uncertainty representation.

RO1 test forecasts must not be used to choose:

interpolation rules,

Monte Carlo sample size,

duration representation,

thresholds,

or any propagation specification.

A later frozen 27D test evaluation may use the already frozen RO1 test forecasts without changing these rules.

17. Required audits

The implementation must verify:

exactly four common demand materials are present;

only RO1 demand series enter propagation;

forecast target dates are after origins;

no future target is used to construct a forecast distribution;

q10 <= q25 <= q50 <= q75 <= q90;

interpolation uses only horizons 1,3,6,12;

no extrapolation outside 1–12 months;

duration samples are positive;

joint duration draws preserve observed component pairing;

no synthetic historical records are written into source data;

Monte Carlo outputs are finite and non-negative;

service-risk probabilities lie in [0,1];

test data are not used for development;

random seed and run configuration are recorded.

18. Scientific interpretation rule

A successful 27D result does NOT mean:

“The model has learned true supplier lead-time uncertainty.”

It means:

“Probabilistic material-demand forecasts were propagated through an empirically observed procurement-process-duration uncertainty representation to obtain a distribution of demand exposure during procurement.”

This distinction must remain explicit in the paper.

19. Frozen status

This specification is the methodological contract for RO2 Step 27D.

No implementation result may be used to redefine the primary propagation method retrospectively.

Next stage after 27D:
RO3 procurement decision engine, where demand-during-procurement-duration uncertainty can become a formal shortage/service-risk input to multi-objective procurement optimization.