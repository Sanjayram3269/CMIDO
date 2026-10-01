from src.construction.experiments.benchmark_runner import (
    run_all_benchmarks,
    run_benchmark_case,
)


def fake_schedule(project_data):
    return {
        "project_duration": 74,
        "critical_path": [
            "A001", "A002", "A003", "A004", "A006",
            "A007", "A008", "A009", "A011",
        ],
    }


def test_benchmark_case_passes_expected_contract():
    result = run_benchmark_case({}, fake_schedule, "baseline_cmido_demo")
    assert result["passed"] is True
    assert result["observed"]["project_duration_days"] == 74


def test_all_benchmarks_pass():
    results = run_all_benchmarks({}, fake_schedule)
    assert results
    assert all(item["passed"] for item in results)
