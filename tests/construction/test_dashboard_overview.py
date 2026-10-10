"""10A.5 — Overview / Project Intelligence tests.

Covers the pure presentation builders in
``src/construction/dashboard_ui/overview.py``, the app's Overview wiring
markers, and end-to-end AppTest renders of the default project.

The tests assert the fabrication guards directly: values shown on Overview
must come from the loaded project or the existing deterministic engines, and
absent values must disappear or become explicit unavailable/partial states —
never placeholder zeros.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.construction.dashboard import build_dashboard_data
from src.construction.dashboard_ui import (
    build_evidence_status,
    build_overview_kpis,
    build_project_context_rows,
    build_publication_status,
    build_schedule_rows,
    build_status_board,
    deterministic_status,
    validate_shell,
)
from src.construction.dashboard_ui import navigation as nav
from src.construction.scheduling import calculate_total_float

PROJECT_PATH = Path("data/projects/cmido_demo_project.json")
APP_PATH = Path("apps/cmido_dashboard.py")


@pytest.fixture(scope="module")
def project() -> dict:
    return json.loads(PROJECT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def data(project: dict) -> dict:
    return build_dashboard_data(project)


@pytest.fixture(scope="module")
def float_rows(project: dict) -> list[dict]:
    return calculate_total_float(project)


def app_text() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def overview_markdown(at) -> str:
    return " ".join(str(markdown.value) for markdown in at.markdown)


# ---------------------------------------------------------------------------
# Project snapshot KPIs — values exist, zeros are never fabricated
# ---------------------------------------------------------------------------
class TestSnapshotKpis:
    def test_kpis_match_existing_engine_values(self, project: dict, data: dict) -> None:
        kpis = {item["label"]: item for item in build_overview_kpis(project, data)}
        overview = data["overview"]
        assert kpis["Project duration"]["value"] == overview["project_duration_days"]
        assert kpis["Project duration"]["unit"] == "d"
        assert kpis["Activities"]["value"] == overview["total_activities"]
        assert kpis["Critical activities"]["value"] == overview["critical_activities"]
        assert kpis["Material types"]["value"] == overview["total_material_types"]
        assert kpis["Suppliers"]["value"] == len(project["suppliers"])
        assert kpis["Project status"]["value"] == project["project"]["status"]

    def test_input_facts_are_marked_observed(self, project: dict, data: dict) -> None:
        kpis = {item["label"]: item for item in build_overview_kpis(project, data)}
        assert kpis["Suppliers"]["provenance"] == "OBS"
        assert kpis["Project status"]["provenance"] == "OBS"
        assert kpis["Project duration"]["provenance"] == "DER"

    def test_absent_source_values_are_omitted_not_zeroed(self) -> None:
        # Empty inputs produce no cards at all — never a row of placeholder zeros.
        assert build_overview_kpis({}, {"overview": {}}) == []

    def test_partial_overview_only_reports_known_fields(self) -> None:
        kpis = build_overview_kpis({}, {"overview": {"project_duration_days": 12}})
        assert [item["label"] for item in kpis] == ["Project duration"]
        assert kpis[0]["value"] == 12

    def test_absent_supplier_key_is_omitted(self, project: dict) -> dict:
        trimmed = dict(project)
        del trimmed["suppliers"]
        labels = [item["label"] for item in build_overview_kpis(trimmed, {"overview": {}})]
        assert "Suppliers" not in labels

    def test_none_value_is_omitted_even_when_key_exists(self) -> None:
        kpis = build_overview_kpis({}, {"overview": {"total_activities": None}})
        assert kpis == []


# ---------------------------------------------------------------------------
# Project context — declared inputs only, no raw objects
# ---------------------------------------------------------------------------
class TestProjectContext:
    def test_context_matches_declared_inputs(self, project: dict) -> None:
        rows = dict(build_project_context_rows(project, "cmido_demo_project.json", r"D:\x\p.json"))
        meta = project["project"]
        assert rows["Project ID"] == meta["project_id"]
        assert rows["Project name"] == meta["project_name"]
        assert rows["Project type"] == meta["project_type"]
        assert rows["Location"] == meta["location"]
        assert rows["Status"] == meta["status"]
        assert rows["Start date"] == meta["start_date"]
        assert rows["Planned end date"] == meta["planned_end_date"]
        expected_horizon = (
            date.fromisoformat(meta["planned_end_date"]) - date.fromisoformat(meta["start_date"])
        ).days
        assert rows["Planned horizon (days)"] == str(expected_horizon)
        assert rows["Calendar"] == project["calendar"]["name"]
        assert rows["Activities (inputs)"] == str(len(project["activities"]))
        assert rows["Dependencies (inputs)"] == str(len(project["dependencies"]))
        assert rows["Materials (inputs)"] == str(len(project["materials"]))
        assert rows["Suppliers (inputs)"] == str(len(project["suppliers"]))
        assert rows["Supplier-material links (inputs)"] == str(len(project["supplier_materials"]))

    def test_source_label_distinguishes_upload_from_bundle(self, project: dict) -> None:
        uploaded = dict(build_project_context_rows(project, "my_project.json", "uploaded"))
        bundled = dict(build_project_context_rows(project, "cmido_demo_project.json", r"D:\x"))
        assert "uploaded in this session" in uploaded["Source"]
        assert "bundled project file" in bundled["Source"]

    def test_context_values_are_plain_text(self, project: dict) -> None:
        for field, value in build_project_context_rows(project, "x.json", "uploaded"):
            assert isinstance(field, str)
            assert isinstance(value, str)
            assert "{" not in value and "}" not in value, f"{field} exposed a raw object"

    def test_empty_project_yields_no_rows(self) -> None:
        assert build_project_context_rows({}, None, None) == []


# ---------------------------------------------------------------------------
# Schedule intelligence — engine rows only, partial timing dropped
# ---------------------------------------------------------------------------
class TestScheduleRows:
    def test_rows_cover_every_activity(self, data: dict, float_rows: list[dict]) -> None:
        rows = build_schedule_rows(data["schedule"]["activities"], float_rows)
        assert len(rows) == len(data["schedule"]["activities"])

    def test_full_timing_includes_float_columns(self, data: dict, float_rows: list[dict]) -> None:
        rows = build_schedule_rows(data["schedule"]["activities"], float_rows)
        expected = {
            "Activity",
            "Name",
            "Duration (d)",
            "Critical",
            "Early start (d)",
            "Early finish (d)",
            "Total float (d)",
        }
        assert set(rows[0]) == expected
        engine = {row["activity_id"]: row for row in float_rows}
        first = rows[0]
        assert first["Early start (d)"] == engine[first["Activity"]]["es"]
        assert first["Total float (d)"] == engine[first["Activity"]]["total_float"]

    def test_criticality_matches_engine_flags(self, data: dict, float_rows: list[dict]) -> None:
        rows = build_schedule_rows(data["schedule"]["activities"], float_rows)
        flags = {row["activity_id"]: row["is_critical"] for row in data["schedule"]["activities"]}
        for row in rows:
            assert row["Critical"] == ("YES" if flags[row["Activity"]] else "NO")

    def test_missing_floats_keep_duration_without_fabrication(self, data: dict) -> None:
        rows = build_schedule_rows(data["schedule"]["activities"], None)
        assert set(rows[0]) == {"Activity", "Name", "Duration (d)", "Critical"}
        assert all("Total float (d)" not in row for row in rows)

    def test_partial_timing_is_dropped_entirely(self, data: dict, float_rows: list[dict]) -> None:
        # Timing for only some activities must not become empty cells or zeros.
        rows = build_schedule_rows(data["schedule"]["activities"], float_rows[:3])
        assert set(rows[0]) == {"Activity", "Name", "Duration (d)", "Critical"}


# ---------------------------------------------------------------------------
# Evidence status — honest counts, planned stays planned
# ---------------------------------------------------------------------------
def snapshot(registered=28, available=26, missing=0, invalid=0) -> dict:
    return {
        "total_artifacts_registered": registered,
        "total_artifacts_available": available,
        "total_artifacts_missing": missing,
        "total_artifacts_invalid": invalid,
    }


class TestEvidenceStatus:
    def test_partial_when_available_below_registered(self) -> None:
        rows, overall, note = build_evidence_status(
            snapshot(), real_world_planned=True, ro_workspaces_planned=True
        )
        assert overall == "partial"
        status = dict(rows)
        assert status["Project data"] == "valid"
        assert status["Dashboard snapshot"] == "valid"
        assert status["Real-world data workspace"] == "optional"
        assert status["RO1/RO2/RO3 workspaces"] == "optional"
        artifact_label = next(label for label, _ in rows if label.startswith("Research evidence"))
        assert "26 of 28" in artifact_label
        assert status[artifact_label] == "partial"
        assert "26 of 28 registered artifacts available" in note
        assert "0 missing" in note and "0 invalid" in note

    def test_fully_available_snapshot_is_valid(self) -> None:
        _, overall, _ = build_evidence_status(
            snapshot(registered=28, available=28), real_world_planned=False, ro_workspaces_planned=False
        )
        assert overall == "valid"

    def test_invalid_artifacts_dominate_the_status(self) -> None:
        _, overall, _ = build_evidence_status(
            snapshot(available=26, invalid=2), real_world_planned=False, ro_workspaces_planned=False
        )
        assert overall == "invalid"

    def test_missing_snapshot_reports_missing_not_zero(self) -> None:
        rows, overall, note = build_evidence_status(
            None, real_world_planned=True, ro_workspaces_planned=True
        )
        assert overall == "missing"
        status = dict(rows)
        assert status["Dashboard snapshot"] == "missing"
        assert status["Research evidence artifacts"] == "missing"
        assert "unavailable" in note
        assert not any("(0 of" in label for label, _ in rows), "missing data must not read as zero counts"

    def test_planned_workspaces_never_inflate_the_overall_status(self) -> None:
        _, overall, _ = build_evidence_status(
            snapshot(registered=28, available=28),
            real_world_planned=True,
            ro_workspaces_planned=True,
        )
        assert overall == "valid"

    def test_status_board_renders_every_row(self) -> None:
        rows = [
            ("Deterministic schedule analysis", "valid"),
            ("Resource feasibility (availability inputs)", "optional"),
            ("Research evidence artifacts", "partial"),
            ("RO1/RO2/RO3 research workspaces", "optional"),
        ]
        html = build_publication_status(title="Status board", rows=rows, status="partial", note="x")
        for label, _ in rows:
            assert label in html


# ---------------------------------------------------------------------------
# Status layers stay separate
# ---------------------------------------------------------------------------
class TestStatusLayers:
    def test_deterministic_status_reports_engine_values(self, data: dict) -> None:
        status, message = deterministic_status(data)
        assert status == "valid"
        assert f"{data['overview']['project_duration_days']} d project duration" in message
        assert "Resource feasibility" in message
        assert "not evaluated" in message

    def test_deterministic_status_is_missing_without_analysis(self) -> None:
        status, _ = deterministic_status({})
        assert status == "missing"

    def test_status_board_keeps_three_layers_separate(self) -> None:
        overall, rows = build_status_board("valid", "partial")
        assert overall == "partial"
        assert [label for label, _ in rows] == [
            "Deterministic schedule analysis",
            "Resource feasibility (availability inputs)",
            "Research evidence artifacts",
            "RO1/RO2/RO3 research workspaces",
        ]
        statuses = dict(rows)
        assert statuses["Deterministic schedule analysis"] == "valid"
        assert statuses["Research evidence artifacts"] == "partial"
        # Planned layers are labelled, not scored.
        assert statuses["RO1/RO2/RO3 research workspaces"] == "optional"


# ---------------------------------------------------------------------------
# App wiring and boundary markers (static)
# ---------------------------------------------------------------------------
class TestOverviewAppWiring:
    def test_app_wires_every_overview_builder(self) -> None:
        text = app_text()
        for marker in (
            "build_overview_kpis",
            "build_project_context_rows",
            "build_schedule_rows",
            "build_evidence_status",
            "deterministic_status",
            "build_status_board",
            "calculate_total_float",
            "schedule_timeline",
            "render_overview(project, data, source_name, source_path)",
        ):
            assert marker in text, f"app must wire {marker}"

    def test_overview_is_routed_through_the_registry(self) -> None:
        assert nav.resolve_page("Overview") == "overview"
        page = nav.page_by_id("overview")
        assert page.group == "CORE"
        assert page.is_available
        assert "legacy_route_for" in app_text()

    def test_app_has_no_raw_artifact_reads(self) -> None:
        text = app_text()
        for token in ("RO3_step32", "rglob", ".csv"):
            assert token not in text, f"Overview app must not touch {token!r}"
        assert text.count("cached_snapshot(") >= 1, "evidence must come through the cached snapshot"

    def test_app_introduces_no_new_css_system(self) -> None:
        text = app_text()
        assert "<style" not in text
        assert "@import" not in text

    def test_overview_module_is_pure_presentation(self) -> None:
        text = Path("src/construction/dashboard_ui/overview.py").read_text(encoding="utf-8")
        assert "streamlit" not in text
        assert "plotly" not in text
        for token in (
            "src.construction.simulation",
            "src.construction.uncertainty",
            "src.construction.experiments",
            "resource_dashboard",
            "integrated_analysis",
            "src.construction.scheduling",
            "results/",
        ):
            assert token not in text, f"overview builders must not import {token}"

    def test_dashboard_ui_has_no_research_engine_imports(self) -> None:
        forbidden = (
            "from src.construction.simulation",
            "from src.construction.uncertainty",
            "from src.construction.experiments",
            "resource_dashboard",
            "integrated_analysis",
            "from ..scheduling",
            "from src.construction.scheduling",
            "results/",
        )
        offenders = []
        for path in sorted(Path("src/construction/dashboard_ui").glob("*.py")):
            source = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in source:
                    offenders.append(f"{path.name}: {token}")
        assert offenders == []

    def test_shell_registry_still_valid_after_10a5_description_change(self) -> None:
        assert validate_shell() == []


# ---------------------------------------------------------------------------
# Runtime render (AppTest)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def overview_app():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH.resolve()), default_timeout=90)
    at.session_state["cmido_active_page"] = "overview"
    at.session_state["10a5_sentinel"] = "kept"
    at.run()
    assert not at.exception
    return at


class TestOverviewRuntime:
    def test_overview_renders_without_exception(self, overview_app) -> None:
        assert not overview_app.exception

    def test_project_identity_is_shown_first(self, overview_app) -> None:
        text = overview_markdown(overview_app)
        assert "Loaded project" in text
        assert "Residential Building Demo" in text
        assert "bundled project file" in text

    def test_breadcrumb_matches_the_registry(self, overview_app) -> None:
        assert nav.breadcrumb_for("overview") == [nav.theme.APP_NAME, "Core", "Overview"]
        text = overview_markdown(overview_app)
        assert "cmido-breadcrumb" in text
        assert "Overview" in text

    def test_snapshot_section_renders_existing_metrics(self, overview_app, data: dict) -> None:
        text = overview_markdown(overview_app)
        assert "Project snapshot" in text
        for label in ("Project duration", "Activities", "Critical activities", "Material types"):
            assert f'cmido-kpi-label">{label}' in text
        assert str(data["overview"]["project_duration_days"]) in text

    def test_project_context_section_renders(self, overview_app) -> None:
        text = overview_markdown(overview_app)
        assert "Project context" in text
        assert "Project input context" in text

    def test_schedule_section_and_critical_path_available(self, overview_app) -> None:
        text = overview_markdown(overview_app)
        assert "Schedule intelligence" in text
        assert "Activity schedule structure" in text
        assert "Deterministic critical path" in text
        assert "Critical path:" in text

    def test_timeline_and_3d_graph_render(self, overview_app) -> None:
        text = overview_markdown(overview_app)
        assert "Schedule progression" in text
        assert "Project intelligence graph" in text
        assert "3D project dependency graph" in text

    def test_resource_feasibility_is_not_fabricated(self, overview_app) -> None:
        text = overview_markdown(overview_app)
        assert "Resource feasibility not evaluated" in text
        # The state must not appear as a KPI card with a placeholder number.
        assert 'cmido-kpi-label">Resource feasibility' not in text

    def test_evidence_and_status_sections_are_honest(self, overview_app) -> None:
        text = overview_markdown(overview_app)
        # HTML builders escape "&" as "&amp;" — assert the rendered form.
        assert "Evidence &amp; data status" in text
        assert "Evidence readiness" in text
        assert "Real-world data workspace" in text
        assert "RO1/RO2/RO3 workspaces" in text
        assert "Project status" in text
        assert "Status board" in text
        assert "Deterministic project state" in text

    def test_material_and_pipeline_sections_render(self, overview_app) -> None:
        text = overview_markdown(overview_app)
        assert "Material &amp; resource intelligence" in text
        assert "Material demand summary" in text
        assert "CMIDO analytical pipeline" in text
        assert "Decision Intelligence" in text

    def test_session_state_and_navigation_roundtrip(self) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_PATH.resolve()), default_timeout=90)
        at.session_state["cmido_active_page"] = "overview"
        at.session_state["10a5_sentinel"] = "kept"
        at.run()
        assert not at.exception
        assert "Residential Building Demo" in overview_markdown(at)

        at.session_state["cmido_active_page"] = "schedule"
        at.run()
        assert not at.exception
        text = overview_markdown(at)
        assert "Schedule" in text and "Critical Path" in text
        assert "Schedule snapshot" in text
        assert "Critical path" in text

        at.session_state["cmido_active_page"] = "overview"
        at.run()
        assert not at.exception
        text = overview_markdown(at)
        assert "Residential Building Demo" in text
        assert "Project snapshot" in text
        # Nothing else in session state was reset by visiting Overview.
        assert at.session_state["10a5_sentinel"] == "kept"

    def test_planned_page_still_shows_honest_placeholder(self) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_PATH.resolve()), default_timeout=90)
        # RO1 ships in 10A.7, RO2 in 10A.8 and RO3 in 10A.9; all three research
        # stages are now available, so procurement_decisions (10A.10) is the
        # planned placeholder exemplar.
        at.session_state["cmido_active_page"] = "procurement_decisions"
        at.run()
        assert not at.exception
        assert "Planned workspace" in overview_markdown(at)
