"""Card components for the CMIDO dashboard design system.

Cards are *presentation only*.  They receive already-computed values and
describe them; they never derive a scientific conclusion, never read an
artifact and never infer provenance on the user's behalf.

Available cards:

* :func:`build_kpi` — the premium KPI card (label / value / unit / delta /
  status / description / provenance / research stage).
* :func:`build_kpi_grid` — responsive KPI grid HTML for equal-height cards.
* :func:`build_chart_card` — titled container for a Plotly figure.
* :func:`build_table_card` — titled container for a dataframe.
* :func:`build_methodology_card` — explanation + key metric + evidence state.
* :func:`build_publication_status` — release / evidence readiness summary.
* :func:`build_legacy_kpi` — compact KPI compatible with the 8L dashboard rows.
"""

from __future__ import annotations

from typing import Any, Sequence

from .badges import (
    build_badge_row,
    build_evidence_state_badge,
    build_provenance_badge,
    build_research_stage_badge,
    build_status_badge,
    build_uncertainty_badge,
)
from .formatting import is_missing
from .states import EvidenceState
from .theme import (
    BORDER_MUTED,
    DANGER,
    INFO,
    MUTED_TEXT,
    POSITIVE,
    POSITIVE_SOFT,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
    SPACING,
    STATUS_PALETTE,
    SURFACE_INSET,
    TYPOGRAPHY,
    WARNING,
    WARNING_SOFT,
    status_colors,
    status_title,
)

#: Semantic colours accepted by :func:`build_kpi` for the value / delta.
DELTA_COLORS = {
    "positive": POSITIVE,
    "negative": DANGER,
    "warning": WARNING,
    "neutral": SECONDARY_TEXT,
    "info": INFO,
    "muted": MUTED_TEXT,
}


def _escape(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_delta_badge(delta: Any, *, direction: str | None = None, suffix: str = "") -> str:
    """Render a delta with an explicit sign and a text arrow.

    ``direction`` may be ``"positive"``/``"negative"``/``"warning"``/
    ``"neutral"``; when omitted it is inferred from the sign of ``delta``.
    """
    if is_missing(delta):
        return ""
    value = float(delta)
    if direction is None:
        direction = "positive" if value >= 0 else "negative"
    key = direction if direction in DELTA_COLORS else "neutral"
    color = DELTA_COLORS[key]
    soft = {
        "positive": POSITIVE_SOFT,
        "negative": STATUS_PALETTE["invalid"]["soft"],
        "warning": WARNING_SOFT,
        "neutral": SURFACE_INSET,
        "info": STATUS_PALETTE["loading"]["soft"],
        "muted": SURFACE_INSET,
    }[key]
    sign = "+" if value >= 0 else "-"
    text = f"{sign}{abs(value):,.2f}{suffix}"
    arrow = "▲" if value >= 0 else "▼"
    return build_badge_row_single(text, color=color, soft=soft, icon=arrow, title=f"Change: {text}")


def build_badge_row_single(text: str, *, color: str, soft: str, icon: str, title: str) -> str:
    """Small helper used by :func:`build_delta_badge`."""
    from .badges import build_badge

    return build_badge(text, color=color, soft=soft, border=soft, icon=icon, title=title)


def build_kpi(
    label: str,
    value: Any,
    *,
    unit: str | None = None,
    delta: Any = None,
    delta_direction: str | None = None,
    status: Any = None,
    description: str | None = None,
    provenance: Any = None,
    research_stage: Any = None,
    uncertainty: Any = None,
    icon: str | None = None,
    value_color: str | None = None,
) -> str:
    """Build a premium KPI card.

    The card deliberately separates three layers so a reader never confuses
    them:

    1. ``VALUE`` — the number plus its unit, largest type on the card.
    2. ``INTERPRETATION`` — optional description and delta.
    3. ``PROVENANCE`` — provenance / research-stage / evidence badges.

    Parameters mirror the 10A.3 KPI specification.  ``status`` accepts an
    :class:`~src.construction.dashboard_ui.states.EvidenceState`, an
    ``ArtifactStatus`` or any string; ``uncertainty`` accepts an
    :class:`~src.construction.dashboard_ui.states.UncertaintyState`.

    No CMIDO research value is hard-coded here — every number is a parameter.
    """
    label_html = f'<p class="cmido-kpi-label">{_escape(label)}</p>'
    if icon:
        label_html = f'<p class="cmido-kpi-label">{_escape(icon)} {_escape(label)}</p>'

    value_text = "—" if is_missing(value) else _escape(value)
    value_style = TYPOGRAPHY["kpi_value"]
    if value_color:
        value_style = value_style.replace(PRIMARY_TEXT, value_color)
    unit_html = f' <span class="cmido-kpi-unit">{_escape(unit)}</span>' if unit else ""
    value_html = f'<p class="cmido-kpi-value" style="{value_style}">{value_text}{unit_html}</p>'

    parts: list[str] = [label_html, value_html]

    if delta is not None and not is_missing(delta):
        parts.append(f'<p class="cmido-kpi-delta">{build_delta_badge(delta, direction=delta_direction)}</p>')

    badges: list[str] = []
    if status is not None:
        badges.append(build_evidence_state_badge(status))
    if provenance is not None:
        badges.append(build_provenance_badge(provenance))
    if research_stage is not None:
        badges.append(build_research_stage_badge(research_stage))
    if uncertainty is not None:
        badges.append(build_uncertainty_badge(uncertainty))
    if badges:
        parts.append(build_badge_row(badges))

    if description:
        parts.append(f'<p class="cmido-kpi-description">{_escape(description)}</p>')

    body = "".join(parts)
    return f'<div class="cmido-kpi">{body}</div>'


def build_kpi_grid(items: Sequence[dict[str, Any]]) -> str:
    """Build a responsive KPI grid from a list of :func:`build_kpi` kwargs.

    Uses CSS ``auto-fit`` so the layout reflows on wide desktop, small desktop
    and with the sidebar expanded — no fixed pixel widths anywhere.
    """
    cards = [build_kpi(**item) for item in items]
    if not cards:
        return ""
    columns = "repeat(auto-fit, minmax(190px, 1fr))"
    style = (
        f"display:grid;grid-template-columns:{columns};gap:{SPACING['sm']};"
        f"margin-bottom:{SPACING['md']};"
    )
    return f'<div class="cmido-kpi-grid" style="{style}">' + "".join(cards) + "</div>"


def build_unavailable_reason(*, label: str, reason: str) -> dict[str, str]:
    """Structured 'why this evidence is unavailable' item.

    Returns a plain mapping so presentation layers can render it as a list
    entry, a table row or a badge stack without re-deriving the wording.
    """
    return {"label": label, "reason": reason}


def build_chart_card(
    figure: Any = None,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    caption: str | None = None,
    research_stage: Any = None,
    provenance: Any = None,
    evidence_state: Any = None,
    uncertainty: Any = None,
    height: int | None = None,
) -> str:
    """Wrap a Plotly figure in a titled, provenance-aware container.

    The figure itself is rendered by Streamlit (``st.plotly_chart``) directly
    after this header so the chart stays interactive; this builder produces the
    header block and returns the container opening markup.
    """
    header_parts: list[str] = []
    if title:
        header_parts.append(f'<p class="cmido-card-title">{_escape(title)}</p>')
    if subtitle:
        header_parts.append(f'<p class="cmido-section-subtitle">{_escape(subtitle)}</p>')
    badges: list[str] = []
    if research_stage is not None:
        badges.append(build_research_stage_badge(research_stage))
    if evidence_state is not None:
        badges.append(build_evidence_state_badge(evidence_state))
    if provenance is not None:
        badges.append(build_provenance_badge(provenance))
    if uncertainty is not None:
        badges.append(build_uncertainty_badge(uncertainty))
    if badges:
        header_parts.append(build_badge_row(badges))
    if caption:
        header_parts.append(f'<p class="cmido-table-note">{_escape(caption)}</p>')
    if not header_parts:
        header_parts.append(f'<p class="cmido-card-title">{_escape("Figure")}</p>')
    if height:
        header_parts.append(
            f'<p class="cmido-table-note" data-chart-height="{int(height)}">Rendered height {int(height)} px</p>'
        )
    return f'<div class="cmido-card">{"".join(header_parts)}'


def build_table_card(
    frame: Any = None,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    caption: str | None = None,
    source: str | None = None,
    provenance: Any = None,
    research_stage: Any = None,
    evidence_state: Any = None,
    uncertainty: Any = None,
    empty_message: str | None = None,
) -> str:
    """Build the header block for a table card (the frame is rendered by Streamlit).

    ``frame`` may be ``None`` or any object exposing ``empty``/``len``; when the
    table has no rows the card advertises an empty state instead of rendering a
    blank container, so the page never shows a silent void.
    """
    header_parts: list[str] = []
    if title:
        header_parts.append(f'<p class="cmido-card-title">{_escape(title)}</p>')
    if subtitle:
        header_parts.append(f'<p class="cmido-section-subtitle">{_escape(subtitle)}</p>')

    badges: list[str] = []
    if research_stage is not None:
        badges.append(build_research_stage_badge(research_stage))
    if evidence_state is not None:
        badges.append(build_evidence_state_badge(evidence_state))
    if provenance is not None:
        badges.append(build_provenance_badge(provenance))
    if uncertainty is not None:
        badges.append(build_uncertainty_badge(uncertainty))
    if badges:
        header_parts.append(build_badge_row(badges))

    if is_empty_frame(frame):
        header_parts.append(
            f'<p class="cmido-table-note">{_escape(empty_message or "No rows available for this table.")}</p>'
        )
    elif caption:
        header_parts.append(f'<p class="cmido-table-note">{_escape(caption)}</p>')

    if source:
        header_parts.append(f'<p class="cmido-table-note">Source: {_escape(source)}</p>')

    if not header_parts:
        header_parts.append('<p class="cmido-card-title">Table</p>')
    return f'<div class="cmido-card">{"".join(header_parts)}'


def is_empty_frame(frame: Any) -> bool:
    """Return True when a dataframe-like object carries no rows."""
    if frame is None:
        return True
    empty = getattr(frame, "empty", None)
    if isinstance(empty, bool):
        return empty
    try:
        return len(frame) == 0
    except TypeError:
        return False


def build_methodology_card(
    title: str,
    explanation: str,
    *,
    key_metric: Any = None,
    key_metric_label: str | None = None,
    key_metric_unit: str | None = None,
    evidence_state: Any = None,
    provenance: Any = None,
    research_stage: Any = None,
    uncertainty: Any = None,
    detail: str | None = None,
) -> str:
    """Build a methodology / insight card.

    Presentation only: the caller supplies both the explanation and the metric,
    so the card can never infer a scientific conclusion on its own.
    """
    parts = [f'<p class="cmido-card-title">{_escape(title)}</p>']

    badges: list[str] = []
    if research_stage is not None:
        badges.append(build_research_stage_badge(research_stage))
    if evidence_state is not None:
        badges.append(build_evidence_state_badge(evidence_state))
    if provenance is not None:
        badges.append(build_provenance_badge(provenance))
    if uncertainty is not None:
        badges.append(build_uncertainty_badge(uncertainty))
    if badges:
        parts.append(build_badge_row(badges))

    parts.append(f'<p class="cmido-card-body">{_escape(explanation)}</p>')

    if key_metric is not None:
        metric_label = f'{_escape(key_metric_label)}: ' if key_metric_label else ""
        unit = f' <span class="cmido-kpi-unit">{_escape(key_metric_unit)}</span>' if key_metric_unit else ""
        parts.append(
            f'<p class="cmido-card-metric">{metric_label}{_escape(key_metric)}{unit}</p>'
        )

    if detail:
        parts.append(f'<p class="cmido-card-body" style="margin-top:0.5rem">{_escape(detail)}</p>')

    return f'<div class="cmido-card">{"".join(parts)}</div>'


def build_publication_status(
    *,
    title: str = "Evidence readiness",
    rows: Sequence[tuple[str, Any]] = (),
    status: Any = EvidenceState.VALID,
    note: str | None = None,
) -> str:
    """Build a compact publication / release readiness summary.

    ``rows`` is a sequence of ``(label, status)`` pairs; each row is rendered
    with an explicit status badge rather than a coloured dot.
    """
    parts = [f'<p class="cmido-card-title">{_escape(title)}</p>']
    parts.append(build_badge_row([build_status_badge(status)]))
    if note:
        parts.append(f'<p class="cmido-card-body">{_escape(note)}</p>')

    if rows:
        items = []
        for label, row_status in rows:
            style = status_colors(row_status)
            items.append(
                '<div style="display:flex;justify-content:space-between;gap:0.6rem;'
                f'padding:0.3rem 0;border-bottom:1px solid {BORDER_MUTED};">'
                f'<span style="{TYPOGRAPHY["table_cell"]}">{_escape(label)}</span>'
                f'<span style="color:{style["color"]};font-size:0.78rem;font-weight:700;">'
                f'{_escape(status_title(row_status))}</span></div>'
            )
        parts.append('<div style="margin-top:0.5rem">' + "".join(items) + "</div>")

    return f'<div class="cmido-card">{"".join(parts)}</div>'


def build_legacy_kpi(icon: str | None, label: str, value: Any, *, description: str | None = None) -> str:
    """Compact KPI compatible with the existing 8L dashboard rows.

    Lets the current pages adopt the design system incrementally without
    rewriting their scientific calculations.
    """
    return build_kpi(label, value, icon=icon, description=description)
