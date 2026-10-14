"""Regression tests for the External Data dashboard page.

Covers what the headless AppTest surface can verify reliably: route
registration, render without exception, presence of the uploader and run
control, and the honest \"unavailable research stages\" section.

Driving the actual ``file_uploader`` widget is not reliable through AppTest in
this Streamlit version, so the full upload -> run -> export flow is exercised in
the browser end-to-end tests (Phase 3) against a real running server.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.construction.dashboard_ui.navigation import (  # noqa: E402
    page_by_id,
    pages,
    page_is_planned,
)

APP_PATH = ROOT / "apps" / "cmido_dashboard.py"
FIXTURE = ROOT / "examples" / "external_data" / "forecast_intervals_fixture.csv"

pytest.importorskip("streamlit", reason="streamlit not installed")


def _app(page_id: str):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=180)
    at.session_state["cmido_active_page"] = page_id
    return at


class TestExternalDataRoute:
    def test_route_is_registered_and_available(self) -> None:
        page = page_by_id("external_data")
        assert page.route == "page/external_data"
        assert page.group == "EVIDENCE"
        assert not page.is_planned
        assert page_is_planned("external_data") is False

    def test_route_appears_in_page_registry(self) -> None:
        assert "external_data" in {p.id for p in pages()}

    def test_has_a_nonempty_legacy_route(self) -> None:
        assert page_by_id("external_data").route.strip() != ""


class TestExternalDataRender:
    def test_page_renders_without_exception(self) -> None:
        at = _app("external_data")
        at.run()
        assert not at.exception, f"page raised: {[str(e.value) for e in at.exception]}"

    def test_page_shows_title(self) -> None:
        at = _app("external_data")
        at.run()
        md = " ".join(str(m.value) for m in at.markdown)
        assert "External Data" in md

    def test_uploader_is_present(self) -> None:
        at = _app("external_data")
        at.run()
        assert len(at.get("file_uploader")) > 0

    def test_unavailable_research_stages_are_shown(self) -> None:
        at = _app("external_data")
        at.run()
        md = " ".join(str(m.value) for m in at.markdown)
        assert "not run on uploaded data" in md
        # Each unavailable stage must state an explicit reason.
        for phrase in ("RO1", "RO2", "RO3"):
            assert phrase in md

    def test_run_button_not_shown_before_upload(self) -> None:
        # The run control appears only after a file parses, so an empty page
        # must not offer a misleading "run" affordance.
        at = _app("external_data")
        at.run()
        labels = {b.label for b in at.button}
        assert "Run analysis" not in labels


class TestFixtureIsDeterministicAndLabelled:
    def test_fixture_exists_and_is_synthetic(self) -> None:
        assert FIXTURE.is_file()
        header = FIXTURE.read_text(encoding="utf-8").splitlines()[0]
        assert header == "region,observed,q50,lower_80,upper_80"

    def test_fixture_has_expected_rows(self) -> None:
        lines = FIXTURE.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 201  # header + 200 rows


class TestPageLayering:
    """The page must go through the component layer (10A.3 rule).

    ``components.py`` is the only module allowed to import Streamlit —
    enforced repo-wide by ``test_dashboard_ui.py``'s layering test and
    per-page by the 10A.11–10A.13 suites. The External Data page is the
    first widget-driven workspace, so it gets the same guard.
    """

    PAGE_SOURCE = (
        ROOT / "src" / "construction" / "dashboard_ui" / "external_data.py"
    ).read_text(encoding="utf-8")

    def test_page_does_not_import_streamlit(self) -> None:
        assert "import streamlit" not in self.PAGE_SOURCE

    def test_page_uses_only_component_layer_adapters(self) -> None:
        # No raw Streamlit module access: widgets, callouts, columns, tables
        # and session state all arrive as components.* adapters.
        import re

        raw = re.findall(r"(?<![\w.])st\.", self.PAGE_SOURCE)
        assert raw == [], f"raw st. usage leaked into the page: {len(raw)} sites"
        assert "from src.construction.dashboard_ui import components" in self.PAGE_SOURCE
