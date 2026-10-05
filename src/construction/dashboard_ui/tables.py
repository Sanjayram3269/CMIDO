"""Table presentation contract for the CMIDO dashboard.

A single wrapper so pages stop calling ``st.dataframe`` with ad-hoc options.
The wrapper:

* applies one readable, restrained table configuration,
* right-aligns numeric columns and left-aligns identifiers,
* rounds display values without mutating the underlying numbers,
* renders a designed empty state instead of a blank frame,
* attaches provenance / source context beneath the table.

The helpers are pure: they build configuration dictionaries and shallow copies
of dataframes.  No artifact is read here.
"""

from __future__ import annotations

import math
from typing import Any, Final, Mapping

from .formatting import is_missing
from .theme import (
    BORDER_MUTED,
    BORDER_REINFORCED,
    MUTED_TEXT,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
    SPACING,
    TYPOGRAPHY,
)

#: Shared ``st.dataframe`` configuration.
TABLE_CONFIG: Final[dict[str, Any]] = {
    "use_container_width": True,
    "hide_index": True,
}

#: Header/row styling injected once with the design-system CSS.
TABLE_CSS: Final[str] = f"""
<style>
.cmido-table-note {{ {TYPOGRAPHY["caption"]} }}
[data-testid="stDataFrame"] {{ border: 1px solid {BORDER_MUTED}; border-radius: 12px; }}
</style>
"""

#: Decimal places applied to float columns by :func:`present_frame`.
DEFAULT_DECIMALS: Final[int] = 2

#: Columns treated as identifiers / labels (left aligned, text formatted).
TEXT_HINTS: Final[tuple[str, ...]] = ("id", "name", "label", "activity", "material", "status", "stage")


def _is_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))
    return False


def is_numeric_series(series: Any) -> bool:
    """True when every non-null value in a pandas Series is numeric."""
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover - pandas is a dashboard dependency
        return False
    if not isinstance(series, pd.Series):
        return False
    non_null = series.dropna()
    if non_null.empty:
        return False
    return bool(non_null.map(_is_numeric).all())


def column_alignment(frame: Any) -> dict[str, str]:
    """Return ``{column: "left"|"right"}`` for a dataframe-like object.

    Numeric columns align right (fast magnitude comparison); identifiers and
    categorical labels align left (easier scanning of names).
    """
    if frame is None or not hasattr(frame, "columns"):
        return {}
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return {}
    alignment: dict[str, str] = {}
    for column in frame.columns:
        name = str(column)
        lowered = name.lower()
        series = frame[column]
        if any(hint in lowered for hint in TEXT_HINTS) and not is_numeric_series(series):
            alignment[name] = "left"
        elif is_numeric_series(series):
            alignment[name] = "right"
        else:
            alignment[name] = "left"
    if not isinstance(frame, pd.DataFrame):
        return alignment
    return alignment


def numeric_columns(frame: Any) -> list[str]:
    """Return the names of numeric columns in a dataframe-like object."""
    if frame is None or not hasattr(frame, "columns"):
        return []
    return [str(c) for c in frame.columns if is_numeric_series(frame[c])]


def build_column_config(frame: Any, decimals: int = DEFAULT_DECIMALS) -> dict[str, Any]:
    """Build a ``st.column_config.NumberColumn`` mapping for numeric columns.

    Uses plain config dictionaries so the result is testable without importing
    Streamlit; :mod:`src.construction.dashboard_ui.components` upgrades them to
    real ``st.column_config`` objects at render time.
    """
    config: dict[str, Any] = {}
    for name in numeric_columns(frame):
        config[name] = {
            "type": "number",
            "format": f"%.{max(0, int(decimals))}f",
            "help": None,
        }
    return config


def present_frame(frame: Any, *, decimals: int = DEFAULT_DECIMALS, copy: bool = True):
    """Return a display copy of a dataframe with floats rounded for display.

    The original object is never mutated, so scientific values used elsewhere
    in the page keep full precision.
    """
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return frame
    if frame is None or not isinstance(frame, pd.DataFrame):
        return frame
    target = frame.copy() if copy else frame
    for column in target.columns:
        series = target[column]
        if series.dtype.kind == "f":
            target[column] = series.round(max(0, int(decimals)))
    return target


def prepare_table(frame: Any, *, decimals: int = DEFAULT_DECIMALS) -> dict[str, Any]:
    """Return everything needed to render a table through the design system.

    Keys: ``frame`` (display copy), ``config`` (``st.dataframe`` options),
    ``column_config``, ``alignment``, ``is_empty``, ``row_count``,
    ``column_count``.
    """
    is_empty = True
    row_count = 0
    column_count = 0
    if frame is not None and hasattr(frame, "columns"):
        try:
            row_count = int(len(frame))
            column_count = int(len(frame.columns))
            is_empty = row_count == 0
        except TypeError:
            row_count = 0
            column_count = int(len(frame.columns))
    display = frame if is_empty else present_frame(frame, decimals=decimals)
    return {
        "frame": display,
        "config": dict(TABLE_CONFIG),
        "column_config": build_column_config(display, decimals=decimals),
        "alignment": column_alignment(display),
        "is_empty": is_empty,
        "row_count": row_count,
        "column_count": column_count,
    }


def build_source_note(
    *,
    source: str | None = None,
    row_count: int | None = None,
    provenance: str | None = None,
) -> str:
    """Return the caption line shown beneath a table."""
    parts: list[str] = []
    if row_count is not None:
        parts.append(f"{row_count:,} row{'s' if row_count != 1 else ''}")
    if provenance:
        parts.append(f"provenance {provenance}")
    if source:
        parts.append(f"source: {source}")
    if not parts:
        return ""
    style = f'{TYPOGRAPHY["caption"]}color:{MUTED_TEXT};'
    return f'<p class="cmido-table-note" style="{style}">' + " · ".join(parts) + "</p>"


def build_empty_table_note(message: str = "No rows available for this table.") -> str:
    """Return the note shown in place of a table with no rows."""
    style = f'{TYPOGRAPHY["caption"]}color:{SECONDARY_TEXT};'
    return f'<p class="cmido-table-note" style="{style}">{message}</p>'


def summarize_columns(frame: Any) -> list[tuple[str, str, str]]:
    """Return ``(column, dtype, alignment)`` triples for tests and captions."""
    if frame is None or not hasattr(frame, "columns"):
        return []
    alignment = column_alignment(frame)
    return [
        (str(column), str(getattr(frame[column], "dtype", "")), alignment.get(str(column), "left"))
        for column in frame.columns
    ]


def to_markdown_summary(frame: Any, *, limit: int = 8) -> str:
    """Return a compact text summary of a table for captions/tooltips."""
    if frame is None or not hasattr(frame, "columns"):
        return "empty table"
    try:
        rows = int(len(frame))
    except TypeError:
        rows = 0
    columns = [str(c) for c in frame.columns]
    shown = columns[:limit]
    suffix = "" if len(columns) <= limit else f" (+{len(columns) - limit} more)"
    return f"{rows} rows · {len(columns)} columns: {', '.join(shown)}{suffix}"


def is_blank(value: Any) -> bool:
    """True for None/empty/NaN values that should render as an em dash."""
    return is_missing(value)


def table_css_tokens() -> Mapping[str, str]:
    """Expose the table-related tokens used by the injected CSS."""
    return {
        "border": BORDER_MUTED,
        "border_reinforced": BORDER_REINFORCED,
        "header_text": PRIMARY_TEXT,
        "cell_text": SECONDARY_TEXT,
        "note_text": MUTED_TEXT,
        "gap": SPACING["sm"],
    }
