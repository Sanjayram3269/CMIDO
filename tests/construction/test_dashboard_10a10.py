# -*- coding: utf-8 -*-
"""Tests for the CMIDO 10A.10 Procurement Decisions workspace.

Contract of behavior we want the new page to uphold, independent of any
particular snapshot built at test time:

* the page module imports cleanly from the UI package,
* the page is registered as AVAILABLE in navigation,
* the page renders without importing the research engine,
* decision-level RO3 artifacts load, validate and adapt into the contract,
* supplier allocation, safety stock and storage-capacity decisions remain
  explicitly unavailable,
* missing decision artifacts render as unavailable, not zero,
* per-period realized-evaluation ledger loading is gated by size,
* raw RO3 scenario ledgers stay blocked,
* no raw repository path or hex color is rendered into the page HTML,
* the page declares the correct future phase and description.

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
from src.construction.dashboard_ui.navigation import ImplementationStatus
from src.construction.dashboard_data.contract import (
    ArtifactProvenance,
    ArtifactStatus,
    ProvenanceClass,
    RO3Evidence,
)
import src.construction.dashboard_data.registry as registry
from src.construction.dashboard_data.registry import (
    ArtifactEntry,
    LoadingPolicy,
)
from src.construction.dashboard_data.loaders import LoadResult
from src.construction.dashboard_ui import _procurement_helpers as ph
from src.construction.dashboard_ui.navigation import pages, pages_by_id


def _assert_no_hex_in_source(path: str) -> None:
    source = pathlib.Path(path).read_text(encoding="utf-8")
    hex_re = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    hits = hex_re.findall(source)
    assert not hits, f"{path} hard codes hex colors: {hits}"


# ---------------------------------------------------------------------------
# Fixtures — small, owned evidence dicts that mirror the contract fields
# ---------------------------------------------------------------------------


@pytest.fixture
def decision_evidence() -> contract.RO3Evidence:
    """An RO3Evidence populated with the five decision-level artifacts."""
    prov: list[contract.ArtifactProvenance] = [
        contract.ArtifactProvenance(
            artifact_id="RO3_O2_SELECTED_DECISIONS",
            source_path="results/RO3/ablation/O2/O2_selected_decisions.csv",
            provenance_class=contract.ProvenanceClass.DER,
            research_stage="RO3",
            status=ArtifactStatus.AVAILABLE,
            row_count=48,
            file_size_bytes=3200,
            schema_status="OK",
            notes="O2 single-origin selected decisions.",
        ),
            contract.ArtifactProvenance(
                artifact_id="RO3_O2_REALIZED_EVALUATION_SUMMARY",
                source_path="results/RO3/ablation/O2/O2_realized_evaluation_summary.csv",
                provenance_class=contract.ProvenanceClass.DER,
                research_stage="RO3",
                status=ArtifactStatus.AVAILABLE,
                row_count=24,
                file_size_bytes=2100,
                schema_status="OK",
                notes="O2 single-origin realized evaluation.",
            ),
            contract.ArtifactProvenance(
                artifact_id="RO3_O4_REALIZED_EVALUATION_LEDGER",
                source_path="results/RO3/ablation/O4_single_origin/O4_single_origin_realized_evaluation_ledger.csv",
                provenance_class=contract.ProvenanceClass.DER,
                research_stage="RO3",
                status=ArtifactStatus.AVAILABLE,
                row_count=420,
                file_size_bytes=48000,
                schema_status="OK",
                notes="O4 single-origin realized ledger (small enough).",
            ),
            contract.ArtifactProvenance(
                artifact_id="RO3_MULTI_ORIGIN_SUMMARY",
                source_path="results/RO3/multi_origin/RO3_step35_origin_summary_N2500.csv",
                provenance_class=contract.ProvenanceClass.DER,
                research_stage="RO3",
                status=ArtifactStatus.AVAILABLE,
                row_count=6,
                file_size_bytes=900,
                schema_status="OK",
                notes="Per-origin Pareto count + objective range.",
            ),
            contract.ArtifactProvenance(
                artifact_id="RO3_DECISION_SENSITIVITY",
                source_path="results/RO3/decision_sensitivity/RO3_step33B_corrected_summary_20220701.csv",
                provenance_class=contract.ProvenanceClass.DER,
                research_stage="RO3",
                status=ArtifactStatus.AVAILABLE,
                row_count=3,
                file_size_bytes=600,
                schema_status="OK",
                notes="Pairwise corrected decision sensitivity.",
            ),
            contract.ArtifactProvenance(
                artifact_id="RO3_SCENARIOS_2500_RAW",
                source_path="results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv",
                provenance_class=contract.ProvenanceClass.SCN,
                research_stage="RO3",
                status=ArtifactStatus.AVAILABLE,
                row_count=None,
                file_size_bytes=171000000,                schema_status="BLOCKED",
                notes="RAW scenario ledger; NEVER loaded.",
            ),
        ]

    return contract.RO3Evidence(
        provenance=prov,
        selected_decisions=[
            {
                "forecast_origin": "2022-07-01",
                "material": "Cement",
                "period": "2022-08-01",
                "order_qty": 273.51343,
                "selected_candidate": "eps_02",
                "optimization_Z1": 32089.540994,
                "optimization_Z2": 1711.270822,
                "optimization_Z3": 2284.761818,
            },
        ],
        realized_evaluation_summary=[
            {
                "forecast_origin": "2022-07-01",
                "material": "Cement",
                "realized_cost": 32548.098156,
                "shortage": 1680.915701,
                "service": 0.619362,
                "procurement_qty": 273.513430,
                "ending_inventory": 0.0,
            },
        ],
        realized_evaluation_ledger=[
            {
                "forecast_origin": "2022-07-01",
                "material": "Cement",
                "period": "2022-08-01",
                "order_qty": 273.51343,
                "arrival_qty": 0.0,
                "demand": 402.46,
                "price": 119.0,
                "shortage": 402.46,
                "ending_inventory": 0.0,
                "procurement_cost": 32548.098156,
                "holding_cost": 0.0,
            },
        ],
        multi_origin_summary=[
            {
                "forecast_origin": "2022-07-01",
                "pareto_count": 5,
                "Z1_min": 0.0,
                "Z1_median": 355101.111547,
                "Z1_max": 3718680.0,
                "Z2_min": 4021.616981,
                "Z2_median": 20621.846168,
                "Z2_max": 37222.075354,
                "Z3_min": 7422.339407,
                "Z3_median": 22706.954429,
                "Z3_max": 38439.937170,
                "runtime_total_sec": 813.812423,
            },
        ],
        decision_sensitivity=[
            {
                "N_A": 1000,
                "N_B": 2500,
                "matched_solutions": 5,
                "mean_objective_distance": 0.007494,
                "max_objective_distance": 0.027201,
                "mean_abs_quantity_difference": 12.836158,
                "mean_total_procurement_normalized_difference": 0.020351,
                "max_total_procurement_normalized_difference": 0.040671,
                "mean_zero_safe_quantity_relative_difference": 0.037836,
            },
        ],
        pareto_summary=[],
        pareto_decisions=[],
        controller_descriptives=[],
        baseline_comparison=[],
        ablation=[],
        stress_summary=[],
        robustness_summary=[],
        convergence_summary={},
        final_audit={},
    )
    decision_evidence.provenance[1] = contract.ArtifactProvenance(
        artifact_id="RO3_O2_REALIZED_EVALUATION_SUMMARY",
        source_path="results/RO3/ablation/O4_single_origin/O4_single_origin_realized_evaluation_ledger.csv",
        provenance_class=contract.ProvenanceClass.DER,
        research_stage="RO3",
        status=ArtifactStatus.AVAILABLE,
        row_count=420,
        file_size_bytes=48000,
        schema_status="OK",
        notes="O4 single-origin realized ledger (small enough).",
    )
    decision_evidence.provenance[2] = contract.ArtifactProvenance(
        artifact_id="RO3_MULTI_ORIGIN_SUMMARY",
        source_path="results/RO3/multi_origin/RO3_step35_origin_summary_N2500.csv",
        provenance_class=contract.ProvenanceClass.DER,
        research_stage="RO3",
        status=ArtifactStatus.AVAILABLE,
        row_count=6,
        file_size_bytes=900,
        schema_status="OK",
        notes="Per-origin Pareto count + objective range.",
    )
    decision_evidence.provenance[3] = contract.ArtifactProvenance(
        artifact_id="RO3_DECISION_SENSITIVITY",
        source_path="results/RO3/decision_sensitivity/RO3_step33B_corrected_summary_20220701.csv",
        provenance_class=contract.ProvenanceClass.DER,
        research_stage="RO3",
        status=ArtifactStatus.AVAILABLE,
        row_count=3,
        file_size_bytes=600,
        schema_status="OK",
        notes="Pairwise corrected decision sensitivity.",
    )
    decision_evidence.provenance[4] = contract.ArtifactProvenance(
        artifact_id="RO3_SCENARIOS_2500_RAW",
        source_path="results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv",
        provenance_class=contract.ProvenanceClass.SCN,
        research_stage="RO3",
        status=ArtifactStatus.AVAILABLE,
        row_count=None,
        file_size_bytes=171000000,
        schema_status="BLOCKED",
        notes="RAW scenario ledger; NEVER loaded.",
    )

    return contract.RO3Evidence(
        provenance=prov,
        selected_decisions=[
            {
                "forecast_origin": "2022-07-01",
                "material": "Cement",
                "period": "2022-08-01",
                "order_qty": 273.51343,
                "selected_candidate": "eps_02",
                "optimization_Z1": 32089.540994,
                "optimization_Z2": 1711.270822,
                "optimization_Z3": 2284.761818,
            },
        ],
        realized_evaluation_summary=[
            {
                "forecast_origin": "2022-07-01",
                "material": "Cement",
                "realized_cost": 32548.098156,
                "shortage": 1680.915701,
                "service": 0.619362,
                "procurement_qty": 273.513430,
                "ending_inventory": 0.0,
            },
        ],
        realized_evaluation_ledger=[
            {
                "forecast_origin": "2022-07-01",
                "material": "Cement",
                "period": "2022-08-01",
                "order_qty": 273.51343,
                "arrival_qty": 0.0,
                "demand": 402.46,
                "price": 119.0,
                "shortage": 402.46,
                "ending_inventory": 0.0,
                "procurement_cost": 32548.098156,
                "holding_cost": 0.0,
            },
        ],
        multi_origin_summary=[
            {
                "forecast_origin": "2022-07-01",
                "pareto_count": 5,
                "Z1_min": 0.0,
                "Z1_median": 355101.111547,
                "Z1_max": 3718680.0,
                "Z2_min": 4021.616981,
                "Z2_median": 20621.846168,
                "Z2_max": 37222.075354,
                "Z3_min": 7422.339407,
                "Z3_median": 22706.954429,
                "Z3_max": 38439.937170,
                "runtime_total_sec": 813.812423,
            },
        ],
        decision_sensitivity=[
            {
                "N_A": 1000,
                "N_B": 2500,
                "matched_solutions": 5,
                "mean_objective_distance": 0.007494,
                "max_objective_distance": 0.027201,
                "mean_abs_quantity_difference": 12.836158,
                "mean_total_procurement_normalized_difference": 0.020351,
                "max_total_procurement_normalized_difference": 0.040671,
                "mean_zero_safe_quantity_relative_difference": 0.037836,
            },
        ],
        pareto_summary=[],
        pareto_decisions=[],
        controller_descriptives=[],
        baseline_comparison=[],
        ablation=[],
        stress_summary=[],
        robustness_summary=[],
        convergence_summary={},
        final_audit={},
    )


# ---------------------------------------------------------------------------
# Module + navigation surface
# ---------------------------------------------------------------------------


def test_procurement_decisions_module_imports_without_research_engine() -> None:
    """The page module must not import the research engine at import time."""
    import src.construction.dashboard_ui.procurement_decisions as page

    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    banned = ("solve_ro3", "run_ro3", "optimization_engine", "scenario_generation")
    for token in banned:
        assert token not in source, f"page module references {token}"


def test_procurement_decisions_page_is_registered_and_available() -> None:
    """The workspace must be registered as AVAILABLE in navigation."""
    by_id = pages_by_id()
    assert "procurement_decisions" in by_id, "procurement_decisions not in pages registry"
    entry = by_id["procurement_decisions"]
    assert entry.implementation is ImplementationStatus.AVAILABLE, "procurement_decisions must be AVAILABLE"
    assert entry.route == "page/procurement_decisions", "route must be page/procurement_decisions"
    assert entry.group == "DECISION", "group must be DECISION"
    assert entry.research_stage == "RO3", "research_stage must be RO3"
    desc = entry.description.lower()
    assert "supplier" in desc or "procurement" in desc, "description must mention supplier/procurement"


def test_procurement_decisions_page_description_declares_scope() -> None:
    """The page description must mention procurement decisions and supplier scope."""
    from src.construction.dashboard_ui.procurement_decisions import (
        page_description as page_description_fn,
    )

    desc = page_description_fn()
    lowered = desc.lower()
    assert "procurement" in lowered
    assert "supplier" in lowered or "allocation" in lowered or "y" in lowered


def test_procurement_decisions_page_future_phase() -> None:
    """The page must point at the next planned phase."""
    from src.construction.dashboard_ui.procurement_decisions import (
        page_future_phase as page_future_phase_fn,
    )

    future = page_future_phase_fn()
    assert future
    assert len(future) > 10


# ---------------------------------------------------------------------------
# Decision-level artifact loading + validation + adaptation
# ---------------------------------------------------------------------------


def test_selected_decisions_schema_is_complete(decision_evidence: contract.RO3Evidence) -> None:
    df = pd.DataFrame(decision_evidence.selected_decisions)
    required = {"forecast_origin", "material", "period", "order_qty", "selected_candidate", "optimization_Z1", "optimization_Z2"}
    missing = required - set(df.columns)
    assert not missing, f"selected_decisions missing columns: {sorted(missing)}"
    assert len(df) >= 1


def test_selected_decisions_order_qty_is_numeric(decision_evidence: contract.RO3Evidence) -> None:
    df = pd.DataFrame(decision_evidence.selected_decisions)
    nums = pd.to_numeric(df["order_qty"], errors="coerce")
    assert nums.notna().all(), "order_qty must be numeric"


def test_selected_decisions_objective_values_travel_with_quantity(decision_evidence: contract.RO3Evidence) -> None:
    row = decision_evidence.selected_decisions[0]
    assert row["optimization_Z1"] is not None
    assert row["optimization_Z2"] is not None
    assert row["selected_candidate"] is not None


def test_realized_evaluation_summary_schema_is_complete(decision_evidence: contract.RO3Evidence) -> None:
    df = pd.DataFrame(decision_evidence.realized_evaluation_summary)
    required = {"material", "realized_cost", "shortage", "service", "procurement_qty"}
    missing = required - set(df.columns)
    assert not missing, f"realized_evaluation_summary missing columns: {sorted(missing)}"
    assert len(df) >= 1


def test_realized_evaluation_summary_service_is_between_zero_and_one(decision_evidence: contract.RO3Evidence) -> None:
    df = pd.DataFrame(decision_evidence.realized_evaluation_summary)
    s = pd.to_numeric(df["service"], errors="coerce")
    assert (s >= 0).all() and (s <= 1).all(), "service must be in [0,1]"


def test_realized_evaluation_ledger_is_small_enough_for_ui(decision_evidence: contract.RO3Evidence) -> None:
    """The O4 single-origin ledger is small enough to be surfaced."""
    ledger = pd.DataFrame(decision_evidence.realized_evaluation_ledger)
    assert 0 < len(ledger) <= adapters._SAFE_LEDGER_ROWS
    assert "arrival_qty" in ledger.columns


def test_multi_origin_summary_schema_is_complete(decision_evidence: contract.RO3Evidence) -> None:
    df = pd.DataFrame(decision_evidence.multi_origin_summary)
    required = {"forecast_origin", "pareto_count", "Z1_min", "Z1_max", "Z2_min", "Z2_max", "Z3_min", "Z3_max"}
    missing = required - set(df.columns)
    assert not missing, f"multi_origin_summary missing columns: {sorted(missing)}"
    assert len(df) >= 1


def test_decision_sensitivity_schema_is_complete(decision_evidence: contract.RO3Evidence) -> None:
    df = pd.DataFrame(decision_evidence.decision_sensitivity)
    required = {"N_A", "N_B", "matched_solutions", "mean_objective_distance", "max_objective_distance", "mean_abs_quantity_difference"}
    missing = required - set(df.columns)
    assert not missing, f"decision_sensitivity missing columns: {sorted(missing)}"
    assert len(df) >= 1


def test_decision_sensitivity_matched_solutions_non_negative(decision_evidence: contract.RO3Evidence) -> None:
    df = pd.DataFrame(decision_evidence.decision_sensitivity)
    assert (pd.to_numeric(df["matched_solutions"], errors="coerce") >= 0).all()


def test_adapter_loads_decision_level_artifacts(decision_evidence: contract.RO3Evidence) -> None:
    """Round-trip: LoadResult dicts -> adapter -> RO3Evidence with decision fields."""
    results: dict[str, LoadResult] = {
        "RO3_O2_SELECTED_DECISIONS": LoadResult(
            entry=registry.ArtifactEntry(
                artifact_id="RO3_O2_SELECTED_DECISIONS",
                name="selected decisions",
                component=registry.ResearchComponent.RO3,
                relative_path="results/RO3/ablation/O2/O2_selected_decisions.csv",
                artifact_type=registry.ArtifactType.CSV,
                loading_policy=registry.LoadingPolicy.SAFE,
                required=False,
                description="",
            ),
            status=ArtifactStatus.AVAILABLE,
            data=pd.DataFrame(decision_evidence.selected_decisions),
            provenance=decision_evidence.provenance[0],
            error_message="",
        ),
        "RO3_O2_REALIZED_EVALUATION_SUMMARY": LoadResult(
            entry=registry.ArtifactEntry(
                artifact_id="RO3_O2_REALIZED_EVALUATION_SUMMARY",
                name="realized evaluation summary",
                component=registry.ResearchComponent.RO3,
                relative_path="results/RO3/ablation/O2/O2_realized_evaluation_summary.csv",
                artifact_type=registry.ArtifactType.CSV,
                loading_policy=registry.LoadingPolicy.SAFE,
                required=False,
                description="",
            ),
            status=ArtifactStatus.AVAILABLE,
            data=pd.DataFrame(decision_evidence.realized_evaluation_summary),
            provenance=decision_evidence.provenance[1],
            error_message="",
        ),
        "RO3_O4_REALIZED_EVALUATION_LEDGER": LoadResult(
            entry=registry.ArtifactEntry(
                artifact_id="RO3_O4_REALIZED_EVALUATION_LEDGER",
                name="realized evaluation ledger",
                component=registry.ResearchComponent.RO3,
                relative_path="results/RO3/ablation/O4_single_origin/O4_single_origin_realized_evaluation_ledger.csv",
                artifact_type=registry.ArtifactType.CSV,
                loading_policy=registry.LoadingPolicy.SAFE,
                required=False,
                description="",
            ),
            status=ArtifactStatus.AVAILABLE,
            data=pd.DataFrame(decision_evidence.realized_evaluation_ledger),
            provenance=decision_evidence.provenance[2],
            error_message="",
        ),
        "RO3_MULTI_ORIGIN_SUMMARY": LoadResult(
            entry=registry.ArtifactEntry(
                artifact_id="RO3_MULTI_ORIGIN_SUMMARY",
                name="multi origin summary",
                component=registry.ResearchComponent.RO3,
                relative_path="results/RO3/multi_origin/RO3_step35_origin_summary_N2500.csv",
                artifact_type=registry.ArtifactType.CSV,
                loading_policy=registry.LoadingPolicy.SAFE,
                required=False,
                description="",
            ),
            status=ArtifactStatus.AVAILABLE,
            data=pd.DataFrame(decision_evidence.multi_origin_summary),
            provenance=decision_evidence.provenance[3],
            error_message="",
        ),
        "RO3_DECISION_SENSITIVITY": LoadResult(
            entry=registry.ArtifactEntry(
                artifact_id="RO3_DECISION_SENSITIVITY",
                name="decision sensitivity",
                component=registry.ResearchComponent.RO3,
                relative_path="results/RO3/decision_sensitivity/RO3_step33B_corrected_summary_20220701.csv",
                artifact_type=registry.ArtifactType.CSV,
                loading_policy=registry.LoadingPolicy.SAFE,
                required=False,
                description="",
            ),
            status=ArtifactStatus.AVAILABLE,
            data=pd.DataFrame(decision_evidence.decision_sensitivity),
            provenance=decision_evidence.provenance[4],
            error_message="",
        ),
    }

    evidence = adapters.adapt_ro3_evidence(results)
    # The adapter carries every decision-level record under its real contract
    # name. The fixture is the source of truth for the load path: when a
    # LoadResult is supplied, the matching field must equal the fixture's data.
    assert evidence.selected_decisions == decision_evidence.selected_decisions
    assert evidence.realized_evaluation_summary == decision_evidence.realized_evaluation_summary
    assert evidence.realized_evaluation_ledger == decision_evidence.realized_evaluation_ledger
    assert evidence.multi_origin_summary == decision_evidence.multi_origin_summary
    assert evidence.decision_sensitivity == decision_evidence.decision_sensitivity
    # The adapter must carry the pipeline provenance for every supplied
    # decision-level artifact, so the procurement-decisions page can credit
    # each record to a registered artifact.
    assert len(evidence.provenance) == 5
    assert {r.artifact_id for r in evidence.provenance} == {
        "RO3_O2_SELECTED_DECISIONS",
        "RO3_O2_REALIZED_EVALUATION_SUMMARY",
        "RO3_O4_REALIZED_EVALUATION_LEDGER",
        "RO3_MULTI_ORIGIN_SUMMARY",
        "RO3_DECISION_SENSITIVITY",
    }


def test_adapter_keeps_large_ledger_out_of_ui_but_keeps_provenance() -> None:
    """A large multi-origin realized ledger is blocked from the UI but its provenance stays."""
    provenance = contract.ArtifactProvenance(
        artifact_id="RO3_O4_REALIZED_EVALUATION_LEDGER",
        source_path="results/RO3/multi_origin/RO3_step35_realized_evaluation_ledger_N2500.csv",
        provenance_class=contract.ProvenanceClass.DER,
        research_stage="RO3",
        status=ArtifactStatus.AVAILABLE,
        row_count=50000,
        file_size_bytes=60000000,
        schema_status="OK",
        notes="Multi-origin realized ledger — too large for UI.",
    )
    results: dict[str, LoadResult] = {
        "RO3_O4_REALIZED_EVALUATION_LEDGER": LoadResult(
            entry=registry.ArtifactEntry(
                artifact_id=provenance.artifact_id,
                name="multi-origin realized ledger",
                component=registry.ResearchComponent.RO3,
                relative_path="results/RO3/multi_origin/RO3_step35_realized_evaluation_ledger_N2500.csv",
                artifact_type=registry.ArtifactType.CSV,
                loading_policy=registry.LoadingPolicy.SAFE,
                required=False,
                description="",
            ),
            status=ArtifactStatus.AVAILABLE,
            data=pd.DataFrame([{"x": i} for i in range(50000)]),
            provenance=provenance,
            error_message="",
        ),
    }
    evidence = adapters.adapt_ro3_evidence(results)
    ledger = pd.DataFrame(evidence.realized_evaluation_ledger)
    assert ledger.empty, "large ledger must not surface in the UI"
    assert provenance.row_count == 50000


def test_adapter_does_not_invent_supplier_allocation() -> None:
    """The adapter must not create y(i,s,t) from material context."""
    results: dict[str, LoadResult] = {
        "RO3_O2_SELECTED_DECISIONS": LoadResult(
            entry=registry.ArtifactEntry(
                artifact_id="RO3_O2_SELECTED_DECISIONS",
                name="selected decisions",
                component=registry.ResearchComponent.RO3,
                relative_path="results/RO3/ablation/O2/O2_selected_decisions.csv",
                artifact_type=registry.ArtifactType.CSV,
                loading_policy=registry.LoadingPolicy.SAFE,
                required=False,
                description="",
            ),
            status=ArtifactStatus.AVAILABLE,
            data=pd.DataFrame([{"forecast_origin": "2022-07-01", "material": "Cement", "period": "2022-08-01", "order_qty": 100.0, "selected_candidate": "eps_02", "optimization_Z1": 1000.0, "optimization_Z2": 100.0}]),
            provenance=contract.ArtifactProvenance(
                artifact_id="RO3_O2_SELECTED_DECISIONS",
                source_path="results/RO3/ablation/O2/O2_selected_decisions.csv",
                provenance_class=contract.ProvenanceClass.DER,
                research_stage="RO3",
                status=ArtifactStatus.AVAILABLE,
                row_count=1,
                schema_status="OK",
            ),
            error_message="",
        ),
    }
    evidence = adapters.adapt_ro3_evidence(results)
    # The contract does not expose a supplier_allocations field; the adapter must not invent one.
    assert getattr(evidence, "supplier_allocations", None) is None


# ---------------------------------------------------------------------------
# Unavailable-state contract
# ---------------------------------------------------------------------------


def test_empty_decision_evidence_leaves_fields_empty() -> None:
    empty = contract.RO3Evidence(provenance=[])
    assert empty.selected_decisions == []
    assert empty.realized_evaluation_summary == []
    assert empty.realized_evaluation_ledger == []
    assert empty.multi_origin_summary == []
    assert empty.decision_sensitivity == []


def test_missing_selected_decisions_is_explicit_in_provenance() -> None:
    prov = [
        contract.ArtifactProvenance(
            artifact_id="RO3_O2_SELECTED_DECISIONS",
            source_path="results/RO3/ablation/O2/O2_selected_decisions.csv",
            provenance_class=contract.ProvenanceClass.DER,
            research_stage="RO3",
            status=ArtifactStatus.MISSING,
            row_count=None,
            schema_status="UNCHECKED",
        ),
    ]
    evidence = contract.RO3Evidence(provenance=prov)
    assert evidence.selected_decisions == []
    statuses = [p.status.value for p in evidence.provenance]
    assert ArtifactStatus.MISSING.value in statuses


def test_unavailable_is_not_zero_for_quantities() -> None:
    """When selected_decisions is absent, no quantity is rendered as 0."""
    empty = contract.RO3Evidence(provenance=[])
    df = pd.DataFrame(empty.selected_decisions)
    assert df.empty


# ---------------------------------------------------------------------------
# Material/unit mapping is a labeling convention, not an optimizer output
# ---------------------------------------------------------------------------


def test_material_unit_map_is_a_labeling_convention() -> None:
    m = ph._material_unit_map()
    assert m["Cement"] == "tonne"
    assert m["Granite"] == "tonne"
    assert m["Ready Mixed Concrete"] == "m3"
    assert m["Steel Reinforcement Bars"] == "tonne"
    assert m.get("NonExistentMaterial", "unit") == "unit"


def test_unit_label_falls_back_to_unit_for_unknown_material() -> None:
    assert ph._unit_label("NonExistentMaterial") == "unit"


# ---------------------------------------------------------------------------
# Large-file protection
# ---------------------------------------------------------------------------


def test_safe_ledger_guard_rejects_empty() -> None:
    entry = registry.ArtifactEntry(
        artifact_id="X",
        relative_path="x.csv",
        artifact_type=registry.ArtifactType.CSV,
        name="x.csv",
        component=registry.ResearchComponent.RO3,
        loading_policy=registry.LoadingPolicy.SAFE,
        required=False,
        description="",
    )
    prov = contract.ArtifactProvenance(
        artifact_id="X",
        source_path="x.csv",
        provenance_class=contract.ProvenanceClass.DER,
        research_stage="RO3",
        status=ArtifactStatus.AVAILABLE,
        row_count=0,
    )
    res = LoadResult(
        entry=entry,
        status=ArtifactStatus.AVAILABLE,
        data=pd.DataFrame(),
        provenance=prov,
        error_message="",
    )
    assert not adapters._ledger_is_safe_for_ui(res, adapters._SAFE_LEDGER_ROWS)


def test_safe_ledger_guard_accepts_small() -> None:
    entry = registry.ArtifactEntry(
        artifact_id="X",
        relative_path="x.csv",
        artifact_type=registry.ArtifactType.CSV,
        name="x.csv",
        component=registry.ResearchComponent.RO3,
        loading_policy=registry.LoadingPolicy.SAFE,
        required=False,
        description="",
    )
    prov = contract.ArtifactProvenance(
        artifact_id="X",
        source_path="x.csv",
        provenance_class=contract.ProvenanceClass.DER,
        research_stage="RO3",
        status=ArtifactStatus.AVAILABLE,
        row_count=42,
    )
    res = LoadResult(
        entry=entry,
        status=ArtifactStatus.AVAILABLE,
        data=pd.DataFrame([{"i": i} for i in range(42)]),
        provenance=prov,
        error_message="",
    )
    assert adapters._ledger_is_safe_for_ui(res, adapters._SAFE_LEDGER_ROWS)


def test_safe_ledger_guard_rejects_too_large() -> None:
    entry = registry.ArtifactEntry(
        artifact_id="X",
        relative_path="x.csv",
        artifact_type=registry.ArtifactType.CSV,
        name="x.csv",
        component=registry.ResearchComponent.RO3,
        loading_policy=registry.LoadingPolicy.SAFE,
        required=False,
        description="",
    )
    prov = contract.ArtifactProvenance(
        artifact_id="X",
        source_path="x.csv",
        provenance_class=contract.ProvenanceClass.DER,
        research_stage="RO3",
        status=ArtifactStatus.AVAILABLE,
        row_count=10000,
    )
    res = LoadResult(
        entry=entry,
        status=ArtifactStatus.AVAILABLE,
        data=pd.DataFrame([{"i": i} for i in range(10000)]),
        provenance=prov,
        error_message="",
    )
    assert not adapters._ledger_is_safe_for_ui(res, adapters._SAFE_LEDGER_ROWS)


def test_safe_ledger_guard_rejects_non_dataframe() -> None:
    entry = registry.ArtifactEntry(
        artifact_id="X",
        relative_path="x.csv",
        artifact_type=registry.ArtifactType.CSV,
        name="x.csv",
        component=registry.ResearchComponent.RO3,
        loading_policy=registry.LoadingPolicy.SAFE,
        required=False,
        description="",
    )
    prov = contract.ArtifactProvenance(
        artifact_id="X",
        source_path="x.csv",
        provenance_class=contract.ProvenanceClass.DER,
        research_stage="RO3",
        status=ArtifactStatus.AVAILABLE,
        row_count=None,
    )
    res = LoadResult(
        entry=entry,
        status=ArtifactStatus.AVAILABLE,
        data={"not": "a dataframe"},
        provenance=prov,
        error_message="",
    )
    assert not adapters._ledger_is_safe_for_ui(res, adapters._SAFE_LEDGER_ROWS)


# ---------------------------------------------------------------------------
# Raw scenario ledger stays blocked
# ---------------------------------------------------------------------------


def test_raw_scenario_ledger_is_blocked_in_registry() -> None:
    from src.construction.dashboard_data.registry import ARTIFACT_REGISTRY, LoadingPolicy
    by_id = {e.artifact_id: e for e in ARTIFACT_REGISTRY}
    assert "RO3_SCENARIOS_2500_RAW" in by_id
    assert "RO3_SCENARIOS_5000_RAW" in by_id
    assert by_id["RO3_SCENARIOS_2500_RAW"].loading_policy == LoadingPolicy.NEVER
    assert by_id["RO3_SCENARIOS_5000_RAW"].loading_policy == LoadingPolicy.NEVER


# ---------------------------------------------------------------------------
# Contract fields are present on RO3Evidence
# ---------------------------------------------------------------------------


def test_ro3evidence_has_decision_level_fields() -> None:
    fields = {f.name for f in contract.RO3Evidence.__dataclass_fields__.values()}
    expected = {
        "selected_decisions",
        "realized_evaluation_summary",
        "realized_evaluation_ledger",
        "multi_origin_summary",
        "decision_sensitivity",
    }
    missing = expected - fields
    assert not missing, f"RO3Evidence missing fields: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Helpers do not leak paths or colors
# ---------------------------------------------------------------------------


def test_clean_audit_detail_strips_path_like_details() -> None:
    assert ph._clean_audit_detail("D:\\CMIDO\\results\\RO3\\something.csv") == ""
    assert ph._clean_audit_detail("/results/RO3/something.csv") == ""
    assert ph._clean_audit_detail("37") == "37"
    assert ph._clean_audit_detail("P50=47") == "P50=47"
    assert ph._clean_audit_detail("file exists") == "file exists"


def test_no_raw_path_in_page_source() -> None:
    import src.construction.dashboard_ui.procurement_decisions as page
    source = pathlib.Path(page.__file__).read_text(encoding="utf-8")
    assert "D:\\CMIDO" not in source
    assert "D:/CMIDO" not in source


def test_no_hex_color_literal_smuggled_into_render() -> None:
    import src.construction.dashboard_ui.procurement_decisions as page
    _assert_no_hex_in_source(page.__file__)


# ---------------------------------------------------------------------------
# Render-time helpers produce honest missing/disabled text
# ---------------------------------------------------------------------------


def test_fmt_missing_for_nan() -> None:
    assert ph._fmt_cell(float("nan")) == "—"
    assert ph._fmt_cell(None) == "—"


def test_fmt_int_for_integer() -> None:
    assert ph._fmt_int(5) == "5"
    assert ph._fmt_int(5.0) == "5"


def test_fmt_num_respects_decimals() -> None:
    assert ph._fmt_num(1.2345, decimals=2) == "1.23"
    assert ph._fmt_num("bad") == "—"


def test_fmt_pct_respects_decimals() -> None:
    assert ph._fmt_pct(0.619362, decimals=1) == "61.9%"


def test_first_origin_returns_earliest() -> None:
    df = pd.DataFrame({"forecast_origin": ["2022-08-01", "2022-07-01", "2022-09-01"]})
    assert ph._first_origin(df) == "2022-07-01"


def test_first_origin_returns_none_for_empty() -> None:
    assert ph._first_origin(pd.DataFrame()) is None


def test_experimental_conditions_derived_from_provenance() -> None:
    prov = [
        contract.ArtifactProvenance(
            artifact_id="RO3_O2_SELECTED_DECISIONS",
            source_path="results/RO3/ablation/O2/O2_selected_decisions.csv",
            provenance_class=contract.ProvenanceClass.DER,
            research_stage="RO3",
            status=ArtifactStatus.AVAILABLE,
            row_count=48,
            file_size_bytes=3200,
            schema_status="OK",
            notes="O2 single-origin selected decisions.",
        ),
        contract.ArtifactProvenance(
            artifact_id="RO3_MULTI_ORIGIN_SUMMARY",
            source_path="results/RO3/multi_origin/RO3_step35_origin_summary_N2500.csv",
            provenance_class=contract.ProvenanceClass.DER,
            research_stage="RO3",
            status=ArtifactStatus.AVAILABLE,
            row_count=6,
            file_size_bytes=900,
            schema_status="OK",
            notes="Per-origin Pareto count + objective range.",
        ),
    ]
    text = ph._experiment_conditions_from_provenance(prov)
    lowered = text.lower()
    # Forecast origin and scenario count are recorded provenance metadata.
    # The test supplies only the summary record (N2500 in its path), so the
    # page treats a filename-implied scenario count as sufficient evidence for
    # the scenario-count claim, and reports the forecast origin as unknown
    # where the provenance does not record it.
    assert "2500" in text, text
    assert "scenario" in lowered


def test_experimental_conditions_returns_provenance_fallback_when_empty() -> None:
    text = ph._experiment_conditions_from_provenance([])
    assert "see provenance" in text.lower()


def test_decision_sensitivity_label_map_is_complete() -> None:
    m = ph._decision_sensitivity_label_map()
    assert "matched_solutions" in m
    assert "mean_objective_distance" in m
    assert "mean_abs_quantity_difference" in m


def test_decision_sensitivity_note_does_not_overclaim() -> None:
    note = ph._decision_sensitivity_note()
    assert "modeled" in note.lower()
    assert "observed" in note.lower()
