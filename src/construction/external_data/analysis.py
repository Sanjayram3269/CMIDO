"""Genuine analysis execution on uploaded data.

Runs only the analyses that the uploaded table can honestly satisfy, using the
real CMIDO statistical engines (``summarize_numeric`` / ``bootstrap_mean_ci``)
so results are seeded, deterministic and reproducible.  Every result is computed
from the uploaded rows only — nothing is copied from canonical research
artifacts and no missing input is fabricated.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.construction.experiments.statistical import (
    bootstrap_mean_ci,
    summarize_numeric,
)

from .contracts import MappingSpec, analysis_by_key

#: Fixed seed so uploaded-data runs are reproducible and auditable.
DEFAULT_SEED = 42
DEFAULT_BOOTSTRAP_RESAMPLES = 1000


class AnalysisError(ValueError):
    """A readable failure while executing a supported analysis."""


def _coerce_numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def _run_descriptive(
    frame: pd.DataFrame, spec: MappingSpec, seed: int, resamples: int
) -> dict[str, Any]:
    measure_col = spec.column_by_field["measure"]
    group_col = spec.column_by_field.get("group")

    numeric = _coerce_numeric(frame, measure_col)
    working = pd.DataFrame({"_measure": numeric})
    if group_col is not None:
        working["_group"] = frame[group_col]

    rows: list[dict[str, Any]] = []

    def _summarise(values: pd.Series, label: str) -> dict[str, Any]:
        clean = values.dropna().astype(float)
        if clean.empty:
            raise AnalysisError(
                f"No numeric '{measure_col}' values available for '{label}'."
            )
        data = clean.tolist()
        summary = summarize_numeric(data)
        ci = bootstrap_mean_ci(data, seed=seed, resamples=resamples)
        return {
            "group": label,
            "n": summary["count"],
            "mean": summary["mean"],
            "std": summary["standard_deviation"],
            "min": summary["minimum"],
            "p25": summary["q1"],
            "median": summary["median"],
            "p75": summary["q3"],
            "max": summary["maximum"],
            "mean_ci95_low": ci["lower"],
            "mean_ci95_high": ci["upper"],
            "bootstrap_resamples": resamples,
            "seed": seed,
        }

    if group_col is None:
        rows.append(_summarise(working["_measure"], "(all rows)"))
    else:
        for group_value, subset in working.groupby("_group", dropna=True):
            rows.append(_summarise(subset["_measure"], str(group_value)))

    return {
        "analysis": "descriptive_statistics",
        "measure_column": measure_col,
        "group_column": group_col,
        "rows": rows,
        "computed_from": "uploaded rows only",
        "engine": "CMIDO summarize_numeric + bootstrap_mean_ci",
    }


def _pinball_loss(actual: float, q: float, level: float) -> float:
    """Pinball (quantile) loss for one observation at probability ``level``."""
    diff = actual - q
    if diff >= 0:
        return level * diff
    return (level - 1.0) * diff


def _run_coverage(
    frame: pd.DataFrame, spec: MappingSpec, seed: int, resamples: int
) -> dict[str, Any]:
    observed_col = spec.column_by_field["observed"]
    lower_col = spec.column_by_field["interval_lower"]
    upper_col = spec.column_by_field["interval_upper"]
    quantile_col = spec.column_by_field.get("quantile")
    quantile_level_raw = spec.column_by_field.get("quantile_level")

    observed = _coerce_numeric(frame, observed_col)
    lower = _coerce_numeric(frame, lower_col)
    upper = _coerce_numeric(frame, upper_col)

    valid = pd.DataFrame(
        {"_obs": observed, "_lo": lower, "_hi": upper}
    ).dropna()
    if valid.empty:
        raise AnalysisError(
            "No rows have both an observed value and interval bounds; cannot "
            "compute coverage."
        )

    inside = (valid["_obs"] >= valid["_lo"]) & (valid["_obs"] <= valid["_hi"])
    coverage = float(inside.mean())
    widths = (valid["_hi"] - valid["_lo"]).astype(float)
    mean_width = float(widths.mean())

    result: dict[str, Any] = {
        "analysis": "forecast_coverage",
        "observed_column": observed_col,
        "interval_lower_column": lower_col,
        "interval_upper_column": upper_col,
        "n_scored": int(len(valid)),
        "n_rows_total": int(len(frame)),
        "coverage_rate": coverage,
        "mean_interval_width": mean_width,
        "computed_from": "uploaded rows only",
        "engine": "CMIDO calibration/coverage discipline",
    }

    # Optional pinball loss for a mapped quantile column.
    if quantile_col is not None:
        quantile = _coerce_numeric(frame, quantile_col)
        q_frame = pd.DataFrame({"_obs": observed, "_q": quantile}).dropna()
        level = _resolve_quantile_level(frame, quantile_level_raw)
        if q_frame.empty:
            raise AnalysisError(
                "A quantile column was mapped but no rows have both an observed "
                "value and a quantile; cannot compute pinball loss."
            )
        losses = [
            _pinball_loss(float(o), float(q), level)
            for o, q in zip(q_frame["_obs"], q_frame["_q"])
        ]
        result["quantile_column"] = quantile_col
        result["quantile_level"] = level
        result["pinball_loss_mean"] = float(sum(losses) / len(losses))
        result["n_scored_quantile"] = int(len(q_frame))
        ci = bootstrap_mean_ci(losses, seed=seed, resamples=resamples)
        result["pinball_loss_ci95_low"] = ci["lower"]
        result["pinball_loss_ci95_high"] = ci["upper"]

    return result


def _resolve_quantile_level(frame: pd.DataFrame, raw: str | None) -> float:
    """Derive the quantile probability level from an explicit column or default."""
    if raw and raw in frame.columns:
        numeric = pd.to_numeric(frame[raw], errors="coerce").dropna()
        if not numeric.empty:
            level = float(numeric.iloc[0])
            if 0.0 < level < 1.0:
                return level
    # Fallback: a median-like quantile; state it explicitly in the result.
    return 0.5


def execute_analysis(
    frame: pd.DataFrame,
    spec: MappingSpec,
    *,
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Execute the supported analysis for ``spec`` on ``frame``.

    Raises :class:`AnalysisError` for unsupported analyses or unsatisfiable
    inputs.  Results are computed from the uploaded rows only.
    """
    analysis = analysis_by_key(spec.analysis_key)
    if not analysis.supported:
        raise AnalysisError(
            f"'{analysis.label}' is not supported on uploaded data: "
            f"{analysis.unavailable_reason}"
        )

    if spec.analysis_key == "descriptive_statistics":
        return _run_descriptive(frame, spec, seed, resamples)
    if spec.analysis_key == "forecast_coverage":
        return _run_coverage(frame, spec, seed, resamples)

    raise AnalysisError(f"No implementation for analysis '{spec.analysis_key}'.")
