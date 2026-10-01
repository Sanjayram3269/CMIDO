from __future__ import annotations

from typing import Any


def _validate_result(result: dict[str, Any]) -> None:
    if not isinstance(result, dict):
        raise ValueError("result must be a dictionary")
    if "scenario" not in result or "metrics" not in result:
        raise ValueError("result missing scenario or metrics")
    scenario = result["scenario"]
    metrics = result["metrics"]
    if not isinstance(scenario, dict) or not isinstance(metrics, dict):
        raise ValueError("scenario and metrics must be dictionaries")
    if not isinstance(scenario.get("activity_id"), str) or not scenario["activity_id"].strip():
        raise ValueError("result scenario activity_id must be a non-empty string")
    if not isinstance(scenario.get("delay_days"), int) or scenario["delay_days"] < 0:
        raise ValueError("result scenario delay_days must be a non-negative integer")
    for field in ("baseline_duration_days", "scenario_duration_days", "project_delay_days"):
        if not isinstance(metrics.get(field), int):
            raise ValueError(f"result metrics {field} must be an integer")


def compare_scenarios(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce transparent deterministic comparisons across experiment results."""
    if not isinstance(results, list):
        raise ValueError("results must be a list")
    for result in results:
        _validate_result(result)

    rows = []
    for result in results:
        scenario = result["scenario"]
        metrics = result["metrics"]
        baseline = metrics["baseline_duration_days"]
        delay = metrics["project_delay_days"]
        rows.append({
            "activity_id": scenario["activity_id"],
            "delay_days": scenario["delay_days"],
            "baseline_duration_days": baseline,
            "scenario_duration_days": metrics["scenario_duration_days"],
            "project_delay_days": delay,
            "relative_delay": delay / baseline if baseline else 0.0,
            "delay_effective": delay > 0,
        })

    max_delay = max((row["project_delay_days"] for row in rows), default=0)
    return {
        "scenario_count": len(rows),
        "rows": rows,
        "maximum_project_delay_days": max_delay,
        "delayed_scenario_count": sum(row["delay_effective"] for row in rows),
        "zero_delay_scenario_count": sum(not row["delay_effective"] for row in rows),
    }


def analyze_activity_sensitivity(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize deterministic delay response by activity."""
    comparison = compare_scenarios(results)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in comparison["rows"]:
        grouped.setdefault(row["activity_id"], []).append(row)

    activities = []
    for activity_id, rows in grouped.items():
        ordered = sorted(rows, key=lambda row: row["delay_days"])
        first = ordered[0]
        last = ordered[-1]
        activities.append({
            "activity_id": activity_id,
            "scenario_count": len(ordered),
            "minimum_input_delay_days": first["delay_days"],
            "maximum_input_delay_days": last["delay_days"],
            "minimum_project_delay_days": min(r["project_delay_days"] for r in ordered),
            "maximum_project_delay_days": max(r["project_delay_days"] for r in ordered),
            "project_delay_change": last["project_delay_days"] - first["project_delay_days"],
            "monotonic_non_decreasing": all(
                ordered[i]["project_delay_days"] <= ordered[i + 1]["project_delay_days"]
                for i in range(len(ordered) - 1)
            ),
        })

    return {
        "activity_count": len(activities),
        "activities": sorted(activities, key=lambda item: item["activity_id"]),
    }


def build_research_analysis(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a deterministic, research-ready comparative analysis record."""
    comparison = compare_scenarios(results)
    sensitivity = analyze_activity_sensitivity(results)
    return {
        "analysis_type": "DETERMINISTIC_COMPARATIVE_SENSITIVITY",
        "scenario_comparison": comparison,
        "activity_sensitivity": sensitivity,
        "scientific_significance_assessed": False,
        "causal_inference_assessed": False,
    }
