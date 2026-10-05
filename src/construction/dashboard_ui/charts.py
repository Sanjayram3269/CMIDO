"""Centralized Plotly configuration for the CMIDO dashboard.

One layout contract for every chart in the application: font, background,
grid, axes, legend, hover, margins and title styling.  Figures themselves are
still built by the page layer; this module only supplies configuration and
semantic colours so no page invents its own visual language.

Performance note: :func:`apply_chart_theme` performs a single shallow update
of an existing figure.  It creates no data and reads no artifacts, so calling
it on every Streamlit rerun is cheap.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Final

from .formatting import format_axis_title as _format_axis_title
from .theme import (
    BORDER_MUTED,
    BORDER_REINFORCED,
    CATEGORICAL_PALETTE,
    CHART_ROLES,
    DIVERGING_PALETTE,
    MUTED_TEXT,
    PAGE_BG,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
    SEQUENTIAL_PALETTE,
    SURFACE,
    TYPOGRAPHY,
)

FONT: Final[str] = "Helvetica, Arial, sans-serif"

AXIS_TICKFONT: Final[dict[str, Any]] = {
    "family": FONT,
    "size": 11,
    "color": SECONDARY_TEXT,
}

AXIS_TITLEFONT: Final[dict[str, Any]] = {
    "family": FONT,
    "size": 12,
    "color": SECONDARY_TEXT,
}

#: Default figure configuration passed to ``st.plotly_chart``.
DEFAULT_CHART_CONFIG: Final[dict[str, Any]] = {
    "displaylogo": False,
    "responsive": True,
    "displayModeBar": "hover",
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}

#: Layout applied to every CMIDO figure.
PLOTLY_THEME: Final[dict[str, Any]] = {
    "font": {"family": FONT, "size": 13, "color": PRIMARY_TEXT},
    "paper_bgcolor": SURFACE,
    "plot_bgcolor": SURFACE,
    "margin": {"l": 64, "r": 28, "t": 72, "b": 60},
    "hovermode": "closest",
    "hoverlabel": {
        "bgcolor": SURFACE,
        "bordercolor": BORDER_REINFORCED,
        "font": {"family": FONT, "size": 12, "color": PRIMARY_TEXT},
        "namelength": 32,
    },
    "legend": {
        "font": {"family": FONT, "size": 11, "color": SECONDARY_TEXT},
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "left",
        "x": 0.0,
        "bgcolor": "rgba(255,255,255,0.85)",
        "borderwidth": 0,
        "traceorder": "normal",
    },
    "title": {
        "font": {"family": FONT, "size": 15, "color": PRIMARY_TEXT},
        "x": 0.0,
        "xanchor": "left",
        "y": 0.97,
        "yanchor": "top",
    },
    "xaxis": {
        "gridcolor": BORDER_MUTED,
        "gridwidth": 1,
        "linecolor": BORDER_REINFORCED,
        "showgrid": True,
        "showline": True,
        "zeroline": False,
        "tickfont": AXIS_TICKFONT,
        "title": {"font": AXIS_TITLEFONT, "standoff": 10},
        "automargin": True,
    },
    "yaxis": {
        "gridcolor": BORDER_MUTED,
        "gridwidth": 1,
        "linecolor": BORDER_REINFORCED,
        "showgrid": True,
        "showline": True,
        "zeroline": False,
        "tickfont": AXIS_TICKFONT,
        "title": {"font": AXIS_TITLEFONT, "standoff": 10},
        "automargin": True,
    },
    "colorway": list(CATEGORICAL_PALETTE),
    "uirevision": "cmido-keep-view",
    "showlegend": True,
}

#: Alias kept for callers that prefer the plural form.
CATEGORICAL: Final[list[str]] = list(CATEGORICAL_PALETTE)
SEQUENTIAL: Final[dict[str, str]] = dict(SEQUENTIAL_PALETTE)
DIVERGING: Final[dict[str, str]] = dict(DIVERGING_PALETTE)

#: Line/fill styling per semantic chart role.  Uncertainty series stay
#: visibly lighter than point estimates so a probabilistic quantity is never
#: read as a deterministic fact.
DISTRIBUTION_STYLES: Final[dict[str, dict[str, Any]]] = {
    "point_estimate": {"line": {"color": CHART_ROLES["point_estimate"], "width": 2.4}, "fill": "tozeroy"},
    "uncertainty": {
        "line": {"color": CHART_ROLES["uncertainty"], "width": 1.6},
        "fill": "toself",
        "opacity": 0.45,
    },
    "observation": {"line": {"color": CHART_ROLES["observation"], "width": 2.0}, "fill": "tozeroy"},
    "scenario": {"line": {"color": CHART_ROLES["scenario"], "width": 2.0, "dash": "dot"}, "fill": "tozeroy"},
    "baseline": {"line": {"color": CHART_ROLES["baseline"], "width": 1.8, "dash": "dash"}, "fill": "tozeroy"},
    "candidate": {"line": {"color": CHART_ROLES["candidate"], "width": 2.2}, "fill": "tozeroy"},
    "optimized": {"line": {"color": CHART_ROLES["optimized"], "width": 2.6}, "fill": "tozeroy"},
    "risk": {"line": {"color": CHART_ROLES["risk"], "width": 2.2}, "fill": "tozeroy"},
    "warning": {"line": {"color": CHART_ROLES["warning"], "width": 2.0}, "fill": "tozeroy"},
}

#: Fill colours for continuous encodings.
CONTINUOUS_SCALES: Final[dict[str, list[list[Any]]]] = {
    "sequential": [[0.0, SEQUENTIAL_PALETTE["low"]], [0.5, SEQUENTIAL_PALETTE["mid"]], [1.0, SEQUENTIAL_PALETTE["high"]]],
    "diverging": [[0.0, DIVERGING_PALETTE["negative"]], [0.5, DIVERGING_PALETTE["zero"]], [1.0, DIVERGING_PALETTE["positive"]]],
}


def get_plotly_theme() -> dict[str, Any]:
    """Return a deep copy of the shared Plotly layout theme.

    Deep-copied so a page can adjust the returned layout (margins, axis titles)
    without mutating the global design system.
    """
    return deepcopy(PLOTLY_THEME)


def get_chart_config() -> dict[str, Any]:
    """Return a copy of the shared ``st.plotly_chart`` config."""
    return deepcopy(DEFAULT_CHART_CONFIG)


def get_chart_colors(role: str) -> dict[str, Any] | None:
    """Return line/fill styling for a semantic chart role, or ``None``."""
    key = str(role or "").strip().lower()
    return dict(DISTRIBUTION_STYLES[key]) if key in DISTRIBUTION_STYLES else None


def get_role_color(role: str) -> str:
    """Return the single semantic colour for a chart role."""
    key = str(role or "").strip().lower()
    return CHART_ROLES.get(key, CHART_ROLES["point_estimate"])


def get_categorical_colors(count: int | None = None) -> list[str]:
    """Return categorical colours, cycled when more series are needed."""
    palette = list(CATEGORICAL_PALETTE)
    if not count or count <= len(palette):
        return palette[:count] if count else palette
    return [palette[i % len(palette)] for i in range(count)]


def format_axis_title(title: str, unit: str | None = None) -> str:
    """Return an axis title with the unit parenthesised (pure helper)."""
    return _format_axis_title(title, unit)


def axis_title_dict(title: str, unit: str | None = None) -> dict[str, Any]:
    """Return a Plotly axis-title dict using the shared axis typography."""
    return {"text": format_axis_title(title, unit), "font": dict(AXIS_TITLEFONT)}


def apply_chart_theme(
    figure: Any,
    *,
    height: int | None = None,
    title: str | None = None,
    x_title: str | None = None,
    y_title: str | None = None,
    x_unit: str | None = None,
    y_unit: str | None = None,
    show_legend: bool | None = None,
    margin: dict[str, int] | None = None,
) -> Any:
    """Apply the CMIDO chart contract to an existing Plotly figure.

    Returns the same figure for convenient chaining.  No data is added or
    recomputed, so this is safe to call on every rerun.
    """
    if figure is None:
        return figure
    updates: dict[str, Any] = deepcopy(dict(PLOTLY_THEME))
    if height is not None:
        updates["height"] = int(height)
    if title is not None:
        updates["title"]["text"] = title
    if margin is not None:
        updates["margin"] = dict(margin)
    if show_legend is not None:
        updates["showlegend"] = bool(show_legend)

    for axis_name, axis_title, axis_unit in (
        ("xaxis", x_title, x_unit),
        ("yaxis", y_title, y_unit),
    ):
        if axis_title is None and axis_unit is None:
            continue
        axis_cfg = updates[axis_name]
        if axis_title is not None:
            axis_cfg["title"]["text"] = format_axis_title(axis_title, axis_unit)
        elif axis_unit is not None:
            axis_cfg["title"]["text"] = f"({axis_unit})"
        updates[axis_name] = axis_cfg

    figure.update_layout(**updates)
    return figure


def axis_reference(title: str, unit: str | None = None) -> dict[str, Any]:
    """Axis config for 3D scenes (which use a different Plotly structure)."""
    return {
        "title": {"text": format_axis_title(title, unit), "font": dict(AXIS_TITLEFONT)},
        "backgroundcolor": PAGE_BG,
        "showbackground": True,
        "color": SECONDARY_TEXT,
        "gridcolor": BORDER_MUTED,
        "zerolinecolor": BORDER_REINFORCED,
    }


def chart_caption(text: str, *, muted: bool = False) -> str:
    """Return caption HTML using the shared caption typography."""
    style = TYPOGRAPHY["caption"] if not muted else TYPOGRAPHY["metadata"]
    return f'<p class="cmido-table-note" style="{style}">{text}</p>'


def accessible_summary(*, title: str, description: str, reading_order: str | None = None) -> str:
    """Screen-reader summary emitted alongside a chart.

    Ensures chart meaning is not available only through hover interactions.
    """
    parts = [
        f'<div role="img" aria-label="{_escape_attr(title)}: {_escape_attr(description)}">',
        f'<span class="cmido-visually-hidden">{_escape(title)}: {_escape(description)}</span>',
    ]
    if reading_order:
        parts.append(f'<p class="cmido-table-note">{_escape(reading_order)}</p>')
    parts.append("</div>")
    return "".join(parts)


def _escape_attr(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def muted_annotation(text: str) -> dict[str, Any]:
    """Annotation dict for a restrained, muted chart note."""
    return {
        "text": text,
        "xref": "paper",
        "yref": "paper",
        "x": 0.0,
        "y": -0.16,
        "showarrow": False,
        "font": {"family": FONT, "size": 11, "color": MUTED_TEXT},
        "align": "left",
    }
