# ---------------------------------------------------------------------------
# CMIDO 10A.11 — Real-World Data workspace
#
# Read-only, schema-validated, provenance-aware rendering of the registered
# real-data evidence: the 9A ingestion fixture, the 9B PSLIB project audit,
# the 9B SUCCESS logistics audit and the two gate manifests. This module does
# NOT run research computations, does NOT import research engines, does NOT
# join the PSLIB and SUCCESS streams, and does NOT infer dataset meaning,
# dates, sample counts or experimental conditions from filenames — every
# displayed value comes from a registered artifact or its provenance record.
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Any

import pandas as pd

from src.construction.dashboard_data.contract import (
    DashboardSnapshot,
    RealDataEvidence,
)
from src.construction.dashboard_ui import components
from src.construction.dashboard_ui import formatting
from src.construction.dashboard_ui import theme
from src.construction.dashboard_ui.navigation import (
    page_by_id,
    page_is_planned,
)
from src.construction.dashboard_ui.sections import (
    build_page_header,
)

# Presentation helpers shared with the other registry-driven workspaces:
# honest missing values, provenance record reads and filesystem-path
# suppression for audit details.
from ._procurement_helpers import (
    _clean_audit_detail,
    _fmt_cell,
    _fmt_int,
    _labeled_paragraph,
    _prov_get,
    _status_text,
)

PAGE_ID = "real_world_data"
RESEARCH_STAGE = "REAL_DATA"

#: Registered real-data artifacts, in the order the page presents them.
REAL_DATA_ARTIFACT_IDS: tuple[str, ...] = (
    "REAL_9A_CANONICAL",
    "REAL_9A_INGESTION_AUDIT",
    "REAL_9A_MANIFEST",
    "REAL_9B_PSLIB_AUDIT",
    "REAL_9B_LOGISTICS_AUDIT",
    "REAL_9B_MANIFEST",
)

#: Human titles for the registered artifact ids (presentation only).
_ARTIFACT_TITLES: dict[str, str] = {
    "REAL_9A_CANONICAL": "9A canonical fixture dataset",
    "REAL_9A_INGESTION_AUDIT": "9A fixture ingestion audit",
    "REAL_9A_MANIFEST": "9A generalization gate manifest",
    "REAL_9B_PSLIB_AUDIT": "9B PSLIB project audit",
    "REAL_9B_LOGISTICS_AUDIT": "9B SUCCESS logistics audit",
    "REAL_9B_MANIFEST": "9B real-project gate manifest",
}

#: Provenance vocabulary as documented by the 9B phase (OBS/DER/EST/SCN).
PROVENANCE_LEGEND: tuple[tuple[str, str], ...] = (
    ("OBS", "Observed — directly represented in the public source."),
    ("DER", "Derived — deterministic transformation performed by CMIDO."),
    ("EST", "Estimated — modelled quantity; must be labelled before use."),
    ("SCN", "Scenario — controlled scenario quantity."),
)


# ---------------------------------------------------------------------------
# Pure presentation builders (no Streamlit, no research engine)
# ---------------------------------------------------------------------------


def _humanize(token: Any) -> str:
    """Presentation label for a recorded identifier: underscores become spaces.

    This is a display transform only. It never changes a value and never
    derives new meaning from a name.
    """
    return str(token).replace("_", " ")


def _fmt_size(num_bytes: Any) -> str:
    """Human file size from a provenance record; honest missing display."""
    if num_bytes is None:
        return formatting.MISSING_DISPLAY
    try:
        size = float(num_bytes)
    except (TypeError, ValueError):
        return formatting.MISSING_DISPLAY
    if size >= 1_048_576:
        return f"{formatting.format_number(size / 1_048_576, decimals=1)} MB"
    if size >= 1024:
        return f"{formatting.format_number(size / 1024, decimals=1)} KB"
    return f"{int(size)} B"


def provenance_code(value: Any) -> str:
    """The OBS/DER/EST/SCN code recorded for a value, or an honest blank."""
    return str(getattr(value, "value", value) or "")


def provenance_label(code: str) -> str:
    """Legend sentence for a provenance code; honest fallback when unknown."""
    for known, meaning in PROVENANCE_LEGEND:
        if code == known:
            return meaning
    return "Provenance class not recorded for this artifact."


def build_provenance_rows(evidence: RealDataEvidence) -> list[dict[str, Any]]:
    """Curate the provenance inventory of the real-data artifacts.

    One row per provenance record attached to the ``RealDataEvidence``
    bundle. Statuses (AVAILABLE / MISSING / INVALID / TOO_LARGE) are carried
    through exactly as the loader and validator recorded them.
    """
    rows: list[dict[str, Any]] = []
    for entry in evidence.provenance:
        rows.append(
            {
                "artifact_id": str(_prov_get(entry, "artifact_id", "")),
                "status": _status_text(_prov_get(entry, "status")),
                "provenance_class": provenance_code(
                    _prov_get(entry, "provenance_class")
                ),
                "research_stage": str(_prov_get(entry, "research_stage", "") or ""),
                "row_count": _prov_get(entry, "row_count"),
                "file_size_bytes": _prov_get(entry, "file_size_bytes"),
                "schema_status": str(
                    _prov_get(entry, "schema_status", "UNCHECKED") or "UNCHECKED"
                ),
            }
        )
    return rows


def artifact_status_index(provenance_rows: list[dict[str, Any]]) -> dict[str, str]:
    """Map artifact id -> recorded status; absent artifacts read MISSING."""
    index = {
        row["artifact_id"]: row["status"]
        for row in provenance_rows
        if row.get("artifact_id")
    }
    for artifact_id in REAL_DATA_ARTIFACT_IDS:
        index.setdefault(artifact_id, "MISSING")
    return index


def build_artifact_table_rows(
    provenance_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Display rows for the registered real-data artifact inventory."""
    by_id = {row["artifact_id"]: row for row in provenance_rows}
    rows: list[dict[str, Any]] = []
    for artifact_id in REAL_DATA_ARTIFACT_IDS:
        record = by_id.get(artifact_id)
        if record is None:
            rows.append(
                {
                    "Artifact": _ARTIFACT_TITLES[artifact_id],
                    "Status": "NOT REGISTERED",
                    "Provenance": formatting.MISSING_DISPLAY,
                    "Rows": formatting.MISSING_DISPLAY,
                    "Size": formatting.MISSING_DISPLAY,
                    "Schema check": formatting.MISSING_DISPLAY,
                }
            )
            continue
        rows.append(
            {
                "Artifact": _ARTIFACT_TITLES[artifact_id],
                "Status": record["status"],
                "Provenance": record["provenance_class"]
                or formatting.MISSING_DISPLAY,
                "Rows": _fmt_int(record["row_count"])
                if record["row_count"] is not None
                else formatting.MISSING_DISPLAY,
                "Size": _fmt_size(record["file_size_bytes"]),
                "Schema check": _humanize(record["schema_status"])
                if record["schema_status"] not in ("", "UNCHECKED")
                else record["schema_status"],
            }
        )
    return rows


def build_fixture_identity_rows(canonical_9a: dict[str, Any]) -> list[dict[str, str]]:
    """Label/value identity rows for the 9A fixture, straight from the artifact."""
    project = canonical_9a.get("project")
    project = project if isinstance(project, dict) else {}
    metadata = canonical_9a.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    pairs = [
        ("Dataset id", canonical_9a.get("dataset_id")),
        ("Project id", project.get("project_id")),
        ("Project name", project.get("project_name")),
        ("Location", project.get("location")),
        ("Project type", project.get("project_type")),
        ("Canonical schema version", canonical_9a.get("schema_version")),
        ("Ingestion schema version", metadata.get("ingestion_schema_version")),
        ("Source format", metadata.get("source_format")),
        ("Dataset fingerprint (SHA-256)", canonical_9a.get("fingerprint_sha256")),
    ]
    return [
        {"Property": label, "Recorded value": _fmt_cell(value)}
        for label, value in pairs
    ]


def build_fixture_activity_rows(canonical_9a: dict[str, Any]) -> list[dict[str, Any]]:
    """Activity rows of the 9A fixture exactly as the artifact records them."""
    activities = canonical_9a.get("activities")
    if not isinstance(activities, list):
        return []
    rows: list[dict[str, Any]] = []
    for activity in activities:
        if not isinstance(activity, dict):
            continue
        rows.append(
            {
                "Activity": _fmt_cell(activity.get("activity_id")),
                "Code": _fmt_cell(activity.get("activity_code")),
                "Name": _fmt_cell(activity.get("activity_name")),
                "Duration (days)": _fmt_cell(activity.get("duration_days")),
                "Status": _fmt_cell(activity.get("status")),
                "Planned start": _fmt_cell(activity.get("planned_start")),
                "Planned finish": _fmt_cell(activity.get("planned_finish")),
            }
        )
    return rows


def build_fixture_time_range(canonical_9a: dict[str, Any]) -> str | None:
    """Earliest planned start and latest planned finish recorded in the fixture.

    Returns ``None`` when the artifact records no dates — the range is never
    inferred from file names, source paths or any other metadata.
    """
    activities = canonical_9a.get("activities")
    if not isinstance(activities, list):
        return None
    starts = [
        str(a.get("planned_start"))
        for a in activities
        if isinstance(a, dict) and a.get("planned_start")
    ]
    finishes = [
        str(a.get("planned_finish"))
        for a in activities
        if isinstance(a, dict) and a.get("planned_finish")
    ]
    if not starts or not finishes:
        return None
    return f"{min(starts)} to {max(finishes)}"


def build_fixture_row_count_rows(canonical_9a: dict[str, Any]) -> list[dict[str, str]]:
    """Source row counts and rejection counts recorded by the 9A ingestion."""
    metadata = canonical_9a.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    counts = metadata.get("source_row_counts")
    counts = counts if isinstance(counts, dict) else {}
    rows = [
        {"Table": _humanize(table), "Source rows": _fmt_int(total)}
        for table, total in counts.items()
    ]
    rows.append(
        {
            "Table": "Rejected records",
            "Source rows": _fmt_int(metadata.get("rejected_record_count")),
        }
    )
    return rows


def build_pslib_coverage_rows(pslib_audit: dict[str, Any]) -> list[dict[str, str]]:
    """Coverage metrics for the PSLIB stream — explicit artifact fields only.

    Every value is read from a recorded field; a field the audit does not
    carry renders as the honest missing display instead of a guess.
    """
    snapshots = pslib_audit.get("control_snapshot_names")
    if isinstance(snapshots, list) and snapshots:
        snapshot_value = f"{len(snapshots)} ({', '.join(str(s) for s in snapshots)})"
    else:
        snapshot_value = formatting.MISSING_DISPLAY
    pairs = [
        ("Activities", pslib_audit.get("activity_count")),
        ("Dependencies", pslib_audit.get("dependency_count")),
        ("Risk profiles", pslib_audit.get("risk_profile_count")),
        ("Control snapshots", snapshot_value),
        ("Resource rows", pslib_audit.get("resource_row_count")),
        ("Rejected dependency records", pslib_audit.get("rejected_dependency_records")),
    ]
    rows: list[dict[str, str]] = []
    for label, value in pairs:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            rendered = value if isinstance(value, str) else formatting.MISSING_DISPLAY
        else:
            rendered = _fmt_int(value)
        rows.append({"Coverage metric": label, "Recorded value": rendered})
    return rows


def build_pslib_identity_rows(pslib_audit: dict[str, Any]) -> list[dict[str, str]]:
    """Identity rows for the PSLIB stream from explicit audit fields."""
    pairs = [
        ("Dataset id", pslib_audit.get("dataset_id")),
        ("Project id", pslib_audit.get("project_id")),
        ("Project name", pslib_audit.get("project_name")),
        ("PSLIB release", pslib_audit.get("pslib_release")),
        ("Audit schema version", pslib_audit.get("schema_version")),
        ("Source fingerprint (SHA-256)", pslib_audit.get("source_sha256")),
        (
            "Canonical fingerprint (SHA-256)",
            pslib_audit.get("canonical_fingerprint_sha256"),
        ),
    ]
    return [
        {"Property": label, "Recorded value": _fmt_cell(value)}
        for label, value in pairs
    ]


def build_logistics_coverage_rows(logistics_audit: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-table coverage for the SUCCESS stream, from the logistics audit."""
    tables = logistics_audit.get("tables")
    if not isinstance(tables, dict):
        return []
    rows: list[dict[str, Any]] = []
    for table_name, meta in tables.items():
        meta = meta if isinstance(meta, dict) else {}
        headers = meta.get("headers")
        column_count = len(headers) if isinstance(headers, list) else None
        rows.append(
            {
                "Table": _humanize(table_name),
                "Rows": _fmt_int(meta.get("row_count")),
                "Columns": _fmt_int(column_count)
                if column_count is not None
                else formatting.MISSING_DISPLAY,
                "Invalid rows": _fmt_int(meta.get("invalid_numeric_or_date_rows")),
                "Recorded provenance": provenance_code(meta.get("provenance"))
                or formatting.MISSING_DISPLAY,
            }
        )
    return rows


def build_logistics_summary_rows(logistics_audit: dict[str, Any]) -> list[dict[str, str]]:
    """Derived summary of the SUCCESS stream as recorded by the 9B gate."""
    summary = logistics_audit.get("derived_summary")
    summary = summary if isinstance(summary, dict) else {}
    labels = {
        "site_count": "Construction sites",
        "material_demand_count": "Material demand rows",
        "material_demand_period_count": "Material demand period rows",
        "origin_destination_count": "Origin–destination rows",
        "supplier_material_rows": "Supplier–material rows",
        "truck_count": "Trucks",
        "ccc_count": "Consolidation centres",
        "unique_materials_in_demand": "Unique materials in demand",
        "unique_suppliers_in_demand": "Unique suppliers in demand",
    }
    rows: list[dict[str, str]] = []
    for key, label in labels.items():
        if key in summary:
            rows.append({"Recorded summary metric": label, "Value": _fmt_int(summary[key])})
    return rows


def build_top_materials_rows(logistics_audit: dict[str, Any]) -> list[dict[str, Any]]:
    """Top materials by demand rows, exactly as the audit recorded them."""
    summary = logistics_audit.get("derived_summary")
    summary = summary if isinstance(summary, dict) else {}
    entries = summary.get("top_materials_by_demand_rows")
    if not isinstance(entries, list):
        return []
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            rows.append(
                {
                    "Material": _fmt_cell(entry[0]),
                    "Demand rows": _fmt_int(entry[1]),
                }
            )
    return rows


def build_logistics_source_rows(logistics_audit: dict[str, Any]) -> list[dict[str, str]]:
    """Recorded source identity of the SUCCESS bundle (format, DOI, scope)."""
    pairs = [
        ("Source format", logistics_audit.get("source_format")),
        ("Dataset DOI", logistics_audit.get("dataset_doi")),
        ("Audit schema version", logistics_audit.get("schema_version")),
        ("Recorded provenance", provenance_code(logistics_audit.get("provenance"))),
    ]
    return [
        {"Property": label, "Recorded value": _fmt_cell(value)}
        for label, value in pairs
    ]


def build_gate_summary(manifest: dict[str, Any]) -> dict[str, str]:
    """Compact gate result: status, checks passed and checks total."""
    status = str(manifest.get("status", "") or "")
    return {
        "status": status if status else "not recorded",
        "passed": _fmt_int(manifest.get("checks_passed")),
        "total": _fmt_int(manifest.get("checks_total")),
    }


def build_gate_check_rows(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Gate check rows with humanized check names and path-free details."""
    checks = manifest.get("checks")
    if not isinstance(checks, list):
        return []
    rows: list[dict[str, str]] = []
    for check in checks:
        check = check if isinstance(check, dict) else {}
        passed = check.get("passed")
        if isinstance(passed, bool):
            result = "PASS" if passed else "FAIL"
        else:
            result = formatting.MISSING_DISPLAY
        detail = _clean_audit_detail(str(check.get("detail", "") or ""))
        rows.append(
            {
                "Check": _humanize(check.get("check", "")),
                "Result": result,
                "Recorded detail": detail or formatting.MISSING_DISPLAY,
            }
        )
    return rows


def build_gate_notes(manifest: dict[str, Any]) -> list[str]:
    """Extra recorded manifest metadata (scope, boundary) — never paths."""
    notes: list[str] = []
    scope = _clean_audit_detail(str(manifest.get("scope", "") or ""))
    if scope:
        notes.append(f"Scope: {scope}")
    frozen = manifest.get("frozen_predecessor_phases")
    if isinstance(frozen, list) and frozen:
        notes.append(
            "Frozen predecessor phases: " + ", ".join(str(p) for p in frozen) + "."
        )
    boundary = str(manifest.get("integration_boundary", "") or "")
    if boundary:
        notes.append(f"Recorded integration boundary: {boundary}")
    return notes


# ---------------------------------------------------------------------------
# Section-level framing
# ---------------------------------------------------------------------------


def _page_title() -> str:
    return "Real-World Data"


def _page_subtitle() -> str:
    return (
        "Observed real-data evidence: dataset coverage, data quality, "
        "provenance and limitations — with the PSLIB and SUCCESS streams kept separate."
    )


def _availability_cards(
    evidence: RealDataEvidence, provenance_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """KPI row derived entirely from provenance records and gate manifests."""
    total = len(provenance_rows)
    available = sum(1 for row in provenance_rows if row["status"] == "AVAILABLE")
    gate_9a = build_gate_summary(evidence.generalization_manifest_9a)
    gate_9b = build_gate_summary(evidence.experiment_9b)
    logistics = evidence.logistics_audit.get("tables")
    table_count = (
        str(len(logistics))
        if isinstance(logistics, dict) and logistics
        else formatting.MISSING_DISPLAY
    )
    return [
        {
            "label": "Registered artifacts",
            "value": f"{available} of {total}" if total else formatting.MISSING_DISPLAY,
            "description": "Real-data artifacts loaded and schema-validated through the 10A.2-B contract.",
            "research_stage": RESEARCH_STAGE,
        },
        {
            "label": "9A gate result",
            "value": _gate_card_value(gate_9a),
            "description": "Real-data ingestion / generalization gate, as recorded in its manifest.",
            "research_stage": RESEARCH_STAGE,
        },
        {
            "label": "9B gate result",
            "value": _gate_card_value(gate_9b),
            "description": "Empirical real-project end-to-end gate, as recorded in its manifest.",
            "research_stage": RESEARCH_STAGE,
        },
        {
            "label": "SUCCESS tables audited",
            "value": table_count,
            "description": "Public construction-logistics CSV tables covered by the 9B logistics audit.",
            "research_stage": RESEARCH_STAGE,
        },
    ]


def _gate_card_value(summary: dict[str, str]) -> str:
    if summary["status"] in ("PASS", "FAIL") and summary["total"] != formatting.MISSING_DISPLAY:
        return f"{summary['status']} {summary['passed']}/{summary['total']}"
    return formatting.MISSING_DISPLAY


def _render_overview(
    evidence: RealDataEvidence, provenance_rows: list[dict[str, Any]]
) -> None:
    """Top-level framing: streams, boundary and availability at a glance."""
    total = len(provenance_rows)
    available = sum(1 for row in provenance_rows if row["status"] == "AVAILABLE")
    if total and available == total:
        state = "available"
    elif available:
        state = "partial"
    else:
        state = "empty"

    components.render_section_header(
        title="Real-world evidence",
        subtitle=(
            "Registered 9A and 9B artifacts: what the observed datasets contain, "
            "how they were audited, and what this evidence does not cover."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state=state,
        methodology=(
            "Registry-driven (10A.2-B). Artifacts are loaded, size-capped and "
            "provenance-tagged before rendering; nothing is recomputed, joined "
            "or inferred in the UI."
        ),
        provenance="See the artifact inventory and the provenance legend below.",
        uncertainty=(
            "Counts, coverage and metadata are shown only where a registered "
            "artifact records them; missing metadata renders as missing."
        ),
    )

    components.render_kpi_columns(_availability_cards(evidence, provenance_rows))

    components.render_paragraph(
        {
            "label": "What this page reports",
            "body": [
                "Three separate evidence streams from phases 9A and 9B, each with its own registered artifacts:",
                "",
                "- PSLIB / DSLIB v3.4 — the empirical project workbook audit (one real construction project workbook,",
                "  with recorded activity, dependency, risk-profile, control-snapshot and resource counts).",
                "- SUCCESS — the construction-logistics bundle audit (seven public CSV tables with recorded headers,",
                "  row counts, invalid-row counts and source fingerprints).",
                "- 9A ingestion fixture — a small civil-project CSV-bundle fixture that proves the ingestion adapter",
                "  and gate. Per the 9A documentation it is not the user's actual civil-project dataset, and it is",
                "  neither PSLIB nor SUCCESS.",
                "",
                "The streams are never joined. This page presents ingestion and gate evidence about the datasets; it "
                "does not claim external generalization, deployment readiness or real-world validation beyond what "
                "the recorded gates demonstrate.",
            ],
        }
    )

    integration = str(evidence.experiment_9b.get("integration_boundary", "") or "")
    values = [
        _labeled_paragraph(
            "PSLIB stream (observed)",
            "Empirical project workbook audited by the 9B gate. Provenance class OBS as recorded in the registry; "
            "the audit reports facts about the public source workbook (project C2025-02, PSLIB / DSLIB v3.4).",
        ),
        _labeled_paragraph(
            "SUCCESS stream (observed)",
            "Public construction-logistics CSV bundle audited table by table by the 9B gate, with the dataset DOI "
            "recorded in the audit itself. Kept strictly separate from the PSLIB project workbook.",
        ),
        _labeled_paragraph(
            "9A fixture stream (adapter proof)",
            "A controlled civil-project fixture used to prove that external CSV bundles can be ingested through an "
            "explicit mapping contract. It is a boundary demonstration, not an observed construction project.",
        ),
        _labeled_paragraph(
            "Integration boundary (recorded by the 9B gate)",
            integration if integration else "Not recorded in the registered 9B manifest.",
        ),
    ]
    components.render_inline_label_values(values)


def _render_artifact_inventory(
    evidence: RealDataEvidence,
    provenance_rows: list[dict[str, Any]],
    status_index: dict[str, str],
) -> None:
    """Registered-artifact inventory plus explicit states for anything absent."""
    components.render_section_header(
        title="Registered real-data artifacts",
        subtitle=(
            "Every artifact behind this page, with the status, provenance class "
            "and schema outcome the loader and validator recorded."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE" if provenance_rows else "empty",
        methodology="Loaded through the 10A.2-B artifact registry; JSON artifacts are read only within the size cap.",
        provenance="Registry provenance records (schema status included).",
    )

    rows = build_artifact_table_rows(provenance_rows)
    components.render_table(
        pd.DataFrame(rows),
        source="10A.2-B artifact registry and provenance records",
        research_stage=RESEARCH_STAGE,
        empty_message="No real-data artifacts were registered for this snapshot.",
    )

    for artifact_id in REAL_DATA_ARTIFACT_IDS:
        status = status_index.get(artifact_id, "MISSING")
        if status != "AVAILABLE":
            components.render_artifact_state(
                artifact_id,
                status,
                description=_ARTIFACT_TITLES[artifact_id],
                stage=RESEARCH_STAGE,
                provenance=_provenance_class_for(provenance_rows, artifact_id),
            )


def _provenance_class_for(
    provenance_rows: list[dict[str, Any]], artifact_id: str
) -> str:
    for row in provenance_rows:
        if row["artifact_id"] == artifact_id:
            return row["provenance_class"]
    return ""


def _render_missing_stream(
    artifact_id: str,
    status: str,
    headline: str,
    why_it_matters: list[str],
    provenance_class: str = "",
) -> None:
    """Honest unavailable state: what is missing, and why the gap matters."""
    components.render_artifact_state(
        artifact_id,
        status,
        description=headline,
        stage=RESEARCH_STAGE,
        provenance=provenance_class,
    )
    components.render_paragraph(
        {"label": "Why this matters", "body": why_it_matters}
    )


# ---------------------------------------------------------------------------
# 9A fixture
# ---------------------------------------------------------------------------


def _render_fixture_section(
    evidence: RealDataEvidence,
    provenance_rows: list[dict[str, Any]],
    status_index: dict[str, str],
) -> None:
    canonical = evidence.canonical_9a
    if not canonical:
        _render_missing_stream(
            "REAL_9A_CANONICAL",
            status_index.get("REAL_9A_CANONICAL", "MISSING"),
            "The 9A canonical fixture dataset is not available for this snapshot.",
            [
                "Without the canonical fixture, the ingestion boundary cannot be inspected on this page: activity "
                "counts, rejected-record counts, the recorded planned dates and the deterministic dataset "
                "fingerprint would all have to be invented to fill the gap, so they are shown as missing instead.",
                "",
                "This does not affect the PSLIB or SUCCESS streams, which have their own registered artifacts.",
            ],
            provenance_class=_provenance_class_for(provenance_rows, "REAL_9A_CANONICAL"),
        )
        return

    components.render_section_header(
        title="9A ingestion fixture",
        subtitle=(
            "A controlled civil-project CSV bundle that proves the 9A adapter and gate: "
            "explicit column mapping, validated structure, zero rejected records and a "
            "deterministic fingerprint."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology="Recorded fields of the canonical fixture artifact; nothing is derived beyond min/max over the recorded planned dates.",
        provenance="OBS source fixture, ingested through an explicit mapping contract.",
        uncertainty=(
            "The fixture is a boundary demonstration. It is not the user's actual project "
            "data and is not evidence about any real construction site."
        ),
    )

    components.render_status_banner(
        "This fixture proves that the ingestion contract works; it is not a real "
        "construction project dataset and is neither PSLIB nor SUCCESS.",
        status="attention",
        title="Fixture scope",
    )

    components.render_table(
        pd.DataFrame(build_fixture_identity_rows(canonical)),
        title="Fixture identity",
        subtitle="Recorded dataset and project properties, including the SHA-256 fingerprint.",
        research_stage=RESEARCH_STAGE,
        provenance="OBS",
    )

    activity_rows = build_fixture_activity_rows(canonical)
    if activity_rows:
        components.render_table(
            pd.DataFrame(activity_rows),
            title="Activities",
            subtitle="All recorded activities with their recorded planned dates.",
            research_stage=RESEARCH_STAGE,
            provenance="OBS",
        )
        time_range = build_fixture_time_range(canonical)
        if time_range:
            components.render_paragraph(
                {
                    "label": "Recorded planned date range",
                    "body": (
                        f"{time_range} — taken from the earliest recorded planned start and the latest "
                        "recorded planned finish of the fixture activities. These are planned fixture "
                        "dates, not observed history."
                    ),
                }
            )
    else:
        components.render_status_banner(
            "The fixture artifact records no activities, so no schedule table and no date "
            "range can be shown.",
            status="empty",
            title="No activity rows in the fixture",
        )

    components.render_table(
        pd.DataFrame(build_fixture_row_count_rows(canonical)),
        title="Ingestion row accounting",
        subtitle="Source row counts and the recorded rejected-record count from the ingestion audit.",
        research_stage=RESEARCH_STAGE,
        provenance="DER",
    )

    metadata = canonical.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    components.render_inline_label_values(
        [
            _labeled_paragraph(
                "Traceability",
                _humanize(
                    metadata.get("source_traceability")
                    or "Not recorded in the fixture metadata."
                ),
            ),
            _labeled_paragraph(
                "Normalization",
                _humanize(
                    metadata.get("normalization")
                    or "Not recorded in the fixture metadata."
                ),
            ),
        ]
    )


# ---------------------------------------------------------------------------
# PSLIB stream
# ---------------------------------------------------------------------------


def _render_pslib_section(
    evidence: RealDataEvidence,
    provenance_rows: list[dict[str, Any]],
    status_index: dict[str, str],
) -> None:
    pslib = evidence.pslib_audit
    if not pslib:
        _render_missing_stream(
            "REAL_9B_PSLIB_AUDIT",
            status_index.get("REAL_9B_PSLIB_AUDIT", "MISSING"),
            "The PSLIB project audit is not available for this snapshot.",
            [
                "Without the PSLIB audit there is no coverage or data-quality evidence for the empirical project "
                "stream on this page: activity, dependency, risk-profile, control-snapshot and resource counts "
                "would have to be assumed, so the stream is shown as unavailable instead.",
                "",
                "The SUCCESS stream is unaffected and remains sourced from its own audit.",
            ],
            provenance_class=_provenance_class_for(provenance_rows, "REAL_9B_PSLIB_AUDIT"),
        )
        return

    components.render_section_header(
        title="PSLIB empirical project stream",
        subtitle=(
            "Coverage and quality metrics recorded by the 9B audit of the public "
            "PSLIB / DSLIB v3.4 project workbook."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology="Values are read directly from the recorded audit fields; no metric is recomputed.",
        provenance="Provenance class OBS as recorded in the registry.",
        uncertainty=(
            "The audit records structure and counts, not analysis results. Rejected records "
            "are reported as counts only; the audit does not list the rejected rows."
        ),
    )

    components.render_table(
        pd.DataFrame(build_pslib_identity_rows(pslib)),
        title="Workbook identity",
        subtitle="Recorded dataset, project and fingerprint properties.",
        research_stage=RESEARCH_STAGE,
        provenance="OBS",
    )

    components.render_table(
        pd.DataFrame(build_pslib_coverage_rows(pslib)),
        title="Recorded coverage",
        subtitle="Counts the audit recorded for this workbook.",
        research_stage=RESEARCH_STAGE,
        provenance="OBS",
    )

    components.render_inline_label_values(
        [
            _labeled_paragraph(
                "Time range",
                "Not recorded. The registered PSLIB audit carries no schedule dates, so no time "
                "range is reported for this stream rather than inferring one from file names.",
            ),
            _labeled_paragraph(
                "Rejected dependency records",
                _rejected_dependency_note(pslib),
            ),
        ]
    )


def _rejected_dependency_note(pslib_audit: dict[str, Any]) -> str:
    value = pslib_audit.get("rejected_dependency_records")
    if value is None:
        return "Not recorded in the audit."
    return (
        f"{_fmt_int(value)} dependency record(s) were rejected during ingestion and are "
        "recorded here as a count; the registered audit does not include the rejected rows."
    )


# ---------------------------------------------------------------------------
# SUCCESS stream
# ---------------------------------------------------------------------------


def _render_success_section(
    evidence: RealDataEvidence,
    provenance_rows: list[dict[str, Any]],
    status_index: dict[str, str],
) -> None:
    logistics = evidence.logistics_audit
    if not logistics:
        _render_missing_stream(
            "REAL_9B_LOGISTICS_AUDIT",
            status_index.get("REAL_9B_LOGISTICS_AUDIT", "MISSING"),
            "The SUCCESS logistics audit is not available for this snapshot.",
            [
                "Without the logistics audit there is no coverage or data-quality evidence for the SUCCESS stream: "
                "per-table row counts, column counts, invalid-row counts and source fingerprints would have to be "
                "assumed, so the stream is shown as unavailable instead.",
                "",
                "This is exactly why the audit is registered separately from PSLIB — each observed stream must "
                "stand on its own evidence.",
            ],
            provenance_class=_provenance_class_for(provenance_rows, "REAL_9B_LOGISTICS_AUDIT"),
        )
        return

    components.render_section_header(
        title="SUCCESS construction-logistics stream",
        subtitle=(
            "Table-by-table coverage and quality recorded by the 9B logistics audit "
            "for the public construction-logistics CSV bundle."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology="Per-table headers, row counts, invalid-row counts and fingerprints are read from the audit as recorded.",
        provenance="Per-table provenance labels are taken from the audit itself.",
        uncertainty=(
            "The bundle has no common project identifier with PSLIB, so nothing on this "
            "stream is attributed to the PSLIB project workbook."
        ),
    )

    components.render_table(
        pd.DataFrame(build_logistics_source_rows(logistics)),
        title="Bundle identity",
        subtitle="Recorded source format, dataset DOI and audit schema version.",
        research_stage=RESEARCH_STAGE,
        provenance="OBS",
    )

    coverage_rows = build_logistics_coverage_rows(logistics)
    if coverage_rows:
        components.render_table(
            pd.DataFrame(coverage_rows),
            title="Table coverage",
            subtitle=(
                "Every audited table with its recorded row, column and invalid-row "
                "counts; table names are humanized from the recorded file names."
            ),
            source="9B SUCCESS logistics audit",
            research_stage=RESEARCH_STAGE,
            provenance="OBS",
        )
    else:
        components.render_status_banner(
            "The logistics audit records no table entries, so table coverage cannot be shown.",
            status="empty",
            title="No audited tables in the artifact",
        )

    summary_rows = build_logistics_summary_rows(logistics)
    if summary_rows:
        components.render_table(
            pd.DataFrame(summary_rows),
            title="Recorded summary metrics",
            subtitle="Deterministic counts the 9B gate recorded over the observed tables.",
            research_stage=RESEARCH_STAGE,
            provenance="DER",
        )

    top_rows = build_top_materials_rows(logistics)
    if top_rows:
        figure = _top_materials_figure(top_rows)
        if figure is not None:
            components.render_chart(
                figure,
                title="Top materials by recorded demand rows",
                subtitle="As recorded in the audit's derived summary — a count of source rows, not a demand forecast.",
                research_stage=RESEARCH_STAGE,
                provenance="DER",
                evidence_state="AVAILABLE",
            )
    components.render_inline_label_values(
        [
            _labeled_paragraph(
                "Time range",
                "Not recorded. The audit records column names (for example planned start and "
                "end date columns) but no date values, so no time range is reported for this "
                "stream rather than inferring one from file names.",
            ),
            _labeled_paragraph(
                "Provenance of the table rows",
                "Each audited table carries the provenance label recorded by the gate "
                "(OBS — observed in the public source). The summary metrics above are "
                "deterministic counts over those observed rows.",
            ),
        ]
    )


def _top_materials_figure(rows: list[dict[str, Any]]) -> Any:
    """Bar figure of the recorded top-materials list; None when unusable."""
    import plotly.graph_objects as go

    labels: list[str] = []
    values: list[int] = []
    for row in rows:
        try:
            labels.append(str(row["Material"]))
            values.append(int(row["Demand rows"]))
        except (KeyError, TypeError, ValueError):
            continue
    if not labels or not values:
        return None

    palette = theme.CATEGORICAL_PALETTE
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=palette[0 % len(palette)],
        )
    )
    fig.update_layout(
        height=340,
        showlegend=False,
        margin=dict(l=40, r=20, t=30, b=90),
    )
    fig.update_xaxes(title_text="Material (as recorded in the audit)", tickangle=-30)
    fig.update_yaxes(title_text="Demand rows recorded")
    return fig


# ---------------------------------------------------------------------------
# Gate evidence
# ---------------------------------------------------------------------------


def _render_gate_section(
    evidence: RealDataEvidence,
    provenance_rows: list[dict[str, Any]],
    status_index: dict[str, str],
) -> None:
    _render_one_gate(
        title="9A generalization gate",
        subtitle="Checks the 9A gate recorded for the ingestion / generalization boundary.",
        manifest=evidence.generalization_manifest_9a,
        artifact_id="REAL_9A_MANIFEST",
        status=status_index.get("REAL_9A_MANIFEST", "MISSING"),
        provenance_class=_provenance_class_for(provenance_rows, "REAL_9A_MANIFEST"),
        why=[
            "Without the 9A manifest there is no recorded gate outcome for the ingestion boundary: the checks that "
            "protect against silent semantic guessing and dropped records would be unauditable on this page.",
        ],
    )
    _render_one_gate(
        title="9B real-project end-to-end gate",
        subtitle="Checks the 9B gate recorded for the PSLIB and logistics evidence streams.",
        manifest=evidence.experiment_9b,
        artifact_id="REAL_9B_MANIFEST",
        status=status_index.get("REAL_9B_MANIFEST", "MISSING"),
        provenance_class=_provenance_class_for(provenance_rows, "REAL_9B_MANIFEST"),
        why=[
            "Without the 9B manifest there is no recorded gate outcome for the empirical streams: source "
            "fingerprints, table completeness and the recorded integration boundary would be unauditable here.",
        ],
    )


def _render_one_gate(
    *,
    title: str,
    subtitle: str,
    manifest: dict[str, Any],
    artifact_id: str,
    status: str,
    provenance_class: str,
    why: list[str],
) -> None:
    if not manifest:
        _render_missing_stream(
            artifact_id,
            status,
            f"{title} manifest is not available.",
            why,
            provenance_class=provenance_class,
        )
        return

    summary = build_gate_summary(manifest)
    components.render_section_header(
        title=title,
        subtitle=subtitle,
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology="Check names, results and details are rendered as recorded; filesystem-path details are suppressed.",
        provenance="DER — deterministic gate checks.",
        uncertainty="A passing gate certifies the recorded checks only; it is not a claim about outcomes beyond them.",
    )

    components.render_status_banner(
        f"Gate status {summary['status']}: {summary['passed']} of {summary['total']} checks passed.",
        status="valid" if summary["status"] == "PASS" else "attention",
        title=title,
    )

    rows = build_gate_check_rows(manifest)
    if rows:
        components.render_table(
            pd.DataFrame(rows),
            title="Recorded checks",
            subtitle="Humanized check labels; results exactly as the manifest recorded them.",
            research_stage=RESEARCH_STAGE,
            provenance="DER",
        )

    notes = build_gate_notes(manifest)
    if notes:
        components.render_paragraph(
            {"label": "Manifest notes", "body": notes}
        )


# ---------------------------------------------------------------------------
# Provenance, separation and limitations
# ---------------------------------------------------------------------------


def _render_provenance_and_separation(
    provenance_rows: list[dict[str, Any]],
) -> None:
    components.render_section_header(
        title="Provenance classes and stream separation",
        subtitle="How each value on this page is epistemically qualified, and the rules that keep the streams apart.",
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology="Classes come from the registry and the artifacts' own recorded labels; none is assigned by the UI.",
        provenance="OBS / DER / EST / SCN vocabulary as documented by the 9B phase.",
        uncertainty="Unknown or absent classes render as not recorded rather than being guessed.",
    )

    legend_rows = [
        {"Class": code, "Meaning": meaning} for code, meaning in PROVENANCE_LEGEND
    ]
    components.render_table(
        pd.DataFrame(legend_rows),
        title="Provenance legend",
        subtitle="The four documented classes and what each one asserts.",
        research_stage=RESEARCH_STAGE,
    )

    recorded = sorted(
        {
            row["provenance_class"]
            for row in provenance_rows
            if row.get("provenance_class")
        }
    )
    est_scm = [code for code in recorded if code in ("EST", "SCN")]
    components.render_inline_label_values(
        [
            _labeled_paragraph(
                "Classes recorded on this page",
                ", ".join(recorded) if recorded else "None recorded.",
            ),
            _labeled_paragraph(
                "EST and SCN evidence",
                (
                    "Present on this page: " + ", ".join(est_scm) + "."
                    if est_scm
                    else "None. No real-data artifact on this page is classified as estimated (EST) or "
                    "scenario-generated (SCN); those classes appear in the RO1 and RO3 workspaces instead."
                ),
            ),
            _labeled_paragraph(
                "Separation rule",
                "The PSLIB and SUCCESS streams are loaded from separate audits, rendered in separate sections and "
                "never combined into one dataset view. The 9A fixture is a third, separate stream. No cross-dataset "
                "project identity is asserted anywhere on this page.",
            ),
            _labeled_paragraph(
                "Not registered, therefore not shown",
                "The repository also contains unregistered real-data files (the canonical PSLIB project JSON, the "
                "real-project experiment output, and the 9A generalization audit table). They are deliberately not "
                "loaded: only registered, size-capped, schema-checked artifacts are displayed here.",
            ),
        ]
    )


def _render_limitations() -> None:
    components.render_section_header(
        title="Limitations and what is missing",
        subtitle="The boundaries of this evidence, stated plainly.",
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology="Limitations are taken from the 9A and 9B documentation and the recorded artifacts.",
        provenance="See the artifact inventory above.",
        uncertainty="Everything below constrains how far the displayed evidence may be interpreted.",
    )

    components.render_paragraph(
        {
            "label": "What this evidence does not demonstrate",
            "body": [
                "- The 9A fixture is not the user's actual civil-project dataset; it demonstrates the ingestion",
                "  contract only. Missing project semantics must come from the dataset owner, never from the UI.",
                "- PSLIB and SUCCESS are complementary observed streams. They are not one joined project, and no",
                "  cross-dataset project identity is fabricated.",
                "- The gates evidence ingestion and controlled execution. They do not establish external",
                "  generalization, deployment readiness or real-world validation of the RO1–RO3 research claims",
                "  beyond the checks that were actually recorded.",
                "- Time coverage: only the 9A fixture records dates. The registered PSLIB and SUCCESS audits record",
                "  no date values, so no time range is shown for those streams.",
                "- No estimated (EST) or scenario (SCN) real-data quantities are registered here, so none is shown.",
                "- Rejected and invalid records appear as counts only; row-level rejection detail is not part of the",
                "  registered artifacts.",
                "- Filesystem source paths are recorded in provenance but suppressed from this page.",
            ],
        }
    )

    components.render_paragraph(
        {
            "label": "What would strengthen this evidence",
            "body": [
                "- Registering the canonical PSLIB project and the real-project experiment output so execution-level",
                "  detail can be inspected under the same loading and provenance rules.",
                "- Recording documented time coverage for the observed streams so date ranges can be reported",
                "  without inference.",
                "- Replacing the fixture with the dataset owner's actual civil-project data once an explicit",
                "  mapping and unit decisions are provided.",
            ],
        }
    )


def _render_handoff() -> None:
    components.render_section_header(
        title="Where this evidence is used",
        subtitle="How the real-data streams relate to the rest of the dashboard.",
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        provenance="See the artifact inventory above.",
    )
    components.render_paragraph(
        {
            "label": "Handoff",
            "body": [
                "This workspace is read-only evidence about ingestion quality and gate outcomes. It does not feed "
                "the optimizer and does not recompute any research result.",
                "",
                "Per the 9B research boundary, any RO1 → RO2 → RO3 integration of these datasets must either use a "
                "documented mapping between the streams or keep them separate. The Research Evidence page remains "
                "the home for the publication-grade evidence package; this page covers only the observed datasets "
                "behind phases 9A and 9B.",
            ],
        }
    )


# ---------------------------------------------------------------------------
# Page render
# ---------------------------------------------------------------------------


def render_page(
    snapshot: DashboardSnapshot,
    page_route: dict[str, Any] | None = None,
    *,
    include_header: bool = True,
) -> None:
    """Render the Real-World Data workspace.

    Parameters
    ----------
    snapshot: the canonical DashboardSnapshot for this run.
    page_route: optional per-request route context (unused here; accepted for
        signature compatibility with the app dispatch).
    include_header: when True (standalone use) the workspace injects the design
        system CSS and its own page header. The dashboard app shell already
        renders both, so it passes False to avoid duplicating them.
    """
    if include_header:
        inject_and_route(snapshot)

    evidence = snapshot.real_data
    provenance_rows = build_provenance_rows(evidence)

    if not provenance_rows:
        components.render_error_state(
            "No real-data evidence registered",
            description=(
                "The snapshot carries no provenance records for the real-data component, so this "
                "workspace is empty. Nothing is computed or inferred in its place."
            ),
        )
        return

    status_index = artifact_status_index(provenance_rows)

    _render_overview(evidence, provenance_rows)
    _render_artifact_inventory(evidence, provenance_rows, status_index)
    _render_fixture_section(evidence, provenance_rows, status_index)
    _render_pslib_section(evidence, provenance_rows, status_index)
    _render_success_section(evidence, provenance_rows, status_index)
    _render_gate_section(evidence, provenance_rows, status_index)
    _render_provenance_and_separation(provenance_rows)
    _render_limitations()
    _render_handoff()


def inject_and_route(snapshot: DashboardSnapshot) -> None:
    """Inject the design system CSS and the page header for this workspace."""
    components.inject_css()

    page_info = page_by_id(PAGE_ID)
    header = build_page_header(
        title=_page_title(),
        subtitle=_page_subtitle(),
        research_stage=RESEARCH_STAGE,
        evidence_state=page_info.implementation.value,
    )
    components.render_html(header)


def page_description() -> str:
    """Zero-argument public export consumed by page tests."""
    from src.construction.dashboard_ui.navigation import (
        page_description as _nav_page_description,
    )

    return _nav_page_description(PAGE_ID)


def page_future_phase() -> str:
    """Zero-argument public export consumed by page tests."""
    from src.construction.dashboard_ui.navigation import (
        page_future_phase as _nav_page_future_phase,
    )

    return str(_nav_page_future_phase(PAGE_ID) or "")


def page_by_id_local() -> dict[str, Any]:
    return page_by_id(PAGE_ID)


def page_is_planned_local() -> bool:
    return page_is_planned(PAGE_ID)
