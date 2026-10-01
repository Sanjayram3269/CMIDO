from src.construction.experiments import ExperimentConfig, run_experiment


def fake_evaluator(project_data, activity_id, delay_days):
    baseline = project_data["baseline"]
    return {
        "baseline_project_duration": baseline,
        "scenario_project_duration": baseline + delay_days,
    }


def test_runner_executes_all_scenarios():
    result = run_experiment(
        {"baseline": 74},
        ExperimentConfig("EXP-001", "delay sweep", seed=42),
        [
            {"activity_id": "A005", "delay_days": 0},
            {"activity_id": "A006", "delay_days": 3},
        ],
        fake_evaluator,
    )

    assert result["scenario_count"] == 2
    assert result["results"][0]["metrics"]["project_delay_days"] == 0
    assert result["results"][1]["metrics"]["project_delay_days"] == 3
    assert result["metadata"]["seed"] == 42
