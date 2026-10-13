# -*- coding: utf-8 -*-
"""Tests for the CMIDO 10A.13 Provenance & Integrity workspace.

Contract of behavior we want the new page to uphold, independent of any
particular snapshot built at test time:

* the page module imports cleanly from the UI package without any research
  engine and without importing Streamlit directly,
* the page is registered as AVAILABLE in navigation with a live route and is
  dispatched by the application shell,
* the artifact inventory maps every registry entry to its recorded provenance
  class, status and schema outcome — missing records read MISSING, never zero,
* recorded integrity checks are reported from artifact-recorded values only,
  and are kept strictly apart from the checks the dashboard performs itself,
* unregistered, missing and partially documented evidence is surfaced
  explicitly, and existence checks are disclosed as dashboard-performed,
* recorded fingerprints are displayed as recorded — never recomputed, never
  presented as scientific validity, and never mistaken for registration,
* PSLIB and SUCCESS remain separate streams in separate builders,
* no raw filesystem path, hex colour or snake_case label reaches the page
  source or the rendered page,
* the large raw scenario ledgers stay blocked by loading policy,
* the recorded RO3 scenario-count convergence failure is preserved verbatim
  through the shared builder,
* the page renders end-to-end against the real repository artifacts with no
  exception and no fabricated evidence.

The tests exercise the module surface and the contract/registry plumbing
directly. They do not depend on a particular snapshot being built at import
time, except where a real-snapshot fixture is explicitly named.
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

from src.construction.dashboard_data.contract import (
    ArtifactProvenance,
    ArtifactStatus,
    DashboardSnapshot,
    ProvenanceClass,
    PublicationEvidence,
    RealDataEvidence,
    RO1Evidence,
    RO2Evidence,
    RO3Evidence,
)
from src.construction.dashboard_data.loaders import load_artifact
from src.construction.dashboard_data.registry import (
    ARTIFACT_REGISTRY,
    get_blocked_ids,
    get_entry,
)
from src.construction.dashboard_data.snapshot import build_dashboard_snapshot
from src.construction.dashboard_ui import ablation_robustness as ablation_page
from src.construction.dashboard_ui import provenance_integrity as page
from src.construction.dashboard_ui.navigation import (
    ImplementationStatus,
    legacy_route_for,
    pages_by_id,
)

_SNAKE_RE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _assert_no_hex_in_source(path: str) -> None:
    source = pathlib.Path(path).read_text(encoding="utf-8")
    hits = _HEX_RE.findall(source)
    assert not hits, f"{path} hard codes hex colors: {hits}"


def _provenance(
    artifact_id: str,
    status: ArtifactStatus = ArtifactStatus.AVAILABLE,
    schema_status: str = "PASSED",
    provenance_class: ProvenanceClass = ProvenanceClass.DER,
    row_count: int | None = 3,
    file_size_bytes: int | None = 1024,
) -> ArtifactProvenance:
    return ArtifactProvenance(
        artifact_id=artifact_id,
        source_path=f"results/fake/{artifact_id}",
        provenance_class=provenance_class,
        research_stage="RO3",
        status=status,
        row_count=row_count,
        file_size_bytes=file_size_bytes,
        schema_status=schema_status,
    )


def _row_values(rows: list[dict[str, Any]]) -> list[str]:
    return [str(value) for row in rows for value in row.values()]


def _assert_no_paths(rows: list[dict[str, Any]]) -> None:
    for value in _row_values(rows):
        assert "results/" not in value, f"path leaked into display row: {value}"
        assert "\\" not in value, f"path leaked into display row: {value}"
        assert "D:" not in value, f"path leaked into display row: {value}"
        assert "src/" not in value, f"path leaked into display row: {value}"


# ---------------------------------------------------------------------------
# Module surface, navigation registration and dispatch
# ---------------------------------------------------------------------------


def test_module_imports_without_research_engine() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "src.optimization",
        "src.simulation",
        "src.forecasting",
        "src.research",
    ):
        assert forbidden not in source, f"page must not import {forbidden}"
    assert "import streamlit" not in source
    assert "from streamlit" not in source


def test_page_is_registered_and_available() -> None:
    by_id = pages_by_id()
    assert "provenance_integrity" in by_id
    entry = by_id["provenance_integrity"]
    assert entry.implementation is ImplementationStatus.AVAILABLE
    assert entry.route == "page/provenance_integrity"
    assert entry.group == "EVIDENCE"
    assert entry.future_phase == "Phase 10A.13"
    assert entry.research_stage == "EVIDENCE"


def test_legacy_route_resolves_for_the_dispatch() -> None:
    assert legacy_route_for("provenance_integrity") == "page/provenance_integrity"


def test_page_description_declares_the_evidence_scope() -> None:
    desc = page.page_description().lower()
    assert "provenance" in desc
    assert "integrity" in desc


def test_page_module_helpers_are_exported() -> None:
    assert page.page_is_planned_local() is False
    assert page.page_by_id_local().id == "provenance_integrity"
    assert page.page_future_phase() == "Phase 10A.13"


def test_app_dispatch_routes_the_page() -> None:
    source = (
        pathlib.Path(__file__).resolve().parents[2] / "apps" / "cmido_dashboard.py"
    ).read_text(encoding="utf-8")
    assert 'elif route == "page/provenance_integrity":' in source
    assert "provenance_workspace.render_page" in source
    assert "import provenance_integrity as provenance_workspace" in source


# ---------------------------------------------------------------------------
# Provenance class and artifact-registry mapping
# ---------------------------------------------------------------------------


def test_inventory_covers_every_registry_entry() -> None:
    snapshot = DashboardSnapshot()
    rows = page.build_inventory_rows(snapshot)
    assert len(rows) == len(ARTIFACT_REGISTRY)
    names = {row["Artifact"] for row in rows}
    assert names == {entry.name for entry in ARTIFACT_REGISTRY}


def test_inventory_without_records_reads_missing_not_zero() -> None:
    rows = page.build_inventory_rows(DashboardSnapshot())
    for row in rows:
        assert row["Status"] == ArtifactStatus.MISSING.value
        assert row["Schema check"] == "NOT RECORDED"
        assert row["Rows"] == "—"
        assert row["Size (bytes)"] == "—"


def test_inventory_carries_recorded_status_schema_and_size() -> None:
    snapshot = DashboardSnapshot(
        provenance=[
            _provenance("RO3_BASELINE_COMPARISON"),
            _provenance(
                "RO3_ABLATION",
                status=ArtifactStatus.INVALID,
                schema_status="MISSING_COLUMNS: mean_difference",
            ),
            _provenance(
                "RO3_STRESS_SUMMARY",
                status=ArtifactStatus.TOO_LARGE,
                schema_status="BLOCKED_BY_POLICY",
                row_count=None,
                file_size_bytes=None,
            ),
        ]
    )
    rows = {row["Artifact"]: row for row in page.build_inventory_rows(snapshot)}
    ok = rows["RO3 Baseline Comparison (publication T5)"]
    assert ok["Status"] == ArtifactStatus.AVAILABLE.value
    assert ok["Schema check"] == "PASSED"
    assert ok["Rows"] == "3"
    assert ok["Size (bytes)"] == "1,024"

    bad = rows["RO3 Ablation (publication T6)"]
    assert bad["Status"] == ArtifactStatus.INVALID.value
    assert bad["Schema check"] == "MISSING COLUMNS: mean difference"

    blocked = rows["RO3 Stress Test Summary"]
    assert blocked["Status"] == ArtifactStatus.TOO_LARGE.value
    assert blocked["Schema check"] == "BLOCKED BY POLICY"
    assert blocked["Rows"] == "—"


def test_inventory_provenance_class_comes_from_the_record() -> None:
    snapshot = DashboardSnapshot(
        provenance=[
            _provenance("RO3_BASELINE_COMPARISON", provenance_class=ProvenanceClass.EST),
            _provenance("REAL_9B_PSLIB_AUDIT", provenance_class=ProvenanceClass.OBS),
        ]
    )
    rows = {row["Artifact"]: row for row in page.build_inventory_rows(snapshot)}
    assert rows["RO3 Baseline Comparison (publication T5)"]["Provenance"] == "EST"
    assert rows["9B PSLIB Audit"]["Provenance"] == "OBS"
    # Entries without a record fall back to the registry's own recorded class.
    assert rows["RO3 Stress Test Summary"]["Provenance"] == "SCN"


def test_class_and_status_counts_follow_the_records() -> None:
    snapshot = DashboardSnapshot(
        provenance=[
            _provenance("RO3_BASELINE_COMPARISON", provenance_class=ProvenanceClass.EST),
            _provenance("REAL_9B_PSLIB_AUDIT", provenance_class=ProvenanceClass.OBS),
            _provenance(
                "RO3_STRESS_SUMMARY",
                status=ArtifactStatus.TOO_LARGE,
                provenance_class=ProvenanceClass.SCN,
            ),
        ]
    )
    classes = page.build_class_counts(snapshot)
    assert classes == {"OBS": 1, "DER": 0, "EST": 1, "SCN": 1}
    statuses = page.build_status_counts(snapshot)
    assert statuses[ArtifactStatus.AVAILABLE.value] == 2
    assert statuses[ArtifactStatus.TOO_LARGE.value] == 1


def test_every_registry_entry_records_a_provenance_class() -> None:
    """No artifact is left unclassified in the registry this page presents."""
    for entry in ARTIFACT_REGISTRY:
        assert entry.provenance_class in {"OBS", "DER", "EST", "SCN"}, (
            f"{entry.artifact_id} records provenance class {entry.provenance_class!r}"
        )


# ---------------------------------------------------------------------------
# Recorded checks vs checks performed by the dashboard
# ---------------------------------------------------------------------------


def test_recorded_check_outcome_derives_from_manifest_values() -> None:
    snapshot = DashboardSnapshot(
        ro3=RO3Evidence(
            ablation_gate_manifest={
                "checks_passed": 3,
                "checks_total": 4,
                "status": "PASS",
            }
        )
    )
    rows = page.build_recorded_check_rows(snapshot)
    gate = next(r for r in rows if r["Check source"] == "8M ablation evidence gate")
    assert gate["Recorded outcome"] == (
        "3 of 4 checks recorded as passed (status PASS)."
    )


def test_recorded_checks_without_artifacts_read_unavailable() -> None:
    rows = page.build_recorded_check_rows(DashboardSnapshot())
    assert len(rows) == 10
    for row in rows:
        assert row["Recorded outcome"] == "Not available in this snapshot", row


def test_rows_outcome_unwraps_adapter_audit_rows() -> None:
    wrapped = {
        "audit_rows": [
            {"check": "a", "passed": True},
            {"check": "b", "passed": False},
            {"check": "c", "passed": True},
        ]
    }
    assert page._rows_outcome(wrapped) == "2 of 3 checks recorded as passed."
    assert page._rows_outcome([{"passed": True}]) == "1 of 1 checks recorded as passed."
    assert page._rows_outcome({}) == "Not available in this snapshot"
    assert page._rows_outcome(None) == "Not available in this snapshot"


def test_recorded_check_rows_never_report_a_re_run() -> None:
    """Outcomes are recorded values; no wording may claim the check was redone."""
    rows = page.build_recorded_check_rows(DashboardSnapshot())
    for row in rows:
        outcome = row["Recorded outcome"]
        assert "re-run" not in outcome
        assert "recomputed" not in outcome


def test_performed_and_not_performed_checks_are_distinct() -> None:
    performed = " ".join(page.DASHBOARD_CHECKS_PERFORMED)
    not_performed = " ".join(page.DASHBOARD_CHECKS_NOT_PERFORMED)
    assert "File presence" in performed
    assert "Column contract" in performed
    assert "Policy enforcement" in performed
    assert "Existence-only disclosure" in performed
    assert "No SHA-256 digest is recomputed" in not_performed
    assert "No recorded gate, audit or reconciliation is re-run" in not_performed
    assert "No recorded statistical test is recomputed" in not_performed
    for phrase in ("recomputed", "re-run", "independently verified"):
        assert phrase not in performed, f"{phrase!r} may only describe unperformed checks"


def test_page_source_states_reported_not_rerun() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "Reported, not re-run" in source
    assert "does not independently establish scientific validity" in source
    assert "never re-derived" in source


# ---------------------------------------------------------------------------
# Missing, invalid, unregistered and partially documented evidence
# ---------------------------------------------------------------------------


def test_unregistered_rows_report_presence_and_registration(tmp_path) -> None:
    specs = page.KNOWN_UNREGISTERED_ARTIFACTS
    present_spec = specs[0]
    absent_spec = specs[1]
    target = tmp_path / present_spec.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")

    rows = page.build_unregistered_rows(tmp_path)
    assert len(rows) == len(specs)
    by_name = {row["Artifact"]: row for row in rows}
    assert by_name[present_spec.artifact]["Present in repository"] == "Yes"
    assert by_name[absent_spec.artifact]["Present in repository"] == "No"
    for row in rows:
        assert row["Registered"] == "No"
    _assert_no_paths(rows)


def test_unregistered_specs_are_really_absent_from_the_registry() -> None:
    registry_paths = {str(entry.relative_path).replace("\\", "/") for entry in ARTIFACT_REGISTRY}
    for spec in page.KNOWN_UNREGISTERED_ARTIFACTS:
        assert spec.relative_path not in registry_paths, (
            f"{spec.relative_path} is registered; it must not be listed as unregistered"
        )


def test_unregistered_specs_reference_known_documentation() -> None:
    """Every gap row names where the limitation is documented."""
    for spec in page.KNOWN_UNREGISTERED_ARTIFACTS:
        assert spec.documented_by, spec
        assert spec.artifact, spec


def test_absent_root_renders_presence_no_not_fabricated_yes(tmp_path) -> None:
    rows = page.build_unregistered_rows(tmp_path)
    assert {row["Present in repository"] for row in rows} == {"No"}


def test_empty_snapshot_lineage_and_fingerprint_builders_stay_empty() -> None:
    snapshot = DashboardSnapshot()
    assert page.build_lineage_rows(snapshot) == []
    assert page.build_gate_fingerprint_rows(snapshot) == []
    assert page.build_success_fingerprint_rows(snapshot) == []


def test_missing_metadata_language_is_explicit_in_source() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "record no collection or creation dates" in source
    assert "undocumented" in source
    assert "never filled in" in source
    assert "transformation chain is not recorded" in source


# ---------------------------------------------------------------------------
# Fingerprints: availability, safe display, and what they establish
# ---------------------------------------------------------------------------


def test_gate_fingerprint_registration_is_computed_against_registry() -> None:
    registered_path = ARTIFACT_REGISTRY[0].relative_path
    snapshot = DashboardSnapshot(
        ro3=RO3Evidence(
            ablation_gate_manifest={
                "source_artifacts": {
                    "origin": {"path": registered_path, "sha256": "a" * 64},
                    "material": {"path": "results/RO3/not_registered.csv", "sha256": "b" * 64},
                    "unknown_key": {"path": "results/x.csv", "sha256": "c" * 64},
                }
            }
        )
    )
    rows = page.build_gate_fingerprint_rows(snapshot)
    assert len(rows) == 3
    assert rows[0]["Registered"] == "Yes"
    assert rows[1]["Registered"] == "No"
    assert rows[0]["Recorded digest"] == "a" * 64
    # Unrecognised keys fall back to a human label, never the raw key.
    assert rows[2]["Source artifact"] == "unknown key"
    _assert_no_paths(rows)


def test_fingerprint_display_never_pretends_to_be_validity() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "does not independently establish scientific validity" in source
    assert "never re-derived" in source
    assert "also not registration" in source
    assert "Registration is computed by comparing" in source


def test_real_snapshot_fingerprints_are_present_and_well_formed() -> None:
    snapshot = build_dashboard_snapshot()

    gate_rows = page.build_gate_fingerprint_rows(snapshot)
    assert len(gate_rows) == 10
    for row in gate_rows:
        assert _DIGEST_RE.match(row["Recorded digest"]), row
        assert row["Registered"] == "No"  # step-36 sources are unregistered
    _assert_no_paths(gate_rows)

    source_rows = page.build_source_fingerprint_rows(snapshot)
    assert len(source_rows) == 3
    pslib_digest = str(snapshot.real_data.pslib_audit.get("source_sha256", ""))
    assert pslib_digest in [row["Recorded digest"] for row in source_rows]
    _assert_no_paths(source_rows)

    success_rows = page.build_success_fingerprint_rows(snapshot)
    assert len(success_rows) == 7
    for row in success_rows:
        assert _DIGEST_RE.match(row["Recorded digest"]), row
    # The SUCCESS stream never carries the PSLIB digests.
    assert pslib_digest not in [row["Recorded digest"] for row in success_rows]
    _assert_no_paths(success_rows)


def test_lineage_rows_display_names_not_paths() -> None:
    snapshot = DashboardSnapshot(
        evidence=PublicationEvidence(
            publication_manifest={
                "artifacts": [
                    {
                        "artifact": "T5_RO3_baseline_comparison.csv",
                        "source_name": "RO3_step36_statistical_pairwise_comparisons.csv",
                        "source_path": "results\\RO3\\ablation\\final_comparison\\x.csv",
                        "source_sha256": "d" * 64,
                        "generation_script": "src/optimization/cmido_8q_publication_artifacts.py",
                    }
                ]
            }
        )
    )
    rows = page.build_lineage_rows(snapshot)
    assert len(rows) == 1
    row = rows[0]
    assert row["Publication table"] == "T5 RO3 baseline comparison.csv"
    assert row["Generation script"] == "cmido 8q publication artifacts"
    assert row["Source digest"] == "d" * 64
    _assert_no_paths(rows)


def test_real_snapshot_publication_lineage_is_recorded() -> None:
    snapshot = build_dashboard_snapshot()
    rows = page.build_lineage_rows(snapshot)
    assert len(rows) == 9
    for row in rows:
        assert _DIGEST_RE.match(row["Source digest"]), row
        assert row["Generation script"] != "—"
    _assert_no_paths(rows)


# ---------------------------------------------------------------------------
# PSLIB and SUCCESS remain separate streams
# ---------------------------------------------------------------------------


def test_success_builder_reads_only_the_logistics_audit() -> None:
    snapshot = DashboardSnapshot(
        real_data=RealDataEvidence(
            pslib_audit={"source_sha256": "e" * 64},
            logistics_audit={
                "tables": {
                    "CCC_options_data.csv": {
                        "file": "CCC_options_data.csv",
                        "sha256": "f" * 64,
                        "row_count": 25,
                    }
                }
            },
        )
    )
    success_rows = page.build_success_fingerprint_rows(snapshot)
    source_rows = page.build_source_fingerprint_rows(snapshot)
    assert [row["Recorded digest"] for row in success_rows] == ["f" * 64]
    assert "e" * 64 in [row["Recorded digest"] for row in source_rows]
    assert "f" * 64 not in [row["Recorded digest"] for row in source_rows]
    assert all(row["SUCCESS table"] != "—" for row in success_rows)


def test_page_source_states_the_separation_rule() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "never joined" in source
    assert "separate observed streams" in source
    assert "never read as supplier-specific procurement" in source


# ---------------------------------------------------------------------------
# Loading policy and blocked large ledgers
# ---------------------------------------------------------------------------


def test_blocked_ids_are_the_raw_scenario_ledgers() -> None:
    blocked = set(get_blocked_ids())
    assert blocked == {"RO3_SCENARIOS_2500_RAW", "RO3_SCENARIOS_5000_RAW"}


def test_never_policy_entries_are_refused_before_any_read() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    for artifact_id in get_blocked_ids():
        entry = get_entry(artifact_id)
        assert entry is not None
        result = load_artifact(entry, root)
        assert result.status == ArtifactStatus.TOO_LARGE
        assert result.data is None
        assert result.provenance.schema_status == "BLOCKED_BY_POLICY"


def test_loading_policy_rows_count_every_policy() -> None:
    rows = page.build_loading_policy_rows()
    assert len(rows) == 4
    by_policy = {row["Policy"]: row for row in rows}
    blocked = by_policy["Blocked (never loaded)"]
    assert int(blocked["Registered artifacts"]) == len(get_blocked_ids())
    assert "never opens these files" in blocked["Rule"]
    safe = by_policy["Safe"]
    assert int(safe["Registered artifacts"]) == len(ARTIFACT_REGISTRY) - len(
        get_blocked_ids()
    )


def test_inventory_marks_blocked_entries_too_large_on_the_real_snapshot() -> None:
    snapshot = build_dashboard_snapshot()
    rows = {row["Artifact"]: row for row in page.build_inventory_rows(snapshot)}
    for artifact_id in get_blocked_ids():
        entry = get_entry(artifact_id)
        assert entry is not None
        row = rows[entry.name]
        assert row["Status"] == ArtifactStatus.TOO_LARGE.value
        assert row["Loading policy"] == "Blocked (never loaded)"
        assert row["Rows"] == "—"


# ---------------------------------------------------------------------------
# Preservation of the recorded RO3 convergence failure
# ---------------------------------------------------------------------------


def test_convergence_lines_are_shared_with_the_ablation_workspace() -> None:
    assert (
        page.build_ro3_convergence_lines
        is ablation_page.build_ro3_convergence_lines
    )


def test_recorded_convergence_failure_is_reported_as_recorded() -> None:
    snapshot = build_dashboard_snapshot()
    lines = page.build_ro3_convergence_lines(snapshot.ro3.convergence_summary or {})
    joined = " ".join(lines)
    assert "Primary transition passed its threshold: No." in joined
    assert "Failed comparisons at the primary transition: 142." in joined
    assert "Recorded decision: RO3 3 EVALUATE 2500." in joined


# ---------------------------------------------------------------------------
# Source hygiene: no paths, no hex, no inline styling, no snake_case ids
# ---------------------------------------------------------------------------


def test_no_raw_path_in_page_source() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "D:\\CMIDO" not in source
    assert "D:/CMIDO" not in source
    # Repository paths live only in the registry module, never in a page.
    assert "results/" not in source


def test_no_hex_color_literal_in_page_source() -> None:
    _assert_no_hex_in_source(page.__file__)


def test_page_uses_only_the_component_layer_for_styling() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "style=" not in source
    assert "<div" not in source
    assert "light-dark(" not in source


def test_unregistered_paths_live_only_in_constants() -> None:
    """Known paths may exist as constants; builders must never surface them."""
    snapshot = build_dashboard_snapshot()
    rows = page.build_unregistered_rows(pathlib.Path(__file__).resolve().parents[2])
    _assert_no_paths(rows)
    inventory = page.build_inventory_rows(snapshot)
    _assert_no_paths(inventory)


def test_real_snapshot_inventory_has_no_leaks() -> None:
    snapshot = build_dashboard_snapshot()
    rows = page.build_inventory_rows(snapshot)
    values = _row_values(rows)
    for value in values:
        assert not _SNAKE_RE.search(value), f"snake_case label leaked: {value}"
        assert "results/" not in value
        assert "\\" not in value


# ---------------------------------------------------------------------------
# Real-snapshot reconciliation of recorded counts
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_snapshot() -> DashboardSnapshot:
    return build_dashboard_snapshot()


def test_real_snapshot_statuses_reconcile(real_snapshot) -> None:
    overview = real_snapshot.overview
    assert overview.total_artifacts_registered == len(ARTIFACT_REGISTRY)
    assert (
        overview.total_artifacts_available
        + overview.total_artifacts_missing
        + overview.total_artifacts_invalid
        + len(get_blocked_ids())
        == len(ARTIFACT_REGISTRY)
    )
    assert overview.total_artifacts_missing == 0
    assert overview.total_artifacts_invalid == 0


def test_real_recorded_checks_report_their_recorded_totals(real_snapshot) -> None:
    rows = {r["Check source"]: r for r in page.build_recorded_check_rows(real_snapshot)}
    assert rows["8M ablation evidence gate"]["Recorded outcome"].startswith("20 of 20")
    assert rows["8S numerical reconciliation audit"]["Recorded outcome"].startswith(
        "81 of 81"
    )
    assert rows["RO3 final experimental integrity audit (step 39)"][
        "Recorded outcome"
    ].startswith("29 of 29")
    assert rows["9B real-project end-to-end gate"]["Recorded outcome"].startswith(
        "22 of 22"
    )
    assert rows["RO1 final integrity audit"]["Recorded outcome"] == (
        "Status recorded as PASS."
    )


def test_builders_accept_the_default_contract_object() -> None:
    """Contract integration: builders take DashboardSnapshot and stay safe."""
    empty = DashboardSnapshot()
    assert page.build_inventory_rows(empty)
    assert page.build_class_counts(empty) == {
        "OBS": 0,
        "DER": 0,
        "EST": 0,
        "SCN": 0,
    }
    assert page.build_status_counts(empty) == {}
    assert page.build_loading_policy_rows()
    assert page.build_provenance_legend_rows()[0]["Class"] == "OBS"
    assert len(page.build_concept_rows()) == 5


# ---------------------------------------------------------------------------
# Runtime render (AppTest) — the page must render end-to-end
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def provenance_app():
    from streamlit.testing.v1 import AppTest

    app_path = pathlib.Path(__file__).resolve().parents[2] / "apps" / "cmido_dashboard.py"
    at = AppTest.from_file(str(app_path), default_timeout=120)
    at.session_state["cmido_active_page"] = "provenance_integrity"
    at.run()
    return at


class TestProvenanceRuntime:
    def test_page_renders_without_exception(self, provenance_app) -> None:
        assert not provenance_app.exception

    def test_page_shows_the_major_sections(self, provenance_app) -> None:
        text = " ".join(str(m.value) for m in provenance_app.markdown)
        for section in (
            "Provenance and integrity evidence",
            "Registered artifact inventory",
            "Recorded fingerprints",
            "Recorded integrity checks",
            "Checks performed by this dashboard",
            "Loading policy and size restrictions",
            "Documented lineage",
            "Known evidence gaps",
            "How to read this evidence",
            "Handoff and open items",
        ):
            assert section in text, f"missing section: {section}"

    def test_page_separates_recorded_from_performed_checks(
        self, provenance_app
    ) -> None:
        text = " ".join(str(m.value) for m in provenance_app.markdown)
        assert "Reported, not re-run" in text
        assert "No SHA-256 digest is recomputed" in text
        assert "Performed at load time" in text
        assert "Not performed by this dashboard" in text

    def test_page_states_what_a_fingerprint_does_not_establish(
        self, provenance_app
    ) -> None:
        text = " ".join(str(m.value) for m in provenance_app.markdown)
        assert "does not independently establish scientific validity" in text
        assert "not registration" in text

    def test_page_surfaces_unregistered_evidence(self, provenance_app) -> None:
        text = " ".join(str(m.value) for m in provenance_app.markdown)
        assert "Present in the repository but not registered" in text
        assert "existence check performed by this page" in text
        # Table cells render as dataframes, not markdown: read them there.
        cell_values = [
            str(value)
            for frame in provenance_app.dataframe
            for value in frame.value.to_numpy().ravel().tolist()
        ]
        assert "Canonical PSLIB project JSON" in cell_values
        assert "Controller freeze manifest (step 36)" in cell_values
        assert "Real-project experiment output" in cell_values

    def test_page_preserves_separation_and_missing_metadata(
        self, provenance_app
    ) -> None:
        text = " ".join(str(m.value) for m in provenance_app.markdown)
        assert "never joined" in text
        assert "record no collection or creation dates" in text

    def test_page_reports_the_recorded_convergence_failure(
        self, provenance_app
    ) -> None:
        text = " ".join(str(m.value) for m in provenance_app.markdown)
        assert "Primary transition passed its threshold: No" in text
        assert "Failed comparisons at the primary transition: 142" in text

    def test_blocked_ledgers_are_shown_as_blocked(self, provenance_app) -> None:
        text = " ".join(str(m.value) for m in provenance_app.markdown)
        assert "NEVER auto-load" in text
        assert "Too large" in text

    def test_inventory_tables_render(self, provenance_app) -> None:
        assert len(provenance_app.dataframe) >= 8

    def test_no_snake_case_labels_leak_into_the_page(self, provenance_app) -> None:
        text = " ".join(str(m.value) for m in provenance_app.markdown)
        leaks = _SNAKE_RE.findall(text)
        assert leaks == [], f"snake_case labels leaked into the page: {leaks}"

    def test_no_filesystem_paths_leak_into_the_page(self, provenance_app) -> None:
        text = " ".join(str(m.value) for m in provenance_app.markdown)
        assert "D:\\CMIDO" not in text
        assert "\\results\\" not in text
        assert "results/" not in text
