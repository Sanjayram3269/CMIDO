from __future__ import annotations

from typing import Any

from .graph import build_predecessor_map
from .topology import topological_order


def calculate_forward_pass(
    project_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Calculate CPM Early Start (ES) and Early Finish (EF).

    Current supported dependency relationship:
        FS (Finish-to-Start)

    For FS:
        ES(successor) =
            max(EF(predecessor) + lag_days)

        EF =
            ES + duration_days

    Activities without predecessors start at ES = 0.
    """

    activities = {
        activity["activity_id"]: activity
        for activity in project_data["activities"]
    }

    predecessors = build_predecessor_map(project_data)
    order = topological_order(project_data)

    dependencies = project_data["dependencies"]

    dependency_lookup: dict[tuple[str, str], dict[str, Any]] = {
        (
            dependency["predecessor_id"],
            dependency["successor_id"],
        ): dependency
        for dependency in dependencies
    }

    results: dict[str, dict[str, Any]] = {}

    for activity_id in order:
        activity = activities[activity_id]

        duration = activity["duration_days"]

        if duration < 0:
            raise ValueError(
                f"Activity duration cannot be negative: {activity_id}"
            )

        activity_predecessors = predecessors[activity_id]

        if not activity_predecessors:
            es = 0

        else:
            predecessor_finish_times = []

            for predecessor_id in activity_predecessors:
                predecessor_result = results[predecessor_id]

                dependency = dependency_lookup[
                    (predecessor_id, activity_id)
                ]

                relationship_type = dependency["relationship_type"]
                lag_days = dependency["lag_days"]

                if relationship_type == "FS":
                    constraint = predecessor_result["ef"] + lag_days
                elif relationship_type == "SS":
                    constraint = predecessor_result["es"] + lag_days
                elif relationship_type == "FF":
                    constraint = predecessor_result["ef"] + lag_days - duration
                elif relationship_type == "SF":
                    constraint = predecessor_result["es"] + lag_days - duration
                else:
                    raise ValueError(
                        f"Unsupported relationship type "
                        f"{relationship_type!r} for dependency "
                        f"{dependency['dependency_id']}."
                    )

                predecessor_finish_times.append(constraint)

            es = max(0, max(predecessor_finish_times))

        ef = es + duration

        results[activity_id] = {
            "activity_id": activity_id,
            "activity_name": activity["activity_name"],
            "duration_days": duration,
            "predecessors": activity_predecessors,
            "es": es,
            "ef": ef,
        }

    return [
        results[activity_id]
        for activity_id in order
    ]
