"""Formatting helpers for the CMIDO dashboard UI layer.

These are pure functions: they take numbers and return display strings.  They
never compute research quantities and never read data artifacts.

Formatting rules enforced here:

* thousands separators, consistent decimal places,
* percentages always rendered with an explicit unit,
* intervals rendered as ``lower–upper`` with a single shared unit,
* missing / non-finite values rendered as an em dash, never as ``nan``,
* uncertainty always labelled (``95% CI``, ``range``, ``P(...)``) rather than
  being shown as a bare number.
"""

from __future__ import annotations

import math
from typing import Any, Final

MISSING_DISPLAY: Final[str] = "—"
NA_DISPLAY: Final[str] = "n/a"


def is_missing(value: Any) -> bool:
    """True when a value cannot be displayed as a number."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return True
    return math.isnan(number) or math.isinf(number)


def format_number(value: Any, decimals: int = 2, suffix: str = "") -> str:
    """Format a number with fixed decimals; missing values become an em dash."""
    if is_missing(value):
        return MISSING_DISPLAY
    text = f"{float(value):,.{max(0, int(decimals))}f}"
    return f"{text}{suffix}"


def format_integer(value: Any, suffix: str = "") -> str:
    """Format a count-like value without decimals."""
    return format_number(value, decimals=0, suffix=suffix)


def format_percent(value: Any, decimals: int = 1) -> str:
    """Format a fraction (0.42) as a percentage string (``42.0%``)."""
    if is_missing(value):
        return MISSING_DISPLAY
    return f"{float(value) * 100:,.{max(0, int(decimals))}f}%"


def format_percent_points(value: Any, decimals: int = 1) -> str:
    """Format a value already expressed in percent points (``42.0`` -> ``42.0%``)."""
    if is_missing(value):
        return MISSING_DISPLAY
    return f"{float(value):,.{max(0, int(decimals))}f}%"


def format_days(value: Any, decimals: int = 1) -> str:
    """Format a duration in days."""
    if is_missing(value):
        return MISSING_DISPLAY
    return f"{float(value):,.{max(0, int(decimals))}f} d"


def format_duration(value: Any, decimals: int = 0) -> str:
    """Alias of :func:`format_days` kept for readability at call sites."""
    return format_days(value, decimals=decimals)


def format_currency(value: Any, decimals: int = 0, symbol: str = "$") -> str:
    """Format a monetary value with a symbol prefix."""
    if is_missing(value):
        return MISSING_DISPLAY
    return f"{symbol}{float(value):,.{max(0, int(decimals))}f}"


def format_signed(value: Any, decimals: int = 2, suffix: str = "") -> str:
    """Format a delta, always carrying an explicit sign."""
    if is_missing(value):
        return MISSING_DISPLAY
    number = float(value)
    sign = "+" if number >= 0 else "-"
    return f"{sign}{abs(number):,.{max(0, int(decimals))}f}{suffix}"


def format_interval(
    lower: Any,
    upper: Any,
    decimals: int = 2,
    suffix: str = "",
    label: str = "95% CI",
) -> str:
    """Format an interval as ``label: lower–upper suffix``.

    Example: ``format_interval(1.2, 3.4, suffix=" d")`` ->
    ``"95% CI: 1.20–3.40 d"``.
    """
    low = format_number(lower, decimals)
    high = format_number(upper, decimals)
    if label:
        prefix = f"{label}: "
    else:
        prefix = ""
    separator = "–"
    unit = f" {suffix.strip()}" if suffix.strip() else ""
    return f"{prefix}{low}{separator}{high}{unit}"


def format_shortage_pct(shortage: Any, required: Any) -> str:
    """Format shortage as a percentage of the required quantity."""
    if is_missing(shortage) or is_missing(required) or float(required) <= 0:
        return "0.0%" if not is_missing(required) and float(required) <= 0 else MISSING_DISPLAY
    return f"{100.0 * float(shortage) / float(required):.1f}%"


def format_feasibility(feasible: Any, total: Any) -> str:
    """Format feasible/total as ``"n/N (pct)"``."""
    if is_missing(feasible) or is_missing(total):
        return MISSING_DISPLAY
    return f"{format_integer(feasible)}/{format_integer(total)} ({format_percent(feasible / total)})"


def format_kpi_value(value: Any, unit: str | None = None, decimals: int = 2) -> str:
    """Split a KPI into a display value plus a separate unit token."""
    if is_missing(value):
        return MISSING_DISPLAY
    if unit and decimals == 0:
        return f"{format_integer(value)}{unit}"
    return f"{format_number(value, decimals)} {unit}".strip()


def format_value_with_unit(value: Any, unit: str | None = None, decimals: int = 2) -> str:
    """Single-token rendering used in captions and methodology notes."""
    if is_missing(value):
        return MISSING_DISPLAY
    if not unit:
        return format_number(value, decimals)
    return f"{format_number(value, decimals)} {unit.strip()}"


def format_axis_title(title: str, unit: str | None = None) -> str:
    """Return an axis title with its unit parenthesised when supplied."""
    if not unit:
        return str(title)
    return f"{title} ({unit.strip()})"


def format_yes_no(flag: Any, yes: str = "Yes", no: str = "No") -> str:
    """Render a boolean as explicit text (never colour alone)."""
    if flag is None:
        return NA_DISPLAY
    return yes if bool(flag) else no


def truncate_label(label: Any, limit: int = 42) -> str:
    """Shorten long activity/material identifiers for compact chips."""
    text = str(label)
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)] + "…"
