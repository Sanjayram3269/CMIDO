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

DEFAULT_PROJECT = ROOT / "data" / "projects" / "cmido_demo_project.json"

st.set_page_config(
    page_title="CMIDO | Construction Decision Intelligence",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container{max-width:1550px;padding-top:1rem;padding-bottom:2rem}
    .hero{padding:1.7rem 2rem;border-radius:24px;background:linear-gradient(135deg,#07111f,#123d70 60%,#0f766e);color:white;box-shadow:0 18px 45px rgba(15,23,42,.24);margin-bottom:1rem}
    .hero h1{margin:0;font-size:2.55rem}.hero p{margin:.45rem 0 0;color:#dbeafe}
    .card{padding:1rem 1.1rem;border:1px solid #dbe3ee;border-radius:18px;background:#fff;box-shadow:0 8px 24px rgba(15,23,42,.07)}
    .flow{display:flex;gap:.55rem;flex-wrap:wrap;padding:1rem;border-radius:18px;background:#f8fafc;border:1px solid #e2e8f0;margin-bottom:1rem}.node{padding:.55rem .8rem;border-radius:12px;background:#fff;border:1px solid #cbd5e1;font-weight:700}
    .pill{display:inline-block;padding:.3rem .65rem;border-radius:999px;background:#ecfeff;border:1px solid #a5f3fc;font-weight:700;margin-right:.3rem}
    </style>
    """,
    unsafe_allow_html=True,
)


def load_project(uploaded: Any) -> tuple[dict[str, Any], str, str]:
    if uploaded is not None:
        data = json.loads(uploaded.getvalue().decode("utf-8"))
        return data, uploaded.name, "uploaded"
    return json.loads(DEFAULT_PROJECT.read_text(encoding="utf-8")), DEFAULT_PROJECT.name, str(DEFAULT_PROJECT)


def kpi(icon: str, label: str, value: str) -> None:
    st.markdown(
        f'<div class="card"><div style="font-size:1.45rem">{icon}</div><small>{label}</small><h3 style="margin:.15rem 0">{value}</h3></div>',
        unsafe_allow_html=True,
    )


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
            colorscale=[[0, "#38bdf8"], [1, "#ef4444"]],
            symbol="diamond", showscale=False,
        ), name="Activities"
    ))
    fig.update_layout(
        height=600, margin=dict(l=0, r=0, t=35, b=0),
        scene=dict(
            xaxis_title="Dependency level", yaxis_title="Parallel position",
            zaxis_title="Duration (days)",
            bgcolor="rgba(0,0,0,0)",
        ),
        legend=dict(orientation="h", y=1.02),
    )
    return fig


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


def render_overview(project: dict[str, Any], data: dict[str, Any]) -> None:
    ov = data["overview"]
    critical = set(data["schedule"]["critical_path"])
    st.subheader(f"{ov['project_name']} · {ov['location']}")
    c = st.columns(6)
    values = [
        ("📅", "Project duration", f"{ov['project_duration_days']} d"),
        ("⚡", "Critical path", f"{ov['critical_path_duration_days']} d"),
        ("🔗", "Activities", str(ov['total_activities'])),
        ("🧱", "Material types", str(ov['total_material_types'])),
        ("⚡", "Critical activities", str(ov['critical_activities'])),
        ("🧭", "Status", "ANALYZED"),
    ]
    for col, item in zip(c, values):
        with col:
            kpi(*item)
    st.markdown(
        '<div class="flow">' + ''.join(
            f'<span class="node">{x}</span>' for x in [
                "📦 Materials", "📅 CPM Schedule", "👷 Resources", "⚠️ Risk Context",
                "🧪 Experiments", "📊 Statistical Evidence",
            ]
        ) + "</div>", unsafe_allow_html=True,
    )
    st.plotly_chart(graph_3d(project, critical), use_container_width=True, config={"displaylogo": False})
    st.info("Critical path: " + " → ".join(data["schedule"]["critical_path"]))


st.markdown(
    '<div class="hero"><h1>🏗️ CMIDO Decision Intelligence</h1>'
    '<p>Interactive construction schedule, resource, procurement, uncertainty and research-evidence command center.</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("🎛️ Control Center")
    uploaded = st.file_uploader("Load project JSON", type=["json"])
    page = st.radio(
        "Navigate",
        ["Overview", "Schedule", "Materials & Resources", "Risk & Scenarios", "Experiment Lab", "Research Evidence", "3D Project Graph"],
    )
    st.divider()
    st.caption("The UI calls the existing deterministic CMIDO engines. It visualizes results and executes controlled scenarios; it does not replace the research logic.")

try:
    project, source_name, source_path = load_project(uploaded)
    data = build_dashboard_data(project)
except Exception as exc:
    st.error(f"Could not load project: {exc}")
    st.stop()

ov = data["overview"]
critical = set(data["schedule"]["critical_path"])

if page == "Overview":
    render_overview(project, data)

elif page == "Schedule":
    st.subheader("📅 Schedule & Critical Path")
    c = st.columns(3)
    with c[0]: kpi("⚡", "Critical activities", str(ov["critical_activities"]))
    with c[1]: kpi("◻️", "Non-critical activities", str(ov["non_critical_activities"]))
    with c[2]: kpi("⏱️", "Duration", f"{ov['project_duration_days']} days")
    st.dataframe(pd.DataFrame(data["schedule"]["activities"]), use_container_width=True, hide_index=True)
    st.info("Critical path: " + " → ".join(data["schedule"]["critical_path"]))

elif page == "Materials & Resources":
    st.subheader("🧱 Materials & Resource Feasibility")
    st.caption("Change availability below and the shortage state is recalculated live by the CMIDO resource engine.")
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
    c = st.columns(3)
    with c[0]: kpi("📦", "Resource types", str(summary["total_resources"]))
    with c[1]: kpi("✅", "Feasible", str(summary["feasible_resources"]))
    with c[2]: kpi("⚠️", "Shortage", str(summary["shortage_resources"]))
    st.dataframe(pd.DataFrame(resource["resources"]), use_container_width=True, hide_index=True)

elif page == "Risk & Scenarios":
    st.subheader("⚠️ Deterministic Risk & Delay Lab")
    ids = [a["activity_id"] for a in project.get("activities", [])]
    activity = st.selectbox("Activity to stress", ids)
    delay = st.slider("Injected delay (days)", 0, 30, 3)
    if st.button("▶ Run scenario", type="primary", use_container_width=True):
        try:
            result = analyze_schedule_impact(project, activity, delay)
            c = st.columns(4)
            with c[0]: kpi("📅", "Baseline", f"{result['baseline_project_duration']} d")
            with c[1]: kpi("🎯", "Scenario", f"{result['scenario_project_duration']} d")
            with c[2]: kpi("🚨", "Project delay", f"{result['project_delay_days']} d")
            with c[3]: kpi("🔀", "CP changed", "YES" if result["critical_path_changed"] else "NO")
            st.write("**Before:**", " → ".join(result["critical_path_before"]))
            st.write("**After:**", " → ".join(result["critical_path_after"]))
            st.dataframe(pd.DataFrame(result["affected_activities"]), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Scenario failed: {exc}")
    with st.expander("Show empty risk context"):
        context = build_uncertainty_context(project, [])
        st.json({"baseline": context["baseline"], "risk_summary": context["risk_summary"], "project_impact": context["project_impact"]})

elif page == "Experiment Lab":
    st.subheader("🧪 Controlled Experiment Lab")
    st.caption("Every selected scenario is executed through the real CMIDO schedule-impact evaluator.")
    ids = [a["activity_id"] for a in project.get("activities", [])]
    selected = st.multiselect("Activities", ids, default=ids[:1])
    delays = st.multiselect("Delay levels", list(range(0, 16)), default=[0, 1, 3, 5])
    seed = st.number_input("Experiment seed", min_value=0, value=42, step=1)
    if st.button("🚀 Execute experiment", type="primary", use_container_width=True):
        if not selected or not delays:
            st.error("Select at least one activity and one delay level.")
        elif source_path == "uploaded":
            st.error("Uploaded projects are supported for visualization. Save the dataset locally before running the real-data experiment runner.")
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
        st.dataframe(frame, use_container_width=True, hide_index=True)
        if not frame.empty:
            fig = go.Figure()
            for activity_id, group in frame.groupby("Activity"):
                fig.add_trace(go.Scatter(
                    x=group["Input delay (days)"], y=group["Project delay (days)"],
                    mode="lines+markers", name=activity_id,
                ))
            fig.update_layout(height=420, xaxis_title="Input delay (days)", yaxis_title="Observed project delay (days)")
            st.plotly_chart(fig, use_container_width=True)

elif page == "Research Evidence":
    st.subheader("📊 Research Evidence")
    experiment = st.session_state.get("experiment")
    if not experiment:
        st.info("Run an experiment in Experiment Lab first.")
    else:
        analysis = build_statistical_analysis(experiment["results"], seed=experiment["experiment"]["seed"])
        project_delay = analysis["project_delay"]
        ci = analysis["mean_project_delay_confidence_interval"]
        c = st.columns(4)
        with c[0]: kpi("🧪", "Scenarios", str(analysis["scenario_count"]))
        with c[1]: kpi("📈", "Mean project delay", f"{project_delay['mean']:.2f} d")
        with c[2]: kpi("⚠️", "Delayed scenarios", f"{analysis['delay_rate']:.1%}")
        with c[3]: kpi("📐", "95% bootstrap CI", f"{ci['lower']:.2f}–{ci['upper']:.2f} d")
        st.json(analysis)

elif page == "3D Project Graph":
    st.subheader("🌐 3D Project Graph")
    st.caption("Rotate, zoom and hover. Diamonds identify critical-path activities; edges are project dependencies.")
    st.plotly_chart(graph_3d(project, critical), use_container_width=True, config={"displaylogo": False, "scrollZoom": True})

st.divider()
st.caption("CMIDO · interactive construction decision intelligence · 8L dashboard")
