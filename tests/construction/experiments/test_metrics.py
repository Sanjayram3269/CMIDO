import pytest

from src.construction.experiments import summarize_result, summarize_schedule_impact


def test_schedule_metrics():
    result = summarize_schedule_impact(74, 77)
    assert result["project_delay_days"] == 3
    assert result["delay_present"] is True
    assert result["relative_delay"] == pytest.approx(3 / 74)


def test_zero_delay():
    result = summarize_schedule_impact(74, 74)
    assert result["project_delay_days"] == 0
    assert result["delay_present"] is False


def test_result_summary_requires_durations():
    with pytest.raises(ValueError):
        summarize_result({})
