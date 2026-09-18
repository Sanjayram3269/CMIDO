"""
CMIDO — RO2 Step 27D.4
Nested Common-Random-Number Monte Carlo Convergence Audit

Run from:
    D:/CMIDO

Command:
    python src/propagation/27d4_nested_common_random_number_convergence.py

Purpose:
    Re-run the frozen 27D propagation using ONE deterministic 25,000-draw
    master stream per material/origin and evaluate nested prefixes.

RO1:
    Step 26C.3 CQR validation forecast artifact.

RO2:
    Step 27B.4 admissible modelling view.

Important:
    RO2 contains procurement-process duration data, not supplier-specific
    material lead-time history. The duration sample is therefore treated as
    the locked aggregate procurement-process-duration proxy.

No RO1 test forecasts are used.
No optimization is performed.
No scientific assumptions are changed by this convergence audit.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parents[2]

RO1_VALIDATION = (
    ROOT
    / "results"
    / "forecasting"
    / "probabilistic_calibration"
    / "RO1_step26c3_validation_forecasts.csv"
)

RO2_COMPONENTS = (
    ROOT
    / "results"
    / "RO2"
    / "data_audit"
    / "RO2_step27b4_admissible_modelling_view.csv"
)

OUT_DIR = (
    ROOT
    / "results"
    / "RO2"
    / "propagation_convergence_nested"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================================
# LOCKED EXPERIMENT SETTINGS
# =============================================================================

MC_SIZES = (
    1000,
    2500,
    5000,
    10000,
    25000,
)

MATERIALS = [
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
]

SOURCE_HORIZONS = (
    1,
    3,
    6,
    12,
)

QUANTILES = (
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
)

CRITERIA = {
    "mean": 1.0,
    "q90": 2.0,
    "q95": 2.0,
    "q99": 5.0,
}

MASTER_SEED = 27404

# Locked paired RO2 component sample.
N_DURATION = 37

# 4 materials × 12 forecast origins.
N_CASES = 48


# =============================================================================
# DETERMINISTIC CASE SEED
# =============================================================================

def stable_seed(
    material: str,
    origin: str,
) -> int:
    """
    Generate a deterministic seed for each material/origin case.
    """

    raw = (
        f"{MASTER_SEED}|{material}|{origin}"
    ).encode("utf-8")

    digest = hashlib.sha256(
        raw
    ).digest()

    return (
        int.from_bytes(
            digest[:8],
            "little",
        )
        % (2**32 - 1)
    )


# =============================================================================
# CALENDAR HELPERS
# =============================================================================

def month_starts_after(
    origin: pd.Timestamp,
    n: int = 12,
):
    """
    Return the first n calendar-month starts after the forecast origin.
    """

    first = (
        origin.to_period("M").to_timestamp()
        + pd.offsets.MonthBegin(1)
    )

    return pd.date_range(
        first,
        periods=n,
        freq="MS",
    )


# =============================================================================
# INVERSE QUANTILE SAMPLING
# =============================================================================

def inverse_piecewise(
    u,
    q_values,
):
    """
    Frozen marginal-demand representation.

    q10..q90 are used as the available marginal quantile representation.

    Lower tail:
        linear extension from q10 toward p=0.

    Middle:
        piecewise-linear interpolation.

    Upper tail:
        linear extension from q90 using the final quantile-segment slope.

    Demand is constrained to be non-negative.
    """

    probs = np.asarray(
        QUANTILES,
        dtype=float,
    )

    vals = np.asarray(
        q_values,
        dtype=float,
    )

    vals = np.maximum.accumulate(
        np.maximum(
            vals,
            0.0,
        )
    )

    u = np.asarray(
        u,
        dtype=float,
    )

    out = np.empty_like(
        u
    )

    lower = u < probs[0]
    upper = u > probs[-1]
    middle = ~(lower | upper)

    # -------------------------------------------------------------------------
    # Middle quantile region.
    # -------------------------------------------------------------------------

    if np.any(middle):

        out[middle] = np.interp(
            u[middle],
            probs,
            vals,
        )

    # -------------------------------------------------------------------------
    # Lower tail.
    # -------------------------------------------------------------------------

    if np.any(lower):

        slope = (
            vals[0] / probs[0]
            if probs[0] > 0
            else 0.0
        )

        out[lower] = np.maximum(
            0.0,
            vals[0]
            + slope
            * (
                u[lower]
                - probs[0]
            ),
        )

    # -------------------------------------------------------------------------
    # Upper tail.
    # -------------------------------------------------------------------------

    if np.any(upper):

        slope = (
            (vals[-1] - vals[-2])
            / (
                probs[-1]
                - probs[-2]
            )
        )

        out[upper] = np.maximum(
            0.0,
            vals[-1]
            + slope
            * (
                u[upper]
                - probs[-1]
            ),
        )

    return np.maximum(
        out,
        0.0,
    )


# =============================================================================
# EXACT CALENDAR OVERLAP
# =============================================================================

def exact_overlap_days(
    start,
    duration_days,
    month_start,
):
    """
    Calculate exact calendar-day overlap between the procurement-process
    duration interval and a calendar month.
    """

    end = (
        start
        + pd.to_timedelta(
            float(duration_days),
            unit="D",
        )
    )

    month_end = (
        month_start
        + pd.offsets.MonthBegin(1)
    )

    left = max(
        start,
        month_start,
    )

    right = min(
        end,
        month_end,
    )

    return max(
        0.0,
        (
            right - left
        ).total_seconds()
        / 86400.0,
    )


# =============================================================================
# INPUT LOADING
# =============================================================================

def load_inputs():
    """
    Load the actual RO1 CQR validation artifact and RO2 27B.4 modelling view.

    RO1 actual schema:
        dataset
        series
        horizon
        forecast_origin
        q10 ... q90

    Only:
        dataset == RO1_DEMAND

    is retained.

    RO2 actual schema:
        Internal_num
        PODN_num
        TotalDN_num
        admissible_component

    The 37 paired component rows are selected from:
        admissible_component == True

    and normalized internally to:
        internal_days
        po_gr_days
        total_days
    """

    # -------------------------------------------------------------------------
    # File existence.
    # -------------------------------------------------------------------------

    if not RO1_VALIDATION.exists():

        raise FileNotFoundError(
            "RO1 validation forecast file not found:\n"
            f"{RO1_VALIDATION}"
        )

    if not RO2_COMPONENTS.exists():

        raise FileNotFoundError(
            "RO2 27B.4 modelling view not found:\n"
            f"{RO2_COMPONENTS}"
        )

    # -------------------------------------------------------------------------
    # Load files.
    # -------------------------------------------------------------------------

    vf = pd.read_csv(
        RO1_VALIDATION
    )

    comp = pd.read_csv(
        RO2_COMPONENTS
    )

    # =========================================================================
    # RO1 VALIDATION FORECAST
    # =========================================================================

    required_vf = {
        "dataset",
        "series",
        "forecast_origin",
        "horizon",
        "q10",
        "q25",
        "q50",
        "q75",
        "q90",
    }

    missing = (
        required_vf
        - set(vf.columns)
    )

    if missing:

        raise AssertionError(
            "RO1 validation forecast missing columns: "
            f"{sorted(missing)}"
        )

    # -------------------------------------------------------------------------
    # Reject explicit RO1_TEST rows.
    # -------------------------------------------------------------------------

    test_rows = vf[
        vf["dataset"]
        .astype(str)
        .str.upper()
        .eq("RO1_TEST")
    ]

    if len(test_rows):

        raise AssertionError(
            "RO1 test forecasts are present in input."
        )

    # -------------------------------------------------------------------------
    # Select only RO1 demand.
    # -------------------------------------------------------------------------

    vf = vf[
        vf["dataset"]
        .astype(str)
        .str.upper()
        .eq("RO1_DEMAND")
    ].copy()

    if len(vf) == 0:

        raise AssertionError(
            "No RO1_DEMAND rows found in RO1 CQR validation artifact."
        )

    # -------------------------------------------------------------------------
    # Normalize series → material.
    # -------------------------------------------------------------------------

    vf = vf.rename(
        columns={
            "series": "material"
        }
    )

    # -------------------------------------------------------------------------
    # Restrict to locked materials.
    # -------------------------------------------------------------------------

    vf = vf[
        vf["material"].isin(
            MATERIALS
        )
        & vf["horizon"].isin(
            SOURCE_HORIZONS
        )
    ].copy()

    # -------------------------------------------------------------------------
    # Data types.
    # -------------------------------------------------------------------------

    vf["forecast_origin"] = pd.to_datetime(
        vf["forecast_origin"],
        errors="raise",
    )

    vf["horizon"] = pd.to_numeric(
        vf["horizon"],
        errors="raise",
    ).astype(int)

    # -------------------------------------------------------------------------
    # Quantile numeric validation.
    # -------------------------------------------------------------------------

    quantile_columns = [
        "q10",
        "q25",
        "q50",
        "q75",
        "q90",
    ]

    for col in quantile_columns:

        vf[col] = pd.to_numeric(
            vf[col],
            errors="raise",
        )

        values = vf[col].to_numpy(
            dtype=float
        )

        if not np.all(
            np.isfinite(values)
        ):

            raise AssertionError(
                f"RO1 column '{col}' contains non-finite values."
            )

    # -------------------------------------------------------------------------
    # Demand must be non-negative.
    # -------------------------------------------------------------------------

    if (
        vf[quantile_columns]
        < 0
    ).any().any():

        raise AssertionError(
            "RO1 demand quantiles contain negative values."
        )

    # -------------------------------------------------------------------------
    # Quantile ordering.
    # -------------------------------------------------------------------------

    q10 = vf["q10"].to_numpy(
        dtype=float
    )

    q25 = vf["q25"].to_numpy(
        dtype=float
    )

    q50 = vf["q50"].to_numpy(
        dtype=float
    )

    q75 = vf["q75"].to_numpy(
        dtype=float
    )

    q90 = vf["q90"].to_numpy(
        dtype=float
    )

    ordered = (
        (q10 <= q25)
        & (q25 <= q50)
        & (q50 <= q75)
        & (q75 <= q90)
    )

    if not np.all(ordered):

        raise AssertionError(
            "RO1 quantile ordering failed."
        )

    # -------------------------------------------------------------------------
    # Complete material-origin cases.
    # -------------------------------------------------------------------------

    counts = (
        vf.groupby(
            [
                "material",
                "forecast_origin",
            ]
        )["horizon"]
        .nunique()
        .reset_index(
            name="n_horizons"
        )
    )

    complete = counts[
        counts["n_horizons"]
        == len(SOURCE_HORIZONS)
    ].copy()

    if len(complete) != N_CASES:

        raise AssertionError(
            f"Expected {N_CASES} complete "
            f"material-origin cases; "
            f"found {len(complete)}."
        )

    # -------------------------------------------------------------------------
    # Keep only complete cases.
    # -------------------------------------------------------------------------

    complete_keys = complete[
        [
            "material",
            "forecast_origin",
        ]
    ].drop_duplicates()

    vf = vf.merge(
        complete_keys,
        on=[
            "material",
            "forecast_origin",
        ],
        how="inner",
        validate="many_to_one",
    )

    # -------------------------------------------------------------------------
    # No duplicate material-origin-horizon rows.
    # -------------------------------------------------------------------------

    duplicate_mask = vf.duplicated(
        subset=[
            "material",
            "forecast_origin",
            "horizon",
        ],
        keep=False,
    )

    if duplicate_mask.any():

        raise AssertionError(
            "Duplicate RO1 material-origin-horizon "
            "rows detected."
        )

    # -------------------------------------------------------------------------
    # Expected row count:
    #
    # 48 cases × 4 source horizons = 192
    # -------------------------------------------------------------------------

    expected_rows = (
        N_CASES
        * len(SOURCE_HORIZONS)
    )

    if len(vf) != expected_rows:

        raise AssertionError(
            "Unexpected RO1 validation row count: "
            f"{len(vf)}; expected {expected_rows}."
        )

    # =========================================================================
    # RO2 27B.4 MODELLING VIEW
    # =========================================================================

    required_comp = {
        "Internal_num",
        "PODN_num",
        "TotalDN_num",
        "admissible_component",
    }

    missing = (
        required_comp
        - set(comp.columns)
    )

    if missing:

        raise AssertionError(
            "RO2 27B.4 modelling view missing columns: "
            f"{sorted(missing)}"
        )

    # -------------------------------------------------------------------------
    # The 27B.4 view contains 57 rows, but only the paired component rows
    # are admissible for joint duration propagation.
    # -------------------------------------------------------------------------

    comp_flag = (
        comp["admissible_component"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(
            [
                "true",
                "1",
                "yes",
            ]
        )
    )

    comp = comp[
        comp_flag
    ].copy()

    # -------------------------------------------------------------------------
    # Convert duration components to numeric.
    # -------------------------------------------------------------------------

    duration_source_columns = [
        "Internal_num",
        "PODN_num",
        "TotalDN_num",
    ]

    for col in duration_source_columns:

        comp[col] = pd.to_numeric(
            comp[col],
            errors="coerce",
        )

    # -------------------------------------------------------------------------
    # Keep only rows with all three component values.
    #
    # This is an additional safety check; the admissible_component flag
    # remains the primary locked selection rule.
    # -------------------------------------------------------------------------

    comp = comp.dropna(
        subset=[
            "Internal_num",
            "PODN_num",
            "TotalDN_num",
        ]
    ).copy()

    # -------------------------------------------------------------------------
    # Normalize actual RO2 column names to canonical internal names.
    # -------------------------------------------------------------------------

    comp = comp.rename(
        columns={
            "Internal_num": "internal_days",
            "PODN_num": "po_gr_days",
            "TotalDN_num": "total_days",
        }
    )

    # -------------------------------------------------------------------------
    # Exact locked paired sample size.
    # -------------------------------------------------------------------------

    if len(comp) != N_DURATION:

        raise AssertionError(
            "Expected the locked paired RO2 duration sample "
            f"to contain {N_DURATION} rows; "
            f"found {len(comp)}."
        )

    # -------------------------------------------------------------------------
    # Numeric finite validation.
    # -------------------------------------------------------------------------

    duration_columns = [
        "internal_days",
        "po_gr_days",
        "total_days",
    ]

    for col in duration_columns:

        values = comp[col].to_numpy(
            dtype=float
        )

        if not np.all(
            np.isfinite(values)
        ):

            raise AssertionError(
                f"RO2 duration column '{col}' "
                "contains non-finite values."
            )

    # -------------------------------------------------------------------------
    # Durations must be non-negative.
    # -------------------------------------------------------------------------

    if (
        comp[duration_columns]
        < 0
    ).any().any():

        raise AssertionError(
            "RO2 duration sample contains negative values."
        )

    # -------------------------------------------------------------------------
    # Exact reconstruction:
    #
    # Internal + PO-GR = Total
    # -------------------------------------------------------------------------

    reconstructed_total = (
        comp["internal_days"]
        + comp["po_gr_days"]
    )

    reconstruction_error = np.abs(
        reconstructed_total
        - comp["total_days"]
    )

    if not np.allclose(
        reconstruction_error,
        0.0,
        atol=1e-12,
    ):

        raise AssertionError(
            "RO2 duration reconstruction failed. "
            "Internal_num + PODN_num does not exactly "
            "reconstruct TotalDN_num."
        )

    return vf, comp


# =============================================================================
# BUILD 12-MONTH DEMAND QUANTILES
# =============================================================================

def build_horizon_quantiles(
    vf,
    material,
    origin,
):
    """
    Interpolate source horizons:

        1, 3, 6, 12

    to all integer horizons:

        1..12

    using linear interpolation.

    No extrapolation beyond the 1..12 propagation window.
    """

    group = vf[
        vf["material"].eq(material)
        & vf["forecast_origin"].eq(origin)
    ].copy()

    observed = sorted(
        group["horizon"]
        .unique()
        .tolist()
    )

    if observed != list(
        SOURCE_HORIZONS
    ):

        raise AssertionError(
            f"Incomplete source horizons for "
            f"{material}/{origin}: "
            f"{observed}"
        )

    group = group.sort_values(
        "horizon"
    )

    target_horizons = np.arange(
        1,
        13,
    )

    output = {}

    for q in [
        "q10",
        "q25",
        "q50",
        "q75",
        "q90",
    ]:

        source_values = (
            group[q]
            .astype(float)
            .to_numpy()
        )

        if not np.all(
            np.isfinite(
                source_values
            )
        ):

            raise AssertionError(
                f"Non-finite {q} for "
                f"{material}/{origin}"
            )

        interpolated = np.interp(
            target_horizons,
            group["horizon"]
            .astype(float)
            .to_numpy(),
            source_values,
        )

        output[q] = np.maximum.accumulate(
            np.maximum(
                interpolated,
                0.0,
            )
        )

    return pd.DataFrame(
        output,
        index=target_horizons,
    )


# =============================================================================
# SIMULATE ONE CASE
# =============================================================================

def simulate_case(
    vf,
    comp,
    material,
    origin,
):
    """
    Simulate one material/origin case using nested common random numbers.

    One 25,000-draw master stream is generated.

    Prefixes:

        1,000
        2,500
        5,000
        10,000
        25,000

    are evaluated using exactly the same underlying draws.
    """

    seed = stable_seed(
        material,
        str(origin.date()),
    )

    rng_demand = np.random.default_rng(
        seed
    )

    rng_duration = np.random.default_rng(
        seed + 1
    )

    n_max = max(
        MC_SIZES
    )

    # -------------------------------------------------------------------------
    # Master nested random streams.
    # -------------------------------------------------------------------------

    u_demand = rng_demand.random(
        (
            n_max,
            12,
        )
    )

    u_duration = rng_duration.random(
        n_max
    )

    # -------------------------------------------------------------------------
    # Build monthly marginal demand quantiles.
    # -------------------------------------------------------------------------

    horizon_quantiles = (
        build_horizon_quantiles(
            vf,
            material,
            origin,
        )
    )

    # -------------------------------------------------------------------------
    # Future months.
    # -------------------------------------------------------------------------

    month_starts = (
        month_starts_after(
            origin,
            12,
        )
    )

    # -------------------------------------------------------------------------
    # Sample duration from the locked empirical paired sample.
    # -------------------------------------------------------------------------

    duration_indices = np.floor(
        u_duration
        * N_DURATION
    ).astype(int)

    duration_indices = np.minimum(
        duration_indices,
        N_DURATION - 1,
    )

    duration_values = (
        comp[
            "total_days"
        ]
        .to_numpy(
            dtype=float
        )
        [duration_indices]
    )

    # -------------------------------------------------------------------------
    # Sample future monthly demand.
    # -------------------------------------------------------------------------

    demand = np.zeros(
        (
            n_max,
            12,
        ),
        dtype=float,
    )

    for j in range(12):

        q_values = (
            horizon_quantiles
            .loc[
                j + 1,
                [
                    "q10",
                    "q25",
                    "q50",
                    "q75",
                    "q90",
                ],
            ]
            .to_numpy(
                dtype=float
            )
        )

        demand[:, j] = (
            inverse_piecewise(
                u_demand[:, j],
                q_values,
            )
        )

    # -------------------------------------------------------------------------
    # Demand exposure during procurement-process duration.
    # -------------------------------------------------------------------------

    exposure = np.zeros(
        n_max,
        dtype=float,
    )

    for j, month_start in enumerate(
        month_starts
    ):

        month_end = (
            month_start
            + pd.offsets.MonthBegin(1)
        )

        month_days = (
            month_end
            - month_start
        ).total_seconds() / 86400.0

        start = month_start

        weights = np.array(
            [
                exact_overlap_days(
                    start,
                    duration_values[k],
                    month_start,
                )
                / month_days
                for k in range(n_max)
            ],
            dtype=float,
        )

        weights = np.clip(
            weights,
            0.0,
            1.0,
        )

        exposure += (
            demand[:, j]
            * weights
        )

    # -------------------------------------------------------------------------
    # Verify supported propagation window.
    # -------------------------------------------------------------------------

    if np.any(
        duration_values > 365
    ):

        raise AssertionError(
            "A procurement-process duration exceeds "
            "the supported 12-month propagation window."
        )

    # -------------------------------------------------------------------------
    # Nested estimates.
    # -------------------------------------------------------------------------

    estimates = []

    for n in MC_SIZES:

        x = exposure[:n]

        estimates.append(
            {
                "material": material,
                "forecast_origin": (
                    origin.date().isoformat()
                ),
                "mc_n": n,
                "mean": float(
                    np.mean(x)
                ),
                "q50": float(
                    np.quantile(
                        x,
                        0.50,
                    )
                ),
                "q75": float(
                    np.quantile(
                        x,
                        0.75,
                    )
                ),
                "q90": float(
                    np.quantile(
                        x,
                        0.90,
                    )
                ),
                "q95": float(
                    np.quantile(
                        x,
                        0.95,
                    )
                ),
                "q99": float(
                    np.quantile(
                        x,
                        0.99,
                    )
                ),
                "min": float(
                    np.min(x)
                ),
                "max": float(
                    np.max(x)
                ),
                "seed": int(seed),
            }
        )

    # -------------------------------------------------------------------------
    # Explicit nested-prefix integrity.
    # -------------------------------------------------------------------------

    x10 = exposure[
        :10000
    ]

    x25 = exposure[
        :25000
    ]

    if not np.isclose(
        np.mean(x10),
        estimates[3]["mean"],
        rtol=0,
        atol=0,
    ):

        raise AssertionError(
            "Nested 10,000-prefix reproducibility failed."
        )

    if not np.isclose(
        np.mean(x25),
        estimates[4]["mean"],
        rtol=0,
        atol=0,
    ):

        raise AssertionError(
            "Nested 25,000-prefix reproducibility failed."
        )

    return estimates


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)

    print(
        "CMIDO RO2 STEP 27D.4 — "
        "NESTED COMMON-RANDOM-NUMBER CONVERGENCE"
    )

    print("=" * 80)

    # -------------------------------------------------------------------------
    # Load inputs.
    # -------------------------------------------------------------------------

    vf, comp = load_inputs()

    print(
        f"RO1 validation rows: {len(vf)}"
    )

    print(
        f"RO2 paired duration rows: {len(comp)}"
    )

    print(
        f"MC sizes: {MC_SIZES}"
    )

    print(
        f"Cases: {N_CASES}"
    )

    # -------------------------------------------------------------------------
    # Run all material/origin cases.
    # -------------------------------------------------------------------------

    all_estimates = []

    for material in MATERIALS:

        origins = sorted(
            vf.loc[
                vf["material"].eq(material),
                "forecast_origin",
            ].unique()
        )

        if len(origins) != 12:

            raise AssertionError(
                f"{material}: expected 12 origins, "
                f"found {len(origins)}"
            )

        print(
            f"\n[{material}] "
            f"complete origins: {len(origins)}"
        )

        for origin in origins:

            all_estimates.extend(
                simulate_case(
                    vf,
                    comp,
                    material,
                    pd.Timestamp(origin),
                )
            )

    estimates = pd.DataFrame(
        all_estimates
    )

    # -------------------------------------------------------------------------
    # Expected:
    #
    # 48 cases × 5 MC sizes = 240 rows
    # -------------------------------------------------------------------------

    expected_rows = (
        N_CASES
        * len(MC_SIZES)
    )

    if len(estimates) != expected_rows:

        raise AssertionError(
            f"Expected {expected_rows} "
            f"estimate rows; "
            f"found {len(estimates)}."
        )

    # -------------------------------------------------------------------------
    # Finite/non-negative checks.
    # -------------------------------------------------------------------------

    estimate_columns = [
        "mean",
        "q50",
        "q75",
        "q90",
        "q95",
        "q99",
    ]

    estimate_values = estimates[
        estimate_columns
    ].to_numpy()

    if not np.all(
        np.isfinite(
            estimate_values
        )
    ):

        raise AssertionError(
            "Non-finite Monte Carlo estimates found."
        )

    if (
        estimates[
            estimate_columns
        ]
        < 0
    ).any().any():

        raise AssertionError(
            "Negative exposure estimate found."
        )

    # -------------------------------------------------------------------------
    # Verify nested MC size structure.
    # -------------------------------------------------------------------------

    for (
        material,
        origin,
    ), group in estimates.groupby(
        [
            "material",
            "forecast_origin",
        ]
    ):

        observed_sizes = sorted(
            group["mc_n"]
            .tolist()
        )

        if observed_sizes != list(
            MC_SIZES
        ):

            raise AssertionError(
                f"Non-nested MC size set for "
                f"{material}/{origin}: "
                f"{observed_sizes}"
            )

    # =============================================================================
    # CONVERGENCE CHANGES
    # =============================================================================

    statistics = [
        "mean",
        "q90",
        "q95",
        "q99",
    ]

    changes = []

    for (
        material,
        origin,
    ), group in estimates.groupby(
        [
            "material",
            "forecast_origin",
        ],
        sort=True,
    ):

        group = group.set_index(
            "mc_n"
        )

        for stat in statistics:

            value_5000 = float(
                group.loc[
                    5000,
                    stat,
                ]
            )

            value_10000 = float(
                group.loc[
                    10000,
                    stat,
                ]
            )

            value_25000 = float(
                group.loc[
                    25000,
                    stat,
                ]
            )

            absolute_5_10 = abs(
                value_10000
                - value_5000
            )

            if abs(
                value_5000
            ) > 0:

                relative_5_10 = (
                    100
                    * absolute_5_10
                    / abs(value_5000)
                )

            else:

                relative_5_10 = np.nan

            absolute_10_25 = abs(
                value_25000
                - value_10000
            )

            if abs(
                value_10000
            ) > 0:

                relative_10_25 = (
                    100
                    * absolute_10_25
                    / abs(value_10000)
                )

            else:

                relative_10_25 = np.nan

            threshold = CRITERIA[
                stat
            ]

            pass_5_10 = bool(
                np.isfinite(
                    relative_5_10
                )
                and relative_5_10
                <= threshold
            )

            pass_10_25 = bool(
                np.isfinite(
                    relative_10_25
                )
                and relative_10_25
                <= threshold
            )

            changes.append(
                {
                    "material": material,
                    "forecast_origin": origin,
                    "statistic": stat,
                    "value_5000": value_5000,
                    "value_10000": value_10000,
                    "value_25000": value_25000,
                    "absolute_change_5k_to_10k": (
                        absolute_5_10
                    ),
                    "relative_change_5k_to_10k_pct": (
                        relative_5_10
                    ),
                    "threshold_pct": threshold,
                    "pass_5k_to_10k": (
                        pass_5_10
                    ),
                    "absolute_change_10k_to_25k": (
                        absolute_10_25
                    ),
                    "relative_change_10k_to_25k_pct": (
                        relative_10_25
                    ),
                    "pass_10k_to_25k": (
                        pass_10_25
                    ),
                }
            )

    changes = pd.DataFrame(
        changes
    )

    # =============================================================================
    # CASE-LEVEL DECISIONS
    # =============================================================================

    case_rows = []

    for (
        material,
        origin,
    ), group in changes.groupby(
        [
            "material",
            "forecast_origin",
        ],
        sort=True,
    ):

        stable_10k = bool(
            group[
                "pass_5k_to_10k"
            ].all()
        )

        stable_25k = bool(
            group[
                "pass_10k_to_25k"
            ].all()
        )

        failed_10k = (
            group.loc[
                ~group[
                    "pass_5k_to_10k"
                ],
                "statistic",
            ]
            .tolist()
        )

        failed_25k = (
            group.loc[
                ~group[
                    "pass_10k_to_25k"
                ],
                "statistic",
            ]
            .tolist()
        )

        case_rows.append(
            {
                "material": material,
                "forecast_origin": origin,
                "stable_at_10000": stable_10k,
                "failed_statistics_5k_to_10k": (
                    ",".join(
                        failed_10k
                    )
                ),
                "stable_at_25000_relative_to_10000": (
                    stable_25k
                ),
                "failed_statistics_10k_to_25k": (
                    ",".join(
                        failed_25k
                    )
                ),
            }
        )

    cases = pd.DataFrame(
        case_rows
    )

    n_stable_10k = int(
        cases[
            "stable_at_10000"
        ].sum()
    )

    n_stable_25k = int(
        cases[
            "stable_at_25000_relative_to_10000"
        ].sum()
    )

    # =============================================================================
    # GLOBAL DECISION
    # =============================================================================

    if n_stable_10k == N_CASES:

        decision = "LOCK_10000"
        recommended = 10000

    elif n_stable_25k == N_CASES:

        decision = "LOCK_25000"
        recommended = 25000

    else:

        decision = "HOLD_FOR_REVIEW"
        recommended = None

    # =============================================================================
    # MATERIAL SUMMARY
    # =============================================================================

    material_rows = []

    for material in MATERIALS:

        case_group = cases[
            cases["material"].eq(
                material
            )
        ]

        change_group = changes[
            changes["material"].eq(
                material
            )
        ]

        row = {
            "material": material,
            "n_cases": len(
                case_group
            ),
            "stable_at_10000_n": int(
                case_group[
                    "stable_at_10000"
                ].sum()
            ),
            "stable_at_10000_pct": (
                100
                * case_group[
                    "stable_at_10000"
                ].mean()
            ),
            "stable_at_25000_n": int(
                case_group[
                    "stable_at_25000_relative_to_10000"
                ].sum()
            ),
            "stable_at_25000_pct": (
                100
                * case_group[
                    "stable_at_25000_relative_to_10000"
                ].mean()
            ),
        }

        for stat in statistics:

            stat_group = change_group[
                change_group[
                    "statistic"
                ].eq(stat)
            ]

            row[
                f"{stat}_median_5k_to_10k_pct"
            ] = float(
                stat_group[
                    "relative_change_5k_to_10k_pct"
                ].median()
            )

            row[
                f"{stat}_max_5k_to_10k_pct"
            ] = float(
                stat_group[
                    "relative_change_5k_to_10k_pct"
                ].max()
            )

            row[
                f"{stat}_median_10k_to_25k_pct"
            ] = float(
                stat_group[
                    "relative_change_10k_to_25k_pct"
                ].median()
            )

            row[
                f"{stat}_max_10k_to_25k_pct"
            ] = float(
                stat_group[
                    "relative_change_10k_to_25k_pct"
                ].max()
            )

        material_rows.append(
            row
        )

    material_summary = pd.DataFrame(
        material_rows
    )

    # =============================================================================
    # STATISTIC SUMMARY
    # =============================================================================

    statistic_rows = []

    for stat in statistics:

        group = changes[
            changes[
                "statistic"
            ].eq(stat)
        ]

        statistic_rows.append(
            {
                "statistic": stat,
                "n_cases": len(group),
                "failed_5k_to_10k": int(
                    (
                        ~group[
                            "pass_5k_to_10k"
                        ]
                    ).sum()
                ),
                "failed_10k_to_25k": int(
                    (
                        ~group[
                            "pass_10k_to_25k"
                        ]
                    ).sum()
                ),
                "failure_rate_5k_to_10k_pct": (
                    100
                    * (
                        ~group[
                            "pass_5k_to_10k"
                        ]
                    ).mean()
                ),
                "failure_rate_10k_to_25k_pct": (
                    100
                    * (
                        ~group[
                            "pass_10k_to_25k"
                        ]
                    ).mean()
                ),
                "median_change_5k_to_10k_pct": (
                    float(
                        group[
                            "relative_change_5k_to_10k_pct"
                        ].median()
                    )
                ),
                "max_change_5k_to_10k_pct": (
                    float(
                        group[
                            "relative_change_5k_to_10k_pct"
                        ].max()
                    )
                ),
                "median_change_10k_to_25k_pct": (
                    float(
                        group[
                            "relative_change_10k_to_25k_pct"
                        ].median()
                    )
                ),
                "max_change_10k_to_25k_pct": (
                    float(
                        group[
                            "relative_change_10k_to_25k_pct"
                        ].max()
                    )
                ),
            }
        )

    statistic_summary = pd.DataFrame(
        statistic_rows
    )

    # =============================================================================
    # REPRODUCIBILITY HASH
    # =============================================================================

    hash_payload = (
        estimates
        .sort_values(
            [
                "material",
                "forecast_origin",
                "mc_n",
            ]
        )
        .to_csv(
            index=False
        )
        .encode("utf-8")
    )

    estimate_hash = hashlib.sha256(
        hash_payload
    ).hexdigest()

    # =============================================================================
    # PREVIOUS 27D.2 COMPARISON
    # =============================================================================

    previous_changes = (
        ROOT
        / "results"
        / "RO2"
        / "propagation_convergence"
        / "RO2_step27d2_convergence_changes.csv"
    )

    previous_max = None

    if previous_changes.exists():

        old = pd.read_csv(
            previous_changes
        )

        if (
            "relative_change_pct"
            in old.columns
        ):

            previous_max = float(
                old[
                    "relative_change_pct"
                ].max()
            )

        elif (
            "relative_change_5k_to_10k_pct"
            in old.columns
        ):

            previous_max = float(
                old[
                    "relative_change_5k_to_10k_pct"
                ].max()
            )

    # =============================================================================
    # SUMMARY
    # =============================================================================

    max_5k_10k = float(
        changes[
            "relative_change_5k_to_10k_pct"
        ].max()
    )

    max_10k_25k = float(
        changes[
            "relative_change_10k_to_25k_pct"
        ].max()
    )

    summary = {
        "step": "27D.4",
        "decision": decision,
        "recommended_mc_lock": recommended,
        "n_cases": N_CASES,
        "stable_at_10000_n": n_stable_10k,
        "stable_at_10000_pct": (
            100
            * n_stable_10k
            / N_CASES
        ),
        "stable_at_25000_n": n_stable_25k,
        "stable_at_25000_pct": (
            100
            * n_stable_25k
            / N_CASES
        ),
        "max_5k_to_10k_relative_change_pct": (
            max_5k_10k
        ),
        "max_10k_to_25k_relative_change_pct": (
            max_10k_25k
        ),
        "previous_27d2_max_relative_change_pct": (
            previous_max
        ),
        "master_seed": MASTER_SEED,
        "mc_sizes": MC_SIZES,
        "nested_prefix": True,
        "ro1_test_forecasts_used": False,
        "ro1_dataset_used": "RO1_DEMAND",
        "ro1_source_horizons": SOURCE_HORIZONS,
        "ro2_duration_rows": N_DURATION,
        "ro2_duration_source": (
            "RO2_step27b4_admissible_modelling_view.csv"
        ),
        "ro2_duration_selection": (
            "admissible_component == True"
        ),
        "estimate_table_sha256": estimate_hash,
        "note": (
            "Common-random-number nesting removes changing "
            "random-stream variation from sample-size comparisons; "
            "it does not itself prove statistical convergence."
        ),
    }

    # =============================================================================
    # SAVE OUTPUTS
    # =============================================================================

    estimates.to_csv(
        OUT_DIR
        / "RO2_step27d4_nested_estimates.csv",
        index=False,
    )

    changes.to_csv(
        OUT_DIR
        / "RO2_step27d4_nested_convergence_changes.csv",
        index=False,
    )

    cases.to_csv(
        OUT_DIR
        / "RO2_step27d4_case_decisions.csv",
        index=False,
    )

    material_summary.to_csv(
        OUT_DIR
        / "RO2_step27d4_material_summary.csv",
        index=False,
    )

    statistic_summary.to_csv(
        OUT_DIR
        / "RO2_step27d4_statistic_summary.csv",
        index=False,
    )

    (
        OUT_DIR
        / "RO2_step27d4_summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    # =============================================================================
    # DECISION FILE
    # =============================================================================

    decision_lines = [
        f"DECISION: {decision}",
        f"Recommended MC lock: {recommended}",
        "",
        f"Cases: {N_CASES}",
        (
            f"Stable at 10,000: "
            f"{n_stable_10k}/{N_CASES} "
            f"({100*n_stable_10k/N_CASES:.2f}%)"
        ),
        (
            f"Stable at 25,000: "
            f"{n_stable_25k}/{N_CASES} "
            f"({100*n_stable_25k/N_CASES:.2f}%)"
        ),
        "",
        "Convergence thresholds:",
        "- mean <= 1%",
        "- q90 <= 2%",
        "- q95 <= 2%",
        "- q99 <= 5%",
        "",
        "Primary comparison: 5,000 -> 10,000",
        "Secondary comparison: 10,000 -> 25,000",
        "",
        "Nested common-random-number sampling: PASS",
        "RO1 dataset used: RO1_DEMAND",
        "RO1 test forecasts used: NO",
        "RO2 paired duration n=37: PASS",
        "",
        (
            "Maximum 5k -> 10k relative change: "
            f"{max_5k_10k:.6f}%"
        ),
        (
            "Maximum 10k -> 25k relative change: "
            f"{max_10k_25k:.6f}%"
        ),
        "",
        "No change to frozen propagation methodology.",
    ]

    (
        OUT_DIR
        / "RO2_step27d4_decision.txt"
    ).write_text(
        "\n".join(
            decision_lines
        )
        + "\n",
        encoding="utf-8",
    )

    # =============================================================================
    # CONSOLE OUTPUT
    # =============================================================================

    print("\nCONVERGENCE RESULTS")

    print(
        f"Material/origin cases: "
        f"{N_CASES}"
    )

    print(
        f"Stable at 10,000: "
        f"{n_stable_10k}/{N_CASES} "
        f"({100*n_stable_10k/N_CASES:.2f}%)"
    )

    print(
        f"Stable at 25,000: "
        f"{n_stable_25k}/{N_CASES} "
        f"({100*n_stable_25k/N_CASES:.2f}%)"
    )

    print(
        "Max 5,000 -> 10,000 relative change:",
        f"{max_5k_10k:.6f}%",
    )

    print(
        "Max 10,000 -> 25,000 relative change:",
        f"{max_10k_25k:.6f}%",
    )

    if previous_max is not None:

        print(
            "Previous 27D.2 maximum relative change:",
            f"{previous_max:.6f}%",
        )

    print(
        "\nDECISION:",
        decision,
    )

    print(
        "Recommended MC lock:",
        recommended,
    )

    print("\nOutputs:")

    for path in sorted(
        OUT_DIR.iterdir()
    ):

        if path.is_file():

            print(
                " -",
                path,
            )

    print(
        "\n27D.4 nested convergence audit complete."
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()