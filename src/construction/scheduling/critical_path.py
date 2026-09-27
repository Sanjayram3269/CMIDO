from __future__ import annotations

from typing import Any

from .classification import classify_activities


def _find_all_critical_paths(
    critical_ids: set[str],
    critical_successors: dict[str, list[str]],
    critical_predecessors: dict[str, list[str]],
) -> list[list[str]]:
    """
    Find all critical paths in the zero-float activity graph.

    A critical path is a dependency-connected sequence of
    zero-float activities from a critical start to a critical end.
    """

    starts = sorted(
        activity_id
        for activity_id in critical_ids
        if not critical_predecessors[activity_id]
    )

    if not starts:
        raise ValueError(
            "No starting critical activity was found."
        )

    ends = {
        activity_id
        for activity_id in critical_ids
        if not critical_successors[activity_id]
    }

    paths: list[list[str]] = []

    def dfs(
        current: str,
        current_path: list[str],
    ) -> None:
        if current in current_path:
            raise ValueError(
                "Cycle detected in critical activity graph."
            )

        updated_path = current_path + [current]

        if current in ends:
            paths.append(updated_path)
            return

        for successor in sorted(
            critical_successors[current]
        ):
            dfs(successor, updated_path)

    for start in starts:
        dfs(start, [])

    if not paths:
        raise ValueError(
            "No complete critical path could be derived."
        )

    return paths


def calculate_critical_path(
    project_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Derive critical paths from zero-float activities.

    Supports both single and multiple critical paths.

    Backward compatibility:
        critical_path
        critical_path_duration
        critical_activities

    Additional output:
        critical_paths
        critical_path_durations
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

    if not critical_ids:
        raise ValueError(
            "No critical activities were found."
        )

    # Build the critical-only dependency graph.
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
            critical_successors[predecessor].append(
                successor
            )

            critical_predecessors[successor].append(
                predecessor
            )

    critical_paths = _find_all_critical_paths(
        critical_ids,
        critical_successors,
        critical_predecessors,
    )

    # Calculate duration of every critical path.
    critical_path_durations = [
        sum(
            by_id[activity_id]["duration_days"]
            for activity_id in path
        )
        for path in critical_paths
    ]

    project_duration = max(
        item["ef"]
        for item in classified
    )

    # At least one critical path must explain the
    # project's total duration.
    if project_duration not in critical_path_durations:
        raise ValueError(
            "No critical path duration matches "
            f"project duration: {project_duration}. "
            f"Critical path durations: "
            f"{critical_path_durations}"
        )

    # Preserve the original API:
    # choose the first longest critical path.
    longest_index = max(
        range(len(critical_paths)),
        key=lambda index: critical_path_durations[index],
    )

    primary_path = critical_paths[longest_index]
    primary_duration = critical_path_durations[
        longest_index
    ]

    primary_path_set = set(primary_path)

    # All zero-float activities remain critical activities.
    critical_activities = [
        item
        for item in classified
        if item["activity_id"] in critical_ids
    ]

    return {
        "project_duration": project_duration,

        # Backward-compatible single-path fields.
        "critical_path_duration": primary_duration,
        "critical_path": primary_path,

        # New multi-path information.
        "critical_paths": critical_paths,
        "critical_path_durations": critical_path_durations,

        "critical_activities": critical_activities,

        "non_critical_activities": [
            item
            for item in classified
            if item["classification"] == "NON_CRITICAL"
        ],
    }