CMIDO RO3.2 — Forecast-Origin Lock Addendum v1.0

Decision

The primary RO3.2 forecast-origin set is frozen at 11 common origins:

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

Evidence

The RO1 calibrated probabilistic artifact contains:

12 complete demand origins: 2022-06-01 through 2023-05-01

12 complete price origins: 2022-07-01 through 2023-06-01

Their exact intersection is therefore 11 origins:

2022-07-01 through 2023-05-01.

The two non-overlapping origins are:

2022-06-01: demand-only

2023-06-01: price-only

Scientific rule

RO3 scenarios require both probabilistic demand and probabilistic price information at the same forecast origin. Therefore, the primary experiment uses the exact intersection rather than imputing, extrapolating, or otherwise manufacturing the missing counterpart.

This is an admissibility rule, not a data-cleaning correction.

Consequence

For four common materials and 12 forecast months, the 100-scenario structural audit contains:

11 origins × 4 materials × 12 months × 100 scenarios = 52,800 rows

The difference from RO2's 12 demand-only origins is intentional: RO2 requires demand uncertainty, whereas RO3 requires the paired demand+price uncertainty intersection.

Lock status

This origin set is frozen for the primary RO3 scenario-generation experiment.

Any future change requires an explicit methodological revision and rerun of the RO3.2 audit.

The machine-readable lock is stored as:

docs/RO3_STEP32_FORECAST_ORIGIN_LOCK_v1.0.json