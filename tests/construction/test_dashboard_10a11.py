# -*- coding: utf-8 -*-
"""Tests for the CMIDO 10A.11 Real-World Data workspace.

Contract of behavior the new page must uphold, independent of any particular
snapshot built at test time:

* the page module imports cleanly and without the research engine,
* the page is registered as AVAILABLE in navigation with its own route,
* the real-data contract keeps the PSLIB, SUCCESS and 9A-fixture streams in
  separate fields (no cross-stream fallback),
* the SUCCESS logistics audit is registered and adapted,
* counts, coverage and time ranges are shown only where the artifacts record
  them — missing metadata renders as missing, never inferred,
* the OBS/DER/EST/SCN provenance vocabulary is presented consistently,
* filesystem paths and hex colors never reach the page source,
* the rendered page carries no raw lowercase snake_case labels,
* the page renders end-to-end through Streamlit's AppTest.
"""
from __future__ import annotations

import pathlib
import re
import sys
from typing import Any

import pytest

# Make the dashboard package importable under the src layout regardless of
# the working directory the test runner picks.
_SRC_ROOT = pathlib.Path(__file__).resolve().parents[2] / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

import src.construction.dashboard_data.adapters as adapters
import src.construction.dashboard_data.contract as contract
from src.construction.dashboard_data.contract import (
    ArtifactProvenance,
    ArtifactStatus,
    ProvenanceClass,
    RealDataEvidence,
)
from src.construction.dashboard_data.loaders import LoadResult
from src.construction.dashboard_data.registry import get_entry
from src.construction.dashboard_ui import formatting
from src.construction.dashboard_ui import real_world_data as page
from src.construction.dashboard_ui.navigation import (
    ImplementationStatus,
    pages_by_id,
)

_SNAKE_RE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _assert_no_hex_in_source(path: str) -> None:
    hits = _HEX_RE.findall(pathlib.Path(path).read_text(encoding="utf-8"))
    assert not hits, f"{path} hard codes hex colors: {hits}"


# ---------------------------------------------------------------------------
# Fixtures — small, owned evidence dicts that mirror the real artifact schemas
# ---------------------------------------------------------------------------


@pytest.fixture
def canonical_9a() -> dict[str, Any]:
    return {
        "schema_version": "8I-1.0",
        "dataset_id": "TEST_FIXTURE",
        "project": {
            "project_id": "TEST-001",
            "project_name": "Test Project",
            "location": "Nowhere",
            "project_type": "Infrastructure",
        },
        "activities": [
            {
                "activity_id": "A001",
                "activity_code": "EXC-001",
                "activity_name": "Excavation",
                "duration_days": 2,
                "status": "planned",
                "planned_start": "2026-01-05",
                "planned_finish": "2026-01-07",
            },
            {
                "activity_id": "A002",
                "activity_code": "CON-001",
                "activity_name": "Concrete Works",
                "duration_days": 5,
                "status": "planned",
                "planned_start": "2026-01-08",
                "planned_finish": "2026-01-12",
            },
        ],
        "dependencies": [
            {
                "predecessor_id": "A001",
                "successor_id": "A002",
                "relationship_type": "FS",
                "lag_days": 0.0,
            }
        ],
        "metadata": {
            "normalization": "explicit_column_mapping",
            "ingestion_schema_version": "9A-1.0",
            "source_format": "csv_bundle",
            "source_row_counts": {"project": 1, "activities": 2, "dependencies": 1},
            "rejected_record_count": 0,
            "source_traceability": "table + 1-based CSV row validated during ingestion",
        },
        "fingerprint_sha256": "a" * 64,
    }


@pytest.fixture
def pslib_audit() -> dict[str, Any]:
    return {
        "schema_version": "9B-1.0",
        "dataset_id": "TEST_PSLIB",
        "project_id": "T2025-01 Test Road",
        "project_name": "A test project workbook",
        "pslib_release": "3.4",
        "source_sha256": "b" * 64,
        "canonical_fingerprint_sha256": "c" * 64,
        "activity_count": 10,
        "dependency_count": 8,
        "risk_profile_count": 12,
        "control_snapshot_names": ["TP1", "TP2"],
        "resource_row_count": 3,
        "rejected_dependency_records": 1,
    }


@pytest.fixture
def logistics_audit() -> dict[str, Any]:
    return {
        "schema_version": "9B-1.0",
        "source_format": "SUCCESS_CSV_BUNDLE",
        "dataset_doi": "10.5281/zenodo.test",
        "tables": {
            "material_demand.csv": {
                "file": "material_demand.csv",
                "sha256": "d" * 64,
                "headers": ["demand_id", "material"],
                "row_count": 127,
                "invalid_numeric_or_date_rows": 0,
                "invalid_records": [],
                "provenance": "OBS",
            },
            "trucks_data.csv": {
                "file": "trucks_data.csv",
                "sha256": "e" * 64,
                "headers": ["Truck_id", "Vehicle"],
                "row_count": 5,
                "invalid_numeric_or_date_rows": 0,
                "invalid_records": [],
                "provenance": "OBS",
            },
        },
        "derived_summary": {
            "site_count": 9,
            "material_demand_count": 127,
            "unique_materials_in_demand": 4,
            "unique_suppliers_in_demand": 7,
            "top_materials_by_demand_rows": [["Pipes", 40], ["Steel", 30]],
        },
        "provenance": "OBS",
    }


@pytest.fixture
def manifest_9a() -> dict[str, Any]:
    return {
        "stage": "9A",
        "status": "PASS",
        "checks_passed": 2,
        "checks_total": 2,
        "checks": [
            {"check": "9a_mapping_exists", "passed": True, "detail": "D:\\repo\\mapping.json"},
            {"check": "zero_rejected_records", "passed": True, "detail": "0"},
        ],
        "frozen_predecessor_phases": ["8M", "8N"],
        "scope": "real-data ingestion boundary; no UI changes",
    }


@pytest.fixture
def manifest_9b() -> dict[str, Any]:
    return {
        "stage": "9B",
        "status": "PASS",
        "checks_passed": 1,
        "checks_total": 1,
        "checks": [
            {"check": "pslib_source_exists", "passed": True, "detail": "D:\\repo\\project.xlsx"},
        ],
        "integration_boundary": (
            "PSLIB empirical project and SUCCESS logistics evidence are retained "
            "as separate observed datasets."
        ),
    }


def _prov(
    artifact_id: str,
    status: ArtifactStatus = ArtifactStatus.AVAILABLE,
    *,
    provenance_class: ProvenanceClass = ProvenanceClass.OBS,
    row_count: int | None = None,
    file_size_bytes: int | None = 1024,
    schema_status: str = "LOADED",
) -> ArtifactProvenance:
    return ArtifactProvenance(
        artifact_id=artifact_id,
        source_path=f"results/{artifact_id.lower()}.json",
        provenance_class=provenance_class,
        research_stage="REAL_DATA",
        status=status,
        row_count=row_count,
        file_size_bytes=file_size_bytes,
        schema_status=schema_status,
    )


@pytest.fixture
def evidence(
    canonical_9a: dict[str, Any],
    pslib_audit: dict[str, Any],
    logistics_audit: dict[str, Any],
    manifest_9a: dict[str, Any],
    manifest_9b: dict[str, Any],
) -> RealDataEvidence:
    return RealDataEvidence(
        pslib_audit=pslib_audit,
        ingestion_audit_9a={"rejected_record_count": 0},
        canonical_9a=canonical_9a,
        generalization_manifest_9a=manifest_9a,
        logistics_audit=logistics_audit,
        experiment_9b=manifest_9b,
        provenance=[
            _prov("REAL_9A_CANONICAL", provenance_class=ProvenanceClass.OBS),
            _prov("REAL_9A_INGESTION_AUDIT", provenance_class=ProvenanceClass.DER),
            _prov("REAL_9A_MANIFEST", provenance_class=ProvenanceClass.DER),
            _prov("REAL_9B_PSLIB_AUDIT", provenance_class=ProvenanceClass.OBS),
            _prov("REAL_9B_LOGISTICS_AUDIT", provenance_class=ProvenanceClass.OBS),
            _prov("REAL_9B_MANIFEST", provenance_class=ProvenanceClass.DER),
        ],
    )


# ---------------------------------------------------------------------------
# Module + navigation surface
# ---------------------------------------------------------------------------


def test_real_world_module_imports_without_research_engine() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    banned = ("solve_ro3", "run_ro3", "optimization_engine", "scenario_generation")
    for token in banned:
        assert token not in source, f"page module references {token}"


def test_page_is_registered_and_available() -> None:
    entry = pages_by_id()["real_world_data"]
    assert entry.implementation is ImplementationStatus.AVAILABLE
    assert entry.route == "page/real_world_data"
    assert entry.group == "EVIDENCE"
    assert entry.research_stage == "REAL_DATA"


def test_page_description_declares_both_observed_streams() -> None:
    desc = page.page_description().lower()
    assert "pslib" in desc
    assert "success" in desc


def test_page_future_phase_is_recorded() -> None:
    future = page.page_future_phase()
    assert future
    assert len(future) > 10


def test_page_is_not_planned() -> None:
    assert not page.page_is_planned_local()


# ---------------------------------------------------------------------------
# Registry + contract + adapter mapping
# ---------------------------------------------------------------------------


def test_logistics_audit_is_registered() -> None:
    entry = get_entry("REAL_9B_LOGISTICS_AUDIT")
    assert entry is not None
    assert entry.artifact_type.value == "JSON"
    assert entry.loading_policy is not None
    assert entry.provenance_class == "OBS"
    assert "SUCCESS" in entry.description


def test_registry_no_longer_calls_the_fixture_success_derived() -> None:
    """Integrity guard: the 9A fixture must not be described as SUCCESS data.

    The corrected descriptions may *deny* a SUCCESS connection ("not PSLIB,
    not SUCCESS"); what they must never do is claim one, as the old strings
    ("SUCCESS-derived", "Audit of SUCCESS") did.
    """
    forbidden_claims = ("SUCCESS-derived", "Audit of SUCCESS", "SUCCESS data ingestion")
    for artifact_id in ("REAL_9A_CANONICAL", "REAL_9A_INGESTION_AUDIT"):
        entry = get_entry(artifact_id)
        assert entry is not None
        for claim in forbidden_claims:
            assert claim not in entry.description, (
                f"{artifact_id} description must not claim {claim!r} provenance"
            )


def test_adapter_keeps_streams_in_separate_fields(
    canonical_9a: dict[str, Any],
    pslib_audit: dict[str, Any],
    logistics_audit: dict[str, Any],
    manifest_9a: dict[str, Any],
    manifest_9b: dict[str, Any],
) -> None:
    def load(artifact_id: str, data: Any) -> LoadResult:
        entry = get_entry(artifact_id)
        assert entry is not None
        return LoadResult(
            entry=entry,
            status=ArtifactStatus.AVAILABLE,
            data=data,
            provenance=_prov(artifact_id),
        )

    adapted = adapters.adapt_real_data_evidence(
        {
            "REAL_9A_CANONICAL": load("REAL_9A_CANONICAL", canonical_9a),
            "REAL_9A_INGESTION_AUDIT": load("REAL_9A_INGESTION_AUDIT", {"x": 1}),
            "REAL_9A_MANIFEST": load("REAL_9A_MANIFEST", manifest_9a),
            "REAL_9B_PSLIB_AUDIT": load("REAL_9B_PSLIB_AUDIT", pslib_audit),
            "REAL_9B_LOGISTICS_AUDIT": load("REAL_9B_LOGISTICS_AUDIT", logistics_audit),
            "REAL_9B_MANIFEST": load("REAL_9B_MANIFEST", manifest_9b),
        }
    )
    assert adapted.canonical_9a["dataset_id"] == "TEST_FIXTURE"
    assert adapted.pslib_audit["dataset_id"] == "TEST_PSLIB"
    assert adapted.logistics_audit["dataset_doi"] == "10.5281/zenodo.test"
    assert adapted.generalization_manifest_9a["status"] == "PASS"
    assert adapted.experiment_9b["stage"] == "9B"
    # The 9A ingestion audit is NOT the SUCCESS stream and must not live in a
    # SUCCESS-named field.
    assert adapted.ingestion_audit_9a == {"x": 1}
    assert len(adapted.provenance) == 6


def test_adapter_leaves_fields_empty_for_invalid_evidence() -> None:
    entry = get_entry("REAL_9B_LOGISTICS_AUDIT")
    assert entry is not None
    invalid = LoadResult(
        entry=entry,
        status=ArtifactStatus.INVALID,
        data=None,
        provenance=_prov("REAL_9B_LOGISTICS_AUDIT", ArtifactStatus.INVALID),
        error_message="parse error",
    )
    adapted = adapters.adapt_real_data_evidence({"REAL_9B_LOGISTICS_AUDIT": invalid})
    assert adapted.logistics_audit == {}
    assert adapted.provenance[0].status == ArtifactStatus.INVALID


def test_adapter_leaves_fields_empty_for_schema_variation() -> None:
    """A JSON artifact that is a list instead of an object adapts to empty."""
    entry = get_entry("REAL_9B_PSLIB_AUDIT")
    assert entry is not None
    weird = LoadResult(
        entry=entry,
        status=ArtifactStatus.AVAILABLE,
        data=[{"unexpected": "list"}],
        provenance=_prov("REAL_9B_PSLIB_AUDIT"),
    )
    adapted = adapters.adapt_real_data_evidence({"REAL_9B_PSLIB_AUDIT": weird})
    assert adapted.pslib_audit == {}


# ---------------------------------------------------------------------------
# Artifact inventory builders — honest statuses
# ---------------------------------------------------------------------------


def test_artifact_status_index_defaults_missing() -> None:
    index = page.artifact_status_index([])
    assert set(index) == set(page.REAL_DATA_ARTIFACT_IDS)
    assert all(status == "MISSING" for status in index.values())


def test_artifact_table_marks_absent_artifacts_not_registered() -> None:
    rows = page.build_artifact_table_rows([])
    assert len(rows) == len(page.REAL_DATA_ARTIFACT_IDS)
    assert all(row["Status"] == "NOT REGISTERED" for row in rows)
    assert all(row["Rows"] == formatting.MISSING_DISPLAY for row in rows)


def test_artifact_table_carries_recorded_statuses(evidence: RealDataEvidence) -> None:
    rows = page.build_artifact_table_rows(page.build_provenance_rows(evidence))
    by_artifact = {row["Artifact"]: row for row in rows}
    pslib_row = by_artifact["9B PSLIB project audit"]
    assert pslib_row["Status"] == "AVAILABLE"
    assert pslib_row["Provenance"] == "OBS"


def test_artifact_table_preserves_invalid_and_too_large() -> None:
    rows = page.build_artifact_table_rows(
        [
            page.build_provenance_rows(
                RealDataEvidence(
                    provenance=[
                        _prov(
                            "REAL_9B_PSLIB_AUDIT",
                            ArtifactStatus.TOO_LARGE,
                            schema_status="EXCEEDS_SIZE_LIMIT",
                        )
                    ]
                )
            )[0]
        ]
    )
    assert rows[3]["Status"] == "TOO_LARGE"
    assert "EXCEEDS SIZE LIMIT" in rows[3]["Schema check"]


def test_fmt_size_is_honest_for_missing_and_small() -> None:
    assert page._fmt_size(None) == formatting.MISSING_DISPLAY
    assert page._fmt_size("bad") == formatting.MISSING_DISPLAY
    assert page._fmt_size(200) == "200 B"
    assert page._fmt_size(2727).endswith("KB")


# ---------------------------------------------------------------------------
# Fixture builders — no inference beyond recorded fields
# ---------------------------------------------------------------------------


def test_fixture_activity_rows_come_from_the_artifact(canonical_9a: dict[str, Any]) -> None:
    rows = page.build_fixture_activity_rows(canonical_9a)
    assert len(rows) == 2
    assert rows[0]["Name"] == "Excavation"
    assert rows[0]["Planned start"] == "2026-01-05"


def test_fixture_time_range_is_minmax_of_recorded_dates(canonical_9a: dict[str, Any]) -> None:
    assert page.build_fixture_time_range(canonical_9a) == "2026-01-05 to 2026-01-12"


def test_fixture_time_range_is_none_without_recorded_dates() -> None:
    """Dates are never inferred from file names, sources or other metadata."""
    no_dates = {
        "source": "D:\\data\\some_project_file.csv",
        "activities": [{"activity_id": "A001", "duration_days": 2}],
    }
    assert page.build_fixture_time_range(no_dates) is None
    assert page.build_fixture_time_range({}) is None


def test_fixture_row_count_rows_include_rejections(canonical_9a: dict[str, Any]) -> None:
    rows = page.build_fixture_row_count_rows(canonical_9a)
    labels = {row["Table"]: row["Source rows"] for row in rows}
    assert labels["activities"] == "2"
    assert labels["Rejected records"] == "0"


# ---------------------------------------------------------------------------
# PSLIB builders — explicit fields only, missing renders missing
# ---------------------------------------------------------------------------


def test_pslib_coverage_rows_read_recorded_fields(pslib_audit: dict[str, Any]) -> None:
    rows = page.build_pslib_coverage_rows(pslib_audit)
    by_metric = {row["Coverage metric"]: row["Recorded value"] for row in rows}
    assert by_metric["Activities"] == "10"
    assert by_metric["Control snapshots"] == "2 (TP1, TP2)"
    assert by_metric["Rejected dependency records"] == "1"


def test_pslib_coverage_shows_missing_for_absent_fields() -> None:
    rows = page.build_pslib_coverage_rows({})
    assert all(row["Recorded value"] == formatting.MISSING_DISPLAY for row in rows)


def test_pslib_time_range_stays_unrecorded(pslib_audit: dict[str, Any]) -> None:
    """The audit has no date fields; the builder must not invent any."""
    assert not any("date" in key for key in pslib_audit)


# ---------------------------------------------------------------------------
# SUCCESS builders — table coverage, humanized labels, honest summaries
# ---------------------------------------------------------------------------


def test_logistics_coverage_rows_humanize_names(logistics_audit: dict[str, Any]) -> None:
    rows = page.build_logistics_coverage_rows(logistics_audit)
    assert len(rows) == 2
    names = [row["Table"] for row in rows]
    assert "material demand.csv" in names
    for name in names:
        assert "_" not in name, "table names must be humanized for display"
    by_name = {row["Table"]: row for row in rows}
    assert by_name["material demand.csv"]["Rows"] == "127"
    assert by_name["material demand.csv"]["Recorded provenance"] == "OBS"


def test_logistics_coverage_empty_without_tables() -> None:
    assert page.build_logistics_coverage_rows({}) == []


def test_logistics_summary_and_top_materials(logistics_audit: dict[str, Any]) -> None:
    summary = page.build_logistics_summary_rows(logistics_audit)
    labels = {row["Recorded summary metric"] for row in summary}
    assert "Construction sites" in labels
    assert "Unique materials in demand" in labels
    top = page.build_top_materials_rows(logistics_audit)
    assert top[0] == {"Material": "Pipes", "Demand rows": "40"}


def test_top_materials_skips_malformed_entries() -> None:
    malformed = {
        "derived_summary": {
            "top_materials_by_demand_rows": [["Pipes", 4], "not-a-pair", ["OnlyName"]],
        }
    }
    assert page.build_top_materials_rows(malformed) == [
        {"Material": "Pipes", "Demand rows": "4"}
    ]


# ---------------------------------------------------------------------------
# Stream separation — no cross-stream fallbacks
# ---------------------------------------------------------------------------


def test_pslib_builder_never_reads_from_the_success_stream(
    logistics_audit: dict[str, Any],
) -> None:
    """Feeding the SUCCESS audit to the PSLIB builder yields no numbers."""
    rows = page.build_pslib_coverage_rows(logistics_audit)
    assert rows
    assert all(
        row["Recorded value"] == formatting.MISSING_DISPLAY for row in rows
    ), "PSLIB metrics must not be populated from SUCCESS evidence"


def test_success_builder_never_reads_from_the_pslib_stream(
    pslib_audit: dict[str, Any],
) -> None:
    assert page.build_logistics_coverage_rows(pslib_audit) == []
    assert page.build_top_materials_rows(pslib_audit) == []


def test_fixture_builder_never_reads_from_either_observed_stream(
    pslib_audit: dict[str, Any], logistics_audit: dict[str, Any]
) -> None:
    assert page.build_fixture_activity_rows(pslib_audit) == []
    assert page.build_fixture_time_range(logistics_audit) is None


# ---------------------------------------------------------------------------
# Gate builders — humanized checks, path suppression, honest results
# ---------------------------------------------------------------------------


def test_gate_summary_reports_recorded_status(manifest_9a: dict[str, Any]) -> None:
    summary = page.build_gate_summary(manifest_9a)
    assert summary == {"status": "PASS", "passed": "2", "total": "2"}


def test_gate_summary_is_honest_when_manifest_is_empty() -> None:
    summary = page.build_gate_summary({})
    assert summary["status"] == "not recorded"
    assert summary["total"] == formatting.MISSING_DISPLAY


def test_gate_check_rows_humanize_names_and_suppress_paths(
    manifest_9a: dict[str, Any],
) -> None:
    rows = page.build_gate_check_rows(manifest_9a)
    assert rows[0]["Check"] == "9a mapping exists"
    assert rows[0]["Result"] == "PASS"
    # The recorded detail names a file path and must be suppressed.
    assert rows[0]["Recorded detail"] == formatting.MISSING_DISPLAY
    assert rows[1]["Recorded detail"] == "0"
    for row in rows:
        assert "_" not in row["Check"]


def test_gate_check_rows_treat_non_bool_results_as_missing() -> None:
    rows = page.build_gate_check_rows(
        {"checks": [{"check": "x", "passed": "maybe", "detail": ""}]}
    )
    assert rows[0]["Result"] == formatting.MISSING_DISPLAY


def test_gate_notes_include_boundary_and_never_paths(
    manifest_9a: dict[str, Any], manifest_9b: dict[str, Any]
) -> None:
    notes_9a = page.build_gate_notes(manifest_9a)
    assert any("Scope:" in note for note in notes_9a)
    assert any("Frozen predecessor phases: 8M, 8N." in note for note in notes_9a)
    notes_9b = page.build_gate_notes(manifest_9b)
    assert any("separate observed datasets" in note for note in notes_9b)
    for note in notes_9a + notes_9b:
        assert ".json" not in note and ".xlsx" not in note


# ---------------------------------------------------------------------------
# Provenance vocabulary
# ---------------------------------------------------------------------------


def test_provenance_legend_covers_the_documented_classes() -> None:
    codes = [code for code, _ in page.PROVENANCE_LEGEND]
    assert codes == ["OBS", "DER", "EST", "SCN"]


def test_provenance_label_falls_back_honestly() -> None:
    assert "not recorded" in page.provenance_label("XYZ").lower()
    assert "observed" in page.provenance_label("OBS").lower()


def test_provenance_rows_carry_classes_and_statuses(evidence: RealDataEvidence) -> None:
    rows = page.build_provenance_rows(evidence)
    assert len(rows) == 6
    classes = {row["provenance_class"] for row in rows}
    assert classes == {"OBS", "DER"}


# ---------------------------------------------------------------------------
# Source hygiene — no paths, no hex, no direct Streamlit, no raw styling
# ---------------------------------------------------------------------------


def test_no_raw_path_in_page_source() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "D:\\CMIDO" not in source
    assert "D:/CMIDO" not in source


def test_no_hex_color_literal_in_page_source() -> None:
    _assert_no_hex_in_source(page.__file__)


def test_page_does_not_import_streamlit_directly() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "import streamlit" not in source
    assert "from streamlit" not in source


def test_page_uses_only_the_component_layer_for_styling() -> None:
    """Light/dark parity is inherited from the design system: no inline CSS."""
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "style=" not in source
    assert "<div" not in source
    assert "light-dark(" not in source


# ---------------------------------------------------------------------------
# Runtime render (AppTest) — the page must render end-to-end
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_world_app():
    from streamlit.testing.v1 import AppTest

    app_path = pathlib.Path(__file__).resolve().parents[2] / "apps" / "cmido_dashboard.py"
    at = AppTest.from_file(str(app_path), default_timeout=90)
    at.session_state["cmido_active_page"] = "real_world_data"
    at.run()
    return at


class TestRealWorldRuntime:
    def test_page_renders_without_exception(self, real_world_app) -> None:
        assert not real_world_app.exception

    def test_page_shows_all_three_streams(self, real_world_app) -> None:
        text = " ".join(str(m.value) for m in real_world_app.markdown)
        assert "PSLIB empirical project stream" in text
        assert "SUCCESS construction-logistics stream" in text
        assert "9A ingestion fixture" in text

    def test_page_shows_separation_boundary(self, real_world_app) -> None:
        text = " ".join(str(m.value) for m in real_world_app.markdown)
        assert "Integration boundary" in text
        assert "separate observed datasets" in text

    def test_page_shows_provenance_legend_and_limitations(self, real_world_app) -> None:
        text = " ".join(str(m.value) for m in real_world_app.markdown)
        assert "Provenance legend" in text
        assert "Limitations and what is missing" in text
        assert "external generalization" in text

    def test_page_shows_artifact_inventory(self, real_world_app) -> None:
        text = " ".join(str(m.value) for m in real_world_app.markdown)
        assert "Registered real-data artifacts" in text

    def test_no_snake_case_labels_leak_into_the_page(self, real_world_app) -> None:
        text = " ".join(str(m.value) for m in real_world_app.markdown)
        leaks = _SNAKE_RE.findall(text)
        assert leaks == [], f"snake_case labels leaked into the page: {leaks}"

    def test_no_filesystem_paths_leak_into_the_page(self, real_world_app) -> None:
        text = " ".join(str(m.value) for m in real_world_app.markdown)
        assert "D:\\CMIDO" not in text
        assert "\\\\results\\\\" not in text
