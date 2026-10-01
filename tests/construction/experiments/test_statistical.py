import pytest

from src.construction.experiments import (
    bootstrap_mean_ci,
    build_statistical_analysis,
    summarize_numeric,
)


def make_results():
    return [
        {
            "scenario": {"activity_id": "A005", "delay_days": 0},
            "metrics": {
                "baseline_duration_days": 74,
                "scenario_duration_days": 74,
                "project_delay_days": 0,
            },
        },
        {
            "scenario": {"activity_id": "A005", "delay_days": 1},
            "metrics": {
                "baseline_duration_days": 74,
                "scenario_duration_days": 75,
                "project_delay_days": 1,
            },
        },
        {
            "scenario": {"activity_id": "A006", "delay_days": 3},
            "metrics": {
                "baseline_duration_days": 74,
                "scenario_duration_days": 77,
                "project_delay_days": 3,
            },
        },
    ]


def test_summarize_numeric_is_transparent():
    summary = summarize_numeric([0, 1, 3])
    assert summary["count"] == 3
    assert summary["mean"] == pytest.approx(4 / 3)
    assert summary["median"] == 1
    assert summary["minimum"] == 0
    assert summary["maximum"] == 3
    assert summary["q1"] == pytest.approx(0.5)
    assert summary["q3"] == pytest.approx(2.0)


def test_bootstrap_ci_is_reproducible():
    first = bootstrap_mean_ci([0, 1, 3], seed=42, resamples=100)
    second = bootstrap_mean_ci([0, 1, 3], seed=42, resamples=100)
    assert first == second
    assert first["lower"] <= 4 / 3 <= first["upper"]


def test_statistical_analysis_contains_delay_evidence():
    analysis = build_statistical_analysis(
        make_results(),
        seed=42,
        bootstrap_resamples=100,
    )

    assert analysis["schema_version"] == "8K-1.0"
    assert analysis["scenario_count"] == 3
    assert analysis["delayed_scenario_count"] == 2
    assert analysis["delay_free_scenario_count"] == 1
    assert analysis["delay_rate"] == pytest.approx(2 / 3)
    assert analysis["project_delay"]["mean"] == pytest.approx(4 / 3)
    assert "mean_project_delay_confidence_interval" in analysis
    assert analysis["analysis_fingerprint"]


def test_statistical_analysis_rejects_empty_results():
    with pytest.raises(ValueError, match="results must not be empty"):
        build_statistical_analysis([])


def test_statistical_analysis_rejects_invalid_delay():
    results = make_results()
    results[0]["scenario"]["delay_days"] = -1
    with pytest.raises(ValueError, match="delay_days"):
        build_statistical_analysis(results)


def test_statistical_analysis_does_not_claim_significance():
    analysis = build_statistical_analysis(
        make_results(),
        bootstrap_resamples=100,
    )
    assert any("No statistical significance claim" in item for item in analysis["limitations"])
