from __future__ import annotations

from typing import Any


def build_dependency_3d_data(project_data: dict[str, Any]) -> dict[str, list[Any]]:
    """Create deterministic coordinates and edges for the interactive 3D schedule view."""
    activities = project_data.get("activities", [])
    dependencies = project_data.get("dependencies", [])
    ids = [a["activity_id"] for a in activities]
    predecessors: dict[str, list[str]] = {activity_id: [] for activity_id in ids}
    for dep in dependencies:
        if dep["successor_id"] in predecessors and dep["predecessor_id"] in predecessors:
            predecessors[dep["successor_id"]].append(dep["predecessor_id"])

    level: dict[str, int] = {}
    visiting: set[str] = set()

    def get_level(activity_id: str) -> int:
        if activity_id in level:
            return level[activity_id]
        if activity_id in visiting:
            return 0
        visiting.add(activity_id)
        parents = predecessors.get(activity_id, [])
        level[activity_id] = 0 if not parents else max(get_level(parent) for parent in parents) + 1
        visiting.remove(activity_id)
        return level[activity_id]

    for activity_id in ids:
        get_level(activity_id)

    groups: dict[int, list[str]] = {}
    for activity_id in ids:
        groups.setdefault(level[activity_id], []).append(activity_id)

    x: list[float] = []
    y: list[float] = []
    z: list[float] = []
    labels: list[str] = []
    for activity in activities:
        activity_id = activity["activity_id"]
        siblings = groups[level[activity_id]]
        rank = siblings.index(activity_id)
        center = (len(siblings) - 1) / 2
        x.append(float(level[activity_id]))
        y.append(float(rank - center))
        z.append(float(activity.get("duration_days", activity.get("duration", 0))))
        labels.append(f"{activity_id} · {activity['activity_name']}")

    edge_x: list[Any] = []
    edge_y: list[Any] = []
    edge_z: list[Any] = []
    positions = {activity_id: (x[i], y[i], z[i]) for i, activity_id in enumerate(ids)}
    for dep in dependencies:
        if dep["predecessor_id"] not in positions or dep["successor_id"] not in positions:
            continue
        start = positions[dep["predecessor_id"]]
        end = positions[dep["successor_id"]]
        edge_x.extend([start[0], end[0], None])
        edge_y.extend([start[1], end[1], None])
        edge_z.extend([start[2], end[2], None])

    return {
        "x": x,
        "y": y,
        "z": z,
        "labels": labels,
        "ids": ids,
        "edge_x": edge_x,
        "edge_y": edge_y,
        "edge_z": edge_z,
    }


def build_kpi_state(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Normalize dashboard metrics for UI rendering."""
    overview = dashboard["overview"]
    resources = dashboard["resources"]["summary"]
    return {
        "duration": overview["project_duration_days"],
        "critical": overview["critical_activities"],
        "activities": overview["total_activities"],
        "materials": overview["total_material_types"],
        "resource_shortages": resources["shortage_resources"],
        "resource_feasible": resources["feasible_resources"],
        "status": dashboard["status"],
    }


def scenario_options(project_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return UI-safe activity options for scenario simulation."""
    return [
        {
            "activity_id": activity["activity_id"],
            "activity_name": activity["activity_name"],
            "duration_days": activity.get("duration_days", activity.get("duration", 0)),
        }
        for activity in project_data.get("activities", [])
    ]
