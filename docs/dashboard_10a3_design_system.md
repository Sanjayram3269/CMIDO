# CMIDO Dashboard Design System (Phase 10A.3)

Reusable, research-grade visual layer for the CMIDO Streamlit dashboard.

## Layering

```
research engines
    -> validated result artifacts            (10A.2-B: dashboard_data)
        -> dashboard_ui                       (this design system)
            -> Streamlit pages                 (apps/cmido_dashboard.py)
```

The UI layer sits **above** the data layer. It never:

- performs a research calculation,
- reads an artifact, CSV or `results/` directory,
- bypasses `src/construction/dashboard_data/`,
- infers provenance, evidence quality or a scientific conclusion,
- loads experiment-scale scenario ledgers (`LoadingPolicy.NEVER`).

It contains no hard-coded CMIDO research values: every number, badge and status
is supplied by the caller.

## Modules

| Module | Responsibility |
| --- | --- |
| `theme.py` | Single source of truth for colour, typography, spacing, radius, status palette and the injected CSS. |
| `states.py` | `EvidenceState` and `UncertaintyState` vocabularies with accessible labels. |
| `formatting.py` | Pure number, percent, interval, duration and axis-title formatting. |
| `badges.py` | Provenance (`OBS`/`DER`/`EST`/`SCN`), research-stage, status, evidence and uncertainty chips. |
| `cards.py` | KPI card and grid, chart card, table card, methodology/insight card, publication status. |
| `sections.py` | App branding, page/section headers, breadcrumb, flow diagram, status banners, artifact and empty states, footer. |
| `charts.py` | Shared Plotly layout theme, palettes, semantic roles, figure helpers. |
| `tables.py` | Shared table configuration, column alignment, display rounding, source notes. |
| `components.py` | Thin Streamlit adapters (`render_*`, `inject_css`). The only module importing Streamlit. |

All modules except `components.py` are Streamlit-free, so they can be imported
by tests, notebooks or a future non-Streamlit renderer.

## Quick start

```python
from src.construction.dashboard_ui import (
    build_kpi_card, build_section_header, build_provenance_badge,
)
from src.construction.dashboard_ui.components import (
    inject_css, render_kpi_columns, render_section_header, render_table,
)

inject_css()

render_section_header(
    "RO2 - JOINT UNCERTAINTY PROPAGATION",
    "Demand + supply/lead-time uncertainty -> joint propagation -> service risk",
    research_stage="RO2",
    evidence_state="valid",
    methodology="Method: joint Monte Carlo propagation.",
)

render_kpi_columns([
    {"label": "Service risk", "value": "0.31",
     "uncertainty": "service_risk", "provenance": "EST"},
])

render_table(frame, title="RO2 joint propagation summary", provenance="EST")
```

## Design rules

1. **Value / Interpretation / Provenance** are visually separated on every KPI.
2. **Provenance is text first.** Badges render the code (`OBS`), the meaning
   ("Observed") and a tooltip; colour is never the only signal.
3. **Uncertainty is declared.** `uncertainty=` marks a value as a point
   estimate, interval, distribution, tail measure, scenario or service risk.
   Probabilistic quantities are never styled like deterministic facts
   (`uncertainty` series are lighter and semi-transparent by design).
4. **Failures are human-readable.** `build_artifact_state` /
   `build_error_state` show plain language first; the exception text is
   secondary ("Technical detail: ...").
5. **Contrast is tested.** Every text/background pair used by badges and
   surfaces clears WCAG AA (4.5:1); see
   `tests/construction/test_dashboard_ui.py::TestAccessibility`.
6. **No colour literals outside `theme.py`.** Enforced by a test.
7. **Responsive.** Layouts use Streamlit columns and CSS `auto-fit`; no fixed
   pixel widths, so wide desktop, small desktop and sidebar states all reflow.
8. **Cheap.** Builders are pure string/`dict` factories; the stylesheet is
   injected once per session and the 10A.2-B snapshot is cached.

## Provenance vocabulary (fixed)

| Code | Meaning |
| --- | --- |
| `OBS` | Observed — measured or recorded input data |
| `DER` | Derived — deterministic derivation from observed data |
| `EST` | Estimated — statistical estimate with uncertainty |
| `SCN` | Scenario — scenario-generated, not observed |

## Artifact statuses (10A.2-B registry)

`AVAILABLE`, `MISSING`, `INVALID`, `TOO_LARGE`, `UNSUPPORTED`, `NOT_APPLICABLE`
all map onto the shared status palette with an explicit text label.

## Tests

`tests/construction/test_dashboard_ui.py` — tokens, typography, formatting,
badges, KPI/cards, section headers, artifact/empty/error states, chart
configuration, table configuration, accessibility contrast, layering and
performance guarantees.

## Out of scope for 10A.3

The full application shell and navigation (10A.4), page redesigns (10A.5–10A.13)
and the end-to-end dashboard gate (10A.14) are later phases. Only the sidebar
*styling* foundation (`build_sidebar_group`, breadcrumb) is provided here.
