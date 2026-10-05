"""Evidence and uncertainty state definitions for the CMIDO dashboard UI.

Two independent vocabularies are modelled here:

``EvidenceState``
    How trustworthy / how available is the underlying artifact.  Mirrors the
    registry statuses produced by 10A.2-B (``AVAILABLE``, ``MISSING``,
    ``INVALID``, ``TOO_LARGE``, ``UNSUPPORTED``) plus UI-only states such as
    ``loading`` and ``empty``.

``UncertaintyState``
    How a probabilistic quantity is being shown.  CMIDO must never present a
    distribution, interval or tail measure as if it were a deterministic fact,
    so every chart/KPI that shows uncertainty declares which of these it is.

Every state carries a text label and a glyph in addition to colour, so the
dashboard never depends on colour alone.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Final

from .theme import (
    BORDER_MUTED,
    BORDER_REINFORCED,
    DANGER,
    DANGER_SOFT,
    INFO,
    INFO_SOFT,
    MUTED_TEXT,
    POSITIVE,
    POSITIVE_SOFT,
    SECONDARY_TEXT,
    SURFACE_INSET,
    UNCERTAINTY_ROLE_TOKENS,
    WARNING,
    WARNING_SOFT,
    status_colors,
)


class EvidenceState(str, Enum):
    """Availability / trustworthiness of a piece of evidence."""

    VALID = "valid"
    AVAILABLE = "available"
    PARTIAL = "partial"
    LOADING = "loading"
    EMPTY = "empty"
    OPTIONAL = "optional"
    MISSING = "missing"
    TOO_LARGE = "too_large"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"
    BLOCKED = "blocked"


class UncertaintyState(str, Enum):
    """How a numeric quantity is epistemically qualified."""

    POINT = "point"
    INTERVAL = "interval"
    DISTRIBUTION = "distribution"
    TAIL = "tail"
    SCENARIO = "scenario"
    RANGE = "range"
    SERVICE_RISK = "service_risk"
    DETERMINISTIC = "deterministic"


EVIDENCE_STATE_LABELS: Final[dict[str, str]] = {
    "valid": "Validated",
    "available": "Available",
    "partial": "Partial evidence",
    "loading": "Loading",
    "empty": "No data",
    "optional": "Optional - unavailable",
    "missing": "Not available",
    "too_large": "Too large to display",
    "unsupported": "Unsupported",
    "invalid": "Invalid",
    "blocked": "Blocked by policy",
}

UNCERTAINTY_STATE_LABELS: Final[dict[str, str]] = {
    "point": "Point estimate",
    "interval": "Interval estimate",
    "distribution": "Distribution",
    "tail": "Tail measure",
    "scenario": "Scenario",
    "range": "Scenario range",
    "service_risk": "Service-risk measure",
    "deterministic": "Deterministic value",
}

UNCERTAINTY_STATE_DESCRIPTIONS: Final[dict[str, str]] = {
    "point": "Single central value; no uncertainty shown.",
    "interval": "Central value with an uncertainty interval.",
    "distribution": "Full probabilistic distribution.",
    "tail": "Upper-tail / exceedance focused quantity.",
    "scenario": "Value produced by a modelled scenario, not observed.",
    "range": "Range spanned by modelled scenarios.",
    "service_risk": "Probability that a service level is violated.",
    "deterministic": "Exact value from deterministic computation.",
}

#: Uncertainty states that must never be presented as certain facts.
STOCHASTIC_UNCERTAINTY_STATES: Final[frozenset[str]] = frozenset(
    {
        UncertaintyState.INTERVAL.value,
        UncertaintyState.DISTRIBUTION.value,
        UncertaintyState.TAIL.value,
        UncertaintyState.SCENARIO.value,
        UncertaintyState.RANGE.value,
        UncertaintyState.SERVICE_RISK.value,
    }
)

#: Glyphs shown next to each uncertainty badge (never colour alone).
UNCERTAINTY_ICONS: Final[dict[str, str]] = {
    "deterministic": "=",
    "point": "●",
    "interval": "◐",
    "distribution": "∿",
    "tail": "⌃",
    "scenario": "◆",
    "range": "≈",
    "service_risk": "☰",
}

UNCERTAINTY_STATE_STYLES: Final[dict[str, dict[str, str]]] = {
    state: {**UNCERTAINTY_ROLE_TOKENS[state], "icon": icon}
    for state, icon in UNCERTAINTY_ICONS.items()
}


def resolve_evidence_state(state: Any) -> str:
    """Normalise an evidence state value onto a known state key."""
    raw = getattr(state, "value", state)
    text = str(raw or "").strip().lower()
    if text in EVIDENCE_STATE_LABELS:
        return text
    return "empty"


def evidence_state_label(state: Any) -> str:
    """Return the accessible text label for an evidence state."""
    return EVIDENCE_STATE_LABELS.get(resolve_evidence_state(state), "Unknown")


def evidence_state_style(state: Any) -> dict[str, str]:
    """Return ``{"color", "soft", "border", "icon"}`` for an evidence state."""
    return status_colors(state)


def resolve_uncertainty_state(state: Any) -> str:
    """Normalise an uncertainty state value onto a known state key."""
    raw = getattr(state, "value", state)
    text = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in UNCERTAINTY_STATE_STYLES else "point"


def uncertainty_state_label(state: Any) -> str:
    """Return the accessible text label for an uncertainty state."""
    return UNCERTAINTY_STATE_LABELS[resolve_uncertainty_state(state)]


def uncertainty_state_description(state: Any) -> str:
    """Return the short methodological description of an uncertainty state."""
    return UNCERTAINTY_STATE_DESCRIPTIONS[resolve_uncertainty_state(state)]


def uncertainty_state_style(state: Any) -> dict[str, str]:
    """Return the visual style mapping for an uncertainty state."""
    return dict(UNCERTAINTY_STATE_STYLES[resolve_uncertainty_state(state)])


def is_stochastic(state: Any) -> bool:
    """True when the state carries probabilistic (non-certain) meaning."""
    return resolve_uncertainty_state(state) in STOCHASTIC_UNCERTAINTY_STATES


# Semantic aliases used by the rest of the UI layer.
EVIDENCE_STATES = EVIDENCE_STATE_LABELS
UNCERTAINTY_STATES = UNCERTAINTY_STATE_LABELS

# Re-exported for callers that only import states.
POSITIVE_COLORS = {"color": POSITIVE, "soft": POSITIVE_SOFT}
WARNING_COLORS = {"color": WARNING, "soft": WARNING_SOFT}
DANGER_COLORS = {"color": DANGER, "soft": DANGER_SOFT}
LOADING_COLORS = {"color": INFO, "soft": INFO_SOFT, "border": BORDER_REINFORCED, "icon": "◐"}
MUTED_COLORS = {"color": MUTED_TEXT, "soft": SURFACE_INSET, "border": BORDER_MUTED, "icon": "—"}
