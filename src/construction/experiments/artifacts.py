from __future__ import annotations

from typing import Any

from .reproducibility import stable_hash


ARTIFACT_SCHEMA_VERSION = "8D-1.0"


def build_experiment_artifact(
    report: dict[str, Any],
) -> dict[str, Any]:
    """Build an auditable, deterministic artifact from a CMIDO report.

    The artifact is a serialization-ready research record. It does not
    execute experiments, alter results, or recompute domain metrics.
    """

    _validate_report(report)

    experiment = report["experiment"]
    metadata = report["metadata"]
    scenario_summary = report["scenario_summary"]
    benchmarks = report["benchmarks"]
    results = report["results"]

    payload = {
        "experiment": experiment,
        "metadata": metadata,
        "scenario_summary": scenario_summary,
        "benchmarks": benchmarks,
        "results": results,
    }

    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "CMIDO_EXPERIMENT_AUDIT",
        "experiment_id": experiment.get("experiment_id"),
        "configuration_fingerprint": metadata.get(
            "configuration_fingerprint"
        ),
        "result_fingerprint": stable_hash(payload),
        "scenario_count": scenario_summary["total_scenarios"],
        "benchmark_count": benchmarks["total"],
        "benchmark_all_passed": benchmarks["all_passed"],
        "experiment": experiment,
        "metadata": metadata,
        "scenario_summary": scenario_summary,
        "benchmarks": benchmarks,
        "results": results,
    }


def validate_experiment_artifact(
    artifact: dict[str, Any],
) -> bool:
    """Validate the structural and fingerprint integrity of an artifact."""

    if not isinstance(artifact, dict):
        raise ValueError("artifact must be a dictionary")

    required = {
        "schema_version",
        "artifact_type",
        "experiment_id",
        "configuration_fingerprint",
        "result_fingerprint",
        "scenario_count",
        "benchmark_count",
        "benchmark_all_passed",
        "experiment",
        "metadata",
        "scenario_summary",
        "benchmarks",
        "results",
    }

    missing = required - artifact.keys()
    if missing:
        raise ValueError(
            "artifact missing fields: "
            f"{sorted(missing)}"
        )

    if artifact["schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("unsupported artifact schema version")

    if artifact["artifact_type"] != "CMIDO_EXPERIMENT_AUDIT":
        raise ValueError("invalid artifact type")

    if not isinstance(artifact["scenario_count"], int):
        raise ValueError("scenario_count must be an integer")
    if not isinstance(artifact["benchmark_count"], int):
        raise ValueError("benchmark_count must be an integer")
    if not isinstance(artifact["benchmark_all_passed"], bool):
        raise ValueError("benchmark_all_passed must be a boolean")

    payload = {
        "experiment": artifact["experiment"],
        "metadata": artifact["metadata"],
        "scenario_summary": artifact["scenario_summary"],
        "benchmarks": artifact["benchmarks"],
        "results": artifact["results"],
    }

    # Fingerprint verification must happen before derived-field consistency
    # checks so that any mutation of an artifact is reported as an integrity
    # failure rather than as a secondary structural mismatch.
    expected_fingerprint = stable_hash(payload)
    if artifact["result_fingerprint"] != expected_fingerprint:
        raise ValueError("artifact result fingerprint mismatch")

    if artifact["experiment_id"] != artifact["experiment"].get("experiment_id"):
        raise ValueError("artifact experiment_id mismatch")

    if artifact["configuration_fingerprint"] != artifact["metadata"].get(
        "configuration_fingerprint"
    ):
        raise ValueError("artifact configuration fingerprint mismatch")

    if artifact["scenario_count"] != artifact["scenario_summary"].get(
        "total_scenarios"
    ):
        raise ValueError("artifact scenario count mismatch")

    if artifact["benchmark_count"] != artifact["benchmarks"].get("total"):
        raise ValueError("artifact benchmark count mismatch")

    if artifact["benchmark_all_passed"] != artifact["benchmarks"].get(
        "all_passed"
    ):
        raise ValueError("artifact benchmark status mismatch")

    return True


def _validate_report(report: dict[str, Any]) -> None:
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
        raise ValueError(
            "report missing fields: "
            f"{sorted(missing)}"
        )

    if not isinstance(report["experiment"], dict):
        raise ValueError("report experiment must be a dictionary")
    if not isinstance(report["metadata"], dict):
        raise ValueError("report metadata must be a dictionary")
    if not isinstance(report["scenario_summary"], dict):
        raise ValueError("report scenario_summary must be a dictionary")
    if not isinstance(report["benchmarks"], dict):
        raise ValueError("report benchmarks must be a dictionary")
    if not isinstance(report["results"], list):
        raise ValueError("report results must be a list")

    if "experiment_id" not in report["experiment"]:
        raise ValueError("report experiment missing experiment_id")
    if "configuration_fingerprint" not in report["metadata"]:
        raise ValueError("report metadata missing configuration_fingerprint")
