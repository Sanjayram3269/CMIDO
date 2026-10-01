# CMIDO 8L — Interactive Research Dashboard

The 8L dashboard is an interactive Streamlit control surface over the existing CMIDO deterministic engines.

## Run locally

```powershell
pip install -r requirements-dashboard.txt
streamlit run apps/cmido_dashboard.py
```

## Dashboard flow

1. **Overview** — project KPIs and interactive 3D dependency graph.
2. **Schedule** — CPM activity table and critical-path visibility.
3. **Materials & Resources** — interactive inventory inputs and feasibility results.
4. **Risk & Scenarios** — activity delay scenario execution through the real schedule-impact engine.
5. **Experiment Lab** — reproducible scenario selection, seed control, and real CMIDO dataset execution.
6. **Research Evidence** — descriptive statistics and deterministic bootstrap uncertainty from experiment outputs.
7. **3D Project Graph** — rotatable dependency network with critical-path highlighting.

## Design principles

- UI actions call the existing domain and experiment layers rather than duplicating scheduling logic.
- Scenario execution is deterministic and seed-controlled.
- The research evidence view explicitly states that bootstrap uncertainty describes the supplied scenarios and is not a population-level causal or predictive claim.
- Uploaded project JSON is supported for dashboard exploration; the Experiment Lab's reproducible run uses the canonical CMIDO project path.

## Dependencies

Dashboard-only dependencies are isolated in `requirements-dashboard.txt` so the research package remains dependency-light.
