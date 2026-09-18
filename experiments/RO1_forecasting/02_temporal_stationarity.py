from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import linregress
from statsmodels.tsa.stattools import adfuller, kpss, acf, pacf
from statsmodels.stats.diagnostic import acorr_ljungbox

warnings.filterwarnings("ignore")


# ============================================================
# CMIDO — RO1 STEP 21B
# TEMPORAL STRUCTURE + STATIONARITY DIAGNOSTICS
# ============================================================

ROOT = Path(r"D:\CMIDO")
INTERIM = ROOT / "data" / "interim"
TABLES = ROOT / "tables"
FIGURES = ROOT / "figures"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)


PRICE_FILE = INTERIM / "RO1_price_long.csv"
DEMAND_FILE = INTERIM / "RO1_demand_long.csv"


print("=" * 78)
print("CMIDO RO1 — STEP 21B")
print("TEMPORAL STRUCTURE + STATIONARITY DIAGNOSTICS")
print("=" * 78)


# ------------------------------------------------------------
# 1. LOAD DATA
# ------------------------------------------------------------

price = pd.read_csv(
    PRICE_FILE,
    parse_dates=["date"],
)

demand = pd.read_csv(
    DEMAND_FILE,
    parse_dates=["date"],
)

price = price.sort_values(
    ["DataSeries", "date"]
).reset_index(drop=True)

demand = demand.sort_values(
    ["DataSeries", "date"]
).reset_index(drop=True)


print("\n[1] DATA")
print("Price rows :", len(price))
print("Demand rows:", len(demand))


# ------------------------------------------------------------
# 2. DIAGNOSTIC FUNCTIONS
# ------------------------------------------------------------

def adf_test(x):
    x = pd.Series(x).dropna()

    result = adfuller(
        x,
        autolag="AIC",
    )

    return {
        "adf_stat": result[0],
        "adf_pvalue": result[1],
        "adf_lags": result[2],
        "adf_nobs": result[3],
    }


def kpss_test(x):
    x = pd.Series(x).dropna()

    try:
        result = kpss(
            x,
            regression="c",
            nlags="auto",
        )

        return {
            "kpss_stat": result[0],
            "kpss_pvalue": result[1],
            "kpss_lags": result[2],
        }

    except Exception:
        return {
            "kpss_stat": np.nan,
            "kpss_pvalue": np.nan,
            "kpss_lags": np.nan,
        }


def ljung_box_test(x, lag=12):
    x = pd.Series(x).dropna()

    result = acorr_ljungbox(
        x,
        lags=[lag],
        return_df=True,
    )

    return {
        "lb_lag": lag,
        "lb_stat": result["lb_stat"].iloc[0],
        "lb_pvalue": result["lb_pvalue"].iloc[0],
    }


def trend_test(x, dates):
    x = pd.Series(x).reset_index(drop=True)
    t = np.arange(len(x))

    result = linregress(t, x)

    return {
        "trend_slope_per_month": result.slope,
        "trend_pvalue": result.pvalue,
        "trend_r_squared": result.rvalue ** 2,
    }


def seasonal_strength(x, period=12):

    x = pd.Series(x).dropna()

    if len(x) < 2 * period:
        return np.nan

    # Classical additive seasonal decomposition implemented
    # without modifying the source series.
    rolling = (
        x.rolling(
            window=period,
            center=True,
        )
        .mean()
    )

    detrended = x - rolling

    seasonal_means = (
        detrended
        .groupby(
            np.arange(len(detrended)) % period
        )
        .transform("mean")
    )

    valid = (
        seasonal_means.notna()
        & detrended.notna()
    )

    if valid.sum() == 0:
        return np.nan

    seasonal_var = np.var(
        seasonal_means[valid]
    )

    residual_var = np.var(
        (detrended[valid] - seasonal_means[valid])
    )

    denominator = seasonal_var + residual_var

    if denominator == 0:
        return 0.0

    return seasonal_var / denominator


def acf_values(x, max_lag=24):

    x = pd.Series(x).dropna()

    values = acf(
        x,
        nlags=max_lag,
        fft=True,
    )

    return values


def pacf_values(x, max_lag=24):

    x = pd.Series(x).dropna()

    max_allowed = min(
        max_lag,
        max(1, len(x) // 2 - 1),
    )

    values = pacf(
        x,
        nlags=max_allowed,
        method="ywm",
    )

    return values


# ------------------------------------------------------------
# 3. RUN LEVEL DIAGNOSTICS
# ------------------------------------------------------------

def run_diagnostics(
    df,
    value_col,
    dataset_name,
):

    rows = []

    for series, group in df.groupby(
        "DataSeries"
    ):

        group = group.sort_values("date")
        x = group[value_col].astype(float)

        adf = adf_test(x)
        kpss_result = kpss_test(x)
        lb = ljung_box_test(x, lag=12)
        trend = trend_test(
            x,
            group["date"],
        )

        rows.append(
            {
                "dataset": dataset_name,
                "series": series,
                "n": len(x),
                "start": group["date"].min(),
                "end": group["date"].max(),
                **adf,
                **kpss_result,
                **lb,
                **trend,
                "seasonal_strength_12m":
                    seasonal_strength(x, 12),
            }
        )

    return pd.DataFrame(rows)


print("\n[2] LEVEL DIAGNOSTICS")

price_diag = run_diagnostics(
    price,
    "price_dollars_per_tonne",
    "price",
)

demand_diag = run_diagnostics(
    demand,
    "demand_thousand_tonnes",
    "demand",
)

level_diag = pd.concat(
    [price_diag, demand_diag],
    ignore_index=True,
)

level_diag.to_csv(
    TABLES / "RO1_level_temporal_diagnostics.csv",
    index=False,
)

print("\nPRICE")
print(
    price_diag[
        [
            "series",
            "adf_pvalue",
            "kpss_pvalue",
            "lb_pvalue",
            "trend_pvalue",
            "trend_r_squared",
            "seasonal_strength_12m",
        ]
    ]
    .round(4)
    .to_string(index=False)
)

print("\nDEMAND")
print(
    demand_diag[
        [
            "series",
            "adf_pvalue",
            "kpss_pvalue",
            "lb_pvalue",
            "trend_pvalue",
            "trend_r_squared",
            "seasonal_strength_12m",
        ]
    ]
    .round(4)
    .to_string(index=False)
)


# ------------------------------------------------------------
# 4. DIFFERENCED DIAGNOSTICS
# ------------------------------------------------------------

print("\n[3] DIFFERENCED DIAGNOSTICS")

diff_rows = []

for dataset_name, df, value_col in [
    (
        "price",
        price,
        "price_dollars_per_tonne",
    ),
    (
        "demand",
        demand,
        "demand_thousand_tonnes",
    ),
]:

    for series, group in df.groupby(
        "DataSeries"
    ):

        group = group.sort_values("date")
        x = group[value_col].astype(float)

        log_x = np.log(x)

        transformations = {
            "first_difference":
                x.diff().dropna(),

            "log_first_difference":
                log_x.diff().dropna(),

            "seasonal_difference_12":
                x.diff(12).dropna(),

            "log_seasonal_difference_12":
                log_x.diff(12).dropna(),
        }

        for transform_name, transformed in transformations.items():

            adf = adf_test(transformed)
            kpss_result = kpss_test(transformed)
            lb = ljung_box_test(
                transformed,
                lag=12,
            )

            diff_rows.append(
                {
                    "dataset": dataset_name,
                    "series": series,
                    "transformation": transform_name,
                    "n": len(transformed),
                    **adf,
                    **kpss_result,
                    **lb,
                }
            )


diff_diag = pd.DataFrame(diff_rows)

diff_diag.to_csv(
    TABLES / "RO1_difference_temporal_diagnostics.csv",
    index=False,
)

print(
    diff_diag[
        [
            "dataset",
            "series",
            "transformation",
            "adf_pvalue",
            "kpss_pvalue",
            "lb_pvalue",
        ]
    ]
    .round(4)
    .to_string(index=False)
)


# ------------------------------------------------------------
# 5. ACF / PACF
# ------------------------------------------------------------

print("\n[4] ACF / PACF")

acf_rows = []
pacf_rows = []

for dataset_name, df, value_col in [
    (
        "price",
        price,
        "price_dollars_per_tonne",
    ),
    (
        "demand",
        demand,
        "demand_thousand_tonnes",
    ),
]:

    for series, group in df.groupby(
        "DataSeries"
    ):

        group = group.sort_values("date")
        x = group[value_col].astype(float)

        log_x = np.log(x)

        acf_level = acf_values(
            log_x,
            max_lag=24,
        )

        pacf_level = pacf_values(
            log_x,
            max_lag=24,
        )

        for lag, value in enumerate(acf_level):
            acf_rows.append(
                {
                    "dataset": dataset_name,
                    "series": series,
                    "transformation": "log_level",
                    "lag": lag,
                    "acf": value,
                }
            )

        for lag, value in enumerate(pacf_level):
            pacf_rows.append(
                {
                    "dataset": dataset_name,
                    "series": series,
                    "transformation": "log_level",
                    "lag": lag,
                    "pacf": value,
                }
            )


acf_df = pd.DataFrame(acf_rows)
pacf_df = pd.DataFrame(pacf_rows)

acf_df.to_csv(
    TABLES / "RO1_acf_log_levels.csv",
    index=False,
)

pacf_df.to_csv(
    TABLES / "RO1_pacf_log_levels.csv",
    index=False,
)


# ------------------------------------------------------------
# 6. ROLLING 12-MONTH MEAN / VOLATILITY
# ------------------------------------------------------------

print("\n[5] ROLLING DIAGNOSTICS")

for dataset_name, df, value_col in [
    (
        "price",
        price,
        "price_dollars_per_tonne",
    ),
    (
        "demand",
        demand,
        "demand_thousand_tonnes",
    ),
]:

    rolling_parts = []

    for series, group in df.groupby(
        "DataSeries"
    ):

        group = group.sort_values("date").copy()

        group["log_value"] = np.log(
            group[value_col]
        )

        group["rolling_12m_mean"] = (
            group[value_col]
            .rolling(12)
            .mean()
        )

        group["rolling_12m_std_log"] = (
            group["log_value"]
            .diff()
            .rolling(12)
            .std()
        )

        rolling_parts.append(
            group[
                [
                    "date",
                    "DataSeries",
                    "rolling_12m_mean",
                    "rolling_12m_std_log",
                ]
            ]
        )

    rolling = pd.concat(
        rolling_parts,
        ignore_index=True,
    )

    rolling.to_csv(
        TABLES
        / f"RO1_{dataset_name}_rolling_diagnostics.csv",
        index=False,
    )


# ------------------------------------------------------------
# 7. 2020 COVID DIAGNOSTICS
# ------------------------------------------------------------

print("\n[6] COVID-PERIOD DIAGNOSTICS")

covid_rows = []

for dataset_name, df, value_col in [
    (
        "price",
        price,
        "price_dollars_per_tonne",
    ),
    (
        "demand",
        demand,
        "demand_thousand_tonnes",
    ),
]:

    for series, group in df.groupby(
        "DataSeries"
    ):

        group = group.sort_values("date").copy()

        pre = group[
            group["date"] < pd.Timestamp("2020-01-01")
        ][value_col]

        covid = group[
            (
                group["date"]
                >= pd.Timestamp("2020-01-01")
            )
            & (
                group["date"]
                <= pd.Timestamp("2020-12-01")
            )
        ][value_col]

        post = group[
            group["date"] >= pd.Timestamp("2021-01-01")
        ][value_col]

        covid_rows.append(
            {
                "dataset": dataset_name,
                "series": series,
                "pre_2020_mean": pre.mean(),
                "covid_2020_mean": covid.mean(),
                "post_2020_mean": post.mean(),
                "pre_2020_std": pre.std(),
                "covid_2020_std": covid.std(),
                "post_2020_std": post.std(),
                "covid_vs_pre_ratio":
                    covid.mean() / pre.mean(),
                "post_vs_pre_ratio":
                    post.mean() / pre.mean(),
            }
        )


covid_diag = pd.DataFrame(covid_rows)

covid_diag.to_csv(
    TABLES / "RO1_covid_period_diagnostics.csv",
    index=False,
)

print(
    covid_diag.round(4).to_string(index=False)
)


# ------------------------------------------------------------
# 8. ACF PLOTS
# ------------------------------------------------------------

for dataset_name, df, value_col in [
    (
        "price",
        price,
        "price_dollars_per_tonne",
    ),
    (
        "demand",
        demand,
        "demand_thousand_tonnes",
    ),
]:

    for series, group in df.groupby(
        "DataSeries"
    ):

        group = group.sort_values("date")
        x = np.log(
            group[value_col].astype(float)
        )

        values = acf_values(
            x,
            max_lag=24,
        )

        plt.figure(figsize=(10, 5))

        plt.stem(
            range(len(values)),
            values,
        )

        plt.axhline(
            0,
            linewidth=0.8,
        )

        plt.title(
            f"ACF of Log Levels — {dataset_name.title()} — {series}"
        )

        plt.xlabel("Lag (months)")
        plt.ylabel("Autocorrelation")

        plt.tight_layout()

        filename = (
            f"{dataset_name}_acf_"
            + series.lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(",", "")
            .replace("-", "_")
            + ".png"
        )

        plt.savefig(
            FIGURES / filename,
            dpi=180,
            bbox_inches="tight",
        )

        plt.close()


# ------------------------------------------------------------
# 9. SUMMARY FLAGS
# ------------------------------------------------------------

print("\n[7] DIAGNOSTIC FLAGS")

for _, row in level_diag.iterrows():

    adf_stationary = row["adf_pvalue"] < 0.05
    kpss_stationary = row["kpss_pvalue"] > 0.05

    if adf_stationary and kpss_stationary:
        stationarity = "consistent_stationary"
    elif (not adf_stationary) and (not kpss_stationary):
        stationarity = "consistent_nonstationary"
    else:
        stationarity = "mixed_test_result"

    print(
        f"{row['dataset']:7s} | "
        f"{row['series'][:40]:40s} | "
        f"ADF p={row['adf_pvalue']:.4f} | "
        f"KPSS p={row['kpss_pvalue']:.4f} | "
        f"{stationarity}"
    )


# ------------------------------------------------------------
# 10. OUTPUT INVENTORY
# ------------------------------------------------------------

print("\n[8] OUTPUTS CREATED")

print("\nTables:")
for f in sorted(TABLES.glob("RO1_*")):
    print(" ", f.name)

print("\nFigures:")
for f in sorted(FIGURES.glob("*acf*.png")):
    print(" ", f.name)

print("\n" + "=" * 78)
print("STEP 21B COMPLETE")
print("RAW CSV FILES WERE READ ONLY")
print("NO OBSERVATIONS WERE REMOVED OR PERMANENTLY TRANSFORMED")
print("=" * 78)
