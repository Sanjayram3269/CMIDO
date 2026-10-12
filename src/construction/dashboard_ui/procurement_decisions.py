# ---------------------------------------------------------------------------
# CMIDO 10A.10 — Procurement Decisions workspace
#
# Read-only, schema-validated, provenance-aware rendering of the RO3
# procurement-decision evidence. This module does NOT run research
# computations, does NOT load raw scenario ledgers, and does NOT infer any
# supplier-allocation, safety-stock, or feasibility values that are not present
# in the registered artifacts.
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Any

import pandas as pd

from src.construction.dashboard_data.contract import (
    DashboardSnapshot,
    RO3Evidence,
)
from src.construction.dashboard_ui import components
from src.construction.dashboard_ui.navigation import (
    page_by_id,
    page_description,
    page_future_phase,
    page_is_planned,
)
from src.construction.dashboard_ui.sections import (
    build_page_header,
)
# Helpers shared with ro3.py (decoupled from the research engine)
from ._procurement_helpers import (
    _bulleted,
    _clean_audit_detail,
    _decision_sensitivity_label_map,
    _decision_sensitivity_note,
    _experiment_conditions_from_provenance,
    _first_origin,
    _fmt_cell,
    _fmt_int,
    _fmt_num,
    _fmt_pct,
    _frame,
    _is_true,
    _labeled_paragraph,
    _metric_direction,
    _metric_label,
    _metric_unit,
    _numbered_list,
    _origin_section_label,
    _prov_get,
    _status_text,
    _material_unit_map,
    _unit_label,
)

PAGE_ID = "procurement_decisions"
RESEARCH_STAGE = "10A.10"


# ---------------------------------------------------------------------------
# Section-level framing
# ---------------------------------------------------------------------------


def _page_title() -> str:
    return "Procurement Decisions"


def _page_subtitle() -> str:
    return "RO3 procurement-decision evidence: what the optimizer selected, and what remains out of scope."


def _render_decision_overview(evidence: RO3Evidence, provenance_rows: list[dict[str, Any]]) -> None:
    """Top-level framing: scope, evidence status, and scientific-integrity callouts."""
    total_artifacts = len(provenance_rows)
    available_artifacts = sum(1 for r in provenance_rows if r["status"] == "AVAILABLE")
    if available_artifacts == total_artifacts:
        evidence_state = "available"
    elif available_artifacts:
        evidence_state = "partial"
    else:
        evidence_state = "empty"
    components.render_section_header(
        title="Procurement decision evidence",
        subtitle="RO3 selected decisions, realized evaluation, and decision sensitivity — displayed only where genuine artifacts exist.",
        research_stage="10A.10",
        evidence_state=evidence_state,
        methodology="Registry-driven (10A.2-B). Artifacts are loaded, schema-validated and provenance-tagged before any rendering; nothing is invented in the UI.",
        provenance="See provenance inventory below.",
        uncertainty="Decision artifacts are available only when the corresponding registered file is present and schema-valid. Missing artifacts remain explicitly unavailable.",
    )

    components.render_paragraph(
        {
            "label": "What this page reports",
            "body": [
                "This is the dedicated Procurement Decisions workspace. It mirrors the decision-level RO3 evidence that sits "
                "alongside the RO3 Pareto evidence: explicitly registered artifacts for selected procurement decisions, the "
                "realized evaluation of those decisions, the per-origin Pareto summary, and the decision-sensitivity summary.",
                "",
                "The page is intentionally narrow: it displays only evidence that is genuinely registered and available, and it "
                "keeps unavailable decision variables — supplier allocations y(i,s,t), safety stock ss(i,t), storage-capacity "
                "constraints, and supplier-disruption probabilities — explicitly unavailable rather than pretending they are zero.",
            ],
        }
    )

    components.render_inline_label_values(
        [
            _labeled_paragraph(
                "Decision variables with registered artifacts",
                [
                    "q(i,t) — monthly-ahead procurement quantity per material (selected decisions + realized evaluation).",
                    "Realization outcomes — realized cost, shortage, service, procurement quantity and ending inventory per material (realized evaluation summary).",
                    "Per-origin Pareto count + objective range — how many nondominated solutions each forecast origin produced and the resulting Z1/Z2/Z3 span (multi-origin summary).",
                    "Decision sensitivity — how stable the selected decisions are when the scenario sample size changes (decision sensitivity summary).",
                ],
            ),
            _labeled_paragraph(
                "Decision variables explicitly out of scope",
                [
                    "y(i,s,t) — supplier allocation is NOT a decision output of this experiment. The frozen formulation audit records "
                    "supplier_specific_allocation_not_claimed and supplier_disruption_probability_excluded as deliberate design choices, "
                    "not as missing data.",
                    "ss(i,t) — safety stock is NOT a decision output of this experiment. No safety-stock artifact is registered, and none "
                    "is inferred from procurement quantities.",
                    "Storage capacity / supplier capacity constraints — NOT modeled as active constraints in this experiment. Feasibility is "
                    "not asserted where constraint evidence is absent.",
                    "Recommended procurement plan — NOT produced by this page. The selected solution is one nondominated candidate from the "
                    "Pareto set, not an endorsed procurement schedule.",
                ],
            ),
            _labeled_paragraph(
                "Experiment conditions (derived from provenance)",
                _experiment_conditions_from_provenance(provenance_rows),
            ),
        ]
    )


def _render_decision_evidence_status(evidence: RO3Evidence) -> None:
    """Compact status table for the five decision-level artifacts."""
    components.render_section_header(
        title="Decision evidence status",
        subtitle="Each decision-level artifact is either available with its schema, or explicitly unavailable.",
        research_stage="10A.10",
    )

    rows = [
        {
            "artifact": "Selected decisions (q(i,t) with period + selected candidate)",
            "expected": "forecast_origin, material, period, order_qty, selected_candidate, optimization_Z1[, optimization_Z3]",
            "status": "AVAILABLE" if not _frame(evidence.selected_decisions).empty else "UNAVAILABLE",
            "rows": _fmt_int(len(evidence.selected_decisions)),
        },
        {
            "artifact": "Realized evaluation summary (per-material realized outcomes)",
            "expected": "material, realized_cost, shortage, service, procurement_qty, [ending_inventory, procurement_events]",
            "status": "AVAILABLE" if not _frame(evidence.realized_evaluation_summary).empty else "UNAVAILABLE",
            "rows": _fmt_int(len(evidence.realized_evaluation_summary)),
        },
        {
            "artifact": "Realized evaluation ledger (per-period realization)",
            "expected": "forecast_origin, material, period, order_qty, arrival_qty, demand, price, shortage, ending_inventory, procurement_cost, holding_cost",
            "status": "AVAILABLE" if not _frame(evidence.realized_evaluation_ledger).empty else "UNAVAILABLE (too large to render)",
            "rows": _fmt_int(len(evidence.realized_evaluation_ledger)),
        },
        {
            "artifact": "Multi-origin summary (per-origin Pareto count + objective range)",
            "expected": "forecast_origin, pareto_count, Z1_min..Z3_max, runtime_total_sec",
            "status": "AVAILABLE" if not _frame(evidence.multi_origin_summary).empty else "UNAVAILABLE",
            "rows": _fmt_int(len(evidence.multi_origin_summary)),
        },
        {
            "artifact": "Decision sensitivity (pairwise corrected summary)",
            "expected": "N_A, N_B, matched_solutions, mean/max_objective_distance, mean/max_abs_quantity_difference, mean/max_total_procurement_normalized_difference, mean_zero_safe_quantity_relative_difference",
            "status": "AVAILABLE" if not _frame(evidence.decision_sensitivity).empty else "UNAVAILABLE",
            "rows": _fmt_int(len(evidence.decision_sensitivity)),
        },
    ]

    components.render_table(pd.DataFrame(rows))


def _render_material_quantities(evidence: RO3Evidence) -> None:
    """Material-level procurement quantities and units from the selected-decisions artifact."""
    dec_df = _frame(evidence.selected_decisions)
    if dec_df.empty:
        components.render_status_banner(
            "No selected-decisions artifact is available for this workspace.",
            status="empty",
        )
        components.render_paragraph(
            {
                "label": "Why unavailable",
                "body": [
                    "The selected-decisions artifact is the only registered artifact that pairs a procurement quantity q(i,t) with the "
                    "calendar period in which it applies and with the selected candidate that produced it. It is not present here, so the "
                    "material-level quantity view cannot be rendered without inventing values.",
                    "",
                    "The Pareto-decisions artifact (q(i,t) per Pareto solution, per material, per month-ahead) is available on the RO3 "
                    "Pareto page and is the closest available evidence for quantities. It is deliberately not re-displayed here because it "
                    "does not carry the selected-candidate or period information that a procurement-decision view requires.",
                ],
            }
        )
        return

    components.render_section_header(
        title="Material-level procurement quantities",
        subtitle="Each row is one selected procurement decision: a quantity q(i,t) for a material in a calendar period, taken from a single selected candidate.",
        research_stage="10A.10",
        evidence_state="AVAILABLE",
        methodology="Registry artifact RO3_O2_SELECTED_DECISIONS.",
        provenance="See provenance inventory.",
    )

    # Honest preview: a single forecast origin and a controlled preview row cap.
    preview_df = dec_df.copy()
    preview_df["order_qty"] = preview_df["order_qty"].apply(lambda v: _fmt_num(v, 2))
    preview_df["optimization_Z1"] = preview_df["optimization_Z1"].apply(lambda v: _fmt_num(v, 2))
    preview_df["optimization_Z2"] = preview_df["optimization_Z2"].apply(lambda v: _fmt_num(v, 2))
    if "optimization_Z3" in preview_df.columns:
        preview_df["optimization_Z3"] = preview_df["optimization_Z3"].apply(lambda v: _fmt_num(v, 2))

    preview_df["unit"] = preview_df["material"].map(_unit_label)

    components.render_table(
        preview_df.head(50)[
            [
                "forecast_origin",
                "material",
                "unit",
                "period",
                "order_qty",
                "selected_candidate",
                "optimization_Z1",
                "optimization_Z2",
            ]
            + (["optimization_Z3"] if "optimization_Z3" in preview_df.columns else [])
        ]
    )

    # Objective framing: all three RO3 objectives are minimization objectives.
    components.render_paragraph(
        {
            "label": "Objective directions",
            "body": [
                "Z1 — procurement cost (minimize).",
                "Z2 — expected shortage (minimize).",
                "Z3 — CVaR_0.95 shortage (minimize).",
                "",
                "All displayed objective values are minimization objectives; smaller is better for each. The selected candidate is one "
                "nondominated solution from the Pareto set for that origin, not a single best solution.",
            ],
        }
    )

    # Material coverage: how many distinct materials and periods are present.
    materials = preview_df["material"].dropna().unique().tolist()
    periods = preview_df["period"].dropna().unique().tolist()
    components.render_inline_label_values(
        [
            _labeled_paragraph("Materials present", ", ".join(materials) if materials else "None"),
            _labeled_paragraph("Periods present", f"{len(periods)} calendar periods" if periods else "None"),
            _labeled_paragraph("Unit convention", "Quantities are shown in each material's native unit (tonne for Cement/Granite/Steel; m3 for Ready Mixed Concrete). The unit is a labeling convention, not an optimizer output."),
        ]
    )


def _render_timing_and_origin_comparison(evidence: RO3Evidence) -> None:
    """Procurement timing and origin comparisons across available artifacts."""
    dec_df = _frame(evidence.selected_decisions)
    mob_df = _frame(evidence.multi_origin_summary)

    if dec_df.empty and mob_df.empty:
        components.render_status_banner(
            "No timing- or origin-level decision artifact is available for this workspace.",
            status="empty",
        )
        components.render_paragraph(
            {
                "label": "Why unavailable",
                "body": [
                    "Procurement timing (which calendar periods receive orders, and how many procurement events occur) is read from the "
                    "selected-decisions artifact. Origin-level comparison (how many Pareto solutions each forecast origin produced and the "
                    "resulting objective range) is read from the multi-origin summary artifact. Neither is available here, so no timing or "
                    "origin comparison can be shown without inventing values.",
                ],
            }
        )
        return

    # Timing view (selected-decisions artifact only).
    if not dec_df.empty:
        components.render_section_header(
            title="Procurement timing",
            subtitle="Which calendar periods receive a non-zero procurement quantity under the selected candidate.",
            research_stage="10A.10",
            evidence_state="AVAILABLE",
        )

        order_by_period = dec_df.copy()
        order_by_period["order_qty_num"] = pd.to_numeric(order_by_period["order_qty"], errors="coerce")
        timing_rows = (
            order_by_period.groupby(["forecast_origin", "material", "period"], dropna=False)
            .agg(
                order_qty=("order_qty_num", "sum"),
                procurement_events=("order_qty_num", lambda s: int((s > 0).sum())),
                selected_candidate=("selected_candidate", "first"),
            )
            .reset_index()
        )
        timing_rows["order_qty"] = timing_rows["order_qty"].apply(lambda v: _fmt_num(v, 2))
        timing_rows["unit"] = timing_rows["material"].map(_unit_label)

        components.render_table(
            timing_rows.head(50)[
                ["forecast_origin", "material", "unit", "period", "order_qty", "procurement_events", "selected_candidate"]
            ]
        )

        components.render_paragraph(
            {
                "label": "Reading this timing view",
                "body": [
                    "A procurement event is any period with order_qty > 0 under the selected candidate. The order_qty summed here is the "
                    "quantity selected by the optimizer for that material in that period; it is not a realized arrival and it is not a "
                    "safety-stock level.",
                    "",
                    "The period column is a calendar month (e.g. 2022-08-01). The forecast_origin column is the month whose demand was being "
                    "forecast when the decision was computed (e.g. 2022-07-01). These are distinct concepts and are kept distinct here.",
                ],
            }
        )

    # Origin comparison view (multi-origin summary only).
    if not mob_df.empty:
        components.render_section_header(
            title="Per-origin Pareto summary",
            subtitle="For each forecast origin: how many nondominated solutions were found and the resulting objective range.",
            research_stage="10A.10",
            evidence_state="AVAILABLE",
        )

        mob_preview = mob_df.copy()
        for col in ["Z1_min", "Z1_median", "Z1_max", "Z2_min", "Z2_median", "Z2_max", "Z3_min", "Z3_median", "Z3_max", "runtime_total_sec"]:
            if col in mob_preview.columns:
                mob_preview[col] = mob_preview[col].apply(lambda v: _fmt_num(v, 2))

        components.render_table(mob_preview.head(50))

        components.render_paragraph(
            {
                "label": "Reading this origin comparison",
                "body": [
                    "Each row summarizes one forecast origin's nondominated set: pareto_count is the number of Pareto solutions found, and "
                    "Z1_min..Z3_max give the span of cost / expected shortage / CVaR_0.95 shortage across those solutions.",
                    "",
                    "This is a description of the Pareto frontier for each origin, not a statement that any one solution was selected for "
                    "procurement. The selected candidate lives in the selected-decisions artifact and is one point inside this frontier.",
                ],
            }
        )


def _render_supplier_and_capacity(evidence: RO3Evidence) -> None:
    """Supplier allocation, supplier capacity, and capacity constraints — out of scope."""
    components.render_section_header(
        title="Supplier allocation and capacity",
        subtitle="Not decision outputs of this experiment.",
        research_stage="10A.10",
    )

    components.render_status_banner(
        "Supplier allocation y(i,s,t), supplier-capacity constraints, and supplier-disruption probabilities are NOT available.",
        status="attention",
    )

    components.render_paragraph(
        {
            "label": "What this means",
            "body": [
                "The RO3 experiment does not model supplier allocation as a decision variable. The frozen formulation audit records two relevant "
                "design decisions:",
                "",
                " - supplier_specific_allocation_not_claimed: pass — the model intentionally does not claim a supplier-specific allocation.",
                " - supplier_disruption_probability_excluded: pass — supplier-disruption probability is intentionally excluded from the model.",
                "",
                "Because of that design, no artifact in this repository contains supplier allocations y(i,s,t), supplier-capacity constraints, or "
                "supplier-disruption probabilities. Nothing on this page infers such values from aggregate material quantities.",
            ],
        }
    )

    components.render_paragraph(
        {
            "label": "Why supplier context is not supplier decisions",
            "body": [
                "The repository contains supplier context (material supplier, unit cost, lead time, minimum order quantity, order frequency) in the "
                "data model. That context is used by the formulation to define the procurement environment; it is NOT evidence that the optimizer "
                "selected a particular supplier, nor is it evidence of a supplier-level decision variable.",
                "",
                "Supplier presence is therefore shown only as context on the Materials & Resources page, never as a procurement decision here.",
            ],
        }
    )

    components.render_paragraph(
        {
            "label": "What would be needed to make this section available",
            "body": [
                "To report supplier allocations here, the research would need to produce a genuine supplier-allocation decision artifact — for "
                "example a y(i,s,t) ledger mapping material i, supplier s, and period t to an allocated quantity — and register that artifact with "
                "the 10A.2-B registry. Until then, supplier allocation remains explicitly unavailable, not zero.",
            ],
        }
    )


def _render_inventory_and_safety_stock(evidence: RO3Evidence) -> None:
    """Inventory and safety-stock decisions — out of scope."""
    components.render_section_header(
        title="Inventory and safety-stock decisions",
        subtitle="Not decision outputs of this experiment.",
        research_stage="10A.10",
    )

    components.render_status_banner(
        "Safety stock ss(i,t) is NOT available; realized ending inventory is shown only where the realized-evaluation summary provides it.",
        status="attention",
    )

    # If the realized-evaluation summary carries ending_inventory, show it as a realized outcome,
    # not as a decision variable.
    rps_df = _frame(evidence.realized_evaluation_summary)
    if not rps_df.empty and "ending_inventory" in rps_df.columns:
        components.render_paragraph(
            {
                "label": "Ending inventory (realized outcome, not a decision)",
                "body": [
                    "The realized-evaluation summary may report ending_inventory as an outcome of the selected decisions under the realized demand "
                    "path. This is a realized ending inventory, not a safety-stock decision and not a planned inventory target.",
                    "",
                    "Safety stock ss(i,t) is a separate planning concept; no safety-stock artifact is registered for this experiment, and no value is "
                    "inferred from realized ending inventory.",
                ],
            }
        )
        inv_preview = rps_df[["material", "ending_inventory"]].copy()
        inv_preview["ending_inventory"] = inv_preview["ending_inventory"].apply(lambda v: _fmt_num(v, 2))
        components.render_table(inv_preview.head(50))
    else:
        components.render_paragraph(
            {
                "label": "Ending inventory",
                "body": [
                    "No realized-evaluation summary artifact is available here, so ending inventory is not shown. Even where realized ending inventory "
                    "is available, it is an outcome, not a safety-stock decision.",
                ],
            }
        )

    components.render_paragraph(
        {
            "label": "Safety stock",
            "body": [
                "No safety-stock artifact is registered for this experiment. Safety stock ss(i,t) is therefore explicitly unavailable on this page.",
                "",
                "To make safety stock available, the research would need to produce a genuine safety-stock decision artifact (e.g. a ss(i,t) ledger or "
                "a safety-stock policy output) and register it with the 10A.2-B registry. Until then, safety stock is not zero — it is not modeled.",
            ],
        }
    )


def _render_feasibility_and_shortage(evidence: RO3Evidence) -> None:
    """Feasibility, shortage, and constraint status."""
    rps_df = _frame(evidence.realized_evaluation_summary)
    dec_df = _frame(evidence.selected_decisions)

    components.render_section_header(
        title="Feasibility, shortage and constraint status",
        subtitle="Shortage is reported where realized evaluation is available; feasibility is not asserted where constraint evidence is absent.",
        research_stage="10A.10",
    )

    if rps_df.empty:
        components.render_status_banner(
            "No realized-evaluation summary is available, so shortage outcomes cannot be reported here.",
            status="empty",
        )
        components.render_paragraph(
            {
                "label": "Why unavailable",
                "body": [
                    "Shortage and service outcomes are read from the realized-evaluation summary artifact. That artifact is not present here, so the "
                    "feasibility / shortage view cannot be rendered without inventing values.",
                ],
            }
        )
        return

    components.render_paragraph(
        {
            "label": "Shortage and service (realized outcomes)",
            "body": [
                "Where the realized-evaluation summary is available, it reports realized_cost, shortage, service, procurement_qty, procurement_events "
                "and ending_inventory per material. These are outcomes of the selected decisions under the realized demand path for that experiment — "
                "not predictions, and not guarantees.",
            ],
        }
    )

    shortage_preview = rps_df.copy()
    for col in ["realized_cost", "shortage", "service", "procurement_qty", "procurement_events", "ending_inventory"]:
        if col in shortage_preview.columns:
            if col in ("service",):
                shortage_preview[col] = shortage_preview[col].apply(lambda v: _fmt_pct(v, 1))
            elif col in ("procurement_events",):
                shortage_preview[col] = shortage_preview[col].apply(lambda v: _fmt_int(v))
            else:
                shortage_preview[col] = shortage_preview[col].apply(lambda v: _fmt_num(v, 2))

    components.render_table(
        shortage_preview.head(50)[
            [
                c
                for c in [
                    "material",
                    "realized_cost",
                    "shortage",
                    "service",
                    "procurement_qty",
                    "procurement_events",
                    "ending_inventory",
                ]
                if c in shortage_preview.columns
            ]
        ]
    )

    components.render_paragraph(
        {
            "label": "Feasibility and constraints",
            "body": [
                "Feasibility is not asserted as a standalone claim on this page because no constraint-satisfaction artifact is registered for this "
                "experiment. The absence of explicit capacity, storage, and supplier-disruption constraints means that feasibility cannot be read off "
                "from the available evidence.",
                "",
                "This is a deliberate limitation, not a failure to load data: the model does not include those constraints, so there is no constraint "
                "evidence to surface.",
            ],
        }
    )


def _render_tradeoffs(evidence: RO3Evidence) -> None:
    """Cost–service–resilience trade-offs via Pareto evidence and objective framing."""
    pareto_df = _frame(evidence.pareto_summary)
    sel_df = _frame(evidence.selected_decisions)

    components.render_section_header(
        title="Cost–service–resilience trade-offs",
        subtitle="RO3 trades procurement cost against expected shortage and tail (CVaR_0.95) shortage. Trade-offs are visible where Pareto evidence exists.",
        research_stage="10A.10",
    )

    if pareto_df.empty:
        components.render_status_banner(
            "No Pareto evidence is available on this workspace; trade-off view is limited to what the selected-decisions artifact carries.",
            status="empty",
        )

    if not pareto_df.empty:
        components.render_paragraph(
            {
                "label": "Pareto evidence (per-origin objective triples)",
                "body": [
                    "The registered RO3_PARETO_ALL_ORIGINS artifact carries one row per nondominated solution per forecast origin with Z1 (cost), "
                    "Z2 (expected shortage) and Z3 (CVaR_0.95 shortage). All three are minimization objectives.",
                    "",
                    "That Pareto evidence lives on the RO3 Pareto page and is not re-rendered here as a standalone scatter. The procurement-decisions "
                    "page instead reports the decisions that sit on or near that frontier (selected decisions) and their realized outcomes.",
                ],
            }
        )

    if not sel_df.empty:
        components.render_paragraph(
            {
                "label": "Trade-off framing for the selected candidate",
                "body": [
                    "Each selected procurement decision carries the Z1/Z2 (and, for O4, Z3) values of the selected candidate for that origin. Those "
                    "objectives describe where the selected candidate sits in the trade-off space relative to the other nondominated solutions.",
                    "",
                    "The realized shortage and service in the realized-evaluation summary describe what actually happened when those decisions were "
                    "evaluated against realized demand — a separate lens from the objective values used during optimization.",
                ],
            }
        )

    components.render_paragraph(
        {
            "label": "What this page does NOT claim",
            "body": [
                "This page does not pick a preferred operating point on the Pareto frontier. The selected candidate is one nondominated solution, not "
                "the single best cost/service/resilience compromise.",
                "",
                "Trade-offs are reported as evidence, not as recommendations.",
            ],
        }
    )


def _render_sensitivity(evidence: RO3Evidence) -> None:
    """Scenario sensitivity and alternative decision comparison."""
    sens_df = _frame(evidence.decision_sensitivity)

    components.render_section_header(
        title="Scenario sensitivity and alternative decision comparison",
        subtitle="How stable the selected decisions are when the scenario sample size changes.",
        research_stage="10A.10",
    )

    if sens_df.empty:
        components.render_status_banner(
            "No decision-sensitivity artifact is available for this workspace.",
            status="empty",
        )
        components.render_paragraph(
            {
                "label": "Why unavailable",
                "body": [
                    "Decision sensitivity is read from the registered pairwise corrected-summary artifact (RO3_step33B_corrected_summary). It compares "
                    "the epsilon-constraint solutions produced under different scenario sample sizes to assess how much the decisions change when the "
                    "scenario basis changes.",
                    "",
                    "That artifact is not present here, so no sensitivity comparison can be shown without inventing values.",
                ],
            }
        )
        return

    components.render_paragraph(
        {
            "label": "What this comparison measures",
            "body": [
                "The decision-sensitivity summary compares epsilon-constraint solutions produced under different scenario sample sizes (N_A vs N_B). "
                "It reports matched-solution counts and several distance/difference measures between the two solution sets.",
            ],
        }
    )

    sens_preview = sens_df.copy()
    for col, kind in [
        ("matched_solutions", "int"),
        ("mean_objective_distance", "num"),
        ("max_objective_distance", "num"),
        ("mean_abs_quantity_difference", "num"),
        ("mean_total_procurement_normalized_difference", "num"),
        ("max_total_procurement_normalized_difference", "num"),
        ("mean_zero_safe_quantity_relative_difference", "num"),
    ]:
        if col in sens_preview.columns:
            if kind == "int":
                sens_preview[col] = sens_preview[col].apply(lambda v: _fmt_int(v))
            else:
                sens_preview[col] = sens_preview[col].apply(lambda v: _fmt_num(v, 4))

    components.render_table(
        sens_preview.head(50)[
            [
                "N_A",
                "N_B",
                "matched_solutions",
                "mean_objective_distance",
                "max_objective_distance",
                "mean_abs_quantity_difference",
                "mean_total_procurement_normalized_difference",
                "max_total_procurement_normalized_difference",
                "mean_zero_safe_quantity_relative_difference",
            ]
        ]
    )

    components.render_paragraph(
        {
            "label": "Reading the sensitivity numbers",
            "body": [
                "matched_solutions is the number of solution pairs matched between the two sample sizes. The distance and difference columns quantify, "
                "in different ways, how far apart the two solution sets are in objective space and in procurement-quantity space.",
                "",
                "These are relative comparison measures between two scenario-based solution sets, not absolute quality scores and not guarantees about "
                "real-world procurement outcomes.",
            ],
        }
    )

    components.render_paragraph(
        {
            "label": "What this page does NOT claim",
            "body": [
                "Scenario sensitivity comparisons are comparisons between modeled solution sets, not observed outcomes. They are not assertions that one "
                "scenario size is the right one, and they are not a substitute for supplier-capacity, storage, or disruption evidence.",
            ],
        }
    )


def _render_provenance_and_limits(evidence: RO3Evidence) -> None:
    """Provenance inventory, assumptions and limitations."""
    components.render_section_header(
        title="Provenance, assumptions and limitations",
        subtitle="Every value on this page traces back to a registered, schema-validated artifact.",
        research_stage="10A.10",
    )

    components.render_paragraph(
        {
            "label": "Assumptions",
            "body": [
                "This page assumes the registration, loading, schema-validation and provenance tagging performed by the 10A.2-B pipeline. It does not "
                "re-validate schemas or re-derive provenance at render time.",
                "",
                "It further assumes that unavailable decision variables remain explicitly unavailable. It does not treat supplier context, material "
                "context, or Pareto evidence as proof of supplier-level or safety-stock decisions.",
            ],
        }
    )

    components.render_paragraph(
        {
            "label": "Limitations",
            "body": [
                "Supplier allocation y(i,s,t) is out of scope by design.",
                "Safety stock ss(i,t) is out of scope by design.",
                "Storage-capacity and supplier-capacity constraints are not modeled as active constraints in this experiment.",
                "Supplier-disruption probability is excluded from the model.",
                "Feasibility is not asserted where constraint evidence is absent.",
                "The selected candidate is one nondominated solution, not a recommended procurement plan.",
                "Shortage, service and ending inventory are realized outcomes under the experiment's realized demand path, not guarantees.",
                "Scenario-sensitivity comparisons are comparisons between modeled solution sets, not observed outcomes.",
            ],
        }
    )

    components.render_paragraph(
        {
            "label": "What would extend this workspace",
            "body": [
                "To add supplier-allocation evidence, the research would need a genuine y(i,s,t) decision artifact registered under the 10A.2-B registry.",
                "To add safety-stock evidence, the research would need a genuine ss(i,t) decision or policy artifact registered under the 10A.2-B registry.",
                "To add constraint-evidence evidence, the research would need a constraint-satisfaction artifact (e.g. feasibility flags, capacity-binding "
                "records, or shortage-cause attribution) registered under the 10A.2-B registry.",
                "None of these are created by this page; they require changes to the research, not to the dashboard.",
            ],
        }
    )


def _render_handoff(evidence: RO3Evidence) -> None:
    """Handoff back to the RO3 optimization evidence."""
    components.render_section_header(
        title="Handoff back to RO3 optimization evidence",
        subtitle="The procurement decisions here are one view of the same RO3 evidence the RO3 Pareto page shows.",
        research_stage="10A.10",
    )

    components.render_paragraph(
        {
            "label": "Where to go next",
            "body": [
                "RO3 Pareto page — the same optimization runs, with the full nondominated objective frontiers and per-solution procurement decisions.",
                "RO3 convergence, robustness, stress, ablation and baseline-comparison evidence — the optimization evidence behind the decisions here.",
            ],
        }
    )

    components.render_inline_label_values(
        [
            _labeled_paragraph(
                "This page vs RO3 Pareto page",
                [
                    "RO3 Pareto page: full Pareto frontier, all origins, per-solution quantities, objective fronts, convergence, robustness, stress, ablation, baseline.",
                    "Procurement decisions page: selected decisions with period + selected candidate, realized evaluation of those decisions, per-origin Pareto summary, decision sensitivity.",
                    "Both pages report the same underlying RO3 evidence; neither rewrites the research.",
                ],
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Page render
# ---------------------------------------------------------------------------


def render_page(
    snapshot: DashboardSnapshot,
    page_route: dict[str, Any] | None = None,
    *,
    include_header: bool = True,
) -> None:
    """Render the Procurement Decisions workspace.

    Parameters
    ----------
    snapshot: the canonical DashboardSnapshot for this run.
    page_route: optional per-request route context (unused here; accepted for
        signature compatibility with the app dispatch).
    include_header: when True (standalone use) the workspace injects the design
        system CSS and its own page header. The dashboard app shell already
        renders both, so it passes False to avoid duplicating them.
    """
    if include_header:
        inject_and_route(snapshot)

    evidence = snapshot.ro3
    provenance_rows = _build_provenance_rows(evidence)

    if not provenance_rows:
        components.render_error_state(
            "No RO3 decision evidence available",
            description="The RO3 evidence bundle did not include any decision-level provenance. This page is therefore empty.",
        )
        return

    _render_decision_overview(evidence, provenance_rows)
    _render_decision_evidence_status(evidence)
    _render_material_quantities(evidence)
    _render_timing_and_origin_comparison(evidence)
    _render_supplier_and_capacity(evidence)
    _render_inventory_and_safety_stock(evidence)
    _render_feasibility_and_shortage(evidence)
    _render_tradeoffs(evidence)
    _render_sensitivity(evidence)
    _render_provenance_and_limits(evidence)
    _render_handoff(evidence)


def inject_and_route(snapshot: DashboardSnapshot) -> None:
    """Inject the design system CSS and the page header for this workspace."""
    components.inject_css()

    page_info = page_by_id(PAGE_ID)
    header = build_page_header(
        title=_page_title(),
        subtitle=_page_subtitle(),
        research_stage="10A.10",
        evidence_state=page_info.implementation.value,
    )
    components.render_html(header)


def _build_provenance_rows(evidence: RO3Evidence) -> list[dict[str, Any]]:
    """Curate a provenance inventory for the decision-level artifacts only."""
    rows: list[dict[str, Any]] = []
    available = 0
    for entry in evidence.provenance:
        status = _status_text(_prov_get(entry, "status"))
        if status == "AVAILABLE":
            available += 1
        rows.append(
            {
                "artifact_id": str(_prov_get(entry, "artifact_id", "")),
                "status": status,
                "provenance_class": str(
                    getattr(_prov_get(entry, "provenance_class"), "value", _prov_get(entry, "provenance_class"))
                    or ""
                ),
                "research_stage": str(_prov_get(entry, "research_stage", "") or ""),
                "row_count": _prov_get(entry, "row_count"),
                "file_size_bytes": _prov_get(entry, "file_size_bytes"),
                "schema_status": str(_prov_get(entry, "schema_status", "UNCHECKED") or "UNCHECKED"),
            }
        )
    return rows


def page_is_planned_fn() -> bool:
    return page_is_planned(PAGE_ID)


def page_description_fn() -> str:
    from src.construction.dashboard_ui.navigation import page_description as _page_description
    return _page_description(PAGE_ID)


def page_description() -> str:
    """Zero-argument public export consumed by page tests."""
    return page_description_fn()


def page_future_phase() -> str:
    """Zero-argument public export consumed by page tests."""
    from src.construction.dashboard_ui.navigation import page_future_phase as _page_future_phase
    return _page_future_phase(PAGE_ID)


def page_future_phase_fn() -> str:
    return page_future_phase(PAGE_ID)


def page_by_id_local() -> dict[str, Any]:
    return page_by_id(PAGE_ID)
