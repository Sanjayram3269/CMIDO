import json

import pytest

from src.construction.experiments import (
    ARTIFACT_SCHEMA_VERSION,
    ExperimentConfig,
    build_experiment_artifact,
    build_experiment_report,
    evaluate_schedule_scenario,
    run_experiment,
    validate_experiment_artifact,
)


PROJECT_PATH = "data/projects/cmido_demo_project.json"


def load_project():
    with open(PROJECT_PATH, encoding="utf-8") as file:
        return json.load(file)


def build_report():
    project = load_project()
    config = ExperimentConfig(
        experiment_id="8D_TEST",
        name="8D Artifact Test",
        seed=42,
        parameters={"purpose": "artifact_test"},
    )

    scenarios = [
        {"activity_id": "A005", "delay_days": 1},
        {"activity_id": "A006", "delay_days": 3},
    ]

    result = run_experiment(
        project,
        config,
        scenarios,
        evaluate_schedule_scenario,
    )

    return build_experiment_report(result)


def test_artifact_contains_audit_identity():
    artifact = build_experiment_artifact(build_report())

    assert artifact["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert artifact["artifact_type"] == "CMIDO_EXPERIMENT_AUDIT"
    assert artifact["experiment_id"] == "8D_TEST"
    assert artifact["scenario_count"] == 2
    assert artifact["result_fingerprint"]
    assert artifact["configuration_fingerprint"]


def test_artifact_is_valid():
    artifact = build_experiment_artifact(build_report())

    assert validate_experiment_artifact(artifact) is True


def test_artifact_is_json_serializable():
    artifact = build_experiment_artifact(build_report())

    encoded = json.dumps(
        artifact,
        sort_keys=True,
    )

    assert json.loads(encoded) == artifact


def test_artifact_detects_result_tampering():
    artifact = build_experiment_artifact(build_report())
    artifact["results"][0]["metrics"]["project_delay_days"] = 99

    with pytest.raises(ValueError, match="fingerprint mismatch"):
        validate_experiment_artifact(artifact)


def test_artifact_detects_identity_mismatch():
    artifact = build_experiment_artifact(build_report())
    artifact["experiment_id"] = "OTHER"

    with pytest.raises(ValueError, match="experiment_id mismatch"):
        validate_experiment_artifact(artifact)


def test_artifact_detects_schema_mismatch():
    artifact = build_experiment_artifact(build_report())
    artifact["schema_version"] = "OLD"

    with pytest.raises(ValueError, match="unsupported artifact schema version"):
        validate_experiment_artifact(artifact)


def test_artifact_rejects_incomplete_report():
    with pytest.raises(ValueError, match="report missing fields"):
        build_experiment_artifact({"experiment": {}})


def test_artifact_benchmark_state_is_preserved():
    report = build_report()
    report["benchmarks"] = {
        "total": 2,
        "passed": 2,
        "failed": 0,
        "all_passed": True,
        "results": [
            {"case_id": "B001", "passed": True},
            {"case_id": "B002", "passed": True},
        ],
    }

    artifact = build_experiment_artifact(report)

    assert artifact["benchmark_count"] == 2
    assert artifact["benchmark_all_passed"] is True
    assert validate_experiment_artifact(artifact) is True
