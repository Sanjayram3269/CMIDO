from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCEN_DIR = ROOT / "results" / "RO3" / "scenario_generation"
OUT_DIR = ROOT / "results" / "RO3" / "scenario_convergence"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SIZES = [100, 250, 500, 1000, 2500, 5000]
MATERIALS = [
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
]
ORIGINS = [
    "2022-07-01", "2022-08-01", "2022-09-01", "2022-10-01",
    "2022-11-01", "2022-12-01", "2023-01-01", "2023-02-01",
    "2023-03-01", "2023-04-01", "2023-05-01",
]

REQUIRED = [
    "scenario_id", "forecast_origin", "material", "period", "month_ahead",
    "demand", "price", "internal_duration_days", "podn_duration_days",
    "total_duration_days", "scenario_set_size", "stream_id",
]

NUMERIC = [
    "scenario_id", "month_ahead", "demand", "price",
    "internal_duration_days", "podn_duration_days",
    "total_duration_days", "scenario_set_size",
]

EPS = 1e-12


def load_and_validate(n):
    path = SCEN_DIR / f"RO3_step32_scenarios_{n}.csv"

    if not path.exists():
        raise FileNotFoundError(f"Missing scenario file: {path}")

    print(f"[LOAD] {n:,} scenarios -> {path.name}", flush=True)

    df = pd.read_csv(path, usecols=REQUIRED)

    expected_rows = 11 * 4 * 12 * n
    if len(df) != expected_rows:
        raise ValueError(
            f"{path.name}: expected {expected_rows:,} rows, got {len(df):,}"
        )

    df["forecast_origin"] = (
        pd.to_datetime(df["forecast_origin"])
        .dt.strftime("%Y-%m-%d")
    )
    df["period"] = pd.to_datetime(df["period"])

    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if sorted(df["forecast_origin"].unique()) != sorted(ORIGINS):
        raise ValueError(f"{path.name}: frozen origin set changed")

    if sorted(df["material"].unique()) != sorted(MATERIALS):
        raise ValueError(f"{path.name}: frozen material set changed")

    if set(df["scenario_set_size"].unique()) != {n}:
        raise ValueError(f"{path.name}: scenario_set_size mismatch")

    if not np.isfinite(df[NUMERIC].to_numpy()).all():
        raise ValueError(f"{path.name}: non-finite numeric values")

    if not df["month_ahead"].between(1, 12).all():
        raise ValueError(f"{path.name}: month_ahead outside 1..12")

    duration_error = (
        df["internal_duration_days"]
        + df["podn_duration_days"]
        - df["total_duration_days"]
    ).abs().max()

    if duration_error > 1e-9:
        raise ValueError(
            f"{path.name}: duration reconstruction error {duration_error}"
        )

    counts = (
        df.groupby(["stream_id", "scenario_id"])["month_ahead"]
        .agg(["count", "nunique", "min", "max"])
    )

    valid_paths = (
        (counts["count"] == 12)
        & (counts["nunique"] == 12)
        & (counts["min"] == 1)
        & (counts["max"] == 12)
    )

    if not valid_paths.all():
        raise ValueError(f"{path.name}: invalid 12-month scenario path")

    print(f"[LOAD] {n:,}: validated {len(df):,} rows", flush=True)

    return df


def calculate_exposure(df):
    """
    Vectorized demand-during-procurement-duration exposure.

    For each scenario path:
      start = first forecast period
      end   = start + sampled total procurement duration

    Each monthly demand value is weighted by the exact number of calendar days
    in that month covered by the procurement window.
    """

    key = ["stream_id", "scenario_id"]

    first = (
        df[df["month_ahead"] == 1]
        [key + ["period", "total_duration_days"]]
        .rename(
            columns={
                "period": "start",
                "total_duration_days": "duration",
            }
        )
    )

    x = df.merge(
        first,
        on=key,
        how="left",
        validate="many_to_one",
    )

    x["end"] = x["start"] + pd.to_timedelta(x["duration"], unit="D")

    month_start = (
        x["period"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    month_end = (
        x["period"]
        .dt.to_period("M")
        .add(1)
        .dt.to_timestamp()
    )

    overlap_start = pd.concat(
        [x["start"], month_start],
        axis=1,
    ).max(axis=1)

    overlap_end = pd.concat(
        [x["end"], month_end],
        axis=1,
    ).min(axis=1)

    covered_days = (
        (overlap_end - overlap_start)
        .dt.total_seconds()
        .div(86400.0)
        .clip(lower=0.0)
    )

    month_days = (
        (month_end - month_start)
        .dt.total_seconds()
        .div(86400.0)
    )

    x["weighted_demand"] = (
        x["demand"] * covered_days / month_days
    )

    exposure = (
        x.groupby(key, sort=False)["weighted_demand"]
        .sum()
        .reset_index(name="exposure")
    )

    metadata = (
        x[key + ["material", "forecast_origin"]]
        .drop_duplicates(key)
    )

    exposure = exposure.merge(
        metadata,
        on=key,
        how="left",
        validate="one_to_one",
    )

    return exposure


def calculate_metrics(df):
    rows = []

    grouped = df.groupby(
        ["material", "forecast_origin"],
        sort=True,
    )

    direct_specs = [
        ("mean_demand", "demand", "mean"),
        ("q90_demand", "demand", "q90"),
        ("mean_price", "price", "mean"),
        ("q90_price", "price", "q90"),
        ("mean_internal_duration", "internal_duration_days", "mean"),
        ("q90_internal_duration", "internal_duration_days", "q90"),
        ("mean_podn_duration", "podn_duration_days", "mean"),
        ("q90_podn_duration", "podn_duration_days", "q90"),
        ("mean_total_duration", "total_duration_days", "mean"),
        ("q90_total_duration", "total_duration_days", "q90"),
    ]

    for (material, origin), group in grouped:
        for label, column, statistic in direct_specs:
            if statistic == "mean":
                value = group[column].mean()
            else:
                value = group[column].quantile(0.90)

            rows.append([
                material,
                origin,
                label,
                float(value),
            ])

    exposure = calculate_exposure(df)

    exposure_groups = exposure.groupby(
        ["material", "forecast_origin"],
        sort=True,
    )["exposure"]

    for (material, origin), values in exposure_groups:
        rows.extend([
            [material, origin, "mean_exposure", float(values.mean())],
            [material, origin, "q90_exposure", float(values.quantile(0.90))],
            [material, origin, "q95_exposure", float(values.quantile(0.95))],
            [material, origin, "q99_exposure", float(values.quantile(0.99))],
        ])

    return pd.DataFrame(
        rows,
        columns=[
            "material",
            "forecast_origin",
            "metric",
            "value",
        ],
    )


def check_nestedness(data):
    comparison_columns = [
        "scenario_id",
        "month_ahead",
        "demand",
        "price",
        "internal_duration_days",
        "podn_duration_days",
        "total_duration_days",
    ]

    print("[AUDIT] Checking nested scenario prefixes...", flush=True)

    for small_n, large_n in zip(SIZES[:-1], SIZES[1:]):
        small = data[small_n]
        large = data[large_n]

        for stream_id in sorted(small["stream_id"].unique()):
            small_stream = (
                small[small["stream_id"] == stream_id]
                .sort_values(["scenario_id", "month_ahead"])
                [comparison_columns]
                .reset_index(drop=True)
            )

            large_stream = (
                large[large["stream_id"] == stream_id]
                .sort_values(["scenario_id", "month_ahead"])
                [comparison_columns]
                .reset_index(drop=True)
            )

            expected_rows = 12 * small_n

            if len(small_stream) != expected_rows:
                raise ValueError(
                    f"Nestedness: unexpected small stream size for {stream_id}"
                )

            prefix = large_stream.iloc[:expected_rows].reset_index(drop=True)

            if not small_stream.equals(prefix):
                raise ValueError(
                    f"Nestedness failure {small_n}->{large_n}, stream={stream_id}"
                )

    print("[AUDIT] Nestedness PASS", flush=True)


def criterion(metric, value_a, value_b):
    """
    Return:
      change, threshold, criterion_type, pass
    """

    if "duration" in metric:
        threshold = 1.0 if metric.startswith("mean_") else 2.0
        change = abs(value_b - value_a)

        return (
            change,
            threshold,
            "absolute_days",
            change <= threshold,
        )

    if metric.startswith("mean_"):
        threshold = 0.01
    elif metric.startswith("q90_"):
        threshold = 0.02
    elif metric == "q95_exposure":
        threshold = 0.02
    else:
        threshold = 0.05

    change = (
        abs(value_b - value_a)
        / max(abs(value_a), EPS)
    )

    return (
        change,
        threshold,
        "relative",
        change <= threshold,
    )


def main():
    data = {}

    for n in SIZES:
        data[n] = load_and_validate(n)

    check_nestedness(data)

    metric_frames = []

    for n in SIZES:
        print(
            f"[METRICS] Calculating {n:,}-scenario metrics...",
            flush=True,
        )

        frame = calculate_metrics(data[n])
        frame["n_scenarios"] = n
        metric_frames.append(frame)

        print(
            f"[METRICS] {n:,} complete",
            flush=True,
        )

    metrics = pd.concat(
        metric_frames,
        ignore_index=True,
    )

    comparisons = []

    for small_n, large_n in zip(SIZES[:-1], SIZES[1:]):
        small = (
            metrics[metrics["n_scenarios"] == small_n]
            .set_index(
                ["material", "forecast_origin", "metric"]
            )["value"]
        )

        large = (
            metrics[metrics["n_scenarios"] == large_n]
            .set_index(
                ["material", "forecast_origin", "metric"]
            )["value"]
        )

        for index in small.index:
            value_a = float(small.loc[index])
            value_b = float(large.loc[index])

            change, threshold, criterion_type, passed = criterion(
                index[2],
                value_a,
                value_b,
            )

            comparisons.append([
                index[0],
                index[1],
                index[2],
                small_n,
                large_n,
                value_a,
                value_b,
                change,
                threshold,
                criterion_type,
                bool(passed),
            ])

    comparison_df = pd.DataFrame(
        comparisons,
        columns=[
            "material",
            "forecast_origin",
            "metric",
            "n_from",
            "n_to",
            "value_from",
            "value_to",
            "change",
            "threshold",
            "criterion",
            "pass",
        ],
    )

    primary = comparison_df[
        (comparison_df["n_from"] == 500)
        & (comparison_df["n_to"] == 1000)
    ]

    later = comparison_df[
        comparison_df["n_from"] >= 1000
    ]

    primary_pass = bool(primary["pass"].all())

    if primary_pass:
        decision = "RO3_3A_LOCK_1000"
    else:
        decision = "RO3_3A_EVALUATE_2500"

    summary = {
        "scenario_sizes": SIZES,
        "material_origin_cases": 44,
        "primary_transition": "500_to_1000",
        "primary_pass": primary_pass,
        "primary_failed_comparisons": int(
            (~primary["pass"]).sum()
        ),
        "primary_max_change": float(
            primary["change"].max()
        ),
        "later_max_change": float(
            later["change"].max()
        ),
        "decision": decision,
        "optimizer_level_convergence_required_later": True,
    }

    metrics_path = (
        OUT_DIR / "RO3_step33A_convergence_metrics.csv"
    )
    comparison_path = (
        OUT_DIR / "RO3_step33A_convergence_comparisons.csv"
    )
    summary_path = (
        OUT_DIR / "RO3_step33A_summary.json"
    )
    decision_path = (
        OUT_DIR / "RO3_step33A_decision.txt"
    )

    metrics.to_csv(metrics_path, index=False)
    comparison_df.to_csv(comparison_path, index=False)

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    decision_path.write_text(
        decision + "\n",
        encoding="utf-8",
    )

    print("=" * 78)
    print("CMIDO RO3.3A — DOMAIN-AWARE SCENARIO CONVERGENCE")
    print("=" * 78)
    print("Scenario sizes:", SIZES)
    print("Material-origin cases: 44")
    print(
        "Primary 500 -> 1000:",
        "PASS" if primary_pass else "FAIL",
    )
    print(
        "Primary failed comparisons:",
        int((~primary["pass"]).sum()),
    )
    print(
        f"Primary max change: {primary['change'].max():.6f}"
    )
    print(
        f"Later max change: {later['change'].max():.6f}"
    )
    print("DECISION:", decision)

    print("\nOutputs:")
    print(metrics_path)
    print(comparison_path)
    print(summary_path)
    print(decision_path)


if __name__ == "__main__":
    main()
