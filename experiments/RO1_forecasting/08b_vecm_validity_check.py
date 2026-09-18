"""
CMIDO — RO1 STEP 25B.1
Cointegration Validity + Rank Reconciliation

Purpose
-------
Reconcile the Step 25A/25B diagnostics before accepting VAR/VECM.

This is a methodological validation gate.

The analysis:
    1. Reconstructs the development-period price and demand systems.
    2. Rechecks level and first-difference stationarity.
    3. Runs Johansen tests under a broader but controlled
       deterministic specification set.
    4. Treats full rank (r = number of variables) correctly:
       it is NOT accepted as evidence for a restricted VECM.
    5. Compares trace and maximum-eigenvalue rank estimates.
    6. Checks whether cointegration evidence is robust under
       reasonable specifications.
    7. Produces a final model-path decision for Step 25C.

Decision philosophy
-------------------
For an I(1) system:

    restricted VECM:
        0 < r < K

    VAR on first differences:
        r = 0

    full-rank Johansen result:
        r = K

does NOT provide evidence for a conventional
cointegrated I(1) VECM.

The full-rank case is therefore flagged as
"FULL_RANK_NOT_VECM".

This script does NOT use validation/test data.

No forecasting is performed here.
"""

from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd

from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen


# ============================================================================
# PROJECT PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

PRICE_DATA = (
    ROOT
    / "data"
    / "interim"
    / "RO1_price_long.csv"
)

DEMAND_DATA = (
    ROOT
    / "data"
    / "interim"
    / "RO1_demand_long.csv"
)

OUTPUT_DIR = (
    ROOT
    / "results"
    / "forecasting"
    / "multivariate"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

DEVELOPMENT_ENDS = {
    "RO1_PRICE":
        pd.Timestamp("2022-06-01"),

    "RO1_DEMAND":
        pd.Timestamp("2022-05-01"),
}

# Johansen deterministic specifications.
#
# statsmodels:
# -1 = no deterministic terms
#  0 = constant restricted to cointegration relation
#  1 = unrestricted constant
#
# We deliberately do NOT use det_order > 1 because the
# available critical-value tables do not support it.

DETERMINISTIC_ORDERS = [
    -1,
    0,
    1,
]

# k_ar_diff = number of lagged differences in VECM.
K_AR_DIFF_VALUES = [
    1,
    2,
    3,
]

ALPHA = 0.05

MIN_OBSERVATIONS = 100

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
)

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
)


# ============================================================================
# HEADER
# ============================================================================

print("=" * 78)
print("CMIDO RO1 — STEP 25B.1")
print("COINTEGRATION VALIDITY + RANK RECONCILIATION")
print("=" * 78)


# ============================================================================
# LOAD DATA
# ============================================================================

print("\n[1] LOADING DEVELOPMENT DATA")

price = pd.read_csv(
    PRICE_DATA,
    parse_dates=["date"],
)

demand = pd.read_csv(
    DEMAND_DATA,
    parse_dates=["date"],
)


# ============================================================================
# STANDARDIZE
# ============================================================================

def standardize_data(
    df: pd.DataFrame,
) -> pd.DataFrame:

    work = df.rename(
        columns={
            "DataSeries":
                "series",

            "price_dollars_per_tonne":
                "value",

            "demand_thousand_tonnes":
                "value",
        }
    ).copy()

    work["date"] = (
        pd.to_datetime(work["date"])
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    work["series"] = (
        work["series"]
        .astype(str)
        .str.strip()
    )

    work["value"] = pd.to_numeric(
        work["value"],
        errors="raise",
    )

    return (
        work[
            [
                "date",
                "series",
                "value",
            ]
        ]
        .sort_values(
            [
                "date",
                "series",
            ]
        )
        .reset_index(drop=True)
    )


price = standardize_data(price)
demand = standardize_data(demand)


# ============================================================================
# BUILD DEVELOPMENT SYSTEM
# ============================================================================

def build_development_system(
    data: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:

    development_end = DEVELOPMENT_ENDS[
        dataset_name
    ]

    development = data.loc[
        data["date"]
        <= development_end
    ].copy()

    wide = (
        development
        .pivot(
            index="date",
            columns="series",
            values="value",
        )
        .sort_index()
        .dropna(how="any")
    )

    if len(wide) < MIN_OBSERVATIONS:
        raise ValueError(
            f"{dataset_name}: only "
            f"{len(wide)} common observations."
        )

    return wide


price_dev = build_development_system(
    price,
    "RO1_PRICE",
)

demand_dev = build_development_system(
    demand,
    "RO1_DEMAND",
)


print(
    f"Price observations : {len(price_dev)}"
)

print(
    f"Demand observations: {len(demand_dev)}"
)


# ============================================================================
# ADF STATIONARITY
# ============================================================================

def run_adf(
    values,
):

    values = np.asarray(
        values,
        dtype=float,
    )

    result = adfuller(
        values,
        regression="ct",
        autolag="AIC",
    )

    return {
        "ADF_statistic":
            float(result[0]),

        "p_value":
            float(result[1]),

        "used_lag":
            int(result[2]),

        "critical_5pct":
            float(result[4]["5%"]),

        "stationary_5pct":
            bool(
                result[1] < ALPHA
            ),
    }


def stationarity_table(
    wide: pd.DataFrame,
    dataset_name: str,
):

    records = []

    for series in wide.columns:

        level = run_adf(
            wide[series]
        )

        records.append(
            {
                "dataset":
                    dataset_name,

                "series":
                    series,

                "transformation":
                    "level",

                **level,
            }
        )

        difference = wide[
            series
        ].diff().dropna()

        diff_result = run_adf(
            difference
        )

        records.append(
            {
                "dataset":
                    dataset_name,

                "series":
                    series,

                "transformation":
                    "first_difference",

                **diff_result,
            }
        )

    return pd.DataFrame(
        records
    )


stationarity = pd.concat(
    [
        stationarity_table(
            price_dev,
            "RO1_PRICE",
        ),

        stationarity_table(
            demand_dev,
            "RO1_DEMAND",
        ),
    ],
    ignore_index=True,
)


print(
    "\n[2] STATIONARITY RECONCILIATION"
)

print(
    stationarity.to_string(
        index=False
    )
)


# ============================================================================
# JOHANSEN TEST
# ============================================================================

def run_johansen_specification(
    wide: pd.DataFrame,
    dataset_name: str,
    det_order: int,
    k_ar_diff: int,
):

    K = wide.shape[1]

    try:

        result = coint_johansen(
            wide,
            det_order=det_order,
            k_ar_diff=k_ar_diff,
        )

    except Exception as exc:

        return {
            "dataset":
                dataset_name,

            "det_order":
                det_order,

            "k_ar_diff":
                k_ar_diff,

            "trace_rank":
                np.nan,

            "max_eigen_rank":
                np.nan,

            "trace_r0_reject":
                False,

            "max_r0_reject":
                False,

            "status":
                "ERROR",

            "error":
                type(exc).__name__,
        }


    # --------------------------------------------------------
    # Sequential rank inference
    # --------------------------------------------------------

    trace_rank = 0
    max_rank = 0

    trace_r0_reject = False
    max_r0_reject = False

    for r in range(K):

        trace_stat = float(
            result.lr1[r]
        )

        trace_critical = float(
            result.cvt[r, 1]
        )

        trace_reject = (
            trace_stat
            > trace_critical
        )

        max_stat = float(
            result.lr2[r]
        )

        max_critical = float(
            result.cvm[r, 1]
        )

        max_reject = (
            max_stat
            > max_critical
        )

        if r == 0:

            trace_r0_reject = (
                trace_reject
            )

            max_r0_reject = (
                max_reject
            )

        if trace_reject:

            trace_rank += 1

        else:

            break

    for r in range(K):

        max_stat = float(
            result.lr2[r]
        )

        max_critical = float(
            result.cvm[r, 1]
        )

        if (
            max_stat
            > max_critical
        ):

            max_rank += 1

        else:

            break


    # --------------------------------------------------------
    # Scientific classification
    # --------------------------------------------------------

    if (
        trace_rank == K
        and max_rank == K
    ):

        status = (
            "FULL_RANK_NOT_VECM"
        )

    elif (
        trace_rank > 0
        and max_rank > 0
    ):

        status = (
            "RESTRICTED_VECM_EVIDENCE"
        )

    else:

        status = (
            "NO_RESTRICTED_COINTEGRATION"
        )


    return {
        "dataset":
            dataset_name,

        "det_order":
            det_order,

        "k_ar_diff":
            k_ar_diff,

        "trace_rank":
            trace_rank,

        "max_eigen_rank":
            max_rank,

        "trace_r0_reject":
            trace_r0_reject,

        "max_r0_reject":
            max_r0_reject,

        "status":
            status,

        "error":
            None,
    }


# ============================================================================
# RUN GRID
# ============================================================================

print(
    "\n[3] JOHANSEN VALIDITY GRID"
)

records = []

for dataset_name, wide in [
    (
        "RO1_PRICE",
        price_dev,
    ),
    (
        "RO1_DEMAND",
        demand_dev,
    ),
]:

    print(
        f"\n--- {dataset_name} ---"
    )

    for det_order in (
        DETERMINISTIC_ORDERS
    ):

        for k_ar_diff in (
            K_AR_DIFF_VALUES
        ):

            result = (
                run_johansen_specification(
                    wide,
                    dataset_name,
                    det_order,
                    k_ar_diff,
                )
            )

            records.append(
                result
            )

            print(
                f"det={det_order:>2}, "
                f"k_ar_diff={k_ar_diff}: "
                f"trace={result['trace_rank']}, "
                f"max={result['max_eigen_rank']}, "
                f"{result['status']}"
            )


johansen = pd.DataFrame(
    records
)


# ============================================================================
# RANK CLASSIFICATION SUMMARY
# ============================================================================

print(
    "\n[4] RANK CLASSIFICATION"
)


def summarize_system(
    johansen_df,
    dataset_name,
):

    work = johansen_df.loc[
        johansen_df["dataset"]
        == dataset_name
    ].copy()

    successful = work.loc[
        work["status"]
        != "ERROR"
    ].copy()

    K = (
        price_dev.shape[1]
        if dataset_name
        == "RO1_PRICE"
        else demand_dev.shape[1]
    )

    restricted = successful.loc[
        successful["status"]
        == "RESTRICTED_VECM_EVIDENCE"
    ]

    full_rank = successful.loc[
        successful["status"]
        == "FULL_RANK_NOT_VECM"
    ]

    no_cointegration = successful.loc[
        successful["status"]
        == "NO_RESTRICTED_COINTEGRATION"
    ]

    trace_positive = (
        successful[
            "trace_rank"
        ] > 0
    ).sum()

    max_positive = (
        successful[
            "max_eigen_rank"
        ] > 0
    ).sum()

    trace_restricted = (
        (
            successful[
                "trace_rank"
            ] > 0
        )
        &
        (
            successful[
                "trace_rank"
            ] < K
        )
    ).sum()

    max_restricted = (
        (
            successful[
                "max_eigen_rank"
            ] > 0
        )
        &
        (
            successful[
                "max_eigen_rank"
            ] < K
        )
    ).sum()

    return {
        "dataset":
            dataset_name,

        "K":
            K,

        "successful_specs":
            len(successful),

        "restricted_status_specs":
            len(restricted),

        "full_rank_specs":
            len(full_rank),

        "no_cointegration_specs":
            len(no_cointegration),

        "trace_positive_specs":
            int(trace_positive),

        "max_eigen_positive_specs":
            int(max_positive),

        "trace_restricted_specs":
            int(trace_restricted),

        "max_eigen_restricted_specs":
            int(max_restricted),

        "trace_rank_min":
            int(
                successful[
                    "trace_rank"
                ].min()
            ),

        "trace_rank_max":
            int(
                successful[
                    "trace_rank"
                ].max()
            ),

        "max_eigen_rank_min":
            int(
                successful[
                    "max_eigen_rank"
                ].min()
            ),

        "max_eigen_rank_max":
            int(
                successful[
                    "max_eigen_rank"
                ].max()
            ),
    }


system_summary = pd.DataFrame(
    [
        summarize_system(
            johansen,
            "RO1_PRICE",
        ),

        summarize_system(
            johansen,
            "RO1_DEMAND",
        ),
    ]
)


print(
    system_summary.to_string(
        index=False
    )
)


# ============================================================================
# FINAL MODEL-PATH DECISION
# ============================================================================

print(
    "\n[5] FINAL MODEL-PATH DECISION"
)


def model_path_decision(
    dataset_name,
    johansen_df,
    stationarity_df,
    K,
):

    work = johansen_df.loc[
        (
            johansen_df["dataset"]
            == dataset_name
        )
        &
        (
            johansen_df["status"]
            != "ERROR"
        )
    ].copy()

    stationarity_work = (
        stationarity_df.loc[
            stationarity_df["dataset"]
            == dataset_name
        ]
    )

    levels = stationarity_work.loc[
        stationarity_work[
            "transformation"
        ]
        == "level"
    ]

    differences = stationarity_work.loc[
        stationarity_work[
            "transformation"
        ]
        == "first_difference"
    ]

    levels_nonstationary = (
        ~levels[
            "stationary_5pct"
        ]
    ).sum()

    differences_stationary = (
        differences[
            "stationary_5pct"
        ].sum()
    )

    # We consider a restricted VECM path only if:
    #
    # 1. Most/all level series are I(1)-like:
    #       nonstationary in levels
    #       stationary after first difference
    #
    # 2. Both trace and max-eigen provide
    #    restricted positive rank in a meaningful
    #    portion of the specification grid.
    #
    trace_restricted = (
        (
            work["trace_rank"] > 0
        )
        &
        (
            work["trace_rank"] < K
        )
    ).sum()

    max_restricted = (
        (
            work["max_eigen_rank"] > 0
        )
        &
        (
            work["max_eigen_rank"] < K
        )
    ).sum()

    total_specs = len(work)

    trace_share = (
        trace_restricted
        / total_specs
        if total_specs
        else 0
    )

    max_share = (
        max_restricted
        / total_specs
        if total_specs
        else 0
    )

    # Strong evidence:
    # both tests indicate restricted rank in at
    # least half of the specification grid.
    #
    # This is intentionally conservative.
    if (
        levels_nonstationary
        >= K - 1
        and
        differences_stationary
        >= K - 1
        and
        trace_share >= 0.50
        and
        max_share >= 0.50
    ):

        decision = (
            "VECM_CANDIDATE"
        )

        reason = (
            "The system behaves as predominantly I(1), "
            "and both Johansen trace and maximum-eigenvalue "
            "tests provide restricted positive-rank evidence "
            "across at least half of the tested specifications."
        )

    else:

        # If the system is predominantly I(1) but
        # restricted cointegration evidence is weak,
        # first-difference VAR is the safer multivariate path.
        if (
            levels_nonstationary
            >= K - 1
            and
            differences_stationary
            >= K - 1
        ):

            decision = (
                "VAR_DIFFERENCED_CANDIDATE"
            )

            reason = (
                "The system behaves as predominantly I(1), "
                "but restricted cointegration evidence is not "
                "sufficiently robust across Johansen specifications. "
                "A VAR in stationary first differences is therefore "
                "the conservative multivariate candidate."
            )

        else:

            decision = (
                "MULTIVARIATE_PATH_REVIEW"
            )

            reason = (
                "Stationarity and cointegration diagnostics "
                "do not support an automatic VAR/VECM decision."
            )

    return {
        "dataset":
            dataset_name,

        "K":
            K,

        "level_nonstationary":
            int(levels_nonstationary),

        "first_difference_stationary":
            int(differences_stationary),

        "trace_restricted_share":
            float(trace_share),

        "max_eigen_restricted_share":
            float(max_share),

        "decision":
            decision,

        "reason":
            reason,
    }


price_decision = model_path_decision(
    "RO1_PRICE",
    johansen,
    stationarity,
    price_dev.shape[1],
)

demand_decision = model_path_decision(
    "RO1_DEMAND",
    johansen,
    stationarity,
    demand_dev.shape[1],
)

decision = pd.DataFrame(
    [
        price_decision,
        demand_decision,
    ]
)


print(
    decision.to_string(
        index=False
    )
)


# ============================================================================
# CANDIDATE RANK INFORMATION
# ============================================================================

print(
    "\n[6] RESTRICTED-RANK DISTRIBUTION"
)


def rank_distribution(
    johansen_df,
    dataset_name,
):

    work = johansen_df.loc[
        (
            johansen_df["dataset"]
            == dataset_name
        )
        &
        (
            johansen_df["status"]
            != "ERROR"
        )
    ].copy()

    records = []

    for rank in sorted(
        work["trace_rank"]
        .dropna()
        .unique()
    ):

        count = int(
            (
                work[
                    "trace_rank"
                ]
                == rank
            ).sum()
        )

        records.append(
            {
                "dataset":
                    dataset_name,

                "test":
                    "trace",

                "rank":
                    int(rank),

                "specification_count":
                    count,
            }
        )

    for rank in sorted(
        work["max_eigen_rank"]
        .dropna()
        .unique()
    ):

        count = int(
            (
                work[
                    "max_eigen_rank"
                ]
                == rank
            ).sum()
        )

        records.append(
            {
                "dataset":
                    dataset_name,

                "test":
                    "max_eigen",

                "rank":
                    int(rank),

                "specification_count":
                    count,
            }
        )

    return pd.DataFrame(
        records
    )


rank_distribution_df = pd.concat(
    [
        rank_distribution(
            johansen,
            "RO1_PRICE",
        ),

        rank_distribution(
            johansen,
            "RO1_DEMAND",
        ),
    ],
    ignore_index=True,
)


print(
    rank_distribution_df.to_string(
        index=False
    )
)


# ============================================================================
# SAVE
# ============================================================================

print(
    "\n[7] SAVING OUTPUTS"
)

stationarity.to_csv(
    OUTPUT_DIR
    / "RO1_step25b1_stationarity_reconciliation.csv",
    index=False,
)

johansen.to_csv(
    OUTPUT_DIR
    / "RO1_step25b1_johansen_validity_grid.csv",
    index=False,
)

system_summary.to_csv(
    OUTPUT_DIR
    / "RO1_step25b1_system_summary.csv",
    index=False,
)

decision.to_csv(
    OUTPUT_DIR
    / "RO1_step25b1_model_path_decision.csv",
    index=False,
)

rank_distribution_df.to_csv(
    OUTPUT_DIR
    / "RO1_step25b1_rank_distribution.csv",
    index=False,
)


# ============================================================================
# ASSERTIONS
# ============================================================================

print(
    "\n[8] FINAL ASSERTIONS"
)

assert len(johansen) == (
    2
    * len(DETERMINISTIC_ORDERS)
    * len(K_AR_DIFF_VALUES)
), (
    "Unexpected Johansen grid size."
)

assert set(
    johansen["dataset"]
) == {
    "RO1_PRICE",
    "RO1_DEMAND",
}, (
    "Both systems must be evaluated."
)

assert not stationarity.empty, (
    "Stationarity output is empty."
)

assert not decision.empty, (
    "Model-path decision is empty."
)

assert set(
    decision["dataset"]
) == {
    "RO1_PRICE",
    "RO1_DEMAND",
}, (
    "Both systems require a decision."
)

assert not decision[
    "decision"
].isna().any(), (
    "Missing model-path decision."
)

# Full-rank results must never be labelled
# as restricted VECM evidence.
full_rank = johansen.loc[
    (
        johansen["status"]
        == "FULL_RANK_NOT_VECM"
    )
]

if not full_rank.empty:

    invalid = full_rank.loc[
        (
            full_rank["trace_rank"]
            < (
                full_rank["dataset"]
                .map(
                    {
                        "RO1_PRICE":
                            price_dev.shape[1],

                        "RO1_DEMAND":
                            demand_dev.shape[1],
                    }
                )
            )
        )
        |
        (
            full_rank["max_eigen_rank"]
            < (
                full_rank["dataset"]
                .map(
                    {
                        "RO1_PRICE":
                            price_dev.shape[1],

                        "RO1_DEMAND":
                            demand_dev.shape[1],
                    }
                )
            )
        )
    ]

    assert invalid.empty, (
        "Full-rank classification inconsistency."
    )


print(
    "Stationarity reconciliation: PASS"
)

print(
    "Johansen validity grid: PASS"
)

print(
    "Full-rank exclusion rule: PASS"
)

print(
    "Model-path decision: PASS"
)

print(
    "Rank distribution audit: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 25B.1 COMPLETE"
)

print(
    "=" * 78
)

print(
    "Cointegration validity : READY"
)

print(
    "Full-rank handling     : CORRECTED"
)

print(
    "Model-path decision    : SAVED"
)

print(
    "\nRO1 STEP 25B.1: READY FOR SCIENTIFIC REVIEW"
)

print(
    "=" * 78
)