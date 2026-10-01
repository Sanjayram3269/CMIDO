from __future__ import annotations

from typing import Any

from .artifacts import validate_experiment_artifact


VALIDATION_SCHEMA_VERSION = "8E-1.0"


def validate_experiment_evidence(
    report: dict[str, Any],
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate internal consistency of a CMIDO experiment report.

    This is an evidence-integrity layer. It checks that scenario counts,
    delay metrics, benchmark aggregates, and optional audit-artifact
    fingerprints agree with one another. It does not claim statistical
    validity, causal validity, or scientific significance.
    """

    if not isinstance(report, dict):
        raise ValueError("report must be a dictionary")

    required = {
        "experiment",
        "metadata",
        "scenario_summary",
        "benchmarks",
        "results",
    }
    missing = required - report.keys()
    if missing:
        raise ValueError(f"report missing fields: {sorted(missing)}")

    experiment = report["experiment"]
    metadata = report["metadata"]
    summary = report["scenario_summary"]
    benchmarks = report["benchmarks"]
    results = report["results"]

    if not isinstance(experiment, dict):
        raise ValueError("report experiment must be a dictionary")
    if not isinstance(metadata, dict):
        raise ValueError("report metadata must be a dictionary")
    if not isinstance(summary, dict):
        raise ValueError("report scenario_summary must be a dictionary")
    if not isinstance(benchmarks, dict):
        raise ValueError("report benchmarks must be a dictionary")
    if not isinstance(results, list):
        raise ValueError("report results must be a list")

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({
            "name": name,
            "passed": bool(passed),
            "detail": detail,
        })

    check(
        "scenario_count",
        summary.get("total_scenarios") == len(results),
        "reported scenario count matches result count",
    )

    delays: list[int] = []
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            raise ValueError(f"result {index} must be a dictionary")
        metrics = item.get("metrics")
        scenario = item.get("scenario")
        if not isinstance(metrics, dict):
            raise ValueError(f"result {index} metrics must be a dictionary")
        if not isinstance(scenario, dict):
            raise ValueError(f"result {index} scenario must be a dictionary")
        delay = metrics.get("project_delay_days")
        if not isinstance(delay, int):
            raise ValueError(f"result {index} project_delay_days must be an integer")
        if delay < 0:
            raise ValueError(f"result {index} project_delay_days cannot be negative")
        delays.append(delay)

    total_delay = sum(delays)
    delayed_count = sum(delay > 0 for delay in delays)
    maximum_delay = max(delays, default=0)

    check(
        "delay_total",
        summary.get("total_delay_days") == total_delay,
        "reported total delay matches scenario metrics",
    )
    check(
        "delayed_scenarios",
        summary.get("delayed_scenarios") == delayed_count,
        "reported delayed-scenario count matches scenario metrics",
    )
    check(
        "maximum_delay",
        summary.get("maximum_delay_days") == maximum_delay,
        "reported maximum delay matches scenario metrics",
    )

    benchmark_results = benchmarks.get("results")
    if not isinstance(benchmark_results, list):
        raise ValueError("benchmarks results must be a list")

    passed = sum(
        isinstance(item, dict) and bool(item.get("passed", False))
        for item in benchmark_results
    )
    failed = len(benchmark_results) - passed

    check(
        "benchmark_count",
        benchmarks.get("total") == len(benchmark_results),
        "reported benchmark count matches benchmark results",
    )
    check(
        "benchmark_pass_count",
        benchmarks.get("passed") == passed,
        "reported benchmark pass count matches benchmark results",
    )
    check(
        "benchmark_fail_count",
        benchmarks.get("failed") == failed,
        "reported benchmark failure count matches benchmark results",
    )
    check(
        "benchmark_status",
        benchmarks.get("all_passed") == (len(benchmark_results) > 0 and failed == 0),
        "reported aggregate benchmark status matches benchmark results",
    )

    check(
        "experiment_identity",
        bool(experiment.get("experiment_id"))
        and metadata.get("experiment_id") == experiment.get("experiment_id"),
        "experiment and metadata identify the same experiment",
    )
    check(
        "configuration_fingerprint",
        bool(metadata.get("configuration_fingerprint")),
        "configuration fingerprint is present",
    )

    if artifact is not None:
        artifact_valid = validate_experiment_artifact(artifact)
        check(
            "audit_artifact",
            artifact_valid
            and artifact.get("experiment_id") == experiment.get("experiment_id"),
            "audit artifact is structurally valid and identifies the same experiment",
        )

    all_passed = all(item["passed"] for item in checks)

    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "validation_type": "CMIDO_EXPERIMENT_EVIDENCE",
        "experiment_id": experiment.get("experiment_id"),
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "valid": all_passed,
        "scientific_claim_status": "NOT_ASSESSED",
    }
