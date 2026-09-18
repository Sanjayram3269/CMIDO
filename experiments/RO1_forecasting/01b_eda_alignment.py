from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"D:\CMIDO")
INTERIM = ROOT / "data" / "interim"
TABLES = ROOT / "tables"

PRICE_FILE = INTERIM / "RO1_price_long.csv"
DEMAND_FILE = INTERIM / "RO1_demand_long.csv"


print("=" * 78)
print("CMIDO RO1 — STEP 21A CORRECTION")
print("EXPLICIT MATERIAL ALIGNMENT + CORRELATION ANALYSIS")
print("=" * 78)


# ------------------------------------------------------------
# 1. LOAD EXISTING INTERIM DATA
# ------------------------------------------------------------

price = pd.read_csv(PRICE_FILE, parse_dates=["date"])
demand = pd.read_csv(DEMAND_FILE, parse_dates=["date"])

print("\n[1] INTERIM DATA")
print("Price rows :", len(price))
print("Demand rows:", len(demand))


# ------------------------------------------------------------
# 2. EXPLICIT MATERIAL MAPPING
# ------------------------------------------------------------

mapping = pd.DataFrame([
    {
        "canonical_material": "Cement",
        "price_series": "Cement In Bulk (Ordinary Portland Cement)",
        "demand_series": "Cement",
        "joint_forecasting": True,
    },
    {
        "canonical_material": "Steel Reinforcement Bars",
        "price_series": "Steel Reinforcement Bars (16-32mm High Tensile)",
        "demand_series": "Steel Reinforcement Bars",
        "joint_forecasting": True,
    },
    {
        "canonical_material": "Granite",
        "price_series": "Granite (20mm Aggregate)",
        "demand_series": "Granite",
        "joint_forecasting": True,
    },
    {
        "canonical_material": "Ready-Mixed Concrete",
        "price_series": "Ready Mixed Concrete",
        "demand_series": "Ready-Mixed Concrete",
        "joint_forecasting": True,
    },
    {
        "canonical_material": "Concreting Sand",
        "price_series": "Concreting Sand",
        "demand_series": None,
        "joint_forecasting": False,
    },
])

mapping.to_csv(
    TABLES / "RO1_material_series_mapping.csv",
    index=False,
)

print("\n[2] MATERIAL MAPPING")

for _, row in mapping.iterrows():
    print(f"\n  Canonical: {row['canonical_material']}")
    print(f"    Price : {row['price_series']}")
    print(f"    Demand: {row['demand_series']}")
    print(f"    Joint : {row['joint_forecasting']}")


# ------------------------------------------------------------
# 3. VALIDATE MAPPING
# ------------------------------------------------------------

price_names = set(price["DataSeries"].unique())
demand_names = set(demand["DataSeries"].unique())

for _, row in mapping.iterrows():

    if row["price_series"] not in price_names:
        raise ValueError(
            f"Price series missing: {row['price_series']}"
        )

    if pd.notna(row["demand_series"]):
        if row["demand_series"] not in demand_names:
            raise ValueError(
                f"Demand series missing: {row['demand_series']}"
            )

print("\n[3] MAPPING VALIDATION")
print("PASS — every declared source series exists.")


# ------------------------------------------------------------
# 4. CREATE CANONICAL DATASETS
# ------------------------------------------------------------

price_parts = []

for _, row in mapping.iterrows():

    p = price[
        price["DataSeries"] == row["price_series"]
    ].copy()

    p["canonical_material"] = row["canonical_material"]

    price_parts.append(p)

price_canonical = pd.concat(
    price_parts,
    ignore_index=True,
)

demand_parts = []

for _, row in mapping.iterrows():

    if row["demand_series"] is None:
        continue

    d = demand[
        demand["DataSeries"] == row["demand_series"]
    ].copy()

    d["canonical_material"] = row["canonical_material"]

    demand_parts.append(d)

demand_canonical = pd.concat(
    demand_parts,
    ignore_index=True,
)


# ------------------------------------------------------------
# 5. JOINT ALIGNMENT
# ------------------------------------------------------------

price_joint = price_canonical[
    price_canonical["canonical_material"]
    .isin(
        mapping.loc[
            mapping["joint_forecasting"],
            "canonical_material",
        ]
    )
].copy()

demand_joint = demand_canonical[
    demand_canonical["canonical_material"]
    .isin(
        mapping.loc[
            mapping["joint_forecasting"],
            "canonical_material",
        ]
    )
].copy()

joint = price_joint.merge(
    demand_joint,
    on=["date", "canonical_material"],
    how="inner",
    suffixes=("_price", "_demand"),
)

print("\n[4] JOINT ALIGNMENT")
print("Joint rows:", len(joint))

print("\nObservations per material:")

alignment = (
    joint.groupby("canonical_material")
    .agg(
        observations=("date", "count"),
        first_date=("date", "min"),
        last_date=("date", "max"),
    )
    .reset_index()
)

print(alignment.to_string(index=False))

expected = 329 * 4

if len(joint) != expected:
    raise ValueError(
        f"Expected {expected} joint observations, "
        f"found {len(joint)}."
    )

print(
    f"\nPASS — expected {expected} aligned observations "
    f"and found {len(joint)}."
)


# ------------------------------------------------------------
# 6. PRICE LEVEL CORRELATION
# ------------------------------------------------------------

price_pivot = price_joint.pivot(
    index="date",
    columns="canonical_material",
    values="price_dollars_per_tonne",
)

price_level_corr = price_pivot.corr()

price_level_corr.to_csv(
    TABLES / "RO1_price_level_correlation.csv"
)

print("\n[5] PRICE LEVEL CORRELATION")
print(price_level_corr.round(3).to_string())


# ------------------------------------------------------------
# 7. DEMAND LEVEL CORRELATION
# ------------------------------------------------------------

demand_pivot = demand_joint.pivot(
    index="date",
    columns="canonical_material",
    values="demand_thousand_tonnes",
)

demand_level_corr = demand_pivot.corr()

demand_level_corr.to_csv(
    TABLES / "RO1_demand_level_correlation.csv"
)

print("\n[6] DEMAND LEVEL CORRELATION")
print(demand_level_corr.round(3).to_string())


# ------------------------------------------------------------
# 8. LOG-CHANGE CORRELATIONS
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

print("\n[7] PRICE LOG-CHANGE CORRELATION")
print(price_change_corr.round(3).to_string())

print("\n[8] DEMAND LOG-CHANGE CORRELATION")
print(demand_change_corr.round(3).to_string())


# ------------------------------------------------------------
# 9. WITHIN-MATERIAL PRICE-DEMAND CORRELATION
# ------------------------------------------------------------

rows = []

for material in mapping.loc[
    mapping["joint_forecasting"],
    "canonical_material",
]:

    temp = joint[
        joint["canonical_material"] == material
    ].sort_values("date")

    price_values = temp["price_dollars_per_tonne"]
    demand_values = temp["demand_thousand_tonnes"]

    level_corr = price_values.corr(
        demand_values
    )

    log_change_price = np.log(
        price_values
    ).diff()

    log_change_demand = np.log(
        demand_values
    ).diff()

    change_corr = log_change_price.corr(
        log_change_demand
    )

    rows.append(
        {
            "material": material,
            "n": len(temp),
            "price_demand_level_corr": level_corr,
            "price_demand_log_change_corr": change_corr,
        }
    )

within_corr = pd.DataFrame(rows)

within_corr.to_csv(
    TABLES / "RO1_within_material_price_demand_correlation.csv",
    index=False,
)

print("\n[9] WITHIN-MATERIAL PRICE-DEMAND CORRELATION")
print(within_corr.round(4).to_string(index=False))


# ------------------------------------------------------------
# 10. LAGGED PRICE-DEMAND CORRELATIONS
# ------------------------------------------------------------

lag_rows = []

for material in mapping.loc[
    mapping["joint_forecasting"],
    "canonical_material",
]:

    temp = joint[
        joint["canonical_material"] == material
    ].sort_values("date")

    p = temp[
        "price_dollars_per_tonne"
    ].reset_index(drop=True)

    d = temp[
        "demand_thousand_tonnes"
    ].reset_index(drop=True)

    for lag in range(-6, 7):

        if lag < 0:
            # Price leads demand by abs(lag) months
            corr = p.iloc[:lag].corr(
                d.iloc[-lag:]
            )

        elif lag > 0:
            # Demand leads price by lag months
            corr = p.iloc[lag:].corr(
                d.iloc[:-lag]
            )

        else:
            corr = p.corr(d)

        lag_rows.append(
            {
                "material": material,
                "lag_months_price_relative_to_demand": lag,
                "correlation": corr,
            }
        )

lagged_corr = pd.DataFrame(lag_rows)

lagged_corr.to_csv(
    TABLES / "RO1_price_demand_lagged_correlation.csv",
    index=False,
)

print("\n[10] LAGGED PRICE-DEMAND CORRELATION")

for material in lagged_corr["material"].unique():

    temp = lagged_corr[
        lagged_corr["material"] == material
    ]

    best = temp.loc[
        temp["correlation"].abs().idxmax()
    ]

    print(
        f"  {material}: "
        f"strongest |r| = {best['correlation']:.4f} "
        f"at lag {int(best['lag_months_price_relative_to_demand'])} month(s)"
    )


# ------------------------------------------------------------
# 11. COMMON TIME WINDOW CHECK
# ------------------------------------------------------------

print("\n[11] COMMON TIME WINDOW")

print(
    "Start:",
    joint["date"].min().strftime("%Y-%m"),
)

print(
    "End  :",
    joint["date"].max().strftime("%Y-%m"),
)


# ------------------------------------------------------------
# 12. FINAL STATUS
# ------------------------------------------------------------

print("\n" + "=" * 78)
print("STEP 21A CORRECTION COMPLETE")
print("MATERIAL MAPPING VALIDATED")
print("CORRELATION TABLES REGENERATED")
print("RAW CSV FILES WERE NOT MODIFIED")
print("=" * 78)
