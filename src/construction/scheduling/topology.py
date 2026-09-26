from __future__ import annotations

from collections import deque
from typing import Any

from .graph import build_predecessor_map, build_successor_map


def topological_order(
    project_data: dict[str, Any],
) -> list[str]:
    """
    Return activities in dependency-safe order.

    Raises ValueError when the dependency graph contains a cycle.
    """

    predecessors = build_predecessor_map(project_data)
    successors = build_successor_map(project_data)

    in_degree = {
        activity_id: len(preds)
        for activity_id, preds in predecessors.items()
    }

    queue = deque(
        activity_id
        for activity_id, degree in in_degree.items()
        if degree == 0
    )

    order: list[str] = []

    while queue:
        activity_id = queue.popleft()
        order.append(activity_id)

        for successor in successors[activity_id]:
            in_degree[successor] -= 1

            if in_degree[successor] == 0:
                queue.append(successor)

    if len(order) != len(predecessors):
        raise ValueError(
            "Dependency graph contains a cycle"
        )

    return order