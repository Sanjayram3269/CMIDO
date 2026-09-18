from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]

PRICE_FILE = ROOT / "data" / "interim" / "RO1_price_long.csv"
DEMAND_FILE = ROOT / "data" / "interim" / "RO1_demand_long.csv"

TABLE_DIR = ROOT / "results" / "forecasting" / "tables"
FIG_DIR = ROOT / "results" / "forecasting" / "figures"

TABLE_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 78)
print("CMIDO RO1 — STEP 21C")
print("STOCHASTIC REGIME + DISTRIBUTIONAL STABILITY ANALYSIS")
print("=" * 78)


# =====================================================================
# 1. LOAD DATA
# =====================================================================

price = pd.read_csv(
    PRICE_FILE,
    parse_dates=["date"]
)

demand = pd.read_csv(
    DEMAND_FILE,
    parse_dates=["date"]
)

print("\n[1] DATA")
print(f"Price rows : {len(price)}")
print(f"Demand rows: {len(demand)}")


# =====================================================================
# 2. STANDARDIZE SCHEMA
# =====================================================================

price = price.rename(
    columns={
        "DataSeries": "series",
        "price_dollars_per_tonne": "value"
    }
)

demand = demand.rename(
    columns={
        "DataSeries": "series",
        "demand_thousand_tonnes": "value"
    }
)

required = {"date", "series", "value"}

if not required.issubset(price.columns):
    raise ValueError(
        f"Invalid price schema: {price.columns.tolist()}"
    )

if not required.issubset(demand.columns):
    raise ValueError(
        f"Invalid demand schema: {demand.columns.tolist()}"
    )


# =====================================================================
# 3. HELPER FUNCTIONS
# =====================================================================

def safe_adf(x):

    x = pd.Series(x).dropna()

    if len(x) < 30:
        return np.nan, np.nan

    try:
        stat, p, *_ = adfuller(
            x,
            autolag="AIC"
        )
        return stat, p
    except Exception:
        return np.nan, np.nan


def safe_ljung_box(x, lag=12):

    x = pd.Series(x).dropna()

    if len(x) <= lag + 5:
        return np.nan

    try:
        result = acorr_ljungbox(
            x,
            lags=[lag],
            return_df=True
        )

        return result["lb_pvalue"].iloc[0]

    except Exception:
        return np.nan


def distribution_summary(x):

    x = pd.Series(x).dropna()

    if len(x) < 10:
        return {
            "mean": np.nan,
            "std": np.nan,
            "median": np.nan,
            "q10": np.nan,
            "q25": np.nan,
            "q75": np.nan,
            "q90": np.nan,
            "skew": np.nan,
            "kurtosis": np.nan,
            "n": len(x)
        }

    return {
        "mean": x.mean(),
        "std": x.std(),
        "median": x.median(),
        "q10": x.quantile(0.10),
        "q25": x.quantile(0.25),
        "q75": x.quantile(0.75),
        "q90": x.quantile(0.90),
        "skew": stats.skew(x),
        "kurtosis": stats.kurtosis(x),
        "n": len(x)
    }


def rolling_regime_diagnostics(
    dates,
    changes,
    window=36
):

    dates = pd.Series(dates).reset_index(drop=True)
    changes = pd.Series(changes).reset_index(drop=True)

    rows = []

    for end in range(window, len(changes) + 1):

        x = changes.iloc[
            end - window:end
        ].dropna()

        if len(x) < window * 0.8:
            continue

        rows.append({
            "date": dates.iloc[end - 1],
            "window": window,
            "mean": x.mean(),
            "std": x.std(),
            "abs_mean": np.abs(x).mean(),
            "q10": x.quantile(0.10),
            "q90": x.quantile(0.90),
            "skew": stats.skew(x),
            "kurtosis": stats.kurtosis(x)
        })

    return pd.DataFrame(rows)


def compare_periods(x1, x2):

    x1 = pd.Series(x1).dropna()
    x2 = pd.Series(x2).dropna()

    if len(x1) < 6 or len(x2) < 6:
        return {
            "mean_diff": np.nan,
            "mean_p": np.nan,
            "variance_ratio": np.nan,
            "variance_p": np.nan,
            "ks_stat": np.nan,
            "ks_p": np.nan
        }

    mean_test = stats.ttest_ind(
        x1,
        x2,
        equal_var=False
    )

    try:
        var_test = stats.levene(
            x1,
            x2,
            center="median"
        )
    except Exception:
        var_test = None

    try:
        ks_test = stats.ks_2samp(
            x1,
            x2
        )
    except Exception:
        ks_test = None

    return {
        "mean_diff": x2.mean() - x1.mean(),
        "mean_p": mean_test.pvalue,
        "variance_ratio": (
            x2.var(ddof=1) / x1.var(ddof=1)
            if x1.var(ddof=1) > 0
            else np.nan
        ),
        "variance_p": (
            var_test.pvalue
            if var_test is not None
            else np.nan
        ),
        "ks_stat": (
            ks_test.statistic
            if ks_test is not None
            else np.nan
        ),
        "ks_p": (
            ks_test.pvalue
            if ks_test is not None
            else np.nan
        )
    }


# =====================================================================
# 4. TRANSFORM SERIES
# =====================================================================

print("\n[2] TRANSFORMATION")

transformed = []

for dataset_name, df in [
    ("price", price),
    ("demand", demand)
]:

    for series_name, group in df.groupby("series"):

        group = (
            group
            .sort_values("date")
            .copy()
        )

        group["log_value"] = np.log(
            group["value"]
        )

        group["log_change"] = (
            group["log_value"].diff()
        )

        group["first_difference"] = (
            group["value"].diff()
        )

        group["month"] = (
            group["date"].dt.month
        )

        group["dataset"] = dataset_name

        transformed.append(
            group
        )

transformed = pd.concat(
    transformed,
    ignore_index=True
)

print(
    f"Transformed rows: {len(transformed)}"
)


# =====================================================================
# 5. GLOBAL STOCHASTIC STABILITY DIAGNOSTICS
# =====================================================================

print("\n[3] GLOBAL STOCHASTIC DIAGNOSTICS")

global_rows = []

for dataset_name, df in transformed.groupby("dataset"):

    for series_name, group in df.groupby("series"):

        x = (
            group["log_change"]
            .dropna()
        )

        summary = distribution_summary(x)

        adf_stat, adf_p = safe_adf(x)
        lb_p = safe_ljung_box(x, lag=12)

        global_rows.append({
            "dataset": dataset_name,
            "series": series_name,
            "n_changes": len(x),
            "mean_log_change": summary["mean"],
            "std_log_change": summary["std"],
            "median_log_change": summary["median"],
            "q10": summary["q10"],
            "q25": summary["q25"],
            "q75": summary["q75"],
            "q90": summary["q90"],
            "skew": summary["skew"],
            "kurtosis": summary["kurtosis"],
            "adf_stat": adf_stat,
            "adf_p": adf_p,
            "ljung_box_p_12": lb_p
        })

global_table = pd.DataFrame(
    global_rows
)

global_table.to_csv(
    TABLE_DIR
    / "RO1_stochastic_global_diagnostics.csv",
    index=False
)

print(
    global_table.to_string(index=False)
)


# =====================================================================
# 6. ROLLING STOCHASTIC REGIME ANALYSIS
# =====================================================================

print("\n[4] ROLLING STOCHASTIC REGIME ANALYSIS")

rolling_tables = []

for dataset_name, df in transformed.groupby("dataset"):

    for series_name, group in df.groupby("series"):

        rolling = rolling_regime_diagnostics(
            group["date"],
            group["log_change"],
            window=36
        )

        rolling.insert(
            0,
            "dataset",
            dataset_name
        )

        rolling.insert(
            1,
            "series",
            series_name
        )

        rolling_tables.append(
            rolling
        )

rolling_table = pd.concat(
    rolling_tables,
    ignore_index=True
)

rolling_table.to_csv(
    TABLE_DIR
    / "RO1_rolling_stochastic_regimes.csv",
    index=False
)

print(
    f"Rolling diagnostic windows: "
    f"{len(rolling_table)}"
)


# =====================================================================
# 7. EARLY / MIDDLE / RECENT REGIME COMPARISON
# =====================================================================

print("\n[5] HISTORICAL REGIME COMPARISON")

periods = {
    "early": (
        pd.Timestamp("1999-01-01"),
        pd.Timestamp("2007-12-01")
    ),

    "middle": (
        pd.Timestamp("2008-01-01"),
        pd.Timestamp("2016-12-01")
    ),

    "recent_pre_covid": (
        pd.Timestamp("2017-01-01"),
        pd.Timestamp("2019-12-01")
    ),

    "post_covid": (
        pd.Timestamp("2021-01-01"),
        pd.Timestamp("2026-05-01")
    )
}

period_rows = []

for dataset_name, df in transformed.groupby("dataset"):

    for series_name, group in df.groupby("series"):

        regime_data = {}

        for period_name, (start, end) in periods.items():

            regime_data[period_name] = group.loc[
                (group["date"] >= start)
                & (group["date"] <= end),
                "log_change"
            ].dropna()

        comparisons = [
            ("early", "middle"),
            ("middle", "recent_pre_covid"),
            ("recent_pre_covid", "post_covid")
        ]

        for p1, p2 in comparisons:

            result = compare_periods(
                regime_data[p1],
                regime_data[p2]
            )

            period_rows.append({
                "dataset": dataset_name,
                "series": series_name,
                "comparison": f"{p1}_vs_{p2}",
                "n_period_1": len(regime_data[p1]),
                "n_period_2": len(regime_data[p2]),
                **result
            })

period_table = pd.DataFrame(
    period_rows
)

period_table.to_csv(
    TABLE_DIR
    / "RO1_historical_regime_comparisons.csv",
    index=False
)

print(
    period_table.to_string(index=False)
)


# =====================================================================
# 8. COVID REGIME
# =====================================================================

print("\n[6] COVID-2020 STOCHASTIC REGIME")

covid_rows = []

for dataset_name, df in transformed.groupby("dataset"):

    for series_name, group in df.groupby("series"):

        pre = group.loc[
            group["date"] < "2020-03-01",
            "log_change"
        ].dropna()

        covid = group.loc[
            (group["date"] >= "2020-03-01")
            & (group["date"] <= "2020-12-01"),
            "log_change"
        ].dropna()

        post = group.loc[
            group["date"] >= "2021-01-01",
            "log_change"
        ].dropna()

        pre_covid = compare_periods(
            pre,
            covid
        )

        covid_post = compare_periods(
            covid,
            post
        )

        covid_rows.append({
            "dataset": dataset_name,
            "series": series_name,

            "pre_mean": pre.mean(),
            "covid_mean": covid.mean(),
            "post_mean": post.mean(),

            "pre_std": pre.std(),
            "covid_std": covid.std(),
            "post_std": post.std(),

            "pre_vs_covid_mean_p":
                pre_covid["mean_p"],

            "pre_vs_covid_variance_p":
                pre_covid["variance_p"],

            "pre_vs_covid_ks_p":
                pre_covid["ks_p"],

            "covid_vs_post_mean_p":
                covid_post["mean_p"],

            "covid_vs_post_variance_p":
                covid_post["variance_p"],

            "covid_vs_post_ks_p":
                covid_post["ks_p"],

            "covid_volatility_ratio":
                (
                    covid.std() / pre.std()
                    if pre.std() > 0
                    else np.nan
                ),

            "post_volatility_ratio":
                (
                    post.std() / pre.std()
                    if pre.std() > 0
                    else np.nan
                )
        })

covid_table = pd.DataFrame(
    covid_rows
)

covid_table.to_csv(
    TABLE_DIR
    / "RO1_covid_stochastic_regime_tests.csv",
    index=False
)

print(
    covid_table.to_string(index=False)
)


# =====================================================================
# 9. ROLLING VOLATILITY PLOTS
# =====================================================================

print("\n[7] ROLLING VOLATILITY FIGURES")

for dataset_name, df in transformed.groupby("dataset"):

    for series_name, group in df.groupby("series"):

        rolling = rolling_table[
            (rolling_table["dataset"] == dataset_name)
            & (rolling_table["series"] == series_name)
        ]

        if rolling.empty:
            continue

        fig, ax = plt.subplots(
            figsize=(12, 5)
        )

        ax.plot(
            rolling["date"],
            rolling["std"],
            linewidth=1.5
        )

        ax.axvspan(
            pd.Timestamp("2020-03-01"),
            pd.Timestamp("2020-12-01"),
            alpha=0.12
        )

        ax.set_title(
            f"{dataset_name.title()} — {series_name}\n"
            "36-month rolling volatility of log changes"
        )

        ax.set_xlabel("Date")
        ax.set_ylabel("Rolling standard deviation")

        ax.grid(alpha=0.25)

        fig.tight_layout()

        safe_name = (
            series_name
            .lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
            .replace("/", "_")
        )

        fig.savefig(
            FIG_DIR
            / f"{dataset_name}_{safe_name}_rolling_volatility.png",
            dpi=180,
            bbox_inches="tight"
        )

        plt.close(fig)


# =====================================================================
# 10. DISTRIBUTION COMPARISON FIGURES
# =====================================================================

print("\n[8] DISTRIBUTION FIGURES")

for dataset_name, df in transformed.groupby("dataset"):

    for series_name, group in df.groupby("series"):

        pre = group.loc[
            group["date"] < "2020-03-01",
            "log_change"
        ].dropna()

        covid = group.loc[
            (group["date"] >= "2020-03-01")
            & (group["date"] <= "2020-12-01"),
            "log_change"
        ].dropna()

        post = group.loc[
            group["date"] >= "2021-01-01",
            "log_change"
        ].dropna()

        if len(pre) == 0:
            continue

        fig, ax = plt.subplots(
            figsize=(10, 5)
        )

        ax.hist(
            pre,
            bins=30,
            alpha=0.45,
            density=True,
            label="Pre-COVID"
        )

        if len(covid) > 0:
            ax.hist(
                covid,
                bins=20,
                alpha=0.45,
                density=True,
                label="COVID-2020"
            )

        if len(post) > 0:
            ax.hist(
                post,
                bins=30,
                alpha=0.45,
                density=True,
                label="Post-COVID"
            )

        ax.set_title(
            f"{dataset_name.title()} — {series_name}\n"
            "Distribution of monthly log changes"
        )

        ax.set_xlabel("Log change")
        ax.set_ylabel("Density")

        ax.legend()
        ax.grid(alpha=0.25)

        fig.tight_layout()

        safe_name = (
            series_name
            .lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
            .replace("/", "_")
        )

        fig.savefig(
            FIG_DIR
            / f"{dataset_name}_{safe_name}_distribution_regimes.png",
            dpi=180,
            bbox_inches="tight"
        )

        plt.close(fig)


# =====================================================================
# 11. FINAL DIAGNOSTIC FLAGS
# =====================================================================

print("\n[9] DIAGNOSTIC FLAGS")

print(
    "\nInterpretation categories:"
)

print(
    "  A = relatively stable stochastic behavior"
)

print(
    "  B = evidence of regime-dependent behavior"
)

print(
    "  C = strong COVID-specific disturbance"
)

diagnostic_rows = []

for _, row in covid_table.iterrows():

    ratio = row["covid_volatility_ratio"]

    if pd.isna(ratio):
        category = "A"

    elif ratio >= 1.5:
        category = "C"

    elif ratio >= 1.25:
        category = "B"

    else:
        category = "A"

    diagnostic_rows.append({
        "dataset": row["dataset"],
        "series": row["series"],
        "covid_volatility_ratio": ratio,
        "diagnostic_category": category
    })

diagnostic_table = pd.DataFrame(
    diagnostic_rows
)

diagnostic_table.to_csv(
    TABLE_DIR
    / "RO1_stochastic_regime_diagnostic_flags.csv",
    index=False
)

print(
    diagnostic_table.to_string(index=False)
)


# =====================================================================
# 12. COMPLETE
# =====================================================================

print("\n" + "=" * 78)
print("STEP 21C STOCHASTIC REGIME ANALYSIS COMPLETE")
print("=" * 78)
print("Raw source/interim CSV files were READ ONLY.")
print("No observations were removed.")
print("No observations were overwritten.")
print("=" * 78)