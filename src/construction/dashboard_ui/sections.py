"""Structural components: branding, page/section headers, banners, states.

Nothing here performs a calculation.  Every builder renders text and badges
supplied by the caller, so the same components can serve an engineering page
and a research page without hard-coding either one's conclusions.

Error philosophy (10A.3 requirement): a raw Python exception is never the
primary user experience.  :func:`build_status_banner` renders a plain-language
message and keeps the technical detail as secondary, collapsible diagnostics.
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
from .theme import (
    APP_NAME,
    APP_SHORT_DESCRIPTION,
    APP_TAGLINE,
    BORDER,
    MUTED_TEXT,
    SECONDARY_TEXT,
    SPACING,
    TYPOGRAPHY,
    status_colors,
    status_title,
)


def _escape(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_app_header() -> str:
    """CMIDO brand lockup. Fixed identity — no invented research title."""
    return (
        '<div class="cmido-brand">'
        '<div>'
        f'<p class="cmido-brand-name">{_escape(APP_NAME)}</p>'
        f'<p class="cmido-brand-tagline">{_escape(APP_TAGLINE)}</p>'
        "</div>"
        "</div>"
    )


def build_page_header(
    title: str,
    subtitle: str | None = None,
    *,
    context: str | None = None,
    research_stage: Any = None,
    provenance: Any = None,
    evidence_state: Any = None,
) -> str:
    """Page-level header: title, subtitle and an optional metadata badge row."""
    parts = [f'<p class="cmido-page-title">{_escape(title)}</p>']
    if subtitle:
        parts.append(f'<p class="cmido-page-subtitle">{_escape(subtitle)}</p>')

    badges: list[str] = []
    if research_stage is not None:
        badges.append(build_research_stage_badge(research_stage))
    if evidence_state is not None:
        badges.append(build_evidence_state_badge(evidence_state))
    if provenance is not None:
        badges.append(build_provenance_badge(provenance))
    if badges:
        parts.append(build_badge_row(badges))
    if context:
        parts.append(f'<p class="cmido-table-note">{_escape(context)}</p>')
    return f'<div class="cmido-page-header">{"".join(parts)}</div>'


def build_breadcrumb(trail: Sequence[str]) -> str:
    """Render a navigation trail, e.g. ``RESEARCH > RO2 > Joint propagation``."""
    items = [str(item) for item in trail if str(item).strip()]
    if not items:
        return ""
    chunks = []
    for index, item in enumerate(items):
        if index:
            chunks.append('<span class="cmido-breadcrumb-sep" aria-hidden="true">/</span>')
        chunks.append(f'<span>{_escape(item)}</span>')
    return f'<div class="cmido-breadcrumb">{"".join(chunks)}</div>'


def build_section_header(
    title: str,
    subtitle: str | None = None,
    *,
    research_stage: Any = None,
    evidence_state: Any = None,
    methodology: str | None = None,
    provenance: Any = None,
    uncertainty: Any = None,
) -> str:
    """Section header with research stage, evidence status and method note.

    Example target rendering::

        RO2 - JOINT UNCERTAINTY PROPAGATION
        Demand uncertainty + supply/lead-time uncertainty
        -> joint propagation
        -> shortage/service-risk distribution

    All content is supplied by the caller; nothing is inferred here.
    """
    parts = []
    if research_stage is not None:
        parts.append(build_research_stage_badge(research_stage))
    parts.append(f'<p class="cmido-section-title">{_escape(title)}</p>')
    if subtitle:
        parts.append(f'<p class="cmido-section-subtitle">{_escape(subtitle)}</p>')

    badges: list[str] = []
    if evidence_state is not None:
        badges.append(build_evidence_state_badge(evidence_state))
    if provenance is not None:
        badges.append(build_provenance_badge(provenance))
    if uncertainty is not None:
        badges.append(build_uncertainty_badge(uncertainty))
    if badges:
        parts.append(f'<div class="cmido-section-meta">{"".join(badges)}</div>')
    if methodology:
        parts.append(f'<p class="cmido-table-note">{_escape(methodology)}</p>')

    return f'<div class="cmido-section">{"".join(parts)}</div>'


def build_flow_diagram(nodes: Sequence[str], *, title: str | None = None) -> str:
    """Horizontal flow of neutral chips (pipeline / method overview).

    Visual only: the caller supplies the node labels in order.
    """
    items = [str(n) for n in nodes if str(n).strip()]
    if not items:
        return ""
    chips = "".join(f'<span class="cmido-flow-node">{_escape(n)}</span>' for n in items)
    heading = f'<p class="cmido-card-title">{_escape(title)}</p>' if title else ""
    return f'<div class="cmido-flow">{heading}{chips}</div>'


def build_status_banner(
    message: str,
    *,
    status: Any = "attention",
    title: str | None = None,
    detail: str | None = None,
    diagnostics: str | None = None,
    hint: str | None = None,
) -> str:
    """Plain-language banner with optional technical diagnostics underneath.

    ``message`` is what the user reads first.  ``diagnostics`` (typically an
    exception string) is kept as secondary text so technical detail is still
    reachable without making it the primary experience.
    """
    style = status_colors(status)
    heading = title or status_title(status)
    parts = [
        f'<div class="cmido-banner" style="background:{style["soft"]};'
        f'border-color:{style["border"]};border-left-color:{style["color"]};">',
        f'<span aria-hidden="true" style="color:{style["color"]};font-weight:700;">{style["icon"]}</span>',
        "<div>",
        f'<p class="cmido-banner-title">{_escape(heading)}</p>',
        f'<p class="cmido-banner-body">{_escape(message)}</p>',
    ]
    if hint:
        parts.append(f'<p class="cmido-banner-detail">{_escape(hint)}</p>')
    if detail:
        parts.append(f'<p class="cmido-banner-detail">{_escape(detail)}</p>')
    if diagnostics:
        parts.append(
            '<p class="cmido-banner-detail" style="font-size:0.72rem;color:'
            f'{MUTED_TEXT};">Technical detail: {_escape(diagnostics)}</p>'
        )
    parts.append("</div></div>")
    return "".join(parts)


def build_artifact_state(
    artifact_id: str,
    status: Any,
    *,
    description: str | None = None,
    diagnostics: str | None = None,
    stage: Any = None,
    provenance: Any = None,
) -> str:
    """Render one artifact's availability as a first-class, readable state.

    Handles the 10A.2-B registry statuses (``AVAILABLE``, ``MISSING``,
    ``INVALID``, ``TOO_LARGE``, ``UNSUPPORTED``) plus UI-only states such as
    ``loading`` and ``empty``.  Missing evidence is described in plain language;
    the underlying exception, when present, is only a secondary line.
    """
    resolved_title = status_title(status)
    default_message = _ARTIFACT_MESSAGES.get(resolved_title, resolved_title)
    message = description or default_message
    return build_status_banner(
        message,
        status=status,
        title=f"{artifact_id} - {resolved_title}",
        diagnostics=diagnostics,
        detail=_artifact_detail(resolved_title),
    ) + _artifact_meta_row(stage, provenance)


_ARTIFACT_MESSAGES = {
    "Available": "Evidence loaded and validated against the dashboard contract.",
    "Validated": "Evidence loaded and validated against the dashboard contract.",
    "Not available": "This evidence is currently unavailable in the repository.",
    "Too large to display": "This artifact exceeds the dashboard display limit and is not loaded.",
    "Unsupported": "This artifact format is not supported by the dashboard loader.",
    "Invalid": "This artifact is present but failed schema validation.",
    "Optional - unavailable": "This artifact is optional and is not present.",
    "Partial evidence": "Only part of this evidence set is available.",
    "No evidence": "No evidence rows were returned for this view.",
    "Loading": "Evidence is being loaded.",
    "Blocked by loading policy": "This artifact is excluded by the dashboard loading policy.",
}

_ARTIFACT_DETAILS = {
    "Too large to display": "The loader refuses experiment-scale ledgers; use the published summaries instead.",
    "Unsupported": "Register a supported adapter in dashboard_data before surfacing it here.",
    "Invalid": "Check the artifact against its declared schema before relying on it.",
    "Blocked by loading policy": "LoadingPolicy.NEVER artifacts must not be read by the UI.",
}


def _artifact_detail(title: str) -> str | None:
    return _ARTIFACT_DETAILS.get(title)


def _artifact_meta_row(stage: Any, provenance: Any) -> str:
    badges: list[str] = []
    if stage is not None:
        badges.append(build_research_stage_badge(stage))
    if provenance is not None:
        badges.append(build_provenance_badge(provenance))
    if not badges:
        return ""
    return f'<div class="cmido-section-meta">{"".join(badges)}</div>'


def build_empty_state(
    message: str,
    *,
    title: str | None = "No data to display",
    hint: str | None = None,
    status: Any = "empty",
) -> str:
    """Polished empty state for a panel that legitimately has no content."""
    parts = [
        '<div class="cmido-empty">',
        f'<div class="cmido-empty-title">{_escape(title)}</div>',
        f'<div class="cmido-empty-body">{_escape(message)}</div>',
    ]
    if hint:
        parts.append(f'<div class="cmido-empty-body">{_escape(hint)}</div>')
    parts.append(build_badge_row([build_status_badge(status)]))
    parts.append("</div>")
    return "".join(parts)


def build_loading_state(message: str = "Loading validated evidence...") -> str:
    """Loading placeholder rendered while a snapshot is assembled."""
    return build_status_banner(message, status="loading", title="Loading")


def build_error_state(
    headline: str,
    *,
    description: str,
    diagnostics: str | None = None,
    hint: str | None = None,
) -> str:
    """Error presentation that never leads with a raw exception string."""
    return build_status_banner(
        description,
        status="error",
        title=headline,
        diagnostics=diagnostics,
        hint=hint,
    )


def build_footer(text: str | None = None) -> str:
    """Restrained dashboard footer."""
    body = text or (
        f"{APP_NAME} - {APP_TAGLINE}. {APP_SHORT_DESCRIPTION}"
    )
    return (
        f'<div style="border-top:1px solid {BORDER};margin-top:{SPACING["lg"]};'
        f'padding-top:{SPACING["sm"]};{TYPOGRAPHY["caption"]}">'
        f"{_escape(body)}</div>"
    )


def build_sidebar_group(label: str, caption: str | None = None) -> str:
    """Sidebar section header used by the 10A.4 grouped navigation."""
    parts = [
        '<div class="cmido-nav-group">',
        f'<div class="cmido-nav-group-label">{_escape(label)}</div>',
    ]
    if caption:
        parts.append(f'<div class="cmido-nav-group-caption">{_escape(caption)}</div>')
    parts.append("</div>")
    return "".join(parts)


def build_nav_item(item_label: str, *, active: bool = False, group: str | None = None) -> str:
    """Sidebar destination row, marked active for the current page."""
    from .navigation import nav_item, resolve_page

    item = nav_item(resolve_page(item_label))
    classes = ["cmido-nav-item"]
    if active:
        classes.append("cmido-nav-item--active")
    group_attr = f' data-group="{_escape(group)}"' if group else ""
    return (
        f'<div class="{"".join(classes)}"{group_attr} '
        f'data-slug="{_escape(item.slug)}">{_escape(item.display)}</div>'
    )


# Re-exported colour helpers keep secondary text tokens available to callers
# that build custom banners.
TEXT_SECONDARY = SECONDARY_TEXT
