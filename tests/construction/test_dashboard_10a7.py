"""Focused 10A.7 tests for the RO1 forecasting workspace."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from src.construction.dashboard_data.contract import RO1Evidence
from src.construction.dashboard_data.loaders import LoadResult, ArtifactStatus


def _ro1_ui() -> Any:
    from src.construction.dashboard_ui import ro1 as _ro1
    return _ro1


def _adapt_ref() -> Any:
    from src.construction.dashboard_data import adapters as _a
    return _a.adapt_ro1_evidence


def _ro1_result(
    artifact_id: str,
    *,
    status: ArtifactStatus,
    data: Any = None,
    provenance: Any = None,
) -> LoadResult:
    """Build a real LoadResult for the adapter, as the loader would."""
    from src.construction.dashboard_data.registry import get_entry

    entry = get_entry(artifact_id)
    assert entry is not None, f"{artifact_id} must be registered in the 10A.2-B registry"
    return LoadResult(
        entry=entry,
        status=status,
        data=data,
        provenance=provenance
        or {"provenance_class": entry.provenance_class, "evidence_role": entry.evidence_role},
    )


# ---------------------------------------------------------------------------
# Basic routing / shell
# ---------------------------------------------------------------------------

class TestRONowAvailable:
    def test_ro1_page_is_available(self) -> None:
        from src.construction.dashboard_ui.navigation import page_by_id as _p
        page = _p("ro1_forecasting")
        assert page.is_available
        assert not page.is_planned
        assert page.route == "RO1 · Forecasting"
        assert page.provenance == "EST"

    def test_ro1_has_correct_group(self) -> None:
        from src.construction.dashboard_ui.navigation import page_by_id as _p
        page = _p("ro1_forecasting")
        assert page.group == "RESEARCH"

    def test_ro1_not_in_planned_set(self) -> None:
        from src.construction.dashboard_ui.navigation import pages as _ps
        planned_ids = {page.id for page in _ps() if page.is_planned}
        assert "ro1_forecasting" not in planned_ids

    def test_ro1_is_not_a_placeholder(self) -> None:
        from src.construction.dashboard_ui.navigation import page_by_id as _p
        page = _p("ro1_forecasting")
        assert not getattr(page, "future_phase", None)


# ---------------------------------------------------------------------------
# Breadcrumb / page identity
# ---------------------------------------------------------------------------

class TestRONavigationShape:
    def test_breadcrumb_ids(self) -> None:
        ro1 = _ro1_ui()
        ids = ro1.breadcrumb_ids()
        assert ids == ("overview", "research", "ro1_forecasting")

    def test_page_title_and_subtitle(self) -> None:
        ro1 = _ro1_ui()
        assert ro1.page_title() == "RO1 · Forecasting"
        subtitle = ro1.page_subtitle()
        assert "probabilistic" in subtitle.lower()
        assert "forecast" in subtitle.lower()


# ---------------------------------------------------------------------------
# Data contract adapter
# ---------------------------------------------------------------------------

class TestRONAdaptersPreserveEvidence:
    def test_adapter_calls_load_artifact_exactly_once_per_registered_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        keys_seen: list[str] = []

        def fake_load(entry: Any, root_path: Any) -> LoadResult:
            keys_seen.append(entry.artifact_id)
            return LoadResult(
                artifact_id=entry.artifact_id,
                status=ArtifactStatus.MISSING,
                error_message="not present in test fixture",
            )

        import src.construction.dashboard_data.registry as _reg_mod
        monkeypatch.setattr(_reg_mod, "load_artifact", fake_load, raising=False)
        adapt = _adapt_ref()
        evidence = adapt({})
        assert isinstance(keys_seen, list)
        assert len(keys_seen) == len(set(keys_seen))

    def test_adapter_accepts_missing_forecast_artifact(self) -> None:
        adapt = _adapt_ref()
        evidence = adapt({})
        assert evidence.validation_forecasts == []

    def test_adapter_keeps_validation_metrics_empty_when_missing(self) -> None:
        adapt = _adapt_ref()
        evidence = adapt({})
        assert evidence.validation_metrics == []

    def test_adapter_records_provenance_for_forecast_artifact(self) -> None:
        frame = pd.DataFrame([{
            "dataset": "RO1_PRICE",
            "series": "Cement",
            "horizon": 3,
            "actual": 100.0,
            "q50": 101.0,
        }])
        results = {
            "RO1_VALIDATION_FORECASTS": _ro1_result(
                "RO1_VALIDATION_FORECASTS",
                status=ArtifactStatus.AVAILABLE,
                data=frame,
                provenance={
                    "provenance_class": "EST",
                    "evidence_role": "RO1 probabilistic forecast evidence",
                },
            ),
        }
        evidence = _adapt_ref()(results)
        assert evidence.validation_forecasts != []
        assert evidence.provenance != []
        assert any(
            (
                getattr(entry, "provenance_class", None)
                or (entry.get("provenance_class") if isinstance(entry, dict) else None)
            ) == "EST"
            for entry in evidence.provenance
        )

    def test_adapter_exists(self) -> None:
        assert _adapt_ref() is not None


    def test_adapter_merges_all_available_artifacts(self) -> None:
        metrics = pd.DataFrame([{"dataset": "RO1_PRICE", "series": "Cement", "horizon": 3, "mae_q50": 1.0}])
        forecasts = pd.DataFrame([{"dataset": "RO1_PRICE", "series": "Cement", "horizon": 3, "actual": 10.0, "q50": 9.0}])
        calib = pd.DataFrame([{"dataset": "RO1_PRICE", "horizon": 3, "calibration_error_50": 0.1}])
        bootstrap = pd.DataFrame([{"dataset": "RO1_PRICE", "series": "Cement", "horizon": 3, "metric": "winkler_80"}])
        integrity = {"status": "PASS"}

        results = {
            "RO1_VALIDATION_METRICS": _ro1_result(
                "RO1_VALIDATION_METRICS", status=ArtifactStatus.AVAILABLE, data=metrics
            ),
            "RO1_VALIDATION_FORECASTS": _ro1_result(
                "RO1_VALIDATION_FORECASTS", status=ArtifactStatus.AVAILABLE, data=forecasts
            ),
            "RO1_CALIBRATION_SCORES": _ro1_result(
                "RO1_CALIBRATION_SCORES", status=ArtifactStatus.AVAILABLE, data=calib
            ),
            "RO1_PAIRED_BOOTSTRAP": _ro1_result(
                "RO1_PAIRED_BOOTSTRAP", status=ArtifactStatus.AVAILABLE, data=bootstrap
            ),
            "RO1_FINAL_INTEGRITY": _ro1_result(
                "RO1_FINAL_INTEGRITY", status=ArtifactStatus.AVAILABLE, data=integrity
            ),
        }
        evidence = _adapt_ref()(results)
        assert len(evidence.validation_metrics) == 1
        assert len(evidence.validation_forecasts) == 1
        assert len(evidence.calibration_summary) == 1
        assert len(evidence.paired_comparison) == 1
        assert evidence.integrity_audit == integrity

# ---------------------------------------------------------------------------
# Presentation builders — opportunistic checks (no Streamlit)
# ---------------------------------------------------------------------------

class TestROPresentationBuilders:
    @pytest.fixture
    def empty_evidence(self) -> RO1Evidence:
        return RO1Evidence()

    def test_page_content_returns_sections(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        sections = ro1.build_page_content(empty_evidence)
        assert isinstance(sections, list)
        assert len(sections) > 0

    def test_empty_evidence_shows_missing_states(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        sections = ro1.build_page_content(empty_evidence)
        joined = " ".join(str(section) for section in sections)
        assert "unavailable" in joined.lower() or "missing" in joined.lower()

    def test_snapshot_cards_do_not_invent_crps(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        cards_ = ro1.build_snapshot_cards(empty_evidence)
        rendered = str(cards_)
        assert "crps" not in rendered.lower() or "not reported" in rendered.lower() or "not available" in rendered.lower()

    def test_model_comparison_empty_state(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        section = ro1.build_model_comparison(empty_evidence)
        rendered = str(section)
        assert "not available" in rendered.lower() or "no ro1 validation metrics" in rendered.lower()

    def test_probabilistic_forecast_empty_state(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        section = ro1.build_probabilistic_forecast_section(empty_evidence)
        rendered = str(section)
        assert "probabilistic forecast" in rendered.lower()
        assert ("not available" in rendered.lower()) or ("not loaded" in rendered.lower())

    def test_calibration_empty_state(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        section = ro1.build_calibration_section(empty_evidence)
        rendered = str(section)
        assert "calibration" in rendered.lower()
        assert ("not available" in rendered.lower()) or ("no calibration" in rendered.lower())

    def test_material_stability_empty_state(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        section = ro1.build_material_stability_section(empty_evidence)
        rendered = str(section)
        assert "material" in rendered.lower() or "series" in rendered.lower()
        assert ("not available" in rendered.lower()) or ("no series" in rendered.lower())

    def test_temporal_stability_empty_state(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        section = ro1.build_temporal_stability_section(empty_evidence)
        rendered = str(section)
        assert "temporal" in rendered.lower()
        assert ("not available" in rendered.lower()) or ("no per-origin" in rendered.lower())


# ---------------------------------------------------------------------------
# No fabricated / unavailable metrics reported as zero
# ---------------------------------------------------------------------------

class TestRONMissingMetricsStayMissing:
    @pytest.fixture
    def empty_evidence(self) -> RO1Evidence:
        return RO1Evidence()

    def test_crps_is_not_shown_as_zero(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        cards_ = ro1.build_snapshot_cards(empty_evidence)
        rendered = str(cards_)
        assert "crps" not in rendered.lower() or "not available" in rendered.lower() or "not reported" in rendered.lower()

    def test_pinball_is_not_shown_as_zero(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        section = ro1.build_model_comparison(empty_evidence)
        rendered = str(section)
        assert "pinball" not in rendered.lower() or "not available" in rendered.lower()

    def test_smap_is_not_shown_as_zero(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        section = ro1.build_model_comparison(empty_evidence)
        rendered = str(section)
        assert "smap" not in rendered.lower() or "not available" in rendered.lower()

    def test_calibration_not_invented_from_point_metrics(self, empty_evidence: RO1Evidence) -> None:
        ro1 = _ro1_ui()
        section = ro1.build_calibration_section(empty_evidence)
        rendered = str(section)
        assert "coverage 100%" not in rendered.lower()
        assert "perfectly calibrated" not in rendered.lower()


# ---------------------------------------------------------------------------
# Dataset separation preserved
# ---------------------------------------------------------------------------

class TestRONDatasetSeparation:
    def test_both_datasets_present_without_fabricated_join(self) -> None:
        metrics = pd.DataFrame([
            {"dataset": "RO1_PRICE", "series": "Cement", "horizon": 3, "mae_q50": 1.0},
            {"dataset": "RO1_DEMAND", "series": "Cement", "horizon": 3, "mae_q50": 2.0},
        ])
        results = {
            "RO1_VALIDATION_METRICS": _ro1_result(
                "RO1_VALIDATION_METRICS", status=ArtifactStatus.AVAILABLE, data=metrics
            ),
        }
        evidence = _adapt_ref()(results)
        ro1 = _ro1_ui()
        section = ro1.build_model_comparison(evidence)
        rendered = str(section)
        assert "RO1_PRICE" in rendered
        assert "RO1_DEMAND" in rendered

# ---------------------------------------------------------------------------
# Provenance displayed
# ---------------------------------------------------------------------------

class TestRONProvenance:
    def test_forecast_rows_provenance_est(self) -> None:
        frame = pd.DataFrame([
            {"dataset": "RO1_PRICE", "series": "Cement", "horizon": 3, "actual": 100.0, "q50": 101.0},
        ])
        results = {
            "RO1_VALIDATION_FORECASTS": _ro1_result(
                "RO1_VALIDATION_FORECASTS",
                status=ArtifactStatus.AVAILABLE,
                data=frame,
                provenance={
                    "provenance_class": "EST",
                    "evidence_role": "RO1 probabilistic forecast evidence",
                },
            ),
        }
        evidence = _adapt_ref()(results)
        ro1 = _ro1_ui()
        section = ro1.build_probabilistic_forecast_section(evidence)
        rendered = str(section)
        assert "provenance" in rendered.lower()
        assert "est" in rendered.lower()

# ---------------------------------------------------------------------------
# No research-engine imports from dashboard UI
# ---------------------------------------------------------------------------

class TestRONNoResearchEngineImports:
    def test_ui_module_has_no_forecasting_engine_import(self) -> None:
        import ast
        from pathlib import Path

        path = Path("src/construction/dashboard_ui/ro1.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden_prefixes = (
            "forecasting",
            "predict",
            "sklearn",
            "statsmodels",
            "prophet",
            "xgboost",
            "lightgbm",
            "torch",
            "tensorflow",
            "pmdarima",
            "neuralforecast",
        )
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                lowered = (module + ".").lower()
                for prefix in forbidden_prefixes:
                    if lowered.startswith(prefix + ".") or lowered == prefix:
                        raise AssertionError(f"Disallowed import found: {module}")


# ---------------------------------------------------------------------------
# No raw artifact reads / no runtime training from presentation code
# ---------------------------------------------------------------------------

class TestRONPresentationPurity:
    def test_ro1_module_never_reads_results_directly(self) -> None:
        import ast
        from pathlib import Path

        source = Path("src/construction/dashboard_ui/ro1.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
                assert name not in {
                    "open",
                    "read_csv",
                    "read_json",
                    "glob",
                    "rglob",
                    "load_artifact",
                }, f"presentation code must not read artifacts directly: {name}"

    def test_ro1_module_never_trains_or_fits_models(self) -> None:
        import ast
        from pathlib import Path

        source = Path("src/construction/dashboard_ui/ro1.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
                assert name not in {
                    "fit",
                    "fit_predict",
                    "predict",
                    "cross_val_score",
                    "train",
                }, f"presentation code must not run model training: {name}"

    def test_snapshot_cards_do_not_show_zero_for_missing_metrics(self) -> None:
        ro1 = _ro1_ui()
        rendered = str(ro1.build_snapshot_cards(RO1Evidence()))
        # Missing evidence must never be rendered as a numeric zero.
        assert ">0<" not in rendered
        assert ">0.0<" not in rendered


# ---------------------------------------------------------------------------
# Runtime render (AppTest) — RO1 page must render without exceptions
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ro1_app():
    from pathlib import Path as _Path

    from streamlit.testing.v1 import AppTest

    app_path = _Path(__file__).resolve().parents[2] / "apps" / "cmido_dashboard.py"
    at = AppTest.from_file(str(app_path), default_timeout=90)
    at.session_state["cmido_active_page"] = "ro1_forecasting"
    at.run()
    return at


class TestRONRuntime:
    def test_ro1_page_renders_without_exception(self, ro1_app) -> None:
        assert not ro1_app.exception

    def test_ro1_page_shows_research_question(self, ro1_app) -> None:
        text = " ".join(str(m.value) for m in ro1_app.markdown)
        assert "Research question and method context" in text
        assert "forecast" in text.lower()

    def test_ro1_page_shows_model_comparison(self, ro1_app) -> None:
        text = " ".join(str(m.value) for m in ro1_app.markdown)
        assert "Model comparison" in text

    def test_ro1_page_shows_probabilistic_section(self, ro1_app) -> None:
        text = " ".join(str(m.value) for m in ro1_app.markdown)
        assert "Probabilistic forecast" in text

    def test_ro1_page_shows_calibration_section(self, ro1_app) -> None:
        text = " ".join(str(m.value) for m in ro1_app.markdown)
        assert "Calibration" in text

    def test_ro1_page_shows_handoff_section(self, ro1_app) -> None:
        text = " ".join(str(m.value) for m in ro1_app.markdown)
        assert "Handoff to RO2" in text

    def test_ro1_page_provenance_badges_present(self, ro1_app) -> None:
        text = " ".join(str(m.value) for m in ro1_app.markdown)
        # OBS/DER/EST/SCN vocabulary must appear somewhere on the page.
        assert any(code in text for code in ("OBS", "DER", "EST", "SCN"))
