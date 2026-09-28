from __future__ import annotations

from typing import Any

from src.construction.integrated_analysis import (
    analyze_project,
)
from src.construction.resource_dashboard import (
    build_resource_dashboard,
)
from src.construction.resource_schedule_impact import (
    analyze_resource_schedule_impact,
)


def build_decision_context(
    project_data: dict[str, Any],
    available_resources: dict[str, float],
    delay_scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build the CMIDO 7C-C decision context.

    Decision flow:

        Project Context
             +
        Resource Availability
             +
        Delay Scenarios
             ↓
        Schedule Impact
             ↓
        Project Impact
             ↓
        Decision

    Decision semantics:

        FEASIBLE
            No scenario causes project delay.

        CONSTRAINT_PRESENT
            Reserved for future constraint-level
            classification when a constraint exists
            without project delay.

        PROJECT_DELAY
            At least one scenario increases
            project duration.

    A delay fully absorbed by activity float is
    therefore FEASIBLE at project level.
    """

    # ---------------------------------------------------------
    # 1. Validate inputs
    # ---------------------------------------------------------

    if not isinstance(project_data, dict):
        raise ValueError(
            "project_data must be a dictionary"
        )

    if not isinstance(available_resources, dict):
        raise ValueError(
            "available_resources must be a dictionary"
        )

    if delay_scenarios is None:
        delay_scenarios = []

    if not isinstance(delay_scenarios, list):
        raise ValueError(
            "delay_scenarios must be a list"
        )

    # ---------------------------------------------------------
    # 2. Build core project context
    # ---------------------------------------------------------

    project_context = build_project_context(
        project_data
    )

    # ---------------------------------------------------------
    # 3. Baseline schedule
    # ---------------------------------------------------------

    baseline = project_context["schedule"]

    baseline_duration = baseline[
        "project_duration_days"
    ]

    baseline_critical_path = baseline[
        "critical_path"
    ]

    # ---------------------------------------------------------
    # 4. Resource context
    # ---------------------------------------------------------

    resource_context = build_resource_dashboard(
        project_data,
        available_resources,
    )

    # ---------------------------------------------------------
    # 5. Analyze delay scenarios
    # ---------------------------------------------------------

    schedule_impacts: list[dict[str, Any]] = []

    for scenario in delay_scenarios:

        if not isinstance(scenario, dict):
            raise ValueError(
                "Each delay scenario must be a dictionary"
            )

        required_fields = {
            "activity_id",
            "delay_days",
        }

        missing = (
            required_fields
            - scenario.keys()
        )

        if missing:
            raise ValueError(
                "Delay scenario missing fields: "
                f"{sorted(missing)}"
            )

        activity_id = scenario[
            "activity_id"
        ]

        delay_days = scenario[
            "delay_days"
        ]

        if not isinstance(delay_days, int):
            raise ValueError(
                "delay_days must be an integer"
            )

        if delay_days < 0:
            raise ValueError(
                "delay_days cannot be negative"
            )

        impact = analyze_resource_schedule_impact(
            project_data,
            resource_id="SCHEDULE",
            activity_id=activity_id,
            shortage_quantity=0,
            shortage_days=delay_days,
        )

        schedule_impacts.append(
            {
                "scenario": {
                    "activity_id": activity_id,
                    "delay_days": delay_days,
                },
                "schedule": impact,
            }
        )

    # ---------------------------------------------------------
    # 6. Procurement domain
    #
    # 7C-C does not introduce procurement scenarios.
    # Preserve the resource/procurement domain from the
    # existing resource-procurement integration contract.
    # ---------------------------------------------------------

    procurement = {
        "total_requirements": 0,
        "requirements": [],
    }

    # ---------------------------------------------------------
    # 7. Determine overall project impact
    # ---------------------------------------------------------

    scenario_duration = baseline_duration
    project_delay_days = 0

    for item in schedule_impacts:

        impact = item["schedule"]

        delay = impact[
            "project_delay_days"
        ]

        duration = impact[
            "scenario_project_duration"
        ]

        project_delay_days = max(
            project_delay_days,
            delay,
        )

        scenario_duration = max(
            scenario_duration,
            duration,
        )

    project_impact = {
        "baseline_duration_days": (
            baseline_duration
        ),
        "scenario_duration_days": (
            scenario_duration
        ),
        "project_delay_days": (
            project_delay_days
        ),
        "delay_present": (
            project_delay_days > 0
        ),
    }

    # ---------------------------------------------------------
    # 8. Decision classification
    # ---------------------------------------------------------

    if project_delay_days > 0:
        decision_status = "PROJECT_DELAY"
    else:
        decision_status = "FEASIBLE"

    # ---------------------------------------------------------
    # 9. Unified 7C-C decision context
    # ---------------------------------------------------------

    return {
        "project": project_context[
            "project"
        ],

        "baseline": {
            "project_duration_days": (
                baseline_duration
            ),
            "critical_path": (
                baseline_critical_path
            ),
        },

        "activities": project_context[
            "activities"
        ],

        "materials": project_context[
            "materials"
        ],

        "resources": resource_context,

        "procurement": procurement,

        "delay_scenarios": delay_scenarios,

        "schedule_impacts": schedule_impacts,

        "project_impact": project_impact,

        "decision": {
            "status": decision_status,
        },
    }


def build_project_context(
    project_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Compatibility wrapper for the existing 7C-A
    project context builder.
    """

    from src.construction.integration.project_context import (
        build_project_context as _build_project_context,
    )

    return _build_project_context(
        project_data
    )