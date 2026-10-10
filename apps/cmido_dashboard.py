"""CMIDO Streamlit dashboard.

Layering (10A.2-B preserved, 10A.3 UI layer added)::

    research engines -> validated artifacts -> dashboard_data snapshot
                    -> dashboard_ui design system -> this page

10A.3 scope: this page consumes the reusable design system
(:mod:`src.construction.dashboard_ui`) for branding, headers, KPI cards,
section headers, chart containers, table wrappers, provenance badges and
artifact status states.  It performs no new research logic and reads no raw
scenario ledgers.

10A.4 scope: this page adds the application shell.  The grouped sidebar,
the breadcrumb and the page router all read from one declarative navigation
registry (:mod:`src.construction.dashboard_ui.navigation`), so the four
research groups - CORE, DECISION, RESEARCH, EVIDENCE - cannot drift apart.
Page content is unchanged from 10A.3.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.construction.dashboard import build_dashboard_data
from src.construction.dashboard_view import build_dependency_3d_data
from src.construction.resource_dashboard import build_resource_dashboard
from src.construction.scheduling import calculate_total_float
from src.construction.simulation.impact import analyze_schedule_impact
from src.construction.uncertainty.context import build_uncertainty_context
from src.construction.experiments import (
    ExperimentConfig,
    build_delay_scenarios,
    build_statistical_analysis,
    run_real_dataset_experiment,
)
from src.construction.dashboard_data import build_dashboard_snapshot
from src.construction.dashboard_ui import (
    apply_chart_theme,
    axis_reference,
    build_artifact_state,
    build_breadcrumb,
    build_nav_breadcrumb,
    page_description,
    page_future_phase,
    page_group_label,
    page_is_planned,
    page_research_stage,
    page_title,
    build_empty_state,
    build_flow_diagram,
    build_footer,
    build_methodology_card,
    build_evidence_status,
    build_overview_kpis,
    build_project_context_rows,
    build_provenance_badge,
    build_publication_status,
    build_schedule_rows,
    build_status_board,
    deterministic_status,
    format_days,
    format_feasibility,
    format_integer,
    format_interval,
    format_number,
    format_percent,
    format_shortage_pct,
    pagelist,
    validate_shell,
)
from src.construction.dashboard_ui.components import (
    inject_css,
    render_active_nav_item,
    render_app_header,
    render_chart,
    render_error_state,
    render_future_page_panel,
    render_html,
    render_kpi_columns,
    render_legacy_kpi_row,
    render_nav_legend,
    render_page_header,
    render_section_block,
    render_section_header,
    render_sidebar_navigation,
    render_status_banner,
    render_table,
)
from src.construction.dashboard_ui import ro1 as ro1_workspace
from src.construction.dashboard_ui import ro2 as ro2_workspace

from src.construction.dashboard_ui.navigation import legacy_route_for
from src.construction.dashboard_ui.theme import DANGER, INFO, SECONDARY_TEXT


def page_provenance(page_id: str) -> str | None:
    """Return the provenance vocabulary for a page, if the registry carries one.

    This is purely a presentation helper; it does not read artifacts or infer
    provenance. Unknown or empty values are left as ``None`` so the page header
    does not invent a provenance badge.
    """
    from src.construction.dashboard_ui.navigation import page_by_id

    page = page_by_id(page_id)
    return page.provenance or None


DEFAULT_PROJECT = ROOT / "data" / "projects" / "cmido_demo_project.json"

#: Destination labels, owned by the 10A.4 navigation registry.  The page body
#: below dispatches on the registry route titles, so the registry stays the single source of
#: truth for the shell, the breadcrumb and the router.
PAGES = list(pagelist())

st.set_page_config(
    page_title="CMIDO | Construction Decision Intelligence",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 10A.3 design system stylesheet (injected once per session).
inject_css()

# 10A.4 shell: refuse to render navigation built on a malformed registry.
NAV_PROBLEMS = validate_shell()
if NAV_PROBLEMS:
    render_error_state(
        "Navigation registry is misconfigured",
        description="The dashboard shell could not resolve its navigation registry. "
                    "Restore src/construction/dashboard_ui/navigation.py to the shipped registry.",
        diagnostics="; ".join(NAV_PROBLEMS),
    )
    st.stop()


@st.cache_data(show_spinner=False, max_entries=1)
def cached_snapshot(root: str) -> Any:
    """Cache the 10A.2-B snapshot so artifact loading is not repeated per rerun.

    The snapshot is validated, read-only evidence assembled from the artifact
    registry; caching it keeps Streamlit reruns cheap without bypassing the
    ``dashboard_data`` layer.
    """
    return build_dashboard_snapshot(Path(root))


def load_project(uploaded: Any) -> tuple[dict[str, Any], str, str]:
    if uploaded is not None:
        data = json.loads(uploaded.getvalue().decode("utf-8"))
        return data, uploaded.name, "uploaded"
    return json.loads(DEFAULT_PROJECT.read_text(encoding="utf-8")), DEFAULT_PROJECT.name, str(DEFAULT_PROJECT)


def graph_3d(project: dict[str, Any], critical: set[str]) -> go.Figure:
    d = build_dependency_3d_data(project)
    critical_mask = [x in critical for x in d["ids"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=d["edge_x"], y=d["edge_y"], z=d["edge_z"], mode="lines",
        line=dict(width=3), name="Dependencies", hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter3d(
        x=d["x"], y=d["y"], z=d["z"], mode="markers+text", text=d["ids"],
        textposition="top center", hovertext=d["labels"], hoverinfo="text",
        marker=dict(
            size=[17 if x else 10 for x in critical_mask],
            color=[10 if x else 0 for x in critical_mask],
            colorscale=[[0, "#3B6EA5"], [1, "#B23A2E"]],
            symbol="diamond", showscale=False,
        ), name="Activities"
    ))
    fig.update_layout(
        height=600,
        scene=dict(
            xaxis=axis_reference("Dependency level"),
            yaxis=axis_reference("Parallel position"),
            zaxis=axis_reference("Duration", "days"),
        ),
    )
    # 3D scenes need the full canvas, so the shared 2D margins are relaxed.
    return apply_chart_theme(fig, margin={"l": 0, "r": 0, "t": 40, "b": 0})


def result_frame(experiment: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in experiment.get("results", []):
        s, m = item["scenario"], item["metrics"]
        rows.append({
            "Activity": s["activity_id"],
            "Input delay (days)": s["delay_days"],
            "Project delay (days)": m["project_delay_days"],
            "Scenario duration (days)": m["scenario_duration_days"],
            "Relative delay": m["relative_delay"],
        })
    return pd.DataFrame(rows)


def critical_path_banner(critical_path: list[str]) -> None:
    """Render the critical path with an explicit deterministic/derived marker."""
    render_status_banner(
        "Critical path: " + " → ".join(critical_path),
        status="valid",
        title="Deterministic critical path",
    )


def schedule_timeline(rows: list[dict[str, Any]], project_duration: Any) -> go.Figure:
    """Gantt-style progression built from existing CPM outputs.

    Each bar spans early start -> early finish for one activity; colour marks
    criticality with the 10A.3 theme tokens. No schedule value is computed
    here - the rows are engine output shaped for presentation only.
    """
    critical_rows = [row for row in rows if row.get("Critical") == "YES"]
    other_rows = [row for row in rows if row.get("Critical") != "YES"]

    def label(row: dict[str, Any]) -> str:
        name = row.get("Name")
        return f"{row.get('Activity')} \u00b7 {name}" if name else str(row.get("Activity"))

    fig = go.Figure()
    for group, name, color in (
        (critical_rows, "Critical", DANGER),
        (other_rows, "Non-critical", INFO),
    ):
        if not group:
            continue
        fig.add_trace(go.Bar(
            y=[label(row) for row in group],
            x=[row.get("Duration (d)") for row in group],
            base=[row.get("Early start (d)") for row in group],
            orientation="h",
            name=name,
            marker=dict(color=color),
            hovertemplate="%{y}<br>early day %{base} \u00b7 %{x} d<extra>"
            + name
            + "</extra>",
        ))
    ordered = sorted(
        rows,
        key=lambda row: (row.get("Early start (d)") or 0, str(row.get("Activity") or "")),
    )
    fig.update_layout(
        barmode="group",
        bargap=0.35,
        yaxis=dict(
            autorange="reversed",
            categoryorder="array",
            categoryarray=[label(row) for row in ordered],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    if isinstance(project_duration, (int, float)):
        fig.add_vline(
            x=project_duration,
            line_dash="dash",
            line_color=SECONDARY_TEXT,
            annotation_text=f"baseline {project_duration} d",
            annotation_position="top",
        )
    height = max(340, 26 * len(rows) + 150)
    return apply_chart_theme(fig, height=height, x_title="Project day (early schedule)")


def render_overview(
    project: dict[str, Any],
    data: dict[str, Any],
    source_name: str,
    source_path: str,
) -> None:
    """10A.5 Project Intelligence workspace: orientation, not research results.

    Every value shown here comes from the loaded project inputs, the existing
    deterministic engines or the cached 10A.2-B snapshot. Nothing is scanned
    from results/ directories and no research claim is made on this page.
    """
    ov = data["overview"]
    critical = set(data["schedule"]["critical_path"])

    # ---- Global context: which project is loaded right now ----------------
    meta = project.get("project") or {}
    identity = " \u00b7 ".join(
        str(part)
        for part in (meta.get("project_id"), meta.get("project_type"), meta.get("location"))
        if part
    )
    if meta.get("status"):
        identity = f"{identity} \u00b7 status {meta['status']}" if identity else f"status {meta['status']}"
    source_label = (
        f"{source_name} \u2014 uploaded in this session"
        if source_path == "uploaded"
        else f"{source_name} \u2014 bundled project file"
    )
    render_status_banner(
        meta.get("project_name") or "Project name unavailable",
        status="valid" if meta.get("project_name") else "optional",
        title="Loaded project",
        detail=" \u00b7 ".join(part for part in (identity, source_label) if part),
    )

    # ---- Project snapshot -------------------------------------------------
    render_section_header(
        "Project snapshot",
        "Orientation metrics computed by the existing CMIDO engines from the loaded project",
        evidence_state="valid",
        provenance="DER",
        methodology="Absent source values are omitted rather than shown as zero; input facts are marked OBS.",
    )
    kpis = build_overview_kpis(project, data)
    if kpis:
        # Uniform rows of three keep card widths consistent at any count.
        for start in range(0, len(kpis), 3):
            render_kpi_columns(kpis[start : start + 3])
    else:
        render_html(build_empty_state(
            "The loaded project did not provide snapshot metrics.",
            title="No snapshot metrics available",
            hint="Load a valid project JSON to populate duration, activity and material metrics.",
        ))

    # ---- Project context --------------------------------------------------
    render_section_header(
        "Project context",
        "Declared inputs, provenance and horizon of the project being analysed",
        provenance="OBS",
        methodology="Input facts are read from the project JSON; the planned horizon is derived from the declared dates.",
    )
    context_rows = build_project_context_rows(project, source_name, source_path)
    if context_rows:
        render_table(
            pd.DataFrame(context_rows, columns=["Field", "Value"]),
            title="Project input context",
            subtitle="What is being analysed right now",
            caption="Declared project inputs (OBS) plus one derived horizon (DER).",
            provenance="OBS",
        )
    else:
        render_html(build_empty_state(
            "The loaded project declared no context fields.",
            title="No project context available",
            hint="A valid CMIDO project JSON declares identity, dates, calendar and counts.",
        ))

    # ---- Schedule intelligence -------------------------------------------
    render_section_header(
        "Schedule intelligence",
        "Critical path method output for the loaded project",
        evidence_state="valid",
        provenance="DER",
        methodology="Deterministic CPM from the existing scheduling engine: early start/finish and total "
                    "float are engine outputs, never recomputed in the UI.",
    )
    float_rows: list[dict[str, Any]] | None = None
    try:
        float_rows = calculate_total_float(project)
    except Exception as exc:  # noqa: BLE001 - partial state, technical detail stays secondary
        render_status_banner(
            "Timing and total-float detail could not be computed for this project. "
            "Duration, activity counts and criticality remain available above.",
            status="optional",
            title="Partial schedule intelligence",
            diagnostics=f"{type(exc).__name__}: {exc}",
        )
    schedule_rows = build_schedule_rows(data["schedule"]["activities"], float_rows)
    if schedule_rows:
        render_table(
            pd.DataFrame(schedule_rows),
            title="Activity schedule structure",
            subtitle="Duration, early timing, total float and criticality",
            caption=f"{len(schedule_rows)} activities \u00b7 critical path length {len(critical)}",
            provenance="DER",
        )
        if schedule_rows[0].get("Early start (d)") is not None:
            duration_note = (
                " Bars span early start to early finish; the dashed line marks the baseline duration."
                if isinstance(ov.get("project_duration_days"), (int, float))
                else " Bars span early start to early finish."
            )
            render_chart(
                schedule_timeline(schedule_rows, ov.get("project_duration_days")),
                title="Schedule progression & critical path",
                subtitle="Horizontal bars show when each activity is scheduled."
                + duration_note,
                caption="Deterministic CPM output \u2014 provenance DER.",
                provenance="DER",
            )
    else:
        render_html(build_empty_state(
            "The loaded project has no activities, so no schedule structure can be shown.",
            title="No schedule rows",
            hint="Load a project JSON that declares activities and dependencies.",
        ))
    critical_path_banner(data["schedule"]["critical_path"])

    # ---- Project intelligence graph (existing 3D view, unchanged) ---------
    render_section_header(
        "Project intelligence graph",
        "Dependency network with critical-path highlighting \u2014 the structural intelligence view of this project",
        evidence_state="valid",
        provenance="DER",
        methodology="Existing dependency-layout view: graph calculations and semantics are unchanged by this page.",
    )
    render_chart(
        graph_3d(project, critical),
        title="3D project dependency graph",
        subtitle="Rotate, zoom and hover. Diamonds identify critical-path activities; edges are project dependencies.",
        caption="Deterministic CPM output \u2014 provenance DER.",
        provenance="DER",
    )

    # ---- Material & resource intelligence ---------------------------------
    render_section_header(
        "Material & resource intelligence",
        "Quantity demand from the loaded project and the current feasibility context",
        provenance="DER",
        methodology="Demand is aggregated from activity-material links by the existing quantity engine; "
                    "feasibility needs availability inputs supplied on Materials & Resources.",
    )
    material_rows = data["materials"]["materials"]
    if material_rows:
        frame = pd.DataFrame(material_rows)
        rename = {
            "material_id": "Material ID",
            "material_name": "Material",
            "total_quantity": "Total required",
            "unit": "Unit",
        }
        frame = frame[[c for c in rename if c in frame.columns]].rename(columns=rename)
        render_table(
            frame,
            title="Material demand summary",
            subtitle="Total required quantity per material type",
            caption=f"{data['materials']['total_material_types']} material types aggregated from activity-material links.",
            provenance="DER",
        )
    else:
        render_html(build_empty_state(
            "The loaded project declares no material requirements.",
            title="No material demand",
            hint="Add materials and activity-material links to the project JSON to populate demand.",
        ))
    render_html(build_empty_state(
        "Resource feasibility needs availability quantities, which are user inputs collected on "
        "Materials & Resources \u2014 not values this page can derive. Material demand, supplier "
        "registrations, schedule and evidence context above remain available.",
        title="Resource feasibility not evaluated",
        hint="Open Materials & Resources, set availability, and the feasibility engine reports shortage states there.",
        status="optional",
    ))

    # ---- Decision & analytical pipeline -----------------------------------
    render_section_header(
        "Decision & analytical pipeline",
        "Route from project data to decision intelligence in this application",
        methodology="Shows the pipeline shape, not completion: research workspaces RO1\u2013RO3 are planned "
                    "(Phases 10A.7\u201310A.9) and are not presented as complete.",
    )
    render_html(build_flow_diagram([
        "Project Data",
        "Validation",
        "Quantity / Demand",
        "CPM Schedule",
        "Resource / Procurement Feasibility",
        "Scenario / Impact Analysis",
        "Research Evidence",
        "Decision Intelligence",
    ], title="CMIDO analytical pipeline"))

    # ---- Evidence & data status -------------------------------------------
    render_section_header(
        "Evidence & data status",
        "What evidence this application can actually show right now",
        methodology="Artifact counts come from the cached 10A.2-B snapshot; planned workspaces are read "
                    "from the 10A.4 page registry.",
    )
    snapshot_error: str | None = None
    try:
        snapshot_overview = cached_snapshot(str(ROOT)).overview
    except Exception as exc:  # noqa: BLE001 - reported as an honest missing state
        snapshot_overview = None
        snapshot_error = f"{type(exc).__name__}: {exc}"
    evidence_rows, evidence_overall, evidence_note = build_evidence_status(
        snapshot_overview,
        real_world_planned=page_is_planned("real_world_data"),
        ro_workspaces_planned=all(
            page_is_planned(pid) for pid in ("ro1_forecasting", "ro2_uncertainty", "ro3_optimization")
        ),
    )
    planned_bits = []
    if page_is_planned("real_world_data"):
        planned_bits.append(
            f"real-world data ({(page_future_phase('real_world_data') or '').replace('Phase ', '')})"
        )
    if all(page_is_planned(pid) for pid in ("ro1_forecasting", "ro3_optimization")):
        first = (page_future_phase("ro1_forecasting") or "").replace("Phase ", "")
        last = (page_future_phase("ro3_optimization") or "").replace("Phase ", "")
        planned_bits.append(f"RO1\u2013RO3 (Phases {first}\u2013{last})")
    if planned_bits:
        evidence_note = f"{evidence_note} Planned: {'; '.join(planned_bits)}."
    render_html(build_publication_status(
        title="Evidence readiness",
        rows=evidence_rows,
        status=evidence_overall,
        note=evidence_note,
    ))
    if snapshot_error:
        render_status_banner(
            "The dashboard snapshot could not be loaded, so artifact counts are unavailable. "
            "Project data, schedule and material intelligence on this page remain available.",
            status="attention",
            title="Evidence snapshot unavailable",
            diagnostics=snapshot_error,
        )

    # ---- Project status (three layers, never collapsed) --------------------
    render_section_header(
        "Project status",
        "Deterministic state, evidence availability and research-stage availability reported separately",
        methodology="These three layers are never collapsed into one verdict.",
    )
    schedule_state, schedule_message = deterministic_status(data)
    render_status_banner(schedule_message, status=schedule_state, title="Deterministic project state")
    board_overall, board_rows = build_status_board(schedule_state, evidence_overall)
    render_html(build_publication_status(
        title="Status board",
        rows=board_rows,
        status=board_overall,
        note="Rows report each layer separately; planned or input-dependent layers are labelled, not scored.",
    ))


def _render_schedule_workspace(
    project: dict[str, Any],
    data: dict[str, Any],
    source_name: str,
    source_path: str,
) -> None:
    """Schedule & Critical Path workspace.

    Presents deterministic CPM output from the existing scheduling engine:
    forward/backward pass, total float, classification, critical path and
    dependency relationships. No schedule value is computed here.
    """
    ov = data["overview"]
    sched = data["schedule"]
    critical_path = sched["critical_path"]
    critical_set = set(critical_path)

    # ---- Float intelligence from the existing engine --------------------
    float_rows: list[dict[str, Any]] | None = None
    timing_available = False
    try:
        float_rows = calculate_total_float(project)
        timing_available = bool(float_rows) and all(
            row.get("activity_id") in critical_set or True
            for row in float_rows
        )
    except Exception as exc:  # noqa: BLE001 - partial state
        render_status_banner(
            "Total float, early/late dates and dependency detail could not be computed for this project. Duration, activity counts and criticality remain available below.",
            status="optional",
            title="Partial schedule intelligence",
            diagnostics=f"{type(exc).__name__}: {exc}",
        )

    float_by_id: dict[str, dict[str, Any]] = {}
    if timing_available and float_rows:
        float_by_id = {row["activity_id"]: row for row in float_rows}

    # ---- Page header ----------------------------------------------------
    render_page_header(
        "Schedule & Critical Path",
        "Schedule structure, dependency intelligence and project-duration drivers from the existing CPM engine.",
        provenance="DER",
        research_stage="RO1",
    )
    render_html(build_breadcrumb(["CMIDO", "Core", "Schedule & Critical Path"]))
    render_html(page_description("schedule"))

    # ---- Schedule snapshot ---------------------------------------------
    render_section_header(
        "Schedule snapshot",
        "Project-level schedule metrics from the existing CPM calculation.",
        provenance="DER",
        evidence_state="valid",
        methodology="All values are derived by the existing scheduling engine; absent values are omitted, never zeroed.",
    )

    float_values = []
    if timing_available and float_by_id:
        float_values = [row["total_float"] for row in float_by_id.values()]

    zero_float_count = 0
    min_float: float | None = None
    max_float: float | None = None
    if float_values:
        zero_float_count = sum(1 for f in float_values if f == 0)
        min_float = min(float_values)
        max_float = max(float_values)

    snapshot_kpis = [
        {
            "label": "Project duration",
            "value": format_number(ov["project_duration_days"], 0),
            "unit": "d",
            "provenance": "DER",
            "status": "valid",
            "description": "Baseline CPM project duration.",
        },
        {
            "label": "Critical-path duration",
            "value": format_number(ov["critical_path_duration_days"], 0),
            "unit": "d",
            "provenance": "DER",
            "status": "valid",
            "description": "Sum of durations along the critical path.",
        },
        {
            "label": "Total activities",
            "value": format_integer(ov["total_activities"]),
            "provenance": "DER",
            "status": "valid",
            "description": f"{ov['critical_activities']} critical · {ov['non_critical_activities']} non-critical.",
        },
        {
            "label": "Critical activities",
            "value": format_integer(ov["critical_activities"]),
            "provenance": "DER",
            "status": "valid",
            "description": "Activities with zero total float.",
        },
    ]
    if min_float is not None:
        snapshot_kpis.append(
            {
                "label": "Minimum float",
                "value": format_number(min_float, 0),
                "unit": "d",
                "provenance": "DER",
                "status": "attention" if min_float == 0 else "valid",
                "description": "Smallest total float across all activities.",
            }
        )
        snapshot_kpis.append(
            {
                "label": "Maximum float",
                "value": format_number(max_float, 0),
                "unit": "d",
                "provenance": "DER",
                "status": "valid",
                "description": "Largest total float across all activities.",
            }
        )
        snapshot_kpis.append(
            {
                "label": "Zero-float activities",
                "value": format_integer(zero_float_count),
                "provenance": "DER",
                "status": "valid",
                "description": "Activities with no scheduling flexibility.",
            }
        )
    render_kpi_columns(snapshot_kpis)

    # ---- Schedule timeline ---------------------------------------------
    if timing_available and float_by_id:
        timeline_rows = []
        for row in float_by_id.values():
            critical = row["activity_id"] in critical_set
            timeline_rows.append(
                {
                    "Activity": row["activity_id"],
                    "Name": row.get("activity_name", ""),
                    "Early start (d)": row.get("es"),
                    "Early finish (d)": row.get("ef"),
                    "Duration (d)": row.get("duration_days"),
                    "Critical": "YES" if critical else "NO",
                }
            )
        render_section_header(
            "Schedule timeline",
            "When each activity is scheduled in the early schedule, with critical-path highlighting.",
            provenance="DER",
            evidence_state="valid",
            methodology="Bars span early start to early finish; the dashed line marks the baseline project duration.",
        )
        if timeline_rows:
            render_chart(
                schedule_timeline(timeline_rows, ov["project_duration_days"]),
                title="Schedule progression & critical path",
                subtitle="Horizontal bars show when each activity is scheduled in the early schedule.",
                caption=f"{len(timeline_rows)} activities · critical path length {len(critical_path)} · provenance DER.",
                provenance="DER",
            )
    else:
        render_html(build_empty_state(
            "Timing detail (early start, early finish, total float) is not available for this project.",
            title="No schedule timeline available",
            hint="The CPM forward/backward pass did not return timing for every activity.",
            status="optional",
        ))

    # ---- Critical path -------------------------------------------------
    render_section_header(
        "Critical path",
        "The sequence of activities that currently determines project completion.",
        provenance="DER",
        evidence_state="valid",
        methodology="The critical path is the longest zero-float chain from the existing CPM engine; it is not recomputed in the UI.",
    )
    if critical_path:
        path_with_durations: list[dict[str, Any]] = []
        total_path_duration = 0
        for act_id in critical_path:
            act = next((a for a in sched["activities"] if a["activity_id"] == act_id), None)
            if act is None:
                continue
            dur = act.get("duration_days", 0)
            es = float_by_id.get(act_id, {}).get("es")
            ef = float_by_id.get(act_id, {}).get("ef")
            tf = float_by_id.get(act_id, {}).get("total_float")
            total_path_duration += dur
            path_with_durations.append(
                {
                    "Order": len(path_with_durations) + 1,
                    "Activity": act_id,
                    "Activity name": act.get("activity_name", ""),
                    "Duration (d)": dur,
                    "Early start (d)": es if es is not None else None,
                    "Early finish (d)": ef if ef is not None else None,
                    "Total float (d)": tf if tf is not None else None,
                    "Critical": "YES",
                }
            )
        if path_with_durations:
            render_table(
                pd.DataFrame(path_with_durations),
                title="Critical path sequence",
                subtitle="Ordered activities that determine project completion.",
                caption=f"Critical path: {' → '.join(critical_path)} · total {total_path_duration} d · provenance DER.",
                provenance="DER",
            )
            render_html(build_methodology_card(
                "Critical-path interpretation",
                "The activities above form the longest zero-float chain in the project. Any delay to one of these activities delays the entire project by the same amount, unless subsequent activities have float to absorb it.",
                key_metric=format_number(total_path_duration, 0),
                key_metric_label="Critical-path duration",
                key_metric_unit="d",
                provenance="DER",
                evidence_state="valid",
            ))
    else:
        render_html(build_empty_state(
            "No critical path could be derived for this project.",
            title="No critical path",
            hint="A critical path requires zero-float activities and a connected dependency chain.",
            status="optional",
        ))

    # ---- Float intelligence --------------------------------------------
    if timing_available and float_by_id:
        render_section_header(
            "Float intelligence",
            "Total float and early/late date windows for every activity.",
            provenance="DER",
            evidence_state="valid",
            methodology="Total float = LS - ES = LF - EF from the existing backward pass. Values are presented as computed, without invented risk bands.",
        )
        float_display: list[dict[str, Any]] = []
        for row in float_by_id.values():
            critical = row["activity_id"] in critical_set
            float_display.append(
                {
                    "Activity": row["activity_id"],
                    "Activity name": row.get("activity_name", ""),
                    "Duration (d)": row.get("duration_days"),
                    "Early start (d)": row.get("es"),
                    "Early finish (d)": row.get("ef"),
                    "Late start (d)": row.get("ls"),
                    "Late finish (d)": row.get("lf"),
                    "Total float (d)": row.get("total_float"),
                    "Critical": "YES" if critical else "NO",
                }
            )
        if float_display:
            render_table(
                pd.DataFrame(float_display),
                title="Activity float & date windows",
                subtitle="Early and late dates plus total float per activity.",
                caption=f"{len(float_display)} activities · zero-float: {zero_float_count} · provenance DER.",
                provenance="DER",
            )

            # Float concentration interpretation
            if zero_float_count == len(float_display):
                render_html(build_methodology_card(
                    "Float concentration",
                    "Every activity in this project has zero total float, so the entire schedule is critical.",
                    key_metric=f"{zero_float_count} of {len(float_display)}",
                    key_metric_label="Zero-float activities",
                    provenance="DER",
                    evidence_state="valid",
                ))
            elif zero_float_count == 0:
                render_html(build_methodology_card(
                    "Float concentration",
                    "No activity in this project has zero total float, so no single activity determines project completion on its own.",
                    key_metric="0 of " + str(len(float_display)),
                    key_metric_label="Zero-float activities",
                    provenance="DER",
                    evidence_state="valid",
                ))
            else:
                render_html(build_methodology_card(
                    "Float concentration",
                    f"{zero_float_count} of {len(float_display)} activities carry zero total float and form the critical chain; the remaining {len(float_display) - zero_float_count} have scheduling flexibility.",
                    key_metric=f"{zero_float_count} of {len(float_display)}",
                    key_metric_label="Zero-float activities",
                    provenance="DER",
                    evidence_state="valid",
                    detail=f"Minimum float: {min_float} d · Maximum float: {max_float} d.",
                ))
    else:
        render_html(build_empty_state(
            "Float and late-date information is not available for this project.",
            title="No float intelligence available",
            hint="Float requires a completed backward pass over the project dependencies.",
            status="optional",
        ))

    # ---- Dependency intelligence ----------------------------------------
    if timing_available and float_by_id:
        render_section_header(
            "Dependency intelligence",
            "Predecessor and successor relationships between activities.",
            provenance="DER",
            evidence_state="valid",
            methodology="Relationships come from the project dependency list; the table presents them as declared, not inferred.",
        )
        dep_rows: list[dict[str, Any]] = []
        for row in float_by_id.values():
            preds = row.get("predecessors") or []
            succs = row.get("successors") or []
            if preds or succs:
                dep_rows.append(
                    {
                        "Activity": row["activity_id"],
                        "Activity name": row.get("activity_name", ""),
                        "Predecessors": " → ".join(preds) if preds else "—",
                        "Successors": " → ".join(succs) if succs else "—",
                        "Critical": "YES" if row["activity_id"] in critical_set else "NO",
                    }
                )
        if dep_rows:
            render_table(
                pd.DataFrame(dep_rows),
                title="Activity dependencies",
                subtitle="Predecessor and successor chains for each activity.",
                caption=f"{len(dep_rows)} activities with dependencies · provenance DER.",
                provenance="DER",
            )
        else:
            render_html(build_empty_state(
                "No dependency relationships are declared for this project.",
                title="No dependencies",
                hint="Add dependencies to the project JSON to populate the dependency view.",
                status="optional",
            ))
    else:
        render_html(build_empty_state(
            "Dependency detail is not available because timing could not be computed.",
            title="No dependency intelligence",
            hint="Dependency view requires a completed CPM forward/backward pass.",
            status="optional",
        ))

    # ---- Full activity table -------------------------------------------
    render_section_header(
        "Activity schedule table",
        "Complete activity schedule with timing, float and criticality.",
        provenance="DER",
        evidence_state="valid",
        methodology="One row per activity. Columns are shown only when the engine supplies the underlying value.",
    )
    if timing_available and float_by_id:
        full_rows: list[dict[str, Any]] = []
        for row in float_by_id.values():
            critical = row["activity_id"] in critical_set
            full_rows.append(
                {
                    "ID": row["activity_id"],
                    "Activity": row.get("activity_name", ""),
                    "Duration (d)": row.get("duration_days"),
                    "Early start (d)": row.get("es"),
                    "Early finish (d)": row.get("ef"),
                    "Late start (d)": row.get("ls"),
                    "Late finish (d)": row.get("lf"),
                    "Total float (d)": row.get("total_float"),
                    "Critical": "YES" if critical else "NO",
                    "Predecessors": " → ".join(row.get("predecessors") or []),
                    "Successors": " → ".join(row.get("successors") or []),
                }
            )
        if full_rows:
            render_table(
                pd.DataFrame(full_rows),
                title="All activities",
                subtitle="Duration, early/late dates, total float, criticality and dependencies.",
                caption=f"{len(full_rows)} activities · critical path length {len(critical_path)} · provenance DER.",
                provenance="DER",
            )
    else:
        simple_rows = []
        for act in sched["activities"]:
            critical = act["activity_id"] in critical_set
            simple_rows.append(
                {
                    "ID": act["activity_id"],
                    "Activity": act.get("activity_name", ""),
                    "Duration (d)": act.get("duration_days"),
                    "Critical": "YES" if critical else "NO",
                }
            )
        if simple_rows:
            render_table(
                pd.DataFrame(simple_rows),
                title="All activities (timing unavailable)",
                subtitle="Activity ID, name, duration and criticality only.",
                caption=f"{len(simple_rows)} activities · timing detail not available · provenance DER.",
                provenance="DER",
            )


def _render_materials_workspace(
    project: dict[str, Any],
    data: dict[str, Any],
    source_name: str,
    source_path: str,
) -> None:
    """Materials & Resources workspace.

    Presents material demand from the existing quantity engine and deterministic
    feasibility from the existing resource-shortage engine. Availability is a
    user input collected on this page; the engine reports shortage state, never
    the reverse.
    """
    ov = data["overview"]

    # ---- Gather existing material and supplier context --------------------
    materials_list = project.get("materials", [])
    activity_materials = project.get("activity_materials", [])
    suppliers = project.get("suppliers", [])
    supplier_materials = project.get("supplier_materials", [])

    materials_by_id = {m["material_id"]: m for m in materials_list}
    supplier_by_id = {s["supplier_id"]: s for s in suppliers}
    supplier_mat_by_mat: dict[str, list[dict[str, Any]]] = {}
    for sm in supplier_materials:
        supplier_mat_by_mat.setdefault(sm["material_id"], []).append(sm)

    # ---- Page header ---------------------------------------------------
    render_page_header(
        "Materials & Resources",
        "Material demand, availability and deterministic feasibility context from the existing CMIDO engines.",
        provenance="DER",
    )
    render_html(build_breadcrumb(["CMIDO", "Core", "Materials & Resources"]))
    render_html(page_description("materials"))

    # ---- Resource snapshot ---------------------------------------------
    render_section_header(
        "Resource snapshot",
        "Material types, demand and feasibility context from the loaded project.",
        provenance="DER",
        evidence_state="valid",
        methodology="Material demand is aggregated from activity-material links by the existing quantity engine. Feasibility needs availability inputs set below.",
    )

    total_material_types = ov.get("total_material_types", 0)
    snapshot_kpis = [
        {
            "label": "Material types",
            "value": format_integer(total_material_types),
            "provenance": "DER",
            "status": "valid",
            "description": "Distinct material types tracked in quantity demand.",
        },
        {
            "label": "Suppliers registered",
            "value": format_integer(len(suppliers)),
            "provenance": "OBS",
            "status": "valid",
            "description": "Supplier declarations in project inputs.",
        },
        {
            "label": "Supplier-material links",
            "value": format_integer(len(supplier_materials)),
            "provenance": "OBS",
            "status": "valid",
            "description": "Declared supplier-c material relationships.",
        },
    ]
    render_kpi_columns(snapshot_kpis)

    # ---- Availability inputs -------------------------------------------
    render_section_header(
        "Availability inputs",
        "Set the currently available quantity for each material. The feasibility engine recomputes shortage state from these values.",
        provenance="OBS",
        evidence_state="valid",
        methodology="Availability is a user input here; the engine compares it against required quantity and reports shortage state. No availability is assumed.",
    )

    if not materials_list:
        render_html(build_empty_state(
            "The loaded project declares no materials, so no availability or feasibility can be evaluated.",
            title="No materials declared",
            hint="Add materials and activity-material links to the project JSON.",
            status="empty",
        ))
        return

    available: dict[str, float] = {}
    cols = st.columns(min(4, max(1, len(materials_list))))
    for i, material in enumerate(materials_list):
        with cols[i % len(cols)]:
            available[material["material_id"]] = st.number_input(
                f"{material['material_name']} ({material['unit']})",
                min_value=0.0,
                value=1000.0,
                step=50.0,
                key="inventory_" + material["material_id"],
                help=f"Currently available quantity of {material['material_name']}.",
            )

    # ---- Material demand -----------------------------------------------
    render_section_header(
        "Material demand",
        "Total required quantity per material, aggregated from activity-material links.",
        provenance="DER",
        evidence_state="valid",
        methodology="Demand is aggregated by the existing quantity engine from activity-material links; units come from the project inputs.",
    )

    demand_by_mat = data["materials"]["materials"]
    demand_rows: list[dict[str, Any]] = []
    for req in demand_by_mat:
        mid = req["material_id"]
        mat = materials_by_id.get(mid, {})
        demand_rows.append(
            {
                "Material": req.get("material_name", mat.get("material_name", mid)),
                "Material ID": mid,
                "Required quantity": req.get("total_quantity"),
                "Unit": req.get("unit", mat.get("unit", "")),
                "Activities using": _activity_count_for_material(mid, activity_materials, project),
                "Required by": " · ".join(
                    _activity_names_for_material(mid, activity_materials, project)
                ) or "—",
            }
        )
    if demand_rows:
        render_table(
            pd.DataFrame(demand_rows),
            title="Material demand summary",
            subtitle="Total required quantity per material and the activities that use it.",
            caption=f"{len(demand_rows)} material types aggregated from activity-material links · provenance DER.",
            provenance="DER",
        )
    else:
        render_html(build_empty_state(
            "No material demand could be aggregated from this project.",
            title="No material demand",
            hint="Add activity-material links to the project JSON.",
            status="empty",
        ))

    # ---- Resource feasibility -------------------------------------------
    render_section_header(
        "Material availability & feasibility",
        "Required vs available quantity and deterministic shortage state per material.",
        provenance="DER",
        evidence_state="valid",
        methodology="Feasibility is computed by the existing resource-shortage engine: required quantity is compared against the availability you set above. NOT_ANALYZED is never treated as feasible.",
    )

    resource_data = _build_materials_feasibility(project, available)
    summary = resource_data["summary"]
    resources = resource_data["resources"]

    feas = summary.get("feasible_resources", 0)
    total = summary.get("total_resources", 0)
    short = summary.get("shortage_resources", 0)

    render_kpi_columns([
        {
            "label": "Materials analyzed",
            "value": format_integer(total),
            "provenance": "DER",
            "status": "valid",
            "description": "Materials with demand in this project.",
        },
        {
            "label": "Feasible",
            "value": format_feasibility(feas, total) if total else "—",
            "provenance": "DER",
            "status": "valid" if short == 0 else "attention",
            "description": "Materials with no shortage detected.",
        },
        {
            "label": "Shortage",
            "value": format_integer(short),
            "provenance": "DER",
            "status": "attention" if short else "valid",
            "description": "Materials where available < required.",
        },
    ])

    if resources:
        feas_rows: list[dict[str, Any]] = []
        for r in resources:
            req_qty = r.get("required_quantity", 0)
            short_qty = r.get("shortage_quantity", 0)
            short_pct = format_shortage_pct(short_qty, req_qty) if req_qty else "—"
            feas_rows.append(
                {
                    "Material": r.get("resource_name", r.get("resource_id", "")),
                    "Material ID": r.get("resource_id", ""),
                    "Unit": r.get("unit", ""),
                    "Required quantity": req_qty,
                    "Available quantity": r.get("available_quantity", 0),
                    "Shortage quantity": short_qty,
                    "Shortage %": short_pct,
                    "Status": _status_label(r.get("status")),
                    "Affected activities": _affected_activity_names(r.get("affected_activities", [])),
                }
            )
        render_table(
            pd.DataFrame(feas_rows),
            title="Material feasibility detail",
            subtitle="Required, available, shortage and deterministic status per material.",
            caption=f"{len(feas_rows)} materials analyzed · availability is a user input · provenance DER.",
            provenance="DER",
        )

        # Shortage intelligence — only when actual shortages exist
        shortage_rows = [r for r in resources if r.get("status") == "SHORTAGE"]
        if shortage_rows:
            render_section_header(
                "Shortage intelligence",
                "Materials where available quantity is below required quantity.",
                provenance="DER",
                evidence_state="attention",
                methodology="A shortage is reported only when the engine compares required against available and finds a deficit. It is not a risk claim.",
            )
            for s in shortage_rows:
                req_qty = s.get("required_quantity", 0)
                avail_qty = s.get("available_quantity", 0)
                short_qty = s.get("shortage_quantity", 0)
                short_pct = format_shortage_pct(short_qty, req_qty) if req_qty else "—"
                affected = s.get("affected_activities", [])
                render_html(build_methodology_card(
                    f"Shortage: {s.get('resource_name', s.get('resource_id', ''))}",
                    f"Required {req_qty} {s.get('unit', '')}; {avail_qty} available; shortage {short_qty} {s.get('unit', '')} ({short_pct}).",
                    key_metric=format_number(short_qty, 0),
                    key_metric_label="Shortage quantity",
                    key_metric_unit=s.get("unit", ""),
                    provenance="DER",
                    evidence_state="attention",
                    detail="Affected activity" + ("ies" if len(affected) != 1 else "") + ": " + (", ".join(a.get("activity_name", a.get("activity_id", "")) for a in affected) or "none"),
                ))
        else:
            render_html(build_empty_state(
                "No shortages detected with the availability set above.",
                title="No shortages",
                hint="Every material's available quantity meets or exceeds its required quantity.",
                status="valid",
            ))
    else:
        render_html(build_empty_state(
            "No material feasibility could be evaluated for this project.",
            title="No feasibility data",
            hint="Add materials and activity-material links to the project JSON.",
            status="empty",
        ))

    # ---- Supplier context -----------------------------------------------
    if supplier_materials:
        render_section_header(
            "Supplier context",
            "Declared suppliers, supplied materials and capacity context from project inputs.",
            provenance="OBS",
            evidence_state="valid",
            methodology="Supplier declarations are project inputs (OBS). This page presents them as context; supplier selection and optimisation are deferred to later decision work.",
        )
        supplier_rows: list[dict[str, Any]] = []
        for sm in supplier_materials:
            sup = supplier_by_id.get(sm["supplier_id"], {})
            mat = materials_by_id.get(sm["material_id"], {})
            supplier_rows.append(
                {
                    "Supplier": sup.get("supplier_name", sm["supplier_id"]),
                    "Supplier ID": sm["supplier_id"],
                    "Material": mat.get("material_name", sm["material_id"]),
                    "Material ID": sm["material_id"],
                    "Unit price": sm.get("unit_price"),
                    "Capacity": sm.get("capacity"),
                    "Lead time (d)": sm.get("lead_time_days"),
                    "Min order qty": sm.get("minimum_order_quantity"),
                    "Location": sup.get("location", "—") or "—",
                }
            )
        if supplier_rows:
            render_table(
                pd.DataFrame(supplier_rows),
                title="Supplier-material declarations",
                subtitle="Declared suppliers, the materials they supply and their capacity context.",
                caption=f"{len(supplier_rows)} supplier-material links declared in project inputs · provenance OBS.",
                provenance="OBS",
            )

            # Supplier summary per material
            render_section_header(
                "Supplier coverage by material",
                "Which declared suppliers cover each material in the project.",
                provenance="OBS",
                evidence_state="valid",
            )
            coverage_rows: list[dict[str, Any]] = []
            for req in demand_by_mat:
                mid = req["material_id"]
                sms = supplier_mat_by_mat.get(mid, [])
                mat = materials_by_id.get(mid, {})
                if sms:
                    coverage_rows.append(
                        {
                            "Material": mat.get("material_name", mid),
                            "Material ID": mid,
                            "Suppliers": " · ".join(s.get("supplier_name", s["supplier_id"]) for s in sms),
                            "Supplier count": len(sms),
                            "Total capacity": sum(s.get("capacity", 0) for s in sms),
                            "Shortest lead time (d)": min((s.get("lead_time_days", 0) for s in sms), default=0),
                            "Coverage": "Declared" if sms else "None declared",
                        }
                    )
                else:
                    coverage_rows.append(
                        {
                            "Material": mat.get("material_name", mid),
                            "Material ID": mid,
                            "Suppliers": "—",
                            "Supplier count": 0,
                            "Total capacity": 0,
                            "Shortest lead time (d)": 0,
                            "Coverage": "None declared",
                        }
                    )
            render_table(
                pd.DataFrame(coverage_rows),
                title="Material supplier coverage",
                subtitle="Declared supplier coverage for each material in demand.",
                caption=f"{len(coverage_rows)} materials · supplier data from project inputs · provenance OBS.",
                provenance="OBS",
            )
    else:
        render_html(build_empty_state(
            "No supplier declarations are present in this project.",
            title="No supplier context",
            hint="Supplier declarations are optional project inputs. Add suppliers and supplier-material links to populate this section.",
            status="optional",
        ))

    # ---- Feasibility interpretation -------------------------------------
    render_section_header(
        "Feasibility interpretation",
        "What the current availability state implies about material feasibility.",
        provenance="DER",
        evidence_state="valid",
        methodology="Interpretation is limited to what the deterministic shortage engine reports: feasible, shortage, or not analyzed. No probabilistic or optimisation claim is made here.",
    )
    if total == 0:
        render_html(build_empty_state(
            "No materials were analyzed, so feasibility cannot be interpreted.",
            title="No materials analyzed",
            status="empty",
        ))
    elif short == 0 and total > 0:
        render_html(build_methodology_card(
            "Current feasibility",
            f"All {total} materials analyzed are feasible with the availability set above: required quantity is met or exceeded for every material.",
            key_metric=f"{total} of {total}",
            key_metric_label="Feasible materials",
            provenance="DER",
            evidence_state="valid",
        ))
    elif short > 0:
        render_html(build_methodology_card(
            "Current feasibility",
            f"{short} of {total} materials analyzed have a shortage with the availability set above. Adjust availability inputs to explore feasible states.",
            key_metric=f"{short} of {total}",
            key_metric_label="Materials with shortage",
            provenance="DER",
            evidence_state="attention",
            detail=f"{total - short} of {total} materials are feasible.",
        ))


def _build_materials_feasibility(
    project: dict[str, Any],
    available: dict[str, float],
) -> dict[str, Any]:
    """Build material feasibility rows using the existing resource dashboard engine.

    This is a presentation adapter: it calls ``build_resource_dashboard`` and
    reshapes its output for the materials workspace. No feasibility logic lives here.
    """
    try:
        resource = build_resource_dashboard(project, available)
    except Exception as exc:  # noqa: BLE001 - report honestly
        return {
            "summary": {
                "total_resources": 0,
                "feasible_resources": 0,
                "shortage_resources": 0,
            },
            "resources": [],
            "_error": f"{type(exc).__name__}: {exc}",
        }
    return resource


def _activity_count_for_material(
    material_id: str,
    activity_materials: list[dict[str, Any]],
    project: dict[str, Any],
) -> int:
    activity_by_id = {a["activity_id"]: a for a in project.get("activities", [])}
    ids = {item["activity_id"] for item in activity_materials if item.get("material_id") == material_id}
    return len(ids)


def _activity_names_for_material(
    material_id: str,
    activity_materials: list[dict[str, Any]],
    project: dict[str, Any],
) -> list[str]:
    activity_by_id = {a["activity_id"]: a for a in project.get("activities", [])}
    ids = sorted(
        {item["activity_id"] for item in activity_materials if item.get("material_id") == material_id}
    )
    return [activity_by_id.get(aid, {}).get("activity_name", aid) for aid in ids]


def _affected_activity_names(affected: list[dict[str, Any]]) -> str:
    if not affected:
        return "—"
    return ", ".join(a.get("activity_name", a.get("activity_id", "")) for a in affected)


def _status_label(status: Any) -> str:
    s = str(status or "").upper()
    return {
        "FEASIBLE": "FEASIBLE",
        "SHORTAGE": "SHORTAGE",
        "NOT_ANALYZED": "NOT ANALYZED",
    }.get(s, s or "UNKNOWN")


with st.sidebar:
    st.header("🎛️ Control Center")
    render_html(build_breadcrumb(["CMIDO", "Control Center"]))
    uploaded = st.file_uploader("Load project JSON", type=["json"])
    st.divider()
    page = render_sidebar_navigation()
    st.divider()
    render_html(build_provenance_badge("DER"))
    st.caption(
        "The UI calls the existing deterministic CMIDO engines. It visualizes results "
        "and executes controlled scenarios; it does not replace the research logic."
    )

render_app_header()
render_nav_legend()
render_html(build_nav_breadcrumb(page))
render_page_header(
    page_title(page),
    page_description(page) or "Interactive construction schedule, resource, procurement, uncertainty and research-evidence command center.",
    research_stage=page_research_stage(page),
    provenance=page_provenance(page),
)

try:
    project, source_name, source_path = load_project(uploaded)
    data = build_dashboard_data(project)
except Exception as exc:  # noqa: BLE001 - surfaced as a designed error state
    render_error_state(
        "Project data unavailable",
        description="The selected project file could not be read. "
                    "Upload a valid CMIDO project JSON or restore the default demo project.",
        diagnostics=f"{type(exc).__name__}: {exc}",
    )
    st.stop()

# Planned pages render an honest placeholder panel and stop inside the
# helper; available pages fall through to the dispatch below.
render_future_page_panel(page)

ov = data["overview"]
critical = set(data["schedule"]["critical_path"])

# The sidebar resolves a stable page id; the legacy dispatch branches on
# route titles, so resolve the route once before the chain.
route = legacy_route_for(page)

if route == "Overview":
    render_overview(project, data, source_name, source_path)

elif route == "Schedule":
    _render_schedule_workspace(project, data, source_name, source_path)

elif route == "Materials & Resources":
    _render_materials_workspace(project, data, source_name, source_path)

elif route == "RO1 · Forecasting":
    # 10A.7 — presentation only: registered RO1 artifacts flow through the
    # 10A.2-B snapshot contract. No model is trained and no metric recomputed.
    try:
        ro1_evidence = cached_snapshot(str(ROOT)).ro1
    except Exception as exc:  # noqa: BLE001 - surfaced as an honest missing state
        render_error_state(
            "RO1 evidence unavailable",
            description=(
                "The validated repository snapshot could not be loaded, so no "
                "forecasting evidence is shown. Nothing is computed in its place."
            ),
            diagnostics=f"{type(exc).__name__}: {exc}",
        )
        ro1_evidence = None
    if ro1_evidence is not None:
        for block in ro1_workspace.build_page_content(ro1_evidence):
            render_section_block(block)

elif route == "RO2 · Uncertainty":
    # 10A.8 — presentation only: registered RO2 artifacts flow through the
    # 10A.2-B snapshot contract. No simulation is run and no metric recomputed.
    try:
        ro2_evidence = cached_snapshot(str(ROOT)).ro2
    except Exception as exc:  # noqa: BLE001 - surfaced as an honest missing state
        render_error_state(
            "RO2 evidence unavailable",
            description=(
                "The validated repository snapshot could not be loaded, so no "
                "uncertainty-propagation evidence is shown. Nothing is computed in its place."
            ),
            diagnostics=f"{type(exc).__name__}: {exc}",
        )
        ro2_evidence = None
    if ro2_evidence is not None:
        for block in ro2_workspace.build_page_content(ro2_evidence):
            render_section_block(block)

elif route == "Risk & Scenarios":
    render_section_header(
        "⚠️ Deterministic Risk & Delay Lab",
        "Inject a delay into a single activity and observe the deterministic schedule response.",
        provenance="SCN",
        evidence_state="valid",
        methodology="Method: single-activity delay injection through the schedule-impact engine. "
                     "Scenario outputs are scenario-generated (SCN), not observed.",
    )
    ids = [a["activity_id"] for a in project.get("activities", [])]
    activity = st.selectbox("Activity to stress", ids)
    delay = st.slider("Injected delay (days)", 0, 30, 3)
    if st.button("▶ Run scenario", type="primary", use_container_width=True):
        try:
            result = analyze_schedule_impact(project, activity, delay)
            render_kpi_columns([
                {"label": "Baseline", "value": format_number(result["baseline_project_duration"], 0), "unit": "d", "provenance": "DER"},
                {"label": "Scenario", "value": format_number(result["scenario_project_duration"], 0), "unit": "d", "provenance": "SCN"},
                {"label": "Project delay", "value": format_number(result["project_delay_days"], 1), "unit": "d", "provenance": "SCN", "status": "attention" if result["project_delay_days"] else "valid"},
                {"label": "Critical path changed", "value": "YES" if result["critical_path_changed"] else "NO", "provenance": "DER"},
            ])
            render_html(build_methodology_card(
                "Scenario interpretation",
                "Critical path before and after the injected delay.",
                key_metric=format_days(result["project_delay_days"]),
                key_metric_label="Project delay",
                evidence_state="valid",
                provenance="SCN",
                detail="Before: " + " → ".join(result["critical_path_before"]) + "\n\nAfter: " + " → ".join(result["critical_path_after"]),
            ))
            render_table(
                pd.DataFrame(result["affected_activities"]),
                title="Affected activities",
                subtitle="Activities whose earliest/latest dates respond to the injected delay.",
                provenance="SCN",
            )
        except Exception as exc:  # noqa: BLE001 - technical detail kept secondary
            render_error_state(
                "Scenario could not be completed",
                description="The schedule-impact engine did not return a result for this configuration. "
                            "Adjust the activity or delay level and run the scenario again.",
                diagnostics=f"{type(exc).__name__}: {exc}",
            )
    with st.expander("Show empty risk context"):
        context = build_uncertainty_context(project, [])
        st.json({"baseline": context["baseline"], "risk_summary": context["risk_summary"], "project_impact": context["project_impact"]})
        render_html(build_empty_state(
            "No demand samples were supplied, so the uncertainty context is intentionally empty.",
            title="Empty risk context",
            hint="This is the expected baseline behaviour of the CMIDO uncertainty context builder.",
        ))

elif route == "Experiment Lab":
    render_section_header(
        "🧪 Controlled Experiment Lab",
        "Deterministic CMIDO scenarios are executed through the real schedule-impact engine; "
        "experiment evidence is kept traceable to the selected configuration and seed.",
        research_stage="RO3",
        provenance="SCN",
        methodology="Method: deterministic scenario grid evaluated by the schedule-impact engine. "
                     "Statistical summaries are computed afterwards from the executed runs.",
    )
    ids = [a["activity_id"] for a in project.get("activities", [])]
    selected = st.multiselect("Activities", ids, default=ids[:1])
    delays = st.multiselect("Delay levels", list(range(0, 16)), default=[0, 1, 3, 5])
    seed = st.number_input("Experiment seed", min_value=0, value=42, step=1)
    if st.button("🚀 Execute experiment", type="primary", use_container_width=True):
        if not selected or not delays:
            render_status_banner(
                "Select at least one activity and one delay level before executing the experiment.",
                status="attention",
                title="Incomplete experiment configuration",
            )
        elif source_path == "uploaded":
            render_status_banner(
                "Uploaded projects are supported for visualization. Save the dataset locally before "
                "running the real-data experiment runner.",
                status="optional",
                title="Uploaded dataset",
                hint="The real-data experiment runner resolves artifacts from a repository path.",
            )
        else:
            scenarios = [scenario for activity in selected for scenario in build_delay_scenarios(activity, delays)]
            config = ExperimentConfig(
                experiment_id="CMIDO_DASHBOARD_RUN",
                name="CMIDO Dashboard Experiment",
                seed=int(seed),
                parameters={"activities": selected, "delay_levels": delays},
            )
            with st.spinner("Running deterministic CMIDO scenarios..."):
                experiment = run_real_dataset_experiment(source_path, config, scenarios)
            st.session_state["experiment"] = experiment
            st.success(f"Executed {experiment['scenario_count']} scenarios.")
    experiment = st.session_state.get("experiment")
    if experiment:
        frame = result_frame(experiment)
        render_table(
            frame,
            title="Executed scenarios",
            subtitle="One row per evaluated scenario from the current experiment run.",
            caption=f"Seed {experiment['experiment']['seed']} · {experiment['scenario_count']} scenarios",
            provenance="SCN",
            research_stage="RO3",
        )
        if not frame.empty:
            fig = go.Figure()
            for activity_id, group in frame.groupby("Activity"):
                fig.add_trace(go.Scatter(
                    x=group["Input delay (days)"], y=group["Project delay (days)"],
                    mode="lines+markers", name=activity_id,
                ))
            apply_chart_theme(fig, height=420)
            render_chart(
                fig,
                title="Observed project delay vs injected delay",
                subtitle="One line per stressed activity; values are deterministic engine outputs.",
                provenance="SCN",
                research_stage="RO3",
            )
    else:
        render_html(build_empty_state(
            "No experiment has been executed in this session yet.",
            title="Empty experiment registry",
            hint="Configure activities, delay levels and a seed, then execute the experiment.",
        ))

elif route == "Research Evidence":
    render_section_header(
        "📊 Research Evidence",
        "Validated repository research artifacts exposed through the 10A.2-B dashboard contract.",
        research_stage="EVIDENCE",
        evidence_state="valid",
        methodology="Method: every artifact is registered, loaded under its loading policy, "
                     "schema-validated and provenance-tagged before display.",
    )

    # 10A.2-B Validated Repository Snapshot
    snapshot = cached_snapshot(str(ROOT))
    with st.expander("🏛️ Repository Research Artifact Ecosystem (10A.2-B Contract)", expanded=True):
        ov_snap = snapshot.overview
        render_kpi_columns([
            {"label": "Registered artifacts", "value": format_integer(ov_snap.total_artifacts_registered), "evidence_state": "valid"},
            {"label": "Available artifacts", "value": format_integer(ov_snap.total_artifacts_available), "evidence_state": "valid", "provenance": "OBS"},
            {"label": "Missing artifacts", "value": format_integer(ov_snap.total_artifacts_missing), "evidence_state": "missing"},
            {"label": "Invalid artifacts", "value": format_integer(ov_snap.total_artifacts_invalid), "evidence_state": "invalid"},
        ])
        render_html(build_publication_status(
            title="Artifact loading policy compliance",
            note="Experiment-scale scenario ledgers are never loaded by the dashboard.",
            status="valid" if ov_snap.total_artifacts_invalid == 0 else "attention",
            rows=[
                ("Registered artifacts", "valid"),
                ("Loaded artifacts", "valid" if ov_snap.total_artifacts_available else "empty"),
                ("Unavailable artifacts", "attention" if ov_snap.total_artifacts_missing else "valid"),
            ],
        ))

        tab_ro1, tab_ro2, tab_ro3, tab_real, tab_prov = st.tabs([
            "RO1 Forecasting", "RO2 Uncertainty", "RO3 Optimisation", "Real-Data Evidence", "Provenance Audit"
        ])
        with tab_ro1:
            render_section_header("RO1 Forecasting Validation Metrics", research_stage="RO1")
            render_table(
                pd.DataFrame(snapshot.ro1.validation_metrics),
                title="RO1 validation metrics (Publication T1)",
                subtitle="Forecast accuracy and calibration evidence produced by the RO1 engine.",
                provenance="EST",
                research_stage="RO1",
                empty_message="RO1 validation metrics are not available in this checkout.",
            )
        with tab_ro2:
            render_section_header("RO2 Joint Uncertainty Propagation", research_stage="RO2")
            render_table(
                pd.DataFrame(snapshot.ro2.joint_propagation_summary),
                title="RO2 joint propagation summary (Publication T2)",
                subtitle="Demand and supply/lead-time uncertainty propagated jointly.",
                provenance="EST",
                research_stage="RO2",
                uncertainty="distribution",
                empty_message="RO2 joint propagation summary is not available in this checkout.",
            )
            render_table(
                pd.DataFrame(snapshot.ro2.service_risk_curve),
                title="RO2 service-risk curve",
                subtitle="Probability that the service level is violated under the joint model.",
                provenance="EST",
                research_stage="RO2",
                uncertainty="service_risk",
                empty_message="RO2 service-risk curve is not available in this checkout.",
            )
        with tab_ro3:
            render_section_header("RO3 Controller Baseline & Ablation", research_stage="RO3")
            render_table(
                pd.DataFrame(snapshot.ro3.baseline_comparison),
                title="RO3 baseline comparison (Publication T5)",
                subtitle="Controller performance against the documented baselines.",
                provenance="DER",
                research_stage="RO3",
                empty_message="RO3 baseline comparison is not available in this checkout.",
            )
            render_table(
                pd.DataFrame(snapshot.ro3.ablation),
                title="Ablation incremental value (Publication T6)",
                subtitle="Contribution of each controller component.",
                provenance="DER",
                research_stage="ABLATION",
                empty_message="RO3 ablation results are not available in this checkout.",
            )
        with tab_real:
            render_section_header("Real-Data Ingestion Quality", research_stage="REAL_DATA")
            render_html(build_methodology_card(
                "Real-world data evidence",
                "Canonical dataset, PSLIB project audit and experiment stage recorded by the ingestion layer.",
                key_metric=str(snapshot.real_data.canonical_9a.get("dataset_id", "n/a")),
                key_metric_label="9A canonical dataset",
                evidence_state="valid",
                provenance="OBS",
                research_stage="REAL_DATA",
                detail=(
                    f"9B PSLIB project: {snapshot.real_data.pslib_audit.get('project_id', 'n/a')} · "
                    f"9B experiment stage: {snapshot.real_data.experiment_9b.get('stage', 'n/a')}"
                ),
            ))
            st.json({
                "9A_canonical_dataset": snapshot.real_data.canonical_9a.get("dataset_id", "N/A"),
                "9B_pslib_project": snapshot.real_data.pslib_audit.get("project_id", "N/A"),
                "9B_experiment_stage": snapshot.real_data.experiment_9b.get("stage", "N/A"),
            })
        with tab_prov:
            render_section_header("Artifact Provenance & Integrity Registry", research_stage="EVIDENCE")
            prov_data = [
                {
                    "Artifact ID": p.artifact_id,
                    "Source Path": p.source_path,
                    "Class": p.provenance_class.value,
                    "Stage": p.research_stage,
                    "Status": p.status.value,
                    "Schema Status": p.schema_status,
                }
                for p in snapshot.provenance
            ]
            render_table(
                pd.DataFrame(prov_data),
                title="Provenance registry",
                subtitle="Every registered artifact with its provenance class and loading status.",
                caption=f"{len(prov_data)} registered artifacts",
                provenance="OBS",
                research_stage="EVIDENCE",
                empty_message="No artifacts are registered in this checkout.",
            )
            unavailable = [p for p in snapshot.provenance if p.status.value != "AVAILABLE"]
            if unavailable:
                render_section_header("Unavailable evidence", methodology="States are reported in plain language; technical notes stay secondary.")
                for record in unavailable[:12]:
                    render_html(build_artifact_state(
                        record.artifact_id,
                        record.status,
                        stage=record.research_stage,
                        provenance=record.provenance_class.value,
                        diagnostics=record.notes or None,
                    ))
            else:
                render_html(build_empty_state(
                    "All registered artifacts loaded successfully.",
                    title="Complete evidence set",
                ))

    st.divider()
    render_section_header(
        "🧪 Live Interactive Experiment Evidence",
        "Statistical analysis of the experiment executed in this session.",
        research_stage="RO3",
        uncertainty="distribution",
    )
    experiment = st.session_state.get("experiment")
    if not experiment:
        render_html(build_empty_state(
            "Run an experiment in Experiment Lab first.",
            title="No live experiment evidence",
            hint="The statistical panel populates once an experiment has been executed in this session.",
        ))
    else:
        analysis = build_statistical_analysis(experiment["results"], seed=experiment["experiment"]["seed"])
        project_delay = analysis["project_delay"]
        ci = analysis["mean_project_delay_confidence_interval"]
        render_kpi_columns([
            {"label": "Scenarios", "value": format_integer(analysis["scenario_count"]), "provenance": "SCN"},
            {"label": "Mean project delay", "value": format_number(project_delay["mean"]), "unit": "d", "provenance": "EST", "uncertainty": "point"},
            {"label": "Delayed scenarios", "value": format_percent(analysis["delay_rate"]), "provenance": "EST", "uncertainty": "distribution"},
            {"label": "95% bootstrap CI", "value": f"{format_number(ci['lower'])}–{format_number(ci['upper'])} d", "provenance": "EST", "uncertainty": "interval",
             "description": format_interval(ci["lower"], ci["upper"], label="Mean project delay")},
        ])
        st.json(analysis)

elif route == "3D Project Graph":
    render_section_header(
        "🌐 3D Project Graph",
        "Rotate, zoom and hover. Diamonds identify critical-path activities; edges are project dependencies.",
        research_stage="RO1",
        provenance="DER",
        methodology="Deterministic dependency layout with critical-path highlighting.",
    )
    render_chart(
        graph_3d(project, critical),
        title="Project dependency graph",
        subtitle="Interactive 3D view of the deterministic dependency network.",
        provenance="DER",
    )

st.divider()
render_html(build_footer())
