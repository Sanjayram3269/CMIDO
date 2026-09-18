"""
CMIDO — RO1 STEP 25C.2B
Corrected Material-Level Test Comparison

Purpose
-------
Compare frozen multivariate forecasts against univariate baselines
at the MATERIAL × HORIZON level.

Price:
    Naive
    SeasonalNaive
    ETS
    SARIMA
    VECM

Demand:
    Naive
    SeasonalNaive
    ETS
    SARIMA
    VAR_DIFF

No model fitting occurs here.
No specification selection occurs here.

All results come from already-generated test forecasts/metrics.

Primary horizon:
    h = 3 months

Primary metric:
    MAE

Secondary:
    RMSE

The comparison is strictly material-specific.
No system-level metric is compared with a material-level metric.
"""


from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

MULTI_METRICS = (
    ROOT
    / "results"
    / "forecasting"
    / "multivariate"
    / "RO1_step25c2m_material_metrics.csv"
)

BASELINE_METRICS = (
    ROOT
    / "results"
    / "forecasting"
    / "baselines"
    / "RO1_step23_test_metrics.csv"
)

CLASSICAL_METRICS = (
    ROOT
    / "results"
    / "forecasting"
    / "classical"
    / "RO1_step24_test_metrics.csv"
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

HORIZONS = [
    1,
    3,
    6,
    12,
]

PRIMARY_HORIZON = 3

PRICE_DATASET = "RO1_PRICE"
DEMAND_DATASET = "RO1_DEMAND"

PRICE_MULTIVARIATE_MODEL = "VECM"
DEMAND_MULTIVARIATE_MODEL = "VAR_DIFF"

UNIVARIATE_MODELS = {
    "Naive",
    "SeasonalNaive",
    "ETS",
    "SARIMA",
}


# ============================================================================
# HEADER
# ============================================================================

print("=" * 78)
print("CMIDO RO1 — STEP 25C.2B")
print("CORRECTED MATERIAL-LEVEL TEST COMPARISON")
print("=" * 78)


# ============================================================================
# HELPERS
# ============================================================================

def detect_column(
    df,
    candidates,
    description,
):

    for candidate in candidates:

        if candidate in df.columns:

            return candidate

    raise RuntimeError(
        f"Could not identify {description}.\n"
        f"Available columns:\n{list(df.columns)}"
    )


def normalize_material(
    value,
):

    text = str(value).strip()

    mapping = {
        "Cement In Bulk (Ordinary Portland Cement)":
            "Cement",

        "Steel Reinforcement Bars (16-32mm High Tensile)":
            "Steel Reinforcement Bars",

        "Granite (20mm Aggregate)":
            "Granite",

        "Ready Mixed Concrete":
            "Ready-Mixed Concrete",

        "Ready-Mixed Concrete":
            "Ready-Mixed Concrete",

        "Concreting Sand":
            "Concreting Sand",

        "Cement":
            "Cement",

        "Steel Reinforcement Bars":
            "Steel Reinforcement Bars",

        "Granite":
            "Granite",
    }

    return mapping.get(
        text,
        text,
    )


def standardize_metrics(
    df,
    source_name,
):

    work = df.copy()

    # ------------------------------------------------------------------
    # Identify material column
    # ------------------------------------------------------------------

    material_column = detect_column(
        work,
        [
            "material",
            "series",
            "DataSeries",
        ],
        "material/series column",
    )

    work = work.rename(
        columns={
            material_column:
                "material"
        }
    )

    # ------------------------------------------------------------------
    # Identify dataset
    # ------------------------------------------------------------------

    if "dataset" not in work.columns:

        raise RuntimeError(
            f"{source_name} does not contain a dataset column."
        )

    # ------------------------------------------------------------------
    # Identify model
    # ------------------------------------------------------------------

    if "model" not in work.columns:

        raise RuntimeError(
            f"{source_name} does not contain a model column."
        )

    # ------------------------------------------------------------------
    # Identify horizon
    # ------------------------------------------------------------------

    if "horizon" not in work.columns:

        raise RuntimeError(
            f"{source_name} does not contain a horizon column."
        )

    # ------------------------------------------------------------------
    # Identify MAE
    # ------------------------------------------------------------------

    if "MAE" in work.columns:

        work["mean_MAE"] = pd.to_numeric(
            work["MAE"],
            errors="raise",
        )

    elif "mean_MAE" in work.columns:

        work["mean_MAE"] = pd.to_numeric(
            work["mean_MAE"],
            errors="raise",
        )

    else:

        raise RuntimeError(
            f"{source_name} has no MAE column."
        )

    # ------------------------------------------------------------------
    # Identify RMSE
    # ------------------------------------------------------------------

    if "RMSE" in work.columns:

        work["mean_RMSE"] = pd.to_numeric(
            work["RMSE"],
            errors="raise",
        )

    elif "mean_RMSE" in work.columns:

        work["mean_RMSE"] = pd.to_numeric(
            work["mean_RMSE"],
            errors="raise",
        )

    else:

        raise RuntimeError(
            f"{source_name} has no RMSE column."
        )

    # ------------------------------------------------------------------
    # Normalize
    # ------------------------------------------------------------------

    work["material"] = (
        work["material"]
        .map(
            normalize_material
        )
    )

    work["horizon"] = (
        pd.to_numeric(
            work["horizon"]
        )
        .astype(int)
    )

    work["source"] = source_name

    return work[
        [
            "dataset",
            "model",
            "material",
            "horizon",
            "mean_MAE",
            "mean_RMSE",
            "source",
        ]
    ].copy()


# ============================================================================
# LOAD MULTIVARIATE MATERIAL METRICS
# ============================================================================

print(
    "\n[1] LOADING FROZEN MULTIVARIATE MATERIAL METRICS"
)

if not MULTI_METRICS.exists():

    raise FileNotFoundError(
        f"Missing material-level multivariate metrics:\n"
        f"{MULTI_METRICS}"
    )


multi = pd.read_csv(
    MULTI_METRICS
)

print(
    f"Rows: {len(multi)}"
)

print(
    f"Columns: {list(multi.columns)}"
)


multi = standardize_metrics(
    multi,
    "STEP25C2M_MULTIVARIATE",
)


# ============================================================================
# VERIFY MULTIVARIATE MODELS
# ============================================================================

print(
    "\nMultivariate models:"
)

print(
    multi[
        [
            "dataset",
            "model",
        ]
    ]
    .drop_duplicates()
    .to_string(
        index=False
    )
)


assert set(
    multi["model"]
) == {
    "VECM",
    "VAR_DIFF",
}


# ============================================================================
# LOAD STEP 23
# ============================================================================

print(
    "\n[2] LOADING STEP 23 BASELINES"
)

if not BASELINE_METRICS.exists():

    raise FileNotFoundError(
        f"Missing Step 23 metrics:\n"
        f"{BASELINE_METRICS}"
    )


baseline = pd.read_csv(
    BASELINE_METRICS
)

print(
    f"Rows: {len(baseline)}"
)

print(
    f"Columns: {list(baseline.columns)}"
)


baseline = standardize_metrics(
    baseline,
    "STEP23_BASELINE",
)


print(
    "\nStep 23 models:"
)

print(
    sorted(
        baseline[
            "model"
        ]
        .unique()
    )
)


# ============================================================================
# LOAD STEP 24
# ============================================================================

print(
    "\n[3] LOADING STEP 24 CLASSICAL MODELS"
)

if not CLASSICAL_METRICS.exists():

    raise FileNotFoundError(
        f"Missing Step 24 metrics:\n"
        f"{CLASSICAL_METRICS}"
    )


classical = pd.read_csv(
    CLASSICAL_METRICS
)

print(
    f"Rows: {len(classical)}"
)

print(
    f"Columns: {list(classical.columns)}"
)


classical = standardize_metrics(
    classical,
    "STEP24_CLASSICAL",
)


print(
    "\nStep 24 models:"
)

print(
    sorted(
        classical[
            "model"
        ]
        .unique()
    )
)


# ============================================================================
# COMBINE
# ============================================================================

print(
    "\n[4] COMBINING MATERIAL-LEVEL RESULTS"
)

all_metrics = pd.concat(
    [
        baseline,
        classical,
        multi,
    ],
    ignore_index=True,
)


# ============================================================================
# MODEL NAME AUDIT
# ============================================================================

print(
    "\nModels available:"
)

print(
    sorted(
        all_metrics[
            "model"
        ]
        .unique()
    )
)


# ============================================================================
# REMOVE ANY DUPLICATE MODEL RESULTS
# ============================================================================

duplicate_keys = [
    "dataset",
    "model",
    "material",
    "horizon",
]


duplicate_count = (
    all_metrics
    .duplicated(
        subset=duplicate_keys
    )
    .sum()
)


print(
    f"\nDuplicate model/material/horizon rows: "
    f"{duplicate_count}"
)


if duplicate_count > 0:

    duplicate_rows = (
        all_metrics.loc[
            all_metrics.duplicated(
                subset=duplicate_keys,
                keep=False,
            )
        ]
        .sort_values(
            duplicate_keys
        )
    )

    print(
        duplicate_rows.to_string(
            index=False
        )
    )

    raise RuntimeError(
        "Duplicate model/material/horizon combinations detected."
    )


# ============================================================================
# EXPECTED MATERIALS
# ============================================================================

PRICE_MATERIALS = {
    "Cement",
    "Steel Reinforcement Bars",
    "Granite",
    "Concreting Sand",
    "Ready-Mixed Concrete",
}

DEMAND_MATERIALS = {
    "Cement",
    "Steel Reinforcement Bars",
    "Granite",
    "Ready-Mixed Concrete",
}


# ============================================================================
# FILTER TO VALID COMPARISON MODELS
# ============================================================================

price_comparison = all_metrics.loc[
    (
        all_metrics[
            "dataset"
        ]
        == PRICE_DATASET
    )
    &
    (
        all_metrics[
            "material"
        ].isin(
            PRICE_MATERIALS
        )
    )
].copy()


demand_comparison = all_metrics.loc[
    (
        all_metrics[
            "dataset"
        ]
        == DEMAND_DATASET
    )
    &
    (
        all_metrics[
            "material"
        ].isin(
            DEMAND_MATERIALS
        )
    )
].copy()


# ============================================================================
# MODEL COVERAGE
# ============================================================================

print(
    "\n[5] MODEL COVERAGE AUDIT"
)

print(
    "\nPRICE:"
)

print(
    price_comparison[
        [
            "material",
            "model",
            "horizon",
        ]
    ]
    .drop_duplicates()
    .groupby(
        [
            "material",
            "model",
        ]
    )
    .size()
    .to_string()
)


print(
    "\nDEMAND:"
)

print(
    demand_comparison[
        [
            "material",
            "model",
            "horizon",
        ]
    ]
    .drop_duplicates()
    .groupby(
        [
            "material",
            "model",
        ]
    )
    .size()
    .to_string()
)


# ============================================================================
# EXPECTED MODEL SET
# ============================================================================

expected_price_models = (
    UNIVARIATE_MODELS
    |
    {
        PRICE_MULTIVARIATE_MODEL
    }
)

expected_demand_models = (
    UNIVARIATE_MODELS
    |
    {
        DEMAND_MULTIVARIATE_MODEL
    }
)


# ============================================================================
# BUILD FAIR COMPARISON
# ============================================================================

print(
    "\n[6] BUILDING MATERIAL × HORIZON COMPARISON"
)


comparison_rows = []


def build_comparison(
    dataset,
    materials,
    expected_models,
):

    rows = []

    subset = all_metrics.loc[
        (
            all_metrics[
                "dataset"
            ]
            == dataset
        )
        &
        (
            all_metrics[
                "material"
            ].isin(materials)
        )
    ].copy()

    for material in sorted(
        materials
    ):

        for horizon in HORIZONS:

            cell = subset.loc[
                (
                    subset[
                        "material"
                    ]
                    == material
                )
                &
                (
                    subset[
                        "horizon"
                    ]
                    == horizon
                )
            ].copy()

            found_models = set(
                cell[
                    "model"
                ]
            )

            missing_models = (
                expected_models
                -
                found_models
            )

            if missing_models:

                raise RuntimeError(
                    f"Missing models for "
                    f"{dataset} / "
                    f"{material} / "
                    f"h={horizon}: "
                    f"{sorted(missing_models)}"
                )

            for model in sorted(
                expected_models
            ):

                row = cell.loc[
                    cell[
                        "model"
                    ]
                    == model
                ]

                if len(row) != 1:

                    raise RuntimeError(
                        f"Expected exactly one "
                        f"row for "
                        f"{dataset} / "
                        f"{material} / "
                        f"h={horizon} / "
                        f"{model}; "
                        f"found {len(row)}."
                    )

                record = (
                    row.iloc[0]
                )

                rows.append(
                    {
                        "dataset":
                            dataset,

                        "material":
                            material,

                        "horizon":
                            horizon,

                        "model":
                            model,

                        "MAE":
                            float(
                                record[
                                    "mean_MAE"
                                ]
                            ),

                        "RMSE":
                            float(
                                record[
                                    "mean_RMSE"
                                ]
                            ),

                        "source":
                            record[
                                "source"
                            ],
                    }
                )

    return pd.DataFrame(
        rows
    )


price_fair = build_comparison(
    PRICE_DATASET,
    PRICE_MATERIALS,
    expected_price_models,
)


demand_fair = build_comparison(
    DEMAND_DATASET,
    DEMAND_MATERIALS,
    expected_demand_models,
)


fair_comparison = pd.concat(
    [
        price_fair,
        demand_fair,
    ],
    ignore_index=True,
)


# ============================================================================
# BEST MODEL BY MATERIAL / HORIZON
# ============================================================================

print(
    "\n[7] BEST MODEL BY MATERIAL × HORIZON"
)

best_model = (
    fair_comparison
    .sort_values(
        [
            "dataset",
            "material",
            "horizon",
            "MAE",
        ]
    )
    .groupby(
        [
            "dataset",
            "material",
            "horizon",
        ],
        as_index=False,
    )
    .first()
)


print(
    best_model.to_string(
        index=False
    )
)


# ============================================================================
# MULTIVARIATE VS BEST UNIVARIATE
# ============================================================================

print(
    "\n[8] MULTIVARIATE VS BEST UNIVARIATE"
)


rows = []


for dataset, materials, multi_model in [
    (
        PRICE_DATASET,
        PRICE_MATERIALS,
        PRICE_MULTIVARIATE_MODEL,
    ),
    (
        DEMAND_DATASET,
        DEMAND_MATERIALS,
        DEMAND_MULTIVARIATE_MODEL,
    ),
]:

    for material in sorted(
        materials
    ):

        for horizon in HORIZONS:

            cell = fair_comparison.loc[
                (
                    fair_comparison[
                        "dataset"
                    ]
                    == dataset
                )
                &
                (
                    fair_comparison[
                        "material"
                    ]
                    == material
                )
                &
                (
                    fair_comparison[
                        "horizon"
                    ]
                    == horizon
                )
            ].copy()


            multi_row = cell.loc[
                cell[
                    "model"
                ]
                == multi_model
            ]

            uni_rows = cell.loc[
                cell[
                    "model"
                ]
                .isin(
                    UNIVARIATE_MODELS
                )
            ]


            if len(multi_row) != 1:

                raise RuntimeError(
                    "Multivariate result missing "
                    f"for {dataset}, "
                    f"{material}, h={horizon}"
                )


            if len(uni_rows) != 4:

                raise RuntimeError(
                    "Expected four univariate "
                    f"models for {dataset}, "
                    f"{material}, h={horizon}; "
                    f"found {len(uni_rows)}"
                )


            multi_mae = float(
                multi_row[
                    "MAE"
                ].iloc[0]
            )


            best_uni_idx = (
                uni_rows[
                    "MAE"
                ]
                .idxmin()
            )


            best_uni = (
                uni_rows
                .loc[
                    best_uni_idx
                ]
            )


            best_uni_mae = float(
                best_uni[
                    "MAE"
                ]
            )


            improvement = (
                (
                    best_uni_mae
                    -
                    multi_mae
                )
                /
                best_uni_mae
                *
                100
            )


            rows.append(
                {
                    "dataset":
                        dataset,

                    "material":
                        material,

                    "horizon":
                        horizon,

                    "multivariate_model":
                        multi_model,

                    "multivariate_MAE":
                        multi_mae,

                    "best_univariate_model":
                        best_uni[
                            "model"
                        ],

                    "best_univariate_MAE":
                        best_uni_mae,

                    "improvement_percent":
                        improvement,

                    "multivariate_wins":
                        bool(
                            multi_mae
                            <
                            best_uni_mae
                        ),
                }
            )


multi_vs_best = pd.DataFrame(
    rows
)


print(
    multi_vs_best.to_string(
        index=False
    )
)


# ============================================================================
# PRIMARY H=3
# ============================================================================

print(
    "\n[9] PRIMARY H=3 RESULTS"
)

primary_h3 = (
    multi_vs_best.loc[
        multi_vs_best[
            "horizon"
        ]
        == PRIMARY_HORIZON
    ]
    .copy()
)


print(
    primary_h3.to_string(
        index=False
    )
)


# ============================================================================
# WIN SUMMARY
# ============================================================================

print(
    "\n[10] MULTIVARIATE WIN SUMMARY"
)


win_summary = (
    multi_vs_best
    .groupby(
        [
            "dataset",
            "horizon",
        ]
    )
    .agg(
        material_count=(
            "material",
            "count",
        ),

        multivariate_wins=(
            "multivariate_wins",
            "sum",
        ),

        mean_improvement_percent=(
            "improvement_percent",
            "mean",
        ),

        median_improvement_percent=(
            "improvement_percent",
            "median",
        ),
    )
    .reset_index()
)


win_summary[
    "win_rate"
] = (
    win_summary[
        "multivariate_wins"
    ]
    /
    win_summary[
        "material_count"
    ]
)


print(
    win_summary.to_string(
        index=False
    )
)


# ============================================================================
# PRIMARY H=3 WIN SUMMARY
# ============================================================================

print(
    "\n[11] PRIMARY H=3 WIN SUMMARY"
)


primary_win_summary = (
    win_summary.loc[
        win_summary[
            "horizon"
        ]
        == PRIMARY_HORIZON
    ]
    .copy()
)


print(
    primary_win_summary.to_string(
        index=False
    )
)


# ============================================================================
# OVERALL MODEL RANKING
# ============================================================================

print(
    "\n[12] MODEL WIN COUNTS — ALL MATERIALS / HORIZONS"
)


overall_wins = (
    fair_comparison
    .merge(
        best_model[
            [
                "dataset",
                "material",
                "horizon",
                "model",
            ]
        ],
        on=[
            "dataset",
            "material",
            "horizon",
        ],
        suffixes=(
            "",
            "_best",
        ),
    )
)


overall_wins[
    "is_best"
] = (
    overall_wins[
        "model"
    ]
    ==
    overall_wins[
        "model_best"
    ]
)


model_win_counts = (
    overall_wins
    .groupby(
        [
            "dataset",
            "model",
        ]
    )
    .agg(
        cells=(
            "is_best",
            "count",
        ),

        wins=(
            "is_best",
            "sum",
        ),
    )
    .reset_index()
)


model_win_counts[
    "win_rate"
] = (
    model_win_counts[
        "wins"
    ]
    /
    model_win_counts[
        "cells"
    ]
)


print(
    model_win_counts.to_string(
        index=False
    )
)


# ============================================================================
# SAVE OUTPUTS
# ============================================================================

print(
    "\n[13] SAVING OUTPUTS"
)


fair_comparison_path = (
    OUTPUT_DIR
    / "RO1_step25c2b_fair_material_model_comparison.csv"
)

best_model_path = (
    OUTPUT_DIR
    / "RO1_step25c2b_best_model_by_material_horizon.csv"
)

multi_vs_best_path = (
    OUTPUT_DIR
    / "RO1_step25c2b_multivariate_vs_best_univariate.csv"
)

primary_path = (
    OUTPUT_DIR
    / "RO1_step25c2b_primary_h3.csv"
)

win_summary_path = (
    OUTPUT_DIR
    / "RO1_step25c2b_win_summary.csv"
)

primary_win_path = (
    OUTPUT_DIR
    / "RO1_step25c2b_primary_h3_win_summary.csv"
)

model_win_path = (
    OUTPUT_DIR
    / "RO1_step25c2b_model_win_counts.csv"
)


fair_comparison.to_csv(
    fair_comparison_path,
    index=False,
)

best_model.to_csv(
    best_model_path,
    index=False,
)

multi_vs_best.to_csv(
    multi_vs_best_path,
    index=False,
)

primary_h3.to_csv(
    primary_path,
    index=False,
)

win_summary.to_csv(
    win_summary_path,
    index=False,
)

primary_win_summary.to_csv(
    primary_win_path,
    index=False,
)

model_win_counts.to_csv(
    model_win_path,
    index=False,
)


# ============================================================================
# FINAL ASSERTIONS
# ============================================================================

print(
    "\n[14] FINAL ASSERTIONS"
)


# 5 price materials × 4 horizons × 5 models
expected_price_rows = (
    5
    * 4
    * 5
)

# 4 demand materials × 4 horizons × 5 models
expected_demand_rows = (
    4
    * 4
    * 5
)

expected_total_rows = (
    expected_price_rows
    +
    expected_demand_rows
)


assert (
    len(fair_comparison)
    ==
    expected_total_rows
)


assert (
    len(primary_h3)
    ==
    9
)


assert (
    fair_comparison[
        "MAE"
    ]
    .notna()
    .all()
)


assert (
    fair_comparison[
        "RMSE"
    ]
    .notna()
    .all()
)


assert (
    np.isfinite(
        fair_comparison[
            "MAE"
        ]
    )
    .all()
)


assert (
    np.isfinite(
        fair_comparison[
            "RMSE"
        ]
    )
    .all()
)


assert (
    set(
        fair_comparison[
            "horizon"
        ]
    )
    ==
    set(HORIZONS)
)


assert (
    set(
        primary_h3[
            "dataset"
        ]
    )
    ==
    {
        PRICE_DATASET,
        DEMAND_DATASET,
    }
)


assert (
    set(
        multi_vs_best[
            "horizon"
        ]
    )
    ==
    set(HORIZONS)
)


print(
    "Material-level comparison integrity: PASS"
)

print(
    "Material identity preservation: PASS"
)

print(
    "Price model coverage: PASS"
)

print(
    "Demand model coverage: PASS"
)

print(
    "Horizon coverage: PASS"
)

print(
    "No system-vs-material metric mixing: PASS"
)

print(
    "Multivariate vs best-univariate comparison: PASS"
)

print(
    "Primary h=3 comparison: PASS"
)


# ============================================================================
# COMPLETION
# ============================================================================

print(
    "\n" + "=" * 78
)

print(
    "STEP 25C.2B COMPLETE"
)

print(
    "=" * 78
)

print(
    "The material-level apples-to-apples comparison is complete."
)

print(
    "\nPrimary output:"
)

print(
    primary_path
)

print(
    "\nFull comparison:"
)

print(
    fair_comparison_path
)

print(
    "\nMultivariate vs best univariate:"
)

print(
    multi_vs_best_path
)

print(
    "\nNo model was refitted."
)

print(
    "No specification was changed."
)

print(
    "No test-based model selection was performed."
)

print(
    "\nRO1 STEP 25C.2B: READY FOR STATISTICAL COMPARISON"
)

print(
    "=" * 78
)