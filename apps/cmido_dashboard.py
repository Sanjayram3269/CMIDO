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
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 18px; background: linear-gradient(135deg,#101827,#172554); color:white; margin-bottom:1rem; box-shadow: 0 12px 35px rgba(15,23,42,.22);}
    .hero h1 {margin:0; font-size:2.2rem;}
    .hero p {margin:.35rem 0 0; color:#cbd5e1;}
    .kpi {padding:1rem; border-radius:16px; border:1px solid #e2e8f0; background:#fff; box-shadow:0 6px 18px rgba(15,23,42,.06); min-height:115px;}
    .kpi .icon {font-size:1.7rem;}
    .kpi .label {color:#64748b; font-size:.82rem; margin-top:.35rem;}
    .kpi .value {font-size:1.65rem; font-weight:750; color:#0f172a;}
    .section {font-size:1.1rem; font-weight:700; margin:1rem 0 .5rem;}
    .status {padding:.65rem .9rem; border-radius:12px; font-weight:700; display:inline-block;}
    .status-good {background:#dcfce7; color:#166534;}
    .status-warn {background:#fef3c7; color:#92400e;}
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


def network_3d(project: dict[str, Any], critical: set[str]) -> go.Figure:
    activities = project["activities"]
    deps = project.get("dependencies", [])
    ids = [a["activity_id"] for a in activities]
    index = {aid: i for i, aid in enumerate(ids)}
    n = max(len(ids), 1)
    x = [i for i in range(n)]
    y = [((i * 7) % 11) for i in range(n)]
    z = [activities[i].get("duration_days", activities[i].get("duration", 0)) for i in range(n)]

    fig = go.Figure()
    edge_x, edge_y, edge_z = [], [], []
    for dep in deps:
        p = dep.get("predecessor_id")
        s = dep.get("successor_id")
        if p in index and s in index:
            i, j = index[p], index[s]
            edge_x += [x[i], x[j], None]
            edge_y += [y[i], y[j], None]
            edge_z += [z[i], z[j], None]
    fig.add_trace(go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, mode="lines", line=dict(width=3), hoverinfo="skip", name="Dependencies"))

    colors = ["#ef4444" if aid in critical else "#38bdf8" for aid in ids]
    sizes = [15 if aid in critical else 9 for aid in ids]
    fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="markers+text", text=ids, textposition="top center", marker=dict(size=sizes, color=colors, symbol="diamond"), hovertemplate="%{text}<br>Duration: %{z} days<extra></extra>", name="Activities"))
    fig.update_layout(height=600, margin=dict(l=0,r=0,t=20,b=0), scene=dict(xaxis_title="Sequence", yaxis_title="Network position", zaxis_title="Duration (days)"), legend=dict(orientation="h"))
    return fig


st.markdown('<div class="hero"><h1>🏗️ CMIDO</h1><p>Construction Material Intelligence & Decision Observatory · interactive project control dashboard</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Control Center")
    uploaded = st.file_uploader("Load project JSON", type=["json"])
    page = st.radio("Navigate", ["Overview", "Schedule", "Materials & Resources", "Risk & Scenarios", "3D Project Graph"], index=0)
    st.divider()
    st.caption("The dashboard calls CMIDO's existing deterministic engines. It does not replace the research pipeline with UI logic.")

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
    st.markdown('<div class="section">Project flow</div>', unsafe_allow_html=True)
    st.info("📦 Materials → 📅 Schedule → 👷 Resources → ⚠️ Risks → 🎯 Decision evidence")
    st.plotly_chart(network_3d(project, critical), use_container_width=True)

elif page == "Schedule":
    st.subheader("📅 Schedule & Critical Path")
    c1, c2, c3 = st.columns(3)
    with c1: kpi("⚡", "Critical activities", str(ov["critical_activities"]))
    with c2: kpi("◻️", "Non-critical activities", str(ov["non_critical_activities"]))
    with c3: kpi("⏱️", "Duration", f"{ov['project_duration_days']} days")
    rows = dashboard["schedule"]["activities"]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("**Critical path:** " + " → ".join(dashboard["schedule"]["critical_path"]))

elif page == "Materials & Resources":
    st.subheader("🧱 Materials & Resource Feasibility")
    materials = project.get("materials", [])
    defaults = {m["material_id"]: 0.0 for m in materials}
    with st.expander("Set available inventory / resource quantities", expanded=True):
        resource_cols = st.columns(min(4, max(1, len(materials))))
        for i, material in enumerate(materials):
            with resource_cols[i % len(resource_cols)]:
                defaults[material["material_id"]] = st.number_input(material["material_name"], min_value=0.0, value=0.0, step=1.0, key=f"avail_{material['material_id']}")
    resource = build_resource_dashboard(project, defaults)
    s = resource["summary"]
    cols = st.columns(3)
    with cols[0]: kpi("📦", "Resource types", str(s["total_resources"]))
    with cols[1]: kpi("✅", "Feasible", str(s["feasible_resources"]))
    with cols[2]: kpi("⚠️", "Shortage", str(s["shortage_resources"]))
    st.dataframe(pd.DataFrame(resource["resources"]), use_container_width=True, hide_index=True)

elif page == "Risk & Scenarios":
    st.subheader("⚠️ Deterministic Risk & Delay Lab")
    activities = project["activities"]
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

else:
    st.subheader("🌐 3D Project Dependency Graph")
    st.caption("Red diamonds = critical-path activities · blue diamonds = non-critical activities · lines = dependencies")
    st.plotly_chart(network_3d(project, critical), use_container_width=True)
    st.success("Drag to rotate · scroll to zoom · hover nodes for activity duration.")

st.divider()
st.caption("CMIDO · deterministic construction decision layer · interactive research-engineering dashboard")
