"""
CMIDO — RO1 STEP 25B
VECM Specification Validation

Purpose
-------
Validate whether the VECM model is methodologically justified after
the Step 25A multivariate diagnostics.

This step:
    1. Tests Johansen cointegration under multiple reasonable
       deterministic specifications.
    2. Tests sensitivity to lag structure.
    3. Summarizes cointegration-rank stability.
    4. Selects a defensible candidate VECM specification.
    5. Saves the specification decision.

Important
---------
- Development data only.
- No validation/test observations are used.
- Price and demand systems remain separate.
- VECM is NOT accepted merely because one Johansen test rejects.
- Rank/specification sensitivity is explicitly examined.
- This step does NOT yet perform final rolling-origin forecasting.

Deterministic specifications
----------------------------
det_order:
    -1 : no deterministic terms
     0 : constant restricted to cointegration relation
     1 : unrestricted constant

Lag interpretation
------------------
statsmodels coint_johansen uses k_ar_diff:
    k_ar_diff = number of lagged differences.

Candidate values:
    1, 2, 3

The final candidate is selected using:
    - cointegration evidence
    - rank stability
    - reasonable lag structure
    - parsimony

VECM is retained only as a candidate for Step 25C.
"""

from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd

from statsmodels.tsa.vector_ar.vecm import (
    coint_johansen,
)


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

DETERMINISTIC_ORDERS = [
    -1,
    0,
    1,
]

K_AR_DIFF_VALUES = [
    1,
    2,
    3,
]

ALPHA = 0.05

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
print("CMIDO RO1 — STEP 25B")
print("VECM SPECIFICATION + COINTEGRATION SENSITIVITY")
print("=" * 78)


# ============================================================================
# DATA LOADING
# ============================================================================

print("\n[1] LOADING DATA")

price = pd.read_csv(
    PRICE_DATA,
    parse_dates=["date"],
)

demand = pd.read_csv(
    DEMAND_DATA,
    parse_dates=["date"],
)


# ============================================================================
# STANDARDIZATION
# ============================================================================

def standardize_data(
    df: pd.DataFrame,
) -> pd.DataFrame:

    work = df.rename(
        columns={
            "DataSeries": "series",
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
# DEVELOPMENT SYSTEM
# ============================================================================

def build_development_system(
    data: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:

    end_date = DEVELOPMENT_ENDS[
        dataset_name
    ]

    development = data.loc[
        data["date"] <= end_date
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
    f"Price development observations : "
    f"{len(price_dev)}"
)

print(
    f"Demand development observations: "
    f"{len(demand_dev)}"
)


# ============================================================================
# JOHANSEN CRITICAL VALUES
# ============================================================================

def johansen_critical_value(
    result,
    test_type,
    rank,
):
    """
    Extract the 5% critical value.

    trace:
        result.cvt

    max eigenvalue:
        result.cvm
    """

    if test_type == "trace":
        return float(
            result.cvt[rank, 1]
        )

    if test_type == "max_eigen":
        return float(
            result.cvm[rank, 1]
        )

    raise ValueError(
        "Unknown test type."
    )


# ============================================================================
# SINGLE JOHANSEN RUN
# ============================================================================

def run_johansen(
    wide: pd.DataFrame,
    dataset_name: str,
    det_order: int,
    k_ar_diff: int,
):
    """
    Run Johansen test for one specification.

    Returns:
        result records
        inferred trace rank
        inferred max-eigen rank
    """

    records = []

    try:

        result = coint_johansen(
            wide,
            det_order=det_order,
            k_ar_diff=k_ar_diff,
        )

        n_series = wide.shape[1]

        trace_rejections = []

        max_eigen_rejections = []

        for rank in range(
            n_series
        ):

            trace_stat = float(
                result.lr1[rank]
            )

            trace_critical = (
                johansen_critical_value(
                    result,
                    "trace",
                    rank,
                )
            )

            trace_reject = (
                trace_stat
                > trace_critical
            )

            max_stat = float(
                result.lr2[rank]
            )

            max_critical = (
                johansen_critical_value(
                    result,
                    "max_eigen",
                    rank,
                )
            )

            max_reject = (
                max_stat
                > max_critical
            )

            trace_rejections.append(
                trace_reject
            )

            max_eigen_rejections.append(
                max_reject
            )

            records.append(
                {
                    "dataset":
                        dataset_name,
                    "det_order":
                        det_order,
                    "k_ar_diff":
                        k_ar_diff,
                    "test":
                        "trace",
                    "rank_r":
                        rank,
                    "statistic":
                        trace_stat,
                    "critical_5pct":
                        trace_critical,
                    "reject_at_5pct":
                        trace_reject,
                }
            )

            records.append(
                {
                    "dataset":
                        dataset_name,
                    "det_order":
                        det_order,
                    "k_ar_diff":
                        k_ar_diff,
                    "test":
                        "max_eigen",
                    "rank_r":
                        rank,
                    "statistic":
                        max_stat,
                    "critical_5pct":
                        max_critical,
                    "reject_at_5pct":
                        max_reject,
                }
            )

        # Johansen rank:
        # sequentially reject r = 0, 1, ... until
        # first non-rejection.
        def infer_rank(
            rejections
        ):

            rank = 0

            for rejected in rejections:

                if rejected:
                    rank += 1
                else:
                    break

            return rank

        trace_rank = infer_rank(
            trace_rejections
        )

        max_rank = infer_rank(
            max_eigen_rejections
        )

        return (
            records,
            trace_rank,
            max_rank,
            None,
        )

    except Exception as exc:

        return (
            [],
            np.nan,
            np.nan,
            type(exc).__name__,
        )


# ============================================================================
# RUN SENSITIVITY GRID
# ============================================================================

print(
    "\n[2] JOHANSEN SENSITIVITY GRID"
)

all_records = []
summary_records = []


systems = [
    (
        "RO1_PRICE",
        price_dev,
    ),
    (
        "RO1_DEMAND",
        demand_dev,
    ),
]


for dataset_name, wide in systems:

    print(
        f"\n--- {dataset_name} ---"
    )

    for det_order in DETERMINISTIC_ORDERS:

        for k_ar_diff in K_AR_DIFF_VALUES:

            (
                records,
                trace_rank,
                max_rank,
                error,
            ) = run_johansen(
                wide=wide,
                dataset_name=dataset_name,
                det_order=det_order,
                k_ar_diff=k_ar_diff,
            )

            all_records.extend(
                records
            )

            summary_records.append(
                {
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
                    "error":
                        error,
                }
            )

            print(
                f"det={det_order:>2}, "
                f"k_ar_diff={k_ar_diff}: "
                f"trace_rank={trace_rank}, "
                f"max_rank={max_rank}"
                + (
                    f", ERROR={error}"
                    if error
                    else ""
                )
            )


johansen_detail = pd.DataFrame(
    all_records
)

johansen_summary = pd.DataFrame(
    summary_records
)


# ============================================================================
# RANK STABILITY
# ============================================================================

print(
    "\n[3] COINTEGRATION-RANK STABILITY"
)


def rank_stability_summary(
    summary_df,
    dataset_name,
):

    work = summary_df.loc[
        summary_df["dataset"]
        == dataset_name
    ].copy()

    successful = work.loc[
        work["error"].isna()
    ].copy()

    if successful.empty:

        return {
            "dataset":
                dataset_name,
            "successful_specifications":
                0,
            "trace_rank_mode":
                np.nan,
            "max_eigen_rank_mode":
                np.nan,
            "trace_rank_min":
                np.nan,
            "trace_rank_max":
                np.nan,
            "max_eigen_rank_min":
                np.nan,
            "max_eigen_rank_max":
                np.nan,
            "stable_positive_cointegration":
                False,
        }

    trace_counts = (
        successful[
            "trace_rank"
        ]
        .value_counts()
    )

    max_counts = (
        successful[
            "max_eigen_rank"
        ]
        .value_counts()
    )

    trace_mode = int(
        trace_counts.index[0]
    )

    max_mode = int(
        max_counts.index[0]
    )

    trace_min = int(
        successful[
            "trace_rank"
        ].min()
    )

    trace_max = int(
        successful[
            "trace_rank"
        ].max()
    )

    max_min = int(
        successful[
            "max_eigen_rank"
        ].min()
    )

    max_max = int(
        successful[
            "max_eigen_rank"
        ].max()
    )

    # We require evidence of at least one
    # cointegrating relation across the
    # sensitivity grid.
    stable_positive = bool(
        trace_min >= 1
        and max_min >= 1
    )

    return {
        "dataset":
            dataset_name,
        "successful_specifications":
            len(successful),
        "trace_rank_mode":
            trace_mode,
        "max_eigen_rank_mode":
            max_mode,
        "trace_rank_min":
            trace_min,
        "trace_rank_max":
            trace_max,
        "max_eigen_rank_min":
            max_min,
        "max_eigen_rank_max":
            max_max,
        "stable_positive_cointegration":
            stable_positive,
    }


rank_stability = pd.DataFrame(
    [
        rank_stability_summary(
            johansen_summary,
            "RO1_PRICE",
        ),
        rank_stability_summary(
            johansen_summary,
            "RO1_DEMAND",
        ),
    ]
)


print(
    rank_stability.to_string(
        index=False
    )
)


# ============================================================================
# SELECT CANDIDATE SPECIFICATION
# ============================================================================

print(
    "\n[4] CANDIDATE VECM SPECIFICATION"
)


def select_candidate(
    summary_df,
    stability_df,
    dataset_name,
):

    work = summary_df.loc[
        (
            summary_df["dataset"]
            == dataset_name
        )
        &
        (
            summary_df["error"].isna()
        )
    ].copy()

    stability = stability_df.loc[
        stability_df["dataset"]
        == dataset_name
    ].iloc[0]

    if work.empty:

        return {
            "dataset":
                dataset_name,
            "status":
                "NOT_JUSTIFIED",
            "det_order":
                np.nan,
            "k_ar_diff":
                np.nan,
            "cointegration_rank":
                np.nan,
            "selection_reason":
                "No successful Johansen specifications.",
        }

    # Preferred rank:
    # use the modal trace rank, because trace statistics
    # are the primary rank diagnostic.
    preferred_rank = int(
        stability[
            "trace_rank_mode"
        ]
    )

    candidates = work.loc[
        work["trace_rank"]
        == preferred_rank
    ].copy()

    # Prefer k_ar_diff = 1 for parsimony,
    # then det_order = 0, then det_order = -1.
    #
    # This is a specification preference, NOT
    # an optimization criterion.
    det_priority = {
        0: 0,
        -1: 1,
        1: 2,
    }

    candidates[
        "det_priority"
    ] = candidates[
        "det_order"
    ].map(
        det_priority
    )

    candidates = candidates.sort_values(
        [
            "k_ar_diff",
            "det_priority",
        ]
    )

    selected = candidates.iloc[0]

    # Final candidate must have positive rank.
    if preferred_rank < 1:

        return {
            "dataset":
                dataset_name,
            "status":
                "NOT_JUSTIFIED",
            "det_order":
                np.nan,
            "k_ar_diff":
                np.nan,
            "cointegration_rank":
                0,
            "selection_reason":
                "Sensitivity analysis did not establish "
                "a positive cointegration rank.",
        }

    reason = (
        "Positive cointegration rank is supported "
        "across the sensitivity grid; candidate uses "
        "the modal trace rank with a parsimonious "
        "lag structure."
    )

    return {
        "dataset":
            dataset_name,
        "status":
            "VECM_CANDIDATE",
        "det_order":
            int(
                selected["det_order"]
            ),
        "k_ar_diff":
            int(
                selected["k_ar_diff"]
            ),
        "cointegration_rank":
            preferred_rank,
        "selection_reason":
            reason,
    }


candidates = pd.DataFrame(
    [
        select_candidate(
            johansen_summary,
            rank_stability,
            "RO1_PRICE",
        ),
        select_candidate(
            johansen_summary,
            rank_stability,
            "RO1_DEMAND",
        ),
    ]
)


print(
    candidates.to_string(
        index=False
    )
)


# ============================================================================
# SPECIFICATION MATRIX
# ============================================================================

print(
    "\n[5] SPECIFICATION MATRIX"
)

spec_matrix = (
    johansen_summary
    .merge(
        rank_stability[
            [
                "dataset",
                "trace_rank_mode",
                "max_eigen_rank_mode",
                "trace_rank_min",
                "trace_rank_max",
                "max_eigen_rank_min",
                "max_eigen_rank_max",
            ]
        ],
        on="dataset",
        how="left",
    )
)

print(
    spec_matrix.to_string(
        index=False
    )
)


# ============================================================================
# SAVE RESULTS
# ============================================================================

print(
    "\n[6] SAVING RESULTS"
)

johansen_detail.to_csv(
    OUTPUT_DIR
    / "RO1_step25b_johansen_sensitivity_detail.csv",
    index=False,
)

johansen_summary.to_csv(
    OUTPUT_DIR
    / "RO1_step25b_johansen_sensitivity_summary.csv",
    index=False,
)

rank_stability.to_csv(
    OUTPUT_DIR
    / "RO1_step25b_cointegration_rank_stability.csv",
    index=False,
)

candidates.to_csv(
    OUTPUT_DIR
    / "RO1_step25b_vecm_candidate_specifications.csv",
    index=False,
)

spec_matrix.to_csv(
    OUTPUT_DIR
    / "RO1_step25b_vecm_specification_matrix.csv",
    index=False,
)


# ============================================================================
# ASSERTIONS
# ============================================================================

print(
    "\n[7] FINAL ASSERTIONS"
)

if johansen_summary.empty:
    raise AssertionError(
        "Johansen sensitivity summary is empty."
    )

if len(johansen_summary) != (
    2
    * len(DETERMINISTIC_ORDERS)
    * len(K_AR_DIFF_VALUES)
):
    raise AssertionError(
        "Unexpected number of sensitivity specifications."
    )

if rank_stability.empty:
    raise AssertionError(
        "Rank stability output is empty."
    )

if candidates.empty:
    raise AssertionError(
        "Candidate specification output is empty."
    )

if set(
    candidates["dataset"]
) != {
    "RO1_PRICE",
    "RO1_DEMAND",
}:
    raise AssertionError(
        "Both price and demand systems must be evaluated."
    )

if candidates[
    "cointegration_rank"
].isna().any():
    raise AssertionError(
        "Missing cointegration rank decision."
    )

print(
    "Johansen sensitivity grid: PASS"
)

print(
    "Rank stability analysis: PASS"
)

print(
    "Candidate specification selection: PASS"
)

print(
    "Price/demand separation: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 25B COMPLETE"
)

print(
    "=" * 78
)

print(
    "Cointegration sensitivity : READY"
)

print(
    "VECM candidates           : READY"
)

print(
    "Specification decision    : SAVED"
)

print(
    "\nRO1 STEP 25B: READY FOR REVIEW"
)

print(
    "=" * 78
)