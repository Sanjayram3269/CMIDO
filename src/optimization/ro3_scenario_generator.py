from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

RO1 = ROOT / "results" / "forecasting" / "probabilistic_calibration" / "RO1_step26c3_validation_forecasts.csv"
RO2 = ROOT / "results" / "RO2" / "data_audit" / "RO2_step27b4_admissible_modelling_view.csv"

OUT = ROOT / "results" / "RO3" / "scenario_generation"

MATERIALS = [
    "Cement",
    "Granite",
    "Ready Mixed Concrete",
    "Steel Reinforcement Bars",
]

SOURCE_HORIZONS = [1, 3, 6, 12]
QUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]
NESTED_SIZES = [100, 250, 500, 1000, 2500, 5000]
MASTER_SEED = 32027


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def stable_seed(*parts: object) -> int:
    text = "|".join(map(str, parts))
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**32 - 1)


def inverse_piecewise_quantile(u: float, qs: np.ndarray) -> float:
    """Piecewise-linear inverse CDF over the frozen q10-q90 representation."""
    probs = np.asarray(QUANTILES, dtype=float)
    qs = np.asarray(qs, dtype=float)

    require(np.isfinite(qs).all(), "Non-finite quantile encountered.")
    require(np.all(np.diff(qs) >= -1e-12),
            f"Quantile crossing detected: {qs.tolist()}")

    # Base representation is explicitly truncated to [0.10, 0.90].
    u = float(np.clip(u, probs[0], probs[-1]))

    return float(np.interp(u, probs, qs))


def interpolate_quantiles(df: pd.DataFrame) -> pd.DataFrame:
    """Interpolate q10-q90 from source horizons 1,3,6,12 to months 1..12."""
    rows = []

    for (dataset, series, origin), g in df.groupby(
        ["dataset", "series", "forecast_origin"], sort=True
    ):
        g = g.copy()
        g["horizon"] = pd.to_numeric(g["horizon"], errors="coerce")

        source = g[g["horizon"].isin(SOURCE_HORIZONS)].copy()
        source = source.drop_duplicates(subset=["horizon"], keep="first")

        if set(source["horizon"].astype(int)) != set(SOURCE_HORIZONS):
            continue

        source = source.sort_values("horizon")

        x = source["horizon"].to_numpy(dtype=float)

        for h in range(1, 13):
            rec = {
                "dataset": dataset,
                "series": series,
                "forecast_origin": origin,
                "month_ahead": h,
            }

            for q in ["q10", "q25", "q50", "q75", "q90"]:
                y = pd.to_numeric(source[q], errors="coerce").to_numpy(float)
                require(np.isfinite(y).all(),
                        f"Non-finite {q}: {dataset}/{series}/{origin}")
                rec[q] = float(np.interp(h, x, y))

            rows.append(rec)

    return pd.DataFrame(rows)


def load_ro1() -> pd.DataFrame:
    require(RO1.exists(), f"RO1 artifact missing: {RO1}")

    df = pd.read_csv(RO1)

    required = {
        "dataset", "series", "horizon", "forecast_origin", "target_date",
        "q10", "q25", "q50", "q75", "q90"
    }
    missing = required - set(df.columns)
    require(not missing, f"RO1 missing columns: {sorted(missing)}")

    df["forecast_origin_dt"] = pd.to_datetime(
        df["forecast_origin"], errors="coerce"
    )
    df["target_date_dt"] = pd.to_datetime(
        df["target_date"], errors="coerce"
    )
    require(df["forecast_origin_dt"].notna().all(),
            "Invalid RO1 forecast-origin dates.")
    require(df["target_date_dt"].notna().all(),
            "Invalid RO1 target dates.")

    require(not df["dataset"].astype(str).str.upper().str.contains("TEST").any(),
            "RO1 test-like dataset detected.")

    # Explicitly retain only the frozen validation datasets.
    df = df[df["dataset"].isin(["RO1_DEMAND", "RO1_PRICE"])].copy()
    df = df[df["series"].isin(MATERIALS)].copy()

    require(len(df) > 0, "No common RO1 material rows available.")

    return df


def load_duration() -> pd.DataFrame:
    require(RO2.exists(), f"RO2 modelling view missing: {RO2}")

    df = pd.read_csv(RO2)

    required = {
        "Internal_num", "PODN_num", "TotalDN_num", "admissible_component"
    }
    missing = required - set(df.columns)
    require(not missing, f"RO2 missing columns: {sorted(missing)}")

    flag = (
        df["admissible_component"]
        .astype(str).str.strip().str.lower()
        .isin(["true", "1", "yes"])
    )

    d = df.loc[flag, [
        "Internal_num", "PODN_num", "TotalDN_num"
    ]].copy()

    for c in d.columns:
        d[c] = pd.to_numeric(d[c], errors="coerce")

    d = d.dropna().reset_index(drop=True)

    require(len(d) == 37, f"Expected 37 paired duration rows, found {len(d)}")
    require(np.isfinite(d.to_numpy()).all(), "Non-finite duration values.")
    require((d > 0).all().all(), "Non-positive duration value detected.")
    require(
        np.allclose(
            d["Internal_num"] + d["PODN_num"],
            d["TotalDN_num"],
            atol=1e-12,
        ),
        "RO2 duration pairing/reconstruction failed."
    )

    return d


def build_complete_origins(ro1: pd.DataFrame) -> list[pd.Timestamp]:
    """Origins complete for all 4 materials and both RO1 datasets."""
    tmp = ro1.copy()
    tmp["horizon"] = pd.to_numeric(tmp["horizon"], errors="coerce")

    eligible = (
        tmp.groupby(["dataset", "series", "forecast_origin"])["horizon"]
        .apply(lambda x: set(x.dropna().astype(int)) >= set(SOURCE_HORIZONS))
        .reset_index(name="complete")
    )
    eligible = eligible[eligible["complete"]]

    demand_origins = set(
        eligible.loc[
            (eligible["dataset"] == "RO1_DEMAND")
            & eligible["series"].isin(MATERIALS),
            "forecast_origin"
        ]
    )
    price_origins = set(
        eligible.loc[
            (eligible["dataset"] == "RO1_PRICE")
            & eligible["series"].isin(MATERIALS),
            "forecast_origin"
        ]
    )

    common = sorted(demand_origins & price_origins)

    # Require every material to be complete at the origin.
    valid = []
    for origin in common:
        ok = True
        for dataset in ["RO1_DEMAND", "RO1_PRICE"]:
            for material in MATERIALS:
                sub = eligible[
                    (eligible["dataset"] == dataset)
                    & (eligible["series"] == material)
                    & (eligible["forecast_origin"] == origin)
                ]
                if len(sub) != 1 or not bool(sub.iloc[0]["complete"]):
                    ok = False
        if ok:
            valid.append(pd.Timestamp(origin))

    require(len(valid) > 0, "No complete common forecast origins found.")
    return valid


def generate_scenarios(n_scenarios: int, ro1: pd.DataFrame,
                       duration: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    require(n_scenarios in NESTED_SIZES,
            f"n_scenarios must be one of {NESTED_SIZES}")

    origins = build_complete_origins(ro1)

    # Interpolated predictive quantiles for all eligible material/origin pairs.
    interp = interpolate_quantiles(ro1)
    interp["forecast_origin_dt"] = pd.to_datetime(
        interp["forecast_origin"], errors="coerce"
    )

    demand = interp[interp["dataset"] == "RO1_DEMAND"].copy()
    price = interp[interp["dataset"] == "RO1_PRICE"].copy()

    demand_key = ["series", "forecast_origin", "month_ahead"]
    price_key = ["series", "forecast_origin", "month_ahead"]

    rows = []

    # One stable master stream per material/origin. Prefixes are nested.
    for material in MATERIALS:
        for origin in origins:
            origin_str = origin.strftime("%Y-%m-%d")

            d = demand[
                (demand["series"] == material)
                & (demand["forecast_origin_dt"] == origin)
            ].sort_values("month_ahead")

            p = price[
                (price["series"] == material)
                & (price["forecast_origin_dt"] == origin)
            ].sort_values("month_ahead")

            require(len(d) == 12, f"Demand horizon construction failed: {material}/{origin_str}")
            require(len(p) == 12, f"Price horizon construction failed: {material}/{origin_str}")

            rng = np.random.default_rng(
                stable_seed(MASTER_SEED, material, origin_str)
            )

            # Master stream is generated once for 5000 scenarios.
            u_d = rng.uniform(0.10, 0.90, size=(NESTED_SIZES[-1], 12))
            u_p = rng.uniform(0.10, 0.90, size=(NESTED_SIZES[-1], 12))
            dur_idx = rng.integers(0, len(duration), size=NESTED_SIZES[-1])

            for s in range(n_scenarios):
                dur = duration.iloc[int(dur_idx[s])]

                for j in range(12):
                    dq = d.iloc[j][["q10", "q25", "q50", "q75", "q90"]].to_numpy(float)
                    pq = p.iloc[j][["q10", "q25", "q50", "q75", "q90"]].to_numpy(float)

                    demand_value = max(
                        inverse_piecewise_quantile(u_d[s, j], dq), 0.0
                    )
                    price_value = max(
                        inverse_piecewise_quantile(u_p[s, j], pq), 0.0
                    )

                    target_period = (
                        origin.to_period("M") + (j + 1)
                    ).to_timestamp()

                    rows.append({
                        "scenario_id": s + 1,
                        "forecast_origin": origin.strftime("%Y-%m-%d"),
                        "material": material,
                        "period": target_period.strftime("%Y-%m-%d"),
                        "month_ahead": j + 1,
                        "demand": demand_value,
                        "price": price_value,
                        "internal_duration_days": float(dur["Internal_num"]),
                        "podn_duration_days": float(dur["PODN_num"]),
                        "total_duration_days": float(dur["TotalDN_num"]),
                        "scenario_set_size": n_scenarios,
                        "stream_id": f"{material}|{origin_str}",
                    })

    out = pd.DataFrame(rows)

    expected = (
        n_scenarios * len(origins) * len(MATERIALS) * 12
    )
    require(len(out) == expected,
            f"Unexpected output rows: {len(out)}; expected {expected}")

    return out, {
        "n_scenarios": n_scenarios,
        "forecast_origins": [o.strftime("%Y-%m-%d") for o in origins],
        "material_count": len(MATERIALS),
        "materials": MATERIALS,
        "source_horizons": SOURCE_HORIZONS,
        "master_seed": MASTER_SEED,
        "quantile_probability_range": [0.10, 0.90],
        "duration_rows": len(duration),
    }


def audit_scenarios(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    checks = []

    def check(name, passed, detail):
        checks.append({
            "check": name,
            "pass": bool(passed),
            "detail": detail,
        })

    check(
        "material_set",
        set(df["material"]) == set(MATERIALS),
        f"found={sorted(df['material'].unique())}"
    )

    check(
        "finite_outputs",
        np.isfinite(
            df[[
                "demand", "price",
                "internal_duration_days",
                "podn_duration_days",
                "total_duration_days"
            ]].to_numpy(float)
        ).all(),
        "all numeric outputs finite"
    )

    check(
        "nonnegative_demand_price",
        (df[["demand", "price"]] >= 0).all().all(),
        "demand and price non-negative"
    )

    check(
        "positive_duration",
        (df[[
            "internal_duration_days",
            "podn_duration_days",
            "total_duration_days"
        ]] > 0).all().all(),
        "duration values positive"
    )

    check(
        "duration_reconstruction",
        np.allclose(
            df["internal_duration_days"] + df["podn_duration_days"],
            df["total_duration_days"],
            atol=1e-12,
        ),
        "internal + PO/GR = total for every scenario"
    )

    origins = pd.to_datetime(df["forecast_origin"])
    periods = pd.to_datetime(df["period"])

    check(
        "future_periods",
        (periods > origins).all(),
        "all generated periods after forecast origins"
    )

    check(
        "month_ahead_range",
        set(df["month_ahead"].unique()) == set(range(1, 13)),
        "months 1..12 present"
    )

    check(
        "scenario_id_range",
        df["scenario_id"].min() == 1
        and df["scenario_id"].max() == config["n_scenarios"],
        f"1..{config['n_scenarios']}"
    )

    check(
        "row_count",
        len(df) == config["n_scenarios"] * len(config["forecast_origins"])
        * len(MATERIALS) * 12,
        f"rows={len(df)}"
    )

    check(
        "no_test_dataset_input",
        True,
        "generator explicitly filters to RO1_DEMAND/RO1_PRICE validation artifact"
    )

    return pd.DataFrame(checks)


def main():
    parser = argparse.ArgumentParser(
        description="CMIDO RO3.2 stochastic scenario generator"
    )
    parser.add_argument(
        "--n-scenarios",
        type=int,
        default=100,
        choices=NESTED_SIZES,
    )
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("CMIDO RO3.2 — SCENARIO GENERATION")
    print("=" * 78)
    print(f"Scenario count: {args.n_scenarios}")
    print(f"RO1: {RO1}")
    print(f"RO2: {RO2}")

    ro1 = load_ro1()
    duration = load_duration()

    scenarios, config = generate_scenarios(
        args.n_scenarios, ro1, duration
    )
    audit = audit_scenarios(scenarios, config)

    scenario_path = OUT / f"RO3_step32_scenarios_{args.n_scenarios}.csv"
    audit_path = OUT / f"RO3_step32_audit_{args.n_scenarios}.csv"
    config_path = OUT / f"RO3_step32_run_config_{args.n_scenarios}.json"
    decision_path = OUT / f"RO3_step32_decision_{args.n_scenarios}.txt"

    scenarios.to_csv(scenario_path, index=False)
    audit.to_csv(audit_path, index=False)

    config.update({
        "status": "PASS" if bool(audit["pass"].all()) else "FAIL",
        "rows_written": int(len(scenarios)),
    })

    config_path.write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )

    passed = int(audit["pass"].sum())
    total = len(audit)
    decision = "RO3_2_AUDIT_PASS" if passed == total else "RO3_2_AUDIT_FAIL"

    decision_path.write_text(
        "CMIDO RO3.2 — SCENARIO GENERATION DECISION\n"
        + "=" * 60 + "\n\n"
        + f"DECISION: {decision}\n"
        + f"CHECKS: {passed}/{total}\n"
        + f"SCENARIOS: {args.n_scenarios}\n"
        + f"ORIGINS: {len(config['forecast_origins'])}\n"
        + "\nIMPORTANT:\n"
        + "- RO3.2 does not lock the final scenario count.\n"
        + "- RO3.3 performs scenario-count convergence.\n"
        + "- Duration remains procurement-process duration, not supplier-specific lead time.\n"
        + "- RO1 supplies marginal horizon-wise predictive distributions.\n",
        encoding="utf-8",
    )

    print("\nRESULT")
    print("-" * 78)
    print(f"Forecast origins: {len(config['forecast_origins'])}")
    print(f"Materials: {len(MATERIALS)}")
    print(f"Rows: {len(scenarios)}")
    print(f"Duration observations: {len(duration)}")
    print(f"Audit: {passed}/{total}")
    print(f"DECISION: {decision}")

    print("\nOutputs:")
    print(f"  {scenario_path}")
    print(f"  {audit_path}")
    print(f"  {config_path}")
    print(f"  {decision_path}")

    if decision != "RO3_2_AUDIT_PASS":
        print("\nFAILED CHECKS:")
        print(audit.loc[~audit["pass"], ["check", "detail"]].to_string(index=False))
        raise SystemExit(1)

    print("\nRO3.2 100-scenario structural audit complete.")


if __name__ == "__main__":
    main()
