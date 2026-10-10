"""Focused 10A.9 tests for the RO3 optimization workspace.

These tests assert scientific-integrity and integration guarantees for the RO3
workspace: registry-driven loading, provenance classification, raw-scenario
ledger gating, objective direction/units, honest unavailable states, and correct
navigation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.construction.dashboard_data.contract import ArtifactStatus, RO3Evidence
from src.construction.dashboard_data.loaders import LoadResult


def _ro3_ui() -> Any:
    from src.construction.dashboard_ui import ro3 as _ro3
    return _ro3


def _adapt() -> Any:
    from src.construction.dashboard_data import adapters as _a
    return _a.adapt_ro3_evidence


def _result(artifact_id: str, *, status: ArtifactStatus, data: Any = None, provenance: Any = None) -> LoadResult:
    from src.construction.dashboard_data.registry import get_entry

    entry = get_entry(artifact_id)
    assert entry is not None, f"{artifact_id} must be registered in the 10A.2-B registry"
    return LoadResult(entry=entry, status=status, data=data, provenance=provenance)


# ---------------------------------------------------------------------------
# 1. Registry entries and loading policies
# ---------------------------------------------------------------------------


class TestRO3Registry:
    RO3_ARTIFACTS = (
        "RO3_BASELINE_COMPARISON",
        "RO3_ABLATION",
        "RO3_CONTROLLER_DESCRIPTIVES",
        "RO3_STRESS_SUMMARY",
        "RO3_ROBUSTNESS_SUMMARY",
        "RO3_CONVERGENCE_SUMMARY",
        "RO3_PARETO_ALL_ORIGINS",
        "RO3_PARETO_DECISIONS",
        "RO3_FINAL_AUDIT",
    )

    def test_all_curated_ro3_artifacts_are_registered(self) -> None:
        from src.construction.dashboard_data.registry import get_entry
        for aid in self.RO3_ARTIFACTS:
            assert get_entry(aid) is not None, f"{aid} must be registered"

    def test_raw_scenario_ledgers_are_registered_but_blocked(self) -> None:
        from src.construction.dashboard_data.registry import get_entry
        for aid in ("RO3_SCENARIOS_2500_RAW", "RO3_SCENARIOS_5000_RAW"):
            entry = get_entry(aid)
            assert entry is not None, f"{aid} must be registered so its policy can forbid loading"

    def test_raw_scenario_ledgers_declared_never_load(self) -> None:
        """Raw 2500/5000 scenario ledgers must never be loaded as UI data."""
        from src.construction.dashboard_data.registry import get_entry
        for aid in ("RO3_SCENARIOS_2500_RAW", "RO3_SCENARIOS_5000_RAW"):
            entry = get_entry(aid)
            policy = getattr(entry, "loading_policy", None) or getattr(entry, "policy", None)
            text = str(policy).lower() if policy is not None else ""
            assert ("never" in text) or ("skip" in text) or ("blocked" in text), (
                f"{aid} must declare a never-load/blocked policy, got {policy!r}"
            )


# ---------------------------------------------------------------------------
# 5 / 14. No raw scenario-ledger loading, no filesystem access in ro3.py
# ---------------------------------------------------------------------------


class TestNoRawAccessOrEngineImports:
    FORBIDDEN_TOKENS = (
        "RO3_step32_scenarios_2500",
        "RO3_step32_scenarios_5000",
        "scenario_2500.csv",
        "scenario_5000.csv",
    )

    def test_ro3_ui_does_not_reference_raw_scenario_files(self) -> None:
        text = Path("src/construction/dashboard_ui/ro3.py").read_text(encoding="utf-8")
        for tok in self.FORBIDDEN_TOKENS:
            assert tok not in text, f"ro3.py must not reference raw scenario ledger {tok!r}"

    def test_ro3_ui_imports_no_research_engines(self) -> None:
        text = Path("src/construction/dashboard_ui/ro3.py").read_text(encoding="utf-8")
        for tok in (
            "src.construction.simulation",
            "src.construction.uncertainty",
            "src.construction.experiments",
            "src.construction.optimization",
            "scipy.optimize",
            "hi_ghs",
            "highs",
        ):
            assert tok not in text, f"ro3.py must not import research engine {tok!r}"

    def test_ro3_ui_has_no_filesystem_scanning(self) -> None:
        text = Path("src/construction/dashboard_ui/ro3.py").read_text(encoding="utf-8")
        for tok in ("glob.glob", "os.walk", "rglob", "Path.rglob", "listdir("):
            assert tok not in text, f"ro3.py must not scan the filesystem ({tok!r})"


# ---------------------------------------------------------------------------
# 2 / 3. Adapter handling of valid, missing, invalid artifacts
# ---------------------------------------------------------------------------


class TestRO3Adapter:
    def test_missing_artifacts_yield_empty_honest_fields(self) -> None:
        adapt = _adapt()
        evidence = adapt({})
        assert evidence.baseline_comparison == []
        assert evidence.ablation == []
        assert evidence.pareto_summary == []
        assert evidence.pareto_decisions == []
        assert evidence.final_audit == {}

    def test_available_dataframe_artifacts_are_adapted(self) -> None:
        adapt = _adapt()
        pareto_df = pd.DataFrame([
            {"origin": "O1", "objective": "Z1", "value": 1.0},
            {"origin": "O1", "objective": "Z2", "value": 2.0},
        ])
        decisions_df = pd.DataFrame([
            {"origin": "O1", "material": "M1", "quantity": 5},
        ])
        evidence = adapt({
            "RO3_PARETO_ALL_ORIGINS": _result(
                "RO3_PARETO_ALL_ORIGINS", status=ArtifactStatus.AVAILABLE, data=pareto_df
            ),
            "RO3_PARETO_DECISIONS": _result(
                "RO3_PARETO_DECISIONS", status=ArtifactStatus.AVAILABLE, data=decisions_df
            ),
        })
        assert len(evidence.pareto_summary) == 2
        assert len(evidence.pareto_decisions) == 1

    def test_unavailable_artifact_stays_empty_not_zero(self) -> None:
        """MISSING/INVALID artifacts must not fabricate rows or zeroes."""
        adapt = _adapt()
        evidence = adapt({
            "RO3_BASELINE_COMPARISON": _result(
                "RO3_BASELINE_COMPARISON", status=ArtifactStatus.MISSING, data=None
            ),
            "RO3_FINAL_AUDIT": _result(
                "RO3_FINAL_AUDIT", status=ArtifactStatus.INVALID, data=None
            ),
        })
        assert evidence.baseline_comparison == []
        assert evidence.final_audit == {}

    def test_non_available_artifact_leaves_dict_field_empty(self) -> None:
        """``final_audit`` is filled only from an AVAILABLE artifact.

        The registry types RO3_FINAL_AUDIT as a CSV, so the adapter's
        DataFrame branch is the only path that can populate ``audit_rows``; a
        non-AVAILABLE result must leave the dict field empty rather than
        inventing audit rows.
        """
        adapt = _adapt()
        evidence = adapt({
            "RO3_FINAL_AUDIT": _result(
                "RO3_FINAL_AUDIT", status=ArtifactStatus.UNSUPPORTED, data=None
            ),
        })
        assert evidence.final_audit == {}

    def test_audit_rows_are_wrapped_for_the_ui_contract(self) -> None:
        """An available audit CSV is wrapped under ``audit_rows`` for the UI."""
        adapt = _adapt()
        audit_df = pd.DataFrame([
            {"check": "gate", "passed": True, "detail": "ok"},
            {"check": "seed", "passed": False, "detail": "n/a"},
        ])
        evidence = adapt({
            "RO3_FINAL_AUDIT": _result(
                "RO3_FINAL_AUDIT", status=ArtifactStatus.AVAILABLE, data=audit_df
            ),
        })
        assert isinstance(evidence.final_audit, dict)
        assert len(evidence.final_audit["audit_rows"]) == 2


# ---------------------------------------------------------------------------
# 4 / 7. Provenance classification and objective direction / units
# ---------------------------------------------------------------------------


class TestProvenanceAndMetricMeta:
    def test_provenance_list_is_populated_from_supplied_artifacts(self) -> None:
        adapt = _adapt()
        evidence = adapt({
            "RO3_CONTROLLER_DESCRIPTIVES": _result(
                "RO3_CONTROLLER_DESCRIPTIVES", status=ArtifactStatus.AVAILABLE,
                data=pd.DataFrame([{"controller": "O1"}]),
            ),
        })
        assert len(evidence.provenance) >= 1

    def test_all_optimised_objectives_are_minimisation(self) -> None:
        ro3 = _ro3_ui()
        for metric in (
            "realized_procurement_holding_cost",
            "realized_total_shortage",
            "realized_shortage_cvar95_monthly",
        ):
            assert ro3._metric_direction(metric) == "min", f"{metric} must be a minimisation objective"

    def test_metric_units_are_declared(self) -> None:
        ro3 = _ro3_ui()
        for metric in ro3._METRIC_META:
            unit = ro3._metric_unit(metric)
            assert unit and unit.strip(), f"metric {metric!r} must declare a unit"


# ---------------------------------------------------------------------------
# 6. Procurement decision fields only when supported
# ---------------------------------------------------------------------------


class TestProcurementDecisionGating:
    def test_empty_decisions_render_unavailable_not_zeros(self) -> None:
        ro3 = _ro3_ui()
        evidence = RO3Evidence()
        block = ro3.build_procurement_decisions(evidence)
        html = _flatten(block)
        assert ("unavailable" in html.lower()) or ("no " in html.lower()) or ("not " in html.lower())
        assert "0.00" not in html, "empty decision evidence must not render fabricated zeroes"

    def test_supported_decisions_render_quantities(self) -> None:
        ro3 = _ro3_ui()
        evidence = RO3Evidence(
            pareto_decisions=[{"origin": "O1", "material": "M1", "quantity": 5}],
            pareto_summary=[{"origin": "O1", "objective": "Z1", "value": 1.0}],
        )
        block = ro3.build_procurement_decisions(evidence)
        assert _flatten(block)


# ---------------------------------------------------------------------------
# 8 / 9 / 10. Pareto, comparison and ablation gating
# ---------------------------------------------------------------------------


class TestEvidenceGating:
    def test_pareto_requires_evidence(self) -> None:
        ro3 = _ro3_ui()
        block = ro3.build_pareto_evidence(RO3Evidence())
        html = _flatten(block).lower()
        assert ("unavailable" in html) or ("no " in html) or ("not " in html)

    def test_pareto_renders_when_present(self) -> None:
        ro3 = _ro3_ui()
        evidence = RO3Evidence(
            pareto_summary=[{"origin": "O1", "objective": "Z1", "value": 1.0}],
        )
        assert _flatten(ro3.build_pareto_evidence(evidence))

    def test_controller_comparison_requires_evidence(self) -> None:
        ro3 = _ro3_ui()
        html = _flatten(ro3.build_controller_comparison(RO3Evidence())).lower()
        assert ("unavailable" in html) or ("no " in html) or ("not " in html)

    def test_ablation_requires_evidence(self) -> None:
        ro3 = _ro3_ui()
        html = _flatten(ro3.build_ablation(RO3Evidence())).lower()
        assert ("unavailable" in html) or ("no " in html) or ("not " in html)

    def test_robustness_requires_evidence(self) -> None:
        ro3 = _ro3_ui()
        html = _flatten(ro3.build_robustness_stress(RO3Evidence())).lower()
        assert ("unavailable" in html) or ("no " in html) or ("not " in html)


# ---------------------------------------------------------------------------
# 11 / 12. No fabricated values / rankings; missing stays unavailable
# ---------------------------------------------------------------------------


class TestNoFabrication:
    FORBIDDEN_CLAIMS = (
        "universally optimal",
        "best controller overall",
        "always superior",
        "composite score",
    )

    def test_page_content_has_no_universal_superiority_claims(self) -> None:
        ro3 = _ro3_ui()
        html = _flatten(ro3.build_page_content(RO3Evidence())).lower()
        for claim in self.FORBIDDEN_CLAIMS:
            assert claim not in html, f"ro3 page must not claim {claim!r}"

    def test_empty_evidence_does_not_invent_numbers(self) -> None:
        ro3 = _ro3_ui()
        html = _flatten(ro3.build_page_content(RO3Evidence()))
        # No stray fabricated percentage or confidence interval on an empty snapshot.
        for tok in ("bootstrap", "confidence interval", "p-value", "statistically significant"):
            assert tok.lower() not in html.lower(), f"empty RO3 page must not fabricate {tok!r}"


# ---------------------------------------------------------------------------
# 15. Complete / partial / absent rendering
# ---------------------------------------------------------------------------


def _flatten(block: Any) -> str:
    """Collect all rendered text of a block (recursively) for assertions.

    Mirrors ``render_section_block``: SectionBlock body/title, nested rows,
    ``{label, body}`` dict rows, and list bodies inside those dict rows.
    """
    if block is None:
        return ""
    if isinstance(block, str):
        return block
    parts: list[str] = []
    if isinstance(block, dict) and "label" in block:
        parts.append(str(block.get("label") or ""))
        inner = block.get("body")
        if isinstance(inner, list):
            for item in inner:
                parts.append(_flatten(item))
        elif inner:
            parts.append(str(inner))
        return " ".join(p for p in parts if p)
    body = getattr(block, "body", None)
    if isinstance(body, list):
        for item in body:
            parts.append(_flatten(item))
    elif body:
        parts.append(str(body))
    rows = getattr(block, "rows", None)
    if rows:
        for row in rows:
            parts.append(_flatten(row))
    title = getattr(block, "title", None)
    if title:
        parts.append(str(title))
    return " ".join(parts)


class TestNoPathLeak:
    def test_clean_audit_detail_suppresses_filesystem_paths(self) -> None:
        ro3 = _ro3_ui()
        path = r"D:\CMIDO\results\RO2\data_audit\RO2_step27b4_admissible_modelling_view.csv"
        assert ro3._clean_audit_detail(path) == ""

    def test_clean_audit_detail_keeps_genuine_values(self) -> None:
        ro3 = _ro3_ui()
        assert ro3._clean_audit_detail("37") == "37"
        assert ro3._clean_audit_detail("163/163") == "163/163"
        assert ro3._clean_audit_detail("n=2500 scenarios") == "n=2500 scenarios"

    def test_clean_audit_detail_suppresses_filename_lists(self) -> None:
        ro3 = _ro3_ui()
        listed = (
            "['RO3_step36_controller_descriptive_statistics.csv', "
            "'RO3_step36_statistical_analysis_audit.csv']"
        )
        assert ro3._clean_audit_detail(listed) == ""
        assert ro3._clean_audit_detail(
            "D:\\CMIDO\\results\\RO3\\scenario_generation\\RO3_step32_scenarios_2500.csv"
        ) == ""

    def test_handoff_section_never_leaks_paths(self) -> None:
        ro3 = _ro3_ui()
        evidence = RO3Evidence(
            final_audit={
                "audit_rows": [
                    {
                        "check": "RO2 27B.4 file exists",
                        "passed": True,
                        "detail": r"D:\CMIDO\results\RO2\data_audit\RO2_step27b4_admissible_modelling_view.csv",
                    },
                    {"check": "RO2 paired duration n=37", "passed": True, "detail": "37"},
                ]
            }
        )
        html = _flatten(ro3.build_handoff_from_ro2(evidence))
        assert "admissible_modelling_view" not in html
        assert "D:\\CMIDO" not in html
        # The check label (not the path) still records the RO2 linkage.
        assert "RO2 27B.4 file exists" in html


class TestRenderingStates:
    def test_full_page_renders_with_complete_evidence(self) -> None:
        ro3 = _ro3_ui()
        evidence = RO3Evidence(
            baseline_comparison=[{
                "comparison": "O2_vs_O1",
                "contrast": "Optimization under deterministic information",
                "metric": "realized_procurement_holding_cost",
                "n_origins": 11,
                "newer_mean": 1290003.0,
                "base_mean": 1587448.9,
                "mean_difference_newer_minus_base": -297445.8,
                "significant_bh_0_05": True,
            }],
            controller_descriptives=[{"controller": "O1", "metric": "cost", "mean": 1.0}],
            pareto_summary=[{"forecast_origin": "2022-01", "Z1": 1.0, "Z2": 2.0, "Z3": 3.0}],
            pareto_decisions=[{"forecast_origin": "2022-01", "material": "M1", "quantity": 5}],
            ablation=[{"contrast": "O2_vs_O1", "metric": "cost", "delta": -0.1}],
            stress_summary=[{"condition": "demand+10%", "metric": "cost", "value": 1.1}],
            final_audit={"audit_rows": [{"check": "gate", "passed": True, "detail": "ok"}]},
        )
        blocks = ro3.build_page_content(evidence)
        assert blocks, "a complete snapshot must render at least one block"

    def test_partial_evidence_renders_without_exception(self) -> None:
        ro3 = _ro3_ui()
        blocks = ro3.build_page_content(RO3Evidence(pareto_summary=[{"origin": "O1"}]))
        assert blocks

    def test_absent_evidence_renders_without_exception(self) -> None:
        ro3 = _ro3_ui()
        blocks = ro3.build_page_content(RO3Evidence())
        assert blocks


# ---------------------------------------------------------------------------
# 16 / 17. Navigation, breadcrumbs and RO1/RO2 regression
# ---------------------------------------------------------------------------


class TestNavigation:
    def test_ro3_is_available_and_in_research_group(self) -> None:
        from src.construction.dashboard_ui.navigation import page_by_id
        page = page_by_id("ro3_optimization")
        assert page.is_available
        assert page.group == "RESEARCH"
        assert not page.is_planned

    def test_breadcrumb_trail_is_correct(self) -> None:
        ro3 = _ro3_ui()
        assert ro3.breadcrumb_ids()[-1] == "ro3_optimization"
        row = ro3.build_breadcrumb_row()
        assert "ro3_optimization" in row.ids

    def test_app_dispatch_handles_ro3_route(self) -> None:
        text = Path("apps/cmido_dashboard.py").read_text(encoding="utf-8")
        assert "RO3 · Optimization" in text
        assert "ro3_workspace" in text


# ---------------------------------------------------------------------------
# 18. Light/dark theme compatibility (token usage, no literal colours)
# ---------------------------------------------------------------------------


class TestThemeCompatibility:
    def test_ro3_uses_theme_tokens_not_literal_hex(self) -> None:
        import re
        text = Path("src/construction/dashboard_ui/ro3.py").read_text(encoding="utf-8")
        # Strip the _fill helper's documented token parsing, then ensure no
        # standalone literal colour hex codes leak into the presentation code.
        literals = re.findall(r"#[0-9a-fA-F]{6}\b", text)
        assert literals == [], f"ro3.py must use theme tokens, found literal colours {literals}"
