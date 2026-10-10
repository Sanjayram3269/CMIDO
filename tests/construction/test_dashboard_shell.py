"""10A.4 — application shell and navigation tests.

These tests cover the dashboard shell only: the page registry, the four research
groups, routing, breadcrumbs, active-state HTML, the future-page placeholder
policy and the preservation of the existing dashboard contract. They do not run
any research engine and do not read any artifact.

Any values used here are registry / presentation fixtures chosen to exercise the
shell — they are not CMIDO research results.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.construction.dashboard_ui import navigation as nav
from src.construction.dashboard_ui import (
    ImplementationStatus,
    NAV_SESSION_KEY,
    PageDefinition,
    PAGES,
    Provenance,
    ResearchStage,
    build_future_page_panel,
    breadcrumb_for,
    group_for,
    page_by_id,
    page_description,
    page_future_phase,
    page_group_label,
    page_is_available,
    page_is_planned,
    page_title,
    page_placeholder_reason,
    page_research_stage,
    pagelist,
    pages,
    pages_in_group,
    resolve_page,
    resolve_page_title,
    page_by_route,
)
from src.construction.dashboard_ui.components import (
    nav_breadcrumb,
    render_active_nav_item,
)


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------

class TestPageRegistry:
    def test_registry_is_nonempty(self) -> None:
        assert PAGES

    def test_every_page_has_stable_id(self) -> None:
        for page in pages():
            assert page.id
            assert page.id == page.id.strip()

    def test_page_ids_are_unique(self) -> None:
        ids = [page.id for page in pages()]
        assert len(ids) == len(set(ids))

    def test_page_slugs_are_unique(self) -> None:
        slugs = [page.slug for page in pages()]
        assert len(slugs) == len(set(slugs))

    def test_page_slugs_are_widget_safe(self) -> None:
        for page in pages():
            # slugs must be usable as Streamlit widget keys
            assert page.slug
            assert page.slug.replace("_", "").isalnum()

    def test_pages_are_ordered_by_group_then_registry(self) -> None:
        expected: list[str] = []
        for group in nav.nav_groups():
            expected.extend(page.id for page in pages_in_group(group.key))
        assert [page.id for page in pages()] == expected

    def test_groups_are_four_and_ordered(self) -> None:
        group_keys = [group.key for group in nav.nav_groups()]
        assert group_keys == ["CORE", "RESEARCH", "DECISION", "EVIDENCE"]

    def test_each_group_has_label_and_caption(self) -> None:
        for group in nav.nav_groups():
            assert group.label.strip()
            assert group.caption.strip()

    def test_all_pages_belong_to_a_known_group(self) -> None:
        valid_groups = {group.key for group in nav.nav_groups()}
        for page in pages():
            assert page.group in valid_groups

    def test_available_pages_have_a_route_for_the_existing_dispatch(self) -> None:
        for page in pages():
            if page.is_available:
                assert page.route.strip(), f"available page {page.id!r} has no route"

    def test_route_lookup_roundtrips_to_page_id(self) -> None:
        for page in pages():
            if page.route:
                assert nav.page_by_route(page.route).id == page.id

    def test_shell_is_valid(self) -> None:
        assert nav.validate_shell() == []


class TestExistingPagesPreserved:
    """The seven existing dashboard pages must still be present and reachable."""

    LEGACY_ROUTES = {
        "Overview",
        "3D Project Graph",
        "Schedule",
        "Materials & Resources",
        "Risk & Scenarios",
        "Experiment Lab",
        "Research Evidence",
    }

    def test_all_legacy_routes_are_registered(self) -> None:
        routes = {page.route for page in pages() if page.route}
        for route in self.LEGACY_ROUTES:
            assert route in routes, f"legacy route {route!r} is missing from the registry"

    def test_each_legacy_route_maps_to_an_available_page(self) -> None:
        for page in pages():
            if page.route in self.LEGACY_ROUTES:
                assert page.is_available, f"{page.route!r} must remain an available page"
                # Slug for legacy routes must be stable for widget keys.
                assert page.slug

    def test_existing_page_ids_are_stable(self) -> None:
        expected_ids = {
            "overview",
            "graph_3d",
            "schedule",
            "materials",
            "scenarios",
            "experiment_lab",
            "evidence",
        }
        ids = {page.id for page in pages() if page.is_available}
        assert expected_ids <= ids

    def test_legacy_evidence_route_still_resolves(self) -> None:
        # The legacy dispatch still uses "Research Evidence" as a route title.
        # That route must resolve to the live EVIDENCE-group evidence page.
        page = page_by_route("Research Evidence")
        assert page.is_available
        assert page.group == "EVIDENCE"
        assert page.route == "Research Evidence"
        assert resolve_page("Research Evidence") == "evidence"


class TestNavigationGroups:
    def test_core_contains_orientation_pages(self) -> None:
        core = pages_in_group("CORE")
        titles = {page.title for page in core}
        assert "Overview" in titles
        # Project Intelligence is served by the 3D Project Graph page.
        assert "3D Project Graph" in titles
        assert "Schedule & Critical Path" in titles
        assert "Materials & Resources" in titles

    def test_decision_contains_planner_pages(self) -> None:
        decision = pages_in_group("DECISION")
        titles = {page.title for page in decision}
        assert "Scenario Lab" in titles
        assert "Procurement Decisions" in titles
        assert "Resilience & Stress" in titles
        # Deterministic planner pages belong to CORE in the intended IA.
        assert "Schedule & Critical Path" not in titles
        assert "Materials & Resources" not in titles

    def test_research_contains_research_placeholders(self) -> None:
        research = pages_in_group("RESEARCH")
        titles = {page.title for page in research}
        assert "RO1 · Forecasting" in titles
        assert "RO2 · Uncertainty" in titles
        assert "RO3 · Optimization" in titles
        # Experiments is an EVIDENCE destination in the intended IA.
        assert "Experiments" not in titles

    def test_evidence_contains_live_evidence_and_placeholders(self) -> None:
        evidence = pages_in_group("EVIDENCE")
        titles = {page.title for page in evidence}
        assert "Research Evidence" in titles
        assert "Experiments" in titles
        assert "Real-World Data" in titles
        assert "Ablation & Robustness" in titles
        assert "Provenance & Integrity" in titles

    def test_group_label_matches_group_key(self) -> None:
        for group in nav.nav_groups():
            assert group.label.strip()
            assert group.key == group.key.upper()


class TestRoutingAndPlaceholders:
    def test_resolve_page_none_returns_default(self) -> None:
        assert resolve_page(None) == nav.DEFAULT_PAGE

    def test_resolve_page_empty_returns_default(self) -> None:
        assert resolve_page("") == nav.DEFAULT_PAGE

    def test_resolve_page_unknown_returns_default(self) -> None:
        assert resolve_page("not a page") == nav.DEFAULT_PAGE

    def test_resolve_page_accepts_page_id(self) -> None:
        assert resolve_page("scenarios") == "scenarios"

    def test_resolve_page_accepts_legacy_route(self) -> None:
        assert resolve_page("Risk & Scenarios") == "scenarios"

    def test_resolve_page_title_none_returns_default_title(self) -> None:
        title = resolve_page_title(None)
        default_page = page_by_id(nav.DEFAULT_PAGE)
        assert title == default_page.title

    def test_available_pages_are_not_planned(self) -> None:
        for page in pages():
            if page.is_available:
                assert not page.is_planned

    def test_future_pages_are_planned(self) -> None:
        for page in pages():
            if page.is_planned:
                assert not page.is_available
                assert page.research_stage
                assert page.description.strip()
                assert page.future_phase

    def test_future_pages_name_their_phase(self) -> None:
        for page in pages():
            if page.is_planned:
                assert page.future_phase, f"planned page {page.id!r} must name its phase"

    def test_ro1_page_is_now_available(self) -> None:
        page = page_by_id("ro1_forecasting")
        assert page.is_available
        assert not page.is_planned
        assert page.route == "RO1 · Forecasting"
        assert page.provenance == "EST"

    def test_no_future_page_is_mistakenly_available(self) -> None:
        for page in pages():
            assert page.is_available != page.is_planned

    def test_ro2_page_is_now_available(self) -> None:
        page = page_by_id("ro2_uncertainty")
        assert page.is_available
        assert not page.is_planned
        assert page.group == "RESEARCH"
        assert page.research_stage == ResearchStage.RO2.value
        assert page.route == "RO2 · Uncertainty"

    def test_provenance_placeholder_is_in_evidence(self) -> None:
        page = page_by_id("provenance_integrity")
        assert page.is_planned
        assert page.group == "EVIDENCE"
        assert page.research_stage == ResearchStage.EVIDENCE.value
        assert page.future_phase


class TestBreadcrumbs:
    def test_breadcrumb_is_three_levels(self) -> None:
        trail = breadcrumb_for("overview")
        assert trail == [nav.theme.APP_NAME, "Core", "Overview"]

    def test_breadcrumb_uses_group_label(self) -> None:
        trail = breadcrumb_for("scenarios")
        assert trail == [nav.theme.APP_NAME, "Decision", "Scenario Lab"]

    def test_breadcrumb_for_future_page_uses_group_and_title(self) -> None:
        trail = breadcrumb_for("ro2_uncertainty")
        assert trail == [nav.theme.APP_NAME, "Research", "RO2 · Uncertainty"]

    def test_nav_breadcrumb_matches_registry_breadcrumb(self) -> None:
        for page in pages():
            assert nav_breadcrumb(page.id) == breadcrumb_for(page.id)

    def test_breadcrumb_for_unknown_page_falls_back_to_default(self) -> None:
        trail = breadcrumb_for("not a page")
        default_page = page_by_id(nav.DEFAULT_PAGE)
        assert trail == [nav.theme.APP_NAME, page_group_label(nav.DEFAULT_PAGE), default_page.title]

    def test_breadcrumb_from_page_id_matches_route_based_resolution(self) -> None:
        # The legacy dispatch resolves "Risk & Scenarios" to the scenarios page.
        assert breadcrumb_for("Risk & Scenarios") == breadcrumb_for("scenarios")


class TestActiveStateAndShellHTML:
    def test_active_nav_item_marks_the_current_page(self) -> None:
        # render_active_nav_item must emit active-class HTML for the chosen page.
        # The Streamlit markdown output is not easily captured here, so we assert at the
        # builder level: the active item HTML must carry the active class.
        page = page_by_id("scenarios")
        from src.construction.dashboard_ui.navigation import build_nav_item_html

        html = build_nav_item_html(page, active=True)
        assert "cmido-nav-item--active" in html
        assert 'data-slug="scenarios"' in html
        assert "Scenario Lab" in html

    def test_active_nav_item_uses_page_html_helper(self) -> None:
        # The rendered active item must be built through build_nav_item_html so it stays
        # consistent with the registry (slug, group, display label).
        from src.construction.dashboard_ui.navigation import build_nav_item_html

        page = page_by_id("materials")
        html = build_nav_item_html(page, active=True)
        assert 'data-slug="materials"' in html
        assert "Materials" in html
        assert "cmido-nav-item--active" in html

    def test_nav_legend_lists_all_four_groups(self) -> None:
        from src.construction.dashboard_ui.navigation import build_nav_legend

        legend = build_nav_legend()
        for group in nav.nav_groups():
            assert group.label in legend


class TestPlaceholderPolicy:
    def test_future_page_panel_is_honest(self) -> None:
        panel = build_future_page_panel("ro3_optimization")
        # No fabricated numbers, charts or KPIs.
        assert "RO3 · Optimization" in panel
        assert "Research stage" in panel
        assert "Delivery" in panel
        # Explicitly not a completed research result
        assert "planned" in panel.lower()

    def test_future_page_panel_mentions_the_phase(self) -> None:
        panel = build_future_page_panel("ro3_optimization")
        assert page_future_phase("ro3_optimization") in panel

    def test_future_page_panel_does_not_contain_numbers_that_look_like_results(self) -> None:
        panel = build_future_page_panel("ro3_optimization")
        # Guard against accidental fabrication; the panel should not claim a numeric result.
        for token in ("95%", "confidence interval", "mean project delay", "bootstrap"):
            assert token.lower() not in panel.lower()

    def test_future_page_panel_requires_a_planned_page(self) -> None:
        available = page_by_id("overview")
        assert available.is_available
        # build_future_page_panel guards against calling it for available pages.
        with pytest.raises(AssertionError):
            build_future_page_panel("overview")

    def test_placeholder_reason_is_nonempty_for_planned_pages(self) -> None:
        for page in pages():
            if page.is_planned:
                assert page_placeholder_reason(page.id)


class TestRegistryDerivedHelpers:
    def test_page_title_matches_registry_title(self) -> None:
        for page in pages():
            assert page_title(page.id) == page.title

    def test_page_group_label_matches_group_label(self) -> None:
        for page in pages():
            assert page_group_label(page.id) == nav.group_for(page.id).label

    def test_page_description_returns_description(self) -> None:
        for page in pages():
            assert page_description(page.id) == page.description

    def test_page_research_stage_matches_registry(self) -> None:
        for page in pages():
            if page.research_stage is None:
                assert page_research_stage(page.id) is None
            else:
                assert page_research_stage(page.id) == page.research_stage

    def test_page_future_phase_returns_phase_for_planned_pages(self) -> None:
        for page in pages():
            if page.is_planned:
                assert page_future_phase(page.id) == page.future_phase

    def test_page_is_available_matches_registry(self) -> None:
        for page in pages():
            assert page_is_available(page.id) == page.is_available

    def test_page_is_planned_matches_registry(self) -> None:
        for page in pages():
            assert page_is_planned(page.id) == page.is_planned


class TestSessionStateHelpers:
    def test_current_page_from_session_defaults_safely(self) -> None:
        assert nav.current_page_from_session(None) == nav.DEFAULT_PAGE

    def test_set_current_page_stores_resolved_id(self) -> None:
        class FakeSession(dict):
            pass

        session = FakeSession()
        nav.set_current_page(session, "not a page")
        assert session[NAV_SESSION_KEY] == nav.DEFAULT_PAGE

    def test_set_current_page_accepts_page_id(self) -> None:
        class FakeSession(dict):
            pass

        session = FakeSession()
        nav.set_current_page(session, "experiment_lab")
        assert session[NAV_SESSION_KEY] == "experiment_lab"


class TestNoFabricatedResearchDataInShell:
    def test_placeholder_helper_does_not_invent_metrics(self) -> None:
        # RO1 ships in 10A.7 and RO2 in 10A.8; RO3 remains planned and must stay honest.
        panel = build_future_page_panel("ro3_optimization")
        forbidden = ("MAE", "RMSE", "95%", "bootstrap", "mean project delay", "shortage")
        lowered = panel.lower()
        for token in forbidden:
            assert token.lower() not in lowered, f"placeholder panel must not fabricate {token!r}"

    def test_shell_imports_do_not_import_research_engines(self) -> None:
        forbidden = (
            "src.construction.simulation",
            "src.construction.uncertainty",
            "src.construction.experiments",
            "src.construction.resource_dashboard",
        )
        offenders = []
        for path in (
            Path("src/construction/dashboard_ui/navigation.py"),
            Path("src/construction/dashboard_ui/components.py"),
        ):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if f"import {token}" in text:
                    offenders.append(f"{path.name}: {token}")
        assert offenders == []

    def test_shell_does_not_contain_research_numbers(self) -> None:
        for path in (
            Path("src/construction/dashboard_ui/navigation.py"),
            Path("src/construction/dashboard_ui/components.py"),
        ):
            text = path.read_text(encoding="utf-8")
            # Heuristic: the shell should not hard-code research metrics like scenario counts.
            for token in ("scenario_count", "total_artifacts_registered", "mean_project_delay"):
                assert token not in text, f"{path.name} must not hard-code {token}"


class TestLegacyAppContractPreserved:
    """The existing dashboard contract markers must still be present in the app."""

    APP_PATH = Path("apps/cmido_dashboard.py")

    @pytest.fixture(autouse=True)
    def _app_text(self) -> str:
        return self.APP_PATH.read_text(encoding="utf-8")

    def test_app_still_imports_research_engines(self, _app_text: str) -> None:
        for marker in (
            "build_dashboard_data",
            "build_resource_dashboard",
            "analyze_schedule_impact",
            "build_uncertainty_context",
            "run_real_dataset_experiment",
            "build_statistical_analysis",
        ):
            assert marker in _app_text, f"app must still import {marker}"

    def test_app_still_hasm_the_existing_page_labels(self, _app_text: str) -> None:
        for label in ("Run scenario", "Execute experiment", "Experiment Lab"):
            assert label in _app_text, f"app must still expose {label!r}"

    def test_app_still_wires_the_10a2b_snapshot(self, _app_text: str) -> None:
        assert "cached_snapshot" in _app_text
        assert "build_dashboard_snapshot" in _app_text

    def test_app_still_wires_scenario_and_experiment_flows(self, _app_text: str) -> None:
        assert "analyze_schedule_impact" in _app_text
        assert "ExperimentConfig" in _app_text

    def test_app_shell_still_validates_the_registry(self, _app_text: str) -> None:
        assert "validate_shell" in _app_text
        assert "Navigation registry" in _app_text or "registry" in _app_text.lower()

    def test_app_streams_the_future_page_panel_for_planned_pages(self, _app_text: str) -> None:
        assert "render_future_page_panel" in _app_text

    def test_app_page_header_uses_page_registry_metadata(self, _app_text: str) -> None:
        assert "page_title" in _app_text
        assert "page_description" in _app_text
        assert "page_research_stage" in _app_text


class TestIntendedIACoverage:
    """The 15-destination information architecture the shell must expose.

    Project Intelligence is intentionally served by the existing 3D Project
    Graph page (documented alias); every other destination maps one to one.
    """

    INTENDED_IA = {
        "CORE": [
            "Overview",
            "Project Intelligence",
            "Schedule & Critical Path",
            "Materials & Resources",
        ],
        "RESEARCH": ["RO1 · Forecasting", "RO2 · Uncertainty", "RO3 · Optimization"],
        "DECISION": ["Scenario Lab", "Procurement Decisions", "Resilience & Stress"],
        "EVIDENCE": [
            "Real-World Data",
            "Experiments",
            "Ablation & Robustness",
            "Research Evidence",
            "Provenance & Integrity",
        ],
    }
    ALIASES = {"Project Intelligence": "3D Project Graph"}

    def test_every_intended_destination_is_registered_in_its_group(self) -> None:
        for group_key, intended in self.INTENDED_IA.items():
            expected = {self.ALIASES.get(title, title) for title in intended}
            actual = {page.title for page in pages_in_group(group_key)}
            assert actual == expected, f"{group_key} registry drifted from the intended IA"

    def test_registry_counts_match_the_intended_ia(self) -> None:
        assert len(pages()) == 15
        assert sum(1 for page in pages() if page.is_available) == 9
        assert sum(1 for page in pages() if page.is_planned) == 6
        counts = {group.key: len(pages_in_group(group.key)) for group in nav.nav_groups()}
        assert counts == {"CORE": 4, "RESEARCH": 3, "DECISION": 3, "EVIDENCE": 5}

    def test_planned_destinations_are_honest_placeholders(self) -> None:
        planned_ids = {
            "ro3_optimization",
            "procurement_decisions",
            "resilience_stress",
            "real_world_data",
            "ablation_robustness",
            "provenance_integrity",
        }
        assert "ro1_forecasting" not in planned_ids
        assert "ro2_uncertainty" not in planned_ids
        for page_id in planned_ids:
            assert page_placeholder_reason(page_id)
        for page_id in planned_ids:
            assert page_placeholder_reason(page_id)


@pytest.mark.parametrize("page_id,expected_group", [
    ("overview", "CORE"),
    ("graph_3d", "CORE"),
    ("schedule", "CORE"),
    ("materials", "CORE"),
    ("scenarios", "DECISION"),
    ("procurement_decisions", "DECISION"),
    ("resilience_stress", "DECISION"),
    ("experiment_lab", "EVIDENCE"),
    ("ro1_forecasting", "RESEARCH"),
    ("ro2_uncertainty", "RESEARCH"),
    ("ro3_optimization", "RESEARCH"),
    ("evidence", "EVIDENCE"),
    ("real_world_data", "EVIDENCE"),
    ("ablation_robustness", "EVIDENCE"),
    ("provenance_integrity", "EVIDENCE"),
])
def test_page_group_membership(page_id: str, expected_group: str) -> None:
    page = page_by_id(page_id)
    assert page.group == expected_group
    assert page_group_label(page_id) == nav.group_for(page_id).label