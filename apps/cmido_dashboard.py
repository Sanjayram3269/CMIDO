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
    build_provenance_badge,
    build_publication_status,
    format_days,
    format_feasibility,
    format_integer,
    format_interval,
    format_number,
    format_percent,
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
    render_section_header,
    render_sidebar_navigation,
    render_status_banner,
    render_table,
)

from src.construction.dashboard_ui.navigation import legacy_route_for


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


def render_overview(project: dict[str, Any], data: dict[str, Any]) -> None:
    ov = data["overview"]
    critical = set(data["schedule"]["critical_path"])
    render_page_header(
        f"{ov['project_name']} · {ov['location']}",
        "Schedule, resource and procurement intelligence computed by the CMIDO engines.",
        context=f"Project duration {format_days(ov['project_duration_days'], 0)} · {format_integer(ov['total_activities'])} activities",
        provenance="DER",
    )
    render_legacy_kpi_row([
        ("📅", "Project duration", format_days(ov["project_duration_days"], 0)),
        ("⚡", "Critical path", format_days(ov["critical_path_duration_days"], 0)),
        ("🔗", "Activities", format_integer(ov["total_activities"])),
        ("🧱", "Material types", format_integer(ov["total_material_types"])),
    ])
    render_legacy_kpi_row([
        ("⚡", "Critical activities", format_integer(ov["critical_activities"])),
        ("🧭", "Analysis status", "ANALYZED"),
    ])
    render_html(build_flow_diagram([
        "📦 Materials",
        "📅 CPM Schedule",
        "👷 Resources",
        "⚠️ Risk Context",
        "🧪 Experiments",
        "📊 Statistical Evidence",
    ], title="Analysis pipeline"))
    render_chart(
        graph_3d(project, critical),
        title="3D project dependency graph",
        subtitle="Diamonds mark critical-path activities; edges are project dependencies.",
        caption="Deterministic CPM output — provenance DER.",
        provenance="DER",
    )
    critical_path_banner(data["schedule"]["critical_path"])


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
    render_overview(project, data)

elif route == "Schedule":
    render_section_header(
        "📅 Schedule & Critical Path",
        "Deterministic CPM forward/backward pass, float and classification.",
        research_stage="RO1",
        provenance="DER",
        evidence_state="valid",
        methodology="Method: critical path method (deterministic). Floats are derived, not estimated.",
    )
    render_kpi_columns([
        {"label": "Critical activities", "value": format_integer(ov["critical_activities"]), "provenance": "DER", "status": "valid"},
        {"label": "Non-critical activities", "value": format_integer(ov["non_critical_activities"]), "provenance": "DER", "status": "valid"},
        {"label": "Project duration", "value": format_number(ov["project_duration_days"], 0), "unit": "d", "provenance": "DER", "status": "valid"},
    ])
    render_table(
        pd.DataFrame(data["schedule"]["activities"]),
        title="Activity schedule",
        subtitle="Forward/backward pass results, total float and critical classification.",
        caption=f"{format_integer(ov['total_activities'])} activities · critical path length "
                f"{format_integer(len(data['schedule']['critical_path']))}",
        provenance="DER",
    )
    critical_path_banner(data["schedule"]["critical_path"])

elif route == "Materials & Resources":
    render_section_header(
        "🧱 Materials & Resource Feasibility",
        "Change availability below and the shortage state is recalculated live by the CMIDO resource engine.",
        provenance="DER",
        evidence_state="valid",
        methodology="Method: deterministic quantity-versus-availability feasibility check.",
    )
    materials = project.get("materials", [])
    available: dict[str, float] = {}
    cols = st.columns(min(4, max(1, len(materials))))
    for i, material in enumerate(materials):
        with cols[i % len(cols)]:
            available[material["material_id"]] = st.number_input(
                material["material_name"], min_value=0.0, value=1000.0, step=50.0,
                key="inventory_" + material["material_id"],
            )
    resource = build_resource_dashboard(project, available)
    summary = resource["summary"]
    render_kpi_columns([
        {"label": "Resource types", "value": format_integer(summary["total_resources"]), "provenance": "DER"},
        {"label": "Feasible", "value": format_feasibility(summary["feasible_resources"], summary["total_resources"]), "provenance": "DER"},
        {"label": "Shortage", "value": format_integer(summary["shortage_resources"]), "provenance": "DER", "status": "attention" if summary["shortage_resources"] else "valid"},
    ])
    render_table(
        pd.DataFrame(resource["resources"]),
        title="Resource feasibility detail",
        subtitle="Required vs available quantity and shortage percentage per resource.",
        caption=f"Shortage share is computed against required quantity ({format_percent(1 - summary['feasible_resources'] / max(1, summary['total_resources']))} of resources short).",
        provenance="DER",
    )

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
