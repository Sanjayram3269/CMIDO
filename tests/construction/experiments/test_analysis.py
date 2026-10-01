import pytest

from src.construction.experiments.analysis import (
    analyze_activity_sensitivity,
    build_research_analysis,
    compare_scenarios,
)


def result(activity_id, delay_days, project_delay, baseline=74):
    return {
        "scenario": {"activity_id": activity_id, "delay_days": delay_days},
        "metrics": {
            "baseline_duration_days": baseline,
            "scenario_duration_days": baseline + project_delay,
            "project_delay_days": project_delay,
        },
    }


def test_compare_scenarios_aggregates_delay_counts():
    output = compare_scenarios([
        result("A005", 0, 0),
        result("A005", 3, 0),
        result("A006", 3, 3),
    ])
    assert output["scenario_count"] == 3
    assert output["delayed_scenario_count"] == 1
    assert output["zero_delay_scenario_count"] == 2
    assert output["maximum_project_delay_days"] == 3


def test_compare_scenarios_is_transparent():
    output = compare_scenarios([result("A006", 3, 3)])
    assert output["rows"][0]["relative_delay"] == 3 / 74
    assert output["rows"][0]["delay_effective"] is True


def test_activity_sensitivity_groups_and_orders_scenarios():
    output = analyze_activity_sensitivity([
        result("A006", 3, 3),
        result("A006", 0, 0),
        result("A006", 6, 6),
    ])
    activity = output["activities"][0]
    assert activity["activity_id"] == "A006"
    assert activity["scenario_count"] == 3
    assert activity["minimum_input_delay_days"] == 0
    assert activity["maximum_input_delay_days"] == 6
    assert activity["maximum_project_delay_days"] == 6
    assert activity["monotonic_non_decreasing"] is True


def test_research_analysis_marks_significance_unassessed():
    output = build_research_analysis([result("A006", 3, 3)])
    assert output["analysis_type"] == "DETERMINISTIC_COMPARATIVE_SENSITIVITY"
    assert output["scientific_significance_assessed"] is False
    assert output["causal_inference_assessed"] is False


def test_analysis_rejects_invalid_results():
    with pytest.raises(ValueError):
        compare_scenarios([{"scenario": {}, "metrics": {}}])

    with pytest.raises(ValueError):
        analyze_activity_sensitivity("invalid")
