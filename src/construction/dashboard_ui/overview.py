"""CMIDO 10A.5 — Overview / Project Intelligence presentation builders.

Pure functions that shape already-computed values into render-ready specs for
the existing 10A.3 components (KPI rows, tables, publication-status cards).

Layering rules, identical to the rest of ``dashboard_ui``:

* no research-engine imports and no Streamlit import — this module stays
  importable by tests and tooling without launching a dashboard;
* no artifact access — evidence counts arrive as an already-loaded 10A.2-B
  snapshot overview, or ``None`` when the snapshot could not be loaded;
* no fabricated values — a metric whose source value is absent is omitted or
  reported as an explicit unavailable/partial state, never replaced with zero;
* no research conclusions — statuses describe deterministic project analysis,
  evidence availability or planned workspaces, and those three layers are
  always reported separately.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence

#: How serious each evidence-style status is when an overall label must be
#: chosen. Planned / input-dependent layers (``optional``, ``empty``) are
#: expected states, so they never drag the overall label down.
_SEVERITY: dict[str, int] = {
    "valid": 0,
    "available": 0,
    "optional": 0,
    "empty": 0,
    "partial": 1,
    "loading": 1,
    "missing": 2,
    "too_large": 2,
    "unsupported": 2,
    "blocked": 3,
    "invalid": 3,
}


def _worst(statuses: Sequence[str]) -> str:
    """Most severe status in ``statuses`` (unknown values count as partial)."""
    values = [str(status) for status in statuses if status]
    if not values:
        return "valid"
    return max(values, key=lambda status: _SEVERITY.get(status, 1))


def _snapshot_value(snapshot_overview: Any, name: str) -> Any:
    """Read a field from a snapshot overview object or mapping, else ``None``."""
    if snapshot_overview is None:
        return None
    if isinstance(snapshot_overview, Mapping):
        return snapshot_overview.get(name)
    return getattr(snapshot_overview, name, None)


def _horizon_days(start: Any, end: Any) -> int | None:
    """Days between declared project dates, or ``None`` when unparsable."""
    try:
        return (date.fromisoformat(str(end)) - date.fromisoformat(str(start))).days
    except (ValueError, TypeError):
        return None


def build_overview_kpis(project: Any, data: Any) -> list[dict[str, Any]]:
    """KPI card specs for the Project Snapshot section.

    Every card corresponds to a value that actually exists in the loaded
    project inputs or the existing engine output.  Missing source values are
    skipped — this builder never emits a placeholder zero.
    """
    data_map = data if isinstance(data, Mapping) else {}
    overview = data_map.get("overview")
    overview = overview if isinstance(overview, Mapping) else {}

    items: list[dict[str, Any]] = []

    def add(
        label: str,
        value: Any,
        *,
        unit: str | None = None,
        description: str | None = None,
        provenance: str = "DER",
        status: str = "valid",
    ) -> None:
        if value is None:
            return
        if isinstance(value, str) and not value.strip():
            return
        items.append(
            {
                "label": label,
                "value": value,
                "unit": unit,
                "description": description,
                "provenance": provenance,
                "status": status,
            }
        )

    duration = overview.get("project_duration_days")
    total = overview.get("total_activities")
    critical = overview.get("critical_activities")
    non_critical = overview.get("non_critical_activities")

    add("Project duration", duration, unit="d", description="Baseline CPM duration (deterministic)")
    if critical is not None and non_critical is not None:
        add("Activities", total, description=f"{critical} critical · {non_critical} non-critical")
    else:
        add("Activities", total, description="Activities registered in the loaded project")
    if critical is not None and total is not None:
        add(
            "Critical activities",
            critical,
            description=f"{critical} of {total} activities on the critical path",
        )
    else:
        add("Critical activities", critical)
    add("Material types", overview.get("total_material_types"), description="tracked in quantity demand")

    project_map = project if isinstance(project, Mapping) else {}
    suppliers = project_map.get("suppliers")
    if isinstance(suppliers, list):
        add("Suppliers", len(suppliers), provenance="OBS", description="registered in project inputs")

    meta = project_map.get("project")
    meta = meta if isinstance(meta, Mapping) else {}
    project_status = meta.get("status")
    if isinstance(project_status, str) and project_status.strip():
        add(
            "Project status",
            project_status,
            provenance="OBS",
            description="declared in project inputs",
        )
    return items


def build_project_context_rows(
    project: Any,
    source_name: str | None = None,
    source_path: str | None = None,
) -> list[tuple[str, str]]:
    """``(field, value)`` rows for the Project Context panel.

    Only declared inputs are exposed, as plain text — never raw dicts.  The
    planned horizon is derived from the declared dates; everything else is a
    verbatim input value or a list length.
    """
    project_map = project if isinstance(project, Mapping) else {}
    meta = project_map.get("project")
    meta = meta if isinstance(meta, Mapping) else {}
    rows: list[tuple[str, str]] = []

    def add(field: str, value: Any) -> None:
        if value is None:
            return
        text = str(value).strip()
        if not text:
            return
        rows.append((field, text))

    add("Project ID", meta.get("project_id"))
    add("Project name", meta.get("project_name"))
    add("Project type", meta.get("project_type"))
    add("Location", meta.get("location"))
    add("Status", meta.get("status"))
    add("Start date", meta.get("start_date"))
    add("Planned end date", meta.get("planned_end_date"))

    horizon = _horizon_days(meta.get("start_date"), meta.get("planned_end_date"))
    if horizon is not None:
        rows.append(("Planned horizon (days)", str(horizon)))

    calendar = project_map.get("calendar")
    calendar = calendar if isinstance(calendar, Mapping) else {}
    add("Calendar", calendar.get("name") or calendar.get("calendar_id"))

    for label, key in (
        ("Activities", "activities"),
        ("Dependencies", "dependencies"),
        ("Materials", "materials"),
        ("Suppliers", "suppliers"),
        ("Supplier-material links", "supplier_materials"),
    ):
        value = project_map.get(key)
        if isinstance(value, list):
            rows.append((f"{label} (inputs)", str(len(value))))

    if isinstance(source_path, str) and source_path == "uploaded":
        add("Source", f"{source_name or 'Uploaded project'} — uploaded in this session")
    elif source_name:
        add("Source", f"{source_name} — bundled project file")
    return rows


def build_schedule_rows(
    schedule_activities: Any,
    float_rows: Any = None,
) -> list[dict[str, Any]]:
    """Activity rows for the schedule-intelligence table.

    Timing and float columns are included only when the scheduling engine
    returned float rows for *every* activity; partial timing is dropped
    entirely rather than rendered as empty cells or zeros.
    """
    activities = [row for row in (schedule_activities or []) if isinstance(row, Mapping)]
    floats = {
        row.get("activity_id"): row
        for row in (float_rows or [])
        if isinstance(row, Mapping) and row.get("activity_id") is not None
    }
    timing_complete = bool(activities) and bool(floats) and all(
        activity.get("activity_id") in floats for activity in activities
    )

    rows: list[dict[str, Any]] = []
    for activity in activities:
        row: dict[str, Any] = {
            "Activity": activity.get("activity_id"),
            "Name": activity.get("activity_name"),
            "Duration (d)": activity.get("duration_days"),
            "Critical": "YES" if activity.get("is_critical") else "NO",
        }
        if timing_complete:
            engine = floats[activity["activity_id"]]
            row["Early start (d)"] = engine.get("es")
            row["Early finish (d)"] = engine.get("ef")
            row["Total float (d)"] = engine.get("total_float")
        rows.append(row)
    return rows


def build_evidence_status(
    snapshot_overview: Any,
    *,
    real_world_planned: bool,
    ro_workspaces_planned: bool,
) -> tuple[list[tuple[str, str]], str, str]:
    """Evidence-readiness rows, an overall status and an honest note.

    Counts come from the loaded 10A.2-B snapshot (``None`` means it could not
    be loaded — that is reported as missing, not as zero).  Planned research
    workspaces contribute ``optional`` rows and never inflate the overall
    status, which is driven by project data, the snapshot and artifact health.
    """
    rows: list[tuple[str, str]] = [("Project data", "valid")]
    core: list[str] = ["valid"]

    registered = available = missing = invalid = None
    if snapshot_overview is not None:
        registered = _snapshot_value(snapshot_overview, "total_artifacts_registered")
        available = _snapshot_value(snapshot_overview, "total_artifacts_available")
        missing = _snapshot_value(snapshot_overview, "total_artifacts_missing")
        invalid = _snapshot_value(snapshot_overview, "total_artifacts_invalid")

    if None in (registered, available, missing, invalid):
        rows.append(("Dashboard snapshot", "missing"))
        rows.append(("Research evidence artifacts", "missing"))
        core.append("missing")
        note = (
            "Dashboard snapshot unavailable, so artifact counts cannot be reported. "
            "Project data and engine results on this page remain available."
        )
    else:
        rows.append(("Dashboard snapshot", "valid"))
        if invalid:
            artifact_status = "invalid"
        elif missing or available < registered:
            artifact_status = "partial"
        else:
            artifact_status = "valid"
        core.append(artifact_status)
        rows.append(
            (f"Research evidence artifacts ({available} of {registered} available)", artifact_status)
        )
        note = (
            f"{available} of {registered} registered artifacts available · "
            f"{missing} missing · {invalid} invalid."
        )

    rows.append(("Real-world data workspace", "optional" if real_world_planned else "valid"))
    rows.append(("RO1/RO2/RO3 workspaces", "optional" if ro_workspaces_planned else "valid"))
    return rows, _worst(core), note


def deterministic_status(data: Any) -> tuple[str, str]:
    """Status label and message for the deterministic project analysis layer."""
    data_map = data if isinstance(data, Mapping) else {}
    overview = data_map.get("overview")
    overview = overview if isinstance(overview, Mapping) else {}

    duration = overview.get("project_duration_days")
    total = overview.get("total_activities")
    critical = overview.get("critical_activities")
    if duration is None or total is None or critical is None:
        return (
            "missing",
            "The schedule analysis for the loaded project is incomplete, so baseline "
            "duration and critical-path state cannot be reported.",
        )
    return (
        "valid",
        f"Baseline analyzed: {duration} d project duration · {critical} of {total} "
        "activities on the critical path. Resource feasibility is reported separately "
        "and is not evaluated on Overview.",
    )


def build_status_board(
    schedule_status: str,
    evidence_overall: str,
) -> tuple[str, list[tuple[str, str]]]:
    """Overall label plus rows for the Project Status board.

    Deterministic analysis, evidence availability and planned research
    workspaces stay on separate rows so the page never collapses them into a
    single misleading verdict.
    """
    rows: list[tuple[str, str]] = [
        ("Deterministic schedule analysis", schedule_status),
        ("Resource feasibility (availability inputs)", "optional"),
        ("Research evidence artifacts", evidence_overall),
        ("RO1/RO2/RO3 research workspaces", "optional"),
    ]
    return _worst([schedule_status, evidence_overall]), rows
