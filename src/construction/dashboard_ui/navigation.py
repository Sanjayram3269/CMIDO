"""CMIDO 10A.4 — Application shell: page registry, groups, routing metadata, breadcrumbs.

This is the single declarative source of truth for the CMIDO application shell:

* which pages exist (or are planned),
* which research group each belongs to,
* how the breadcrumb reads,
* whether a page is available now or is a planned future workspace,
* what research stage, provenance vocabulary and implementation status attach to it.

Everything downstream — the grouped sidebar, the main-area breadcrumb, the
legend, the active-state styling and the page dispatch in
``apps/cmido_dashboard.py`` — is derived from this registry. The four research
groups are fixed and enforced by tests so they cannot drift apart.

Grouping rationale (sidebar order, fixed):

``CORE``
    Orientation. What the project *is*.
``RESEARCH``
    Controlled scenarios, experiments and the derived evidence around them.
``DECISION``
    Deterministic decision support. The analyses a planner acts on.
``EVIDENCE``
    The validated repository artifact layer behind every number shown.

Layering contract (unchanged from 10A.3, reaffirmed for 10A.4):

* This module is pure metadata and HTML — no research logic, no artifact access,
  no inference about provenance. It does not read anything and it does not
  import any research engine.
* Streamlit is imported only by :mod:`.components`. This module stays importable
  without Streamlit installed, so tests and tooling can inspect the registry
  without launching a dashboard.
* Page content lives in ``apps/cmido_dashboard.py``. This module only describes
  the shell and the routing shape; it never renders a research result.
* Future pages are declared honestly. A planned workspace is described as planned,
  never as completed research. No fabricated numbers, charts or KPIs are produced
  here or anywhere in the shell.

Mapping to the intended 15-destination information architecture (audited for 10A.4):

``CORE``
    *Overview* — existing Overview page.
    *3D Project Graph* — existing page serving the Project Intelligence destination.
    *Schedule & Critical Path*, *Materials & Resources* — existing deterministic
    planner pages (moved into CORE by the 10A.4 registry audit).
``RESEARCH``
    *RO1 · Forecasting*, *RO2 · Uncertainty*, *RO3 · Optimization* — all three
    are available research workspaces (10A.7 / 10A.8 / 10A.9).
``DECISION``
    *Scenario Lab* — existing Risk & Scenarios page.
    *Procurement Decisions*, *Resilience & Stress* — CMIDO has no live
    implementation for these yet, so they are declared as planned future pages
    (Phase 10A.10) rather than routed to live content.
``EVIDENCE``
    *Experiments* — existing Experiment Lab page.
    *Research Evidence* — existing Research Evidence page.
    *Real-World Data*, *Ablation & Robustness*, *Provenance & Integrity* — planned
    future workspaces for the corresponding evidence activities.

The registry therefore carries all 15 destinations: 10 available and 5 planned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from . import theme
from .sections import build_breadcrumb, build_sidebar_group

# ---------------------------------------------------------------------------
# Regex helpers — defined before any registry object is constructed.
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# ---------------------------------------------------------------------------
# Session / routing constants
# ---------------------------------------------------------------------------

#: Session-state key holding the active destination id.
NAV_SESSION_KEY = "cmido_active_page"

#: Stable id of the page shown when no valid selection exists (bad or missing state).
DEFAULT_PAGE = "overview"

# ---------------------------------------------------------------------------
# Typing: implementation status
# ---------------------------------------------------------------------------

class ImplementationStatus(str, Enum):
    """Whether a page is currently available in the dashboard."""

    AVAILABLE = "available"
    PLANNED = "planned"


class ResearchStage(str, Enum):
    """Fixed research-stage vocabulary for the shell breadcrumbs and badges.

    The actual badge rendering imports these values through the existing
    design-system helpers; this registry only describes them, it does not render
    anything.
    """

    CORE = "CORE"
    RO1 = "RO1"
    RO2 = "RO2"
    RO3 = "RO3"
    ABLATION = "ABLATION"
    REAL_DATA = "REAL_DATA"
    EVIDENCE = "EVIDENCE"


class Provenance(str, Enum):
    """Fixed provenance vocabulary used by the dashboards and the evidence tab.

    The same four values are used everywhere in the app: OBS / DER / EST / SCN.
    """

    OBSERVED = "OBS"
    DERIVED = "DER"
    ESTIMATED = "EST"
    SCENARIO = "SCN"


# ---------------------------------------------------------------------------
# Typing: a single page definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PageDefinition:
    """One navigable page in the application shell.

    ``id`` is the stable routing key. The legacy dashboard dispatches on page
    title, so every available page also exposes a ``route`` that matches the
    string the existing ``elif page == ...`` dispatch expects. For planned pages
    the route is unused by the current dispatch.
    """

    id: str
    title: str
    group: str
    icon: str = ""
    description: str = ""
    research_stage: str | None = None
    provenance: str | None = None
    implementation: ImplementationStatus = ImplementationStatus.AVAILABLE
    future_phase: str | None = None
    evidence_state_note: str = ""
    route: str = ""

    # derived, cached once per definition — not recomputed on every call
    _slug: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        slug = _SLUG_RE.sub("_", self.id.strip().lower()).strip("_")
        object.__setattr__(self, "_slug", slug)

    @property
    def display(self) -> str:
        """Icon-decorated label shown in the sidebar."""
        return f"{self.icon} {self.title}".strip()

    @property
    def slug(self) -> str:
        """Stable, widget-key-safe identifier derived from the page id."""
        return self._slug

    @property
    def breadcrumb(self) -> list[str]:
        """``CMIDO > Group > Title`` trail for this page."""
        return [theme.APP_NAME, group_by_key(self.group).label, self.title]

    @property
    def is_available(self) -> bool:
        return self.implementation is ImplementationStatus.AVAILABLE

    @property
    def is_planned(self) -> bool:
        return self.implementation is ImplementationStatus.PLANNED


# ---------------------------------------------------------------------------
# Typing: a navigation group
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NavGroup:
    """An ordered sidebar section."""

    key: str
    label: str
    caption: str
    order: int


# ---------------------------------------------------------------------------
# Declarative registry
# ---------------------------------------------------------------------------

NAV_GROUPS: tuple[NavGroup, ...] = (
    NavGroup(key="CORE", label="Core", caption="Project orientation and structure", order=0),
    NavGroup(key="RESEARCH", label="Research", caption="Controlled scenarios and evidence", order=1),
    NavGroup(
        key="DECISION",
        label="Decision",
        caption="Deterministic decision support",
        order=2,
    ),
    NavGroup(key="EVIDENCE", label="Evidence", caption="Validated repository research artifacts", order=3),
)

#: Every page in display order (grouped, then registry order within each group).
#: Every page in display order (grouped, then registry order within each group).
PAGES: tuple[PageDefinition, ...] = (
    # ---- CORE ----------------------------------------------------------------
    PageDefinition(
        id="overview",
        title="Overview",
        group="CORE",
        icon="\U0001f3d7",
        description="Project intelligence and decision context for the loaded project.",
        provenance="DER",
        route="Overview",
    ),
    PageDefinition(
        id="graph_3d",
        title="3D Project Graph",
        group="CORE",
        icon="\U0001f310",
        description="Dependency network with critical-path highlighting (the Project Intelligence destination).",
        research_stage="RO1",
        provenance="DER",
        route="3D Project Graph",
    ),
    PageDefinition(
        id="schedule",
        title="Schedule & Critical Path",
        group="CORE",
        icon="\U0001f4c5",
        description="CPM forward/backward pass, float and classification",
        research_stage="RO1",
        provenance="DER",
        route="Schedule",
    ),
    PageDefinition(
        id="materials",
        title="Materials & Resources",
        group="CORE",
        icon="\U0001f9f1",
        description="Quantity-versus-availability feasibility",
        provenance="DER",
        route="Materials & Resources",
    ),
    # ---- RESEARCH -------------------------------------------------------------
    PageDefinition(
        id="ro1_forecasting",
        title="RO1 · Forecasting",
        group="RESEARCH",
        icon="\U0001f4ca",
        description="Probabilistic demand/price forecasting, predictive uncertainty and calibration evidence.",
        research_stage="RO1",
        provenance="EST",
        route="RO1 · Forecasting",
        implementation=ImplementationStatus.AVAILABLE,
    ),
    PageDefinition(
        id="ro2_uncertainty",
        title="RO2 · Uncertainty",
        group="RESEARCH",
        icon="\U0001f4ca",
        description="Joint uncertainty propagation and service-risk workspace.",
        research_stage="RO2",
        provenance="SCN",
        route="RO2 · Uncertainty",
        implementation=ImplementationStatus.AVAILABLE,
    ),
    PageDefinition(
        id="ro3_optimization",
        title="RO3 · Optimization",
        group="RESEARCH",
        icon="\U0001f4ca",
        description="Controller baseline, ablation and robustness workspace.",
        research_stage="RO3",
        provenance="SCN",
        route="RO3 · Optimization",
        implementation=ImplementationStatus.AVAILABLE,
    ),
    # ---- DECISION -------------------------------------------------------------
    PageDefinition(
        id="scenarios",
        title="Scenario Lab",
        group="DECISION",
        icon="\u26a0\ufe0f",
        description="Single-activity delay injection and response",
        provenance="SCN",
        route="Risk & Scenarios",
    ),
    PageDefinition(
        id="procurement_decisions",
        title="Procurement Decisions",
        group="DECISION",
        icon="\U0001f4ca",
        description="Supplier selection, award and procurement decision workspace.",
        research_stage="RO3",
        evidence_state_note="Not yet implemented",
        implementation=ImplementationStatus.PLANNED,
        future_phase="Phase 10A.10",
    ),
    PageDefinition(
        id="resilience_stress",
        title="Resilience & Stress",
        group="DECISION",
        icon="\U0001f4ca",
        description="Stress testing, resilience and robustness analysis workspace.",
        research_stage="STRESS",
        evidence_state_note="Not yet implemented",
        implementation=ImplementationStatus.PLANNED,
        future_phase="Phase 10A.10",
    ),
    # ---- EVIDENCE -------------------------------------------------------------
    PageDefinition(
        id="evidence",
        title="Research Evidence",
        group="EVIDENCE",
        icon="\U0001f4ca",
        description="Validated repository research artifacts and provenance audit",
        research_stage="EVIDENCE",
        provenance="OBS",
        route="Research Evidence",
    ),
    PageDefinition(
        id="experiment_lab",
        title="Experiments",
        group="EVIDENCE",
        icon="\U0001f9ea",
        description="Controlled scenario grid with a fixed seed",
        research_stage="RO3",
        provenance="SCN",
        route="Experiment Lab",
    ),
    PageDefinition(
        id="real_world_data",
        title="Real-World Data",
        group="EVIDENCE",
        icon="\U0001f4ca",
        description="Canonical dataset, PSLIB project audit and ingestion-stage evidence.",
        research_stage="REAL_DATA",
        provenance="OBS",
        evidence_state_note="Not yet implemented",
        implementation=ImplementationStatus.PLANNED,
        future_phase="Phase 10A.11",
    ),
    PageDefinition(
        id="ablation_robustness",
        title="Ablation & Robustness",
        group="EVIDENCE",
        icon="\U0001f4ca",
        description="Controller ablation, stress and robustness evidence.",
        research_stage="ABLATION",
        provenance="DER",
        evidence_state_note="Not yet implemented",
        implementation=ImplementationStatus.PLANNED,
        future_phase="Phase 10A.12",
    ),
    PageDefinition(
        id="provenance_integrity",
        title="Provenance & Integrity",
        group="EVIDENCE",
        icon="\U0001f4ca",
        description="Artifact provenance, integrity and loading-policy registry.",
        research_stage="EVIDENCE",
        provenance="OBS",
        evidence_state_note="Not yet implemented",
        implementation=ImplementationStatus.PLANNED,
        future_phase="Phase 10A.13",
    ),
)

# ---------------------------------------------------------------------------
# Derived lookups
# ---------------------------------------------------------------------------

NAV_GROUP_KEYS: tuple[str, ...] = tuple(group.key for group in NAV_GROUPS)

PAGELIST: tuple[str, ...] = tuple(page.id for page in PAGES)

_PAGES_BY_ID: dict[str, PageDefinition] = {page.id: page for page in PAGES}
_ROUTES_BY_TITLE: dict[str, PageDefinition] = {
    page.route: page for page in PAGES if page.route
}
_GROUP_BY_KEY: dict[str, NavGroup] = {group.key: group for group in NAV_GROUPS}

def pagelist() -> tuple[str, ...]:
    """Every page id, in display order."""
    return PAGELIST


# Public alias kept for the package __init__ and any existing call sites that
# expect a top-level page-id sequence rather than the PageDefinition tuples.
PAGELIST: tuple[str, ...] = pagelist()


def nav_groups() -> tuple[NavGroup, ...]:
    """Sidebar groups in display order."""
    return tuple(sorted(NAV_GROUPS, key=lambda group: group.order))


def pages() -> tuple[PageDefinition, ...]:
    """All pages in display order (grouped, then registry order within each group)."""
    return PAGES


def pagelist() -> tuple[str, ...]:
    """Every page id, in display order."""
    return PAGELIST


def page_by_id(page_id: str) -> PageDefinition:
    """Return a page by stable id, raising ``KeyError`` with valid options listed."""
    try:
        return _PAGES_BY_ID[str(page_id).strip()]
    except KeyError:
        raise KeyError(
            f"Unknown page id {page_id!r}; expected one of {list(_PAGES_BY_ID)}"
        ) from None


def page_by_route(route: str) -> PageDefinition:
    """Return the page matched by an existing dashboard route/title."""
    try:
        return _ROUTES_BY_TITLE[str(route).strip()]
    except KeyError:
        raise KeyError(
            f"Unknown route {route!r}; expected one of {list(_ROUTES_BY_TITLE)}"
        ) from None


def group_by_key(key: str) -> NavGroup:
    """Return a group by key, raising ``KeyError`` with valid options listed."""
    try:
        return _GROUP_BY_KEY[str(key).strip().upper()]
    except KeyError:
        raise KeyError(
            f"Unknown navigation group {key!r}; expected one of {list(_GROUP_BY_KEY)}"
        ) from None


def group_for(page_id: str) -> NavGroup:
    """Return the group a page belongs to."""
    return group_by_key(page_by_id(page_id).group)


def group_for_page(page_id: str) -> NavGroup:
    """Legacy alias kept for call sites that imported ``group_for_page``."""
    return group_for(page_id)


def pages_in_group(key: str) -> tuple[PageDefinition, ...]:
    """Pages belonging to one group, in display order."""
    wanted = group_by_key(key).key
    return tuple(page for page in PAGES if page.group == wanted)


def resolve_page(candidate: Any) -> str:
    """Coerce arbitrary state into a valid page id.

    Unknown, empty or malformed values fall back to :data:`DEFAULT_PAGE` so a
    stale session key can never strand the shell.
    """
    if candidate is None:
        return DEFAULT_PAGE
    text = str(candidate).strip()
    if not text:
        return DEFAULT_PAGE
    # Prefer id lookup first (new registry), then route lookup (legacy dispatch).
    try:
        return page_by_id(text).id
    except KeyError:
        pass
    try:
        return page_by_route(text).id
    except KeyError:
        return DEFAULT_PAGE


def resolve_page_title(candidate: Any) -> str:
    """Return the display title for a page id or route, falling back to the default page title."""
    page = page_by_id(resolve_page(candidate))
    return page.title


def breadcrumb_for(page_id: str) -> list[str]:
    """``CMIDO > Group > Title`` trail for a page id."""
    return page_by_id(resolve_page(page_id)).breadcrumb


def page_title(page_id: str) -> str:
    """Display title of a page."""
    return page_by_id(resolve_page(page_id)).title


def page_description(page_id: str) -> str:
    """Short description of a page (used by sidebar tooltips and planned-page panels)."""
    return page_by_id(resolve_page(page_id)).description


def page_group_label(page_id: str) -> str:
    """Label of the group a page belongs to."""
    return group_for(page_id).label


def page_research_stage(page_id: str) -> str | None:
    """Research stage attached to a page, if any."""
    return page_by_id(resolve_page(page_id)).research_stage


def page_is_available(page_id: str) -> bool:
    """Whether a page currently renders real content."""
    return page_by_id(resolve_page(page_id)).is_available


def page_is_planned(page_id: str) -> bool:
    """Whether a page is a planned future workspace."""
    return page_by_id(resolve_page(page_id)).is_planned


def page_future_phase(page_id: str) -> str | None:
    """Implementation phase a planned page will be delivered in, if any."""
    return page_by_id(resolve_page(page_id)).future_phase


def page_placeholder_phase(page_id: str) -> str | None:
    """For planned pages, the phase label shown in the placeholder panel."""
    page = page_by_id(resolve_page(page_id))
    return page.future_phase or "Later phase"


def page_placeholder_reason(page_id: str) -> str:
    """One-line honest reason a page is not yet available."""
    page = page_by_id(resolve_page(page_id))
    if page.is_available:
        return ""
    return page.evidence_state_note or "Planned workspace"


def legacy_route_for(page_id: str) -> str:
    """Route/title string used by the existing ``elif page == ...`` dispatch.

    Available pages expose a route; planned pages do not participate in the live
    dispatch yet, so this returns the empty string for them.
    """
    page = page_by_id(resolve_page(page_id))
    return page.route


# ---------------------------------------------------------------------------
# HTML builders (pure functions, no Streamlit import here)
# ---------------------------------------------------------------------------

def build_nav_group_header(group: NavGroup) -> str:
    """Grouped sidebar section header for a navigation group."""
    return build_sidebar_group(group.label, group.caption)


def build_nav_item_html(item: PageDefinition, *, active: bool = False) -> str:
    """Sidebar destination row, marked active for the current page."""
    classes = ["cmido-nav-item"]
    if active:
        classes.append("cmido-nav-item--active")
    group_attr = f' data-group="{_escape(item.group)}"' if item.group else ""
    return (
        f'<div class="{ " ".join(classes) }"{group_attr} '
        f'data-slug="{_escape(item.slug)}">{_escape(item.display)}</div>'
    )


def build_nav_legend() -> str:
    """Compact legend explaining the four navigation groups."""
    parts = [
        '<div class="cmido-nav-legend">',
        f'<span class="cmido-nav-legend-title">{theme.APP_NAME} shell</span>',
    ]
    for group in nav_groups():
        parts.append(
            f'<span class="cmido-nav-legend-item">'
            f'<strong>{group.label}</strong>'
            f'<span>{group.caption}</span>'
            f"</span>"
        )
    parts.append("</div>")
    return "".join(parts)


def build_nav_breadcrumb(page_id: str) -> str:
    """Main-area breadcrumb for a page id."""
    return build_breadcrumb(breadcrumb_for(page_id))


def build_future_page_panel(page_id: str) -> str:
    """Honest placeholder panel for a planned page.

    This deliberately contains no fabricated numbers, charts or KPIs. It states
    what the workspace will cover and which phase will deliver it.
    """
    page = page_by_id(resolve_page(page_id))
    assert page.is_planned, f"build_future_page_panel called for an available page: {page.id!r}"
    parts: list[str] = [
        '<div class="cmido-future-page">',
        f'<p class="cmido-future-page-status">Planned workspace</p>',
        f'<p class="cmido-page-title">{_escape(page.title)}</p>',
        f'<p class="cmido-page-subtitle">{_escape(page.description)}</p>',
    ]
    if page.research_stage:
        parts.append(
            f'<p class="cmido-table-note">Research stage: {_escape(page.research_stage)}</p>'
        )
    parts.append(
        f'<p class="cmido-table-note">Delivery: {_escape(page_future_phase(page.id))}</p>'
    )
    parts.append("</div>")
    return "".join(parts)


def build_footer(text: str | None = None) -> str:
    """Restrained dashboard footer reuse from the design system."""
    from .sections import build_footer as _build_footer

    return _build_footer(text)


# ---------------------------------------------------------------------------
# Manifest + validation
# ---------------------------------------------------------------------------

def nav_manifest() -> list[dict[str, Any]]:
    """Serialisable snapshot of the registry (audits, tests, docs)."""
    manifest: list[dict[str, Any]] = []
    for group in nav_groups():
        for page in pages_in_group(group.key):
            manifest.append(
                {
                    "id": page.id,
                    "title": page.title,
                    "slug": page.slug,
                    "group": group.key,
                    "group_label": group.label,
                    "order": page_order(page.id),
                    "icon": page.icon,
                    "description": page.description,
                    "research_stage": page.research_stage,
                    "provenance": page.provenance,
                    "implementation": page.implementation.value,
                    "route": page.route,
                    "is_planned": page.is_planned,
                    "breadcrumb": page.breadcrumb,
                    "future_phase": page.future_phase,
                }
            )
    return manifest


def page_order(page_id: str) -> int:
    """Display order of a page within the shell."""
    for index, page in enumerate(PAGES):
        if page.id == resolve_page(page_id):
            return index
    raise KeyError(f"Unknown page id {page_id!r}")


def validate_shell() -> list[str]:
    """Return a list of registry defects; an empty list means healthy.

    The application surfaces any defects as a designed status state rather than
    letting a malformed registry fail deep inside routing.
    """
    problems: list[str] = []

    if DEFAULT_PAGE not in _PAGES_BY_ID:
        problems.append(f"DEFAULT_PAGE {DEFAULT_PAGE!r} is not a registered page")

    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    seen_routes: set[str] = set()
    for page in PAGES:
        if not page.id.strip():
            problems.append("A page has a blank id")
        if page.id in seen_ids:
            problems.append(f"Duplicate page id {page.id!r}")
        seen_ids.add(page.id)
        if not page.slug:
            problems.append(f"Page {page.id!r} produces an empty slug")
        if page.slug in seen_slugs:
            problems.append(f"Duplicate page slug {page.slug!r}")
        seen_slugs.add(page.slug)
        if page.group not in _GROUP_BY_KEY:
            problems.append(f"Page {page.id!r} references unknown group {page.group!r}")
        if page.research_stage is not None:
            theme.resolve_research_stage(page.research_stage)
        if page.provenance is not None:
            theme.resolve_provenance(page.provenance)
        if page.route:
            if page.route in seen_routes:
                problems.append(f"Duplicate route {page.route!r}")
            seen_routes.add(page.route)
        if page.is_planned:
            if not page.title.strip():
                problems.append(f"Planned page {page.id!r} has a blank title")
            if not page.description.strip():
                problems.append(f"Planned page {page.id!r} has no description")
        if page.is_available and not page.route:
            problems.append(f"Available page {page.id!r} has no route for the existing dispatch")

    for group in NAV_GROUPS:
        if not group.label.strip():
            problems.append(f"Group {group.key!r} has a blank label")
        if not pages_in_group(group.key):
            problems.append(f"Group {group.key!r} has no pages")

    orders = [group.order for group in NAV_GROUPS]
    if len(set(orders)) != len(orders):
        problems.append("Navigation groups have duplicate order values")

    # Every existing dashboard route must map back to exactly one available page.
    used_routes = {page.route for page in PAGES if page.route}
    for route in used_routes:
        page = page_by_route(route)
        if not page.is_available:
            problems.append(f"Route {route!r} maps to a planned page {page.id!r}")

    return problems


def current_page_from_session(session: Any) -> str:
    """Resolve the active page id from a Streamlit session dict, defaulting safely."""
    candidate = None
    if session is not None:
        candidate = session.get(NAV_SESSION_KEY)
    return resolve_page(candidate)


def set_current_page(session: Any, page_id: str) -> None:
    """Store an active page id in a Streamlit session dict if the session supports it."""
    if session is not None and hasattr(session, "__setitem__"):
        session[NAV_SESSION_KEY] = resolve_page(page_id)


# Re-export the escape helper used by the HTML builders so navigation.py does
# not import Streamlit indirectly through sections.
# _escape lives in sections.py, not theme.py. Import it once so the HTML
# builders here stay independent of Streamlit.
from .sections import _escape as theme__escape

# Stable alias for the HTML builders in this module.
_escape = theme__escape