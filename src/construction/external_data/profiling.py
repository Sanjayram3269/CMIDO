"""Column profiling for an uploaded table.

Produces a JSON-serialisable profile used for the data preview and the
column-to-CMIDO mapping step: inferred column types, missingness, distinct
counts, numeric and date summaries, duplicate rows and validation warnings.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

#: Above this fraction of missing values a column is flagged as sparse.
SPARSE_THRESHOLD = 0.5

#: A column is treated as datetime-candidate if this fraction of non-null
#: values parse as dates under ``pd.to_datetime``.
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%Y-%m-%d %H:%M:%S",
)


def _infer_type(series: pd.Series) -> str:
    """Infer a coarse, honest column type for display and mapping."""
    non_null = series.dropna()
    if non_null.empty:
        return "empty"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    # Object column: probe whether most non-null values parse as dates.
    sample = non_null.astype(str).head(200)
    parsed = _probe_dates(sample)
    if parsed is not None:
        return "datetime"
    return "category"


def _probe_dates(sample: pd.Series) -> pd.DatetimeIndex | None:
    """Return a DatetimeIndex if most of ``sample`` parses as dates, else None."""
    if sample.empty:
        return None
    for fmt in _DATE_FORMATS:
        try:
            parsed = pd.to_datetime(sample, format=fmt, errors="coerce")
        except Exception:  # noqa: BLE001 - a format that errors simply doesn't match
            continue
        frac = parsed.notna().mean()
        if frac >= 0.9:
            return parsed
    # Fall back to general (non-format-specific) parsing.
    try:
        parsed = pd.to_datetime(sample, errors="coerce", utc=False)
    except Exception:  # noqa: BLE001
        return None
    if parsed.notna().mean() >= 0.9:
        return parsed
    return None


def _numeric_summary(series: pd.Series) -> dict[str, Any] | None:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return None
    desc = numeric.describe()
    return {
        "min": _jsonable(numeric.min()),
        "max": _jsonable(numeric.max()),
        "mean": _jsonable(desc.get("mean")),
        "std": _jsonable(desc.get("std")),
    }


def _date_range(series: pd.Series) -> dict[str, str] | None:
    parsed = _probe_dates(series.dropna().astype(str).head(1000))
    if parsed is None:
        return None
    parsed = parsed.dropna()
    if parsed.empty:
        return None
    return {"min": str(parsed.min()), "max": str(parsed.max())}


def _jsonable(value: Any) -> Any:
    """Coerce numpy scalars to plain Python for JSON serialisation."""
    if value is None:
        return None
    try:
        if pd.isna(value):  # type: ignore[arg-type]
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            return str(value)
    return value


def profile_table(frame: pd.DataFrame) -> dict[str, Any]:
    """Build a profile of ``frame`` for preview, mapping and validation."""
    rows, cols = frame.shape
    columns: list[dict[str, Any]] = []
    warnings: list[str] = []

    for name in frame.columns:
        series = frame[name]
        missing = int(series.isna().sum())
        missing_frac = (missing / rows) if rows else 0.0
        col_type = _infer_type(series)
        entry: dict[str, Any] = {
            "name": str(name),
            "inferred_type": col_type,
            "missing_count": missing,
            "missing_fraction": round(missing_frac, 4),
            "distinct_count": int(series.nunique(dropna=True)),
        }
        if col_type == "numeric":
            entry["numeric_summary"] = _numeric_summary(series)
        if col_type == "datetime":
            entry["date_range"] = _date_range(series)
        if missing_frac >= SPARSE_THRESHOLD:
            entry["sparse"] = True
            warnings.append(
                f"Column '{name}' is {missing_frac:.0%} missing; "
                "analyses using it will be based on few rows."
            )
        if series.nunique(dropna=True) <= 1 and rows > 1:
            entry["constant"] = True
            warnings.append(f"Column '{name}' holds a single distinct value.")
        columns.append(entry)

    duplicate_rows = int(frame.duplicated().sum())
    if duplicate_rows:
        warnings.append(f"{duplicate_rows} duplicate row(s) detected.")

    if rows == 0:
        warnings.append("The table has no data rows.")

    return {
        "row_count": rows,
        "column_count": cols,
        "columns": columns,
        "duplicate_rows": duplicate_rows,
        "warnings": warnings,
    }
