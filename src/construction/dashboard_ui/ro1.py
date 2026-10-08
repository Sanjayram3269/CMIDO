"""Presentation builders for the RO1 · Forecasting dashboard workspace.

Pure module — no Streamlit imports, no model training, no artifact scanning.
Wired through the existing 10A.2-B dashboard data contract and adapters.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from src.construction.dashboard_data.contract import RO1Evidence
from src.construction.dashboard_ui import (
    badges,
    cards,
    charts,
    components,
    formatting,
    states,
    tables,
    theme,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BREADCRUMB_IDS = ("overview", "research", "ro1_forecasting")
_IDS_PLACEHOLDER = {
    "ro1_forecasting": "RO1 · Forecasting",
    "research": "Research",
    "overview": "Overview",
}
_IDS_NOT_IMPLEMENTED = {"research"}

UAL_LABELS = {"available": "Available", "partial": "Partial", "missing": "Missing"}

_ROWS_PER_CHART_PREVIEW = 24


def _fill(color: str, alpha: float) -> str:
    """Build an rgba() fill from a theme token (no literal colour in UI code)."""
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def breadcrumb_ids() -> tuple[str, ...]:
    """Public breadcrumb trail for the RO1 page."""
    return _BREADCRUMB_IDS


def page_title() -> str:
    return "RO1 · Forecasting"


def page_subtitle() -> str:
    return "Probabilistic demand/price forecasting, predictive uncertainty and calibration evidence."


def breadcrumb_checkpoint_label(id_: str) -> str:
    """Resolve breadcrumb checkpoints to labels."""
    return _IDS_PLACEHOLDER.get(id_, id_.replace("_", " ").title())


def breadcrumb_is_missing(id_: str) -> bool:
    return id_ in _IDS_NOT_IMPLEMENTED


def build_breadcrumb_row() -> components.BreadcrumbRow:
    return components.build_breadcrumb(
        ids=_BREADCRUMB_IDS,
        labels_map={id_: breadcrumb_checkpoint_label(id_) for id_ in _BREADCRUMB_IDS},
        missing_set=_IDS_NOT_IMPLEMENTED,
    )


def _snapshot_context(evidence: RO1Evidence) -> dict[str, Any]:
    """Curate research context derived ONLY from the existing RO1 evidence snapshot."""
    context: dict[str, Any] = {}

    metrics_df = pd.DataFrame(evidence.validation_metrics)
    forecasts_df = pd.DataFrame(evidence.validation_forecasts)
    cal_df = pd.DataFrame(evidence.calibration_summary)

    # Dataset / evidence stream inventory
    if not metrics_df.empty:
        context["datasets"] = sorted(metrics_df["dataset"].dropna().unique().tolist())
    else:
        context["datasets"] = []

    if not forecasts_df.empty:
        context["forecast_datasets"] = sorted(forecasts_df["dataset"].dropna().unique().tolist())
    else:
        context["forecast_datasets"] = context["datasets"]

    # Series / material inventory (preserve literal spellings from artifacts)
    if not metrics_df.empty and "series" in metrics_df.columns:
        context["series"] = sorted(metrics_df["series"].dropna().unique().tolist())
    else:
        context["series"] = []

    if not forecasts_df.empty and "series" in forecasts_df.columns:
        forecast_series = sorted(forecasts_df["series"].dropna().unique().tolist())
        if forecast_series and forecast_series != context["series"]:
            # Keep the metrics file as authoritative for the series inventory;
            # only surface the forecast file's series if they differ and are non-empty.
            context["forecast_series"] = forecast_series

    # Horizon inventory
    if not metrics_df.empty and "horizon" in metrics_df.columns:
        context["horizons"] = sorted(metrics_df["horizon"].dropna().unique().tolist(), key=_coerce_sort_key)
    else:
        context["horizons"] = []

    if not forecasts_df.empty and "horizon" in forecasts_df.columns:
        fh = sorted(forecasts_df["horizon"].dropna().unique().tolist(), key=_coerce_sort_key)
        context["forecast_horizons"] = fh

    # Row inventory (honest counts, never asserted against a single canonical total)
    context["metrics_row_count"] = int(len(metrics_df))
    context["forecast_row_count"] = int(len(forecasts_df))

    # Provenance inventory
    provenance_tally: dict[str, list[str]] = {}
    for entry in evidence.provenance:
        cls = _prov_get(entry, "provenance_class")
        cls = getattr(cls, "value", cls)
        role = _prov_get(entry, "evidence_role")
        if cls:
            provenance_tally.setdefault(str(cls), [])
            provenance_tally[str(cls)].append(str(role or ""))
    context["provenance_tally"] = provenance_tally
    context["provenance_flat"] = [
        str(getattr(_prov_get(entry, "provenance_class"), "value", _prov_get(entry, "provenance_class")) or "")
        for entry in evidence.provenance
    ]

    # Integrity audit summary (if present)
    audit = evidence.integrity_audit or {}
    if audit:
        context["integrity_status"] = audit.get("status")
        context["integrity_notes"] = audit.get("notes") or []
        primary_horizon = audit.get("primary_horizon")
        if primary_horizon is not None:
            context["primary_horizon"] = primary_horizon

    # Which calibration sources are actually present
    context["has_calibration_scores"] = bool(cal_df.empty is False)
    context["calibration_columns"] = list(cal_df.columns) if not cal_df.empty else []

    # Distributional score columns (CRPS / pinball / sMAPE) — reported only
    # when the artifact actually carries them; never substituted.
    score_keys = ("crps", "pinball", "smap")
    context["probabilistic_score_columns"] = [
        c for c in metrics_df.columns if any(k in str(c).lower() for k in score_keys)
    ]

    return context


def _prov_get(entry: Any, key: str, default: Any = None) -> Any:
    """Read provenance metadata from a dict or an ArtifactProvenance record."""
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _coerce_sort_key(value: Any) -> Any:
    """Sort horizons/numbers honestly; fall back to string sort."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


# ---------------------------------------------------------------------------
# A. Research question / method context
# ---------------------------------------------------------------------------

def build_research_method_context(evidence: RO1Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    dataset_lines = _bulleted(ctx["datasets"]) if ctx["datasets"] else ["No dataset inventory found in RO1 artifacts."]
    series_lines = _bulleted(ctx["series"]) if ctx["series"] else ["No material/series inventory found in RO1 artifacts."]

    horizon_display = _bulleted([str(int(h)) if _is_integer_like(h) else str(h) for h in ctx["horizons"]]) or [
        "Horizon inventory not found in artifacts."
    ]

    provenance_section = _provenance_method_block(ctx["provenance_tally"], ctx["provenance_flat"])

    rows = [
        _labeled_paragraph("Research objective", _research_objective_text()),
        _labeled_paragraph(
            "Forecast target(s)",
            _forecast_target_text(ctx["datasets"]),
        ),
        _labeled_paragraph(
            "Dataset / evidence streams",
            _numbered_list(dataset_lines),
        ),
        _labeled_paragraph(
            "Material / series under forecast",
            _numbered_list(series_lines),
        ),
        _labeled_paragraph(
            "Forecast horizons",
            _numbered_list(horizon_display),
        ),
        _labeled_paragraph(
            "Probabilistic representation",
            _probabilistic_representation_text(
                ctx["forecast_row_count"],
                ctx["calibration_columns"],
            ),
        ),
        _labeled_paragraph(
            "Evidence provenance",
            provenance_section,
        ),
    ]

    return components.build_section(
        header=components.build_section_header(
            title="Research question and method context",
            subtitle="RO1 forecasting — what is being forecast, by which evidence, from which source.",
        ),
        rows=rows,
    )


def _research_objective_text() -> str:
    return (
        "RO1 tests whether probabilistic forecasting can produce not only a point estimate of future "
        "material price and demand, but also a calibrated representation of predictive uncertainty that "
        "can subsequently be propagated into procurement decisions. The section presents existing RO1 "
        "evidence only; it does not train, refit, or regenerate any forecast."
    )


def _forecast_target_text(datasets: list[str]) -> str:
    if not datasets:
        return "Dataset(s) not available from RO1 artifacts."
    return " and ".join(f"{ds} (price/demand)" for ds in datasets)


def _bulleted(lines: list[str]) -> list[str]:
    return [f"- {line}" for line in lines]


def _numbered_list(lines: list[str]) -> list[str]:
    return [f"{i}. {line}" for i, line in enumerate(lines, start=1)]


def _labeled_paragraph(label: str, body: str | list[str]) -> dict[str, Any]:
    if isinstance(body, list):
        body = "\n".join(body)
    return {"label": label, "body": body}


def _is_integer_like(value: Any) -> bool:
    try:
        return float(value).is_integer()
    except (TypeError, ValueError):
        return False


def _probabilistic_representation_text(forecast_row_count: int, calibration_columns: list[str]) -> str:
    parts = [
        f"Per-evaluation-origin forecast rows available: {forecast_row_count}.",
    ]
    if not calibration_columns:
        parts.append(
            "Per-row calibration flags are not exposed in the curated dashboard artifacts; do not treat "
            "this as evidence that calibration was not computed."
        )
    else:
        reported = [c for c in calibration_columns if "calibration_available" in c.lower() or "calibration" in c.lower()]
        if reported:
            parts.append(f"Calibration-related columns present: {', '.join(reported)}.")
        else:
            parts.append("No calibration-flag columns surfaced by the curated artifacts.")
    return "\n".join(parts)


def _provenance_method_block(tallies: dict[str, list[str]], flat: list[str]) -> str:
    if not tallies:
        return "No provenance metadata attached to the RO1 evidence snapshot."
    lines: list[str] = []
    for cls, roles in tallies.items():
        role_phrase = " ".join(sorted({r for r in roles if r}))
        if role_phrase:
            lines.append(f"{cls} — {role_phrase}")
        else:
            lines.append(cls)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# B. Forecasting snapshot KPIs
# ---------------------------------------------------------------------------

def build_snapshot_cards(evidence: RO1Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)

    cards_: list[dict[str, Any]] = [
        cards.build_kpi(
            label="Evaluated datasets",
            value=_dataset_count(ctx),
            description="Distinct dataset identifiers found in RO1 validation metrics.",
            provenance="DER",
            ),
            cards.build_kpi(
                label="Evaluated materials / series",
                value=_material_count(ctx),
                    description="Distinct series identifiers found in RO1 validation metrics.",
                provenance="DER",
            ),
            cards.build_kpi(
                label="Forecast horizons",
                value=_horizon_count(ctx),
                    description="Distinct forecast horizons evaluated.",
                provenance="DER",
            ),
            cards.build_kpi(
                label="Validation metrics rows",
                value=(
                    str(ctx["metrics_row_count"])
                    if ctx["metrics_row_count"]
                    else formatting.MISSING_DISPLAY
                ),
                description="Rows curated for the dashboard from RO1 validation metrics.",
                provenance="DER",
            ),
            cards.build_kpi(
                label="Forecast evaluation rows",
                value=(
                    str(ctx["forecast_row_count"])
                    if ctx["forecast_row_count"]
                    else formatting.MISSING_DISPLAY
                ),
                description="Per-origin probabilistic forecast rows available in RO1 artifacts.",
                provenance="EST",
            ),
        ]

    integrity_card = _build_integrity_kpi(ctx)
    if integrity_card:
        cards_.append(integrity_card)

    missing_cards = _missing_snapshot_cards(ctx)

    return components.build_kpi_columns(cards=cards_) + _missing_snapshot_subblock(missing_cards)


def _dataset_count(ctx: dict[str, Any]) -> str:
    n = len(ctx["datasets"])
    if n == 0:
        return formatting.MISSING_DISPLAY
    return str(n)


def _material_count(ctx: dict[str, Any]) -> str:
    n = len(ctx["series"])
    if n == 0:
        return formatting.MISSING_DISPLAY
    return str(n)


def _horizon_count(ctx: dict[str, Any]) -> str:
    n = len(ctx["horizons"])
    if n == 0:
        return formatting.MISSING_DISPLAY
    return str(n)


def _build_integrity_kpi(ctx: dict[str, Any]) -> dict[str, Any] | None:
    status = ctx.get("integrity_status")
    notes = ctx.get("integrity_notes")
    if status is None:
        return None
    display = "PASS" if str(status).upper() == "PASS" else "FAIL"
    note = ""
    if notes:
        note = notes[0] if len(notes) == 1 else f"{len(notes)} integrity notes attached."
    return cards.build_kpi(
        label="Final integrity audit",
        value=display,
        description=note or "No integrity notes attached.",
        provenance="DER",
    )


def _missing_snapshot_subblock(missing: list[dict[str, Any]]) -> components.SectionBlock:
    if not missing:
        return components.build_empty_state("No missing snapshot evidence to report.")
    block_rows = [
        components.build_section_header(
            title="Snapshot evidence not available",
            subtitle="Metrics not present in the RO1 artifacts are shown as unavailable rather than invented.",
        ),
        components.build_unavailable_stack(items=missing),
    ]
    return components.build_section(rows=block_rows)


def _missing_snapshot_cards(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Honest 'this metric is not in the artifacts' cards — never a zero."""
    missing: list[dict[str, Any]] = []
    if ctx["metrics_row_count"] == 0:
        missing.append(
            cards.build_unavailable_reason(
                label="Point-forecast metrics",
                reason="No RO1 validation metrics loaded for this workspace.",
            )
        )
    if ctx["forecast_row_count"] == 0:
        missing.append(
            cards.build_unavailable_reason(
                label="Probabilistic forecast rows",
                reason="No per-origin probabilistic forecast rows available in the curated artifacts.",
            )
        )
    if not ctx.get("probabilistic_score_columns"):
        missing.append(
            cards.build_unavailable_reason(
                label="CRPS / pinball / sMAPE",
                reason="Not reported in the RO1 validation metrics artifact.",
            )
        )
    return missing


# ---------------------------------------------------------------------------
# Real metric columns actually present in the RO1 artifacts
# ---------------------------------------------------------------------------

_ACTUAL_METRIC_COLUMNS = frozenset({
    "dataset",
    "series",
    "horizon",
    "n_raw",
    "n_calibrated_50",
    "n_calibrated_80",
    "mae_q50",
    "rmse_q50",
    "raw_coverage_50",
    "raw_coverage_80",
    "raw_coverage_error_50",
    "raw_coverage_error_80",
    "raw_mean_width_50",
    "raw_mean_width_80",
    "raw_winkler_50",
    "raw_winkler_80",
    "prequential_coverage_50",
    "prequential_coverage_80",
    "prequential_coverage_error_50",
    "prequential_coverage_error_80",
    "prequential_mean_width_50",
    "prequential_mean_width_80",
    "prequential_winkler_50",
    "prequential_winkler_80",
})

def _is_real_metric_column(column: str) -> bool:
    return column in _ACTUAL_METRIC_COLUMNS


# ---------------------------------------------------------------------------
# C. Model comparison
# ---------------------------------------------------------------------------

def build_model_comparison(evidence: RO1Evidence) -> components.SectionBlock:
    metrics_df = pd.DataFrame(evidence.validation_metrics)

    if metrics_df.empty:
        return components.build_empty_state(
            title="Model comparison not available",
            body="No RO1 validation metrics loaded for this workspace.",
        )

    columns = list(metrics_df.columns)
    table = _build_model_comparison_table(metrics_df, columns)

    provenance_row = _model_comparison_provenance_row()

    header = components.build_section_header(
        title="Model comparison",
        subtitle="Existing RO1 evaluation results, presented as recorded. No composite ranking is invented.",
    )

    return components.build_section(
        header=header,
        rows=[
            table,
            components.build_note_bare(provenance_row),
        ],
    )


def build_model_comparison_header_title() -> str:
    return "Model comparison"


def build_research_method_context_header_title() -> str:
    return "Research question and method context"


def build_point_forecast_section_header_title() -> str:
    return "Point forecast performance"


def build_probabilistic_forecast_section_header_title() -> str:
    return "Probabilistic forecast"


def build_uncertainty_width_section_header_title() -> str:
    return "Uncertainty width / sharpness"


def build_calibration_section_header_title() -> str:
    return "Calibration"


def build_material_stability_section_header_title() -> str:
    return "Material / series stability"


def build_temporal_stability_section_header_title() -> str:
    return "Temporal stability"


def build_handoff_section_header_title() -> str:
    return "Handoff to RO2"


def build_research_pipeline_block_header_title() -> str:
    return "Research pipeline"


def build_ro1_page_title() -> str:
    return "RO1 · Forecasting"


def build_ro1_page_subtitle() -> str:
    return "Probabilistic demand/price forecasting, predictive uncertainty and calibration evidence."


def build_breadcrumb_element(id_: str) -> dict[str, Any]:
    return {
        "id": id_,
        "label": breadcrumb_checkpoint_label(id_),
        "missing": breadcrumb_is_missing(id_),
    }


def _column_candidates() -> dict[str, str]:
    return {
        "model": "Model",
        "method": "Model",
        "approach": "Model",
        "series": "Material / series",
        "dataset": "Dataset",
        "horizon": "Horizon",
        "mae_q50": "MAE (q50)",
        "rmse_q50": "RMSE (q50)",
        "raw_coverage_50": "Raw coverage 50%",
        "raw_coverage_80": "Raw coverage 80%",
        "raw_mean_width_50": "Raw mean width 50%",
        "raw_mean_width_80": "Raw mean width 80%",
        "raw_winkler_50": "Raw Winkler 50%",
        "raw_winkler_80": "Raw Winkler 80%",
        "prequential_coverage_50": "Prequential coverage 50%",
        "prequential_coverage_80": "Prequential coverage 80%",
        "prequential_mean_width_50": "Prequential mean width 50%",
        "prequential_mean_width_80": "Prequential mean width 80%",
        "prequential_winkler_50": "Prequential Winkler 50%",
        "prequential_winkler_80": "Prequential Winkler 80%",
        "n_raw": "Raw obs",
        "n_calibrated_50": "Calibrated n 50%",
        "n_calibrated_80": "Calibrated n 80%",
    }


def _build_model_comparison_table(metrics_df: pd.DataFrame, columns: list[str]) -> components.TableBlock:
    candidates = _column_candidates()
    present = {c for c in columns if c in candidates or _is_showable_metric(c)}
    header_map = {c: candidates.get(c, _friendly_metric_header(c)) for c in present}

    display_cols = list(header_map.keys())
    display_headers = [header_map[c] for c in display_cols]

    # Build a presentable frame
    rows_data: list[dict[str, Any]] = []
    for _, row in metrics_df.iterrows():
        entry: dict[str, Any] = {}
        for c in display_cols:
            value = row.get(c)
            entry[c] = _format_metric_cell(c, value)
        rows_data.append(entry)

    return components.build_table(
        headers=display_headers,
        rows=rows_data,
        column_config=_build_model_comparison_table_config(display_headers),
    )


def _build_model_comparison_table_config(headers: list[str]) -> tables.TableConfig:
    config = tables.TableConfig()
    config.min_width = 280
    config.max_width = 720
    config.default_alignment = tables.ColumnAlignment.LEFT
    for header in ("Horizon",):
        if header in headers:
            idx = headers.index(header)
            config.column_config[idx] = tables.ColumnConfig(alignment=tables.ColumnAlignment.CENTER)
    return config


def _is_showable_metric(column: str) -> bool:
    return False


def _friendly_metric_header(column: str) -> str:
    return column.replace("_", " ").title()


def _format_metric_cell(column: str, value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return formatting.MISSING_DISPLAY
    if column in ("horizon",):
        try:
            return str(int(float(value)))
        except (TypeError, ValueError):
            return str(value)
    try:
        num = float(value)
        if column.startswith("coverage") or column.endswith("coverage"):
            return formatting.format_percent(num, decimals=1)
        if column.startswith("mae") or column.startswith("rmse") or column.startswith("winkler") or column.startswith("width"):
            return formatting.format_number(num, decimals=2)
    except (TypeError, ValueError):
        return str(value)
    return str(value)


def _model_comparison_provenance_row() -> str:
    return (
        "Provenance: validation metrics are derived from the RO1 evaluation artifacts. "
        "Do not read the table order as a ranking; no composite score is computed in the dashboard."
    )


# ---------------------------------------------------------------------------
# D. Point forecast performance
# ---------------------------------------------------------------------------

def build_point_forecast_section(evidence: RO1Evidence) -> components.SectionBlock:
    metrics_df = pd.DataFrame(evidence.validation_metrics)

    if metrics_df.empty:
        return components.build_empty_state(
            title="Point forecast performance not available",
            body="No RO1 validation metrics loaded for this workspace.",
        )

    # Use aggregate KPIs only if they are present in the artifact
    rows: list[Any] = [
        _point_forecast_method_context(),
    ]

    # Horizon summary
    horizon_rows = _build_point_forecast_horizon_summary(metrics_df)
    rows.append(
        components.build_section_header(
            title="Performance by horizon",
            subtitle="Point-forecast error metrics as recorded in the RO1 artifacts.",
        )
    )
    rows.append(horizon_rows)

    return components.build_section(
        header=components.build_section_header(
            title="Point forecast performance",
            subtitle="Accuracy metrics only. Probabilistic calibration is reported separately.",
        ),
        rows=rows,
    )


def _point_forecast_method_context() -> dict[str, Any]:
    return {
        "label": "Scope",
        "body": (
            "Point-forecast performance uses the RO1 validation metrics artifact. "
            "Where a metric is not reported, it is shown as unavailable. "
            "This section does not substitute MAE for CRPS, nor coverage for sharpness."
        ),
    }


def _build_point_forecast_horizon_summary(metrics_df: pd.DataFrame) -> components.TableBlock:
    horizon_cols = [c for c in ("horizon", "mae_q50", "rmse_q50", "raw_coverage_50", "raw_coverage_80", "raw_mean_width_50", "raw_mean_width_80")]
    present = [c for c in horizon_cols if c in metrics_df.columns]
    if not present:
        return components.build_empty_state(
            title="Horizon summary not available",
            body="No horizon-level columns found in the RO1 validation metrics artifact.",
        )

    headers = [c.replace("_", " ").title() for c in present]
    rows_data: list[dict[str, Any]] = []
    for _, row in metrics_df.iterrows():
        entry: dict[str, Any] = {}
        for c in present:
            value = row.get(c)
            entry[c] = _format_metric_cell(c, value)
        rows_data.append(entry)

    return components.build_table(
        headers=headers,
        rows=rows_data,
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.LEFT),
    )


# ---------------------------------------------------------------------------
# E. Probabilistic forecast
# ---------------------------------------------------------------------------

def build_probabilistic_forecast_section(evidence: RO1Evidence) -> components.SectionBlock:
    forecasts_df = pd.DataFrame(evidence.validation_forecasts)

    if forecasts_df.empty:
        return components.build_unavailable_block(
            title="Probabilistic forecast evidence not available",
            body=(
                "No per-origin probabilistic forecast rows loaded from the RO1 artifacts. "
                "This dashboard does not fabricate quantiles or intervals."
            ),
            provenance="EST",
        )

    rows: list[Any] = [
        _probabilistic_method_context(),
        _build_quantile_legend(),
    ]

    chart = _build_forecast_chart(forecasts_df)
    rows.append(chart)

    preview = _build_forecast_preview_table(forecasts_df)
    rows.append(preview)

    provenance = (
        "Provenance: per-row forecast quantiles and intervals come from the RO1 probabilistic "
        "forecast artifact and represent estimated model outputs. Calibration availability flags "
        "indicate where conformal adjustment is present."
    )
    rows.append(components.build_note_bare(provenance))

    return components.build_section(
        header=components.build_section_header(
            title="Probabilistic forecast",
            subtitle="Observed, point forecast and predictive intervals from existing RO1 evidence.",
        ),
        rows=rows,
    )


def _probabilistic_method_context() -> dict[str, Any]:
    return {
        "label": "Scope",
        "body": (
            "Each evaluation-origin row shows the observed target, the point forecast (median / q50), "
            "and the predictive interval bounds produced by the RO1 method. Where calibration is available, "
            "both raw and calibrated intervals are shown. This is a forecast visualization, not a confidence "
            "interval in the frequentist sense unless the artifact explicitly defines it as such."
        ),
    }


def _build_quantile_legend() -> components.TableBlock:
    LEGEND_ROWS = [
        {"id": "observed", "label": "Observed", "meaning": "Actual realized value at the target date."},
        {"id": "point_forecast", "label": "Point forecast (q50)", "meaning": "Median forecast from the evaluated model."},
        {"id": "interval_50", "label": "Predictive interval 50%", "meaning": "Central 50% interval lower–upper."},
        {"id": "interval_80", "label": "Predictive interval 80%", "meaning": "Central 80% interval lower–upper."},
        {"id": "calibrated", "label": "Calibrated", "meaning": "Interval after conformal adjustment, where available."},
    ]
    return components.build_table(
        headers=["Element", "Meaning"],
        rows=[{ "Element": r["label"], "Meaning": r["meaning"] } for r in LEGEND_ROWS],
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.LEFT, min_width=360),
    )


def _forecast_legend_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": "observed",
            "label": "Observed",
            "meaning": "Actual realized value at the target date.",
            "color": theme.CHART_ROLES["observation"],
        },
        {
            "id": "point_forecast",
            "label": "Point forecast (q50)",
            "meaning": "Median forecast from the evaluated model.",
            "color": theme.CHART_ROLES["point_estimate"],
        },
        {
            "id": "interval_50",
            "label": "Predictive interval 50%",
            "meaning": "Central 50% interval lower–upper.",
            "color": theme.CHART_ROLES["uncertainty"],
        },
        {
            "id": "interval_80",
            "label": "Predictive interval 80%",
            "meaning": "Central 80% interval lower–upper.",
            "color": theme.CATEGORICAL_PALETTE[1],
        },
        {
            "id": "calibrated",
            "label": "Calibrated",
            "meaning": "Interval after conformal adjustment, where available.",
            "color": theme.CHART_ROLES["estimated"],
        },
    ]


def _build_forecast_chart(forecasts_df: pd.DataFrame) -> components.ChartBlock:
    preview_rows = _prepare_forecast_preview_rows(forecasts_df)
    if preview_rows.empty:
        return components.build_empty_state(title="Forecast preview not available", body="No chartable rows after filtering.")

    fig = _make_forecast_figure(preview_rows)
    caption = _forecast_chart_caption(preview_rows)
    return components.build_chart(
        chart=fig,
        caption=caption,
        chart_config=charts.CHART_CONFIG_FORECAST,
    )


def _prepare_forecast_preview_rows(forecasts_df: pd.DataFrame) -> pd.DataFrame:
    df = forecasts_df.copy()
    if df.empty:
        return df
    for col in ("target_date", "forecast_origin"):
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except (TypeError, ValueError):
                pass
    if "target_date" in df.columns and df["target_date"].notna().any():
        key_col = "target_date"
    elif "forecast_origin" in df.columns and df["forecast_origin"].notna().any():
        key_col = "forecast_origin"
    else:
        key_col = None
    if key_col is not None:
        df = df.sort_values(key_col).head(_ROWS_PER_CHART_PREVIEW)
    else:
        df = df.head(_ROWS_PER_CHART_PREVIEW)
    return df


def _forecast_preview_table(forecasts_df: pd.DataFrame) -> components.TableBlock:
    preview_rows = _prepare_forecast_preview_rows(forecasts_df)
    if preview_rows.empty:
        return components.build_empty_state(title="Preview table not available", body="No rows to display.")

    headers = ["Series", "Horizon", "Observed", "Point forecast (q50)", "Lower 50%", "Upper 50%", "Lower 80%", "Upper 80%"]
    cols = ["series", "horizon", "actual", "q50", "raw_lower_50", "raw_upper_50", "raw_lower_80", "raw_upper_80"]
    rows_data: list[dict[str, Any]] = []
    for _, row in preview_rows.iterrows():
        entry: dict[str, Any] = {}
        for h, c in zip(headers, cols):
            value = row.get(c)
            if c == "horizon":
                try:
                    entry[h] = str(int(float(value)))
                except (TypeError, ValueError):
                    entry[h] = str(value)
            elif c in ("actual", "q50", "raw_lower_50", "raw_upper_50", "raw_lower_80", "raw_upper_80"):
                try:
                    entry[h] = formatting.format_number(float(value), decimals=2)
                except (TypeError, ValueError):
                    entry[h] = formatting.MISSING_DISPLAY
                    if pd.isna(value):
                        entry[h] = formatting.MISSING_DISPLAY
            else:
                entry[h] = str(value) if value is not None else formatting.MISSING_DISPLAY
        rows_data.append(entry)

    return components.build_table(
        headers=headers,
        rows=rows_data,
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.RIGHT, min_width=420),
    )


def _make_forecast_figure(preview_rows: pd.DataFrame) -> Any:
    import plotly.graph_objects as go

    fig = go.Figure()

    if "target_date" in preview_rows.columns and preview_rows["target_date"].notna().any():
        x = preview_rows["target_date"].dt.strftime("%Y-%m-%d").tolist()
    elif "forecast_origin" in preview_rows.columns and preview_rows["forecast_origin"].notna().any():
        x = preview_rows["forecast_origin"].astype(str).tolist()
    else:
        x = [f"row {i + 1}" for i in range(len(preview_rows))]

    observed = preview_rows.get("actual")
    q50 = preview_rows.get("q50")

    fig.add_trace(go.Scatter(x=x, y=observed, mode="lines+markers", name="Observed", line=dict(color=theme.CHART_ROLES["observation"])))
    fig.add_trace(go.Scatter(x=x, y=q50, mode="lines", name="Point forecast (q50)", line=dict(color=theme.CHART_ROLES["point_estimate"])))

    lower_50 = preview_rows.get("raw_lower_50")
    upper_50 = preview_rows.get("raw_upper_50")
    if lower_50 is not None and upper_50 is not None and lower_50.notna().any():
        fig.add_trace(
            go.Scatter(
                x=x,
                y=upper_50.fillna(pd.NA).tolist(),
                mode="lines",
                name="Predictive interval 50% (upper)",
                line=dict(color=theme.CHART_ROLES["uncertainty"], dash="dot"),
                showlegend=True,
                legendgroup="i50",
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=lower_50.fillna(pd.NA).tolist(),
                mode="lines",
                name="Predictive interval 50% (lower)",
                line=dict(color=theme.CHART_ROLES["uncertainty"], dash="dot"),
                showlegend=False,
                legendgroup="i50",
                fill="tonexty",
                fillcolor=_fill(theme.CHART_ROLES["uncertainty"], 0.25),
                hoverinfo="skip",
            )
        )

    lower_80 = preview_rows.get("raw_lower_80")
    upper_80 = preview_rows.get("raw_upper_80")
    if lower_80 is not None and upper_80 is not None and lower_80.notna().any():
        fig.add_trace(
            go.Scatter(
                x=x,
                y=upper_80.fillna(pd.NA).tolist(),
                mode="lines",
                name="Predictive interval 80% (upper)",
                line=dict(color=theme.CATEGORICAL_PALETTE[1], dash="dot"),
                showlegend=True,
                legendgroup="i80",
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=lower_80.fillna(pd.NA).tolist(),
                mode="lines",
                name="Predictive interval 80% (lower)",
                line=dict(color=theme.CATEGORICAL_PALETTE[1], dash="dot"),
                showlegend=False,
                legendgroup="i80",
                fill="tonexty",
                fillcolor=_fill(theme.CATEGORICAL_PALETTE[1], 0.18),
                hoverinfo="skip",
            )
        )

    fig.update_layout(margin=dict(l=40, r=10, t=30, b=40))
    return fig


def _forecast_chart_caption(preview_rows: pd.DataFrame) -> str:
    n = len(preview_rows)
    return f"Interactive preview of up to {n} evaluation-origin forecast rows. Observed, point forecast and predictive intervals are read directly from the RO1 probabilistic forecast artifact."


def _build_forecast_preview_table(forecasts_df: pd.DataFrame) -> components.TableBlock:
    preview_rows = _prepare_forecast_preview_rows(forecasts_df)
    if preview_rows.empty:
        return components.build_empty_state(title="Preview table not available", body="No rows to display.")

    headers = ["Series", "Horizon", "Observed", "Point forecast (q50)", "Lower 50%", "Upper 50%", "Lower 80%", "Upper 80%"]
    cols = ["series", "horizon", "actual", "q50", "raw_lower_50", "raw_upper_50", "raw_lower_80", "raw_upper_80"]
    rows_data: list[dict[str, Any]] = []
    for _, row in preview_rows.iterrows():
        entry: dict[str, Any] = {}
        for h, c in zip(headers, cols):
            value = row.get(c)
            if c == "horizon":
                try:
                    entry[h] = str(int(float(value)))
                except (TypeError, ValueError):
                    entry[h] = str(value)
            elif c in ("actual", "q50", "raw_lower_50", "raw_upper_50", "raw_lower_80", "raw_upper_80"):
                try:
                    entry[h] = formatting.format_number(float(value), decimals=2)
                except (TypeError, ValueError):
                    entry[h] = formatting.MISSING_DISPLAY
                    if pd.isna(value):
                        entry[h] = formatting.MISSING_DISPLAY
            else:
                entry[h] = str(value) if value is not None else formatting.MISSING_DISPLAY
        rows_data.append(entry)

    return components.build_table(
        headers=headers,
        rows=rows_data,
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.RIGHT, min_width=420),
    )


# ---------------------------------------------------------------------------
# F. Uncertainty width / sharpness
# ---------------------------------------------------------------------------

def build_uncertainty_width_section(evidence: RO1Evidence) -> components.SectionBlock:
    metrics_df = pd.DataFrame(evidence.validation_metrics)

    if metrics_df.empty:
        return components.build_unavailable_block(
            title="Uncertainty width / sharpness not available",
            body="No RO1 validation metrics loaded to inspect interval width.",
            provenance="DER",
        )

    width_cols = [
        "raw_mean_width_50",
        "raw_mean_width_80",
        "prequential_mean_width_50",
        "prequential_mean_width_80",
    ]
    present = [c for c in width_cols if c in metrics_df.columns]

    if not present:
        return components.build_unavailable_block(
            title="Uncertainty width / sharpness not available",
            body="No mean-width / sharpness columns found in the RO1 validation metrics artifact.",
            provenance="DER",
        )

    header = components.build_section_header(
        title="Uncertainty width / sharpness",
        subtitle="Interval width is reported where available. Narrower is only useful alongside adequate coverage.",
    )
    note = (
        "Sharpness is reflected by mean interval width. The dashboard does not declare narrower intervals "
        "to be better unless calibration evidence supports that interpretation."
    )

    rows: list[Any] = [
        _width_method_context(),
        _build_width_table(metrics_df, present),
        components.build_note_bare(note),
    ]
    return components.build_section(header=header, rows=rows)


def _width_method_context() -> dict[str, Any]:
    return {
        "label": "Scope",
        "body": (
            "Width metrics are taken from the RO1 validation metrics artifact. They describe the concentration "
            "of the predictive intervals and are not themselves a measure of accuracy or calibration."
        ),
    }


def _build_width_table(metrics_df: pd.DataFrame, cols: list[str]) -> components.TableBlock:
    headers = [c.replace("_", " ").title() for c in cols]
    rows_data: list[dict[str, Any]] = []
    for _, row in metrics_df.iterrows():
        entry: dict[str, Any] = {}
        for c in cols:
            value = row.get(c)
            entry[c] = _format_metric_cell(c, value)
        rows_data.append(entry)
    return components.build_table(
        headers=headers,
        rows=rows_data,
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.RIGHT, min_width=320),
    )


# ---------------------------------------------------------------------------
# G. Calibration
# ---------------------------------------------------------------------------

def build_calibration_section(evidence: RO1Evidence) -> components.SectionBlock:
    metrics_df = pd.DataFrame(evidence.validation_metrics)
    cal_df = pd.DataFrame(evidence.calibration_summary)

    if cal_df.empty and not _has_calibration_columns(metrics_df):
        return components.build_unavailable_block(
            title="Calibration evidence not available",
            body=(
                "No calibration artifact loaded for this workspace, and no calibration columns found "
                "in the RO1 validation metrics. The dashboard does not estimate calibration from point forecasts."
            ),
            provenance="DER",
        )

    rows: list[Any] = [
        _calibration_method_context(),
    ]

    if not cal_df.empty:
        rows.append(_build_calibration_summary_table(cal_df))
    if _has_calibration_columns(metrics_df):
        rows.append(_build_calibration_from_metrics_table(metrics_df))

    return components.build_section(
        header=components.build_section_header(
            title="Calibration",
            subtitle="Whether empirical coverage agrees with nominal coverage, where such evidence exists.",
        ),
        rows=rows,
    )


def _has_calibration_columns(metrics_df: pd.DataFrame) -> bool:
    cal_keywords = ("coverage", "calibration")
    return any(c for c in metrics_df.columns if any(k in c.lower() for k in cal_keywords))


def _calibration_method_context() -> dict[str, Any]:
    return {
        "label": "Scope",
        "body": (
            "Calibration evidence is presented only where the RO1 artifacts supply it. Where calibration is "
            "available, both nominal and empirical coverage are shown; deviation is reported honestly. "
            "Missing calibration is reported as unavailable rather than inferred."
        ),
    }


def _build_calibration_summary_table(cal_df: pd.DataFrame) -> components.TableBlock:
    cols = [
        c
        for c in cal_df.columns
        if any(k in c.lower() for k in ("coverage", "width", "score", "horizon", "dataset", "series"))
    ]
    if not cols:
        return components.build_empty_state(title="Calibration summary not surfaceable", body="No recognized calibration columns found.")
    headers = [c.replace("_", " ").title() for c in cols]
    rows_data: list[dict[str, Any]] = []
    for _, row in cal_df.iterrows():
        entry: dict[str, Any] = {}
        for c in cols:
            value = row.get(c)
            entry[c] = _format_metric_cell(c, value) if _is_numeric_calibration_cell(c, value) else str(value)
        rows_data.append(entry)
    return components.build_table(
        headers=headers,
        rows=rows_data,
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.RIGHT, min_width=360),
    )


def _is_numeric_calibration_cell(column: str, value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _build_calibration_from_metrics_table(metrics_df: pd.DataFrame) -> components.TableBlock:
    cols = [
        "raw_coverage_50",
        "raw_coverage_80",
        "prequential_coverage_50",
        "prequential_coverage_80",
    ]
    present = [c for c in cols if c in metrics_df.columns]
    if not present:
        return components.build_empty_state(title="Calibration columns not surfaceable", body="No coverage columns found in metrics.")
    headers = [c.replace("_", " ").title() for c in present]
    rows_data: list[dict[str, Any]] = []
    for _, row in metrics_df.iterrows():
        entry: dict[str, Any] = {}
        for c in present:
            value = row.get(c)
            if value is None or (isinstance(value, float) and pd.isna(value)):
                entry[c] = formatting.MISSING_DISPLAY
            else:
                try:
                    entry[c] = formatting.format_percent(float(value), decimals=1)
                except (TypeError, ValueError):
                    entry[c] = str(value)
        rows_data.append(entry)
    return components.build_table(
        headers=headers,
        rows=rows_data,
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.RIGHT, min_width=320),
    )


# ---------------------------------------------------------------------------
# H. Material / series stability
# ---------------------------------------------------------------------------

def build_material_stability_section(evidence: RO1Evidence) -> components.SectionBlock:
    metrics_df = pd.DataFrame(evidence.validation_metrics)

    if metrics_df.empty or "series" not in metrics_df.columns:
        return components.build_unavailable_block(
            title="Material / series stability not available",
            body="No series-identifying column in the RO1 validation metrics artifact.",
            provenance="DER",
        )

    series = metrics_df["series"].dropna().unique().tolist()
    if not series:
        return components.build_unavailable_block(
            title="Material / series stability not available",
            body="No material/series values found.",
            provenance="DER",
        )

    header = components.build_section_header(
        title="Material / series stability",
        subtitle="Performance across materials/series, as recorded in the RO1 artifacts.",
    )
    rows: list[Any] = [
        _series_stability_method_context(series),
        _build_series_summary_table(metrics_df),
    ]
    return components.build_section(header=header, rows=rows)


def _series_stability_method_context(series: list[str]) -> dict[str, Any]:
    return {
        "label": "Scope",
        "body": (
            f"RO1 evaluates {len(series)} material/series: {', '.join(series)}. "
            "The dashboard shows the distribution of results across them; it does not assert generalization "
            "unless the evidence supports that claim."
        ),
    }


def _build_series_summary_table(metrics_df: pd.DataFrame) -> components.TableBlock:
    group_cols = [c for c in ("series", "horizon", "dataset") if c in metrics_df.columns]
    metric_cols = [
        "mae_q50",
        "rmse_q50",
        "raw_coverage_50",
        "raw_coverage_80",
        "raw_mean_width_50",
        "raw_mean_width_80",
    ]
    present_metrics = [c for c in metric_cols if c in metrics_df.columns]
    present = group_cols + present_metrics
    if not present:
        return components.build_empty_state(title="Series summary not surfaceable", body="No recognized columns in metrics.")

    headers = [c.replace("_", " ").title() for c in present]
    rows_data: list[dict[str, Any]] = []
    for _, row in metrics_df.iterrows():
        entry: dict[str, Any] = {}
        for c in present:
            value = row.get(c)
            if c in group_cols:
                entry[c] = str(value) if value is not None else formatting.MISSING_DISPLAY
            else:
                entry[c] = _format_metric_cell(c, value)
        rows_data.append(entry)
    return components.build_table(
        headers=headers,
        rows=rows_data,
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.LEFT, min_width=360),
    )


# ---------------------------------------------------------------------------
# I. Temporal stability
# ---------------------------------------------------------------------------

def build_temporal_stability_section(evidence: RO1Evidence) -> components.SectionBlock:
    forecasts_df = pd.DataFrame(evidence.validation_forecasts)

    if forecasts_df.empty:
        return components.build_unavailable_block(
            title="Temporal stability not available",
            body="No per-origin forecast rows available to inspect across evaluation time.",
            provenance="EST",
        )

    origin_col = "forecast_origin" if "forecast_origin" in forecasts_df.columns else None
    if origin_col is None:
        return components.build_unavailable_block(
            title="Temporal stability not available",
            body="No forecast-origin column available to build a temporal view.",
            provenance="EST",
        )

    header = components.build_section_header(
        title="Temporal stability",
        subtitle="Forecast behavior across evaluation origins, as recorded in the RO1 artifacts.",
    )
    rows: list[Any] = [
        _temporal_method_context(),
        _build_temporal_origin_summary(forecasts_df, origin_col),
    ]
    return components.build_section(header=header, rows=rows)


def _temporal_method_context() -> dict[str, Any]:
    return {
        "label": "Scope",
        "body": (
            "Temporal stability uses the per-origin forecast rows from the RO1 probabilistic forecast artifact. "
            "It does not run a new backtest."
        ),
    }


def _build_temporal_origin_summary(forecasts_df: pd.DataFrame, origin_col: str) -> components.TableBlock:
    df = forecasts_df.copy()
    df[origin_col] = pd.to_datetime(df[origin_col], errors="coerce")
    df = df.dropna(subset=[origin_col])
    if df.empty:
        return components.build_empty_state(title="Temporal summary not surfaceable", body="No usable forecast origins.")

    agg = df.groupby(origin_col).agg(
        rows=("actual", "size"),
        covered_50=("raw_lower_50", lambda s: int((s.notna()).sum())),
    ).reset_index()
    agg["origin"] = agg[origin_col].dt.strftime("%Y-%m-%d")
    headers = ["Forecast origin", "Rows", "Interval-bounds present (50%)"]
    rows_data: list[dict[str, Any]] = []
    for _, row in agg.iterrows():
        rows_data.append(
            {
                "Forecast origin": str(row["origin"]),
                "Rows": str(int(row["rows"])),
                "Interval-bounds present (50%)": str(int(row["covered_50"])),
            }
        )
    return components.build_table(
        headers=headers,
        rows=rows_data,
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.LEFT, min_width=320),
    )


# ---------------------------------------------------------------------------
# J. RO1 -> RO2 handoff
# ---------------------------------------------------------------------------

def build_handoff_section(evidence: RO1Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    has_forecasts = ctx["forecast_row_count"] > 0
    has_calibration = ctx["has_calibration_scores"]

    rows: list[Any] = [
        _handoff_method_context(),
    ]

    if has_forecasts:
        rows.append(_build_handoff_available_block())
    else:
        rows.append(
            components.build_unavailable_block(
                title="Probabilistic handoff not available",
                body=(
                    "RO1 does not expose per-origin probabilistic forecast rows in the current dashboard "
                    "artifacts. The RO2 handoff is therefore shown as unavailable, not fabricated."
                ),
                provenance="EST",
            )
        )

    if has_calibration:
        rows.append(_build_handoff_calibration_block())

    rows.append(_build_handoff_research_flow())

    return components.build_section(
        header=components.build_section_header(
            title="Handoff to RO2",
            subtitle="What RO1 produces that RO2 can consume, and what is only expected.",
        ),
        rows=rows,
    )


def _handoff_method_context() -> dict[str, Any]:
    return {
        "label": "Scope",
        "body": (
            "The handoff section distinguishes what RO1 actually produced from what RO2 is expected to consume. "
            "Do not treat expected inputs as already produced."
        ),
    }


def _build_handoff_available_block() -> components.TableBlock:
    return components.build_table(
        headers=["RO1 output", "Status", "Notes"],
        rows=[
            {"RO1 output": "Point forecast", "Status": "AVAILABLE", "Notes": "Median forecast (q50) from existing RO1 artifacts."},
            {"RO1 output": "Predictive intervals", "Status": "AVAILABLE", "Notes": "50% / 80% intervals from existing RO1 artifacts."},
            {"RO1 output": "Quantiles (q10/q25/q75/q90)", "Status": "AVAILABLE", "Notes": "Distributional quantiles where present in the artifact."},
        ],
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.LEFT, min_width=420),
    )


def _build_handoff_calibration_block() -> components.TableBlock:
    return components.build_table(
        headers=["RO1 output", "Status", "Notes"],
        rows=[
            {"RO1 output": "Calibration flags", "Status": "AVAILABLE", "Notes": "Conformal calibration availability per row, where present."},
            {"RO1 output": "Calibration summary metrics", "Status": "AVAILABLE", "Notes": "Derived calibration evidence, if present in artifacts."},
        ],
        column_config=tables.TableConfig(default_alignment=tables.ColumnAlignment.LEFT, min_width=420),
    )


def _build_handoff_research_flow() -> components.ChartBlock:
    fig = _make_handoff_flow_figure()
    return components.build_chart(
        chart=fig,
        caption="Research flow from observed data through RO1 forecasting to RO3 procurement optimization.",
        chart_config=charts.CHART_CONFIG_FLOW,
    )


def build_handoff_interaction():
    """RO1 to RO2 handoff as a small, honest interaction guidance panel."""
    return components.build_section(
        header=components.build_section_header(
            title="How to read this page and pass the evidence",
            subtitle="A short workflow so a reviewer can move RO1 evidence into RO2 without inventing any metric.",
        ),
        rows=[
            _labeled_paragraph(
                "Step 1",
                "Start on the Research question and method context block. It states the forecast target, the dataset, the material/series and the horizon exactly as the RO1 artifacts describe them.",
            ),
            _labeled_paragraph(
                "Step 2",
                "Read the Probabilistic forecast chart and the per-row table. Point forecasts, predictive interval bounds and any conformal availability flags are read as recorded; nothing here is regenerated or refit.",
            ),
            _labeled_paragraph(
                "Step 3",
                "Check Calibration and Uncertainty width only where those columns exist. Missing calibration is reported as unavailable, never inferred from a coverage number.",
            ),
            _labeled_paragraph(
                "Step 4",
                "Use the handoff block to decide what RO2 may consume: a point forecast, an estimated distribution or interval, or only scenario parameters. Expected inputs are listed separately and are not treated as already produced.",
            ),
        ],
    )


def _make_handoff_flow_figure():
    import plotly.graph_objects as go

    steps = [
        ("Observed / historical data", theme.PRIMARY_TEXT),
        ("RO1 forecasting", theme.RESEARCH_STAGE_COLORS["RO1"]),
        ("Point forecast + predictive uncertainty", theme.RESEARCH_STAGE_COLORS["RO1"]),
        ("Calibration / distributional evaluation", theme.ACCENT),
        ("RO2 uncertainty propagation", theme.RESEARCH_STAGE_COLORS["RO2"]),
        ("RO3 procurement optimization", theme.RESEARCH_STAGE_COLORS["RO3"]),
    ]

    fig = go.Figure()
    n = len(steps)
    for i, (label, color) in enumerate(steps):
        x0 = i
        x1 = i + 1
        fig.add_shape(
            type="rect",
            x0=x0,
            y0=0.4,
            x1=x1,
            y1=0.7,
            fillcolor=color,
            line=dict(width=0),
            layer="below",
        )
        fig.add_trace(
            go.Scatter(
                x=[(x0 + x1) / 2],
                y=[0.55],
                mode="text",
                text=[label],
                textposition="middle center",
                textfont=dict(size=12, color="white"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        if i < n - 1:
            fig.add_shape(
                type="line",
                x0=x1,
                y0=0.55,
                x1=x1,
                y1=0.55,
                line=dict(color=theme.MUTED_TEXT, width=3),
                layer="above",
            )

    fig.update_layout(
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.2, n + 0.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.2, 0.9]),
        margin=dict(l=20, r=20, t=30, b=20),
        height=160,
    )
    return fig


# ---------------------------------------------------------------------------
# Research pipeline visual (compact)
# ---------------------------------------------------------------------------

def build_research_pipeline_block() -> components.SectionBlock:
    fig = _make_pipeline_figure()
    return components.build_section(
        header=components.build_section_header(
            title="Research pipeline",
            subtitle="How RO1 evidence fits between observed data and downstream research phases.",
        ),
        rows=[
            components.build_chart(
                chart=fig,
                caption="RO1 sits between observed/historical data and downstream joint uncertainty propagation.",
                chart_config=charts.CHART_CONFIG_FLOW,
            ),
        ],
    )


def _make_pipeline_figure() -> Any:
    import plotly.graph_objects as go

    steps = [
        ("Observed / historical data", theme.PRIMARY_TEXT),
        ("RO1 forecasting", theme.RESEARCH_STAGE_COLORS["RO1"]),
        ("Point forecast + predictive uncertainty", theme.RESEARCH_STAGE_COLORS["RO1"]),
        ("Calibration / distributional evaluation", theme.ACCENT),
    ]
    fig = go.Figure()
    n = len(steps)
    for i, (label, color) in enumerate(steps):
        x0 = i
        x1 = i + 1
        fig.add_shape(
            type="rect",
            x0=x0,
            y0=0.4,
            x1=x1,
            y1=0.7,
            fillcolor=color,
            line=dict(width=0),
            layer="below",
        )
        fig.add_trace(
            go.Scatter(
                x=[(x0 + x1) / 2],
                y=[0.55],
                mode="text",
                text=[label],
                textposition="middle center",
                textfont=dict(size=12, color="white"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        if i < n - 1:
            fig.add_shape(
                type="line",
                x0=x1,
                y0=0.55,
                x1=x1,
                y1=0.55,
                line=dict(color=theme.MUTED_TEXT, width=3),
                layer="above",
            )

    fig.update_layout(
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.2, n + 0.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.2, 0.9]),
        margin=dict(l=20, r=20, t=30, b=20),
        height=160,
    )
    return fig


# ---------------------------------------------------------------------------
# Page wiring
# ---------------------------------------------------------------------------

def build_page_content(evidence: RO1Evidence) -> list[components.SectionBlock]:
    """Return the RO1 page sections, in display order."""
    return [
        build_research_method_context(evidence),
        build_snapshot_cards(evidence),
        build_model_comparison(evidence),
        build_point_forecast_section(evidence),
        build_probabilistic_forecast_section(evidence),
        build_uncertainty_width_section(evidence),
        build_calibration_section(evidence),
        build_material_stability_section(evidence),
        build_temporal_stability_section(evidence),
        build_handoff_section(evidence),
        build_research_pipeline_block(),
        build_handoff_interaction(),
    ]
