from __future__ import annotations

from typing import Any

from .dataset_fingerprint import build_dataset_metadata
from .dataset_loader import load_json_dataset
from .evaluator import evaluate_schedule_scenario
from .report import build_experiment_report
from .runner import run_experiment


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
