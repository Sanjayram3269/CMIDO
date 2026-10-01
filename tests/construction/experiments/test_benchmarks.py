from src.construction.experiments.benchmarks import (
    get_benchmark_case,
    get_benchmark_cases,
)


def test_benchmark_cases_are_registered():
    cases = get_benchmark_cases()
    assert cases
    assert cases[0]["case_id"] == "baseline_cmido_demo"


def test_baseline_contract_matches_locked_cpm_result():
    case = get_benchmark_case("baseline_cmido_demo")
    assert case["expected_duration_days"] == 74
    assert case["expected_critical_path"] == [
        "A001", "A002", "A003", "A004", "A006",
        "A007", "A008", "A009", "A011",
    ]


def test_unknown_benchmark_is_rejected():
    try:
        get_benchmark_case("does_not_exist")
    except ValueError as exc:
        assert "Unknown benchmark case" in str(exc)
    else:
        raise AssertionError("Unknown benchmark should be rejected")
