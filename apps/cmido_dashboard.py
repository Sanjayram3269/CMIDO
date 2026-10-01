from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.construction.dashboard import build_dashboard_data
from src.construction.resource_dashboard import build_resource_dashboard
from src.construction.simulation.impact import analyze_schedule_impact
from src.construction.uncertainty.context import build_uncertainty_context
from src.construction.experiments import (
    ExperimentConfig,
    build_delay_scenarios,
    build_experiment_report,
    build_statistical_analysis,
    run_real_dataset_experiment,
)

ROOT = Path(__file__).resolve().parents[1]
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
    .block-container {padding-top:1.2rem;padding-bottom:2.5rem;max-width:1500px;}
    .hero {padding:1.5rem 1.7rem;border-radius:22px;background:linear-gradient(135deg,#0f172a,#1e3a8a);color:white;margin-bottom:1rem;box-shadow:0 18px 45px rgba(15,23,42,.25);}
    .hero h1 {margin:0;font-size:2.35rem;letter-spacing:-.03em;}
    .hero p {margin:.4rem 0 0;color:#cbd5e1;font-size:1rem;}
    .kpi {padding:1rem 1.05rem;border-radius:17px;border:1px solid #e2e8f0;background:white;box-shadow:0 7px 22px rgba(15,23,42,.07);min-height:112px;}
    .kpi .icon {font-size:1.55rem}.kpi .label{color:#64748b;font-size:.8rem;margin-top:.25rem}.kpi .value{font-size:1.55rem;font-weight:760;color:#0f172a;margin-top:.12rem}
    .section {font-size:1.15rem;font-weight:750;margin:1.15rem 0 .55rem;color:#0f172a}
    .flow {display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;padding:1rem;border:1px solid #e2e8f0;border-radius:18px;background:#f8fafc;margin:.6rem 0 1rem}
    .flow-item {padding:.65rem .9rem;border-radius:12px;background:white;border:1px solid #cbd5e1;font-weight:700;box-shadow:0 3px 10px rgba(15,23,42,.05)}
    .flow-arrow {font-size:1.2rem;color:#64748b}
    .small-note {color:#64748b;font-size:.82rem}
    </style>
    """,
    unsafe_allow_html=True,
)


def load_project(uploaded: Any) -> tuple[dict[str, Any], str]:
    if uploaded is not None:
        return json.loads(uploaded.getvalue().decode("utf-8")), uploaded.name
    with DEFAULT_PROJECT.open(encoding="utf-8") as handle:
        return json.load(handle), DEFAULT_PROJECT.name


def kpi(icon: str, label: str, value: str) -> None:
    st.markdown(
        f'<div class="kpi"><div class="icon">{icon}</div><div class="label">{label}</div><div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def flow(items: list[str]) -> None:
    html = []
    for index, item in enumerate(items):
        if index:
            html.append('<span class="flow-arrow">→</span>')
        html.append(f'<span class="flow-item">{item}</span>')
    st.markdown('<div class="flow">' + ''.join(html) + '</div>', unsafe_allow_html=True)


def network_3d(project: dict[str, Any], critical: set[str]) -> go.Figure:
    activities = project.get("activities", [])
    deps = project.get("dependencies", [])
    ids = [a["activity_id"] for a in activities]
    index = {aid: i for i, aid in enumerate(ids)}
    n = max(len(ids), 1)
    x = list(range(n))
    y = [((i * 7) % 11) for i in range(n)]
    z = [a.get("duration_days", a.get("duration", 0)) for a in activities]

    fig = go.Figure()
    edge_x, edge_y, edge_z = [], [], []
    for dep in deps:
        p, s = dep.get("predecessor_id"), dep.get("successor_id")
        if p in index and s in index:
            i, j = index[p], index[s]
            edge_x += [x[i], x[j], None]
            edge_y += [y[i], y[j], None]
            edge_z += [z[i], z[j], None]
    fig.add_trace(go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, mode="lines", line=dict(width=3), hoverinfo="skip", name="Dependencies"))
    colors = ["#ef4444" if aid in critical else "#38bdf8" for aid in ids]
    sizes = [16 if aid in critical else 10 for aid in ids]
    fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="markers+text", text=ids, textposition="top center", marker=dict(size=sizes, color=colors, symbol="diamond"), hovertemplate="<b>%{text}</b><br>Duration: %{z} days<extra></extra>", name="Activities"))
    fig.update_layout(height=610, margin=dict(l=0,r=0,t=15,b=0), scene=dict(xaxis_title="Sequence", yaxis_title="Network position", zaxis_title="Duration (days)"), legend=dict(orientation="h"))
    return fig


def experiment_frame(result: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in result.get("results", []):
        scenario = item["scenario"]
        metrics = item["metrics"]
        rows.append({
            "Activity": scenario["activity_id"],
            "Input delay (days)": scenario["delay_days"],
            "Project delay (days)": metrics["project_delay_days"],
            "Baseline (days)": metrics["baseline_duration_days"],
            "Scenario duration (days)": metrics["scenario_duration_days"],
            "Relative delay": metrics["relative_delay"],
        })
    return pd.DataFrame(rows)


st.markdown('<div class="hero"><h1>🏗️ CMIDO</h1><p>Construction Material Intelligence & Decision Observatory · interactive deterministic decision and research dashboard</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Control Center")
    uploaded = st.file_uploader("Load project JSON", type=["json"])
    page = st.radio(
        "Navigate",
        ["Overview", "Schedule", "Materials & Resources", "Risk & Scenarios", "Experiment Lab", "Research Evidence", "3D Project Graph"],
        index=0,
    )
    st.divider()
    st.caption("UI actions call the existing CMIDO engines. Dashboard code does not replace domain logic or research calculations.")

try:
    project, source_name = load_project(uploaded)
    dashboard = build_dashboard_data(project)
except Exception as exc:
    st.error(f"Could not load project: {exc}")
    st.stop()

ov = dashboard["overview"]
critical = set(dashboard["schedule"]["critical_path"])

if page == "Overview":
    st.subheader(f"{ov['project_name']} · {ov['location']}")
    st.caption(f"Source: {source_name} · Project ID: {ov['project_id']}")
    cols = st.columns(4)
    with cols[0]: kpi("📅", "Project duration", f"{ov['project_duration_days']} days")
    with cols[1]: kpi("⚡", "Critical path", f"{ov['critical_path_duration_days']} days")
    with cols[2]: kpi("🔗", "Activities", str(ov["total_activities"]))
    with cols[3]: kpi("🧱", "Material types", str(ov["total_material_types"]))
    st.markdown('<div class="section">CMIDO decision flow</div>', unsafe_allow_html=True)
    flow(["📦 Materials", "📅 Schedule", "👷 Resources", "⚠️ Risks", "🧪 Experiments", "🎯 Evidence"])
    st.plotly_chart(network_3d(project, critical), use_container_width=True)

elif page == "Schedule":
    st.subheader("📅 Schedule & Critical Path")
    c1, c2, c3 = st.columns(3)
    with c1: kpi("⚡", "Critical activities", str(ov["critical_activities"]))
    with c2: kpi("◻️", "Non-critical activities", str(ov["non_critical_activities"]))
    with c3: kpi("⏱️", "Duration", f"{ov['project_duration_days']} days")
    st.markdown('<div class="section">Activity schedule</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(dashboard["schedule"]["activities"]), use_container_width=True, hide_index=True)
    st.info("Critical path: " + " → ".join(dashboard["schedule"]["critical_path"]))

elif page == "Materials & Resources":
    st.subheader("🧱 Materials & Resource Feasibility")
    materials = project.get("materials", [])
    defaults = {m["material_id"]: 0.0 for m in materials}
    with st.expander("Set available inventory", expanded=True):
        resource_cols = st.columns(min(4, max(1, len(materials))))
        for i, material in enumerate(materials):
            with resource_cols[i % len(resource_cols)]:
                defaults[material["material_id"]] = st.number_input(material["material_name"], min_value=0.0, value=0.0, step=1.0, key=f"avail_{material['material_id']}")
    resource = build_resource_dashboard(project, defaults)
    summary = resource["summary"]
    cols = st.columns(3)
    with cols[0]: kpi("📦", "Resource types", str(summary["total_resources"]))
    with cols[1]: kpi("✅", "Feasible", str(summary["feasible_resources"]))
    with cols[2]: kpi("⚠️", "Shortage", str(summary["shortage_resources"]))
    st.dataframe(pd.DataFrame(resource["resources"]), use_container_width=True, hide_index=True)

elif page == "Risk & Scenarios":
    st.subheader("⚠️ Deterministic Risk & Delay Lab")
    activities = project.get("activities", [])
    ids = [a["activity_id"] for a in activities]
    activity = st.selectbox("Activity", ids)
    delay = st.slider("Scenario delay (days)", 0, 30, 3)
    if st.button("▶ Run scenario", type="primary", use_container_width=True):
        try:
            result = analyze_schedule_impact(project, activity, delay)
            a, b, c = st.columns(3)
            with a: kpi("📅", "Baseline", f"{result['baseline_project_duration']} days")
            with b: kpi("🎯", "Scenario", f"{result['scenario_project_duration']} days")
            with c: kpi("🚨", "Project delay", f"{result['project_delay_days']} days")
            if result["project_delay_days"] > 0:
                st.warning("Project-level delay detected by the deterministic schedule engine.")
            else:
                st.success("Scenario is absorbed without increasing project duration.")
            st.write("**Critical path before:**", " → ".join(result["critical_path_before"]))
            st.write("**Critical path after:**", " → ".join(result["critical_path_after"]))
            st.dataframe(pd.DataFrame(result["affected_activities"]), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Scenario failed: {exc}")
    with st.expander("Risk context preview"):
        context = build_uncertainty_context(project, [])
        st.json({"baseline": context["baseline"], "risk_summary": context["risk_summary"], "project_impact": context["project_impact"]})

elif page == "Experiment Lab":
    st.subheader("🧪 Reproducible Experiment Lab")
    st.caption("Execute deterministic delay scenarios through the real CMIDO evaluator and inspect the resulting experiment metrics.")
    activities = [a["activity_id"] for a in project.get("activities", [])]
    selected = st.multiselect("Activities", activities, default=activities[:1])
    delay_levels = st.multiselect("Delay levels", list(range(0, 11)), default=[0, 1, 3, 5])
    seed = st.number_input("Experiment seed", min_value=0, value=42, step=1)
    if st.button("🚀 Execute experiment", type="primary", use_container_width=True):
        if not selected or not delay_levels:
            st.error("Select at least one activity and one delay level.")
        else:
            scenarios = [scenario for activity_id in selected for scenario in build_delay_scenarios(activity_id, delay_levels)]
            config = ExperimentConfig(experiment_id="CMIDO_DASHBOARD_RUN", name="CMIDO Dashboard Experiment", seed=int(seed), parameters={"activities": selected, "delay_levels": delay_levels})
            with st.spinner("Running deterministic CMIDO scenarios..."):
                experiment = run_real_dataset_experiment(str(DEFAULT_PROJECT), config, scenarios)
            st.session_state["last_experiment"] = experiment
            st.session_state["last_experiment_scenarios"] = scenarios
            st.success(f"Executed {experiment['scenario_count']} scenarios.")

    experiment = st.session_state.get("last_experiment")
    if experiment:
        frame = experiment_frame(experiment)
        st.dataframe(frame, use_container_width=True, hide_index=True)
        if not frame.empty:
            chart = go.Figure()
            for activity_id, group in frame.groupby("Activity"):
                chart.add_trace(go.Scatter(x=group["Input delay (days)"], y=group["Project delay (days)"], mode="lines+markers", name=activity_id))
            chart.update_layout(height=420, xaxis_title="Input delay (days)", yaxis_title="Observed project delay (days)", hovermode="x unified")
            st.plotly_chart(chart, use_container_width=True)

elif page == "Research Evidence":
    st.subheader("📊 Research Evidence & Statistical Summary")
    experiment = st.session_state.get("last_experiment")
    if not experiment:
        st.info("Run an experiment in the Experiment Lab first. This page will then summarize the observed results using the 8K statistical layer.")
    else:
        analysis = build_statistical_analysis(experiment["results"], seed=experiment["experiment"]["seed"])
        project_delay = analysis["project_delay"]
        ci = analysis["mean_project_delay_confidence_interval"]
        cols = st.columns(4)
        with cols[0]: kpi("🧪", "Scenarios", str(analysis["scenario_count"]))
        with cols[1]: kpi("📈", "Mean project delay", f"{project_delay['mean']:.2f} d")
        with cols[2]: kpi("⚠️", "Delayed scenarios", f"{analysis['delay_rate']:.1%}")
        with cols[3]: kpi("📐", "95% bootstrap CI", f"{ci['lower']:.2f}–{ci['upper']:.2f} d")
        st.markdown('<div class="section">Descriptive evidence</div>', unsafe_allow_html=True)
        evidence_frame = pd.DataFrame({
            "Metric": ["Mean", "Median", "Std. deviation", "Minimum", "Q1", "Q3", "Maximum"],
            "Project delay (days)": [project_delay[k] for k in ["mean", "median", "standard_deviation", "minimum", "q1", "q3", "maximum"]],
        })
        st.dataframe(evidence_frame, use_container_width=True, hide_index=True)
        st.markdown('<div class="section">Evidence interpretation</div>', unsafe_allow_html=True)
        st.info("The displayed interval is a deterministic percentile bootstrap interval over the supplied experiment scenarios. It is not a population-level confidence claim and does not establish causality or prediction.")
        with st.expander("Research analysis payload"):
            st.json(analysis)

else:
    st.subheader("🌐 3D Project Dependency Graph")
    st.caption("Red diamonds = critical-path activities · blue diamonds = non-critical activities · lines = dependencies")
    st.plotly_chart(network_3d(project, critical), use_container_width=True)
    st.success("Drag to rotate · scroll to zoom · hover nodes for activity duration.")

st.divider()
st.caption("CMIDO · deterministic construction decision layer · reproducible research dashboard · 8L")
