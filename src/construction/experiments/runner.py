from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .config import ExperimentConfig
from .metrics import summarize_result
from .reproducibility import build_metadata
from .scenarios import validate_scenario


ImpactEvaluator = Callable[[dict[str, Any], str, int], dict[str, Any]]


def run_experiment(
    project_data: dict[str, Any],
    config: ExperimentConfig,
    scenarios: list[dict[str, Any]],
    evaluator: ImpactEvaluator,
) -> dict[str, Any]:
    """Run deterministic scenarios through an existing CMIDO evaluator.

    The runner orchestrates experiments only; it does not implement domain logic.
    """
    if not isinstance(project_data, dict):
        raise ValueError("project_data must be a dictionary")
    if not isinstance(scenarios, list):
        raise ValueError("scenarios must be a list")
    if not callable(evaluator):
        raise ValueError("evaluator must be callable")

    normalized = [validate_scenario(item) for item in scenarios]
    results: list[dict[str, Any]] = []

    for scenario in normalized:
        raw = evaluator(
            project_data,
            scenario["activity_id"],
            scenario["delay_days"],
        )
        metrics = summarize_result(raw)
        results.append(
            {
                "scenario": scenario,
                "metrics": metrics,
                "raw_result": raw,
            }
        )

    metadata = build_metadata(
        config.experiment_id,
        config.seed,
        config.parameters,
    )

    return {
        "experiment": config.to_dict(),
        "metadata": metadata,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario_count": len(results),
        "results": results,
    }
