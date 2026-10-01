from __future__ import annotations

from typing import Any


def build_experiment_report(
    experiment_result: dict[str, Any],
    benchmark_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a research-ready report from a completed CMIDO experiment."""
    if not isinstance(experiment_result, dict):
        raise ValueError("experiment_result must be a dictionary")

    if benchmark_results is None:
        benchmark_results = []
    if not isinstance(benchmark_results, list):
        raise ValueError("benchmark_results must be a list")

    required_fields = {"experiment", "metadata", "scenario_count", "results"}
    missing = required_fields - experiment_result.keys()
    if missing:
        raise ValueError(f"experiment_result missing fields: {sorted(missing)}")

    results = experiment_result["results"]
    if not isinstance(results, list):
        raise ValueError("experiment_result['results'] must be a list")

    total_scenarios = len(results)
    delayed_scenarios = 0
    total_delay_days = 0
    maximum_delay_days = 0

    for item in results:
        if not isinstance(item, dict):
            raise ValueError("Each experiment result must be a dictionary")
        metrics = item.get("metrics")
        if not isinstance(metrics, dict):
            raise ValueError("metrics must be a dictionary")
        delay = metrics.get("project_delay_days", 0)
        if not isinstance(delay, int):
            raise ValueError("project_delay_days must be an integer")
        total_delay_days += delay
        if delay > 0:
            delayed_scenarios += 1
        maximum_delay_days = max(maximum_delay_days, delay)

    benchmark_count = len(benchmark_results)
    passed_benchmarks = sum(
        bool(item.get("passed", False))
        for item in benchmark_results
        if isinstance(item, dict)
    )

    report = {
        "experiment": experiment_result["experiment"],
        "metadata": experiment_result["metadata"],
        "scenario_summary": {
            "total_scenarios": total_scenarios,
            "delayed_scenarios": delayed_scenarios,
            "delay_free_scenarios": total_scenarios - delayed_scenarios,
            "total_delay_days": total_delay_days,
            "maximum_delay_days": maximum_delay_days,
            "average_delay_days": total_delay_days / total_scenarios if total_scenarios else 0.0,
        },
        "benchmarks": {
            "total": benchmark_count,
            "passed": passed_benchmarks,
            "failed": benchmark_count - passed_benchmarks,
            "all_passed": benchmark_count > 0 and benchmark_count == passed_benchmarks,
            "results": benchmark_results,
        },
        "results": results,
    }

    if "dataset" in experiment_result:
        report["dataset"] = experiment_result["dataset"]

    return report
