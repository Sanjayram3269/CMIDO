from __future__ import annotations

from typing import Any

from .backward_pass import calculate_backward_pass


def calculate_total_float(
    project_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Calculate Total Float for every activity.

    Total Float:
        TF = LS - ES

    Equivalent:
        TF = LF - EF

    The two calculations must produce the same result.
    """

    backward_results = calculate_backward_pass(project_data)

    results = []

    for item in backward_results:
        total_float = item["ls"] - item["es"]

        # Independent consistency check.
        alternate_float = item["lf"] - item["ef"]

        if total_float != alternate_float:
            raise ValueError(
                f"Float inconsistency for activity "
                f"{item['activity_id']}: "
                f"LS-ES={total_float}, "
                f"LF-EF={alternate_float}"
            )

        if total_float < 0:
            raise ValueError(
                f"Negative total float detected for "
                f"activity {item['activity_id']}: "
                f"{total_float}"
            )

        result = dict(item)
        result["total_float"] = total_float

        results.append(result)

    return results