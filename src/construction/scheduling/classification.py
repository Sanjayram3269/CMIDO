from __future__ import annotations

from typing import Any

from .float import calculate_total_float


def classify_activities(
    project_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Classify activities using Total Float.

    Float == 0:
        Critical

    Float > 0:
        Non-critical
    """

    results = calculate_total_float(project_data)

    classified = []

    for item in results:
        activity = dict(item)

        if item["total_float"] == 0:
            activity["classification"] = "CRITICAL"
        else:
            activity["classification"] = "NON_CRITICAL"

        classified.append(activity)

    return classified