"""Focused 10A.8 tests for the RO2 uncertainty workspace.

Covers: registry entries and safe loading, adapter behaviour for
valid/missing/invalid artifacts, provenance classification, demand versus
supply/duration representation, joint-propagation claim gating,
missing-evidence-never-zero, dataset boundaries, presentation purity
(no raw reads, no engine imports, no training), honest UI states, RO1
regression, and the RO1 metric audit findings (CRPS absent, pinball and
sMAPE now registered).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.construction.dashboard_data.contract import RO1Evidence, RO2Evidence
from src.construction.dashboard_data.loaders import ArtifactStatus, LoadResult


def _ro2_ui() -> Any:
    from src.construction.dashboard_ui import ro2 as _ro2

    return _ro2


def _ro1_ui() -> Any:
    from src.construction.dashboard_ui import ro1 as _ro1

    return _ro1


def _adapt_ro2() -> Any:
    from src.construction.dashboard_data import adapters as _a

    return _a.adapt_ro2_evidence


def _adapt_ro1() -> Any:
    from src.construction.dashboard_data import adapters as _a

    return _a.adapt_ro1_evidence


def _result(artifact_id: str, *, status: ArtifactStatus, data: Any = None) -> LoadResult:
    """Build a real LoadResult for the adapter, as the loader would."""
    from src.construction.dashboard_data.registry import get_entry

    entry = get_entry(artifact_id)
    assert entry is not None, f"{artifact_id} must be registered in the 10A.2-B registry"
    return LoadResult(
        entry=entry,
        status=status,
        data=data,
        provenance={
            "artifact_id": artifact_id,
            "provenance_class": entry.provenance_class,
            "evidence_role": entry.evidence_role,
            "status": status,
        },
    )


def _snapshot() -> Any:
    from src.construction.dashboard_data.snapshot import build_dashboard_snapshot

    return build_dashboard_snapshot(Path(__file__).resolve().parents[2])


# ---------------------------------------------------------------------------
# Registry entries and safe loading
# ---------------------------------------------------------------------------


class TestRO2RegistryEntries:
    def _entry(self, artifact_id: str) -> Any:
        from src.construction.dashboard_data.registry import get_entry

        entry = get_entry(artifact_id)
        assert entry is not None, f"{artifact_id} must be registered"
        return entry

    @pytest.mark.parametrize(
        "artifact_id",
        [
            "RO2_PROPAGATION_CONFIG",
            "RO2_PROPAGATION_SUMMARY",
            "RO2_DISTRIBUTION_DECISION",
            "RO2_DURATION_OBSERVED_STATS",
            "RO2_PROPAGATION_AUDIT",
            "RO2_CONVERGENCE_SUMMARY",
        ],
    )
    def test_ro2_artifact_is_registered_with_safe_policy(self, artifact_id: str) -> None:
        from src.construction.dashboard_data.registry import LoadingPolicy

        entry = self._entry(artifact_id)
        assert entry.loading_policy == LoadingPolicy.SAFE
        assert entry.max_safe_bytes <= 500_000, "new RO2 artifacts must carry a tight size cap"

    def test_observed_duration_stats_are_classified_obs(self) -> None:
        entry = self._entry("RO2_DURATION_OBSERVED_STATS")
        assert entry.provenance_class == "OBS"

    def test_derived_artifacts_are_not_classified_obs(self) -> None:
        for artifact_id in (
            "RO2_PROPAGATION_SUMMARY",
            "RO2_PROPAGATION_CONFIG",
            "RO2_DISTRIBUTION_DECISION",
            "RO2_PROPAGATION_AUDIT",
            "RO2_CONVERGENCE_SUMMARY",
        ):
            assert self._entry(artifact_id).provenance_class == "DER"

    def test_expected_columns_match_real_artifact_headers(self) -> None:
        root = Path(__file__).resolve().parents[2]
        for artifact_id in (
            "RO2_PROPAGATION_SUMMARY",
            "RO2_DISTRIBUTION_DECISION",
            "RO2_DURATION_OBSERVED_STATS",
        ):
            entry = self._entry(artifact_id)
            header = (root / entry.relative_path).read_text(encoding="utf-8").splitlines()[0]
            for col in entry.expected_columns:
                assert col in header, f"{artifact_id}: expected column {col!r} missing from header"


# ---------------------------------------------------------------------------
# Adapters: valid, missing, invalid, oversized
# ---------------------------------------------------------------------------


class TestRO2Adapters:
    def test_missing_artifacts_yield_empty_evidence_not_zero(self) -> None:
        evidence = _adapt_ro2()({})
        assert evidence.propagation_summary == []
        assert evidence.service_risk_curve == []
        assert evidence.sensitivity == []
        assert evidence.duration_observed_stats == []
        assert evidence.distribution_decision == []
        assert evidence.propagation_config == {}
        assert evidence.propagation_audit == {}
        assert evidence.convergence_summary == {}

    @pytest.mark.parametrize(
        "status",
        [ArtifactStatus.MISSING, ArtifactStatus.INVALID, ArtifactStatus.TOO_LARGE, ArtifactStatus.UNSUPPORTED],
    )
    def test_non_available_statuses_never_populate_fields(self, status: ArtifactStatus) -> None:
        results = {
            "RO2_PROPAGATION_SUMMARY": _result("RO2_PROPAGATION_SUMMARY", status=status, data=pd.DataFrame([{"material": "X"}])),
            "RO2_PROPAGATION_AUDIT": _result("RO2_PROPAGATION_AUDIT", status=status, data={"decision": "PASS"}),
        }
        evidence = _adapt_ro2()(results)
        assert evidence.propagation_summary == []
        assert evidence.propagation_audit == {}

    def test_available_artifacts_flow_into_contract(self) -> None:
        prop = pd.DataFrame([{"material": "Cement", "forecast_origin": "2022-06-01", "representation": "joint_duration_primary", "mc_n": 10000, "q50": 1.0, "q90": 2.0}])
        audit = {"decision": "PASS_WITH_RECORDED_CAVEATS", "structural_checks_pass": True}
        results = {
            "RO2_PROPAGATION_SUMMARY": _result("RO2_PROPAGATION_SUMMARY", status=ArtifactStatus.AVAILABLE, data=prop),
            "RO2_PROPAGATION_AUDIT": _result("RO2_PROPAGATION_AUDIT", status=ArtifactStatus.AVAILABLE, data=audit),
        }
        evidence = _adapt_ro2()(results)
        assert evidence.propagation_summary == prop.to_dict(orient="records")
        assert evidence.propagation_audit == audit

    def test_provenance_is_collected_even_when_data_missing(self) -> None:
        results = {"RO2_CONVERGENCE_SUMMARY": _result("RO2_CONVERGENCE_SUMMARY", status=ArtifactStatus.MISSING)}
        evidence = _adapt_ro2()(results)
        assert len(evidence.provenance) == 1


# ---------------------------------------------------------------------------
# Real-artifact integration (the dashboard must show the real numbers)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ro2_real() -> Any:
    return _snapshot().ro2


class TestRO2RealArtifacts:
    def test_propagation_summary_has_both_representations(self, ro2_real: Any) -> None:
        ro2 = ro2_real
        df = pd.DataFrame(ro2.propagation_summary)
        assert not df.empty
        assert set(df["representation"]) >= {"joint_duration_primary", "independent_duration_sensitivity"}

    def test_config_records_test_data_not_used(self, ro2_real: Any) -> None:
        assert ro2_real.propagation_config.get("test_data_used") is False

    def test_config_duration_terminology_is_procurement_process(self, ro2_real: Any) -> None:
        assert "procurement-process" in str(ro2_real.propagation_config.get("duration_terminology", ""))

    def test_propagation_audit_passes_with_caveats(self, ro2_real: Any) -> None:
        assert ro2_real.propagation_audit.get("decision") == "PASS_WITH_RECORDED_CAVEATS"
        assert ro2_real.propagation_audit.get("structural_checks_pass") is True

    def test_convergence_locks_10k(self, ro2_real: Any) -> None:
        assert ro2_real.convergence_summary.get("decision") == "LOCK_10000"
        assert ro2_real.convergence_summary.get("recommended_mc_lock") == 10000

    def test_duration_stats_flag_missing_and_negative_values(self, ro2_real: Any) -> None:
        df = pd.DataFrame(ro2_real.duration_observed_stats)
        assert not df.empty
        assert "n_missing_or_unparseable" in df.columns

    def test_distribution_decision_covers_three_components(self, ro2_real: Any) -> None:
        df = pd.DataFrame(ro2_real.distribution_decision)
        assert set(df["variable"]) == {"Total_DN", "Internal", "PO_GR_DN"}
        assert "recommended_status" in df.columns


# ---------------------------------------------------------------------------
# Demand versus supply/duration representation + dataset boundaries
# ---------------------------------------------------------------------------


class TestRO2RepresentationBoundaries:
    def test_demand_quantile_evidence_is_not_labelled_observed(self) -> None:
        ro2 = _ro2_ui()
        evidence = RO2Evidence(
            propagation_summary=[{"material": "Cement", "forecast_origin": "2022-06-01", "representation": "joint_duration_primary", "mc_n": 10, "q50": 1.0}],
        )
        rendered = str(ro2.build_demand_uncertainty(evidence))
        assert "not observed outcomes" in rendered

    def test_fixed_duration_is_never_presented_as_estimated_distribution(self) -> None:
        ro2 = _ro2_ui()
        rendered = str(ro2.build_supply_duration_uncertainty(RO2Evidence()))
        assert "unavailable" in rendered.lower()

    def test_price_dataset_is_not_propagated_in_ro2(self) -> None:
        # RO2's recorded run covers demand materials only; the page must say so
        # rather than implying price uncertainty was propagated.
        evidence = RO2Evidence(final_audit={"caveats": ["RO1 supplies marginal predictive quantiles."]})
        rendered = str(_ro2_ui().build_limitations(evidence))
        assert "RO1_PRICE" in rendered


# ---------------------------------------------------------------------------
# Joint-propagation claim gating
# ---------------------------------------------------------------------------


class TestJointPropagationClaimGating:
    def test_joint_claim_is_withheld_without_audit(self) -> None:
        joint = pd.DataFrame([{"paired_n": 37, "decision": "JOINT_EMPIRICAL_PRIMARY", "independence_assumption_supported": True}])
        evidence = RO2Evidence(joint_propagation_summary=joint.to_dict(orient="records"))
        rendered = str(_ro2_ui().build_joint_propagation(evidence))
        assert "not validated here" in rendered

    def test_joint_claim_not_shown_without_summary(self) -> None:
        evidence = RO2Evidence(propagation_audit={"structural_checks_pass": True, "decision": "PASS"})
        rendered = str(_ro2_ui().build_joint_propagation(evidence))
        assert "no joint-propagation result is claimed" in rendered

    def test_joint_section_never_proves_dependence(self) -> None:
        snapshot = _snapshot()
        rendered = str(_ro2_ui().build_joint_propagation(snapshot.ro2))
        assert "does not prove statistical dependence" in rendered or "not prove statistical dependence" in rendered


# ---------------------------------------------------------------------------
# Missing evidence remains unavailable, never zero
# ---------------------------------------------------------------------------


class TestMissingEvidenceNeverZero:
    def test_empty_ro2_page_renders_unavailable_states(self) -> None:
        blocks = _ro2_ui().build_page_content(RO2Evidence())
        joined = " ".join(str(b) for b in blocks)
        assert "unavailable" in joined.lower()
        assert ">0<" not in joined
        assert ">0.0<" not in joined

    def test_artifact_status_counts_hidden_when_nothing_loaded(self) -> None:
        rendered = str(_ro2_ui().build_evidence_status(RO2Evidence()))
        assert "—" in rendered  # MISSING_DISPLAY stands in for the counts


# ---------------------------------------------------------------------------
# Presentation purity: no raw reads, no training, no engines
# ---------------------------------------------------------------------------


class TestRO2PresentationPurity:
    def _tree(self) -> Any:
        import ast

        source = Path("src/construction/dashboard_ui/ro2.py").read_text(encoding="utf-8")
        return ast.parse(source)

    def test_module_never_reads_results_directly(self) -> None:
        for node in __import__("ast").walk(self._tree()):
            if isinstance(node, __import__("ast").Call):
                name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
                assert name not in {"open", "read_csv", "read_json", "glob", "rglob", "load_artifact"}

    def test_module_never_trains_or_fits_models(self) -> None:
        for node in __import__("ast").walk(self._tree()):
            if isinstance(node, __import__("ast").Call):
                name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
                assert name not in {"fit", "fit_predict", "predict", "cross_val_score", "train"}

    def test_module_imports_no_research_engines(self) -> None:
        import ast

        tree = self._tree()
        forbidden_prefixes = (
            "src.construction.simulation",
            "src.construction.uncertainty",
            "src.construction.experiments",
            "src.construction.models",
            "src.construction.quantity",
            "forecasting", "predict", "sklearn", "statsmodels", "prophet",
            "xgboost", "lightgbm", "torch", "tensorflow", "pmdarima", "neuralforecast",
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
                    assert not (lowered.startswith(prefix + ".") or lowered == prefix), f"Disallowed import: {module}"

    def test_no_streamlit_import_in_pure_module(self) -> None:
        import ast

        for node in ast.walk(self._tree()):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = node.module if isinstance(node, ast.ImportFrom) else ""
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
                assert "streamlit" not in (module or "")
                assert "streamlit" not in names


# ---------------------------------------------------------------------------
# Honest language guards
# ---------------------------------------------------------------------------


class TestHonestLanguageGuards:
    def test_duration_never_relabelled_as_supplier_lead_time(self) -> None:
        snapshot = _snapshot()
        blocks = _ro2_ui().build_page_content(snapshot.ro2)
        joined = " ".join(str(b) for b in blocks).lower()
        assert "not supplier-specific" in joined or "not a supplier" in joined

    def test_service_risk_is_labelled_conditional_exposure(self) -> None:
        snapshot = _snapshot()
        rendered = str(_ro2_ui().build_service_risk(snapshot.ro2)).lower()
        assert "conditional" in rendered
        assert "calibrated" in rendered

    def test_no_composite_uncertainty_score_anywhere(self) -> None:
        snapshot = _snapshot()
        joined = " ".join(str(b) for b in _ro2_ui().build_page_content(snapshot.ro2)).lower()
        for phrase in ("composite score", "uncertainty score", "overall risk score", "risk index"):
            assert phrase not in joined

    def test_handoff_does_not_claim_decision_improvement(self) -> None:
        snapshot = _snapshot()
        rendered = str(_ro2_ui().build_handoff_to_ro3(snapshot.ro2)).lower()
        assert "not" in rendered and "improv" in rendered


# ---------------------------------------------------------------------------
# RO1 metric audit (10A.8): CRPS absent; pinball and sMAPE now registered
# ---------------------------------------------------------------------------


class TestRO1MetricAuditFindings:
    def test_crps_is_genuinely_absent_from_results(self) -> None:
        root = Path(__file__).resolve().parents[2] / "results"
        hits = [
            p for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in {".csv", ".json", ".txt", ".md"}
            and "crps" in p.read_text(encoding="utf-8", errors="ignore").lower()
        ]
        assert hits == [], f"CRPS unexpectedly present in {[str(h) for h in hits]}"

    def test_pinball_is_registered_and_present(self) -> None:
        ro1 = _snapshot().ro1
        df = pd.DataFrame(ro1.test_metrics)
        assert not df.empty
        assert "pinball_q50" in df.columns

    def test_smape_is_registered_and_present(self) -> None:
        ro1 = _snapshot().ro1
        df = pd.DataFrame(ro1.baseline_metrics)
        assert not df.empty
        assert "sMAPE_percent" in df.columns

    def test_ro1_test_metrics_kept_separate_from_validation(self) -> None:
        # Held-out test split must not silently merge into validation metrics.
        ro1 = _snapshot().ro1
        val = pd.DataFrame(ro1.validation_metrics)
        test = pd.DataFrame(ro1.test_metrics)
        assert not val.empty and not test.empty
        assert "pinball_q50" not in val.columns

    def test_ro1_crps_card_still_honest(self) -> None:
        rendered = str(_ro1_ui().build_snapshot_cards(RO1Evidence()))
        assert "CRPS" in rendered

    def test_ro1_test_scores_section_renders(self) -> None:
        rendered = str(_ro1_ui().build_test_scores_section(_snapshot().ro1))
        assert "Pinball q50" in rendered
        assert "sMAPE (%)" in rendered

    def test_ro1_test_scores_section_honest_when_missing(self) -> None:
        rendered = str(_ro1_ui().build_test_scores_section(RO1Evidence()))
        assert "unavailable" in rendered.lower()


# ---------------------------------------------------------------------------
# Runtime render (AppTest) — RO2 page must render without exceptions
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ro2_app() -> Any:
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parents[2] / "apps" / "cmido_dashboard.py"
    at = AppTest.from_file(str(app_path), default_timeout=90)
    at.session_state["cmido_active_page"] = "ro2_uncertainty"
    at.run()
    return at


class TestRO2Runtime:
    def test_ro2_page_renders_without_exception(self, ro2_app) -> None:
        assert not ro2_app.exception

    def test_ro2_page_shows_all_sections(self, ro2_app) -> None:
        text = " ".join(str(m.value) for m in ro2_app.markdown)
        for heading in (
            "Research question and methodology",
            "Evidence status",
            "Demand uncertainty",
            "Supply and lead-time uncertainty",
            "Joint propagation",
            "Shortage and service-risk outcomes",
            "Material and scenario comparisons",
            "Sensitivity and stress evidence",
            "Uncertainty handoff to RO3",
            "Limitations and next evidence required",
        ):
            assert heading in text, f"missing section heading: {heading}"

    def test_ro2_page_shows_provenance_vocabulary(self, ro2_app) -> None:
        text = " ".join(str(m.value) for m in ro2_app.markdown)
        assert any(code in text for code in ("OBS", "DER", "EST", "SCN"))

    def test_ro2_page_no_snake_case_labels(self, ro2_app) -> None:
        import re

        text = " ".join(str(m.value) for m in ro2_app.markdown)
        # Artifact ids are uppercase by design; lowercase snake leaks are not.
        leaks = re.findall(r"\b[a-z]+(?:_[a-z0-9]+)+\b", text)
        assert leaks == [], f"snake_case labels leaked into RO2 page: {leaks}"


# ---------------------------------------------------------------------------
# RO1 rendering and navigation remain unchanged
# ---------------------------------------------------------------------------


class TestRO1Regression:
    def test_ro1_page_still_renders(self) -> None:
        from streamlit.testing.v1 import AppTest

        app_path = Path(__file__).resolve().parents[2] / "apps" / "cmido_dashboard.py"
        at = AppTest.from_file(str(app_path), default_timeout=90)
        at.session_state["cmido_active_page"] = "ro1_forecasting"
        at.run()
        assert not at.exception
        text = " ".join(str(m.value) for m in at.markdown)
        assert "RO1 · Forecasting" in text
        assert "Handoff to RO2" in text

    def test_ro1_navigation_unchanged(self) -> None:
        from src.construction.dashboard_ui.navigation import page_by_id

        page = page_by_id("ro1_forecasting")
        assert page.is_available
        assert page.route == "RO1 · Forecasting"
