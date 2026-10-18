# ---------------------------------------------------------------------------
# CMIDO 10A.13 — Provenance & Integrity workspace
#
# Read-only, registry-driven rendering of artifact provenance, recorded
# fingerprints, recorded integrity checks, documented lineage, loading
# restrictions and known evidence gaps. This module does NOT run research
# computations, does NOT import research engines, does NOT recompute any
# digest, gate, audit or statistical test, and does NOT re-run any recorded
# check. It reads the 10A.2-B snapshot contract and static registry metadata,
# plus one explicitly disclosed metadata-only existence check for files that
# are known to be unregistered (existence only — contents are never read).
#
# Scientific-integrity rules encoded in this module:
#
# * A SHA-256 fingerprint establishes file identity relative to a recorded
#   digest. It is never presented as establishing scientific validity,
#   correct methodology, reproducibility or authenticity.
# * Recorded checks (written by research gates and audits) are kept strictly
#   apart from checks this dashboard performs at load time (presence, size,
#   parse, column contract, policy enforcement). An unperformed check is never
#   represented as passed.
# * File integrity, schema validity, reproducibility, statistical
#   significance and scientific validity are stated as five separate
#   concepts; none is allowed to stand in for another.
# * Provenance classes are shown exactly as the registry recorded them;
#   no class is invented to make the inventory look complete.
# * Unregistered, missing, invalid and partially documented evidence is
#   surfaced explicitly rather than silently omitted. Fingerprints recorded
#   inside a manifest are never mistaken for artifact registration.
# * PSLIB and SUCCESS are separate observed streams; they are rendered in
#   separate tables and never joined.
# * Missing metadata (dates, authorship, software versions, source URLs)
#   renders as undocumented — never as a fabricated value.
# * The recorded RO3 scenario-count convergence failure is reported verbatim
#   through the shared convergence builder; no dashboard change resolves it.
# * Raw filesystem paths, project roots and hex colours never reach the
#   rendered page. Digests are recorded values and are displayed as recorded.
# ---------------------------------------------------------------------------
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.construction.dashboard_data.contract import (
    ArtifactStatus,
    DashboardSnapshot,
)
from src.construction.dashboard_data.registry import (
    ARTIFACT_REGISTRY,
    KNOWN_UNREGISTERED_ARTIFACTS,
    LoadingPolicy,
)
from src.construction.dashboard_data.snapshot import get_default_root
from src.construction.dashboard_ui import components
from src.construction.dashboard_ui import formatting
from src.construction.dashboard_ui.navigation import (
    PageDefinition,
    page_by_id,
    page_is_planned,
)
from src.construction.dashboard_ui.sections import build_page_header

# Presentation helpers shared with the other registry-driven workspaces:
# honest missing values, provenance record reads and audit-path suppression.
from ._procurement_helpers import (
    _fmt_int,
    _is_true,
    _labeled_paragraph,
    _prov_get,
    _status_text,
)
# Recorded convergence is reported by the shared builder so this page states
# the recorded RO3 failure exactly as the Ablation & Robustness workspace does.
from .ablation_robustness import build_ro3_convergence_lines

PAGE_ID = "provenance_integrity"
RESEARCH_STAGE = "EVIDENCE"

_PROVENANCE_CLASSES: tuple[tuple[str, str], ...] = (
    ("OBS", "Observed — recorded directly from a source dataset or file."),
    ("DER", "Derived — deterministic transformation of registered inputs."),
    ("EST", "Estimated — statistical estimate computed from data."),
    ("SCN", "Scenario — generated under controlled scenario assumptions."),
)

_POLICY_LABELS: dict[LoadingPolicy, str] = {
    LoadingPolicy.SAFE: "Safe",
    LoadingPolicy.METADATA_ONLY: "Metadata only",
    LoadingPolicy.HEADER_ONLY: "Header only",
    LoadingPolicy.NEVER: "Blocked (never loaded)",
}

_POLICY_MEANINGS: dict[LoadingPolicy, str] = {
    LoadingPolicy.SAFE: (
        "Content is parsed under a byte-size cap and validated against the "
        "registered schema before any value is displayed."
    ),
    LoadingPolicy.METADATA_ONLY: (
        "Small metadata content is read under the same byte-size cap."
    ),
    LoadingPolicy.HEADER_ONLY: (
        "Only structure and row counts are read; content rows are not used."
    ),
    LoadingPolicy.NEVER: (
        "Refused before any read. The dashboard never opens these files, "
        "never reads them into memory and never relaxes this policy."
    ),
}

#: The five distinct concepts this page refuses to conflate.
_CONCEPTS: tuple[tuple[str, str], ...] = (
    (
        "File integrity",
        "whether a file's bytes still match a recorded digest. Only a digest "
        "comparison establishes this, and this dashboard performs none.",
    ),
    (
        "Schema validity",
        "whether content matches the registered column or key contract. The "
        "dashboard performs this check when it loads an artifact.",
    ),
    (
        "Reproducibility",
        "whether the same result can be regenerated from documented inputs "
        "and steps. Recorded only where a source and generation script are "
        "documented; absent elsewhere.",
    ),
    (
        "Statistical significance",
        "a property of a statistical test recorded by a research artifact. "
        "Reported only where an artifact recorded a test.",
    ),
    (
        "Scientific validity",
        "whether method, data and conclusions are sound. Nothing on this "
        "page establishes it.",
    ),
)

#: Checks the dashboard performs itself, at snapshot build time.
DASHBOARD_CHECKS_PERFORMED: tuple[str, ...] = (
    "File presence — every registered artifact path is checked against the "
    "repository when the snapshot is built.",
    "Size cap — byte size is compared against the artifact's registered "
    "safety limit before any content is read.",
    "Content parse — registered CSV, JSON and text content is parsed under "
    "the artifact's loading policy.",
    "Column contract — expected columns are compared against the parsed "
    "table; a mismatch is recorded as invalid, never silently dropped.",
    "Policy enforcement — artifacts registered as blocked are refused before "
    "any read is attempted.",
    "Existence-only disclosure — for the unregistered files listed below, "
    "this page checks whether the file is present. It reads no content.",
)

#: Checks this dashboard explicitly does NOT perform.
DASHBOARD_CHECKS_NOT_PERFORMED: tuple[str, ...] = (
    "No SHA-256 digest is recomputed. Recorded fingerprints are displayed "
    "as recorded, never re-derived and never compared against current file "
    "bytes.",
    "No recorded gate, audit or reconciliation is redone. Their outcomes "
    "are reported as those artifacts recorded them.",
    "No recorded statistical test is recomputed and no p-value, interval or "
    "effect size is recalculated.",
    "No authorship, collection condition, software version or methodological "
    "claim is independently verified.",
    "No research result is recomputed, rescored or replaced anywhere on this "
    "page.",
)

#: Human labels for the source artifacts fingerprinted by the 8M gate
#: manifest (keyed by the manifest's recorded key, never displayed raw).
_GATE_SOURCE_LABELS: dict[str, str] = {
    "controller_manifest": "Controller freeze manifest (step 36)",
    "controller_audit": "Controller input audit (step 36)",
    "common_manifest": "Common evaluation manifest (step 36)",
    "common_audit": "Common evaluation audit (step 36)",
    "origin": "Origin-level results (step 36)",
    "material": "Material-level results (step 36)",
    "descriptive": "Controller descriptive statistics (step 36)",
    "primary": "Primary ablation results (step 36)",
    "pairwise": "Statistical pairwise comparisons (step 36)",
    "audit": "Statistical analysis audit (step 36)",
}

_UNAVAILABLE = "Not available in this snapshot"


# ---------------------------------------------------------------------------
# Pure presentation builders (no Streamlit, no research engine)
# ---------------------------------------------------------------------------


def label(value: Any) -> str:
    """Display label for a recorded identifier: underscores become spaces.

    This is a display transform only. It never changes a value and never
    derives new meaning from a name. Missing values render as an honest dash.
    """
    if value is None or value == "":
        return formatting.MISSING_DISPLAY
    return str(value).replace("_", " ")


def provenance_code(value: Any) -> str:
    """The OBS/DER/EST/SCN code recorded for a value, or an honest blank."""
    return str(getattr(value, "value", value) or "")


def _digest_text(value: Any) -> str:
    """A recorded digest, displayed as recorded (never recomputed)."""
    text = str(value or "").strip()
    return text if text else formatting.MISSING_DISPLAY


def _bool_text(value: Any) -> str:
    if value is None:
        return formatting.MISSING_DISPLAY
    return "Yes" if _is_true(value) else "No"


def _norm_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


def build_inventory_rows(snapshot: DashboardSnapshot) -> list[dict[str, Any]]:
    """One display row per registered artifact, joined with its provenance.

    Statuses, schema outcomes, row counts and byte sizes are carried through
    exactly as the loader and validator recorded them. An artifact with no
    provenance record reads MISSING — never zero and never inferred.
    """
    index: dict[str, Any] = {}
    for record in snapshot.provenance:
        artifact_id = str(_prov_get(record, "artifact_id", "") or "")
        if artifact_id:
            index[artifact_id] = record

    rows: list[dict[str, Any]] = []
    for entry in ARTIFACT_REGISTRY:
        record = index.get(entry.artifact_id)
        if record is None:
            status = ArtifactStatus.MISSING.value
            schema_status = "NOT RECORDED"
            provenance = label(entry.provenance_class)
            row_count = None
            file_size = None
        else:
            status = _status_text(_prov_get(record, "status"))
            schema_status = label(_prov_get(record, "schema_status", "NOT RECORDED"))
            provenance = provenance_code(_prov_get(record, "provenance_class")) or label(
                entry.provenance_class
            )
            row_count = _prov_get(record, "row_count")
            file_size = _prov_get(record, "file_size_bytes")
        rows.append(
            {
                "Artifact": entry.name,
                "Component": entry.component.value,
                "Provenance": provenance or formatting.MISSING_DISPLAY,
                "Loading policy": _POLICY_LABELS[entry.loading_policy],
                "Status": status,
                "Schema check": schema_status,
                "Rows": _fmt_int(row_count) if row_count is not None else formatting.MISSING_DISPLAY,
                "Size (bytes)": (
                    formatting.format_integer(file_size)
                    if file_size is not None
                    else formatting.MISSING_DISPLAY
                ),
            }
        )
    return rows


def build_class_counts(snapshot: DashboardSnapshot) -> dict[str, int]:
    """Count of provenance records per recorded class (OBS/DER/EST/SCN)."""
    counts = {code: 0 for code, _ in _PROVENANCE_CLASSES}
    for record in snapshot.provenance:
        code = provenance_code(_prov_get(record, "provenance_class"))
        if code in counts:
            counts[code] += 1
    return counts


def build_status_counts(snapshot: DashboardSnapshot) -> dict[str, int]:
    """Count of provenance records per recorded load status."""
    counts: dict[str, int] = {}
    for record in snapshot.provenance:
        status = _status_text(_prov_get(record, "status"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def build_gate_fingerprint_rows(snapshot: DashboardSnapshot) -> list[dict[str, Any]]:
    """Source fingerprints recorded inside the 8M gate manifest.

    Registration is computed by comparing the recorded source path against
    the live registry — a fingerprint inside a manifest is never treated as
    registration. Recorded paths are used only for that comparison and are
    never displayed.
    """
    manifest = snapshot.ro3.ablation_gate_manifest or {}
    sources = manifest.get("source_artifacts") or {}
    if not isinstance(sources, dict) or not sources:
        return []
    registry_paths = {_norm_path(entry.relative_path) for entry in ARTIFACT_REGISTRY}
    rows: list[dict[str, Any]] = []
    for key, record in sources.items():
        if not isinstance(record, dict):
            continue
        recorded_path = _norm_path(record.get("path"))
        registered = bool(recorded_path) and recorded_path in registry_paths
        rows.append(
            {
                "Source artifact": _GATE_SOURCE_LABELS.get(str(key), label(key)),
                "Recorded digest": _digest_text(record.get("sha256")),
                "Registered": "Yes" if registered else "No",
            }
        )
    return rows


def build_source_fingerprint_rows(snapshot: DashboardSnapshot) -> list[dict[str, Any]]:
    """Observed-source and ingestion fingerprints recorded by the 9A/9B audits."""
    pslib = snapshot.real_data.pslib_audit or {}
    ingestion = snapshot.real_data.ingestion_audit_9a or {}
    rows = [
        {
            "Recorded digest": _digest_text(pslib.get("source_sha256")),
            "What it covers": "PSLIB source workbook, as recorded by the 9B audit",
            "Recorded by": "9B PSLIB audit",
        },
        {
            "Recorded digest": _digest_text(pslib.get("canonical_fingerprint_sha256")),
            "What it covers": "Canonicalised PSLIB project, as recorded by the 9B audit",
            "Recorded by": "9B PSLIB audit",
        },
        {
            "Recorded digest": _digest_text(ingestion.get("fingerprint_sha256")),
            "What it covers": "9A civil-project fixture bundle at ingestion",
            "Recorded by": "9A ingestion audit",
        },
    ]
    return rows


def build_success_fingerprint_rows(snapshot: DashboardSnapshot) -> list[dict[str, Any]]:
    """Per-table source fingerprints recorded by the SUCCESS logistics audit."""
    logistics = snapshot.real_data.logistics_audit or {}
    tables = logistics.get("tables") or {}
    if not isinstance(tables, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key, record in tables.items():
        if not isinstance(record, dict):
            continue
        rows.append(
            {
                "SUCCESS table": label(record.get("file") or key),
                "Recorded digest": _digest_text(record.get("sha256")),
                "Rows recorded": (
                    _fmt_int(record.get("row_count"))
                    if record.get("row_count") is not None
                    else formatting.MISSING_DISPLAY
                ),
            }
        )
    return rows


def build_lineage_rows(snapshot: DashboardSnapshot) -> list[dict[str, Any]]:
    """Documented lineage of the publication tables (8Q) and ingestion steps.

    A row is shown only where the manifest records a source and a generation
    script. Digests and script names are recorded values; the script's
    filesystem path is never displayed.
    """
    manifest = snapshot.evidence.publication_manifest or {}
    artifacts = manifest.get("artifacts") or []
    if not isinstance(artifacts, list):
        return []
    rows: list[dict[str, Any]] = []
    for record in artifacts:
        if not isinstance(record, dict):
            continue
        script = str(record.get("generation_script") or "")
        script_name = script.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        rows.append(
            {
                "Publication table": label(record.get("artifact")),
                "Source artifact": label(record.get("source_name")),
                "Source digest": _digest_text(record.get("source_sha256")),
                "Generation script": (
                    label(script_name.removesuffix(".py")) if script_name else formatting.MISSING_DISPLAY
                ),
            }
        )
    return rows


def _counts_outcome(manifest: dict[str, Any]) -> str:
    """Recorded outcome from a manifest's own checks-passed / checks-total."""
    if not manifest:
        return _UNAVAILABLE
    total = manifest.get("checks_total")
    passed = manifest.get("checks_passed")
    if total is None or passed is None:
        return f"Status recorded as {label(manifest.get('status'))}."
    return (
        f"{_fmt_int(passed)} of {_fmt_int(total)} checks recorded as passed "
        f"(status {label(manifest.get('status'))})."
    )


def _rows_outcome(rows: Any) -> str:
    """Recorded outcome from an audit's own check rows.

    Adapters wrap CSV audit rows in an ``audit_rows`` dict; a bare list of
    records is accepted too. Anything else reads as unavailable.
    """
    if isinstance(rows, dict):
        rows = rows.get("audit_rows") or []
    if not rows:
        return _UNAVAILABLE
    total = len(rows)
    passed = sum(1 for row in rows if _is_true(_prov_get(row, "passed")))
    return f"{_fmt_int(passed)} of {_fmt_int(total)} checks recorded as passed."


def build_recorded_check_rows(snapshot: DashboardSnapshot) -> list[dict[str, Any]]:
    """Integrity outcomes REPORTED from recorded artifacts — never re-run.

    Every outcome string is derived from values the artifacts themselves
    recorded. Missing artifacts render as unavailable, never as passed.
    """
    real_data = snapshot.real_data
    evidence = snapshot.evidence
    ro1 = snapshot.ro1
    ro2 = snapshot.ro2
    ro3 = snapshot.ro3

    propagation = ro2.propagation_audit or {}
    final_audit = ro2.final_audit or {}
    ro1_audit = ro1.integrity_audit or {}

    rows = [
        {
            "Check source": "8M ablation evidence gate",
            "Recorded outcome": _counts_outcome(ro3.ablation_gate_manifest or {}),
            "What the artifact records": (
                "Controllers, locked origins, common materials, inferential "
                "unit and per-check gate results for the ablation inputs."
            ),
        },
        {
            "Check source": "RO3 final experimental integrity audit (step 39)",
            "Recorded outcome": _rows_outcome(ro3.final_audit or {}),
            "What the artifact records": (
                "Experimental integrity checks recorded after the RO3 "
                "ablation and comparison runs."
            ),
        },
        {
            "Check source": "8S numerical reconciliation audit",
            "Recorded outcome": _rows_outcome(evidence.reconciliation_audit or []),
            "What the artifact records": (
                "Cross-stage numerical reconciliation between pipeline "
                "stages, recorded check by check."
            ),
        },
        {
            "Check source": "9A real-data generalization gate",
            "Recorded outcome": _counts_outcome(real_data.generalization_manifest_9a or {}),
            "What the artifact records": (
                "Ingestion-contract gate outcome for the 9A fixture bundle."
            ),
        },
        {
            "Check source": "9B real-project end-to-end gate",
            "Recorded outcome": _counts_outcome(real_data.experiment_9b or {}),
            "What the artifact records": (
                "Source-existence, ingestion, fingerprint and execution checks "
                "recorded for the two separate observed streams."
            ),
        },
        {
            "Check source": "8Q publication artifact gate",
            "Recorded outcome": _counts_outcome(evidence.publication_manifest or {}),
            "What the artifact records": (
                "Publication-table gate outcome with recorded sources and "
                "generation scripts."
            ),
        },
        {
            "Check source": "8R figure concordance",
            "Recorded outcome": _counts_outcome(evidence.figure_concordance or {}),
            "What the artifact records": (
                "Figure-to-table concordance mapping recorded for the "
                "publication package."
            ),
        },
        {
            "Check source": "RO1 final integrity audit",
            "Recorded outcome": (
                f"Status recorded as {label(ro1_audit.get('status'))}."
                if ro1_audit
                else _UNAVAILABLE
            ),
            "What the artifact records": (
                "Forecasting integrity gate recorded by the RO1 engine "
                "before the final probabilistic comparison."
            ),
        },
        {
            "Check source": "RO2 final audit",
            "Recorded outcome": (
                f"All audit checks recorded as passed: "
                f"{_bool_text(final_audit.get('all_audit_checks_pass'))}; "
                f"decision recorded as {label(final_audit.get('decision'))}."
                if final_audit
                else _UNAVAILABLE
            ),
            "What the artifact records": (
                "Audit-lock decision recorded by the RO2 engine across its "
                "distribution, propagation and convergence stages."
            ),
        },
        {
            "Check source": "RO2 propagation audit (27D.1)",
            "Recorded outcome": (
                f"Decision recorded as {label(propagation.get('decision'))}; "
                f"structural checks recorded as "
                f"{_bool_text(propagation.get('structural_checks_pass'))}; "
                f"distribution checks recorded as "
                f"{_bool_text(propagation.get('distribution_checks_pass'))}."
                if propagation
                else _UNAVAILABLE
            ),
            "What the artifact records": (
                "Structural, distribution and service-risk audit outcome "
                "gating the joint-propagation claim."
            ),
        },
    ]
    return rows


def build_loading_policy_rows() -> list[dict[str, Any]]:
    """Registered artifact counts per loading policy, with each policy's rule."""
    rows: list[dict[str, Any]] = []
    for policy in LoadingPolicy:
        count = sum(1 for entry in ARTIFACT_REGISTRY if entry.loading_policy == policy)
        rows.append(
            {
                "Policy": _POLICY_LABELS[policy],
                "Rule": _POLICY_MEANINGS[policy],
                "Registered artifacts": formatting.format_integer(count),
            }
        )
    return rows


def build_unregistered_rows(root: Path | None) -> list[dict[str, Any]]:
    """Known-unregistered files: presence (metadata only) and registration state.

    Presence is a filesystem existence check performed by this page — it is
    disclosed as such in the UI. Contents are never read. Registration is
    computed by comparing the known path (held in the registry module, never
    displayed) against the live registry.
    """
    registry_paths = {_norm_path(entry.relative_path) for entry in ARTIFACT_REGISTRY}
    rows: list[dict[str, Any]] = []
    for spec in KNOWN_UNREGISTERED_ARTIFACTS:
        rel = spec.relative_path
        present = False
        if root is not None:
            try:
                present = (root / rel).is_file()
            except OSError:
                present = False
        registered = _norm_path(rel) in registry_paths
        rows.append(
            {
                "Artifact": spec.artifact,
                "Documented by": spec.documented_by,
                "Present in repository": "Yes" if present else "No",
                "Registered": "Yes" if registered else "No",
            }
        )
    return rows


def build_provenance_legend_rows() -> list[dict[str, Any]]:
    """The four recorded provenance classes and what each means."""
    return [
        {"Class": code, "Meaning": meaning} for code, meaning in _PROVENANCE_CLASSES
    ]


def build_concept_rows() -> list[dict[str, Any]]:
    """The five distinct concepts this page keeps apart."""
    return [{"Concept": name, "What it means here": meaning} for name, meaning in _CONCEPTS]


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _evidence_state(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "empty"
    available = sum(1 for row in rows if row["Status"] == ArtifactStatus.AVAILABLE.value)
    if available == len(rows):
        return "available"
    return "partial" if available else "empty"


def _render_overview(snapshot: DashboardSnapshot, inventory: list[dict[str, Any]]) -> None:
    """Top-level framing: what the page reports and how to read its vocabulary."""
    overview = snapshot.overview
    blocked = sum(
        1 for entry in ARTIFACT_REGISTRY if entry.loading_policy == LoadingPolicy.NEVER
    )
    components.render_section_header(
        title="Provenance and integrity evidence",
        subtitle=(
            "What every registered artifact is, which recorded fingerprints "
            "and integrity checks support it, and which gaps remain."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state=_evidence_state(inventory),
        methodology=(
            "Registry-driven (10A.2-B). Rows come from provenance records the "
            "loader and validator produced, from metadata recorded inside "
            "registered artifacts, and from one disclosed existence-only "
            "check for known-unregistered files. Nothing is recomputed."
        ),
        provenance="See the artifact inventory, recorded fingerprints and recorded checks below.",
        uncertainty=(
            "A recorded check, a fingerprint and a scientific claim are three "
            "different things; this page reports each separately."
        ),
    )

    components.render_kpi_columns(
        [
            {
                "label": "Registered artifacts",
                "value": formatting.format_integer(overview.total_artifacts_registered),
                "evidence_state": "valid",
                "description": "Entries in the 10A.2-B artifact registry.",
            },
            {
                "label": "Available",
                "value": formatting.format_integer(overview.total_artifacts_available),
                "evidence_state": "valid",
                "description": "Present, parsed and schema-validated at load time.",
            },
            {
                "label": "Missing or invalid",
                "value": formatting.format_integer(
                    overview.total_artifacts_missing + overview.total_artifacts_invalid
                ),
                "evidence_state": (
                    "missing"
                    if (overview.total_artifacts_missing + overview.total_artifacts_invalid)
                    else "valid"
                ),
                "description": "Recorded by the loader as missing or failing its schema contract.",
            },
            {
                "label": "Blocked from loading",
                "value": formatting.format_integer(blocked),
                "evidence_state": "valid",
                "description": "Raw scenario ledgers refused by policy before any read.",
            },
        ]
    )

    components.render_paragraph(
        {
            "label": "What this page answers",
            "body": [
                "- Which evidence artifacts exist and which of them are registered in the",
                "  dashboard contract, with recorded status and schema outcomes.",
                "- Which provenance class each artifact carries — observed, derived,",
                "  estimated or scenario — exactly as the registry recorded it.",
                "- Which SHA-256 fingerprints and integrity checks are recorded, and what",
                "  each of them does and does not establish.",
                "- Which lineage is documented, which metadata is missing, and which files",
                "  are unregistered or otherwise unverifiable through this dashboard.",
                "- Which loading restrictions protect the dashboard from unsafe or",
                "  excessively large inputs.",
            ],
        }
    )

    components.render_paragraph(
        _labeled_paragraph(
            "Provenance classes, as recorded",
            [f"- {code} — {meaning}" for code, meaning in _PROVENANCE_CLASSES]
            + [
                "Classes are read from registry records only. No class is assigned here,",
                "and no artifact is reclassified to make the inventory look complete.",
            ],
        )
    )

    components.render_paragraph(
        _labeled_paragraph(
            "Five different concepts, kept apart",
            [
                f"- {name}: {meaning}"
                for name, meaning in _CONCEPTS
            ],
        )
    )


def _render_inventory(snapshot: DashboardSnapshot, inventory: list[dict[str, Any]]) -> None:
    """Full registered-artifact inventory plus explicit states for anything absent."""
    components.render_section_header(
        title="Registered artifact inventory",
        subtitle=(
            "Every registry entry with its recorded provenance class, loading "
            "policy, load status and schema outcome."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state=_evidence_state(inventory),
        methodology=(
            "One row per registry entry, joined to the provenance record the "
            "loader produced. An artifact without a record reads MISSING."
        ),
        provenance="Provenance records produced at snapshot build time.",
        uncertainty=(
            "Schema vocabulary as recorded: LOADED means content was parsed, "
            "PASSED means the expected columns were present, and any other "
            "value is reproduced from the loader's own record."
        ),
    )

    components.render_table(
        pd.DataFrame(inventory),
        title="Registered artifacts and their recorded outcomes",
        source="10A.2-B artifact registry and provenance records",
        research_stage=RESEARCH_STAGE,
        empty_message="No registered artifacts were recorded for this snapshot.",
    )

    status_index = {
        str(_prov_get(record, "artifact_id", "") or ""): _status_text(
            _prov_get(record, "status")
        )
        for record in snapshot.provenance
    }
    for entry in ARTIFACT_REGISTRY:
        status = status_index.get(entry.artifact_id, ArtifactStatus.MISSING.value)
        if status != ArtifactStatus.AVAILABLE.value:
            components.render_artifact_state(
                entry.artifact_id,
                status,
                description=entry.description,
                stage=RESEARCH_STAGE,
                provenance=entry.provenance_class,
            )

    counts = build_status_counts(snapshot)
    summary = ", ".join(
        f"{label(status)} {formatting.format_integer(count)}"
        for status, count in sorted(counts.items())
    ) or "No provenance records."
    components.render_paragraph(
        _labeled_paragraph("Recorded status summary", summary)
    )


def _render_fingerprints(snapshot: DashboardSnapshot) -> None:
    """Recorded fingerprints: what exists, what covers what, what it establishes."""
    components.render_section_header(
        title="Recorded fingerprints",
        subtitle=(
            "SHA-256 digests recorded inside registered artifacts, shown as "
            "recorded — never recomputed here."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology=(
            "Digests are read from the 8M gate manifest and the 9A and 9B "
            "audit artifacts. This page performs no hashing of its own."
        ),
        provenance="Digest values as recorded by the named artifacts.",
        uncertainty=(
            "A digest identifies file bytes relative to the recorded value; "
            "it says nothing about method or result quality."
        ),
    )

    components.render_paragraph(
        {
            "label": "What a fingerprint establishes, and what it does not",
            "body": [
                "- A recorded SHA-256 fingerprint establishes file identity relative to the",
                "  digest that was recorded at the time it was written.",
                "- It does not independently establish scientific validity, correct",
                "  methodology, reproducibility or authenticity, and it is not evidence",
                "  that the file's current bytes still match — this dashboard never",
                "  recomputes a digest to check.",
                "- A fingerprint recorded inside a manifest is also not registration: it",
                "  records that a source file was digested, not that the dashboard may",
                "  load or display it.",
                "- Recorded source paths behind these digests are suppressed; only the",
                "  digest and its coverage are shown.",
            ],
        }
    )

    source_rows = build_source_fingerprint_rows(snapshot)
    components.render_table(
        pd.DataFrame(source_rows),
        title="Observed-source and ingestion fingerprints",
        subtitle="PSLIB and 9A fixture digests, recorded by their own audits.",
        source="9B PSLIB audit and 9A ingestion audit",
        research_stage=RESEARCH_STAGE,
        empty_message="No source fingerprints are recorded in this snapshot.",
    )

    success_rows = build_success_fingerprint_rows(snapshot)
    components.render_table(
        pd.DataFrame(success_rows),
        title="SUCCESS table fingerprints",
        subtitle=(
            "Per-table digests recorded by the SUCCESS logistics audit. This "
            "stream is presented separately from PSLIB and is never joined "
            "with it."
        ),
        source="9B SUCCESS logistics audit",
        research_stage=RESEARCH_STAGE,
        empty_message="No SUCCESS table fingerprints are recorded in this snapshot.",
    )

    gate_rows = build_gate_fingerprint_rows(snapshot)
    components.render_table(
        pd.DataFrame(gate_rows),
        title="8M gate source fingerprints",
        subtitle=(
            "Sources digested by the ablation evidence gate, with their live "
            "registration state computed against the registry."
        ),
        source="8M ablation evidence gate manifest",
        research_stage=RESEARCH_STAGE,
        empty_message="The 8M gate manifest recorded no source fingerprints in this snapshot.",
    )

    if not gate_rows:
        components.render_paragraph(
            _labeled_paragraph(
                "Fingerprint coverage",
                "The registered 8M gate manifest recorded no source "
                "fingerprints in this snapshot, so no source fingerprint "
                "claim is made for the ablation inputs.",
            )
        )


def _render_recorded_checks(snapshot: DashboardSnapshot) -> None:
    """Integrity outcomes reported from recorded artifacts, as recorded."""
    components.render_section_header(
        title="Recorded integrity checks",
        subtitle=(
            "Outcomes written by research gates and audits, reported exactly "
            "as those artifacts recorded them."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology=(
            "Each row reads recorded counters or recorded status values from "
            "a registered artifact. The dashboard does not re-run any of "
            "these checks."
        ),
        provenance="See the artifact inventory for the provenance class of each source.",
        uncertainty=(
            "A recorded pass reflects the rules that artifact encoded at the "
            "time; it is not re-verified here and it is not a statement of "
            "scientific validity."
        ),
    )

    rows = build_recorded_check_rows(snapshot)
    components.render_table(
        pd.DataFrame(rows),
        title="Integrity outcomes, as recorded",
        source="Registered gate manifests and audit artifacts",
        research_stage=RESEARCH_STAGE,
        empty_message="No recorded integrity checks are available in this snapshot.",
    )

    components.render_paragraph(
        _labeled_paragraph(
            "Reported, not redone,",
            [
                "Every figure above was written by the artifact named in its row. This",
                "page copies those recorded outcomes; it does not re-execute a gate,",
                "re-verify a check or promote an unperformed check to passed.",
                "Artifacts that are missing or invalid in this snapshot would appear as",
                "unavailable above — never as zero and never as a pass.",
            ],
        )
    )


def _render_performed_checks() -> None:
    """Checks this dashboard performs itself, kept apart from recorded checks."""
    components.render_section_header(
        title="Checks performed by this dashboard",
        subtitle=(
            "What the loading pipeline actually verifies itself, and what it "
            "deliberately does not."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology=(
            "These checks run at snapshot build time over registered "
            "artifacts only. They are separate from the recorded checks "
            "reported above."
        ),
        provenance="Produced by the loader, validator and registry policy at load time.",
        uncertainty=(
            "Passing these checks means the file was present, small enough, "
            "parseable and schema-conformant — nothing more."
        ),
    )

    components.render_paragraph(
        _labeled_paragraph(
            "Performed at load time",
            [f"- {item}" for item in DASHBOARD_CHECKS_PERFORMED],
        )
    )
    components.render_paragraph(
        _labeled_paragraph(
            "Not performed by this dashboard",
            [f"- {item}" for item in DASHBOARD_CHECKS_NOT_PERFORMED],
        )
    )


def _render_loading_policy(snapshot: DashboardSnapshot) -> None:
    """Loading restrictions, including the ledgers that are never read."""
    components.render_section_header(
        title="Loading policy and size restrictions",
        subtitle=(
            "Which artifacts the dashboard may read, under which limits, and "
            "which files it refuses before any read."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology=(
            "Policy is static registry metadata; the blocked states below "
            "come from the loader's recorded refusal."
        ),
        provenance="Registry loading policies and loader provenance records.",
        uncertainty=(
            "Refusal is a safety property, not an evidence outcome: a blocked "
            "file is not missing evidence, it is evidence deliberately not "
            "read at interface scale."
        ),
    )

    components.render_table(
        pd.DataFrame(build_loading_policy_rows()),
        title="Loading policies in force",
        source="10A.2-B artifact registry",
        research_stage=RESEARCH_STAGE,
        empty_message="No loading policies are registered.",
    )

    blocked_entries = [
        entry for entry in ARTIFACT_REGISTRY if entry.loading_policy == LoadingPolicy.NEVER
    ]
    status_index = {
        str(_prov_get(record, "artifact_id", "") or ""): _status_text(
            _prov_get(record, "status")
        )
        for record in snapshot.provenance
    }
    for entry in blocked_entries:
        components.render_artifact_state(
            entry.artifact_id,
            status_index.get(entry.artifact_id, ArtifactStatus.TOO_LARGE.value),
            description=entry.description,
            stage=RESEARCH_STAGE,
            provenance=entry.provenance_class,
        )

    components.render_paragraph(
        {
            "label": "How the block is enforced",
            "body": [
                "- Raw experiment-scale scenario ledgers are registered with the blocked",
                "  policy: the loader refuses them before opening the file, so their bytes",
                "  are never read into memory and their rows are never displayed.",
                "- The size cap is applied to every other artifact before content is read; a",
                "  file above its cap is recorded as too large rather than loaded.",
                "- No page, including this one, may weaken a policy to populate a panel.",
                "  A blocked artifact appears above as blocked, not as missing evidence.",
            ],
        }
    )


def _render_lineage(snapshot: DashboardSnapshot) -> None:
    """Documented lineage next to what remains undocumented."""
    components.render_section_header(
        title="Documented lineage",
        subtitle=(
            "Where a source and a documented transformation are recorded, and "
            "where the chain stops."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology=(
            "Lineage rows are read from the 8Q publication manifest and the "
            "9A and 9B schema-version fields. No transformation is replayed."
        ),
        provenance="Recorded sources, digests and generation-script names.",
        uncertainty=(
            "Full lineage is claimed only where the artifacts record both a "
            "source and a documented step; everywhere else the page says so."
        ),
    )

    lineage_rows = build_lineage_rows(snapshot)
    components.render_table(
        pd.DataFrame(lineage_rows),
        title="Publication table lineage (recorded by the 8Q manifest)",
        subtitle=(
            "Each publication table with its recorded source artifact, source "
            "digest and generation script. Script paths are not displayed."
        ),
        source="8Q publication artifact manifest",
        research_stage=RESEARCH_STAGE,
        empty_message="The publication manifest recorded no lineage rows in this snapshot.",
    )

    ingestion = snapshot.real_data.ingestion_audit_9a or {}
    canonical = snapshot.real_data.canonical_9a or {}
    pslib = snapshot.real_data.pslib_audit or {}
    logistics = snapshot.real_data.logistics_audit or {}
    version_rows = [
        {
            "Documented step": "9A fixture ingestion",
            "Recorded version": label(
                ingestion.get("ingestion_schema_version")
                or canonical.get("schema_version")
            ),
            "Recorded by": "9A ingestion audit",
        },
        {
            "Documented step": "Canonical schema applied to the 9A fixture",
            "Recorded version": label(
                ingestion.get("canonical_schema_version")
                or canonical.get("schema_version")
            ),
            "Recorded by": "9A ingestion audit",
        },
        {
            "Documented step": "PSLIB project audit schema",
            "Recorded version": label(pslib.get("schema_version")),
            "Recorded by": "9B PSLIB audit",
        },
        {
            "Documented step": "SUCCESS logistics audit schema",
            "Recorded version": label(logistics.get("schema_version")),
            "Recorded by": "9B SUCCESS logistics audit",
        },
        {
            "Documented step": "SUCCESS dataset citation",
            "Recorded version": label(logistics.get("dataset_doi")),
            "Recorded by": "9B SUCCESS logistics audit",
        },
    ]
    components.render_table(
        pd.DataFrame(version_rows),
        title="Recorded schema versions and citations",
        source="9A and 9B audit artifacts",
        research_stage=RESEARCH_STAGE,
        empty_message="No schema-version metadata is recorded in this snapshot.",
    )

    components.render_paragraph(
        {
            "label": "Where the documented chain stops",
            "body": [
                "- Publication tables record a source artifact, a source digest and a",
                "  generation script — documented lineage for those tables only.",
                "- The step-36 execution-level sources are digested by the 8M gate manifest,",
                "  but those files are unregistered, so their contents and execution",
                "  context cannot be inspected through this dashboard.",
                "- No registered artifact records software versions, environment capture,",
                "  authorship or creation timestamps. Those fields are undocumented and",
                "  are shown as unavailable — never filled in.",
                "- Where a transformation chain is not recorded, this page claims no",
                "  lineage for it.",
            ],
        }
    )


def _render_gaps(snapshot: DashboardSnapshot, root: Path | None) -> None:
    """Unregistered files, missing metadata, separation rules and recorded limits."""
    components.render_section_header(
        title="Known evidence gaps",
        subtitle=(
            "Unregistered files, missing metadata and recorded limitations — "
            "surfaced rather than omitted."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="partial",
        methodology=(
            "Unregistered-file presence is an existence-only check performed "
            "by this page (no content is read); registration is computed "
            "against the live registry. Everything else is reported from "
            "recorded artifacts or recorded documentation."
        ),
        provenance="See the inventory and fingerprint tables above.",
        uncertainty=(
            "Each item below constrains what this dashboard can substantiate; "
            "none of them is resolved by this page."
        ),
    )

    unregistered_rows = build_unregistered_rows(root)
    components.render_table(
        pd.DataFrame(unregistered_rows),
        title="Present in the repository but not registered",
        subtitle=(
            "Files that exist on disk yet carry no registry entry, so no "
            "provenance record, schema check or size cap applies to them "
            "here."
        ),
        source="Registry comparison and existence-only check performed by this page",
        research_stage=RESEARCH_STAGE,
        empty_message="No known-unregistered files are listed for this snapshot.",
    )

    components.render_paragraph(
        {
            "label": "What this table does and does not show",
            "body": [
                "- Presence was verified by an existence check performed by this page; the",
                "  contents of these files were not opened, parsed or displayed.",
                "- Registration was computed against the current registry, not assumed from",
                "  documentation: a recorded fingerprint or a prior-phase inventory entry",
                "  does not register a file.",
                "- The Phase 10A.10 decision-level inventory names five decision-level",
                "  artifacts as registered; the current registry contains no entry for",
                "  them, so a live snapshot carries no provenance record for that content.",
                "- The 9A repository inventory and 9A audit table, the canonical PSLIB",
                "  project and the 9B experiment output remain outside the contract, as",
                "  recorded by the Phase 10A.11 documentation.",
            ],
        }
    )

    components.render_paragraph(
        _labeled_paragraph(
            "Missing metadata, preserved as missing",
            [
                "- The PSLIB and SUCCESS audits record no collection or creation dates, so no",
                "  date is shown for either stream — the field reads undocumented.",
                "- No registered artifact records authorship, software versions, source URLs",
                "  or experimental conditions for the digests above.",
                "- Schema versions and dataset citations appear only where an audit",
                "  recorded them (see the recorded versions table).",
                "- Nothing in this section is inferred, estimated or back-filled to make the",
                "  provenance record look complete.",
            ],
        )
    )

    components.render_paragraph(
        _labeled_paragraph(
            "Separation and recorded limits",
            [
                "- PSLIB and SUCCESS remain separate observed streams: they are digested by",
                "  separate audits, rendered in separate tables and never joined. This page",
                "  asserts no cross-dataset relationship.",
                "- Observed travel times are never read as supplier-specific procurement",
                "  lead times anywhere in this evidence.",
                "- The recorded RO3 scenario-count convergence result below is reproduced as",
                "  recorded; no dashboard change resolves this research-side issue.",
            ],
        )
    )

    components.render_paragraph(
        _labeled_paragraph(
            "Recorded RO3 convergence (reported as recorded)",
            build_ro3_convergence_lines(snapshot.ro3.convergence_summary or {}),
        )
    )


def _render_interpretation() -> None:
    """How to read everything above, without overclaiming."""
    components.render_section_header(
        title="How to read this evidence",
        subtitle="The rules that keep recorded facts, dashboard checks and claims apart.",
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology="Interpretation only; no artifact is read or recomputed in this section.",
        provenance="Rules stated by this page's design, consistent with the recorded artifacts.",
        uncertainty="Everything above constrains how far any provenance statement may be taken.",
    )

    components.render_paragraph(
        {
            "label": "Reading rules",
            "body": [
                "- Recorded checks were written by research gates; dashboard checks were",
                "  performed by the loading pipeline. The two are never merged into one",
                "  notion of passed.",
                "- A fingerprint is file identity relative to a recorded digest. It is not",
                "  validity, not reproducibility and not authenticity, and this page never",
                "  presents it as such.",
                "- Schema validity means the column contract held. It says nothing about",
                "  whether the numbers are scientifically meaningful.",
                "- Missing, invalid, unregistered and undocumented states are shown as",
                "  exactly those states. No unavailable value becomes zero, and no",
                "  unperformed check is shown as passed.",
                "- Provenance classes describe origin of evidence, not quality: a scenario",
                "  result is not weakened or upgraded by being labelled, and an observed",
                "  record is not promoted by having a digest.",
                "- The recorded convergence failure, the descriptive-only stress and",
                "  holding-rate evidence, and the unregistered files above all continue to",
                "  constrain interpretation exactly as their source phases recorded.",
            ],
        }
    )


def _render_handoff() -> None:
    """What remains open after this page — honestly scoped."""
    components.render_section_header(
        title="Handoff and open items",
        subtitle="What this page cannot settle, and where the remaining work lives.",
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
        methodology="Scope statement for this presentation-only workspace.",
        provenance="Consistent with the limitations recorded across the source phases.",
        uncertainty="No item below is resolved by rendering it.",
    )

    components.render_paragraph(
        {
            "label": "Open items",
            "body": [
                "- Research side: the recorded RO3 scenario-count convergence failure and its",
                "  recorded decision remain open research work; surfacing them here does not",
                "  resolve them.",
                "- Registration side: the unregistered files above stay outside the dashboard",
                "  contract until a phase with an evidence audit decides otherwise. This",
                "  page reports the gap and does not register anything itself.",
                "- Documentation side: lineage beyond the recorded sources, scripts and",
                "  schema versions is undocumented; closing that gap requires research-side",
                "  documentation, not interface work.",
                "- Verification side: digest re-verification against current file bytes is",
                "  not performed anywhere in the dashboard and would need an explicit,",
                "  audited tool — never an implicit UI action.",
            ],
        }
    )


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def render_page(
    snapshot: DashboardSnapshot,
    page_route: dict[str, Any] | None = None,
    *,
    include_header: bool = True,
    root: Path | None = None,
) -> None:
    """Render the Provenance & Integrity workspace.

    Parameters
    ----------
    snapshot: the canonical DashboardSnapshot for this run.
    page_route: optional per-request route context (unused here; accepted for
        signature compatibility with the app dispatch).
    include_header: when True (standalone use) the workspace injects the design
        system CSS and its own page header. The dashboard app shell already
        renders both, so it passes False to avoid duplicating them.
    root: repository root used only for the disclosed existence-only check of
        known-unregistered files. Defaults to the snapshot's root resolver.
    """
    if include_header:
        inject_and_route(snapshot)

    if not snapshot.provenance:
        components.render_error_state(
            "No provenance records in this snapshot",
            description=(
                "The snapshot carries no artifact provenance records, so no "
                "provenance or integrity evidence can be shown. Nothing is "
                "computed or inferred in its place."
            ),
        )
        return

    if root is None:
        root = get_default_root()

    inventory = build_inventory_rows(snapshot)

    _render_overview(snapshot, inventory)
    _render_inventory(snapshot, inventory)
    _render_fingerprints(snapshot)
    _render_recorded_checks(snapshot)
    _render_performed_checks()
    _render_loading_policy(snapshot)
    _render_lineage(snapshot)
    _render_gaps(snapshot, root)
    _render_interpretation()
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


def _page_title() -> str:
    return "Provenance & Integrity"


def _page_subtitle() -> str:
    return (
        "Registered artifact provenance classes, recorded fingerprints and "
        "integrity checks, documented lineage, loading restrictions and "
        "known evidence gaps."
    )


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


def page_by_id_local() -> PageDefinition:
    return page_by_id(PAGE_ID)


def page_is_planned_local() -> bool:
    return page_is_planned(PAGE_ID)
