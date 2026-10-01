import pytest

from src.construction.experiments import (
    build_experiment_artifact,
    validate_experiment_artifact,
    validate_experiment_evidence,
)


def make_report():
    return {
        "experiment": {
            "experiment_id": "8E_TEST",
            "name": "8E Test",
            "seed": 42,
        },
        "metadata": {
            "experiment_id": "8E_TEST",
            "seed": 42,
            "parameters": {"purpose": "validation"},
            "configuration_fingerprint": "config-8e",
        },
        "scenario_summary": {
            "total_scenarios": 2,
            "delayed_scenarios": 1,
            "delay_free_scenarios": 1,
            "total_delay_days": 3,
            "maximum_delay_days": 3,
            "average_delay_days": 1.5,
        },
        "benchmarks": {
            "total": 2,
            "passed": 2,
            "failed": 0,
            "all_passed": True,
            "results": [
                {"case_id": "B1", "passed": True},
                {"case_id": "B2", "passed": True},
            ],
        },
        "results": [
            {
                "scenario": {"activity_id": "A005", "delay_days": 0},
                "metrics": {"project_delay_days": 0},
            },
            {
                "scenario": {"activity_id": "A006", "delay_days": 3},
                "metrics": {"project_delay_days": 3},
            },
        ],
    }


def test_validation_accepts_consistent_report():
    evidence = validate_experiment_evidence(make_report())

    assert evidence["valid"] is True
    assert evidence["checks_failed"] == 0
    assert evidence["scientific_claim_status"] == "NOT_ASSESSED"


def test_validation_reports_all_checks():
    evidence = validate_experiment_evidence(make_report())

    assert evidence["checks_total"] >= 8
    assert evidence["checks_passed"] == evidence["checks_total"]


def test_validation_detects_scenario_count_mismatch():
    report = make_report()
    report["scenario_summary"]["total_scenarios"] = 99

    evidence = validate_experiment_evidence(report)

    assert evidence["valid"] is False
    assert evidence["checks_failed"] >= 1


def test_validation_detects_delay_aggregate_mismatch():
    report = make_report()
    report["scenario_summary"]["total_delay_days"] = 4

    evidence = validate_experiment_evidence(report)

    assert evidence["valid"] is False
    assert any(
        check["name"] == "delay_total" and not check["passed"]
        for check in evidence["checks"]
    )


def test_validation_detects_benchmark_mismatch():
    report = make_report()
    report["benchmarks"]["passed"] = 1

    evidence = validate_experiment_evidence(report)

    assert evidence["valid"] is False
    assert any(
        check["name"] == "benchmark_pass_count" and not check["passed"]
        for check in evidence["checks"]
    )


def test_validation_accepts_matching_audit_artifact():
    artifact = build_experiment_artifact(make_report())
    evidence = validate_experiment_evidence(make_report(), artifact)

    assert validate_experiment_artifact(artifact) is True
    assert evidence["valid"] is True
    assert any(
        check["name"] == "audit_artifact" and check["passed"]
        for check in evidence["checks"]
    )


def test_validation_rejects_tampered_artifact():
    artifact = build_experiment_artifact(make_report())
    artifact["scenario_count"] = 99

    with pytest.raises(ValueError, match="artifact result fingerprint mismatch"):
        validate_experiment_evidence(make_report(), artifact)


def test_validation_rejects_negative_delay():
    report = make_report()
    report["results"][1]["metrics"]["project_delay_days"] = -1

    with pytest.raises(ValueError, match="cannot be negative"):
        validate_experiment_evidence(report)


def test_validation_rejects_missing_report_fields():
    report = make_report()
    del report["benchmarks"]

    with pytest.raises(ValueError, match="report missing fields"):
        validate_experiment_evidence(report)
