"""CMIDO 10A.3 — centralized design tokens for the dashboard UI layer.

This module is the single source of truth for colour, typography, spacing and
radius decisions.  No other module in :mod:`src.construction.dashboard_ui` may
hard-code a hex value; every component resolves its styling from these tokens.

Design intent
-------------
The CMIDO dashboard is a scientific instrument, not a generic SaaS console.
Tokens therefore favour:

* neutral steel surfaces that keep analytical content readable,
* a single restrained accent used for emphasis and provenance,
* semantic colours (positive / warning / danger / info) reserved for status,
* separate research-stage and provenance families so a reader can tell whether
  a number is observed, derived, estimated or scenario-generated.

Colour is never the only carrier of meaning: every component that uses colour
also emits a text label and (where useful) a glyph.
"""

from __future__ import annotations

from typing import Any, Final

# ---------------------------------------------------------------------------
# Surfaces
# ---------------------------------------------------------------------------
PAGE_BG: Final[str] = "#F4F6F9"
SURFACE: Final[str] = "#FFFFFF"
SURFACE_ELEVATED: Final[str] = "#F8FAFC"
SURFACE_INSET: Final[str] = "#EEF2F7"

# ---------------------------------------------------------------------------
# Borders
# ---------------------------------------------------------------------------
BORDER: Final[str] = "#D6DEE8"
BORDER_MUTED: Final[str] = "#E3E9F0"
BORDER_REINFORCED: Final[str] = "#C7D3E0"

# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------
PRIMARY_TEXT: Final[str] = "#12233A"
SECONDARY_TEXT: Final[str] = "#3F556E"
#: Muted metadata/caption text. Darkened to clear WCAG AA (>= 4.5:1) on every
#: light surface the design system uses, including the inset/elevated tones.
MUTED_TEXT: Final[str] = "#5C6E85"

# ---------------------------------------------------------------------------
# Accent — used sparingly (branding, emphasis, provenance chrome)
# ---------------------------------------------------------------------------
ACCENT: Final[str] = "#0F6E6E"
ACCENT_STRONG: Final[str] = "#0B5353"
ACCENT_SOFT: Final[str] = "#ECF6F6"

# ---------------------------------------------------------------------------
# Semantic status colours
# ---------------------------------------------------------------------------
POSITIVE: Final[str] = "#167A4B"
POSITIVE_SOFT: Final[str] = "#E7F4EC"
WARNING: Final[str] = "#9A5F00"
WARNING_SOFT: Final[str] = "#F7EDDA"
DANGER: Final[str] = "#B23A2E"
DANGER_SOFT: Final[str] = "#F6E0DE"
INFO: Final[str] = "#1D4E89"
INFO_SOFT: Final[str] = "#E4EDF6"
NEUTRAL: Final[str] = MUTED_TEXT
NEUTRAL_SOFT: Final[str] = SURFACE_INSET

# ---------------------------------------------------------------------------
# Brand identity (fixed by project convention — do not invent new titles)
# ---------------------------------------------------------------------------
APP_NAME: Final[str] = "CMIDO"
APP_TAGLINE: Final[str] = "Construction Material Intelligence & Decision Optimization"
APP_SHORT_DESCRIPTION: Final[str] = (
    "Schedule, resource, procurement, uncertainty and research-evidence analysis."
)

# ---------------------------------------------------------------------------
# Typography — semantic roles, not raw font stacks per component.
# Font stack stays on widely available system fonts.
# ---------------------------------------------------------------------------
FONT_STACK: Final[str] = '"Source Sans Pro", "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif'
MONO_STACK: Final[str] = '"JetBrains Mono", "Consolas", "SFMono-Regular", Menlo, monospace'

TYPOGRAPHY: Final[dict[str, str]] = {
    "app_name": (
        f"font-family: {FONT_STACK}; color: {PRIMARY_TEXT}; font-weight: 700;"
        " font-size: 1.18rem; letter-spacing: 0.10em; text-transform: uppercase; line-height: 1.2;"
    ),
    "app_tagline": (
        f"font-family: {FONT_STACK}; color: {SECONDARY_TEXT}; font-size: 0.84rem;"
        " font-weight: 500; letter-spacing: 0.02em;"
    ),
    "page_title": (
        f"font-family: {FONT_STACK}; color: {PRIMARY_TEXT}; font-weight: 700;"
        " font-size: 1.62rem; line-height: 1.2; letter-spacing: -0.01em;"
    ),
    "page_subtitle": (
        f"font-family: {FONT_STACK}; color: {SECONDARY_TEXT}; font-size: 0.98rem;"
        " font-weight: 500; line-height: 1.45;"
    ),
    "section_title": (
        f"font-family: {FONT_STACK}; color: {PRIMARY_TEXT}; font-weight: 700;"
        " font-size: 1.24rem; line-height: 1.25;"
    ),
    "section_subtitle": (
        f"font-family: {FONT_STACK}; color: {SECONDARY_TEXT}; font-size: 0.93rem;"
        " font-weight: 400; line-height: 1.5;"
    ),
    "subsection_title": (
        f"font-family: {FONT_STACK}; color: {PRIMARY_TEXT}; font-weight: 600; font-size: 1.03rem;"
    ),
    "kpi_label": (
        f"font-family: {FONT_STACK}; color: {SECONDARY_TEXT}; font-size: 0.74rem;"
        " font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em;"
    ),
    "kpi_value": (
        f"font-family: {FONT_STACK}; color: {PRIMARY_TEXT}; font-weight: 700;"
        " font-size: 1.52rem; line-height: 1.18; letter-spacing: -0.01em;"
    ),
    "kpi_unit": (
        f"font-family: {FONT_STACK}; color: {MUTED_TEXT}; font-size: 0.86rem; font-weight: 600;"
    ),
    "kpi_delta": f"font-family: {FONT_STACK}; font-size: 0.78rem; font-weight: 600;",
    "kpi_description": (
        f"font-family: {FONT_STACK}; color: {MUTED_TEXT}; font-size: 0.79rem; line-height: 1.45;"
    ),
    "body": f"font-family: {FONT_STACK}; color: {PRIMARY_TEXT}; font-size: 0.95rem; line-height: 1.55;",
    "caption": f"font-family: {FONT_STACK}; color: {MUTED_TEXT}; font-size: 0.83rem; line-height: 1.5;",
    "metadata": (
        f"font-family: {MONO_STACK}; color: {MUTED_TEXT}; font-size: 0.74rem; letter-spacing: 0.01em;"
    ),
    "provenance": (
        f"font-family: {FONT_STACK}; color: {MUTED_TEXT}; font-size: 0.72rem;"
        " font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;"
    ),
    "methodology": f"font-family: {FONT_STACK}; color: {SECONDARY_TEXT}; font-size: 0.89rem; line-height: 1.6;",
    "table_header": (
        f"font-family: {FONT_STACK}; color: {PRIMARY_TEXT}; font-size: 0.76rem;"
        " font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;"
    ),
    "table_cell": f"font-family: {FONT_STACK}; color: {PRIMARY_TEXT}; font-size: 0.85rem; line-height: 1.45;",
}

# ---------------------------------------------------------------------------
# Spacing scale (rem) — used instead of ad-hoc margins.
# ---------------------------------------------------------------------------
SPACING: Final[dict[str, str]] = {
    "xs": "0.35rem",
    "sm": "0.6rem",
    "md": "0.95rem",
    "lg": "1.35rem",
    "xl": "1.9rem",
    "xxl": "2.6rem",
}

# ---------------------------------------------------------------------------
# Corner radius (px) — restrained, technical, consistent.
# ---------------------------------------------------------------------------
CORNERS: Final[dict[str, str]] = {
    "xs": "4px",
    "sm": "8px",
    "md": "12px",
    "lg": "16px",
    "pill": "999px",
}

# ---------------------------------------------------------------------------
# Research stages — badge family, compact and non-dominant.
# ---------------------------------------------------------------------------
RESEARCH_STAGE_LABELS: Final[dict[str, str]] = {
    "RO1": "RO1",
    "RO2": "RO2",
    "RO3": "RO3",
    "ABLATION": "Ablation",
    "STRESS": "Stress",
    "ROBUSTNESS": "Robustness",
    "REAL_DATA": "Real Data",
    "EVIDENCE": "Evidence",
}

RESEARCH_STAGE_TITLES: Final[dict[str, str]] = {
    "RO1": "RO1 - Probabilistic forecasting",
    "RO2": "RO2 - Uncertainty propagation",
    "RO3": "RO3 - Multi-objective optimisation",
    "ABLATION": "Ablation study",
    "STRESS": "Stress testing",
    "ROBUSTNESS": "Robustness analysis",
    "REAL_DATA": "Real-world data evidence",
    "EVIDENCE": "Research evidence",
}

RESEARCH_STAGE_COLORS: Final[dict[str, str]] = {
    "RO1": "#3B6EA5",
    "RO2": "#5B4A8C",
    "RO3": "#7A3B2E",
    "ABLATION": "#8A6A00",
    "STRESS": "#8A3B00",
    "ROBUSTNESS": "#2E6E5E",
    "REAL_DATA": "#1F5FA8",
    "EVIDENCE": ACCENT,
}

RESEARCH_STAGE_SOFT: Final[dict[str, str]] = {
    "RO1": "#EAF1F9",
    "RO2": "#EFECF7",
    "RO3": "#F6EBE8",
    "ABLATION": "#F7F0DC",
    "STRESS": "#F6E9E2",
    "ROBUSTNESS": "#E5F1EE",
    "REAL_DATA": "#E7EFF8",
    "EVIDENCE": ACCENT_SOFT,
}

# ---------------------------------------------------------------------------
# Provenance classes — fixed CMIDO vocabulary: OBS / DER / EST / SCN.
# ---------------------------------------------------------------------------
PROVENANCE_LABELS: Final[dict[str, str]] = {
    "OBS": "Observed",
    "DER": "Derived",
    "EST": "Estimated",
    "SCN": "Scenario",
}

PROVENANCE_DESCRIPTIONS: Final[dict[str, str]] = {
    "OBS": "Observed - measured or recorded input data",
    "DER": "Derived - deterministic derivation from observed data",
    "EST": "Estimated - statistical estimate with uncertainty",
    "SCN": "Scenario - scenario-generated, not observed",
}

PROVENANCE_COLORS: Final[dict[str, str]] = {
    "OBS": "#3B6EA5",
    "DER": "#5B4A8C",
    "EST": "#7A3B2E",
    "SCN": "#846300",
}

PROVENANCE_SOFT: Final[dict[str, str]] = {
    "OBS": "#EAF1F9",
    "DER": "#EFECF7",
    "EST": "#F6EBE8",
    "SCN": "#F7F0DC",
}

# ---------------------------------------------------------------------------
# Evidence / artifact status palette.
# Maps :class:`src.construction.dashboard_data.contract.ArtifactStatus` values and
# the internal UI states onto one consistent visual contract.
# ---------------------------------------------------------------------------
STATUS_PALETTE: Final[dict[str, dict[str, str]]] = {
    "valid": {"color": POSITIVE, "soft": POSITIVE_SOFT, "border": POSITIVE, "icon": "✓"},
    "available": {"color": POSITIVE, "soft": POSITIVE_SOFT, "border": POSITIVE, "icon": "✓"},
    "optional": {"color": SECONDARY_TEXT, "soft": NEUTRAL_SOFT, "border": BORDER_MUTED, "icon": "○"},
    "empty": {"color": SECONDARY_TEXT, "soft": NEUTRAL_SOFT, "border": BORDER_MUTED, "icon": "○"},
    "loading": {"color": INFO, "soft": INFO_SOFT, "border": INFO, "icon": "◐"},
    "attention": {"color": WARNING, "soft": WARNING_SOFT, "border": BORDER_REINFORCED, "icon": "⚠"},
    "partial": {"color": WARNING, "soft": WARNING_SOFT, "border": BORDER_REINFORCED, "icon": "⚠"},
    "missing": {"color": WARNING, "soft": WARNING_SOFT, "border": BORDER_REINFORCED, "icon": "⚠"},
    "too_large": {"color": WARNING, "soft": WARNING_SOFT, "border": BORDER_REINFORCED, "icon": "⚠"},
    "unsupported": {"color": WARNING, "soft": WARNING_SOFT, "border": BORDER_REINFORCED, "icon": "⚠"},
    "invalid": {"color": DANGER, "soft": DANGER_SOFT, "border": DANGER, "icon": "✕"},
    "error": {"color": DANGER, "soft": DANGER_SOFT, "border": DANGER, "icon": "✕"},
    "blocked": {"color": MUTED_TEXT, "soft": NEUTRAL_SOFT, "border": BORDER_MUTED, "icon": "—"},
}

STATUS_TITLES: Final[dict[str, str]] = {
    "valid": "Validated",
    "available": "Available",
    "optional": "Optional - not available",
    "empty": "No evidence",
    "loading": "Loading",
    "attention": "Requires attention",
    "partial": "Partial evidence",
    "missing": "Not available",
    "too_large": "Too large to display",
    "unsupported": "Unsupported artifact",
    "invalid": "Invalid",
    "error": "Error",
    "blocked": "Blocked by loading policy",
}

#: Normalises ``ArtifactStatus`` / UI state strings onto palette keys.
STATUS_ALIASES: Final[dict[str, str]] = {
    "AVAILABLE": "available",
    "MISSING": "missing",
    "INVALID": "invalid",
    "UNSUPPORTED": "unsupported",
    "TOO_LARGE": "too_large",
    "NOT_APPLICABLE": "optional",
}

# ---------------------------------------------------------------------------
# Chart roles — semantic colours for analytical series.
# ---------------------------------------------------------------------------
CHART_ROLES: Final[dict[str, str]] = {
    "point_estimate": ACCENT,
    "uncertainty": "#B9C6D6",
    "observation": SECONDARY_TEXT,
    "scenario": "#8A6A00",
    "baseline": MUTED_TEXT,
    "candidate": "#3B6EA5",
    "optimized": POSITIVE,
    "risk": DANGER,
    "warning": WARNING,
    "positive": POSITIVE,
    "observed": PROVENANCE_COLORS["OBS"],
    "derived": PROVENANCE_COLORS["DER"],
    "estimated": PROVENANCE_COLORS["EST"],
}

CATEGORICAL_PALETTE: Final[tuple[str, ...]] = (
    "#0F6E6E",
    "#3B6EA5",
    "#5B4A8C",
    "#7A3B2E",
    "#8A6A00",
    "#167A4B",
    "#3F556E",
    "#2E6E5E",
)

SEQUENTIAL_PALETTE: Final[dict[str, str]] = {
    "low": BORDER_MUTED,
    "mid": "#C3D2E2",
    "high": "#6E7F97",
}

DIVERGING_PALETTE: Final[dict[str, str]] = {
    "negative": DANGER,
    "zero": BORDER_MUTED,
    "positive": POSITIVE,
}

# ---------------------------------------------------------------------------
# Uncertainty visual language.
#
# Point estimates carry the accent colour; every stochastic quantity (interval,
# distribution, tail, scenario, range, service risk) is deliberately rendered in
# a different, labelled family so a probabilistic value is never read as a
# deterministic fact.
# ---------------------------------------------------------------------------
SLATE: Final[str] = "#6E7F97"
DISTRIBUTION_BORDER: Final[str] = "#8FB0D8"
TAIL_BORDER: Final[str] = "#C7A99B"
SCENARIO_BORDER: Final[str] = "#C7A975"
UNCERTAINTY_BORDER: Final[str] = "#7FB0AE"

UNCERTAINTY_ROLE_TOKENS: Final[dict[str, dict[str, str]]] = {
    "deterministic": {"color": SECONDARY_TEXT, "soft": SURFACE_INSET, "border": BORDER_MUTED},
    "point": {"color": ACCENT, "soft": ACCENT_SOFT, "border": UNCERTAINTY_BORDER},
    "interval": {"color": SLATE, "soft": SURFACE_INSET, "border": BORDER_MUTED},
    "distribution": {"color": INFO, "soft": INFO_SOFT, "border": DISTRIBUTION_BORDER},
    "tail": {"color": DANGER, "soft": DANGER_SOFT, "border": TAIL_BORDER},
    "scenario": {"color": WARNING, "soft": WARNING_SOFT, "border": SCENARIO_BORDER},
    "range": {"color": SLATE, "soft": SURFACE_INSET, "border": BORDER_MUTED},
    "service_risk": {"color": DANGER, "soft": DANGER_SOFT, "border": TAIL_BORDER},
}

# ---------------------------------------------------------------------------
# Layout presets — Streamlit column counts. No pixel widths anywhere.
# ---------------------------------------------------------------------------
LAYOUT_COLUMNS: Final[dict[str, int]] = {
    "full": 1,
    "half": 2,
    "thirds": 3,
    "quarters": 4,
    "kpi_2": 2,
    "kpi_3": 3,
    "kpi_4": 4,
    "kpi_6": 6,
    "chart_insight": 3,
}

CONTENT_MAX_WIDTH: Final[str] = "1480px"


def resolve_status_key(status: Any) -> str:
    """Return the palette key for a status value of unknown casing.

    Accepts ``ArtifactStatus`` enums, uppercase registry strings and lowercase
    UI states.
    """
    raw = getattr(status, "value", status)
    text = str(raw).strip()
    lowered = text.lower()
    if lowered in STATUS_PALETTE:
        return lowered
    return STATUS_ALIASES.get(text.upper(), "attention")


def status_colors(status: Any) -> dict[str, str]:
    """Return ``{"color", "soft", "border", "icon"}`` for a status value."""
    return dict(STATUS_PALETTE[resolve_status_key(status)])


def status_title(status: Any) -> str:
    """Return a human readable title for a status value."""
    return STATUS_TITLES[resolve_status_key(status)]


def resolve_research_stage(stage: Any) -> str:
    """Normalise a research-stage identifier, defaulting to ``EVIDENCE``."""
    text = str(getattr(stage, "value", stage) or "").strip().upper().replace("-", "_")
    if text in RESEARCH_STAGE_LABELS:
        return text
    for known in RESEARCH_STAGE_LABELS:
        if text.startswith(known):
            return known
    return "EVIDENCE"


def resolve_provenance(provenance: Any) -> str | None:
    """Normalise a provenance class, returning ``None`` when unknown/blank."""
    if provenance is None:
        return None
    text = str(getattr(provenance, "value", provenance) or "").strip().upper()
    return text if text in PROVENANCE_LABELS else None


def build_css() -> str:
    """Return the stylesheet injected once per Streamlit run.

    Scoping every rule under ``.cmido`` keeps the design system from leaking
    into third-party widgets (dataframes, tabs, expander chrome).
    """
    return f"""
<style>
/* ---- CMIDO 10A.3 design system --------------------------------------- */
.block-container {{
    max-width: {CONTENT_MAX_WIDTH};
    padding-top: 1.6rem;
    padding-bottom: 2.4rem;
}}
[data-testid="stSidebar"] .block-container {{
    padding-top: 1.2rem;
}}

.cmido-brand {{
    display: flex; align-items: flex-start; gap: {SPACING['md']};
    padding: {SPACING['lg']} {SPACING['lg']} {SPACING['md']} {SPACING['lg']};
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-left: 4px solid {ACCENT};
    border-radius: {CORNERS['md']};
    margin-bottom: {SPACING['lg']};
}}
.cmido-brand-name {{ {TYPOGRAPHY['app_name']} margin: 0; }}
.cmido-brand-tagline {{ {TYPOGRAPHY['app_tagline']} margin: 0.15rem 0 0 0; }}

.cmido-page-title {{ {TYPOGRAPHY['page_title']} margin: 0 0 0.2rem 0; }}
.cmido-page-subtitle {{ {TYPOGRAPHY['page_subtitle']} margin: 0 0 0.15rem 0; }}

.cmido-section {{
    padding: {SPACING['md']} 0 {SPACING['sm']} 0;
    border-bottom: 1px solid {BORDER_MUTED};
    margin-bottom: {SPACING['md']};
}}
.cmido-section-title {{ {TYPOGRAPHY['section_title']} margin: 0; }}
.cmido-section-subtitle {{ {TYPOGRAPHY['section_subtitle']} margin: 0.25rem 0 0 0; }}
.cmido-section-meta {{ display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.55rem; }}

.cmido-kpi {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {CORNERS['md']};
    padding: {SPACING['md']};
    height: 100%;
}}
.cmido-kpi-label {{ {TYPOGRAPHY['kpi_label']} margin: 0; }}
.cmido-kpi-value {{ {TYPOGRAPHY['kpi_value']} margin: 0.25rem 0 0 0; }}
.cmido-kpi-unit {{ {TYPOGRAPHY['kpi_unit']} }}
.cmido-kpi-description {{ {TYPOGRAPHY['kpi_description']} margin: 0.45rem 0 0 0; }}
.cmido-kpi-delta {{ {TYPOGRAPHY['kpi_delta']} margin: 0.3rem 0 0 0; }}
.cmido-kpi-meta {{ display: flex; gap: 0.35rem; flex-wrap: wrap; margin-top: 0.55rem; }}

.cmido-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {CORNERS['md']};
    padding: {SPACING['md']} {SPACING['lg']} {SPACING['md']} {SPACING['md']};
    margin-bottom: {SPACING['md']};
}}
.cmido-card-title {{ {TYPOGRAPHY['section_title']} font-size: 1.06rem; margin: 0 0 0.3rem 0; }}
.cmido-card-body {{ {TYPOGRAPHY['methodology']} margin: 0; }}
.cmido-card-metric {{ {TYPOGRAPHY['kpi_value']} font-size: 1.22rem; margin: 0.5rem 0 0 0; }}
.cmido-card-meta {{ display: flex; gap: 0.35rem; flex-wrap: wrap; margin-top: 0.6rem; }}

.cmido-flow {{
    display: flex; flex-wrap: wrap; gap: 0.5rem;
    padding: {SPACING['md']};
    background: {SURFACE_ELEVATED};
    border: 1px solid {BORDER_MUTED};
    border-radius: {CORNERS['md']};
    margin-bottom: {SPACING['md']};
}}
.cmido-flow-node {{
    padding: 0.4rem 0.7rem; border-radius: {CORNERS['sm']};
    background: {SURFACE}; border: 1px solid {BORDER};
    color: {SECONDARY_TEXT}; font-size: 0.82rem; font-weight: 600;
}}

.cmido-banner {{
    display: flex; gap: 0.6rem; align-items: flex-start;
    padding: {SPACING['md']};
    border: 1px solid {BORDER};
    border-left: 4px solid {BORDER};
    border-radius: {CORNERS['sm']};
    margin-bottom: {SPACING['md']};
    {TYPOGRAPHY['body']}
}}
.cmido-banner-title {{ font-weight: 700; margin: 0 0 0.15rem 0; }}
.cmido-banner-body {{ margin: 0; }}
.cmido-banner-detail {{ margin: 0.4rem 0 0 0; }}

.cmido-breadcrumb {{
    display: flex; gap: 0.45rem; flex-wrap: wrap; align-items: center;
    {TYPOGRAPHY['metadata']} margin-bottom: {SPACING['xs']};
}}
.cmido-breadcrumb-sep {{ color: {BORDER_REINFORCED}; }}

.cmido-empty {{
    padding: {SPACING['lg']};
    border: 1px dashed {BORDER_REINFORCED};
    border-radius: {CORNERS['md']};
    background: {SURFACE_ELEVATED};
    text-align: center;
    color: {MUTED_TEXT};
}}
.cmido-empty-title {{ font-weight: 600; color: {SECONDARY_TEXT}; }}
.cmido-empty-body {{ margin-top: 0.35rem; }}

.cmido-table-note {{ {TYPOGRAPHY['caption']} margin: 0.35rem 0 0 0; }}
</style>
"""
