from __future__ import annotations

from math import ceil, floor, fsum, sqrt
from typing import Any

from .reproducibility import stable_hash


STATISTICAL_ANALYSIS_SCHEMA_VERSION = "8K-1.0"


def _validate_numeric(values: list[float | int], name: str = "values") -> list[float]:
    if not isinstance(values, list):
        raise ValueError(f"{name} must be a list")
    normalized: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must contain only numeric values")
        normalized.append(float(value))
    return normalized


def _quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("cannot compute quantile of an empty sample")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("quantile probability must be between 0 and 1")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = floor(position)
    upper = ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def summarize_numeric(values: list[float | int]) -> dict[str, Any]:
    """Return transparent descriptive statistics for one numeric sample."""
    data = _validate_numeric(values)
    if not data:
        raise ValueError("values must not be empty")

    ordered = sorted(data)
    count = len(data)
    mean = fsum(data) / count
    variance = (
        fsum((value - mean) ** 2 for value in data) / (count - 1)
        if count > 1
        else 0.0
    )

    return {
        "count": count,
        "mean": mean,
        "median": _quantile(ordered, 0.5),
        "standard_deviation": sqrt(variance),
        "minimum": ordered[0],
        "q1": _quantile(ordered, 0.25),
        "q3": _quantile(ordered, 0.75),
        "maximum": ordered[-1],
    }


def _deterministic_bootstrap_sample(values: list[float], seed: int, sample_index: int) -> list[float]:
    """Generate one reproducible bootstrap sample without external dependencies."""
    state = (seed + 0x9E3779B9 * (sample_index + 1)) & 0xFFFFFFFF
    sample: list[float] = []
    for _ in values:
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= state >> 17
        state ^= (state << 5) & 0xFFFFFFFF
        state &= 0xFFFFFFFF
        sample.append(values[state % len(values)])
    return sample


def bootstrap_mean_ci(
    values: list[float | int],
    seed: int = 42,
    resamples: int = 2000,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Compute a deterministic percentile bootstrap CI for the sample mean."""
    data = _validate_numeric(values)
    if not data:
        raise ValueError("values must not be empty")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not isinstance(resamples, int) or isinstance(resamples, bool) or resamples < 100:
        raise ValueError("resamples must be an integer >= 100")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    means = []
    for index in range(resamples):
        sample = _deterministic_bootstrap_sample(data, seed, index)
        means.append(fsum(sample) / len(sample))

    means.sort()
    alpha = (1.0 - confidence) / 2.0
    return {
        "method": "deterministic_percentile_bootstrap_mean",
        "seed": seed,
        "resamples": resamples,
        "confidence": confidence,
        "lower": _quantile(means, alpha),
        "upper": _quantile(means, 1.0 - alpha),
    }


def _validate_results(results: list[dict[str, Any]]) -> None:
    if not isinstance(results, list):
        raise ValueError("results must be a list")
    if not results:
        raise ValueError("results must not be empty")
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("each result must be a dictionary")
        scenario = result.get("scenario")
        metrics = result.get("metrics")
        if not isinstance(scenario, dict) or not isinstance(metrics, dict):
            raise ValueError("each result must contain scenario and metrics dictionaries")
        delay = scenario.get("delay_days")
        project_delay = metrics.get("project_delay_days")
        baseline = metrics.get("baseline_duration_days")
        if isinstance(delay, bool) or not isinstance(delay, int) or delay < 0:
            raise ValueError("scenario delay_days must be a non-negative integer")
        if isinstance(project_delay, bool) or not isinstance(project_delay, int):
            raise ValueError("project_delay_days must be an integer")
        if isinstance(baseline, bool) or not isinstance(baseline, int) or baseline < 0:
            raise ValueError("baseline_duration_days must be a non-negative integer")


def build_statistical_analysis(
    results: list[dict[str, Any]],
    *,
    seed: int = 42,
    bootstrap_resamples: int = 2000,
) -> dict[str, Any]:
    """Build deterministic descriptive and uncertainty statistics for experiment results.

    This layer summarizes observed experiment outputs. It does not perform
    hypothesis testing, causal inference, prediction, or optimization.
    """
    _validate_results(results)

    project_delays = [result["metrics"]["project_delay_days"] for result in results]
    input_delays = [result["scenario"]["delay_days"] for result in results]
    relative_delays = [
        result["metrics"]["project_delay_days"] / result["metrics"]["baseline_duration_days"]
        if result["metrics"]["baseline_duration_days"]
        else 0.0
        for result in results
    ]

    delayed_count = sum(delay > 0 for delay in project_delays)
    delay_rate = delayed_count / len(project_delays)

    summary = summarize_numeric(project_delays)
    input_summary = summarize_numeric(input_delays)
    relative_summary = summarize_numeric(relative_delays)
    mean_ci = bootstrap_mean_ci(
        project_delays,
        seed=seed,
        resamples=bootstrap_resamples,
    )

    evidence = {
        "schema_version": STATISTICAL_ANALYSIS_SCHEMA_VERSION,
        "analysis_type": "DESCRIPTIVE_AND_BOOTSTRAP_UNCERTAINTY",
        "scenario_count": len(results),
        "project_delay": summary,
        "input_delay": input_summary,
        "relative_delay": relative_summary,
        "delay_rate": delay_rate,
        "delayed_scenario_count": delayed_count,
        "delay_free_scenario_count": len(project_delays) - delayed_count,
        "mean_project_delay_confidence_interval": mean_ci,
        "limitations": [
            "This analysis is descriptive and does not establish causality.",
            "Bootstrap uncertainty reflects the supplied experiment scenarios, not a population-level sampling design.",
            "No statistical significance claim is made.",
            "No prediction or optimization is performed.",
        ],
    }

    evidence["analysis_fingerprint"] = stable_hash(evidence)
    return evidence
