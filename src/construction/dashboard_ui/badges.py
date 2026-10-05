"""Badge components for the CMIDO dashboard design system.

Three badge families are provided:

* **provenance** — ``OBS`` / ``DER`` / ``EST`` / ``SCN``.  The CMIDO vocabulary
  is fixed and must never be renamed.  Every badge also carries a spelled-out
  label and a description for assistive technology, so provenance is never
  communicated by colour alone.
* **research stage** — compact ``RO1`` / ``RO2`` / ``RO3`` / ``Ablation`` /
  ``Stress`` / ``Robustness`` / ``Real Data`` / ``Evidence`` chips.
* **status / evidence / uncertainty** — availability and epistemic-quality
  markers.

All builders return HTML strings (Streamlit renders them with
``unsafe_allow_html=True``) and are pure, so they are unit-testable without a
running Streamlit server.
"""

from __future__ import annotations

from typing import Any, Final

from .formatting import truncate_label
from .states import (
    evidence_state_label,
    evidence_state_style,
    resolve_evidence_state,
    resolve_uncertainty_state,
    uncertainty_state_description,
    uncertainty_state_label,
    uncertainty_state_style,
)
from .theme import (
    ACCENT,
    BORDER_MUTED,
    CORNERS,
    MUTED_TEXT,
    PROVENANCE_COLORS,
    PROVENANCE_DESCRIPTIONS,
    PROVENANCE_LABELS,
    PROVENANCE_SOFT,
    RESEARCH_STAGE_COLORS,
    RESEARCH_STAGE_LABELS,
    RESEARCH_STAGE_SOFT,
    RESEARCH_STAGE_TITLES,
    SURFACE_INSET,
    resolve_provenance,
    resolve_research_stage,
    status_colors,
    status_title,
)

#: Provenance glyphs. Secondary cue so colour is never the only signal.
PROVENANCE_ICONS: Final[dict[str, str]] = {
    "OBS": "◉",
    "DER": "◆",
    "EST": "≈",
    "SCN": "◇",
}

#: Research-stage glyphs.
RESEARCH_STAGE_ICONS: Final[dict[str, str]] = {
    "RO1": "R1",
    "RO2": "R2",
    "RO3": "R3",
    "ABLATION": "A",
    "STRESS": "S",
    "ROBUSTNESS": "B",
    "REAL_DATA": "D",
    "EVIDENCE": "E",
}

PROVENANCE_STYLES: Final[dict[str, dict[str, str]]] = {
    code: {"color": PROVENANCE_COLORS[code], "soft": PROVENANCE_SOFT[code], "border": PROVENANCE_SOFT[code]}
    for code in PROVENANCE_LABELS
}

RESEARCH_STAGE_STYLES: Final[dict[str, dict[str, str]]] = {
    stage: {
        "color": RESEARCH_STAGE_COLORS[stage],
        "soft": RESEARCH_STAGE_SOFT[stage],
        "border": RESEARCH_STAGE_SOFT[stage],
    }
    for stage in RESEARCH_STAGE_LABELS
}

#: Legacy/alias mappings so callers can pass either compact or verbose names.
RESEARCH_STAGE_ALIASES: Final[dict[str, str]] = {
    "RO1_FORECASTING": "RO1",
    "RO2_UNCERTAINTY": "RO2",
    "RO3_OPTIMISATION": "RO3",
    "RO3_OPTIMIZATION": "RO3",
    "RO": "EVIDENCE",
}


def _escape(text: Any) -> str:
    """Minimal HTML escaping for text injected into badges."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def badge_css(
    color: str,
    soft: str,
    border: str,
    *,
    font_color: str | None = None,
    radius: str = CORNERS["sm"],
) -> str:
    """Inline style string shared by every badge variant."""
    text_color = font_color or color
    return (
        "display:inline-flex;align-items:center;gap:0.32rem;"
        f"padding:0.16rem 0.5rem;border-radius:{radius};"
        f"background:{soft};color:{text_color};"
        f"border:1px solid {border};"
        "font-size:0.7rem;font-weight:700;letter-spacing:0.05em;"
        "line-height:1.4;white-space:nowrap;"
    )


def build_badge(
    label: str,
    *,
    color: str = ACCENT,
    soft: str = SURFACE_INSET,
    border: str | None = None,
    icon: str | None = None,
    title: str | None = None,
    css_class: str = "cmido-badge",
) -> str:
    """Build a generic inline badge."""
    style = badge_css(color, soft, border or soft)
    icon_html = f'<span aria-hidden="true">{_escape(icon)}</span> ' if icon else ""
    title_attr = f' title="{_escape(title)}"' if title else ""
    return (
        f'<span class="{css_class}" style="{style}"{title_attr}>'
        f'{icon_html}{_escape(label)}</span>'
    )


def build_badge_row(badges: list[str] | tuple[str, ...] | None) -> str:
    """Wrap badges in a flex row so multiple chips stay on one baseline."""
    chips = [b for b in (badges or ()) if b]
    if not chips:
        return ""
    return '<div class="cmido-kpi-meta">' + "".join(chips) + "</div>"


def build_provenance_badge(provenance: Any, label: str | None = None) -> str:
    """Compact provenance chip, e.g. ``OBS Observed``.

    Unknown values fall back to a neutral ``n/a`` chip rather than raising, so
    a malformed record can never break the page.
    """
    code = resolve_provenance(provenance)
    if code is None:
        return build_badge(
            label or "Provenance n/a",
            color=MUTED_TEXT,
            soft=SURFACE_INSET,
            border=BORDER_MUTED,
            icon="?",
            title="Provenance class not recorded",
        )
    text = label or PROVENANCE_LABELS[code]
    style = PROVENANCE_STYLES[code]
    return build_badge(
        f"{code} {text}",
        color=style["color"],
        soft=style["soft"],
        border=style["border"],
        icon=PROVENANCE_ICONS[code],
        title=PROVENANCE_DESCRIPTIONS[code],
        css_class="cmido-badge cmido-badge-provenance",
    )


def build_provenance_chip(provenance: Any) -> str:
    """Code-only provenance chip (``OBS``) for dense contexts."""
    code = resolve_provenance(provenance)
    if code is None:
        return build_badge("n/a", color=MUTED_TEXT, soft=SURFACE_INSET, border=BORDER_MUTED)
    style = PROVENANCE_STYLES[code]
    return build_badge(
        code,
        color=style["color"],
        soft=style["soft"],
        border=style["border"],
        icon=PROVENANCE_ICONS[code],
        title=PROVENANCE_DESCRIPTIONS[code],
        css_class="cmido-badge cmido-badge-provenance cmido-badge-compact",
    )


def build_research_stage_badge(stage: Any, label: str | None = None) -> str:
    """Compact research-stage chip (``RO2``, ``Ablation``, ...)."""
    key = str(stage or "").strip().upper().replace("-", "_")
    key = RESEARCH_STAGE_ALIASES.get(key, key)
    resolved = resolve_research_stage(key)
    style = RESEARCH_STAGE_STYLES[resolved]
    text = label or RESEARCH_STAGE_LABELS[resolved]
    return build_badge(
        text,
        color=style["color"],
        soft=style["soft"],
        border=style["border"],
        icon=RESEARCH_STAGE_ICONS[resolved],
        title=RESEARCH_STAGE_TITLES[resolved],
        css_class="cmido-badge cmido-badge-stage",
    )


def build_status_badge(status: Any, label: str | None = None) -> str:
    """Artifact / evidence availability badge.

    Accepts ``ArtifactStatus`` enums and registry strings such as
    ``"TOO_LARGE"`` as well as UI states like ``"loading"``.
    """
    style = status_colors(status)
    text = label or status_title(status)
    return build_badge(
        text,
        color=style["color"],
        soft=style["soft"],
        border=style["border"],
        icon=style["icon"],
        title=f"Evidence status: {text}",
        css_class="cmido-badge cmido-badge-status",
    )


def build_evidence_state_badge(state: Any, label: str | None = None) -> str:
    """Evidence-health badge with an explicit text label."""
    resolved = resolve_evidence_state(state)
    return build_status_badge(resolved, label or evidence_state_label(resolved))


def build_uncertainty_badge(state: Any, label: str | None = None) -> str:
    """Badge declaring how a value is epistemically qualified."""
    resolved = resolve_uncertainty_state(state)
    style = uncertainty_state_style(resolved)
    text = label or uncertainty_state_label(resolved)
    return build_badge(
        text,
        color=style["color"],
        soft=style["soft"],
        border=style["border"],
        icon=style["icon"],
        title=uncertainty_state_description(resolved),
        css_class="cmido-badge cmido-badge-uncertainty",
    )


def build_entity_chip(label: Any, icon: str | None = None) -> str:
    """Neutral chip for activity / material identifiers in flow diagrams."""
    return build_badge(
        truncate_label(label, 34),
        color=MUTED_TEXT,
        soft=SURFACE_INSET,
        border=BORDER_MUTED,
        icon=icon,
        css_class="cmido-chip",
    )
