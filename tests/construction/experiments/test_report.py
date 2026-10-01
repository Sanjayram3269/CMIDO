import json

import pytest

from src.construction.experiments import (
    ExperimentConfig,
    build_experiment_report,
    build_delay_scenarios,
    evaluate_schedule_scenario,
    run_experiment,
)


PROJECT_PATH = "data/projects/cmido_demo_project.json"


def load_project():
    with open(
        PROJECT_PATH,
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_report_contains_experiment_information():

    project = load_project()

    config = ExperimentConfig(
        experiment_id="8C_TEST",
        name="8C Test",
        seed=42,
        parameters={
            "purpose": "report_test",
        },
    )

    scenarios = [
    {
        "activity_id": "A005",
        "delay_days": 1,
    },
    {
        "activity_id": "A006",
        "delay_days": 3,
    },
]

    result = run_experiment(
        project,
        config,
        scenarios,
        evaluate_schedule_scenario,
    )

    report = build_experiment_report(result)

    assert report["experiment"]["experiment_id"] == "8C_TEST"
    assert report["metadata"]["seed"] == 42
    assert report["scenario_summary"]["total_scenarios"] == 2


def test_report_aggregates_delay_metrics():

    project = load_project()

    config = ExperimentConfig(
        experiment_id="8C_DELAY",
        name="8C Delay",
        seed=42,
        parameters={},
    )

    scenarios = [
    {
        "activity_id": "A005",
        "delay_days": 1,
    },
    {
        "activity_id": "A006",
        "delay_days": 3,
    },
]

    result = run_experiment(
        project,
        config,
        scenarios,
        evaluate_schedule_scenario,
    )

    report = build_experiment_report(result)

    summary = report[
        "scenario_summary"
    ]

    assert summary["total_scenarios"] == 2
    assert summary["delayed_scenarios"] == 1
    assert summary["delay_free_scenarios"] == 1
    assert summary["total_delay_days"] == 3
    assert summary["maximum_delay_days"] == 3
    assert summary["average_delay_days"] == 1.5


def test_report_aggregates_benchmarks():

    experiment_result = {
        "experiment": {
            "experiment_id": "8C_BENCH",
        },
        "metadata": {
            "seed": 42,
        },
        "scenario_count": 0,
        "results": [],
    }

    benchmark_results = [
        {
            "case_id": "B001",
            "passed": True,
        },
        {
            "case_id": "B002",
            "passed": True,
        },
        {
            "case_id": "B003",
            "passed": False,
        },
    ]

    report = build_experiment_report(
        experiment_result,
        benchmark_results,
    )

    benchmarks = report["benchmarks"]

    assert benchmarks["total"] == 3
    assert benchmarks["passed"] == 2
    assert benchmarks["failed"] == 1
    assert benchmarks["all_passed"] is False


def test_report_handles_empty_scenarios():

    experiment_result = {
        "experiment": {
            "experiment_id": "EMPTY",
        },
        "metadata": {
            "seed": 1,
        },
        "scenario_count": 0,
        "results": [],
    }

    report = build_experiment_report(
        experiment_result
    )

    assert (
        report["scenario_summary"][
            "total_scenarios"
        ]
        == 0
    )

    assert (
        report["scenario_summary"][
            "average_delay_days"
        ]
        == 0.0
    )


def test_report_rejects_invalid_input():

    with pytest.raises(ValueError):
        build_experiment_report(
            []
        )


def test_report_rejects_missing_fields():

    with pytest.raises(ValueError):
        build_experiment_report(
            {
                "experiment": {},
                "metadata": {},
            }
        )
