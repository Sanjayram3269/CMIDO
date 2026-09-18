from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# CMIDO — RO1 STEP 21A
# Structural + Descriptive Exploratory Data Analysis
# ============================================================

ROOT = Path(r"D:\CMIDO")
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
FIGURES = ROOT / "figures"
TABLES = ROOT / "tables"

INTERIM.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)


PRICE_FILE = RAW / "ConstructionMaterialMarketPricesMonthly.csv"
DEMAND_FILE = RAW / "DemandForConstructionMaterialsMonthly.csv"


print("=" * 78)
print("CMIDO RO1 — STEP 21A")
print("STRUCTURAL + DESCRIPTIVE EXPLORATORY DATA ANALYSIS")
print("=" * 78)


# ------------------------------------------------------------
# 1. LOAD RAW DATA
# ------------------------------------------------------------

price_raw = pd.read_csv(PRICE_FILE)
demand_raw = pd.read_csv(DEMAND_FILE)

print("\n[1] RAW DATA LOADED")
print("Price shape :", price_raw.shape)
print("Demand shape:", demand_raw.shape)


# ------------------------------------------------------------
# 2. IDENTIFY MONTH COLUMNS
# ------------------------------------------------------------

def get_month_columns(df):
    cols = []
    for c in df.columns:
        if c == "DataSeries":
            continue

        try:
            pd.to_datetime(c, format="%Y%b")
            cols.append(c)
        except Exception:
            pass

    return cols


price_months = get_month_columns(price_raw)
demand_months = get_month_columns(demand_raw)

price_dates = pd.to_datetime(price_months, format="%Y%b")
demand_dates = pd.to_datetime(demand_months, format="%Y%b")

print("\n[2] TEMPORAL COVERAGE")
print(
    "Price :",
    price_dates.min().strftime("%Y-%m"),
    "to",
    price_dates.max().strftime("%Y-%m"),
)
print(
    "Demand:",
    demand_dates.min().strftime("%Y-%m"),
    "to",
    demand_dates.max().strftime("%Y-%m"),
)


# ------------------------------------------------------------
# 3. CONVERT WIDE → LONG
# ------------------------------------------------------------

def wide_to_long(df, value_name):

    long_df = df.melt(
        id_vars=["DataSeries"],
        var_name="period",
        value_name=value_name,
    )

    long_df["date"] = pd.to_datetime(
        long_df["period"],
        format="%Y%b",
    )

    long_df[value_name] = pd.to_numeric(
        long_df[value_name],
        errors="coerce",
    )

    long_df = long_df[
        ["date", "DataSeries", value_name]
    ].sort_values(
        ["DataSeries", "date"]
    ).reset_index(drop=True)

    return long_df


price = wide_to_long(
    price_raw,
    "price_dollars_per_tonne",
)

demand = wide_to_long(
    demand_raw,
    "demand_thousand_tonnes",
)


# ------------------------------------------------------------
# 4. SAVE NON-DESTRUCTIVE LONG VERSIONS
# ------------------------------------------------------------

price.to_csv(
    INTERIM / "RO1_price_long.csv",
    index=False,
)

demand.to_csv(
    INTERIM / "RO1_demand_long.csv",
    index=False,
)

print("\n[3] LONG FORMAT")
print("Price rows :", len(price))
print("Demand rows:", len(demand))

print(
    "Saved:",
    INTERIM / "RO1_price_long.csv",
)

print(
    "Saved:",
    INTERIM / "RO1_demand_long.csv",
)


# ------------------------------------------------------------
# 5. COMMON MATERIALS
# ------------------------------------------------------------

price_materials = set(price["DataSeries"].unique())
demand_materials = set(demand["DataSeries"].unique())

common_materials = sorted(
    price_materials.intersection(demand_materials)
)

price_only_materials = sorted(
    price_materials.difference(demand_materials)
)

print("\n[4] MATERIAL ALIGNMENT")

print("Common materials:")
for x in common_materials:
    print("  -", x)

print("\nPrice-only materials:")
for x in price_only_materials:
    print("  -", x)


# ------------------------------------------------------------
# 6. COMMON TIME WINDOW
# ------------------------------------------------------------

common_start = max(
    price["date"].min(),
    demand["date"].min(),
)

common_end = min(
    price["date"].max(),
    demand["date"].max(),
)

print("\n[5] COMMON PRICE-DEMAND WINDOW")
print(
    common_start.strftime("%Y-%m"),
    "to",
    common_end.strftime("%Y-%m"),
)

common_price = price[
    (price["date"] >= common_start)
    & (price["date"] <= common_end)
    & price["DataSeries"].isin(common_materials)
].copy()

common_demand = demand[
    (demand["date"] >= common_start)
    & (demand["date"] <= common_end)
    & demand["DataSeries"].isin(common_materials)
].copy()


# ------------------------------------------------------------
# 7. DESCRIPTIVE STATISTICS
# ------------------------------------------------------------

price_summary = (
    price.groupby("DataSeries")["price_dollars_per_tonne"]
    .agg(
        n="count",
        mean="mean",
        std="std",
        min="min",
        median="median",
        max="max",
    )
    .reset_index()
)

demand_summary = (
    demand.groupby("DataSeries")["demand_thousand_tonnes"]
    .agg(
        n="count",
        mean="mean",
        std="std",
        min="min",
        median="median",
        max="max",
    )
    .reset_index()
)

price_summary["cv"] = (
    price_summary["std"]
    / price_summary["mean"]
)

demand_summary["cv"] = (
    demand_summary["std"]
    / demand_summary["mean"]
)

price_summary.to_csv(
    TABLES / "RO1_price_descriptive_statistics.csv",
    index=False,
)

demand_summary.to_csv(
    TABLES / "RO1_demand_descriptive_statistics.csv",
    index=False,
)

print("\n[6] PRICE DESCRIPTIVE STATISTICS")
print(price_summary.to_string(index=False))

print("\n[7] DEMAND DESCRIPTIVE STATISTICS")
print(demand_summary.to_string(index=False))


# ------------------------------------------------------------
# 8. MONTHLY SEASONALITY
# ------------------------------------------------------------

price["month"] = price["date"].dt.month
demand["month"] = demand["date"].dt.month

price_seasonality = (
    price.groupby(
        ["DataSeries", "month"]
    )["price_dollars_per_tonne"]
    .mean()
    .reset_index()
)

demand_seasonality = (
    demand.groupby(
        ["DataSeries", "month"]
    )["demand_thousand_tonnes"]
    .mean()
    .reset_index()
)

price_seasonality.to_csv(
    TABLES / "RO1_price_monthly_seasonality.csv",
    index=False,
)

demand_seasonality.to_csv(
    TABLES / "RO1_demand_monthly_seasonality.csv",
    index=False,
)


# ------------------------------------------------------------
# 9. LOG CHANGES / PERCENT CHANGES
# ------------------------------------------------------------

price["log_value"] = np.log(
    price["price_dollars_per_tonne"]
)

demand["log_value"] = np.log(
    demand["demand_thousand_tonnes"]
)

price["log_change"] = (
    price.groupby("DataSeries")["log_value"]
    .diff()
)

demand["log_change"] = (
    demand.groupby("DataSeries")["log_value"]
    .diff()
)

price["pct_change"] = (
    price.groupby("DataSeries")["price_dollars_per_tonne"]
    .pct_change()
)

demand["pct_change"] = (
    demand.groupby("DataSeries")["demand_thousand_tonnes"]
    .pct_change()
)

price_change_summary = (
    price.groupby("DataSeries")["log_change"]
    .agg(
        n="count",
        mean="mean",
        std="std",
        min="min",
        median="median",
        max="max",
    )
    .reset_index()
)

demand_change_summary = (
    demand.groupby("DataSeries")["log_change"]
    .agg(
        n="count",
        mean="mean",
        std="std",
        min="min",
        median="median",
        max="max",
    )
    .reset_index()
)

price_change_summary.to_csv(
    TABLES / "RO1_price_log_change_statistics.csv",
    index=False,
)

demand_change_summary.to_csv(
    TABLES / "RO1_demand_log_change_statistics.csv",
    index=False,
)

print("\n[8] LOG-CHANGE VOLATILITY")
print("\nPrice:")
print(price_change_summary.to_string(index=False))

print("\nDemand:")
print(demand_change_summary.to_string(index=False))


# ------------------------------------------------------------
# 10. EXTREME OBSERVATION FLAGGING
#     IMPORTANT: FLAGS ONLY — NOTHING IS REMOVED
# ------------------------------------------------------------

def iqr_flags(df, value_col):

    result = []

    for series, group in df.groupby("DataSeries"):

        x = group[value_col]

        q1 = x.quantile(0.25)
        q3 = x.quantile(0.75)
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        flagged = group[
            (x < lower)
            | (x > upper)
        ].copy()

        flagged["lower_bound"] = lower
        flagged["upper_bound"] = upper

        result.append(flagged)

    if result:
        return pd.concat(result, ignore_index=True)

    return pd.DataFrame()


price_flags = iqr_flags(
    price,
    "price_dollars_per_tonne",
)

demand_flags = iqr_flags(
    demand,
    "demand_thousand_tonnes",
)

price_flags.to_csv(
    TABLES / "RO1_price_extreme_observation_flags.csv",
    index=False,
)

demand_flags.to_csv(
    TABLES / "RO1_demand_extreme_observation_flags.csv",
    index=False,
)

print("\n[9] EXTREME OBSERVATION FLAGS")
print(
    "Price flagged:",
    len(price_flags),
)

print(
    "Demand flagged:",
    len(demand_flags),
)

print(
    "NOTE: These are statistical flags only. "
    "No observations were removed or modified."
)


# ------------------------------------------------------------
# 11. LEVEL CORRELATION — COMMON MATERIALS
# ------------------------------------------------------------

price_pivot = common_price.pivot(
    index="date",
    columns="DataSeries",
    values="price_dollars_per_tonne",
)

demand_pivot = common_demand.pivot(
    index="date",
    columns="DataSeries",
    values="demand_thousand_tonnes",
)

price_level_corr = price_pivot.corr()
demand_level_corr = demand_pivot.corr()

price_level_corr.to_csv(
    TABLES / "RO1_price_level_correlation.csv"
)

demand_level_corr.to_csv(
    TABLES / "RO1_demand_level_correlation.csv"
)


# ------------------------------------------------------------
# 12. LOG-CHANGE CORRELATION
# ------------------------------------------------------------

price_change_corr = (
    np.log(price_pivot)
    .diff()
    .corr()
)

demand_change_corr = (
    np.log(demand_pivot)
    .diff()
    .corr()
)

price_change_corr.to_csv(
    TABLES / "RO1_price_change_correlation.csv"
)

demand_change_corr.to_csv(
    TABLES / "RO1_demand_change_correlation.csv"
)

print("\n[10] LEVEL CORRELATIONS — PRICE")
print(price_level_corr.round(3).to_string())

print("\n[11] LEVEL CORRELATIONS — DEMAND")
print(demand_level_corr.round(3).to_string())

print("\n[12] LOG-CHANGE CORRELATIONS — PRICE")
print(price_change_corr.round(3).to_string())

print("\n[13] LOG-CHANGE CORRELATIONS — DEMAND")
print(demand_change_corr.round(3).to_string())


# ------------------------------------------------------------
# 13. PRICE-DEMAND WITHIN-MATERIAL CORRELATION
# ------------------------------------------------------------

cross_corr_rows = []

for material in common_materials:

    p = common_price[
        common_price["DataSeries"] == material
    ][
        ["date", "price_dollars_per_tonne"]
    ].rename(
        columns={
            "price_dollars_per_tonne": "price"
        }
    )

    d = common_demand[
        common_demand["DataSeries"] == material
    ][
        ["date", "demand_thousand_tonnes"]
    ].rename(
        columns={
            "demand_thousand_tonnes": "demand"
        }
    )

    merged = p.merge(
        d,
        on="date",
        how="inner",
    )

    level_corr = merged["price"].corr(
        merged["demand"]
    )

    log_corr = np.log(
        merged["price"]
    ).diff().corr(
        np.log(merged["demand"]).diff()
    )

    cross_corr_rows.append(
        {
            "material": material,
            "n": len(merged),
            "price_demand_level_corr": level_corr,
            "price_demand_log_change_corr": log_corr,
        }
    )

cross_corr = pd.DataFrame(cross_corr_rows)

cross_corr.to_csv(
    TABLES / "RO1_within_material_price_demand_correlation.csv",
    index=False,
)

print("\n[14] WITHIN-MATERIAL PRICE-DEMAND CORRELATION")
print(cross_corr.round(4).to_string(index=False))


# ------------------------------------------------------------
# 14. TREND FIGURES
# ------------------------------------------------------------

plt.rcParams["figure.figsize"] = (12, 5)

for material in price["DataSeries"].unique():

    subset = price[
        price["DataSeries"] == material
    ]

    plt.figure()
    plt.plot(
        subset["date"],
        subset["price_dollars_per_tonne"],
    )

    plt.axvspan(
        pd.Timestamp("2020-04-01"),
        pd.Timestamp("2020-08-01"),
        alpha=0.15,
    )

    plt.title(
        f"RO1 Price Series — {material}"
    )

    plt.xlabel("Date")
    plt.ylabel("Dollar per tonne")
    plt.tight_layout()

    filename = (
        "price_"
        + material.lower()
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


for material in demand["DataSeries"].unique():

    subset = demand[
        demand["DataSeries"] == material
    ]

    plt.figure()
    plt.plot(
        subset["date"],
        subset["demand_thousand_tonnes"],
    )

    plt.axvspan(
        pd.Timestamp("2020-04-01"),
        pd.Timestamp("2020-08-01"),
        alpha=0.15,
    )

    plt.title(
        f"RO1 Demand Series — {material}"
    )

    plt.xlabel("Date")
    plt.ylabel("Thousand tonnes")
    plt.tight_layout()

    filename = (
        "demand_"
        + material.lower()
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
# 15. SEASONALITY FIGURES
# ------------------------------------------------------------

for material in price["DataSeries"].unique():

    subset = price_seasonality[
        price_seasonality["DataSeries"] == material
    ]

    plt.figure()
    plt.plot(
        subset["month"],
        subset["price_dollars_per_tonne"],
        marker="o",
    )

    plt.xticks(range(1, 13))
    plt.title(
        f"Average Monthly Price Seasonality — {material}"
    )
    plt.xlabel("Calendar month")
    plt.ylabel("Dollar per tonne")
    plt.tight_layout()

    filename = (
        "price_seasonality_"
        + material.lower()
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


for material in demand["DataSeries"].unique():

    subset = demand_seasonality[
        demand_seasonality["DataSeries"] == material
    ]

    plt.figure()
    plt.plot(
        subset["month"],
        subset["demand_thousand_tonnes"],
        marker="o",
    )

    plt.xticks(range(1, 13))
    plt.title(
        f"Average Monthly Demand Seasonality — {material}"
    )
    plt.xlabel("Calendar month")
    plt.ylabel("Thousand tonnes")
    plt.tight_layout()

    filename = (
        "demand_seasonality_"
        + material.lower()
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
# 16. 12-MONTH ROLLING VOLATILITY
# ------------------------------------------------------------

rolling_rows = []

for material, group in price.groupby("DataSeries"):

    group = group.sort_values("date").copy()

    group["rolling_12m_std"] = (
        group["log_change"]
        .rolling(12)
        .std()
    )

    temp = group[
        [
            "date",
            "DataSeries",
            "rolling_12m_std",
        ]
    ]

    rolling_rows.append(temp)

price_rolling = pd.concat(
    rolling_rows,
    ignore_index=True,
)

price_rolling.to_csv(
    TABLES / "RO1_price_rolling_12m_volatility.csv",
    index=False,
)


rolling_rows = []

for material, group in demand.groupby("DataSeries"):

    group = group.sort_values("date").copy()

    group["rolling_12m_std"] = (
        group["log_change"]
        .rolling(12)
        .std()
    )

    temp = group[
        [
            "date",
            "DataSeries",
            "rolling_12m_std",
        ]
    ]

    rolling_rows.append(temp)

demand_rolling = pd.concat(
    rolling_rows,
    ignore_index=True,
)

demand_rolling.to_csv(
    TABLES / "RO1_demand_rolling_12m_volatility.csv",
    index=False,
)


# ------------------------------------------------------------
# 17. FINAL REPORT
# ------------------------------------------------------------

print("\n[15] OUTPUTS CREATED")

print("\nInterim:")
print(" ", INTERIM / "RO1_price_long.csv")
print(" ", INTERIM / "RO1_demand_long.csv")

print("\nTables:")
for f in sorted(TABLES.glob("RO1_*")):
    print(" ", f.name)

print("\nFigures:")
for f in sorted(FIGURES.glob("*.png")):
    print(" ", f.name)

print("\n" + "=" * 78)
print("STEP 21A COMPLETE")
print("RAW CSV FILES WERE READ ONLY — NO RAW DATA WAS MODIFIED")
print("=" * 78)
