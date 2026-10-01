from __future__ import annotations

from typing import Any

from src.construction.integration.decision_context import (
    build_decision_context,
)
from src.construction.integration.project_context import (
    build_project_context,
)
from src.construction.integration.resource_procurement import (
    build_resource_procurement_context,
)
from src.construction.uncertainty.context import (
    build_uncertainty_context,
)


def build_cross_domain_context(
    project_data: dict[str, Any],
    available_resources: dict[str, float],
    delay_scenarios: list[dict[str, Any]] | None = None,
    risks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build the CMIDO 7E cross-domain construction context.

    7E composes the completed 7C-A, 7C-B, 7C-C and 7D
    contracts into one traceable cross-domain representation.

    It intentionally does not reimplement scheduling, resource,
    procurement, delay, or risk calculations.
    """

    if not isinstance(project_data, dict):
        raise ValueError("project_data must be a dictionary")

    if not isinstance(available_resources, dict):
        raise ValueError(
            "available_resources must be a dictionary"
        )

    if delay_scenarios is None:
        delay_scenarios = []

    if risks is None:
        risks = []

    if not isinstance(delay_scenarios, list):
        raise ValueError("delay_scenarios must be a list")

    if not isinstance(risks, list):
        raise ValueError("risks must be a list")

    project_context = build_project_context(project_data)

    resource_procurement_context = (
        build_resource_procurement_context(
            project_data,
            available_resources,
        )
    )

    decision_context = build_decision_context(
        project_data,
        available_resources,
        delay_scenarios,
    )

    uncertainty_context = build_uncertainty_context(
        project_data,
        risks,
    )

    baseline_duration = project_context[
        "schedule"
    ]["project_duration_days"]

    decision_impact = decision_context[
        "project_impact"
    ]
    uncertainty_impact = uncertainty_context[
        "project_impact"
    ]

    scenario_duration = max(
        baseline_duration,
        decision_impact["scenario_duration_days"],
        uncertainty_impact["scenario_duration_days"],
    )

    project_delay_days = scenario_duration - baseline_duration

    if project_delay_days > 0:
        decision_status = "PROJECT_DELAY"
    else:
        decision_status = "FEASIBLE"

    evidence = {
        "baseline": {
            "source": "7C-A",
            "project_duration_days": baseline_duration,
            "critical_path": project_context[
                "schedule"
            ]["critical_path"],
        },
        "resources": {
            "source": "7C-B",
            "resource_summary": resource_procurement_context[
                "resources"
            ]["summary"],
        },
        "procurement": {
            "source": "7C-B",
            "total_requirements": resource_procurement_context[
                "procurement"
            ]["total_requirements"],
            "requirements": resource_procurement_context[
                "procurement"
            ]["requirements"],
        },
        "delay_scenarios": {
            "source": "7C-C",
            "count": len(
                decision_context["schedule_impacts"]
            ),
            "schedule_impacts": decision_context[
                "schedule_impacts"
            ],
        },
        "risks": {
            "source": "7D",
            "count": uncertainty_context[
                "risk_summary"
            ]["total_risks"],
            "risk_summary": uncertainty_context[
                "risk_summary"
            ],
            "scenarios": uncertainty_context[
                "scenarios"
            ],
        },
    }

    return {
        "project": project_context["project"],
        "baseline": project_context["schedule"],
        "activities": project_context["activities"],
        "materials": project_context["materials"],
        "resources": resource_procurement_context[
            "resources"
        ],
        "procurement": resource_procurement_context[
            "procurement"
        ],
        "delay_scenarios": decision_context[
            "delay_scenarios"
        ],
        "schedule_impacts": decision_context[
            "schedule_impacts"
        ],
        "risks": uncertainty_context["risks"],
        "risk_summary": uncertainty_context[
            "risk_summary"
        ],
        "risk_scenarios": uncertainty_context[
            "scenarios"
        ],
        "project_impact": {
            "baseline_duration_days": baseline_duration,
            "scenario_duration_days": scenario_duration,
            "project_delay_days": project_delay_days,
            "delay_present": project_delay_days > 0,
            "schedule_delay_days": decision_impact[
                "project_delay_days"
            ],
            "risk_delay_days": uncertainty_impact[
                "project_delay_days"
            ],
        },
        "decision": {
            "status": decision_status,
        },
        "evidence": evidence,
    }
