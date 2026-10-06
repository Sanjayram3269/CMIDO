# 10A.5 — Overview & Project Intelligence

Phase 10A.5 redesigns the CMIDO **Overview** page into a project-intelligence
workspace. It is orientation only: it answers *what project is loaded, what is
its schedule state, what context exists, and what evidence can the application
actually show*. It is **not** a research-results page — no RO1/RO2/RO3 outputs
are computed or presented here.

Related documentation: `dashboard_10a3_design_system.md` (components) and the
10A.4 shell/navigation registry. This document covers only the Overview page.

## Purpose

A first-time reader — researcher, supervisor, reviewer, engineer or
decision-maker — should understand the loaded project within one screen:

1. Which project is being analysed (identity, source, status).
2. Snapshot metrics (duration, activities, criticality, materials, suppliers).
3. Declared project context and provenance of every input.
4. Schedule intelligence: CPM table, timing, float, criticality.
5. Critical-path progression (Gantt-style timeline + path banner).
6. The structural intelligence graph (existing 3D dependency view).
7. Material demand and the current (non-)state of resource feasibility.
8. The decision/analytical pipeline this application runs.
9. Evidence/data health, honestly reported.
10. Project status as three separate layers: deterministic analysis,
    evidence availability, and planned research workspaces.

## Information architecture (rendered order)

| # | Section | Content | Provenance |
|---|---------|---------|------------|
| 1 | Loaded project banner | name, id, type, location, status, source (bundled vs uploaded) | inputs (OBS) |
| 2 | Project snapshot | KPI rows of three: duration, activities, critical activities, material types, suppliers, project status | DER for engine values, OBS for input facts |
| 3 | Project context | `Field / Value` table: identity, dates, derived horizon, calendar, input counts, source | OBS (+ derived horizon DER) |
| 4 | Schedule intelligence | activity table (duration, early start/finish, total float, critical) + Gantt timeline + critical-path banner | DER |
| 5 | Project intelligence graph | existing 3D dependency graph, unchanged calculation | DER |
| 6 | Material & resource intelligence | material demand table + explicit "feasibility not evaluated" state | DER |
| 7 | Decision & analytical pipeline | `Project Data → Validation → Quantity/Demand → CPM Schedule → Resource/Procurement Feasibility → Scenario/Impact Analysis → Research Evidence → Decision Intelligence` | n/a (flow only) |
| 8 | Evidence & data status | publication-status card from the cached 10A.2-B snapshot + planned-workspace rows from the 10A.4 registry | snapshot/registry |
| 9 | Project status | deterministic banner + status board rows, one row per layer | DER / evidence / registry |

The shell (10A.4) renders the app header, nav legend, breadcrumb
`CMIDO / Core / Overview`, page header and footer; the page never duplicates
them.

## Data sources

Everything comes through existing layers — the Overview never reads `results/`
directories, raw CSVs or experiment ledgers:

- `build_dashboard_data(project)` — 10A.2-B-bound deterministic analysis
  (overview counts, schedule rows, material totals).
- `calculate_total_float(project)` — existing scheduling engine for early
  start/finish and total float (cheap; wrapped so a failing project degrades to
  a partial state instead of an error page).
- The loaded project JSON — identity, dates, calendar, input counts.
- `cached_snapshot(...)` — the cached 10A.2-B artifact snapshot for evidence
  counts (same cache the Research Evidence page uses).
- The 10A.4 registry (`page_is_planned`, `page_future_phase`) for honest
  planned-workspace labels (RO1–RO3 = 10A.7–10A.9, real-world data = 10A.11).

Presentation builders live in `src/construction/dashboard_ui/overview.py` as
pure functions (no Streamlit, no engines, no artifact access) so the fabrication
guards are unit-testable.

## Project intelligence vs research evidence

- **Project intelligence** = deterministic facts about the *loaded project*
  (DER/OBS only): schedule, quantities, counts, context.
- **Research evidence** = validated repository artifacts and planned research
  workspaces, reported separately with their own statuses.

The Project Status board always keeps three rows — deterministic analysis,
research-evidence artifacts, RO1–RO3 workspaces — and never collapses them into
one verdict. Probabilistic/estimated research claims (EST, RO1/RO2/RO3) never
appear on this page.

## 3D Project Graph

The registry maps *3D Project Graph* to the Project Intelligence destination.
10A.5 preserves it verbatim: `graph_3d()` in the app keeps its calculation,
semantics, interactions, legend and critical-path highlighting. The page only
wraps it in a section header; no graph logic moved into `dashboard_ui`.

## Project upload & session state

The sidebar uploader is unchanged. `render_overview(project, data,
source_name, source_path)` receives the load source so the banner and context
table distinguish *uploaded in this session* from *bundled project file*.
Navigating away and back, or reloading, never resets the uploaded project,
scenario or experiment session state; the Overview only reads state.

## Empty / partial / error policy

- A metric whose source value is absent is **omitted**, never shown as zero.
  A real zero (e.g. a project registering no suppliers) is shown as data.
- Resource feasibility is **not evaluated** on Overview (availability is a user
  input on Materials & Resources) and renders an explanatory empty state.
- Partial schedule timing: float columns appear only when the engine returned
  floats for every activity; otherwise the table keeps duration/criticality and
  a partial-state banner explains it.
- Missing snapshot → evidence rows report `missing` with counts omitted, plus a
  banner stating what remains available. Exceptions surface only as secondary
  "technical detail" text.

## Intentionally deferred to 10A.6+

Full schedule redesign (deep float analysis, dependency logic), full Materials
& Resources redesign with interactive feasibility, and every research
workspace (10A.7–10A.13). The Overview must stay orientation-only.

## Adding an Overview metric safely

1. Confirm the value already exists in `build_dashboard_data`, the project
   JSON, `calculate_total_float` or the cached snapshot — do not compute new
   research here.
2. Add it inside a pure builder in `dashboard_ui/overview.py`: skip when the
   source value is `None`/absent (no placeholder zeros) and tag the correct
   provenance (`OBS` inputs, `DER` engine outputs, never `EST`/`SCN` claims).
3. Render it with the existing 10A.3 components (`render_kpi_columns`,
   `render_table`, `build_publication_status`, `build_empty_state`) — no new
   CSS or KPI implementations.
4. Extend `tests/construction/test_dashboard_overview.py`: value equality
   against the source, omission behaviour for missing sources, and the AppTest
   render assertions.
