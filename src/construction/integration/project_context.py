from __future__ import annotations

from typing import Any

from src.construction.integrated_analysis import (
    analyze_project,
)


def build_project_context(
    project_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the unified CMIDO project context.

    7C-A integration layer:

        Project Data
             ↓
        Core Analysis
        ├── CPM / Schedule
        ├── Activities
        └── Materials
             ↓
        Unified Project Context

    This function intentionally does not perform:
        - resource allocation
        - procurement decisions
        - delay simulation
        - risk classification

    Those belong to later 7C layers.

    The existing deterministic domain engines are reused
    through integrated_analysis.analyze_project().
    """

    if not isinstance(project_data, dict):
        raise ValueError(
            "project_data must be a dictionary"
        )

    analysis = analyze_project(project_data)

    schedule = analysis["schedule"]

    return {
        "project": analysis["project"],

        "schedule": {
            "project_duration_days": (
                schedule["project_duration"]
            ),
            "critical_path_duration_days": (
                schedule["critical_path_duration"]
            ),
            "critical_path": (
                schedule["critical_path"]
            ),
            "critical_activities": (
                schedule["critical_activities"]
            ),
            "non_critical_activities": (
                schedule["non_critical_activities"]
            ),
        },

        "activities": analysis["activities"],

        "materials": analysis["materials"],
    }