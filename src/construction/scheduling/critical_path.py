from __future__ import annotations

from typing import Any

from .classification import classify_activities


def calculate_critical_path(
    project_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Derive the critical path from zero-float activities
    and the project's dependency graph.

    Critical activities are those with total_float == 0.

    The critical path is the ordered chain of critical
    activities connected by project dependencies.
    """

    classified = classify_activities(project_data)

    by_id = {
        item["activity_id"]: item
        for item in classified
    }

    critical_ids = {
        item["activity_id"]
        for item in classified
        if item["classification"] == "CRITICAL"
    }

    # Build successor relationships restricted to
    # critical activities.
    critical_successors: dict[str, list[str]] = {
        activity_id: []
        for activity_id in critical_ids
    }

    critical_predecessors: dict[str, list[str]] = {
        activity_id: []
        for activity_id in critical_ids
    }

    for dependency in project_data["dependencies"]:
        predecessor = dependency["predecessor_id"]
        successor = dependency["successor_id"]

        if (
            predecessor in critical_ids
            and successor in critical_ids
        ):
            critical_successors[predecessor].append(successor)
            critical_predecessors[successor].append(predecessor)

    # A starting critical activity has no critical predecessor.
    starts = [
        activity_id
        for activity_id in critical_ids
        if not critical_predecessors[activity_id]
    ]

    if len(starts) != 1:
        raise ValueError(
            "Expected exactly one starting critical activity, "
            f"but found: {starts}"
        )

    path = []
    current = starts[0]

    while True:
        path.append(current)

        successors = critical_successors[current]

        if not successors:
            break

        if len(successors) != 1:
            raise ValueError(
                "Critical path branches at "
                f"{current}: {successors}"
            )

        current = successors[0]

    # Every zero-float activity should belong to the
    # derived critical path for this single-path model.
    path_set = set(path)

    missing = critical_ids - path_set

    if missing:
        raise ValueError(
            "Zero-float activities are not connected "
            f"to the derived critical path: {sorted(missing)}"
        )

    critical_path_duration = sum(
        by_id[activity_id]["duration_days"]
        for activity_id in path
    )

    project_duration = max(
        item["ef"]
        for item in classified
    )

    if critical_path_duration != project_duration:
        raise ValueError(
            "Critical path duration does not match "
            f"project duration: "
            f"{critical_path_duration} != "
            f"{project_duration}"
        )

    return {
        "project_duration": project_duration,
        "critical_path_duration": critical_path_duration,
        "critical_path": path,
        "critical_activities": [
            by_id[activity_id]
            for activity_id in path
        ],
        "non_critical_activities": [
            item
            for item in classified
            if item["classification"] == "NON_CRITICAL"
        ],
    }