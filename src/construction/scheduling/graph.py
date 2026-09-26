from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_predecessor_map(
    project_data: dict[str, Any],
) -> dict[str, list[str]]:
    """
    Build:

        activity_id -> predecessor activity IDs

    from the project's dependency list.
    """

    activities = project_data["activities"]
    dependencies = project_data["dependencies"]

    activity_ids = {
        activity["activity_id"]
        for activity in activities
    }

    predecessors: dict[str, list[str]] = {
        activity_id: []
        for activity_id in activity_ids
    }

    for dependency in dependencies:
        predecessor = dependency["predecessor_id"]
        successor = dependency["successor_id"]

        if predecessor not in activity_ids:
            raise ValueError(
                f"Unknown predecessor activity: {predecessor}"
            )

        if successor not in activity_ids:
            raise ValueError(
                f"Unknown successor activity: {successor}"
            )

        predecessors[successor].append(predecessor)

    return predecessors


def build_successor_map(
    project_data: dict[str, Any],
) -> dict[str, list[str]]:
    """
    Build:

        activity_id -> successor activity IDs
    """

    activities = project_data["activities"]
    dependencies = project_data["dependencies"]

    activity_ids = {
        activity["activity_id"]
        for activity in activities
    }

    successors: dict[str, list[str]] = {
        activity_id: []
        for activity_id in activity_ids
    }

    for dependency in dependencies:
        predecessor = dependency["predecessor_id"]
        successor = dependency["successor_id"]

        if predecessor not in activity_ids:
            raise ValueError(
                f"Unknown predecessor activity: {predecessor}"
            )

        if successor not in activity_ids:
            raise ValueError(
                f"Unknown successor activity: {successor}"
            )

        successors[predecessor].append(successor)

    return successors