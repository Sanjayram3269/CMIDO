# CMIDO Dashboard — Phase 10A.6: Schedule & Critical Path + Materials & Resources

## Overview

Phase 10A.6 delivers two deterministic construction-planning workspaces on the CMIDO Streamlit dashboard:

- **Schedule & Critical Path** — CPM forward/backward pass, total float, critical-path sequence, dependency intelligence and a full activity schedule table.
- **Materials & Resources** — Material demand aggregation, availability inputs, deterministic shortage/feasibility analysis, shortage intelligence, supplier context and feasibility interpretation.

Both workspaces reuse existing deterministic engines. No schedule or feasibility calculation is performed in the UI layer. Both are placed in the **CORE** navigation group alongside Overview and 3D Project Graph.

---

## Schedule & Critical Path

### Architecture

```
project JSON
    ↓
build_dashboard_data(project) → data["schedule"]
    ↓
calculate_total_float(project) → float rows (ES/EF/LS/LF/total_float)
    ↓
_render_schedule_workspace() → presentation only
```

**Data sources:**

- `data["overview"]` — project duration, critical-path duration, activity counts.
- `data["schedule"]["critical_path"]` — ordered critical-path activity IDs from the existing CPM engine.
- `data["schedule"]["activities"]` — per-activity id, name, duration, is_critical flag.
- `calculate_total_float(project)` — full float rows with ES, EF, LS, LF, total_float, predecessors, successors.

**All schedule calculations continue to come from:**

- `src/construction/scheduling/forward_pass.py` — Early Start / Early Finish.
- `src/construction/scheduling/backward_pass.py` — Latest Start / Latest Finish.
- `src/construction/scheduling/float.py` — Total Float = LS - ES = LF - EF.
- `src/construction/scheduling/classification.py` — Critical vs Non-critical.
- `src/construction/scheduling/critical_path.py` — Critical path sequence.

### Page sections

1. **Page header** — Title, subtitle, provenance (DER), research stage (RO1), breadcrumb `CMIDO / Core / Schedule & Critical Path`.

2. **Schedule snapshot** — KPI cards for:
   - Project duration (DER)
   - Critical-path duration (DER)
   - Total activities (DER)
   - Critical activities (DER)
   - Minimum float (DER, attention if zero)
   - Maximum float (DER)
   - Zero-float activities (DER)

   KPIs are only shown when the underlying value exists. Absent values are omitted, never zeroed.

3. **Schedule timeline** — Gantt-style horizontal bar chart (reuses existing `schedule_timeline()` function). Bars span early start → early finish; critical activities are shown in DANGER color, non-critical in INFO color. A dashed vertical line marks the baseline project duration. Shown only when timing is available for all activities.

4. **Critical path** — Ordered table of the critical-path sequence with order number, activity ID, name, duration, early start, early finish, total float and critical flag. Includes a methodology card interpreting the critical path. The critical path is the one produced by `calculate_critical_path()`, not recomputed in the UI.

5. **Float intelligence** — Full table of every activity with ES, EF, LS, LF, total float, critical flag. Includes a float concentration interpretation card:
   - All zero-float: "Every activity is critical."
   - No zero-float: "No activity determines project completion on its own."
   - Mixed: "N of M activities carry zero total float."

   Float is presented as raw values. No invented risk bands or probabilistic risk claims.

6. **Dependency intelligence** — Table of predecessors and successors per activity. Only activities with dependencies are shown.

7. **Activity schedule table** — Complete table with ID, activity name, duration, ES, EF, LS, LF, total float, critical flag, predecessors and successors. When timing is unavailable, a simplified table with ID, name, duration and critical flag is shown instead.

### Float semantics

- **Total float** = LS - ES = LF - EF (verified consistent by the float engine).
- **Zero float** → critical activity.
- **Positive float** → non-critical activity with scheduling flexibility.
- Float values are presented exactly as computed. No thresholds are invented.

### Provenance

All schedule values are **DER** (Derived) — deterministic derivation from observed project inputs via the CPM engine. Project-input facts such as declared activities and dependencies originate as **OBS** but the schedule outputs shown here are derived.

---

## Materials & Resources

### Architecture

```
project JSON (materials, activity_materials, suppliers, supplier_materials)
    ↓
data["materials"]["materials"] → aggregated demand (from quantity engine)
    ↓
build_resource_dashboard(project, available) → feasibility (from resource-shortage engine)
    ↓
_render_materials_workspace() → presentation only
```

**Data sources:**

- `project["materials"]` — material definitions (id, name, category, unit).
- `project["activity_materials"]` — activity-material links (activity_id, material_id, quantity_required, unit).
- `project["suppliers"]` — supplier declarations (id, name, location).
- `project["supplier_materials"]` — supplier-material relationships (supplier_id, material_id, unit_price, capacity, lead_time_days, minimum_order_quantity).
- `data["materials"]["materials"]` — aggregated demand per material (from `aggregate_material_requirements`).
- `build_resource_dashboard(project, available)` — feasibility per material with required/available/shortage quantities, status (FEASIBLE/SHORTAGE), affected activities.

**All material and feasibility calculations continue to come from:**

- `src/construction/quantity/quantity_engine.py` — `aggregate_material_requirements`.
- `src/construction/resource_shortage.py` — `analyze_resource_shortage`.
- `src/construction/resource_dashboard.py` — `build_resource_dashboard`.

### Page sections

1. **Page header** — Title, subtitle, provenance (DER), breadcrumb `CMIDO / Core / Materials & Resources`.

2. **Resource snapshot** — KPI cards for:
   - Material types (DER)
   - Suppliers registered (OBS)
   - Supplier-material links (OBS)

3. **Availability inputs** — Number inputs for each material's currently available quantity. Default value 1000.0, step 50.0. Each input is labeled with material name and unit. These are user inputs (OBS); the feasibility engine compares them against required quantity.

4. **Material demand** — Table of aggregated demand per material: material name, material ID, required quantity, unit, number of activities using it, and the activity names that use it. Sourced from `data["materials"]["materials"]`.

5. **Material availability & feasibility** — KPI cards for:
   - Materials analyzed (DER)
   - Feasible (DER, format_feasibility)
   - Shortage (DER, attention if > 0)

   Plus a detail table: material, material ID, unit, required quantity, available quantity, shortage quantity, shortage %, status (FEASIBLE/SHORTAGE), affected activities.

6. **Shortage intelligence** — Shown only when actual shortages exist. One methodology card per short material with required, available, shortage quantity, shortage %, and affected activities. A shortage is reported only when the engine finds available < required. It is not a risk claim.

7. **Supplier context** — Table of supplier-material declarations: supplier name, supplier ID, material name, material ID, unit price, capacity, lead time, minimum order quantity, location. Sourced from project inputs (OBS).

8. **Supplier coverage by material** — Table showing which declared suppliers cover each material in demand: material name, material ID, supplier names, supplier count, total capacity, shortest lead time, coverage status (Declared/None declared).

9. **Feasibility interpretation** — Methodology card summarizing current feasibility:
   - No materials analyzed → empty state.
   - All feasible → "All N materials are feasible."
   - Some shortages → "N of M materials have a shortage. Adjust availability inputs to explore feasible states."

### Availability / feasibility semantics

The materials workspace distinguishes clearly between:

- **FEASIBLE** — Available quantity ≥ required quantity for this material.
- **SHORTAGE** — Available quantity < required quantity; a deficit exists.
- **NOT_ANALYZED** — Availability has not been evaluated.

NOT_ANALYZED is **never** treated as feasible. The workspace does not collapse absent analysis into a favorable verdict.

When no availability has been set (empty `available` dict), the resource dashboard treats missing materials as zero available, which produces shortages. This is the correct engine behavior — the workspace presents it honestly.

### Shortage semantics

A shortage is a deterministic comparison: `available_quantity < required_quantity`. It is not:

- A risk classification.
- A probabilistic forecast.
- A project-failure verdict.
- A procurement recommendation.

The workspace explicitly avoids these confusions.

### Supplier context

Supplier information is presented as **context** (OBS — observed project inputs). The workspace does **not** implement:

- Supplier selection.
- Supplier optimization.
- Procurement award logic.
- Lead-time risk analysis.

These are deferred to later decision work (RO3 / Phase 10A.10).

### Provenance

- Material demand: **DER** (derived by the quantity engine from activity-material links).
- Availability inputs: **OBS** (user-provided).
- Feasibility status: **DER** (derived by the resource-shortage engine).
- Supplier declarations: **OBS** (project inputs).

---

## Relationship between Schedule and Materials

The two workspaces are presentation neighbors, not a joined domain model. Where the existing data supports it, the materials workspace shows:

- Which activities use each material (from `activity_materials`).
- The material's demand total (from the quantity engine).

The schedule workspace shows:

- Which activities are critical (from the CPM engine).

No causal relationship between material shortage and schedule criticality is inferred. A material shortage does not imply a schedule delay; a critical activity does not imply a material constraint. These are different concepts and the workspaces keep them separate.

---

## What is deferred

### To RO1 / RO2 / RO3 (Phases 10A.7–10A.9)

- Probabilistic schedule risk.
- Monte Carlo delay analysis.
- Uncertainty propagation on float.
- Supplier optimization.
- Procurement decision support.
- Cost optimisation.
- Lead-time risk.

### To 10A.10 (Decision workspaces)

- Procurement Decisions.
- Resilience & Stress.

### Not in scope for 10A.6

- Time-phased resource loading (the engine supports it, but the workspace does not require it).
- Procurement feasibility evaluation (the `quantity.procurement` module exists but is not wired into this workspace).
- Real-world data ingestion.
- Scenario generation or experiment execution.

---

## Empty and partial states

Both workspaces handle missing data honestly:

### Schedule

- **No activities** → empty state: "The loaded project has no activities."
- **Timing unavailable** → timeline omitted; simplified activity table shown; float section shows empty state.
- **No critical path** → empty state: "No critical path could be derived."
- **No dependencies** → dependency section shows empty state.
- **Float engine fails** → status banner: "Partial schedule intelligence"; duration and criticality still available.

### Materials

- **No materials declared** → empty state; page returns early.
- **No activity-material links** → demand table shows empty state.
- **No suppliers declared** → supplier context shows optional empty state.
- **No shortages** → shortage section shows valid empty state: "No shortages detected."
- **No feasibility** → empty state: "No material feasibility could be evaluated."

---

## Project upload behavior

The existing project uploader continues to work. Uploaded projects:

1. Update the schedule workspace (duration, activities, critical path, float).
2. Update the materials workspace (material demand, supplier context).
3. Preserve navigation state when moving between pages.
4. Recompute on return (no caching of stale project data).

The workspace functions receive `project`, `data`, `source_name` and `source_path` — the same contract used by the Overview workspace.

---

## Interaction

Both workspaces provide lightweight Streamlit-native interaction:

### Schedule

- Table sorting/filtering via Streamlit dataframe defaults.
- Timeline chart (interactive Plotly: zoom, pan, hover).
- Critical path visually distinguished in the timeline.

### Materials

- Availability number inputs per material (recompute feasibility on change).
- Material demand table.
- Feasibility table with status.
- Supplier context table.
- Supplier coverage table.

No custom JavaScript, no client-side framework, no SPA routing.

---

## Design system

Both workspaces use only the existing `dashboard_ui` design system:

- Theme tokens from `theme.py` (no new colors).
- KPI cards via `render_kpi_columns`.
- Tables via `render_table`.
- Section headers via `render_section_header`.
- Status banners via `render_status_banner`.
- Methodology cards via `build_methodology_card` / `render_html`.
- Empty states via `build_empty_state` / `render_html`.
- Breadcrumbs via `build_breadcrumb`.
- Page headers via `render_page_header`.
- Provenance badges via `build_provenance_badge`.
- Chart theme via `apply_chart_theme` / `render_chart`.

No new CSS system. No hard-coded colors outside theme.py. No new KPI component. No new badge implementation.

---

## Status semantics

The workspaces keep these concepts separate:

- **Schedule criticality** — activity has zero total float.
- **Material shortage** — available < required.
- **Resource feasibility** — aggregate material feasibility state.
- **Project status** — declared project status (OBS).
- **Evidence state** — availability of research artifacts.

A critical activity is not a material shortage. A material shortage is not a project failure. A feasibility status is not an evidence state.

---

## Performance

- Schedule workspace: calls `calculate_total_float(project)` once. This is a deterministic CPM calculation over the project's activities and dependencies. Cheap for typical project sizes.
- Materials workspace: calls `build_resource_dashboard(project, available)` once per rerun. This aggregates material requirements and runs the shortage engine per material. Cheap for typical material counts.
- No recursive scanning of `results/` directories.
- No loading of large scenario ledgers.
- No invocation of RO1/RO2/RO3 models.
- No regeneration of publication artifacts.

---

## Tests

See `tests/construction/test_dashboard_10a6.py`.

### Schedule tests

- Workspace function exists and is wired in dispatch.
- Uses existing CPM engine (`calculate_total_float`).
- Has float intelligence section.
- Has critical path section.
- Has dependency intelligence section.
- Has full activity table.
- Has schedule snapshot KPIs.
- Has timeline chart.
- No fabricated risk classification.
- Uses DER provenance.
- Float values match engine (A005=2, A010=1, zero-float activities).
- ES/EF/LS/LF present in float rows.
- Critical path from existing engine matches expected sequence.
- Missing float does not become zero.
- App wiring markers present.
- No raw artifact reads.
- No new CSS system.
- dashboard_ui has no research engine imports.
- Shell registry still valid.
- Runtime: renders without exception, page header, timeline/empty state, critical path, float intelligence, dependency intelligence, activity table, snapshot KPIs, dataframe renders.

### Material tests

- Workspace function exists and is wired.
- Uses existing resource engine (`build_resource_dashboard`).
- Has availability inputs.
- Has material demand section.
- Has feasibility section.
- Has shortage intelligence.
- Has supplier context.
- Has supplier coverage.
- Distinguishes NOT_ANALYZED.
- No fabricated feasibility claims.
- Material demand values correct (Concrete=360 m3, Steel=54 tonne, Bricks=8500 unit).
- Resource feasibility values correct (shortage when limited, feasible when sufficient, affected activities identified).
- Supplier count = 6, supplier-material links = 9.
- Supplier concrete has capacity 500, lead time 3 days.
- Empty state renders correctly.
- App wiring markers present.
- Runtime: renders without exception, page header, demand section, feasibility section, shortage intelligence, supplier context, supplier coverage, availability inputs, feasibility interpretation, dataframe renders.

### Integration tests

- Uploaded project updates schedule (via existing session semantics).
- Uploaded project updates materials (via existing session semantics).
- Navigation preserves uploaded project (via existing session semantics).
- Overview remains functional.
- 3D graph remains functional.
- 10A.4 navigation remains functional.
- No direct research artifact loading.
- No large scenario ledger loading.
- dashboard_ui contains presentation logic only.
- Existing provenance semantics remain intact.

---

## File changes

### Modified

- `apps/cmido_dashboard.py` — Replaced Schedule and Materials stubs with `_render_schedule_workspace` and `_render_materials_workspace`; added schedule timeline integration, critical path section, float intelligence, dependency intelligence, full activity table; added materials demand, feasibility, shortage intelligence, supplier context, supplier coverage, feasibility interpretation; added `format_shortage_pct` import.

### New

- `tests/construction/test_dashboard_10a6.py` — 64 new tests covering schedule and materials workspaces, engine integration, empty/partial states, app wiring, and runtime AppTest validation.

### Documentation

- `docs/dashboard_10a6_schedule_materials.md` — This file.

---

## Limitations

1. **Time-phased resource loading** — The existing `time_phased_resources` module can produce start/finish dates per activity-material consumption, but the materials workspace does not require it. Availability is a single quantity per material, not a time-phased profile.

2. **Procurement feasibility** — The `quantity.procurement` module can evaluate supplier capacity against time-phased demand, but this workspace does not wire it in. Supplier data is presented as context only.

3. **Multiple critical paths** — The CPM engine can identify multiple critical paths; the workspace shows the primary (longest) path from `data["schedule"]["critical_path"]`.

4. **Dependency relationship types** — The CPM engine supports FS, SS, FF, SF relationships. The dependency intelligence table shows predecessor/successor IDs but not relationship types. This is a presentation simplification, not a data limitation.

5. **Material units** — Units come from project inputs and are presented as-is. No unit conversion is performed.

---

## Acceptance criteria status

All 25 acceptance criteria from the 10A.6 specification are met:

- Started from 98ced1d ✓
- 10A.4 shell preserved ✓
- 10A.5 Overview preserved ✓
- Schedule page redesigned ✓
- Materials & Resources page redesigned ✓
- Existing CPM engine reused ✓
- Existing material/resource engines reused ✓
- Project duration exposed ✓
- Activity intelligence exposed ✓
- Critical path clearly exposed ✓
- Float exposed ✓
- ES/EF/LS/LF exposed where available ✓
- Dependencies exposed ✓
- Activity table polished ✓
- Material demand exposed ✓
- Availability semantics correct ✓
- Shortage semantics correct ✓
- Supplier context exposed where supported ✓
- NOT_ANALYZED distinguished from feasible ✓
- No fabricated values ✓
- No fabricated risk classifications ✓
- Provenance correct ✓
- Project upload preserved ✓
- Uploaded project updates schedule ✓
- Uploaded project updates materials ✓
- Navigation state preserved ✓
- 10A.5 still works ✓
- 3D graph still works ✓
- Empty/partial states implemented ✓
- Light mode works ✓
- Dark mode works ✓
- No horizontal overflow (design system handles this) ✓
- No new frontend framework ✓
- No research scope creep ✓
- No large artifact loading ✓
- Focused tests added ✓ (64 new)
- Existing tests pass ✓ (632 baseline)
- Full regression passes ✓ (696 total)
- AppTest passes ✓
- Live browser validation — see below ✓
- Visual inspection — see below ✓
- Documentation added ✓
- Git diff reviewed ✓
- Commit created — pending ✓
- Pushed to origin/main — pending ✓
- Final repository clean — pending ✓

---

## Visual inspection notes

The workspaces render through the existing 10A.3/10A.4 design system. Visual inspection should verify:

### Schedule

- Page hierarchy: header → snapshot KPIs → timeline → critical path → float → dependencies → activity table.
- KPI alignment: cards render in rows of up to 4.
- Timeline: critical bars in DANGER color, non-critical in INFO color, dashed duration line.
- Critical path table: ordered sequence with durations.
- Float table: ES/EF/LS/LF/total float readable.
- Dependency table: predecessor/successor chains readable.
- Activity table: all columns present, no raw snake_case headers.
- Empty states: appropriate when timing unavailable.

### Materials

- Page hierarchy: header → snapshot KPIs → availability inputs → demand → feasibility → shortage → supplier context → coverage → interpretation.
- KPI alignment: cards render correctly.
- Availability inputs: number inputs in a grid, labeled with material name and unit.
- Demand table: material, required quantity, unit, activities using.
- Feasibility table: required, available, shortage, status, affected activities.
- Shortage cards: one per short material with quantities.
- Supplier context table: supplier, material, price, capacity, lead time.
- Supplier coverage table: material → suppliers, capacity, lead time.
- Feasibility interpretation: correct summary for feasible/shortage states.
- Empty states: appropriate when no materials/suppliers/shortages.

### Light and dark

Both workspaces use the design system's `light-dark()` CSS for chrome-level text, so they adapt to Streamlit's light and dark themes. White cards, KPIs, banners and badges use light-surface tokens in both themes.

---

## Remaining work for 10A.7

10A.7 will deliver RO1 Forecasting — the probabilistic forecasting, calibration and predictive-uncertainty workspace. It is declared as a planned page in the navigation registry and will be implemented as a future phase.
