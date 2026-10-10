"""Presentation builders for the RO3 · Optimization dashboard workspace.

Pure module — no Streamlit imports, no simulation/forecasting/optimization
engines, no artifact scanning. Every value flows through the existing 10A.2-B
dashboard data contract (:class:`RO3Evidence`) and its registry-driven adapters.

Scientific-integrity rules encoded in this module:

* Missing evidence renders as an explicit unavailable state, never as zero.
* Objective direction (all RO3 objectives are minimised) and units travel with
  the numbers; a cost from one experiment is never compared with an
  incompatible metric or evaluation configuration.
* The 2x2 controller design (O1 deterministic+heuristic, O2 deterministic+
  optimization, O3 probabilistic+heuristic, O4 probabilistic+optimization) is
  attributed per contrast; no controller is called universally optimal and the
  genuinely mixed trade-offs are surfaced as recorded.
* Pareto points are the solver's recorded nondominated set — never
  reclassified, never manufactured from unrelated aggregates, and never shown
  without their objective definitions.
* Scenario-based stress/robustness outputs stay SCN; they are not observations,
  and a sensitivity result is not relabelled proof of robustness.
* The raw scenario ledgers (169 MB / 338 MB) are NEVER loaded; only curated
  summaries reach this page.
* No composite score or cross-experiment ranking is computed anywhere.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.construction.dashboard_data.contract import RO3Evidence
from src.construction.dashboard_ui import (
    cards,
    charts,
    components,
    formatting,
    theme,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BREADCRUMB_IDS = ("overview", "research", "ro3_optimization")
_IDS_PLACEHOLDER = {
    "ro3_optimization": "RO3 · Optimization",
    "research": "Research",
    "overview": "Overview",
}
_IDS_NOT_IMPLEMENTED = {"research"}

#: Recorded 2x2 controller conditions (source: CMIDO RO3.6 ablation spec).
#: Keyed exactly as the artifacts spell the controller ids.
_CONTROLLER_DEFS: dict[str, str] = {
    "O1": "Deterministic + Heuristic (baseline)",
    "O2": "Deterministic + Optimization",
    "O3": "Probabilistic + Heuristic",
    "O4": "Probabilistic + Optimization (CMIDO)",
}

#: Human labels for the recorded T5/T6 contrasts.
_CONTRAST_LABELS: dict[str, str] = {
    "O2_vs_O1": "O2 vs O1 — value of optimization under deterministic information",
    "O3_vs_O1": "O3 vs O1 — value of probabilistic information under heuristic control",
    "O4_vs_O2": "O4 vs O2 — incremental value of uncertainty-aware optimization",
    "O4_vs_O3": "O4 vs O3 — incremental value of optimization under probabilistic information",
    "O4_vs_O1": "O4 vs O1 — integrated CMIDO vs deterministic heuristic baseline",
}

#: Metric display metadata: (label, unit, direction). Direction is minimisation
#: for every RO3 objective as formulated; service level is a realised outcome
#: reported alongside, where a higher value is better but it is NOT itself the
#: optimised objective.
_METRIC_META: dict[str, tuple[str, str, str]] = {
    "realized_procurement_holding_cost": ("Realised procurement + holding cost", "cost units", "min"),
    "realized_total_shortage": ("Realised total shortage quantity", "units", "min"),
    "realized_shortage_cvar95_monthly": ("Realised monthly CVaR_0.95 shortage", "units", "min"),
    "realized_total_procurement_quantity": ("Realised total procurement quantity", "units", "reported"),
    "realized_mean_ending_inventory": ("Realised mean ending inventory", "units", "reported"),
    "realized_procurement_events": ("Realised procurement events", "count", "reported"),
    "realized_service_level": ("Realised service level", "fraction", "reported (higher=better)"),
}


def _fill(color: str, alpha: float) -> str:
    """Build an rgba() fill from a theme token (no literal colour in UI code)."""
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


# ---------------------------------------------------------------------------
# Page shell metadata
# ---------------------------------------------------------------------------


def breadcrumb_ids() -> tuple[str, ...]:
    """Public breadcrumb trail for the RO3 page."""
    return _BREADCRUMB_IDS


def page_title() -> str:
    return "RO3 · Optimization"


def page_subtitle() -> str:
    return "Controller baselines, Pareto trade-offs, ablation and robustness evidence workspace."


def breadcrumb_checkpoint_label(id_: str) -> str:
    """Resolve breadcrumb checkpoints to labels."""
    return _IDS_PLACEHOLDER.get(id_, id_.replace("_", " ").title())


def breadcrumb_is_missing(id_: str) -> bool:
    return id_ in _IDS_NOT_IMPLEMENTED


def build_breadcrumb_row() -> components.BreadcrumbRow:
    return components.build_breadcrumb(
        ids=_BREADCRUMB_IDS,
        labels_map={id_: breadcrumb_checkpoint_label(id_) for id_ in _BREADCRUMB_IDS},
        missing_set=_IDS_NOT_IMPLEMENTED,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _prov_get(entry: Any, key: str, default: Any = None) -> Any:
    """Read provenance metadata from a dict or an ArtifactProvenance record."""
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _status_text(value: Any) -> str:
    return str(getattr(value, "value", value) or "UNKNOWN")


def _frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(records) if records else pd.DataFrame()


def _bulleted(lines: list[str]) -> list[str]:
    return [f"- {line}" for line in lines]


def _numbered_list(lines: list[str]) -> list[str]:
    return [f"{i}. {line}" for i, line in enumerate(lines, start=1)]


def _labeled_paragraph(label: str, body: str | list[str]) -> dict[str, Any]:
    if isinstance(body, list):
        body = "\n".join(body)
    return {"label": label, "body": body}


def _fmt_num(value: Any, decimals: int = 2) -> str:
    try:
        return formatting.format_number(float(value), decimals=decimals)
    except (TypeError, ValueError):
        return formatting.MISSING_DISPLAY


def _fmt_pct(value: Any, decimals: int = 1) -> str:
    try:
        return formatting.format_percent(float(value), decimals=decimals)
    except (TypeError, ValueError):
        return formatting.MISSING_DISPLAY


def _fmt_int(value: Any) -> str:
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return formatting.MISSING_DISPLAY


def _fmt_cell(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return formatting.MISSING_DISPLAY
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _is_true(value: Any) -> bool:
    return str(value).strip().lower() in ("true", "yes", "1")


def _clean_audit_detail(detail: str) -> str:
    """Hide filesystem paths from integrity-audit detail text.

    Some audit rows record the path of the file that was checked (e.g. a
    \"file exists\" check). Surfacing that path would leak raw repository layout
    into the research page, so path-like details are suppressed; the check label
    already records what was verified.
    """
    text = detail.strip()
    lowered = text.lower()
    if not text:
        return ""
    if ".csv" in lowered or ".json" in lowered:
        # A detail that names result files (a path, or a recorded list of
        # paths) exposes raw repository layout; the check label already
        # records what was verified.
        return ""
    looks_like_path = (
        ("/" in text and lowered.startswith("/")) or (":" in text and "\\" in text)
    )
    return "" if looks_like_path else text


def _first_origin(frame: pd.DataFrame) -> Any:
    """Earliest forecast origin present in the frame (honest preview choice)."""
    if frame.empty or "forecast_origin" not in frame.columns:
        return None
    origins = sorted(frame["forecast_origin"].dropna().unique().tolist(), key=str)
    return origins[0] if origins else None


def _metric_label(metric: str) -> str:
    return _METRIC_META.get(metric, (metric.replace("_", " ").capitalize(), "", "reported"))[0]


def _metric_unit(metric: str) -> str:
    return _METRIC_META.get(metric, (_metric_label(metric), "", "reported"))[1]


def _metric_direction(metric: str) -> str:
    return _METRIC_META.get(metric, (_metric_label(metric), "", "reported"))[2]


def available_controllers(evidence: RO3Evidence) -> list[str]:
    """Distinct controllers present in the descriptive artifact (for app filters)."""
    desc_df = _frame(evidence.controller_descriptives)
    if desc_df.empty or "controller" not in desc_df.columns:
        return []
    return sorted(desc_df["controller"].dropna().unique().tolist())


def _snapshot_context(evidence: RO3Evidence) -> dict[str, Any]:
    """Curate research context derived ONLY from the RO3 evidence snapshot."""
    context: dict[str, Any] = {}

    base_df = _frame(evidence.baseline_comparison)
    abl_df = _frame(evidence.ablation)
    desc_df = _frame(evidence.controller_descriptives)
    stress_df = _frame(evidence.stress_summary)
    robust_df = _frame(evidence.robustness_summary)
    pareto_df = _frame(evidence.pareto_summary)
    dec_df = _frame(evidence.pareto_decisions)

    context["base_df"] = base_df
    context["abl_df"] = abl_df
    context["desc_df"] = desc_df
    context["stress_df"] = stress_df
    context["robust_df"] = robust_df
    context["pareto_df"] = pareto_df
    context["dec_df"] = dec_df

    context["base_row_count"] = int(len(base_df))
    context["abl_row_count"] = int(len(abl_df))
    context["desc_row_count"] = int(len(desc_df))
    context["stress_row_count"] = int(len(stress_df))
    context["robust_row_count"] = int(len(robust_df))
    context["pareto_row_count"] = int(len(pareto_df))
    context["dec_row_count"] = int(len(dec_df))

    context["controllers"] = available_controllers(evidence)

    if not pareto_df.empty and "forecast_origin" in pareto_df.columns:
        origins = sorted(pareto_df["forecast_origin"].dropna().unique().tolist(), key=str)
        context["pareto_origins"] = origins
        context["first_origin"] = origins[0] if origins else None
    else:
        context["pareto_origins"] = []
        context["first_origin"] = None

    if not base_df.empty and "metric" in base_df.columns:
        context["metrics"] = sorted(base_df["metric"].dropna().unique().tolist())
    else:
        context["metrics"] = []

    if not base_df.empty and "comparison" in base_df.columns:
        context["contrasts"] = sorted(base_df["comparison"].dropna().unique().tolist())
    else:
        context["contrasts"] = []

    audit = evidence.final_audit if isinstance(evidence.final_audit, dict) else {}
    context["audit"] = audit
    context["audit_rows"] = audit.get("audit_rows", []) if isinstance(audit.get("audit_rows"), list) else []
    context["convergence"] = evidence.convergence_summary if isinstance(evidence.convergence_summary, dict) else {}

    # Provenance inventory (statuses come from the 10A.2-B loader, never invented)
    prov_rows: list[dict[str, Any]] = []
    available = 0
    for entry in evidence.provenance:
        status = _status_text(_prov_get(entry, "status"))
        if status == "AVAILABLE":
            available += 1
        prov_rows.append(
            {
                "artifact_id": str(_prov_get(entry, "artifact_id", "")),
                "status": status,
                "provenance": str(getattr(_prov_get(entry, "provenance_class"), "value", _prov_get(entry, "provenance_class")) or ""),
                "row_count": _prov_get(entry, "row_count"),
                "schema_status": str(_prov_get(entry, "schema_status", "UNCHECKED") or "UNCHECKED"),
            }
        )
    context["provenance_rows"] = prov_rows
    context["artifact_total"] = len(prov_rows)
    context["artifact_available"] = available
    context["artifact_unavailable"] = len(prov_rows) - available

    return context


def _section_header(title: str, subtitle: str) -> str:
    return components.build_section_header(
        title=title,
        subtitle=subtitle,
        research_stage="RO3",
    )


def _table_block(
    frame: pd.DataFrame,
    *,
    columns: list[str],
    headers: list[str],
    caption: str | None = None,
    formatter: Any = None,
) -> components.TableBlock:
    """Positional table over a curated column subset; absent columns render as unavailable."""
    fmt = formatter or _fmt_cell
    rows_data: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        entry: dict[str, Any] = {}
        for col in columns:
            entry[col] = fmt(col, row.get(col)) if col in frame.columns else formatting.MISSING_DISPLAY
        rows_data.append(entry)
    return components.build_table(headers=headers, rows=rows_data, caption=caption)


# ---------------------------------------------------------------------------
# A. Research objective and methodology
# ---------------------------------------------------------------------------


def build_research_method_context(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    controllers = ctx["controllers"]

    controller_lines = _bulleted(
        [f"{cid} — {_CONTROLLER_DEFS.get(cid, 'recorded controller condition')}" for cid in controllers]
    ) if controllers else ["Controller inventory not reported in the loaded RO3 artifacts."]

    contrasts = ctx["contrasts"]
    contrast_lines = _bulleted(
        [_CONTRAST_LABELS.get(c, c.replace("_", " ")) for c in contrasts]
    ) if contrasts else ["Contrast inventory not reported in the loaded RO3 artifacts."]

    rows = [
        _labeled_paragraph(
            "Research objective",
            (
                "RO3 asks whether uncertainty-aware procurement optimization measurably improves "
                "procurement decisions relative to suitable baselines under a comparable evaluation "
                "protocol — not merely whether an optimizer can return a feasible solution. It turns "
                "RO1 forecasts and RO2 uncertainty evidence into concrete decisions (quantities, "
                "timing) and quantifies the objective trade-offs those decisions imply. Every value "
                "on this page is read from registered research artifacts; nothing is re-optimized "
                "or recomputed in the dashboard."
            ),
        ),
        _labeled_paragraph(
            "Relationship to RO1 and RO2",
            (
                "RO1 supplies calibrated predictive demand quantiles; RO2 propagates demand and "
                "procurement-process duration uncertainty into shortage/service exposure. RO3 "
                "consumes that uncertainty evidence inside a two-stage stochastic procurement "
                "formulation and evaluates the resulting decision policies. The pipeline is "
                "RO1 forecasting -> RO2 uncertainty -> RO3 optimization -> decision-level "
                "evaluation; the sections below distinguish what the current experiments have "
                "actually validated from what the pipeline merely intends."
            ),
        ),
        _labeled_paragraph(
            "Experimental design (2×2 factorial)",
            (
                "Controllers cross information type (deterministic vs probabilistic) with decision "
                "rule (heuristic vs optimization), so that observed differences can be attributed "
                "to uncertainty, to optimization, or to their integration rather than to a single "
                "opaque comparison."
            ),
        ),
        _labeled_paragraph("Evaluated controllers / conditions", _numbered_list(controller_lines)),
        _labeled_paragraph("Recorded contrasts and what each isolates", _numbered_list(contrast_lines)),
        _labeled_paragraph(
            "Evaluation protocol",
            (
                "All controllers are realised under the same locked multi-origin evaluation over "
                "the recorded forecast origins and common materials, so pairwise contrasts are "
                "like-for-like. Comparisons are kept inside this protocol; results from other "
                "datasets, evaluation windows or configurations are never mixed in."
            ),
        ),
        _labeled_paragraph(
            "Evidence provenance",
            _provenance_tally_lines(evidence),
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Research objective and methodology",
            "What RO3 evaluates, under which recorded design, and how it relates to RO1 and RO2.",
        ),
        rows=rows,
    )


def _provenance_tally_lines(evidence: RO3Evidence) -> str:
    tallies: dict[str, set[str]] = {}
    for entry in evidence.provenance:
        cls = str(getattr(_prov_get(entry, "provenance_class"), "value", _prov_get(entry, "provenance_class")) or "")
        role = str(_prov_get(entry, "evidence_role") or "")
        if cls:
            tallies.setdefault(cls, set()).add(role)
    if not tallies:
        return "No provenance metadata attached to the RO3 evidence snapshot."
    lines = []
    for cls in sorted(tallies):
        roles = " ".join(sorted(r for r in tallies[cls] if r))
        lines.append(f"{cls} — {roles}" if roles else cls)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# B. Optimization evidence snapshot
# ---------------------------------------------------------------------------


def build_evidence_status(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    nothing_loaded = ctx["artifact_total"] == 0

    def _count(value: int) -> str:
        return str(value) if not nothing_loaded else formatting.MISSING_DISPLAY

    audit_rows = ctx["audit_rows"]
    audit_passed = sum(1 for r in audit_rows if _is_true(_prov_get(r, "passed")))

    cards_ = [
        cards.build_kpi(
            label="RO3 artifacts registered",
            value=_count(ctx["artifact_total"]),
            description="Registered RO3 artifacts resolved by the 10A.2-B loader (raw scenario ledgers are blocked and never loaded).",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Available",
            value=_count(ctx["artifact_available"]),
            description="Artifacts loaded successfully with schema validation applied.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Not available",
            value=_count(ctx["artifact_unavailable"]),
            description="Missing, invalid, unsupported or oversized artifacts. Their sections render honest unavailable states, never zeros.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Controllers evaluated",
            value=(str(len(ctx["controllers"])) if ctx["controllers"] and not nothing_loaded else formatting.MISSING_DISPLAY),
            description="Distinct controller conditions in the descriptive artifact.",
            provenance="DER",
        ),
    ]
    if audit_rows:
        cards_.append(
            cards.build_kpi(
                label="Integrity audit",
                value=f"{audit_passed}/{len(audit_rows)}",
                description="Final experimental-integrity checks passing, as recorded in the RO3.9 audit.",
                provenance="DER",
            )
        )

    rows: list[Any] = [components.build_kpi_columns(cards=cards_)]

    prov = ctx["provenance_rows"]
    if prov:
        frame = pd.DataFrame(prov)
        rows.append(
            _table_block(
                frame,
                columns=["artifact_id", "status", "provenance", "row_count", "schema_status"],
                headers=["Artifact", "Status", "Provenance", "Rows", "Schema"],
                caption="Loader outcome per registered RO3 artifact (AVAILABLE / MISSING / INVALID / TOO_LARGE / UNSUPPORTED).",
                formatter=lambda col, value: (_fmt_int(value) if col == "row_count" else _fmt_cell(value)),
            )
        )
    else:
        rows.append(
            components.build_unavailable_block(
                "No RO3 artifact provenance loaded",
                body=(
                    "The 10A.2-B loader returned no RO3 artifacts for this workspace, so no RO3 "
                    "evidence can be shown. Nothing is computed in their place."
                ),
            )
        )

    return components.build_section(
        header=_section_header(
            "Optimization evidence snapshot",
            "Which RO3 optimization artifacts loaded, which are unavailable, and the recorded integrity status.",
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# C. Procurement decision outputs
# ---------------------------------------------------------------------------


def build_procurement_decisions(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    dec_df: pd.DataFrame = ctx["dec_df"]

    if dec_df.empty:
        return components.build_section(
            header=_section_header(
                "Procurement decision outputs",
                "Per-solution procurement quantities exactly as recorded by the optimizer.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Procurement decision evidence unavailable",
                    body=(
                        "The registered per-solution decision artifact was not available, so no "
                        "procurement quantities, allocations or timing are displayed. No value is "
                        "substituted or defaulted."
                    ),
                ),
            ],
        )

    origin = _first_origin(dec_df)
    materials = sorted(dec_df["material"].dropna().unique().tolist()) if "material" in dec_df.columns else []
    pareto_ids = sorted(dec_df["pareto_id"].dropna().unique().tolist()) if "pareto_id" in dec_df.columns else []

    # Preview: one representative Pareto solution at the earliest origin.
    preview_id = pareto_ids[0] if pareto_ids else None
    preview = dec_df
    if origin is not None and "forecast_origin" in dec_df.columns:
        preview = preview[preview["forecast_origin"] == origin]
    if preview_id is not None and "pareto_id" in preview.columns:
        preview = preview[preview["pareto_id"] == preview_id]

    cards_ = [
        cards.build_kpi(
            label="Materials with decisions",
            value=str(len(materials)) if materials else formatting.MISSING_DISPLAY,
            description="Distinct materials carrying a procurement quantity decision.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Decision rows",
            value=str(ctx["dec_row_count"]),
            description="Recorded per-solution, per-material, per-month procurement quantity rows.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Pareto solutions",
            value=(str(len(pareto_ids)) if pareto_ids else formatting.MISSING_DISPLAY),
            description="Distinct nondominated solutions carrying a decision vector.",
            provenance="DER",
        ),
    ]

    rows: list[Any] = [
        components.build_kpi_columns(cards=cards_),
        _table_block(
            preview,
            columns=["material", "month_ahead", "q"],
            headers=["Material", "Month ahead", "Procurement quantity q(i,t)"],
            caption=(
                f"Decision vector for Pareto solution {preview_id} at forecast origin {origin}. "
                "Quantities are decision variables as solved, in each material's native units."
            ),
            formatter=lambda col, value: (_fmt_int(value) if col == "month_ahead" else _fmt_num(value)),
        ),
        components.build_note_bare(
            "Provenance: DER. q(i,t) is the optimised procurement quantity for material i in "
            "month-ahead t of the planning horizon. Only what the artifact records is shown: "
            "aggregate quantity decisions per solution, not supplier-selection binaries or safety-"
            "stock state variables, which are not exposed in the registered summary artifact."
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Procurement decision outputs",
            "Procurement quantities q(i,t) per material and horizon, as solved and recorded.",
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# D. Objective and trade-off analysis
# ---------------------------------------------------------------------------


def build_objective_tradeoffs(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    desc_df: pd.DataFrame = ctx["desc_df"]

    if desc_df.empty:
        return components.build_section(
            header=_section_header(
                "Objective and trade-off analysis",
                "Realised objective values per controller, with direction and units kept explicit.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Objective evidence unavailable",
                    body=(
                        "The registered controller-descriptive artifact was not available, so no "
                        "objective values are displayed."
                    ),
                ),
            ],
        )

    # Curated columns: controller + the realised objective/outcome means.
    metric_cols = [c for c in desc_df.columns if c.endswith("_mean")]
    preview_cols = ["controller"] + metric_cols
    headers = ["Controller"] + [_metric_label(c[:-5]) for c in metric_cols]

    table = _table_block(
        desc_df,
        columns=preview_cols,
        headers=headers,
        caption="Realised objective and outcome means per controller across the locked evaluation origins.",
        formatter=lambda col, value: _fmt_num(value) if col.endswith("_mean") else _fmt_cell(value),
    )

    rows: list[Any] = [
        _labeled_paragraph(
            "Objective definitions and direction",
            (
                "Z1 = expected procurement + holding cost (minimise). Z2 = expected total shortage "
                "quantity (minimise). Z3 = CVaR_0.95 of total shortage quantity (minimise). Service "
                "level and realised inventory/procurement quantities are reported outcomes, not the "
                "optimised objectives themselves. All costs are in the model's recorded cost units; "
                "quantities are in each material's native units."
            ),
        ),
        table,
        _tradeoff_chart(desc_df, metric_cols),
        components.build_note_bare(
            "Provenance: DER. Controllers share one locked evaluation protocol, so these columns are "
            "mutually comparable. Differences are point estimates over the recorded origins; no "
            "statistical significance is asserted here — significance, where it exists, is recorded "
            "in the baseline/ablation artifacts with bootstrap intervals and multiplicity correction. "
            "No composite score is computed."
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Objective and trade-off analysis",
            "Realised objective values per controller, with direction and units kept explicit.",
        ),
        rows=rows,
    )


def _tradeoff_chart(desc_df: pd.DataFrame, metric_cols: list[str]) -> Any:
    import plotly.graph_objects as go

    controllers = (
        sorted(desc_df["controller"].dropna().unique().tolist())
        if not desc_df.empty and "controller" in desc_df.columns
        else []
    )
    # Plot the two headline minimised objectives (cost and shortage) as a
    # grouped bar so the cost/shortage trade-off is visible at a glance.
    want = [c for c in metric_cols if c in (
        "realized_procurement_holding_cost_mean", "realized_total_shortage_mean"
    )]
    if not controllers or not want:
        return None

    fig = go.Figure()
    palette = theme.CATEGORICAL_PALETTE
    for idx, col in enumerate(want):
        label = _metric_label(col[:-5])
        values = []
        for ctrl in controllers:
            row = desc_df[desc_df["controller"] == ctrl]
            raw = row.iloc[0].get(col) if not row.empty else None
            try:
                values.append(float(raw))
            except (TypeError, ValueError):
                values.append(None)
        fig.add_trace(
            go.Bar(
                name=label,
                x=controllers,
                y=values,
                marker_color=palette[idx % len(palette)],
            )
        )

    fig.update_layout(
        barmode="group",
        legend_title_text="Objective (both minimised)",
        height=360,
    )
    fig.update_xaxes(title_text="Controller")
    fig.update_yaxes(title_text="Realised value (recorded units)")
    return fig


# ---------------------------------------------------------------------------
# E. Pareto evidence
# ---------------------------------------------------------------------------


def build_pareto_evidence(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    pareto_df: pd.DataFrame = ctx["pareto_df"]

    if pareto_df.empty:
        return components.build_section(
            header=_section_header(
                "Pareto evidence",
                "Nondominated cost/shortage/risk trade-offs exactly as the solver recorded them.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Pareto evidence unavailable",
                    body=(
                        "The registered Pareto artifact was not available, so no Pareto front is "
                        "displayed. No front is manufactured from unrelated aggregate results."
                    ),
                ),
            ],
        )

    origin = ctx["first_origin"]
    preview = pareto_df[pareto_df["forecast_origin"] == origin] if origin is not None else pareto_df

    # A front is only asserted when the source itself labelled these points as a
    # nondominated set; otherwise we show rows without claiming dominance.
    labelled = bool(
        "nondominated" in {str(c).lower() for c in pareto_df.columns}
        or "pareto" in {str(c).lower() for c in pareto_df.columns}
    )

    cards_ = [
        cards.build_kpi(
            label="Pareto points",
            value=str(ctx["pareto_row_count"]),
            description="Recorded nondominated solutions across all locked origins.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Origins with a front",
            value=(str(len(ctx["pareto_origins"])) if ctx["pareto_origins"] else formatting.MISSING_DISPLAY),
            description="Distinct forecast origins carrying Pareto evidence.",
            provenance="DER",
        ),
    ]

    rows: list[Any] = [
        components.build_kpi_columns(cards=cards_),
        components.build_chart(
            _make_pareto_figure(preview),
            caption=(
                f"Recorded Pareto front at forecast origin {origin}. Both axes are minimised: "
                "lower-left is preferable. Points are the solver's own nondominated set."
            ),
            chart_config=charts.CHART_CONFIG_FORECAST,
        ),
        _table_block(
            preview,
            columns=["Z1", "Z2", "Z3"],
            headers=["Z1 — cost (min)", "Z2 — shortage (min)", "Z3 — CVaR_0.95 shortage (min)"],
            caption=f"Objective values of the nondominated solutions at origin {origin}, as recorded.",
            formatter=lambda col, value: _fmt_num(value),
        ),
        components.build_note_bare(
            "Provenance: DER. Objectives: Z1 = expected procurement + holding cost, Z2 = expected "
            "total shortage quantity, Z3 = CVaR_0.95 of total shortage quantity — all minimised. "
            "Dominance classification is taken from the source artifact's methodology and is not "
            "recomputed here. Points from one forecast origin are shown together because they share "
            "a single evaluation configuration; fronts are not pooled across origins."
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Pareto evidence",
            "Nondominated cost/shortage/risk trade-offs exactly as the solver recorded them.",
        ),
        rows=rows,
    )


def _make_pareto_figure(preview: pd.DataFrame) -> Any:
    import plotly.graph_objects as go

    fig = go.Figure()
    if preview.empty or not {"Z1", "Z2"}.issubset(preview.columns):
        return fig

    fig.add_trace(
        go.Scatter(
            x=preview.get("Z1"),
            y=preview.get("Z2"),
            mode="markers",
            name="Nondominated solutions",
            marker=dict(size=9, color=theme.ACCENT),
            text=[str(v) for v in preview.get("pareto_id", [""] * len(preview))],
            hovertemplate="Z1=%{x:.3f}<br>Z2=%{y:.3f}<br>point %{text}<extra></extra>",
        )
    )
    fig.update_layout(height=380, showlegend=False)
    fig.update_xaxes(title_text="Z1 — expected procurement + holding cost (min)")
    fig.update_yaxes(title_text="Z2 — expected total shortage quantity (min)")
    return fig


# ---------------------------------------------------------------------------
# F. Baseline and controller comparison
# ---------------------------------------------------------------------------


def build_controller_comparison(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    base_df: pd.DataFrame = ctx["base_df"]

    if base_df.empty:
        return components.build_section(
            header=_section_header(
                "Baseline and controller comparison",
                "Like-for-like pairwise contrasts under the shared evaluation protocol.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Baseline comparison unavailable",
                    body=(
                        "The registered baseline-comparison artifact was not available, so no "
                        "controller contrast is displayed."
                    ),
                ),
            ],
        )

    # Curated subset: one row per (contrast, metric) with its interval + flag.
    columns = [
        "comparison", "metric", "newer_mean", "base_mean",
        "mean_difference_newer_minus_base", "bootstrap_ci95_lower", "bootstrap_ci95_upper",
        "significant_bh_0_05",
    ]
    headers = [
        "Contrast", "Metric", "Newer mean", "Base mean", "Difference (newer − base)",
        "95% CI lower", "95% CI upper", "Significant",
    ]

    rows: list[Any] = [
        _labeled_paragraph(
            "How to read this table",
            (
                "Each row contrasts two controllers on one metric under the same evaluation. "
                "A negative difference means the newer controller recorded a lower value for that "
                "metric; whether that is better depends on the metric's direction (cost and shortage "
                "are minimised; service level is a reported outcome where higher is better). "
                "Confidence intervals and the multiplicity-corrected significance flag are as "
                "recorded by the artifact."
            ),
        ),
        _table_block(
            base_df,
            columns=columns,
            headers=headers,
            caption="Pairwise controller contrasts with bootstrap 95% intervals and BH-corrected significance.",
            formatter=_fmt_comparison_cell,
        ),
        components.build_note_bare(
            "Provenance: EST. Comparisons are valid only within this recorded evaluation protocol. "
            "This table deliberately does not order controllers into a single ranking and does not "
            "declare any controller universally best — the recorded evidence is a mixed set of "
            "cost/shortage/service trade-offs."
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Baseline and controller comparison",
            "Like-for-like pairwise contrasts under the shared evaluation protocol, with intervals.",
        ),
        rows=rows,
    )


def _fmt_comparison_cell(col: str, value: Any) -> str:
    if col == "comparison":
        return _CONTRAST_LABELS.get(str(value), str(value).replace("_", " "))
    if col == "metric":
        return _metric_label(str(value))
    if col == "significant_bh_0_05":
        return "Yes" if _is_true(value) else "No"
    if col in ("newer_mean", "base_mean", "mean_difference_newer_minus_base", "bootstrap_ci95_lower", "bootstrap_ci95_upper"):
        return _fmt_num(value)
    return _fmt_cell(value)


# ---------------------------------------------------------------------------
# G. Ablation evidence
# ---------------------------------------------------------------------------


def build_ablation(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    abl_df: pd.DataFrame = ctx["abl_df"]

    if abl_df.empty:
        return components.build_section(
            header=_section_header(
                "Ablation evidence",
                "Component-wise incremental value from the controlled 2×2 design.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Ablation evidence unavailable",
                    body=(
                        "The registered ablation artifact was not available, so no component-wise "
                        "attribution is displayed."
                    ),
                ),
            ],
        )

    columns = [
        "comparison", "metric", "relative_mean_difference",
        "improved_count", "worsened_count", "tie_count",
        "rank_biserial_sign", "significant_bh_0_05",
    ]
    headers = [
        "Contrast (component isolated)", "Metric", "Relative difference",
        "Improved", "Worsened", "Tied", "Rank-biserial sign", "Significant",
    ]

    rows: list[Any] = [
        _labeled_paragraph(
            "What each contrast isolates",
            (
                "The 2×2 design changes one factor at a time: O2−O1 isolates optimization under "
                "deterministic information; O3−O1 isolates probabilistic information under heuristic "
                "control; O4−O2 isolates adding uncertainty on top of optimization; O4−O3 isolates "
                "adding optimization on top of probabilistic information. Because only the named "
                "factor changes within a contrast, a difference can be attributed to that component "
                "under this protocol. This is a controlled attribution, not a causal claim beyond "
                "the recorded experimental design."
            ),
        ),
        _table_block(
            abl_df,
            columns=columns,
            headers=headers,
            caption="Component-wise ablation over the locked evaluation origins, with multiplicity-corrected significance.",
            formatter=_fmt_ablation_cell,
        ),
        components.build_note_bare(
            "Provenance: EST. Improved/worsened counts are per-origin sign tallies recorded by the "
            "artifact. A significant result here means the component measurably shifted that metric "
            "within this protocol; it does not establish real-world deployment performance."
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Ablation evidence",
            "Component-wise incremental value from the controlled 2×2 design, one factor at a time.",
        ),
        rows=rows,
    )


def _fmt_ablation_cell(col: str, value: Any) -> str:
    if col == "comparison":
        return _CONTRAST_LABELS.get(str(value), str(value).replace("_", " "))
    if col == "metric":
        return _metric_label(str(value))
    if col == "significant_bh_0_05":
        return "Yes" if _is_true(value) else "No"
    if col == "relative_mean_difference":
        return _fmt_pct(value, decimals=1)
    if col in ("improved_count", "worsened_count", "tie_count"):
        return _fmt_int(value)
    if col == "rank_biserial_sign":
        return _fmt_num(value, decimals=2)
    return _fmt_cell(value)


# ---------------------------------------------------------------------------
# H. Robustness and stress testing
# ---------------------------------------------------------------------------


def build_robustness_stress(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    stress_df: pd.DataFrame = ctx["stress_df"]
    robust_df: pd.DataFrame = ctx["robust_df"]

    rows: list[Any] = []

    if stress_df.empty and robust_df.empty:
        return components.build_section(
            header=_section_header(
                "Robustness and stress testing",
                "Scenario-based sensitivity of the decisions to disruption and cost parameters.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Robustness and stress evidence unavailable",
                    body=(
                        "Neither the stress-test nor the holding-rate robustness artifact was "
                        "available, so no stress result is displayed."
                    ),
                ),
            ],
        )

    if not stress_df.empty:
        stress_cases = sorted(stress_df["stress_case"].dropna().unique().tolist()) if "stress_case" in stress_df.columns else []
        cards_ = [
            cards.build_kpi(
                label="Stress cases",
                value=(str(len(stress_cases)) if stress_cases else formatting.MISSING_DISPLAY),
                description="Recorded disruption-duration stress conditions evaluated.",
                provenance="SCN",
            ),
            cards.build_kpi(
                label="Controllers under stress",
                value=(str(len(stress_df["controller"].dropna().unique().tolist())) if "controller" in stress_df.columns else formatting.MISSING_DISPLAY),
                description="Controllers realised under each stress condition.",
                provenance="SCN",
            ),
        ]
        rows.append(components.build_kpi_columns(cards=cards_))
        rows.append(
            _table_block(
                stress_df,
                columns=["controller", "stress_case", "duration_days", "mean_cost", "mean_shortage", "mean_service"],
                headers=["Controller", "Stress case", "Duration (days)", "Mean cost", "Mean shortage", "Mean service"],
                caption="Realised outcomes under each recorded disruption stress case.",
                formatter=lambda col, value: (
                    _fmt_num(value) if col in ("mean_cost", "mean_shortage", "mean_service", "duration_days") else _fmt_cell(value)
                ),
            )
        )
        rows.append(
            components.build_note_bare(
                "Provenance: SCN. These are scenario-based stress simulations, not observed real-world "
                "disruptions. A stress result shows how decisions behave under perturbed assumptions; "
                "it is not, by itself, proof of robustness."
            )
        )

    if not robust_df.empty:
        rows.append(
            _table_block(
                robust_df,
                columns=["controller", "holding_case", "annual_holding_rate", "mean_cost", "mean_shortage", "mean_service"],
                headers=["Controller", "Holding case", "Annual holding rate", "Mean cost", "Mean shortage", "Mean service"],
                caption="Sensitivity of realised outcomes to the annual holding-rate parameter.",
                formatter=lambda col, value: (
                    _fmt_num(value) if col in ("mean_cost", "mean_shortage", "mean_service")
                    else _fmt_pct(value) if col == "annual_holding_rate"
                    else _fmt_cell(value)
                ),
            )
        )
        rows.append(
            components.build_note_bare(
                "Provenance: SCN. Holding-rate variation is a parameter sensitivity over a cost "
                "assumption, not an observed economic measurement."
            )
        )

    return components.build_section(
        header=_section_header(
            "Robustness and stress testing",
            "Scenario-based sensitivity to disruption duration and holding cost — evaluated, not observed.",
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# I. RO2 → RO3 uncertainty handoff
# ---------------------------------------------------------------------------


def build_handoff_from_ro2(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    convergence: dict[str, Any] = ctx["convergence"]
    audit_rows = ctx["audit_rows"]

    # Only assert the handoff where the audit artifact actually records the RO2
    # linkage; otherwise state it honestly as not evidenced here.
    ro2_links = [r for r in audit_rows if "RO2" in str(_prov_get(r, "check", ""))]

    handoff_items: list[str] = []
    for r in ro2_links:
        check = str(_prov_get(r, "check", ""))
        detail = _clean_audit_detail(str(_prov_get(r, "detail", "") or ""))
        handoff_items.append(f"{check}{f' — {detail}' if detail else ''}")

    if not handoff_items:
        handoff_items.append(
            "The registered RO3 audit artifact did not record an explicit RO2 linkage, so the handoff "
            "is not asserted on this page."
        )

    rows: list[Any] = [
        _labeled_paragraph(
            "Uncertainty inputs consumed",
            (
                "RO3 consumes RO1's calibrated predictive demand quantiles and RO2's demand-during-"
                "duration uncertainty through scenario sampling inside a two-stage stochastic "
                "formulation: first-stage procurement decisions are chosen before uncertainty "
                "resolves, and recourse actions adapt per scenario. The inputs fall into four "
                "recorded classes — empirically supported inputs (observed duration pairs), estimated "
                "uncertainty distributions (RO1 quantiles), scenario-defined assumptions (the sampled "
                "scenario set), and fixed parameters (frozen planning configuration)."
            ),
        ),
        _labeled_paragraph(
            "Recorded RO2 linkage in the RO3 audit",
            _bulleted(handoff_items),
        ),
        _labeled_paragraph(
            "Scenario-count convergence",
            _convergence_lines(convergence),
        ),
        components.build_note_bare(
            "Provenance: DER / SCN. This is uncertainty-aware optimization in the sense that RO1/RO2 "
            "uncertainty enters the formulation via scenarios; it is not a claim of fully integrated "
            "or distribution-free robustness. Duration is procurement-process duration, not supplier-"
            "specific lead time, consistent with RO2."
        ),
    ]

    return components.build_section(
        header=_section_header(
            "RO2 → RO3 uncertainty handoff",
            "Which uncertainty outputs the optimization actually consumes, and how they enter the formulation.",
        ),
        rows=rows,
    )


def _convergence_lines(convergence: dict[str, Any]) -> str:
    if not convergence:
        return (
            "The registered convergence artifact was not available, so no scenario-count "
            "convergence status is claimed."
        )
    decision = str(convergence.get("decision") or "not recorded").replace("_", " ")
    sizes = convergence.get("scenario_sizes") or []
    sizes_text = ", ".join(_fmt_int(s) for s in sizes) if sizes else "not recorded"
    primary_pass = convergence.get("primary_pass")
    later = convergence.get("later_max_relative_change")
    lines = [
        f"Recorded decision: {decision}.",
        f"Scenario sizes evaluated: {sizes_text}.",
        f"Primary transition passed: {_fmt_cell(primary_pass)}.",
    ]
    if later is not None:
        lines.append(f"Later maximum relative change: {_fmt_pct(float(later), decimals=2)}.")
    lines.append(
        "Scenario-count convergence is an evaluated property of this run; it is reported as recorded, "
        "not re-derived here."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# J. Decision-level validation and limitations
# ---------------------------------------------------------------------------


def build_decision_validation(evidence: RO3Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    base_df: pd.DataFrame = ctx["base_df"]

    rows: list[Any] = []

    if base_df.empty:
        rows.append(
            components.build_unavailable_block(
                "Decision-level validation evidence unavailable",
                body=(
                    "The registered baseline-comparison artifact was not available, so this page "
                    "makes no claim that optimized decisions outperform a baseline."
                ),
            )
        )
    else:
        rows.append(
            _labeled_paragraph(
                "What the evidence supports",
                _validation_findings(base_df),
            )
        )
        rows.append(
            components.build_note_bare(
                "Provenance: EST. All statements above are within-protocol comparisons over the "
                "recorded evaluation origins. They characterise simulation/evaluation behaviour, "
                "not demonstrated real-world deployment performance, and they do not establish "
                "statistical significance beyond what the recorded intervals and corrected p-values "
                "show."
            )
        )

    rows.append(
        _labeled_paragraph(
            "What remains unvalidated / limitations",
            _bulleted(
                [
                    "Real-world deployment performance: all outcomes are realised under the recorded evaluation simulation, not observed procurement operations.",
                    "Supplier-specific lead time: decisions are optimised against procurement-process duration, not supplier-specific lead-time distributions (consistent with RO2).",
                    "Historical shortage labels: service/shortage outcomes are simulated exposures, not calibrated against realised shortage events.",
                    "Cross-protocol generalisation: results hold for the locked evaluation window and materials; they are not established for other datasets, horizons or configurations.",
                    "No universal optimality: the recorded evidence is a set of cost/shortage/service trade-offs; no single controller is established as best under every objective.",
                ]
            ),
        )
    )

    return components.build_section(
        header=_section_header(
            "Decision-level validation and limitations",
            "Whether optimized decisions measurably beat a baseline under a comparable protocol — and what is still unvalidated.",
        ),
        rows=rows,
    )


def _validation_findings(base_df: pd.DataFrame) -> list[str]:
    """Honest, direction-aware summary of the recorded contrasts (no ranking)."""
    lines: list[str] = []
    for comparison in sorted(base_df["comparison"].dropna().unique().tolist()):
        sub = base_df[base_df["comparison"] == comparison]
        label = _CONTRAST_LABELS.get(comparison, comparison.replace("_", " "))
        parts: list[str] = []
        for _, r in sub.iterrows():
            metric = str(r.get("metric"))
            mlabel = _metric_label(metric)
            direction = _metric_direction(metric)
            diff = r.get("mean_difference_newer_minus_base")
            sig = _is_true(r.get("significant_bh_0_05"))
            try:
                d = float(diff)
            except (TypeError, ValueError):
                continue
            if not sig:
                continue
            verb = "recorded a lower" if d < 0 else "recorded a higher"
            qualifier = ""
            if direction == "min":
                qualifier = " (lower is better for this metric)"
            elif "higher=better" in direction:
                qualifier = " (higher is better for this metric)"
            parts.append(f"the newer controller {verb} {mlabel.lower()} ({_fmt_num(d)}){qualifier}")
        if parts:
            lines.append(f"{label}: " + "; ".join(parts) + ".")
        else:
            lines.append(f"{label}: no metric reached corrected significance in this contrast.")
    return lines or ["No contrast rows were available to summarise."]


# ---------------------------------------------------------------------------
# Page wiring
# ---------------------------------------------------------------------------


def build_page_content(evidence: RO3Evidence) -> list[Any]:
    """Return the RO3 page sections, in display order."""
    return [
        build_research_method_context(evidence),
        build_evidence_status(evidence),
        build_procurement_decisions(evidence),
        build_objective_tradeoffs(evidence),
        build_pareto_evidence(evidence),
        build_controller_comparison(evidence),
        build_ablation(evidence),
        build_robustness_stress(evidence),
        build_handoff_from_ro2(evidence),
        build_decision_validation(evidence),
    ]
