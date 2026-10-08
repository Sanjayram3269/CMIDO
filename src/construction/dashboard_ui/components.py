"""Streamlit render layer for the CMIDO design system.

This is the only module in :mod:`src.construction.dashboard_ui` that touches
Streamlit, and it does so through a lazy accessor: importing the design system
(for tests, tooling or a future non-Streamlit renderer) must not require
Streamlit to be installed.

Every function here is a thin adapter. It renders markup produced by the pure
builders in :mod:`theme`, :mod:`badges`, :mod:`cards`, :mod:`sections`,
:mod:`charts` and :mod:`tables`, so the visual contract lives in one place.

Rules enforced by this layer:

* no research calculations - values arrive fully computed;
* no artifact access - data comes from the 10A.2-B snapshot or page-local
  engines;
* no raw Python exception is rendered as the primary message;
* no expensive work per rerun (the stylesheet is emitted once per session).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .badges import build_badge_row, build_evidence_state_badge, build_provenance_badge, build_research_stage_badge
from .cards import build_chart_card, build_kpi, build_table_card
from .charts import get_chart_config, get_plotly_theme
from .formatting import is_missing
from .navigation import (
    NAV_SESSION_KEY,
    breadcrumb_for,
    build_future_page_panel,
    build_nav_breadcrumb,
    build_nav_group_header,
    build_nav_item_html,
    build_nav_legend,
    group_for,
    nav_groups,
    page_by_id,
    page_description,
    page_future_phase,
    page_is_planned,
    pages_in_group,
    pages,
    resolve_page,
)
from .sections import (
    build_artifact_state,
    build_empty_state as _sections_empty_state,
    build_error_state,
    build_page_header,
    build_section_header,
    build_status_banner,
)
from .tables import prepare_table
from .theme import build_css

#: Session key recording that CSS has been emitted at least once this session.
CSS_SESSION_KEY = "_cmido_css_injected"


def _st() -> Any:
    """Return the Streamlit module, imported lazily on first render."""
    import streamlit

    return streamlit


def inject_css(*, force: bool = False) -> bool:
    """Emit the design-system stylesheet.

    Streamlit rebuilds the DOM on every run *and* on every page reload, while
    session state survives reconnections. A once-per-session guard therefore
    left a reloaded page unstyled: the run after a reload remembered that the
    CSS had been emitted but no longer carried the element. The stylesheet is
    now emitted on every run — Streamlit replaces the markdown element in
    place, so exactly one ``<style>`` block exists — and the return value
    still reports whether this is the session's first emission.

    ``force`` is kept for API compatibility; emission is unconditional.
    """
    st = _st()
    first_emission = not st.session_state.get(CSS_SESSION_KEY)
    st.markdown(build_css(), unsafe_allow_html=True)
    st.session_state[CSS_SESSION_KEY] = True
    return first_emission


# ---------------------------------------------------------------------------
# Generic rendering
# ---------------------------------------------------------------------------
def render_html(markup: str) -> None:
    """Render builder HTML output."""
    if markup:
        _st().markdown(markup, unsafe_allow_html=True)


def render_app_header() -> None:
    """Render the CMIDO brand lockup."""
    from .sections import build_app_header

    render_html(build_app_header())


def render_page_header(
    title: str,
    subtitle: str | None = None,
    *,
    context: str | None = None,
    research_stage: Any = None,
    provenance: Any = None,
    evidence_state: Any = None,
) -> None:
    """Render a page-level header with optional metadata badges."""
    render_html(
        build_page_header(
            title,
            subtitle,
            context=context,
            research_stage=research_stage,
            provenance=provenance,
            evidence_state=evidence_state,
        )
    )


def render_section_header(
    title: str,
    subtitle: str | None = None,
    *,
    research_stage: Any = None,
    evidence_state: Any = None,
    methodology: str | None = None,
    provenance: Any = None,
    uncertainty: Any = None,
) -> None:
    """Render a section header with research / evidence metadata."""
    render_html(
        build_section_header(
            title,
            subtitle,
            research_stage=research_stage,
            evidence_state=evidence_state,
            methodology=methodology,
            provenance=provenance,
            uncertainty=uncertainty,
        )
    )


# ---------------------------------------------------------------------------
# KPI rendering
# ---------------------------------------------------------------------------
def render_kpi(
    label: str,
    value: Any,
    *,
    unit: str | None = None,
    delta: Any = None,
    delta_direction: str | None = None,
    status: Any = None,
    evidence_state: Any = None,
    uncertainty: Any = None,
    description: str | None = None,
    provenance: Any = None,
    research_stage: Any = None,
    icon: str | None = None,
) -> None:
    """Render one KPI card through the design system.

    ``status`` and ``evidence_state`` are aliases: ``evidence_state`` reads
    better on research panels, ``status`` on operational ones.
    """
    render_html(
        build_kpi(
            label,
            value,
            unit=unit,
            delta=delta,
            delta_direction=delta_direction,
            status=status if status is not None else evidence_state,
            description=description,
            provenance=provenance,
            research_stage=research_stage,
            uncertainty=uncertainty,
            icon=icon,
        )
    )


def render_kpi_columns(
    items: Sequence[dict[str, Any]],
    *,
    columns: int | None = None,
) -> None:
    """Render a row of KPI cards using responsive Streamlit columns.

    ``columns`` defaults to ``len(items)`` capped at 4, so a long KPI list wraps
    instead of collapsing into unreadable widths on a small desktop.
    """
    st = _st()
    entries = list(items)
    if not entries:
        return
    count = max(1, columns or min(len(entries), 4))
    slots = st.columns(count)
    for index, item in enumerate(entries):
        with slots[index % count]:
            render_kpi(**item)


def render_legacy_kpi_row(items: Sequence[tuple[str, str, Any]]) -> None:
    """Render ``(icon, label, value)`` rows used by the existing 8L pages.

    Lets the current pages adopt the design system without rewriting their
    scientific calculations.
    """
    st = _st()
    entries = list(items)
    if not entries:
        return
    count = max(1, min(len(entries), 4))
    slots = st.columns(count)
    for index, (icon, label, value) in enumerate(entries):
        with slots[index % count]:
            render_kpi(label, value, icon=icon)


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------
def render_chart(
    figure: Any,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    caption: str | None = None,
    research_stage: Any = None,
    provenance: Any = None,
    evidence_state: Any = None,
    uncertainty: Any = None,
    use_container_width: bool = True,
    chart_config: dict[str, Any] | None = None,
) -> None:
    """Render a Plotly figure inside the shared chart card.

    The figure itself is expected to already carry the shared theme (see
    :func:`apply_chart_theme`); this function supplies the container header,
    provenance badges and the standard ``st.plotly_chart`` configuration.
    """
    render_html(
        build_chart_card(
            title=title,
            subtitle=subtitle,
            caption=caption,
            research_stage=research_stage,
            provenance=provenance,
            evidence_state=evidence_state,
            uncertainty=uncertainty,
        )
    )
    if figure is not None:
        _st().plotly_chart(
            figure,
            use_container_width=use_container_width,
            config=chart_config or get_chart_config(),
        )
        render_html("</div>")


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------
def render_table(
    frame: Any,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    caption: str | None = None,
    source: str | None = None,
    provenance: Any = None,
    research_stage: Any = None,
    evidence_state: Any = None,
    uncertainty: Any = None,
    decimals: int | None = None,
    empty_message: str | None = None,
) -> dict[str, Any]:
    """Render a dataframe through the shared table contract.

    Returns the :func:`~src.construction.dashboard_ui.tables.prepare_table`
    payload so callers can reuse the computed row/column counts.
    """
    prepared = prepare_table(frame) if decimals is None else prepare_table(frame, decimals=decimals)
    render_html(
        build_table_card(
            frame=prepared["frame"],
            title=title,
            subtitle=subtitle,
            caption=caption,
            source=source,
            provenance=provenance,
            research_stage=research_stage,
            evidence_state=evidence_state,
            uncertainty=uncertainty,
            empty_message=empty_message,
        )
    )
    if not prepared["is_empty"]:
        _st().dataframe(prepared["frame"], **prepared["config"])
    render_html("</div>")
    return prepared


# ---------------------------------------------------------------------------
# State rendering
# ---------------------------------------------------------------------------
def render_status_banner(
    message: str,
    *,
    status: Any = "attention",
    title: str | None = None,
    detail: str | None = None,
    diagnostics: str | None = None,
    hint: str | None = None,
) -> None:
    """Render a plain-language status banner."""
    render_html(
        build_status_banner(
            message,
            status=status,
            title=title,
            detail=detail,
            diagnostics=diagnostics,
            hint=hint,
        )
    )


def render_error_state(
    headline: str,
    *,
    description: str,
    diagnostics: str | None = None,
    hint: str | None = None,
) -> None:
    """Render an error state that keeps the exception out of the headline."""
    render_html(
        build_error_state(
            headline,
            description=description,
            diagnostics=diagnostics,
            hint=hint,
        )
    )


def render_empty_state(
    message: str,
    *,
    title: str | None = "No data to display",
    hint: str | None = None,
) -> None:
    """Render the designed empty state."""
    render_html(build_empty_state(message, title=title, hint=hint))


def render_artifact_state(
    artifact_id: str,
    status: Any,
    *,
    description: str | None = None,
    diagnostics: str | None = None,
    stage: Any = None,
    provenance: Any = None,
) -> None:
    """Render the availability state of a single validated artifact."""
    render_html(
        build_artifact_state(
            artifact_id,
            status,
            description=description,
            diagnostics=diagnostics,
            stage=stage,
            provenance=provenance,
        )
    )


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------
def render_badges(*badges: str) -> None:
    """Render a row of badges produced by the badge builders."""
    render_html(build_badge_row(list(badges)))


# ---------------------------------------------------------------------------
# Application shell (10A.4)
# ---------------------------------------------------------------------------
def render_breadcrumb(trail: Sequence[str]) -> None:
    """Render a navigation trail such as CMIDO / Decision / Schedule."""
    from .sections import build_breadcrumb

    render_html(build_breadcrumb(trail))


def render_nav_legend() -> None:
    """Render the compact explanation of the navigation groups."""
    render_html(build_nav_legend())


def render_sidebar_navigation(active: Any = None, *, rerun: bool = True) -> str:
    """Render the grouped sidebar navigation and return the active page id.

    The selection is held in session state rather than in a flat radio widget
    so the sidebar can present the pages in their four research groups. Unknown
    or missing state resolves to the default page instead of raising, which keeps
    a stale session from stranding the shell.

    For planned pages the button still renders, but the live dispatch below treats
    them as ``st.stop()`` placeholders so navigating to a future workspace surfaces
    the honest ``build_future_page_panel`` rather than silently dropping through to
    the next ``elif`` branch.
    """
    st = _st()

    current = resolve_page(
        active if active is not None else st.session_state.get(NAV_SESSION_KEY)
    )
    st.session_state[NAV_SESSION_KEY] = current

    for group in nav_groups():
        members = pages_in_group(group.key)
        if not members:
            continue
        render_html(build_nav_group_header(group))
        for page in members:
            selected = st.button(
                page.display,
                key=f"cmido_nav_{page.slug}",
                use_container_width=True,
                type="primary" if page.id == current else "secondary",
                help=page_description(page.id) or None,
            )
            if selected and page.id != current:
                st.session_state[NAV_SESSION_KEY] = page.id
                if rerun:
                    st.rerun()
    return current


def render_future_page_panel(page_id: str) -> None:
    """Render an honest placeholder panel for a planned page.

    This deliberately contains no fabricated numbers, charts or KPIs. It states
    what the workspace will cover and which phase will deliver it, then stops the
    page so the dashboard does not fall through to unrelated content.
    """
    page = page_by_id(resolve_page(page_id))
    if not page.is_planned:
        return
    render_html(build_future_page_panel(page.id))
    st = _st()
    st.divider()
    render_status_banner(
        "Planned workspace — not yet available.",
        status="optional",
        title=f"{page.title} ({page_future_phase(page.id)})",
        hint=page_description(page.id),
    )
    st.stop()


def render_active_nav_item(label: str) -> None:
    """Render the sidebar-style active row for a destination (audit/tests)."""
    page = page_by_id(resolve_page(label))
    render_html(build_nav_item_html(page, active=True))


def nav_breadcrumb(label: str) -> list[str]:
    """Return the breadcrumb trail for a destination without rendering it."""
    return breadcrumb_for(resolve_page(label))


def page_title_st(label: str) -> str:
    """Convenience for Streamlit pages that already carry a legacy route string."""
    return page_title(resolve_page(label))


def render_metadata_badges(
    *,
    research_stage: Any = None,
    provenance: Any = None,
    evidence_state: Any = None,
) -> None:
    """Render the standard research-stage / provenance / evidence badge trio."""
    badges: list[str] = []
    if research_stage is not None:
        badges.append(build_research_stage_badge(research_stage))
    if provenance is not None:
        badges.append(build_provenance_badge(provenance))
    if evidence_state is not None:
        badges.append(build_evidence_state_badge(evidence_state))
    render_badges(*badges)


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------
def design_tokens() -> dict[str, Any]:
    """Expose the Plotly layout theme to pages that build their own figures."""
    return get_plotly_theme()


def format_display_value(value: Any, *, unit: str | None = None, decimals: int = 2) -> str:
    """Return a display string for a value that may be missing."""
    from .formatting import format_number

    if is_missing(value):
        return "—"
    text = format_number(value, decimals)
    return f"{text} {unit}".strip() if unit else text


def _escape(text: Any) -> str:
    """Minimal HTML escaping for text injected into builders."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Section blocks (research page layer)
# ---------------------------------------------------------------------------


@dataclass
class SectionBlock:
    """Tagged structural block emitted by the pure dashboard builders.

    ``kind`` selects the render treatment: ``unavailable_block`` renders as a
    dedicated evidence-unavailable panel, ``empty_block`` as a polite no-data
    panel, ``kpi_columns``/``section`` as ordinary content sections.
    """

    kind: str
    title: str | None = None
    body: str = ""
    rows: list[Any] = field(default_factory=list)
    provenance: Any = None
    evidence_state: Any = None
    uncertainty: Any = None
    metadata: dict[str, Any] | None = None

    def __str__(self) -> str:
        parts: list[str] = [self.title or "", self.body or ""]
        parts.extend(str(row) for row in self.rows)
        if self.provenance is not None:
            parts.append(str(self.provenance))
        if self.evidence_state is not None:
            parts.append(str(self.evidence_state))
        return "\n".join(part for part in parts if part)

    def __add__(self, other: Any) -> "SectionBlock":
        """Concatenate two blocks (or a block and an HTML string)."""
        return SectionBlock("section", rows=[self, other])


@dataclass
class TableBlock:
    """A presentation-only table: display headers plus formatted row dicts."""

    headers: list[str]
    rows: list[dict[str, Any]]
    column_config: Any = None
    caption: str | None = None

    def to_frame(self) -> Any:
        """Positional DataFrame so display headers stay authoritative."""
        import pandas as pd

        data = [list(row.values()) for row in self.rows]
        return pd.DataFrame(data, columns=list(self.headers))

    def __str__(self) -> str:
        head = "".join(f"<th>{_escape(h)}</th>" for h in self.headers)
        body_rows = []
        for row in self.rows:
            cells = "".join(f"<td>{_escape(v)}</td>" for v in row.values())
            body_rows.append(f"<tr>{cells}</tr>")
        caption = f"<caption>{_escape(self.caption)}</caption>" if self.caption else ""
        return f"<table>{caption}<thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


@dataclass
class ChartBlock:
    """A Plotly figure deferred to the Streamlit render layer."""

    figure: Any = None
    caption: str | None = None
    config: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.caption or "chart"


@dataclass
class BreadcrumbRow:
    """Breadcrumb trail data rendered by the shell or a page."""

    ids: tuple[str, ...] = ()
    labels: list[str] = field(default_factory=list)
    missing: frozenset[str] = frozenset()

    def __str__(self) -> str:
        return " / ".join(
            f"{label} (planned)" if id_ in self.missing else label
            for id_, label in zip(self.ids, self.labels)
        )


def section_block(kind: str, *, title: str | None = None, body: str = "", **kwargs: Any) -> SectionBlock:
    """Tiny constructor kept for the pure builders in dashboard_ui."""
    return SectionBlock(kind=kind, title=title, body=body, **kwargs)


def build_empty_state(
    message: str | None = None,
    *,
    title: str | None = "No data to display",
    hint: str | None = None,
    body: str | None = None,
) -> str:
    """Render the designed empty state as HTML.

    ``body`` is an alias for ``message`` so research builders can express
    intent with either name; only one of the two should be supplied.
    """
    text = message if message is not None else (body or "")
    return _sections_empty_state(text, title=title, hint=hint)


def build_note_bare(text: str) -> str:
    """A bare note paragraph (no card, no banner) for provenance lines."""
    return f'<p class="cmido-table-note">{_escape(text)}</p>'


def build_unavailable_body(title: str, body: str) -> str:
    """Body HTML for an unavailable block: title plus bullet lines."""
    parts = [
        '<div class="cmido-unavailable-body">',
        f'<p class="cmido-unavailable-title">{_escape(title)}</p>',
        '<ul class="cmido-unavailable-list">',
    ]
    for line in body.splitlines():
        line = line.strip()
        if line:
            parts.append(f'<li class="cmido-unavailable-item">{_escape(line)}</li>')
    parts.append("</ul></div>")
    return "".join(parts)


def build_unavailable_block(
    title: str,
    *,
    body: str,
    provenance: Any = None,
    evidence_state: Any = None,
) -> SectionBlock:
    """A research-grade 'unavailable' block with optional provenance."""
    return SectionBlock(
        "unavailable_block",
        title=title,
        body=build_unavailable_body(title, body),
        provenance=provenance,
        evidence_state=evidence_state,
    )


def build_empty_block(
    message: str,
    *,
    title: str | None = "No data to display",
    hint: str | None = None,
) -> SectionBlock:
    """A designed empty-state panel (no data to display)."""
    return SectionBlock(
        "empty_block",
        title=title,
        body=build_empty_state(message, title=title, hint=hint),
    )


def build_section(*, header: str | None = None, rows: Sequence[Any] = ()) -> SectionBlock:
    """A titled section composed of heterogeneous presentation rows."""
    return SectionBlock("section", body=header or "", rows=list(rows))


def build_kpi_columns(*, cards: Sequence[str]) -> SectionBlock:
    """Wrap pre-built KPI card HTML in the responsive grid."""
    from .cards import SPACING

    if not cards:
        return SectionBlock("kpi_columns", body="")
    style = (
        "display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));"
        f"gap:{SPACING['sm']};margin-bottom:{SPACING['md']};"
    )
    html = f'<div class="cmido-kpi-grid" style="{style}">' + "".join(cards) + "</div>"
    return SectionBlock("kpi_columns", body=html)


def build_table(
    *,
    headers: Sequence[str],
    rows: Sequence[dict[str, Any]],
    column_config: Any = None,
    caption: str | None = None,
) -> TableBlock:
    """A presentation-only table block."""
    return TableBlock(
        headers=list(headers),
        rows=list(rows),
        column_config=column_config,
        caption=caption,
    )


def build_chart(
    chart: Any = None,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    caption: str | None = None,
    research_stage: Any = None,
    provenance: Any = None,
    evidence_state: Any = None,
    uncertainty: Any = None,
    chart_config: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> ChartBlock:
    """Defer a Plotly figure to the Streamlit render layer."""
    return ChartBlock(
        figure=chart,
        caption=caption,
        config=chart_config or config,
    )


def build_unavailable_stack(*, items: Sequence[Any]) -> str:
    """Render structured unavailable reasons as a compact list."""
    parts = ['<ul class="cmido-unavailable-list">']
    for item in items:
        if isinstance(item, Mapping):
            label = item.get("label", "")
            reason = item.get("reason", "")
            parts.append(
                f'<li class="cmido-unavailable-item"><strong>{_escape(label)}</strong> — {_escape(reason)}</li>'
            )
        else:
            parts.append(f'<li class="cmido-unavailable-item">{_escape(item)}</li>')
    parts.append("</ul>")
    return "".join(parts)


def build_breadcrumb(
    *,
    ids: Sequence[str],
    labels_map: Mapping[str, str],
    missing_set: Sequence[str] | set[str] | frozenset[str] = (),
) -> BreadcrumbRow:
    """Structured breadcrumb trail for a research page."""
    return BreadcrumbRow(
        ids=tuple(ids),
        labels=[labels_map.get(id_, id_) for id_ in ids],
        missing=frozenset(missing_set),
    )


def render_section_block(block: Any) -> None:
    """Render any research-page block (recursive) through the shell."""
    if block is None:
        return
    if isinstance(block, SectionBlock):
        if block.body:
            render_html(block.body)
        elif block.title:
            render_html(f'<p class="cmido-section-title">{_escape(block.title)}</p>')
        for row in block.rows:
            render_section_block(row)
        return
    if isinstance(block, TableBlock):
        render_table(block.to_frame(), caption=block.caption)
        return
    if isinstance(block, ChartBlock):
        render_chart(block.figure, caption=block.caption, chart_config=block.config)
        return
    if isinstance(block, dict) and "label" in block and "body" in block:
        label = block.get("label") or ""
        body = block.get("body") or ""
        render_html(
            '<div class="cmido-card">'
            f'<p class="cmido-kpi-label">{_escape(label)}</p>'
            f'<p class="cmido-section-subtitle" style="white-space:pre-wrap">{_escape(body)}</p>'
            "</div>"
        )
        return
    if isinstance(block, str):
        render_html(block)
        return
    render_html(str(block))
