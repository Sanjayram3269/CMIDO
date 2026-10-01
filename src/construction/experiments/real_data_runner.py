from __future__ import annotations

from typing import Any

from .dataset_fingerprint import build_dataset_metadata
from .dataset_loader import load_json_dataset
from .evaluator import evaluate_schedule_scenario
from .report import build_experiment_report
from .runner import run_experiment
from .statistical import build_statistical_analysis


def run_real_dataset_experiment(
    dataset_path: str,
    config: Any,
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    """Execute the CMIDO deterministic experiment pipeline on a canonical dataset.

    The dataset must already have passed the 8H canonical validation layer.
    This function adds dataset provenance to the experiment output and uses
    the real CMIDO schedule-impact evaluator rather than a mock evaluator.
    """
    dataset = load_json_dataset(dataset_path)
    dataset_metadata = build_dataset_metadata(dataset)

    experiment = run_experiment(
        dataset,
        config,
        scenarios,
        evaluate_schedule_scenario,
    )

    experiment["dataset"] = dataset_metadata
    return experiment


def run_real_dataset_report(
    dataset_path: str,
    config: Any,
    scenarios: list[dict[str, Any]],
    benchmarks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run a real-data experiment and build the standard research report."""
    experiment = run_real_dataset_experiment(dataset_path, config, scenarios)
    return build_experiment_report(
        experiment,
        benchmarks or [],
    )


def run_real_dataset_statistical_analysis(
    dataset_path: str,
    config: Any,
    scenarios: list[dict[str, Any]],
    *,
    seed: int = 42,
    bootstrap_resamples: int = 2000,
) -> dict[str, Any]:
    """Run a real-data experiment and generate reproducible statistical evidence."""
    experiment = run_real_dataset_experiment(dataset_path, config, scenarios)
    analysis = build_statistical_analysis(
        experiment["results"],
        seed=seed,
        bootstrap_resamples=bootstrap_resamples,
    )
    return {
        "experiment": experiment,
        "statistical_analysis": analysis,
    }
