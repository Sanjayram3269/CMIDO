# CMIDO — Final Research Package: Verification Notes

This folder records the verification performed against the final publication artifacts and the final
package state. It is a working verification note, not a substitute for the underlying result files.

## What was verified this session

- 8Q publication tables exist, are non-empty, and match the structure asserted by the 8Q/8S manifests.
- 8R figures exist, are non-empty, and match the structure asserted by the 8R concordance.
- 8S reconciliation reported PASS (81/81).
- 8M/8N/8O/8P manifests reported PASS.
- Full construction + optimization regression: 1059 passed, exit 0.

## Important reconciliation notes

- 8Q and 8S compare publication tables against their declared source CSVs using the generation scripts'
  declared deterministic rules. That is the authoritative table-vs-source check used by this project.
- Against the raw source CSVs directly, the publication tables are faithful in all numeric columns that
  both sides share, and faithful in every column where the publication table's column set exactly matches
  the source table's column set.
- The one visible publication-vs-source difference in column inventories is structural, not a numeric
  mismatch:
  - `T1_RO1_validation_metrics.csv` is a publication-facing projection of the broader
    `RO1_step26c3_validation_metrics.csv` source. The publication table drops the `raw_*` coverage/width/
    winkler columns and keeps the prequential-calibrated columns; the numeric values that both tables share
    are identical.
  - `T5_RO3_baseline_comparison.csv` is a publication-facing projection of
    `RO3_step36_statistical_pairwise_comparisons.csv`. The publication table keeps the core contrast/
    metric/estimate/inference columns; the source keeps additional per-contrast control columns
    (`relative_mean_difference`, `improved_count`, `worsened_count`, `tie_count`, `rank_biserial_sign`).
    The shared numeric columns are identical.
  - `T6_RO3_ablation.csv` and `T5_T6_controller_descriptives.csv` have the same column set as their source
    files and share identical values.

## Conclusion

The publication artifact chain is internally consistent and reconciles against its declared sources under
both the manifest-defined checks and the direct numeric comparison. The package can therefore be assembled
from these frozen artifacts without inventing numbers.

## Next verification step

After the manuscript and package are assembled, verify:
- every manuscript-bound numerical claim is traceable to one of the 8Q/8R source rows above;
- every table/figure caption points to the correct generation path;
- the package manifest matches the repo state and the result manifests;
- all expected package files exist and are non-empty.
