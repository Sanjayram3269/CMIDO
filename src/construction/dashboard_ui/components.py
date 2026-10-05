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

from typing import Any, Sequence

from .badges import build_badge_row, build_evidence_state_badge, build_provenance_badge, build_research_stage_badge
from .cards import build_chart_card, build_kpi, build_table_card
from .charts import get_chart_config, get_plotly_theme
from .formatting import is_missing
from .sections import (
    build_artifact_state,
    build_empty_state,
    build_error_state,
    build_page_header,
    build_section_header,
    build_status_banner,
)
from .tables import prepare_table
from .theme import build_css

#: Session key guarding one-time CSS injection.
CSS_SESSION_KEY = "_cmido_css_injected"


def _st() -> Any:
    """Return the Streamlit module, imported lazily on first render."""
    import streamlit

    return streamlit


def inject_css(*, force: bool = False) -> bool:
    """Emit the design-system stylesheet once per Streamlit session.

    Returns ``True`` when the stylesheet was written on this call.
    """
    st = _st()
    if not force and st.session_state.get(CSS_SESSION_KEY):
        return False
    st.markdown(build_css(), unsafe_allow_html=True)
    st.session_state[CSS_SESSION_KEY] = True
    return True


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
