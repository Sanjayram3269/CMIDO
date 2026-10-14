"""Column-to-CMIDO-field mapping and validation.

Builds a :class:`MappingSpec` from the chosen analysis and the user's
field->column assignments, then validates that mapping against the uploaded
table's profile and the declared field contracts.  Validation produces explicit
errors (blocking) and warnings (informational) so the user sees every problem
*before* an analysis runs.  Semantic equivalence is never inferred from
similar column names — a column is used only where the user maps it.
"""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from .contracts import (
    AnalysisSpec,
    FieldSpec,
    FieldType,
    MappingSpec,
    ValidationReport,
    analysis_by_key,
)


def build_mapping_spec(
    analysis_key: str, column_by_field: Mapping[str, str]
) -> MappingSpec:
    """Construct a :class:`MappingSpec`, validating the analysis key exists."""
    analysis_by_key(analysis_key)  # raises KeyError for unknown analysis
    clean = {
        str(k): str(v)
        for k, v in column_by_field.items()
        if v is not None and str(v).strip()
    }
    return MappingSpec(analysis_key=analysis_key, column_by_field=clean)


def _column_for(frame: pd.DataFrame, column: str) -> pd.Series | None:
    if column in frame.columns:
        return frame[column]
    return None


def _validate_numeric_field(
    frame: pd.DataFrame, spec: FieldSpec, column: str, report: ValidationReport
) -> None:
    series = _column_for(frame, column)
    if series is None:
        report.add_error(spec.key, f"Column '{column}' was not found in the table.")
        return
    numeric = pd.to_numeric(series, errors="coerce")
    valid = int(numeric.notna().sum())
    if valid == 0:
        report.add_error(
            spec.key,
            f"Column '{column}' has no numeric values; '{spec.label}' requires numbers.",
        )
    elif valid < len(series.dropna()):
        coerced = int(series.notna().sum()) - valid
        report.add_warning(
            spec.key,
            f"Column '{column}' has {coerced} non-numeric value(s) that will be "
            "treated as missing.",
        )


def _validate_category_field(
    frame: pd.DataFrame, spec: FieldSpec, column: str, report: ValidationReport
) -> None:
    series = _column_for(frame, column)
    if series is None:
        report.add_error(spec.key, f"Column '{column}' was not found in the table.")
        return
    if series.nunique(dropna=True) == 0:
        report.add_error(
            spec.key,
            f"Column '{column}' has no values; '{spec.label}' requires categories.",
        )


def validate_mapping(
    frame: pd.DataFrame, spec: MappingSpec
) -> ValidationReport:
    """Validate ``spec`` against ``frame``; returns errors and warnings."""
    analysis: AnalysisSpec = spec.analysis
    report = ValidationReport(analysis_key=spec.analysis_key)

    if not analysis.supported:
        report.add_error(
            "",
            f"'{analysis.label}' is not supported on uploaded data: "
            f"{analysis.unavailable_reason}",
        )
        return report

    # Every required field must be mapped.
    for req in analysis.required_fields():
        if req.key not in spec.column_by_field:
            report.add_error(
                req.key,
                f"Required field '{req.label}' is not mapped to any column.",
            )

    # Mapped fields must exist on the analysis and the column must be usable.
    valid_field_keys = {f.key for f in analysis.fields}
    for field_key, column in spec.column_by_field.items():
        if field_key not in valid_field_keys:
            report.add_error(
                field_key,
                f"'{field_key}' is not a field of '{analysis.label}'.",
            )
            continue
        field_spec = next(f for f in analysis.fields if f.key == field_key)
        if field_spec.field_type == FieldType.NUMERIC:
            _validate_numeric_field(frame, field_spec, column, report)
        elif field_spec.field_type == FieldType.CATEGORY:
            _validate_category_field(frame, field_spec, column, report)
        else:
            if _column_for(frame, column) is None:
                report.add_error(
                    field_key, f"Column '{column}' was not found in the table."
                )

    # Two different fields must not silently reuse one numeric column where it
    # would be misleading (observed vs bounds). Warn, do not error.
    numeric_fields = [
        f for f in analysis.fields if f.field_type == FieldType.NUMERIC
    ]
    used = {
        spec.column_by_field[f.key]
        for f in numeric_fields
        if f.key in spec.column_by_field
    }
    if len(used) < len(
        [f for f in numeric_fields if f.key in spec.column_by_field]
    ):
        report.add_warning(
            "",
            "Two or more numeric fields are mapped to the same column; this is "
            "rarely meaningful and is flagged for review.",
        )

    return report


def field_options(profile: dict[str, Any], field_spec: FieldSpec) -> list[str]:
    """Return profile column names whose inferred type suits ``field_spec``."""
    wanted = {
        FieldType.NUMERIC: {"numeric"},
        FieldType.DATETIME: {"datetime"},
        FieldType.CATEGORY: {"category", "boolean"},
        FieldType.IDENTIFIER: {"category", "numeric", "datetime", "boolean"},
    }.get(field_spec.field_type, set())
    cols = profile.get("columns", [])
    if field_spec.field_type == FieldType.IDENTIFIER:
        return [c["name"] for c in cols]
    return [c["name"] for c in cols if c.get("inferred_type") in wanted]
