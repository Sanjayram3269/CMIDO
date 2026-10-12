# -*- coding: utf-8 -*-
"""Tests for the CMIDO 10A.12 Ablation & Robustness workspace.

Contract of behavior we want the new page to uphold, independent of any
particular snapshot built at test time:

* the page module imports cleanly from the UI package,
* the page is registered as AVAILABLE in navigation,
* the page renders without importing the research engine,
* ablation, controller-comparison, stress, robustness, sensitivity,
  convergence and integrity artifacts load, validate and adapt into the
  contract,
* the 8M ablation evidence gate is registered and its recorded design
  properties flow through unmolested,
* statistically tested evidence (T5/T6) is kept apart from descriptive-only
  evidence (stress paired changes, holding contrasts, sensitivity),
* non-significance is never presented as equivalence,
* trade-offs are surfaced as recorded — no composite score, no ranking,
* scenario-count convergence is reported as recorded, including its recorded
  failure,
* missing or invalid artifacts render as unavailable, not zero,
* no raw repository path, hex colour or lowercase snake_case label reaches
  the page source or the rendered page,
* the raw scenario ledgers stay blocked,
* light/dark compatibility is inherited through the component layer only.

The tests exercise the module surface and the contract/registry/adapters
plumbing directly. They do not depend on a particular snapshot being built
at import time.
"""
from __future__ import annotations

import pathlib
import re
import sys
from typing import Any

import pandas as pd
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
    RO2Evidence,
    RO3Evidence,
)
from src.construction.dashboard_data.loaders import LoadResult
from src.construction.dashboard_data.registry import get_entry
from src.construction.dashboard_ui import ablation_robustness as page
from src.construction.dashboard_ui.navigation import (
    ImplementationStatus,
    pages_by_id,
)

_SNAKE_RE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _assert_no_hex_in_source(path: str) -> None:
    source = pathlib.Path(path).read_text(encoding="utf-8")
    hits = _HEX_RE.findall(source)
    assert not hits, f"{path} hard codes hex colors: {hits}"


def _provenance(
    artifact_id: str,
    status: ArtifactStatus = ArtifactStatus.AVAILABLE,
    schema_status: str = "PASSED",
) -> ArtifactProvenance:
    return ArtifactProvenance(
        artifact_id=artifact_id,
        source_path=f"results/fake/{artifact_id}",
        provenance_class=ProvenanceClass.DER,
        research_stage="RO3",
        status=status,
        row_count=3,
        file_size_bytes=1024,
        schema_status=schema_status,
    )


def _load_result(
    artifact_id: str,
    data: Any,
    status: ArtifactStatus = ArtifactStatus.AVAILABLE,
) -> LoadResult:
    entry = get_entry(artifact_id)
    assert entry is not None, f"{artifact_id} must be registered"
    return LoadResult(
        entry=entry,
        status=status,
        data=data,
        provenance=_provenance(artifact_id, status=status),
        error_message=None,
    )


# ---------------------------------------------------------------------------
# Fixtures — small, owned evidence dicts that mirror the contract fields
# ---------------------------------------------------------------------------


@pytest.fixture
def gate_manifest() -> dict[str, Any]:
    return {
        "stage": "8M",
        "status": "PASS",
        "project_root": "X:\\SOMEWHERE",  # must never reach the page
        "controllers": ["O1", "O2", "O3", "O4"],
        "locked_origins": ["2022-07-01", "2022-08-01"],
        "common_materials": ["Cement", "Granite"],
        "inferential_unit": "forecast_origin",
        "checks_passed": 2,
        "checks_total": 2,
        "source_artifacts": {
            "controller_manifest": {
                "path": "results\\fake\\controller.json",
                "sha256": "abc123",
            },
        },
    }


@pytest.fixture
def gate_audit() -> dict[str, Any]:
    return {
        "audit_rows": [
            {
                "check": "four_controllers_present",
                "passed": True,
                "detail": "X:\\SOMEWHERE\\results\\fake\\controllers.csv",
            },
            {
                "check": "origin_metrics_finite",
                "passed": True,
                "detail": "",
            },
        ]
    }


@pytest.fixture
def baseline_comparison() -> list[dict[str, Any]]:
    return [
        {
            "comparison": "O2_vs_O1",
            "contrast": "Optimization under deterministic information",
            "metric": "realized_procurement_holding_cost",
            "n_origins": 2,
            "newer_mean": 100.0,
            "base_mean": 130.0,
            "mean_difference_newer_minus_base": -30.0,
            "bootstrap_ci95_lower": -35.0,
            "bootstrap_ci95_upper": -25.0,
            "wilcoxon_p_raw": 0.01,
            "wilcoxon_q_bh": 0.02,
            "significant_bh_0_05": True,
        },
        {
            "comparison": "O2_vs_O1",
            "contrast": "Optimization under deterministic information",
            "metric": "realized_shortage_cvar95_monthly",
            "n_origins": 2,
            "newer_mean": 10.0,
            "base_mean": 10.5,
            "mean_difference_newer_minus_base": -0.5,
            "bootstrap_ci95_lower": -2.0,
            "bootstrap_ci95_upper": 1.0,
            "wilcoxon_p_raw": 0.5,
            "wilcoxon_q_bh": 0.6,
            "significant_bh_0_05": False,
        },
        {
            "comparison": "O4_vs_O1",
            "contrast": "Integrated CMIDO vs deterministic heuristic baseline",
            "metric": "realized_procurement_holding_cost",
            "n_origins": 2,
            "newer_mean": 200.0,
            "base_mean": 130.0,
            "mean_difference_newer_minus_base": 70.0,
            "bootstrap_ci95_lower": 60.0,
            "bootstrap_ci95_upper": 80.0,
            "wilcoxon_p_raw": 0.01,
            "wilcoxon_q_bh": 0.02,
            "significant_bh_0_05": True,
        },
        {
            "comparison": "O4_vs_O1",
            "contrast": "Integrated CMIDO vs deterministic heuristic baseline",
            "metric": "realized_service_level",
            "n_origins": 2,
            "newer_mean": 0.8,
            "base_mean": 0.5,
            "mean_difference_newer_minus_base": 0.3,
            "bootstrap_ci95_lower": 0.25,
            "bootstrap_ci95_upper": 0.35,
            "wilcoxon_p_raw": 0.01,
            "wilcoxon_q_bh": 0.02,
            "significant_bh_0_05": True,
        },
    ]


@pytest.fixture
def ablation_rows() -> list[dict[str, Any]]:
    return [
        {
            "comparison": "O4_vs_O2",
            "contrast": "Incremental value of uncertainty-aware optimization",
            "metric": "realized_total_shortage",
            "n_origins": 2,
            "newer_mean": 5.0,
            "base_mean": 8.0,
            "mean_difference_newer_minus_base": -3.0,
            "relative_mean_difference": -0.375,
            "bootstrap_ci95_lower": -4.0,
            "bootstrap_ci95_upper": -2.0,
            "wilcoxon_p_raw": 0.02,
            "improved_count": 2,
            "worsened_count": 0,
            "tie_count": 0,
            "rank_biserial_sign": -1.0,
            "wilcoxon_q_bh": 0.03,
            "significant_bh_0_05": True,
        }
    ]


@pytest.fixture
def controller_descriptives() -> list[dict[str, Any]]:
    return [
        {
            "controller": "O1",
            "n_origins": 2,
            "realized_procurement_holding_cost_mean": 130.0,
            "realized_total_shortage_mean": 8.0,
            "realized_service_level_mean": 0.5,
            "realized_shortage_cvar95_monthly_mean": 10.5,
            "realized_mean_ending_inventory_mean": 7.0,
        },
        {
            "controller": "O4",
            "n_origins": 2,
            "realized_procurement_holding_cost_mean": 200.0,
            "realized_total_shortage_mean": 3.0,
            "realized_service_level_mean": 0.8,
            "realized_shortage_cvar95_monthly_mean": 9.0,
            "realized_mean_ending_inventory_mean": 20.0,
        },
    ]


@pytest.fixture
def stress_summary() -> list[dict[str, Any]]:
    return [
        {
            "controller": "O1",
            "stress_case": "P50",
            "duration_days": 47.0,
            "n_origins": 2,
            "mean_cost": 100.0,
            "median_cost": 99.0,
            "mean_shortage": 6.0,
            "median_shortage": 5.5,
            "mean_service": 0.83,
            "median_service": 0.84,
            "mean_inventory": 5.0,
            "mean_procurement_quantity": 170.0,
            "mean_events": 38.0,
        },
        {
            "controller": "O1",
            "stress_case": "P95",
            "duration_days": 98.8,
            "n_origins": 2,
            "mean_cost": 90.0,
            "median_cost": 89.0,
            "mean_shortage": 12.0,
            "median_shortage": 11.0,
            "mean_service": 0.67,
            "median_service": 0.66,
            "mean_inventory": 2.0,
            "mean_procurement_quantity": 170.0,
            "mean_events": 38.0,
        },
    ]


@pytest.fixture
def stress_paired() -> list[dict[str, Any]]:
    return [
        {
            "controller": "O1",
            "comparison": "P95_vs_P50",
            "metric": "shortage",
            "mean_difference": 6.0,
            "median_difference": 5.5,
            "min_difference": 4.0,
            "max_difference": 7.0,
        }
    ]


@pytest.fixture
def robustness_summary() -> list[dict[str, Any]]:
    return [
        {
            "controller": "O1",
            "holding_case": "H20",
            "annual_holding_rate": 0.2,
            "n_origins": 2,
            "mean_cost": 95.0,
            "median_cost": 94.0,
            "mean_shortage": 6.0,
            "median_shortage": 5.5,
            "mean_service": 0.83,
            "median_service": 0.84,
            "mean_inventory": 5.0,
            "mean_procurement_quantity": 170.0,
            "mean_events": 38.0,
        }
    ]


@pytest.fixture
def holding_contrasts() -> list[dict[str, Any]]:
    return [
        {
            "holding_case": "H20",
            "contrast": "O2_vs_O1",
            "metric": "cost",
            "mean_difference": -50.0,
            "median_difference": -49.0,
            "min_difference": -60.0,
            "max_difference": -40.0,
        }
    ]


@pytest.fixture
def holding_sensitivity() -> list[dict[str, Any]]:
    return [
        {
            "controller": "O1",
            "comparison": "H20_vs_H30",
            "metric": "cost",
            "mean_difference": -10.0,
            "median_difference": -9.0,
            "min_difference": -12.0,
            "max_difference": -8.0,
        }
    ]


@pytest.fixture
def ro3_convergence() -> dict[str, Any]:
    return {
        "scenario_sizes": [100, 2500],
        "material_origin_cases": 44,
        "primary_transition": "500_to_1000",
        "primary_pass": False,
        "primary_failed_comparisons": 142,
        "primary_max_relative_change": 0.176,
        "later_max_relative_change": 0.1206,
        "decision": "RO3_3_EVALUATE_2500",
        "optimization_level_convergence_required_later": True,
    }


@pytest.fixture
def ro2_convergence() -> dict[str, Any]:
    return {
        "step": "27D.4",
        "decision": "LOCK_10000",
        "recommended_mc_lock": 10000,
        "n_cases": 48,
        "stable_at_10000_n": 48,
        "max_5k_to_10k_relative_change_pct": 0.67,
        "max_10k_to_25k_relative_change_pct": 0.31,
    }


@pytest.fixture
def sensitivity_rows() -> list[dict[str, Any]]:
    return [
        {
            "material": "Cement",
            "forecast_origin": "2022-06-01",
            "quantile": 0.9,
            "joint_duration_days_q50_q99_distribution": 1000.0,
            "independent_duration_sensitivity": 1050.0,
            "independent_minus_joint": 50.0,
            "independent_vs_joint_pct": 5.0,
        },
        {
            "material": "Steel",
            "forecast_origin": "2022-06-01",
            "quantile": 0.99,
            "joint_duration_days_q50_q99_distribution": 1400.0,
            "independent_duration_sensitivity": 1300.0,
            "independent_minus_joint": -100.0,
            "independent_vs_joint_pct": -7.14,
        },
    ]


@pytest.fixture
def final_audit() -> dict[str, Any]:
    return {
        "audit_rows": [
            {"check": "N2500 rows", "passed": True, "detail": "1320000"},
            {
                "check": "RO3.5 audit exists",
                "passed": True,
                "detail": "X:\\SOMEWHERE\\results\\fake\\audit.csv",
            },
        ]
    }


@pytest.fixture
def evidence(
    gate_manifest: dict[str, Any],
    gate_audit: dict[str, Any],
    baseline_comparison: list[dict[str, Any]],
    ablation_rows: list[dict[str, Any]],
    controller_descriptives: list[dict[str, Any]],
    stress_summary: list[dict[str, Any]],
    stress_paired: list[dict[str, Any]],
    robustness_summary: list[dict[str, Any]],
    holding_contrasts: list[dict[str, Any]],
    holding_sensitivity: list[dict[str, Any]],
    ro3_convergence: dict[str, Any],
    final_audit: dict[str, Any],
) -> RO3Evidence:
    return RO3Evidence(
        baseline_comparison=baseline_comparison,
        ablation=ablation_rows,
        controller_descriptives=controller_descriptives,
        stress_summary=stress_summary,
        robustness_summary=robustness_summary,
        convergence_summary=ro3_convergence,
        ablation_gate_manifest=gate_manifest,
        ablation_gate_audit=gate_audit,
        stress_paired=stress_paired,
        holding_contrasts=holding_contrasts,
        holding_sensitivity=holding_sensitivity,
        final_audit=final_audit,
        provenance=[
            _provenance("ABLATION_8M_GATE_MANIFEST"),
            _provenance("ABLATION_8M_GATE_AUDIT"),
            _provenance("RO3_BASELINE_COMPARISON"),
            _provenance("RO3_ABLATION"),
            _provenance("RO3_STRESS_PAIRED", status=ArtifactStatus.INVALID),
        ],
    )


# ---------------------------------------------------------------------------
# Module surface and navigation registration
# ---------------------------------------------------------------------------


def test_ablation_module_imports_without_research_engine() -> None:
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
    assert "ablation_robustness" in by_id
    entry = by_id["ablation_robustness"]
    assert entry.implementation is ImplementationStatus.AVAILABLE
    assert entry.route == "page/ablation_robustness"
    assert entry.group == "EVIDENCE"


def test_page_description_declares_the_evidence_scope() -> None:
    desc = page.page_description().lower()
    assert "ablation" in desc
    assert "stress" in desc or "robustness" in desc


def test_page_future_phase_is_recorded() -> None:
    assert page.page_future_phase() == "Phase 10A.12"


def test_page_is_not_planned() -> None:
    assert page.page_is_planned_local() is False


def test_resilience_stress_phase_label_is_no_longer_stale() -> None:
    """The stale 'Phase 10A.10' label must not survive on the planned page."""
    entry = pages_by_id()["resilience_stress"]
    assert entry.is_planned
    assert entry.future_phase != "Phase 10A.10"
    assert entry.future_phase


def test_dead_procurement_snapshot_abstraction_is_gone() -> None:
    """The never-populated snapshot.procurement field must stay removed."""
    assert not hasattr(contract.DashboardSnapshot(), "procurement")
    assert not hasattr(contract, "ProcurementDecisionsEvidence")


# ---------------------------------------------------------------------------
# Registry and adapter plumbing
# ---------------------------------------------------------------------------


def test_new_artifacts_are_registered_with_expected_columns() -> None:
    gate = get_entry("ABLATION_8M_GATE_MANIFEST")
    assert gate is not None
    assert gate.artifact_type.value == "JSON"
    paired = get_entry("RO3_STRESS_PAIRED")
    assert paired is not None
    assert "controller" in paired.expected_columns
    contrasts = get_entry("RO3_HOLDING_CONTRASTS")
    assert contrasts is not None
    assert "holding_case" in contrasts.expected_columns
    sensitivity = get_entry("RO3_HOLDING_SENSITIVITY")
    assert sensitivity is not None
    assert "comparison" in sensitivity.expected_columns


def test_raw_scenario_ledgers_stay_blocked() -> None:
    for artifact_id in ("RO3_SCENARIOS_2500_RAW", "RO3_SCENARIOS_5000_RAW"):
        entry = get_entry(artifact_id)
        assert entry is not None
        assert entry.loading_policy.value == "NEVER"


def test_adapter_maps_gate_and_descriptive_artifacts() -> None:
    results = {
        "ABLATION_8M_GATE_MANIFEST": _load_result(
            "ABLATION_8M_GATE_MANIFEST", {"controllers": ["O1"]}
        ),
        "ABLATION_8M_GATE_AUDIT": _load_result(
            "ABLATION_8M_GATE_AUDIT", pd.DataFrame([{"check": "c", "passed": True, "detail": ""}])
        ),
        "RO3_STRESS_PAIRED": _load_result(
            "RO3_STRESS_PAIRED",
            pd.DataFrame([{"controller": "O1", "comparison": "P95_vs_P50", "metric": "cost"}]),
        ),
        "RO3_HOLDING_CONTRASTS": _load_result(
            "RO3_HOLDING_CONTRASTS",
            pd.DataFrame([{"holding_case": "H20", "contrast": "O2_vs_O1", "metric": "cost"}]),
        ),
        "RO3_HOLDING_SENSITIVITY": _load_result(
            "RO3_HOLDING_SENSITIVITY",
            pd.DataFrame([{"controller": "O1", "comparison": "H20_vs_H30", "metric": "cost"}]),
        ),
    }
    bundle = adapters.adapt_ro3_evidence(results)
    assert bundle.ablation_gate_manifest == {"controllers": ["O1"]}
    assert len(bundle.ablation_gate_audit.get("audit_rows", [])) == 1
    assert len(bundle.stress_paired) == 1
    assert len(bundle.holding_contrasts) == 1
    assert len(bundle.holding_sensitivity) == 1


def test_adapter_leaves_fields_empty_for_missing_artifacts() -> None:
    bundle = adapters.adapt_ro3_evidence({})
    assert bundle.ablation_gate_manifest == {}
    assert bundle.ablation_gate_audit == {}
    assert bundle.stress_paired == []
    assert bundle.holding_contrasts == []
    assert bundle.holding_sensitivity == []


def test_adapter_leaves_fields_empty_for_invalid_artifacts() -> None:
    results = {
        "RO3_STRESS_PAIRED": _load_result(
            "RO3_STRESS_PAIRED", pd.DataFrame([{"unexpected": 1}]),
            status=ArtifactStatus.INVALID,
        ),
        "ABLATION_8M_GATE_MANIFEST": _load_result(
            "ABLATION_8M_GATE_MANIFEST", [1, 2, 3], status=ArtifactStatus.INVALID
        ),
    }
    bundle = adapters.adapt_ro3_evidence(results)
    assert bundle.stress_paired == []
    assert bundle.ablation_gate_manifest == {}


def test_adapter_keeps_provenance_of_new_artifacts() -> None:
    results = {
        "RO3_HOLDING_CONTRASTS": _load_result(
            "RO3_HOLDING_CONTRASTS", pd.DataFrame()
        ),
    }
    bundle = adapters.adapt_ro3_evidence(results)
    ids = [p.artifact_id for p in bundle.provenance]
    assert "RO3_HOLDING_CONTRASTS" in ids


# ---------------------------------------------------------------------------
# Provenance curation and artifact inventory
# ---------------------------------------------------------------------------


def test_provenance_rows_cover_only_this_workspaces_artifacts(
    evidence: RO3Evidence,
) -> None:
    rows = page.build_provenance_rows(evidence, RO2Evidence())
    ids = {row["artifact_id"] for row in rows}
    assert ids == {
        "ABLATION_8M_GATE_MANIFEST",
        "ABLATION_8M_GATE_AUDIT",
        "RO3_BASELINE_COMPARISON",
        "RO3_ABLATION",
        "RO3_STRESS_PAIRED",
    }


def test_provenance_rows_include_ro2_sensitivity_artifact(
    evidence: RO3Evidence,
) -> None:
    ro2 = RO2Evidence(provenance=[_provenance("RO2_SENSITIVITY")])
    rows = page.build_provenance_rows(evidence, ro2)
    assert "RO2_SENSITIVITY" in {row["artifact_id"] for row in rows}


def test_status_index_defaults_missing(
    evidence: RO3Evidence,
) -> None:
    rows = page.build_provenance_rows(evidence, RO2Evidence())
    index = page.artifact_status_index(rows)
    # Registered-but-absent artifacts read MISSING, never zero or available.
    assert index["RO3_CONVERGENCE_SUMMARY"] == "MISSING"
    assert index["RO3_FINAL_AUDIT"] == "MISSING"
    # Carried-through statuses are preserved verbatim.
    assert index["RO3_STRESS_PAIRED"] == "INVALID"


def test_artifact_table_marks_unregistered_artifacts() -> None:
    rows = page.build_artifact_table_rows([])
    assert rows
    assert all(row["Status"] == "NOT REGISTERED" for row in rows)


def test_artifact_table_carries_recorded_statuses(evidence: RO3Evidence) -> None:
    rows = page.build_artifact_table_rows(
        page.build_provenance_rows(evidence, RO2Evidence())
    )
    by_artifact = {row["Artifact"]: row for row in rows}
    gate_row = by_artifact[page._ARTIFACT_TITLES["ABLATION_8M_GATE_MANIFEST"]]
    assert gate_row["Status"] == "AVAILABLE"
    paired_row = by_artifact[page._ARTIFACT_TITLES["RO3_STRESS_PAIRED"]]
    assert paired_row["Status"] == "INVALID"


# ---------------------------------------------------------------------------
# Design and gate builders
# ---------------------------------------------------------------------------


def test_design_cards_derive_from_recorded_manifest(
    gate_manifest: dict[str, Any],
) -> None:
    cards = page.build_design_cards(gate_manifest)
    values = {card["label"]: card["value"] for card in cards}
    assert values["Controllers evaluated"] == "4"
    assert values["Locked forecast origins"] == "2"
    assert values["Common materials"] == "2"
    assert values["Evidence-gate checks"] == "2 of 2"


def test_design_cards_are_honest_when_manifest_is_empty() -> None:
    cards = page.build_design_cards({})
    for card in cards:
        assert card["value"] == "—"


def test_design_rows_humanize_the_inferential_unit(
    gate_manifest: dict[str, Any],
) -> None:
    rows = page.build_design_rows(gate_manifest)
    unit_row = next(r for r in rows if r["Property"] == "Inferential unit")
    assert unit_row["Recorded value"] == "forecast origin"
    # Controller definitions follow the documented 2×2 spec.
    defs_row = next(r for r in rows if r["Property"] == "Arm definitions")
    assert "O1 = Deterministic + heuristic (baseline)" in defs_row["Recorded value"]
    assert "O4 = Probabilistic + optimisation (CMIDO)" in defs_row["Recorded value"]


def test_gate_audit_rows_suppress_paths_and_treat_non_bool_as_missing(
    gate_audit: dict[str, Any], gate_manifest: dict[str, Any],
) -> None:
    rows = page.build_gate_audit_rows(gate_manifest, gate_audit)
    assert rows[0]["Recorded detail"] == "—"  # path-like detail suppressed
    assert rows[0]["Passed"] == "Yes"
    assert rows[1]["Passed"] == "Yes"


def test_gate_audit_rows_treat_non_bool_pass_as_missing() -> None:
    audit = {"audit_rows": [{"check": "x", "passed": "maybe", "detail": ""}]}
    rows = page.build_gate_audit_rows({}, audit)
    assert rows[0]["Passed"] == "—"


def test_gate_source_rows_keep_fingerprint_and_drop_paths(
    gate_manifest: dict[str, Any],
) -> None:
    rows = page.build_gate_source_rows(gate_manifest)
    assert len(rows) == 1
    assert rows[0]["Source artifact"] == "controller manifest"
    assert rows[0]["SHA-256 fingerprint"] == "abc123"
    joined = " ".join(str(v) for row in rows for v in row.values())
    assert "results" not in joined.lower()
    assert "SOMEWHERE" not in joined


def test_gate_source_rows_empty_without_manifest() -> None:
    assert page.build_gate_source_rows({}) == []
    assert page.build_gate_source_rows({"source_artifacts": "not-a-dict"}) == []


# ---------------------------------------------------------------------------
# Statistically tested comparison builders
# ---------------------------------------------------------------------------


def test_comparison_rows_carry_recorded_statistics(
    baseline_comparison: list[dict[str, Any]],
) -> None:
    rows = page.build_comparison_rows(pd.DataFrame(baseline_comparison))
    assert len(rows) == 4
    first = rows[0]
    assert first["Contrast"].startswith("O2 vs O1")
    assert first["Metric"] == "Realised procurement + holding cost"
    assert first["Corrected significance"] == "Yes"
    assert first["95% CI lower"] == "-35.00"


def test_ablation_rows_include_effect_sizes(
    ablation_rows: list[dict[str, Any]],
) -> None:
    rows = page.build_ablation_rows(pd.DataFrame(ablation_rows))
    assert len(rows) == 1
    row = rows[0]
    assert row["Relative mean difference"] == "-37.5%"
    assert row["Origins improved / worsened / tied"] == "2 / 0 / 0"
    assert row["Corrected significance"] == "Yes"


def test_contrast_findings_report_significant_differences(
    baseline_comparison: list[dict[str, Any]],
) -> None:
    findings = page.build_contrast_findings(pd.DataFrame(baseline_comparison))
    assert len(findings) == 2
    o2 = findings[0]
    assert "Statistically tested differences" in o2
    assert "lower is better" in o2


def test_contrast_findings_never_equate_non_significance(
    baseline_comparison: list[dict[str, Any]],
) -> None:
    findings = page.build_contrast_findings(pd.DataFrame(baseline_comparison))
    o2 = findings[0]
    assert "Did not reach corrected significance" in o2
    assert "not evidence of equivalence" in o2


def test_contrast_findings_surface_trade_offs_as_recorded(
    baseline_comparison: list[dict[str, Any]],
) -> None:
    findings = page.build_contrast_findings(pd.DataFrame(baseline_comparison))
    o4 = findings[1]
    # O4 raises cost (worse) and raises service (better): a recorded trade-off.
    assert "Trade-off, not a uniform win" in o4
    assert "no overall winner is declared" in o4


def test_contrast_findings_without_any_significance_say_so() -> None:
    rows = [
        {
            "comparison": "O3_vs_O1",
            "metric": "realized_total_shortage",
            "mean_difference_newer_minus_base": 1.0,
            "significant_bh_0_05": False,
        }
    ]
    findings = page.build_contrast_findings(pd.DataFrame(rows))
    assert "No metric in this contrast reached corrected significance" in findings[0]
    assert "not evidence of equivalence" in findings[0]


def test_contrast_findings_empty_frame_is_honest() -> None:
    findings = page.build_contrast_findings(pd.DataFrame())
    assert "unavailable" in findings[0]


def test_findings_never_produce_snake_case_labels(
    baseline_comparison: list[dict[str, Any]],
) -> None:
    findings = page.build_contrast_findings(pd.DataFrame(baseline_comparison))
    joined = " ".join(findings)
    leaks = _SNAKE_RE.findall(joined)
    assert leaks == [], f"snake_case labels leaked: {leaks}"


# ---------------------------------------------------------------------------
# Descriptive builders (stress, holding rate)
# ---------------------------------------------------------------------------


def test_stress_rows_carry_recorded_values(stress_summary: list[dict[str, Any]]) -> None:
    rows = page.build_stress_rows(pd.DataFrame(stress_summary))
    assert len(rows) == 2
    assert rows[0]["Stress case"] == "P50"
    assert rows[0]["Disruption duration (days)"] == "47.0"
    assert rows[1]["Stress case"] == "P95"


def test_stress_paired_rows_are_humanized(stress_paired: list[dict[str, Any]]) -> None:
    rows = page.build_stress_paired_rows(pd.DataFrame(stress_paired))
    assert rows[0]["Comparison"] == "P95 vs P50"
    assert rows[0]["Metric"] == "shortage"


def test_holding_rows_carry_recorded_rate(
    robustness_summary: list[dict[str, Any]],
) -> None:
    rows = page.build_holding_rows(pd.DataFrame(robustness_summary))
    assert rows[0]["Annual holding rate"] == "20.0%"


def test_holding_contrast_rows_label_contrasts(
    holding_contrasts: list[dict[str, Any]],
) -> None:
    rows = page.build_holding_contrast_rows(pd.DataFrame(holding_contrasts))
    assert rows[0]["Contrast"].startswith("O2 vs O1")


def test_holding_sensitivity_rows_humanize_comparison(
    holding_sensitivity: list[dict[str, Any]],
) -> None:
    rows = page.build_holding_sensitivity_rows(pd.DataFrame(holding_sensitivity))
    assert rows[0]["Comparison"] == "H20 vs H30"


# ---------------------------------------------------------------------------
# Convergence builders — recorded failure must survive
# ---------------------------------------------------------------------------


def test_ro3_convergence_reports_recorded_failure(
    ro3_convergence: dict[str, Any],
) -> None:
    lines = page.build_ro3_convergence_lines(ro3_convergence)
    joined = " ".join(lines)
    assert "Primary transition passed its threshold: No." in joined
    assert "Failed comparisons at the primary transition: 142." in joined
    assert "convergence recorded as still required" in joined
    assert "did not clear its threshold" in joined


def test_ro3_convergence_humanizes_recorded_tokens(
    ro3_convergence: dict[str, Any],
) -> None:
    lines = page.build_ro3_convergence_lines(ro3_convergence)
    joined = " ".join(lines)
    leaks = _SNAKE_RE.findall(joined)
    assert leaks == [], f"snake_case tokens leaked: {leaks}"


def test_ro3_convergence_empty_is_honest() -> None:
    lines = page.build_ro3_convergence_lines({})
    assert "unavailable" in lines[0]


def test_ro2_convergence_reports_recorded_lock(
    ro2_convergence: dict[str, Any],
) -> None:
    lines = page.build_ro2_convergence_lines(ro2_convergence)
    joined = " ".join(lines)
    assert "Recorded decision: LOCK 10000." in joined
    assert "Recommended Monte-Carlo lock: 10000 draws." in joined
    assert "Cases stable at the lock size: 48 of 48." in joined


def test_ro2_convergence_empty_is_honest() -> None:
    lines = page.build_ro2_convergence_lines({})
    assert "unavailable" in lines[0]


# ---------------------------------------------------------------------------
# RO2 sensitivity summary — counts and recorded range only
# ---------------------------------------------------------------------------


def test_sensitivity_summary_counts_and_range(
    sensitivity_rows: list[dict[str, Any]],
) -> None:
    summary = page.build_sensitivity_summary(sensitivity_rows)
    assert summary["rows"] == 2
    assert summary["materials"] == ["Cement", "Steel"]
    assert summary["quantiles"] == [0.9, 0.99]
    assert summary["pct_min"] == pytest.approx(-7.14)
    assert summary["pct_max"] == pytest.approx(5.0)


def test_sensitivity_summary_handles_malformed_rows() -> None:
    summary = page.build_sensitivity_summary(
        [{"material": "Cement", "independent_vs_joint_pct": "not-a-number"}]
    )
    assert summary["rows"] == 1
    assert summary["pct_min"] is None


def test_sensitivity_preview_carries_recorded_values(
    sensitivity_rows: list[dict[str, Any]],
) -> None:
    rows = page.build_sensitivity_preview_rows(sensitivity_rows)
    assert len(rows) == 2
    assert rows[0]["Material"] == "Cement"
    assert rows[0]["Joint duration (days)"] == "1,000.00"


def test_sensitivity_preview_limits_rows(
    sensitivity_rows: list[dict[str, Any]],
) -> None:
    many = sensitivity_rows * 10
    rows = page.build_sensitivity_preview_rows(many, limit=5)
    assert len(rows) == 5


# ---------------------------------------------------------------------------
# Integrity builders — paths suppressed
# ---------------------------------------------------------------------------


def test_integrity_rows_suppress_paths(final_audit: dict[str, Any]) -> None:
    rows = page.build_integrity_rows(final_audit)
    assert rows[0]["Recorded detail"] == "1320000"
    assert rows[1]["Recorded detail"] == "—"  # path-like detail suppressed
    assert rows[0]["Check"] == "N2500 rows"


def test_integrity_summary_counts_passed_checks(final_audit: dict[str, Any]) -> None:
    lines = page.build_integrity_summary(final_audit)
    assert "Recorded audit checks: 2, passed: 2, not passed: 0." in lines[0]
    assert "do not re-run any statistical test" in lines[1]


def test_integrity_summary_empty_is_honest() -> None:
    lines = page.build_integrity_summary({})
    assert "unavailable" in lines[0]


# ---------------------------------------------------------------------------
# Charts — recorded values only, no ranking
# ---------------------------------------------------------------------------


def test_tradeoff_figure_has_one_trace_per_controller(
    controller_descriptives: list[dict[str, Any]],
) -> None:
    fig = page._make_tradeoff_figure(pd.DataFrame(controller_descriptives))
    assert len(fig.data) == 1
    assert sorted(fig.data[0].text) == ["O1", "O4"]


def test_tradeoff_figure_empty_without_columns() -> None:
    fig = page._make_tradeoff_figure(pd.DataFrame([{"controller": "O1"}]))
    assert len(fig.data) == 0


def test_stress_figure_has_one_trace_per_controller(
    stress_summary: list[dict[str, Any]],
) -> None:
    fig = page._make_stress_figure(pd.DataFrame(stress_summary))
    assert len(fig.data) == 1  # one controller in the fixture


def test_stress_figure_empty_without_columns() -> None:
    fig = page._make_stress_figure(pd.DataFrame([{"controller": "O1"}]))
    assert len(fig.data) == 0


# ---------------------------------------------------------------------------
# Missing-evidence behaviour at the section level
# ---------------------------------------------------------------------------


def test_empty_evidence_provenance_builds_no_rows() -> None:
    rows = page.build_provenance_rows(RO3Evidence(), RO2Evidence())
    assert rows == []


def test_render_page_with_empty_snapshot_shows_error_state_only() -> None:
    """An empty snapshot must render the designed error state, not fabricate."""
    from src.construction.dashboard_data.contract import DashboardSnapshot
    import streamlit as st

    # The render path uses st.markdown via the component layer; AppTest-free
    # we assert the guard directly: no provenance rows -> early error return.
    snap = DashboardSnapshot()
    assert page.build_provenance_rows(snap.ro3, snap.ro2) == []


# ---------------------------------------------------------------------------
# Source hygiene: no paths, no hex, no inline styling, no snake_case ids
# ---------------------------------------------------------------------------


def test_no_raw_path_in_page_source() -> None:
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "D:\\CMIDO" not in source
    assert "D:/CMIDO" not in source


def test_no_hex_color_literal_in_page_source() -> None:
    _assert_no_hex_in_source(page.__file__)


def test_page_uses_only_the_component_layer_for_styling() -> None:
    """Light/dark parity is inherited from the design system: no inline CSS."""
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "style=" not in source
    assert "<div" not in source
    assert "light-dark(" not in source


def test_integrity_language_is_present_in_source() -> None:
    """The page must state the non-equivalence and trade-off rules."""
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "not evidence of equivalence" in source
    assert "Trade-off, not a uniform win" in source
    assert "no composite score" in source


# ---------------------------------------------------------------------------
# Runtime render (AppTest) — the page must render end-to-end
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ablation_app():
    from streamlit.testing.v1 import AppTest

    app_path = pathlib.Path(__file__).resolve().parents[2] / "apps" / "cmido_dashboard.py"
    at = AppTest.from_file(str(app_path), default_timeout=120)
    at.session_state["cmido_active_page"] = "ablation_robustness"
    at.run()
    return at


class TestAblationRuntime:
    def test_page_renders_without_exception(self, ablation_app) -> None:
        assert not ablation_app.exception

    def test_page_shows_the_major_sections(self, ablation_app) -> None:
        text = " ".join(str(m.value) for m in ablation_app.markdown)
        assert "Ablation and robustness evidence" in text
        assert "Experimental design and evidence gate" in text
        assert "Statistically tested controller comparisons" in text
        assert "2×2 component ablation" in text
        assert "Stress testing (scenario-based)" in text
        assert "Holding-rate robustness" in text
        assert "Convergence diagnostics" in text
        assert "Final experimental integrity audit" in text
        assert "How to read this evidence" in text

    def test_page_states_integrity_rules(self, ablation_app) -> None:
        text = " ".join(str(m.value) for m in ablation_app.markdown)
        assert "not evidence of equivalence" in text
        assert "Trade-off, not a uniform win" in text
        assert "no composite score is computed" in text

    def test_page_reports_recorded_convergence_failure(self, ablation_app) -> None:
        text = " ".join(str(m.value) for m in ablation_app.markdown)
        assert "Primary transition passed its threshold: No" in text

    def test_page_labels_stress_as_scenario_based(self, ablation_app) -> None:
        text = " ".join(str(m.value) for m in ablation_app.markdown)
        # The scenario-not-observation boundary is stated in the section
        # methodology and the closing provenance note of the stress section.
        assert "Stress cases re-evaluate the recorded decisions under perturbed" in text
        assert "not evidence of observed disruption performance" in text

    def test_no_snake_case_labels_leak_into_the_page(self, ablation_app) -> None:
        text = " ".join(str(m.value) for m in ablation_app.markdown)
        leaks = _SNAKE_RE.findall(text)
        assert leaks == [], f"snake_case labels leaked into the page: {leaks}"

    def test_no_filesystem_paths_leak_into_the_page(self, ablation_app) -> None:
        text = " ".join(str(m.value) for m in ablation_app.markdown)
        assert "D:\\CMIDO" not in text
        assert "\\results\\" not in text
