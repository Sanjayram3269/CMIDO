from __future__ import annotations

from typing import Any, Callable

from .benchmarks import get_benchmark_cases


ScheduleFn = Callable[[dict[str, Any]], dict[str, Any]]


def run_benchmark_case(
    project_data: dict[str, Any],
    schedule_fn: ScheduleFn,
    case_id: str,
) -> dict[str, Any]:
    """Run one benchmark and compare observed CPM outputs with its contract."""
    cases = {case["case_id"]: case for case in get_benchmark_cases()}
    if case_id not in cases:
        raise ValueError(f"Unknown benchmark case: {case_id}")

    expected = cases[case_id]
    observed = schedule_fn(project_data)

    observed_path = list(observed["critical_path"])
    observed_duration = observed["project_duration"]

    return {
        "case_id": case_id,
        "expected": {
            "project_duration_days": expected["expected_duration_days"],
            "critical_path": expected["expected_critical_path"],
        },
        "observed": {
            "project_duration_days": observed_duration,
            "critical_path": observed_path,
        },
        "passed": (
            observed_duration == expected["expected_duration_days"]
            and observed_path == expected["expected_critical_path"]
        ),
    }


def run_all_benchmarks(
    project_data: dict[str, Any],
    schedule_fn: ScheduleFn,
) -> list[dict[str, Any]]:
    """Run every registered benchmark case."""
    return [
        run_benchmark_case(project_data, schedule_fn, case["case_id"])
        for case in get_benchmark_cases()
    ]
