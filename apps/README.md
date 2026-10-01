# CMIDO Interactive Dashboard

The dashboard is a real Streamlit application over the existing CMIDO deterministic engines. It is not a static mockup.

## Run locally

From the repository root:

```powershell
python -m pip install -r requirements-dashboard.txt
python -m streamlit run apps/cmido_dashboard.py
```

## Interactive flow

1. Load the bundled CMIDO demo project or upload a compatible JSON project.
2. Use **Overview** to inspect live CPM, materials and project KPIs.
3. Use **Schedule** to inspect activities and the critical path.
4. Use **Materials & Resources** to change available quantities and recalculate shortage feasibility.
5. Use **Risk & Scenarios** to inject an activity delay and inspect schedule propagation.
6. Use **Experiment Lab** to execute deterministic scenario batches through the real CMIDO evaluator.
7. Use **Research Evidence** to inspect statistical summaries produced by the experiment layer.
8. Use **3D Project Graph** to rotate/zoom/hover through the activity dependency network.

The dashboard intentionally calls existing domain engines instead of duplicating scheduling, resource, uncertainty, or experiment calculations.
