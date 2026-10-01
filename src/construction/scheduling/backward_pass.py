from __future__ import annotations

from typing import Any

from .graph import build_successor_map
from .topology import topological_order
from .forward_pass import calculate_forward_pass


def calculate_backward_pass(
    project_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Calculate CPM Latest Start (LS) and Latest Finish (LF).

    The backward pass works from the project finish backwards.

    For FS relationships:

        LF(predecessor) =
            min(LS(successor) - lag_days)

        LS =
            LF - duration_days

    The project duration is obtained from the forward pass.
    """

    activities = {
        activity["activity_id"]: activity
        for activity in project_data["activities"]
    }

    successors = build_successor_map(project_data)
    order = topological_order(project_data)

    forward_results = calculate_forward_pass(project_data)

    forward_by_id = {
        result["activity_id"]: result
        for result in forward_results
    }

    project_duration = max(
        result["ef"]
        for result in forward_results
    )

    dependency_lookup: dict[tuple[str, str], dict[str, Any]] = {
        (
            dependency["predecessor_id"],
            dependency["successor_id"],
        ): dependency
        for dependency in project_data["dependencies"]
    }

    results: dict[str, dict[str, Any]] = {}

    # Work backwards through the dependency-safe order.
    for activity_id in reversed(order):
        activity = activities[activity_id]

        duration = activity["duration_days"]

        activity_successors = successors[activity_id]

        if not activity_successors:
            # Final activity.
            lf = project_duration

        else:
            successor_constraints = []

            for successor_id in activity_successors:
                successor_result = results[successor_id]

                dependency = dependency_lookup[
                    (activity_id, successor_id)
                ]

                relationship_type = dependency["relationship_type"]
                lag_days = dependency["lag_days"]

                if relationship_type == "FS":
                    constraint = successor_result["ls"] - lag_days
                elif relationship_type == "SS":
                    constraint = successor_result["ls"] - lag_days + duration
                elif relationship_type == "FF":
                    constraint = successor_result["lf"] - lag_days
                elif relationship_type == "SF":
                    constraint = successor_result["lf"] - lag_days + duration
                else:
                    raise ValueError(
                        f"Unsupported relationship type "
                        f"{relationship_type!r} for dependency "
                        f"{dependency['dependency_id']}."
                    )

                successor_constraints.append(constraint)

            lf = min(successor_constraints)

        ls = lf - duration

        results[activity_id] = {
            "activity_id": activity_id,
            "activity_name": activity["activity_name"],
            "duration_days": duration,
            "es": forward_by_id[activity_id]["es"],
            "ef": forward_by_id[activity_id]["ef"],
            "ls": ls,
            "lf": lf,
            "successors": activity_successors,
        }

    return [
        results[activity_id]
        for activity_id in order
    ]