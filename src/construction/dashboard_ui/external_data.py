"""CMIDO External Data workspace.

A Streamlit page that accepts a user-uploaded CSV or JSON table, previews and
profiles it, lets the user map its columns onto declared CMIDO field contracts,
validates that mapping, and — where the required fields and semantics are
satisfied — executes a genuinely supported analysis using the real CMIDO
statistical engines.

Every displayed number is computed from the uploaded rows only. Uploaded-data
runs are written to an isolated workspace and are clearly separated from the
canonical research artifacts. The three full research stages (RO1 training,
RO2 propagation, RO3 optimization) are shown as unavailable for uploaded data
with an explicit reason, never silently simulated.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pandas as pd

from src.construction.external_data import (
    MAX_UPLOAD_BYTES,
    SUPPORTED_EXTENSIONS,
    WorkflowResult,
    parse_upload,
    profile_table,
    run_workflow,
)
from src.construction.external_data.contracts import (
    ANALYSES,
    AnalysisSpec,
    analysis_by_key,
)
from src.construction.external_data.mapping import field_options
from src.construction.external_data.parsing import ParseError
from src.construction.external_data.lineage import RunStore
from src.construction.dashboard_ui import components
from src.construction.dashboard_ui.navigation import page_by_id
from src.construction.dashboard_ui.sections import build_page_header

PAGE_ID = "external_data"
RESEARCH_STAGE = "EXTERNAL_DATA"

#: Where uploaded-data runs are persisted (isolated from canonical results).
_DEFAULT_RUN_ROOT = (
    pathlib.Path(__file__).resolve().parents[3] / "results" / "external_data_runs"
)


def _page_title() -> str:
    return page_by_id(PAGE_ID).title


def _page_subtitle() -> str:
    return (
        "Upload a CSV or JSON table, map its columns to CMIDO fields, and run a "
        "genuinely supported analysis on your own data."
    )


def _supported_analyses() -> list[AnalysisSpec]:
    return [a for a in ANALYSES if a.supported]


def _unavailable_analyses() -> list[AnalysisSpec]:
    return [a for a in ANALYSES if not a.supported]


def _run_store() -> RunStore:
    return RunStore(_DEFAULT_RUN_ROOT)


# ---------------------------------------------------------------------------
# Upload + parse + profile
# ---------------------------------------------------------------------------


def _render_upload() -> tuple[bytes | None, str, Any]:
    """Render the uploader; return (payload, filename, parsed_or_None)."""
    components.render_markdown("### 1. Upload a data file")
    components.render_caption(
        f"Accepted: {', '.join(SUPPORTED_EXTENSIONS)}. "
        f"Maximum size {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB. "
        "Files are parsed as data only; no uploaded code is executed."
    )
    uploaded = components.widget_file_uploader(
        "Choose a CSV or JSON file",
        types=SUPPORTED_EXTENSIONS,
        key="external_data_upload",
    )
    if uploaded is None:
        components.render_empty_state(
            "Upload a CSV or JSON table to begin. A deterministic example "
            "fixture (a forecast-intervals table) ships with the repository if "
            "you want to try the workflow first.",
            title="No file selected",
        )
        return None, "", None

    payload = uploaded.getvalue()
    filename = uploaded.name
    try:
        parsed = parse_upload(filename, payload)
    except ParseError as exc:
        components.render_error_state(
            "Could not read the uploaded file",
            description=str(exc),
        )
        return payload, filename, None
    return payload, filename, parsed


def _render_preview(parsed: Any) -> dict[str, Any]:
    components.render_markdown("### 2. Preview and profile")
    profile = profile_table(parsed.frame)
    c1, c2, c3 = components.widget_columns(3)
    c1.metric("Rows", f"{profile['row_count']:,}")
    c2.metric("Columns", f"{profile['column_count']:,}")
    c3.metric("Duplicate rows", f"{profile['duplicate_rows']:,}")

    components.render_markdown("**First rows**")
    components.widget_dataframe(parsed.frame.head(20))

    components.render_markdown("**Column profile**")
    profile_frame = pd.DataFrame(
        [
            {
                "column": c["name"],
                "type": c["inferred_type"],
                "missing": f"{c['missing_fraction']:.0%}",
                "distinct": c["distinct_count"],
            }
            for c in profile["columns"]
        ]
    )
    components.widget_dataframe(profile_frame, hide_index=True)

    if profile["warnings"]:
        components.render_markdown("**Validation warnings**")
        for warning in profile["warnings"]:
            components.render_warning(warning)
    return profile


# ---------------------------------------------------------------------------
# Analysis selection + mapping
# ---------------------------------------------------------------------------


def _render_analysis_and_mapping(profile: dict[str, Any]) -> tuple[str, dict[str, str]]:
    components.render_markdown("### 3. Choose an analysis and map columns")
    supported = _supported_analyses()
    labels = {a.label: a.key for a in supported}
    choice = components.widget_selectbox(
        "Analysis", list(labels.keys()), key="external_data_analysis"
    )
    analysis_key = labels[choice]
    spec = analysis_by_key(analysis_key)

    components.render_caption(spec.summary)

    column_names = [c["name"] for c in profile["columns"]]
    mapping: dict[str, str] = {}

    components.render_markdown("**Required fields**")
    for field_spec in spec.required_fields():
        options = field_options(profile, field_spec)
        options = options or column_names
        picked = components.widget_selectbox(
            f"{field_spec.label} ({field_spec.field_type.value})",
            [""] + options,
            key=f"ext_field_{field_spec.key}",
            help=field_spec.describe(),
        )
        mapping[field_spec.key] = picked or ""

    optional = spec.optional_fields()
    if optional:
        with components.widget_expander("Optional fields", expanded=False):
            for field_spec in optional:
                options = field_options(profile, field_spec)
                options = options or column_names
                picked = components.widget_selectbox(
                    f"{field_spec.label} ({field_spec.field_type.value})",
                    [""] + options,
                    key=f"ext_field_{field_spec.key}",
                    help=field_spec.describe(),
                )
                mapping[field_spec.key] = picked or ""

    return analysis_key, mapping


# ---------------------------------------------------------------------------
# Validation preview
# ---------------------------------------------------------------------------


def _render_validation_preview(parsed: Any, analysis_key: str, mapping: dict[str, str]) -> bool:
    from src.construction.external_data.mapping import build_mapping_spec, validate_mapping

    spec = build_mapping_spec(analysis_key, mapping)
    report = validate_mapping(parsed.frame, spec)
    components.render_markdown("### 4. Validation")
    if report.ok:
        components.render_success("Mapping is valid. The analysis can run.")
    else:
        components.render_error(
            "Mapping has blocking problems. Fix them before running."
        )
        for issue in report.errors:
            components.render_error(f"{issue.field_key or 'mapping'}: {issue.message}")
    for issue in report.warnings:
        components.render_warning(f"{issue.field_key or 'mapping'}: {issue.message}")
    return report.ok


# ---------------------------------------------------------------------------
# Execution + results
# ---------------------------------------------------------------------------


def _render_results(result: WorkflowResult) -> None:
    analysis = result.analysis or {}
    components.render_markdown("### 5. Results (computed from your uploaded data)")
    components.render_caption(
        "These numbers are derived only from the rows you uploaded. They are "
        "not canonical research results and do not overwrite them."
    )

    if analysis.get("analysis") == "descriptive_statistics":
        rows = analysis.get("rows", [])
        components.widget_dataframe(pd.DataFrame(rows), hide_index=True)
    elif analysis.get("analysis") == "forecast_coverage":
        c1, c2, c3 = components.widget_columns(3)
        c1.metric("Rows scored", f"{analysis.get('n_scored', 0):,}")
        c2.metric("Coverage rate", f"{analysis.get('coverage_rate', 0.0):.3f}")
        c3.metric("Mean interval width", f"{analysis.get('mean_interval_width', 0.0):.3f}")
        if "pinball_loss_mean" in analysis:
            components.widget_metric(
                "Pinball loss (mean)",
                f"{analysis.get('pinball_loss_mean', 0.0):.4f}",
            )

    _render_lineage(result)
    _render_exports(result)


def _render_lineage(result: WorkflowResult) -> None:
    record = result.record
    if record is None:
        return
    components.render_markdown("**Run lineage**")
    lineage = pd.DataFrame(
        [
            ("Run ID", record.run_id),
            ("Input file", record.input_filename),
            ("Input SHA-256", record.input_sha256[:16] + "…"),
            ("Rows / columns", f"{record.row_count:,} / {record.column_count:,}"),
            ("Seed", str(record.seed)),
            ("Provenance", record.provenance_class),
            ("Status", record.status),
            ("Duration (s)", f"{record.duration_seconds:.3f}"),
        ],
        columns=["field", "value"],
    )
    components.widget_dataframe(lineage, hide_index=True)


def _render_exports(result: WorkflowResult) -> None:
    record = result.record
    if record is None:
        return
    components.render_markdown("**Export**")
    components.render_caption(
        "Download the validated input mapping, the run summary and the result "
        "table. Exports reflect this uploaded dataset only."
    )
    cols = components.widget_columns(3)
    mapping_json = __import__("json").dumps(record.mapping, indent=2, sort_keys=True)
    cols[0].download_button(
        "Schema mapping (JSON)", mapping_json,
        file_name=f"{record.run_id}_mapping.json", mime="application/json",
        key="ext_dl_mapping",
    )
    record_json = __import__("json").dumps(record.as_dict(), indent=2, default=str)
    cols[1].download_button(
        "Run summary (JSON)", record_json,
        file_name=f"{record.run_id}_run_record.json", mime="application/json",
        key="ext_dl_record",
    )
    analysis = result.analysis or {}
    rows = analysis.get("rows")
    if rows:
        csv_text = pd.DataFrame(rows).to_csv(index=False)
    else:
        flat = {k: v for k, v in analysis.items() if not isinstance(v, (list, dict))}
        csv_text = pd.DataFrame([flat]).to_csv(index=False)
    cols[2].download_button(
        "Result table (CSV)", csv_text,
        file_name=f"{record.run_id}_result.csv", mime="text/csv",
        key="ext_dl_result",
    )


def _render_unavailable() -> None:
    components.render_markdown("### Research stages not run on uploaded data")
    components.render_caption(
        "These require frozen upstream artifacts and are never simulated on an "
        "arbitrary upload. They are listed here so the boundary is explicit."
    )
    for spec in _unavailable_analyses():
        with components.widget_expander(f"{spec.label} — not available", expanded=False):
            components.render_markdown(spec.summary)
            components.render_warning(spec.unavailable_reason)


# ---------------------------------------------------------------------------
# Page render
# ---------------------------------------------------------------------------


def render_page(*, include_header: bool = True) -> None:
    """Render the External Data workspace."""
    if include_header:
        components.inject_css()
        page_info = page_by_id(PAGE_ID)
        header = build_page_header(
            title=_page_title(),
            subtitle=_page_subtitle(),
            research_stage=RESEARCH_STAGE,
            evidence_state=page_info.implementation.value,
        )
        components.render_html(header)

    payload, filename, parsed = _render_upload()
    if parsed is None:
        _render_unavailable()
        return

    profile = _render_preview(parsed)
    analysis_key, mapping = _render_analysis_and_mapping(profile)
    valid = _render_validation_preview(parsed, analysis_key, mapping)

    if components.widget_button("Run analysis", key="ext_run", disabled=not valid):
        result = run_workflow(filename, payload, analysis_key, mapping, store=_run_store())
        components.set_state("ext_last_result", result)

    last: WorkflowResult | None = components.get_state("ext_last_result")
    if last is not None:
        if last.error:
            components.render_error_state(
                "Analysis did not run",
                description=last.error,
            )
        else:
            _render_results(last)

    _render_unavailable()
