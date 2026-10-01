from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Streamlit executes this file as a script. Add the repository root explicitly
# so the package imports work from both PowerShell and the Streamlit launcher.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.construction.dashboard import build_dashboard_data
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

st.set_page_config(page_title="CMIDO | Construction Decision Intelligence", page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container{max-width:1500px;padding-top:1rem}
.hero{padding:1.7rem 2rem;border-radius:24px;background:linear-gradient(135deg,#07111f,#123d70 60%,#0f766e);color:white;box-shadow:0 18px 45px rgba(15,23,42,.24);margin-bottom:1rem}
.hero h1{margin:0;font-size:2.5rem}.hero p{margin:.45rem 0 0;color:#dbeafe}
.card{padding:1rem 1.1rem;border:1px solid #dbe3ee;border-radius:18px;background:#fff;box-shadow:0 8px 24px rgba(15,23,42,.07)}
.flow{display:flex;gap:.55rem;flex-wrap:wrap;padding:1rem;border-radius:18px;background:#f8fafc;border:1px solid #e2e8f0;margin-bottom:1rem}.node{padding:.55rem .8rem;border-radius:12px;background:#fff;border:1px solid #cbd5e1;font-weight:700}
</style>
""", unsafe_allow_html=True)


def load_project(uploaded: Any) -> tuple[dict[str, Any], str]:
    if uploaded is not None:
        return json.loads(uploaded.getvalue().decode("utf-8")), uploaded.name
    return json.loads(DEFAULT_PROJECT.read_text(encoding="utf-8")), DEFAULT_PROJECT.name


def kpi(icon: str, label: str, value: str) -> None:
    st.markdown(f'<div class="card"><div style="font-size:1.45rem">{icon}</div><small>{label}</small><h3 style="margin:.15rem 0">{value}</h3></div>', unsafe_allow_html=True)


def graph_3d(project: dict[str, Any], critical: set[str]) -> go.Figure:
    acts = project.get("activities", [])
    deps = project.get("dependencies", [])
    ids = [a["activity_id"] for a in acts]
    pos = {x:i for i,x in enumerate(ids)}
    x = list(range(len(ids)))
    y = [(i * 7) % 13 for i in range(len(ids))]
    z = [a.get("duration_days", a.get("duration", 0)) for a in acts]
    ex, ey, ez = [], [], []
    for d in deps:
        p, s = d.get("predecessor_id"), d.get("successor_id")
        if p in pos and s in pos:
            i, j = pos[p], pos[s]
            ex += [x[i], x[j], None]; ey += [y[i], y[j], None]; ez += [z[i], z[j], None]
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(x=ex,y=ey,z=ez,mode="lines",line=dict(width=3),name="Dependencies",hoverinfo="skip"))
    fig.add_trace(go.Scatter3d(x=x,y=y,z=z,mode="markers+text",text=ids,textposition="top center",marker=dict(size=[16 if a in critical else 9 for a in ids],color=["#ef4444" if a in critical else "#38bdf8" for a in ids],symbol="diamond"),hovertemplate="<b>%{text}</b><br>Duration: %{z} days<extra></extra>",name="Activities"))
    fig.update_layout(height=600,margin=dict(l=0,r=0,t=20,b=0),scene=dict(xaxis_title="Sequence",yaxis_title="Network position",zaxis_title="Duration (days)"))
    return fig


def result_frame(experiment: dict[str, Any]) -> pd.DataFrame:
    rows=[]
    for item in experiment.get("results",[]):
        s,m=item["scenario"],item["metrics"]
        rows.append({"Activity":s["activity_id"],"Input delay (days)":s["delay_days"],"Project delay (days)":m["project_delay_days"],"Scenario duration (days)":m["scenario_duration_days"],"Relative delay":m["relative_delay"]})
    return pd.DataFrame(rows)


st.markdown('<div class="hero"><h1>🏗️ CMIDO</h1><p>Construction Material Intelligence & Decision Observatory · deterministic construction decision intelligence + reproducible research</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🎛️ Control Center")
    uploaded=st.file_uploader("Load project JSON",type=["json"])
    page=st.radio("Navigate",["Overview","Schedule","Materials & Resources","Risk & Scenarios","Experiment Lab","Research Evidence","3D Project Graph"])
    st.divider(); st.caption("All controls call the existing CMIDO domain engines; the dashboard is an interface, not a replacement for the research logic.")

try:
    project,source_name=load_project(uploaded)
    data=build_dashboard_data(project)
except Exception as exc:
    st.error(f"Could not load project: {exc}"); st.stop()

ov=data["overview"]
critical=set(data["schedule"]["critical_path"])

if page=="Overview":
    st.subheader(f"{ov['project_name']} · {ov['location']}")
    st.caption(f"Source: {source_name} · Project ID: {ov['project_id']}")
    c=st.columns(4)
    with c[0]: kpi("📅","Project duration",f"{ov['project_duration_days']} days")
    with c[1]: kpi("⚡","Critical path",f"{ov['critical_path_duration_days']} days")
    with c[2]: kpi("🔗","Activities",str(ov['total_activities']))
    with c[3]: kpi("🧱","Material types",str(ov['total_material_types']))
    st.markdown('<div class="flow">'+''.join(f'<span class="node">{x}</span>' for x in ["📦 Materials","📅 Schedule","👷 Resources","⚠️ Risks","🧪 Experiments","📊 Evidence"])+"</div>",unsafe_allow_html=True)
    st.plotly_chart(graph_3d(project,critical),use_container_width=True)

elif page=="Schedule":
    st.subheader("📅 Schedule & Critical Path")
    c=st.columns(3)
    with c[0]: kpi("⚡","Critical activities",str(ov["critical_activities"]))
    with c[1]: kpi("◻️","Non-critical activities",str(ov["non_critical_activities"]))
    with c[2]: kpi("⏱️","Duration",f"{ov['project_duration_days']} days")
    st.dataframe(pd.DataFrame(data["schedule"]["activities"]),use_container_width=True,hide_index=True)
    st.info("Critical path: " + " → ".join(data["schedule"]["critical_path"]))

elif page=="Materials & Resources":
    st.subheader("🧱 Materials & Resource Feasibility")
    materials=project.get("materials",[]); available={}
    cols=st.columns(min(4,max(1,len(materials))))
    for i,m in enumerate(materials):
        with cols[i%len(cols)]: available[m["material_id"]]=st.number_input(m["material_name"],min_value=0.0,value=0.0,step=1.0,key="inventory_"+m["material_id"])
    resource=build_resource_dashboard(project,available); s=resource["summary"]
    c=st.columns(3)
    with c[0]: kpi("📦","Resource types",str(s["total_resources"]))
    with c[1]: kpi("✅","Feasible",str(s["feasible_resources"]))
    with c[2]: kpi("⚠️","Shortage",str(s["shortage_resources"]))
    st.dataframe(pd.DataFrame(resource["resources"]),use_container_width=True,hide_index=True)

elif page=="Risk & Scenarios":
    st.subheader("⚠️ Deterministic Risk & Delay Lab")
    ids=[a["activity_id"] for a in project.get("activities",[])]
    activity=st.selectbox("Activity",ids); delay=st.slider("Scenario delay (days)",0,30,3)
    if st.button("▶ Run scenario",type="primary",use_container_width=True):
        try:
            r=analyze_schedule_impact(project,activity,delay)
            c=st.columns(3)
            with c[0]: kpi("📅","Baseline",f"{r['baseline_project_duration']} days")
            with c[1]: kpi("🎯","Scenario",f"{r['scenario_project_duration']} days")
            with c[2]: kpi("🚨","Project delay",f"{r['project_delay_days']} days")
            st.write("Critical path before:"," → ".join(r["critical_path_before"])); st.write("Critical path after:"," → ".join(r["critical_path_after"]))
            st.dataframe(pd.DataFrame(r["affected_activities"]),use_container_width=True,hide_index=True)
        except Exception as exc: st.error(f"Scenario failed: {exc}")
    with st.expander("Risk context"):
        ctx=build_uncertainty_context(project,[]); st.json({"baseline":ctx["baseline"],"risk_summary":ctx["risk_summary"],"project_impact":ctx["project_impact"]})

elif page=="Experiment Lab":
    st.subheader("🧪 Experiment Lab")
    st.caption("Deterministic CMIDO scenarios are executed through the real schedule-impact evaluator.")
    ids=[a["activity_id"] for a in project.get("activities",[])]
    selected=st.multiselect("Activities",ids,default=ids[:1]); delays=st.multiselect("Delay levels",list(range(0,11)),default=[0,1,3,5]); seed=st.number_input("Seed",min_value=0,value=42,step=1)
    if st.button("🚀 Execute experiment",type="primary",use_container_width=True):
        if not selected or not delays: st.error("Select at least one activity and one delay level.")
        else:
            scenarios=[s for a in selected for s in build_delay_scenarios(a,delays)]
            config=ExperimentConfig(experiment_id="CMIDO_DASHBOARD_RUN",name="CMIDO Dashboard Experiment",seed=int(seed),parameters={"activities":selected,"delay_levels":delays})
            with st.spinner("Running deterministic CMIDO scenarios..."): exp=run_real_dataset_experiment(str(DEFAULT_PROJECT),config,scenarios)
            st.session_state["experiment"]=exp; st.success(f"Executed {exp['scenario_count']} scenarios.")
    exp=st.session_state.get("experiment")
    if exp:
        frame=result_frame(exp); st.dataframe(frame,use_container_width=True,hide_index=True)
        if not frame.empty:
            fig=go.Figure()
            for aid,g in frame.groupby("Activity"): fig.add_trace(go.Scatter(x=g["Input delay (days)"],y=g["Project delay (days)"],mode="lines+markers",name=aid))
            fig.update_layout(height=420,xaxis_title="Input delay (days)",yaxis_title="Observed project delay (days)"); st.plotly_chart(fig,use_container_width=True)

elif page=="Research Evidence":
    st.subheader("📊 Research Evidence")
    exp=st.session_state.get("experiment")
    if not exp: st.info("Run an experiment in Experiment Lab first.")
    else:
        analysis=build_statistical_analysis(exp["results"],seed=exp["experiment"]["seed"])
        project_delay=analysis["project_delay"]; ci=analysis["mean_project_delay_confidence_interval"]
        c=st.columns(4)
        with c[0]: kpi("🧪","Scenarios",str(analysis["scenario_count"]))
        with c[1]: kpi("📈","Mean project delay",f"{project_delay['mean']:.2f} d")
        with c[2]: kpi("⚠️","Delayed scenarios",f"{analysis['delay_rate']:.1%}")
        with c[3]: kpi("📐","95% bootstrap CI",f"{ci['lower']:.2f}–{ci['upper']:.2f} d")
        st.write("Delay rate:",analysis["delay_rate"])
        st.json(analysis)

elif page=="3D Project Graph":
    st.subheader("🌐 3D Project Graph")
    st.caption("Interactive dependency network. Critical activities are emphasized; rotate, zoom and hover to inspect the graph.")
    st.plotly_chart(graph_3d(project,critical),use_container_width=True)

st.divider()
st.caption("CMIDO · deterministic construction decision layer · reproducible research dashboard · 8L")
