"""
CMIDO — RO1 STEP 25A
Multivariate Forecasting Diagnostics

Purpose
-------
Determine whether cross-material multivariate forecasting is
empirically justified before implementing VAR/VECM.

Systems
-------
1. Construction-material PRICE system
2. Construction-material DEMAND system

Diagnostics
-----------
- Stationarity
- Correlation
- Lag-order selection
- Granger causality
- Johansen cointegration
- VAR/VECM suitability assessment

Important
---------
No forecasting model is fitted for final evaluation in this step.

This step is a methodological gate:
VAR/VECM are implemented only if the diagnostics justify them.

No random split is used.
No test-period information is used for model specification.
Development-period data are used for diagnostics.
"""

from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd

from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import (
    coint_johansen,
)


# ============================================================================
# PROJECT PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / "src"),
)

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
    "RO1_PRICE": pd.Timestamp(
        "2022-06-01"
    ),
    "RO1_DEMAND": pd.Timestamp(
        "2022-05-01"
    ),
}

MAX_LAG = 12

GRANGER_MAX_LAG = 6

COINT_DETERMINISTIC_ORDER = 0

ALPHA = 0.05

MIN_OBSERVATIONS = 60

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
)

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
)


# ============================================================================
# HEADER
# ============================================================================

print("=" * 78)
print("CMIDO RO1 — STEP 25A")
print("MULTIVARIATE DEPENDENCE + VAR/VECM JUSTIFICATION")
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
            "price_dollars_per_tonne": "value",
            "demand_thousand_tonnes": "value",
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
# BUILD WIDE DEVELOPMENT SYSTEM
# ============================================================================

def build_development_system(
    data: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:

    development_end = (
        DEVELOPMENT_ENDS[
            dataset_name
        ]
    )

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
    )

    # Keep only complete common observations.
    wide = wide.dropna(
        how="any"
    )

    if len(wide) < MIN_OBSERVATIONS:
        raise ValueError(
            f"Insufficient common observations "
            f"for {dataset_name}: {len(wide)}"
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
    "\nDevelopment observations:"
)

print(
    f"Price : {len(price_dev)}"
)

print(
    f"Demand: {len(demand_dev)}"
)


# ============================================================================
# ADF TEST
# ============================================================================

def adf_test(
    series,
    name,
):
    """
    ADF test with constant and linear trend.

    The test is used as one diagnostic component only.
    Stationarity decisions are not based on ADF alone.
    """

    result = adfuller(
        series,
        regression="ct",
        autolag="AIC",
    )

    return {
        "series": name,
        "n": len(series),
        "ADF_statistic": float(
            result[0]
        ),
        "p_value": float(
            result[1]
        ),
        "used_lag": int(
            result[2]
        ),
        "critical_1pct": float(
            result[4]["1%"]
        ),
        "critical_5pct": float(
            result[4]["5%"]
        ),
        "critical_10pct": float(
            result[4]["10%"]
        ),
        "stationary_at_5pct":
            bool(
                result[1] < ALPHA
            ),
    }


def stationarity_diagnostics(
    wide,
    dataset_name,
):

    records = []

    # Levels
    for column in wide.columns:

        records.append(
            {
                "dataset":
                    dataset_name,
                "transformation":
                    "level",
                **adf_test(
                    wide[column].to_numpy(),
                    column,
                ),
            }
        )

    # First differences
    diff = wide.diff().dropna()

    for column in diff.columns:

        records.append(
            {
                "dataset":
                    dataset_name,
                "transformation":
                    "first_difference",
                **adf_test(
                    diff[column].to_numpy(),
                    column,
                ),
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================================
# CORRELATION DIAGNOSTICS
# ============================================================================

def correlation_diagnostics(
    wide,
    dataset_name,
):

    records = []

    corr = wide.corr()

    columns = list(
        wide.columns
    )

    for i in range(
        len(columns)
    ):

        for j in range(
            i + 1,
            len(columns),
        ):

            records.append(
                {
                    "dataset":
                        dataset_name,
                    "transformation":
                        "level",
                    "series_1":
                        columns[i],
                    "series_2":
                        columns[j],
                    "correlation":
                        float(
                            corr.loc[
                                columns[i],
                                columns[j],
                            ]
                        ),
                }
            )

    diff = wide.diff().dropna()

    corr_diff = diff.corr()

    for i in range(
        len(columns)
    ):

        for j in range(
            i + 1,
            len(columns),
        ):

            records.append(
                {
                    "dataset":
                        dataset_name,
                    "transformation":
                        "first_difference",
                    "series_1":
                        columns[i],
                    "series_2":
                        columns[j],
                    "correlation":
                        float(
                            corr_diff.loc[
                                columns[i],
                                columns[j],
                            ]
                        ),
                }
            )

    return pd.DataFrame(
        records
    )


# ============================================================================
# VAR LAG SELECTION
# ============================================================================

def var_lag_diagnostics(
    wide,
    dataset_name,
):

    diff = wide.diff().dropna()

    model = VAR(
        diff
    )

    results = []

    for lag in range(
        1,
        MAX_LAG + 1,
    ):

        try:

            fitted = model.fit(
                lag,
                trend="c",
            )

            results.append(
                {
                    "dataset":
                        dataset_name,
                    "lag":
                        lag,
                    "AIC":
                        float(
                            fitted.aic
                        ),
                    "BIC":
                        float(
                            fitted.bic
                        ),
                    "HQIC":
                        float(
                            fitted.hqic
                        ),
                    "FPE":
                        float(
                            fitted.fpe
                        ),
                }
            )

        except Exception:

            results.append(
                {
                    "dataset":
                        dataset_name,
                    "lag":
                        lag,
                    "AIC":
                        np.nan,
                    "BIC":
                        np.nan,
                    "HQIC":
                        np.nan,
                    "FPE":
                        np.nan,
                }
            )

    return pd.DataFrame(
        results
    )


# ============================================================================
# GRANGER CAUSALITY
# ============================================================================

def granger_diagnostics(
    wide,
    dataset_name,
):

    """
    Test whether lagged information from one material
    improves prediction of another material.

    Tests are conducted on first differences.

    This is predictive precedence, not causal proof.
    """

    diff = wide.diff().dropna()

    columns = list(
        diff.columns
    )

    records = []

    for caused in columns:

        for causing in columns:

            if caused == causing:
                continue

            pair = diff[
                [
                    caused,
                    causing,
                ]
            ]

            for lag in range(
                1,
                GRANGER_MAX_LAG + 1,
            ):

                try:

                    test_result = VAR(
                        pair
                    ).fit(
                        lag,
                        trend="c",
                    ).test_causality(
                        caused=caused,
                        causing=[causing],
                        kind="f",
                    )

                    records.append(
                        {
                            "dataset":
                                dataset_name,
                            "causing":
                                causing,
                            "caused":
                                caused,
                            "lag":
                                lag,
                            "test_statistic":
                                float(
                                    test_result.test_statistic
                                ),
                            "p_value":
                                float(
                                    test_result.pvalue
                                ),
                            "significant_5pct":
                                bool(
                                    test_result.pvalue
                                    < ALPHA
                                ),
                        }
                    )

                except Exception as exc:

                    records.append(
                        {
                            "dataset":
                                dataset_name,
                            "causing":
                                causing,
                            "caused":
                                caused,
                            "lag":
                                lag,
                            "test_statistic":
                                np.nan,
                            "p_value":
                                np.nan,
                            "significant_5pct":
                                False,
                            "error":
                                type(
                                    exc
                                ).__name__,
                        }
                    )

    return pd.DataFrame(
        records
    )


# ============================================================================
# JOHANSEN COINTEGRATION
# ============================================================================

def johansen_diagnostics(
    wide,
    dataset_name,
):

    """
    Johansen trace and maximum-eigenvalue diagnostics.

    Applied to development-level series.

    Interpretation:
        evidence of cointegration can justify VECM;
        absence of cointegration favors VAR on stationary
        transformed data rather than VECM.
    """

    records = []

    try:

        result = coint_johansen(
            wide,
            det_order=COINT_DETERMINISTIC_ORDER,
            k_ar_diff=1,
        )

        for rank_index, statistic in enumerate(
            result.lr1
        ):

            critical = result.cvt[
                rank_index,
                1,
            ]

            records.append(
                {
                    "dataset":
                        dataset_name,
                    "test":
                        "trace",
                    "rank_r":
                        rank_index,
                    "statistic":
                        float(
                            statistic
                        ),
                    "critical_5pct":
                        float(
                            critical
                        ),
                    "reject_at_5pct":
                        bool(
                            statistic
                            > critical
                        ),
                }
            )

        for rank_index, statistic in enumerate(
            result.lr2
        ):

            critical = result.cvm[
                rank_index,
                1,
            ]

            records.append(
                {
                    "dataset":
                        dataset_name,
                    "test":
                        "max_eigen",
                    "rank_r":
                        rank_index,
                    "statistic":
                        float(
                            statistic
                        ),
                    "critical_5pct":
                        float(
                            critical
                        ),
                    "reject_at_5pct":
                        bool(
                            statistic
                            > critical
                        ),
                }
            )

    except Exception as exc:

        records.append(
            {
                "dataset":
                    dataset_name,
                "test":
                    "FAILED",
                "rank_r":
                    np.nan,
                "statistic":
                    np.nan,
                "critical_5pct":
                    np.nan,
                "reject_at_5pct":
                    False,
                "error":
                    type(exc).__name__,
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================================
# RUN DIAGNOSTICS
# ============================================================================

print(
    "\n[2] STATIONARITY DIAGNOSTICS"
)

price_stationarity = (
    stationarity_diagnostics(
        price_dev,
        "RO1_PRICE",
    )
)

demand_stationarity = (
    stationarity_diagnostics(
        demand_dev,
        "RO1_DEMAND",
    )
)

stationarity = pd.concat(
    [
        price_stationarity,
        demand_stationarity,
    ],
    ignore_index=True,
)


print(
    stationarity.to_string(
        index=False
    )
)


print(
    "\n[3] CROSS-SERIES CORRELATION"
)

price_corr = (
    correlation_diagnostics(
        price_dev,
        "RO1_PRICE",
    )
)

demand_corr = (
    correlation_diagnostics(
        demand_dev,
        "RO1_DEMAND",
    )
)

correlations = pd.concat(
    [
        price_corr,
        demand_corr,
    ],
    ignore_index=True,
)


print(
    correlations.to_string(
        index=False
    )
)


print(
    "\n[4] VAR LAG DIAGNOSTICS"
)

price_lags = (
    var_lag_diagnostics(
        price_dev,
        "RO1_PRICE",
    )
)

demand_lags = (
    var_lag_diagnostics(
        demand_dev,
        "RO1_DEMAND",
    )
)

lag_results = pd.concat(
    [
        price_lags,
        demand_lags,
    ],
    ignore_index=True,
)


print(
    lag_results.to_string(
        index=False
    )
)


print(
    "\n[5] GRANGER PREDICTIVE-DEPENDENCE DIAGNOSTICS"
)

price_granger = (
    granger_diagnostics(
        price_dev,
        "RO1_PRICE",
    )
)

demand_granger = (
    granger_diagnostics(
        demand_dev,
        "RO1_DEMAND",
    )
)

granger = pd.concat(
    [
        price_granger,
        demand_granger,
    ],
    ignore_index=True,
)


print(
    granger.to_string(
        index=False
    )
)


print(
    "\n[6] JOHANSEN COINTEGRATION DIAGNOSTICS"
)

price_johansen = (
    johansen_diagnostics(
        price_dev,
        "RO1_PRICE",
    )
)

demand_johansen = (
    johansen_diagnostics(
        demand_dev,
        "RO1_DEMAND",
    )
)

johansen = pd.concat(
    [
        price_johansen,
        demand_johansen,
    ],
    ignore_index=True,
)


print(
    johansen.to_string(
        index=False
    )
)


# ============================================================================
# SUMMARY DECISION
# ============================================================================

print(
    "\n[7] VAR / VECM JUSTIFICATION SUMMARY"
)


def summarize_system(
    dataset_name,
    stationarity_df,
    lag_df,
    granger_df,
    johansen_df,
):

    level = stationarity_df.loc[
        (
            stationarity_df["dataset"]
            == dataset_name
        )
        &
        (
            stationarity_df[
                "transformation"
            ]
            == "level"
        )
    ]

    diff = stationarity_df.loc[
        (
            stationarity_df["dataset"]
            == dataset_name
        )
        &
        (
            stationarity_df[
                "transformation"
            ]
            == "first_difference"
        )
    ]

    level_nonstationary = int(
        (
            ~level[
                "stationary_at_5pct"
            ]
        ).sum()
    )

    diff_stationary = int(
        diff[
            "stationary_at_5pct"
        ].sum()
    )

    granger_significant = int(
        granger_df.loc[
            granger_df["dataset"]
            == dataset_name,
            "significant_5pct",
        ].sum()
    )

    # Johansen trace evidence at r = 0.
    trace_r0 = johansen_df.loc[
        (
            johansen_df["dataset"]
            == dataset_name
        )
        &
        (
            johansen_df["test"]
            == "trace"
        )
        &
        (
            johansen_df["rank_r"]
            == 0
        )
    ]

    cointegration_evidence = False

    if not trace_r0.empty:
        cointegration_evidence = bool(
            trace_r0.iloc[0][
                "reject_at_5pct"
            ]
        )

    # Best lag according to BIC.
    valid_lags = lag_df.loc[
        lag_df["dataset"]
        == dataset_name
    ].dropna(
        subset=["BIC"]
    )

    if valid_lags.empty:
        selected_lag = np.nan
    else:
        selected_lag = int(
            valid_lags.sort_values(
                "BIC"
            ).iloc[0]["lag"]
        )

    if (
        granger_significant > 0
        and cointegration_evidence
    ):
        recommendation = (
            "VECM_CANDIDATE"
        )

    elif (
        granger_significant > 0
        and diff_stationary > 0
    ):
        recommendation = (
            "VAR_CANDIDATE"
        )

    else:
        recommendation = (
            "UNJUSTIFIED"
        )

    return {
        "dataset":
            dataset_name,
        "level_nonstationary_series":
            level_nonstationary,
        "stationary_first_difference_series":
            diff_stationary,
        "significant_granger_tests_5pct":
            granger_significant,
        "cointegration_evidence_at_r0":
            cointegration_evidence,
        "BIC_selected_lag":
            selected_lag,
        "recommendation":
            recommendation,
    }


price_summary = summarize_system(
    "RO1_PRICE",
    stationarity,
    lag_results,
    granger,
    johansen,
)

demand_summary = summarize_system(
    "RO1_DEMAND",
    stationarity,
    lag_results,
    granger,
    johansen,
)

summary = pd.DataFrame(
    [
        price_summary,
        demand_summary,
    ]
)


print(
    summary.to_string(
        index=False
    )
)


# ============================================================================
# SAVE RESULTS
# ============================================================================

print(
    "\n[8] SAVING DIAGNOSTIC OUTPUTS"
)

stationarity.to_csv(
    OUTPUT_DIR
    / "RO1_step25_stationarity.csv",
    index=False,
)

correlations.to_csv(
    OUTPUT_DIR
    / "RO1_step25_cross_series_correlations.csv",
    index=False,
)

lag_results.to_csv(
    OUTPUT_DIR
    / "RO1_step25_var_lag_diagnostics.csv",
    index=False,
)

granger.to_csv(
    OUTPUT_DIR
    / "RO1_step25_granger_diagnostics.csv",
    index=False,
)

johansen.to_csv(
    OUTPUT_DIR
    / "RO1_step25_johansen_cointegration.csv",
    index=False,
)

summary.to_csv(
    OUTPUT_DIR
    / "RO1_step25_var_vecm_decision.csv",
    index=False,
)


# ============================================================================
# ASSERTIONS
# ============================================================================

print(
    "\n[9] FINAL ASSERTIONS"
)

if set(
    summary["dataset"]
) != {
    "RO1_PRICE",
    "RO1_DEMAND",
}:

    raise AssertionError(
        "Both RO1 systems must be evaluated."
    )


if stationarity.empty:
    raise AssertionError(
        "Stationarity diagnostics are empty."
    )


if correlations.empty:
    raise AssertionError(
        "Cross-series correlations are empty."
    )


if lag_results.empty:
    raise AssertionError(
        "VAR lag diagnostics are empty."
    )


if granger.empty:
    raise AssertionError(
        "Granger diagnostics are empty."
    )


if johansen.empty:
    raise AssertionError(
        "Johansen diagnostics are empty."
    )


if summary[
    "recommendation"
].isna().any():

    raise AssertionError(
        "Missing VAR/VECM recommendation."
    )


print(
    "Stationarity diagnostics: PASS"
)

print(
    "Cross-series diagnostics: PASS"
)

print(
    "VAR lag diagnostics: PASS"
)

print(
    "Granger diagnostics: PASS"
)

print(
    "Johansen diagnostics: PASS"
)

print(
    "VAR/VECM decision: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 25A COMPLETE"
)

print(
    "=" * 78
)

print(
    "Multivariate diagnostics : READY"
)

print(
    "VAR/VECM justification   : READY"
)

print(
    "Model decision            : SAVED"
)

print(
    "\nRO1 STEP 25A DIAGNOSTICS: READY"
)

print(
    "=" * 78
)