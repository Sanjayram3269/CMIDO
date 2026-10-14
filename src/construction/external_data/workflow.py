"""End-to-end external-data workflow orchestrator.

Ties parsing → profiling → mapping validation → analysis execution → lineage
persistence → export together in one testable function, so the same code path
the dashboard calls is exercised directly by automated tests.  Uploaded-data
outputs are written to an isolated run workspace, never to canonical
``results/`` artifacts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .analysis import DEFAULT_BOOTSTRAP_RESAMPLES, DEFAULT_SEED, AnalysisError, execute_analysis
from .contracts import MappingSpec, ProvenanceClass, ValidationReport
from .lineage import RunRecord, RunStore, finish_record, start_record
from .mapping import build_mapping_spec, validate_mapping
from .parsing import ParsedTable, ParseError, parse_upload
from .profiling import profile_table


@dataclass
class WorkflowResult:
    """The full outcome of one external-data run."""

    parsed: ParsedTable
    profile: dict[str, Any]
    mapping: MappingSpec
    validation: ValidationReport
    analysis: dict[str, Any] | None = None
    record: RunRecord | None = None
    exports: dict[str, str] = field(default_factory=dict)
    error: str = ""


def run_workflow(
    filename: str,
    payload: bytes,
    analysis_key: str,
    column_by_field: dict[str, str],
    *,
    store: RunStore | None = None,
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
) -> WorkflowResult:
    """Run the full ingest→analyse→persist workflow for one upload.

    Never raises for expected user errors (bad format, invalid mapping,
    unsatisfiable inputs); those are returned in ``WorkflowResult.error`` and
    in the validation report so the UI can render an honest state.
    """
    store = store or RunStore()

    parsed = parse_upload(filename, payload)
    profile = profile_table(parsed.frame)
    mapping = build_mapping_spec(analysis_key, column_by_field)
    validation = validate_mapping(parsed.frame, mapping)

    result = WorkflowResult(
        parsed=parsed, profile=profile, mapping=mapping, validation=validation
    )

    if not validation.ok:
        result.error = "Validation failed; no analysis was run."
        return result

    # Provenance: the measure/scored columns are derived from uploaded observed
    # rows; bootstrap intervals are statistical estimates.
    provenance = ProvenanceClass.DER.value

    record = start_record(
        analysis_key=mapping.analysis_key,
        input_filename=filename,
        payload=payload,
        row_count=int(parsed.frame.shape[0]),
        column_count=int(parsed.frame.shape[1]),
        mapping=mapping.column_by_field,
        validation=validation.as_dict(),
        seed=seed,
        resamples=resamples,
        provenance_class=provenance,
    )
    started = time.monotonic()

    try:
        analysis = execute_analysis(
            parsed.frame, mapping, seed=seed, resamples=resamples
        )
    except AnalysisError as exc:
        finish_record(record, started, ok=False, error=str(exc))
        store.write_json(record.run_id, "run_record.json", record.as_dict())
        result.record = record
        result.error = str(exc)
        return result

    result.analysis = analysis

    # Persist lineage + isolated exports.
    exports: dict[str, str] = {}
    exports["mapping"] = store.write_json(
        record.run_id, "schema_mapping.json", mapping.column_by_field
    )
    exports["validation"] = store.write_json(
        record.run_id, "validation_report.json", validation.as_dict()
    )
    exports["profile"] = store.write_json(
        record.run_id, "input_profile.json", profile
    )
    exports["result"] = store.write_json(record.run_id, "analysis_result.json", analysis)

    # Export result tables as CSV where the analysis yields rows.
    rows = analysis.get("rows")
    if isinstance(rows, list) and rows:
        exports["result_table"] = store.write_csv(
            record.run_id, "analysis_result.csv", rows
        )
    elif analysis.get("analysis") == "forecast_coverage":
        exports["result_table"] = store.write_csv(
            record.run_id,
            "analysis_result.csv",
            [{k: v for k, v in analysis.items() if not isinstance(v, (list, dict))}],
        )

    finish_record(record, started, ok=True)
    record.output_dir = str(store.run_dir(record.run_id))
    record.outputs = exports
    exports["run_record"] = store.write_json(
        record.run_id, "run_record.json", record.as_dict()
    )

    result.record = record
    result.exports = exports
    return result
