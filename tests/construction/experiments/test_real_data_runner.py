import json
from pathlib import Path

from src.construction.experiments import (
    ExperimentConfig,
    build_delay_scenarios,
    run_real_dataset_experiment,
    run_real_dataset_report,
)


PROJECT_PATH = Path("data/projects/cmido_demo_project.json")


def canonical_fixture(tmp_path):
    raw = json.loads(PROJECT_PATH.read_text(encoding="utf-8"))
    path = tmp_path / "cmido_real_fixture.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def make_config():
    return ExperimentConfig(
        experiment_id="8J_REAL_DATA",
        name="8J Real Dataset Execution",
        seed=42,
        parameters={"dataset_type": "canonical_construction"},
    )


def test_real_dataset_experiment_executes_actual_evaluator(tmp_path):
    dataset_path = canonical_fixture(tmp_path)
    scenarios = build_delay_scenarios("A005", [0, 1, 3])

    result = run_real_dataset_experiment(
        str(dataset_path),
        make_config(),
        scenarios,
    )

    assert result["scenario_count"] == 3
    assert result["dataset"]["dataset_id"] == "CMIDO_DATASET"
    assert result["results"][0]["metrics"]["project_delay_days"] == 0
    assert result["results"][1]["metrics"]["project_delay_days"] == 0


def test_real_dataset_report_preserves_dataset_provenance(tmp_path):
    dataset_path = canonical_fixture(tmp_path)
    report = run_real_dataset_report(
        str(dataset_path),
        make_config(),
        build_delay_scenarios("A006", [0, 3]),
    )

    assert report["scenario_summary"]["total_scenarios"] == 2
    assert report["dataset"]["schema_version"] == "8H-1.0"
    assert report["dataset"]["dataset_fingerprint"]


def test_real_dataset_runner_rejects_missing_dataset(tmp_path):
    missing = tmp_path / "missing.json"
    try:
        run_real_dataset_experiment(str(missing), make_config(), [])
    except ValueError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("missing dataset should be rejected")
