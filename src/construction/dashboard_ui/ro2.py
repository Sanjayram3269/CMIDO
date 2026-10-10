"""Presentation builders for the RO2 · Uncertainty dashboard workspace.

Pure module — no Streamlit imports, no simulation/forecasting/optimization
engines, no artifact scanning. Every value flows through the existing 10A.2-B
dashboard data contract (:class:`RO2Evidence`) and its registry-driven adapters.

Scientific-integrity rules encoded in this module:

* Missing evidence renders as an explicit unavailable state, never as zero.
* The joint demand–supply propagation claim is gated on the registered
  propagation-audit artifact; without it the claim is not presented.
* Procurement-process duration is never relabelled as supplier-specific lead
  time; the recorded caveats travel with the numbers.
* Service-risk outputs are conditional exposure curves (SCN), not calibrated
  operational service levels.
* No composite uncertainty score or ranking is computed anywhere.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.construction.dashboard_data.contract import RO2Evidence
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

_BREADCRUMB_IDS = ("overview", "research", "ro2_uncertainty")
_IDS_PLACEHOLDER = {
    "ro2_uncertainty": "RO2 · Uncertainty",
    "research": "Research",
    "overview": "Overview",
}
_IDS_NOT_IMPLEMENTED = {"research"}

_QUANTILE_LEVELS = ("q50", "q75", "q90", "q95", "q99")


def _fill(color: str, alpha: float) -> str:
    """Build an rgba() fill from a theme token (no literal colour in UI code)."""
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


# ---------------------------------------------------------------------------
# Page shell metadata
# ---------------------------------------------------------------------------


def breadcrumb_ids() -> tuple[str, ...]:
    """Public breadcrumb trail for the RO2 page."""
    return _BREADCRUMB_IDS


def page_title() -> str:
    return "RO2 · Uncertainty"


def page_subtitle() -> str:
    return "Joint uncertainty propagation and service-risk evidence workspace."


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


def _is_integer_like(value: Any) -> bool:
    try:
        return float(value).is_integer()
    except (TypeError, ValueError):
        return False


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


def _fmt_days(value: Any, decimals: int = 1) -> str:
    try:
        return formatting.format_days(float(value), decimals=decimals)
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


def _first_origin(frame: pd.DataFrame) -> Any:
    """Earliest forecast origin present in the frame (honest preview choice)."""
    if frame.empty or "forecast_origin" not in frame.columns:
        return None
    origins = sorted(frame["forecast_origin"].dropna().unique().tolist(), key=str)
    return origins[0] if origins else None


def available_materials(evidence: RO2Evidence) -> list[str]:
    """Distinct materials present in the propagation summary (for app-layer filters)."""
    prop_df = _frame(evidence.propagation_summary)
    if prop_df.empty or "material" not in prop_df.columns:
        return []
    return sorted(prop_df["material"].dropna().unique().tolist())


def _snapshot_context(evidence: RO2Evidence) -> dict[str, Any]:
    """Curate research context derived ONLY from the RO2 evidence snapshot."""
    context: dict[str, Any] = {}

    joint_df = _frame(evidence.joint_propagation_summary)
    tail_df = _frame(evidence.tail_comparison)
    svc_df = _frame(evidence.service_risk_curve)
    sens_df = _frame(evidence.sensitivity)
    prop_df = _frame(evidence.propagation_summary)
    dist_df = _frame(evidence.distribution_decision)
    dur_df = _frame(evidence.duration_observed_stats)

    context["joint_df"] = joint_df
    context["tail_df"] = tail_df
    context["svc_df"] = svc_df
    context["sens_df"] = sens_df
    context["prop_df"] = prop_df
    context["dist_df"] = dist_df
    context["dur_df"] = dur_df

    context["joint_row_count"] = int(len(joint_df))
    context["tail_row_count"] = int(len(tail_df))
    context["svc_row_count"] = int(len(svc_df))
    context["sens_row_count"] = int(len(sens_df))
    context["prop_row_count"] = int(len(prop_df))
    context["dist_row_count"] = int(len(dist_df))
    context["dur_row_count"] = int(len(dur_df))

    context["materials"] = available_materials(evidence)

    if not prop_df.empty and "forecast_origin" in prop_df.columns:
        origins = sorted(prop_df["forecast_origin"].dropna().unique().tolist(), key=str)
        context["origins"] = origins
        context["first_origin"] = origins[0] if origins else None
    else:
        context["origins"] = []
        context["first_origin"] = None

    if not prop_df.empty and "representation" in prop_df.columns:
        context["representations"] = sorted(prop_df["representation"].dropna().unique().tolist())
    else:
        context["representations"] = []

    if not prop_df.empty and "mc_n" in prop_df.columns:
        mc_values = sorted({int(v) for v in prop_df["mc_n"].dropna().tolist()})
        context["mc_sizes"] = mc_values
    else:
        context["mc_sizes"] = []

    config = evidence.propagation_config or {}
    context["config"] = config if isinstance(config, dict) else {}
    context["audit"] = evidence.propagation_audit if isinstance(evidence.propagation_audit, dict) else {}
    context["convergence"] = evidence.convergence_summary if isinstance(evidence.convergence_summary, dict) else {}
    context["final_audit"] = evidence.final_audit if isinstance(evidence.final_audit, dict) else {}

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
        research_stage="RO2",
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
# A. Research question and methodology
# ---------------------------------------------------------------------------


def build_research_method_context(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    config = ctx["config"]

    materials = config.get("materials") or ctx["materials"]
    material_lines = _bulleted([str(m) for m in materials]) if materials else ["Material inventory not reported in RO2 artifacts."]

    source_horizons = config.get("source_horizons") or []
    horizon_text = (
        ", ".join(str(int(h)) if _is_integer_like(h) else str(h) for h in source_horizons)
        if source_horizons
        else "not reported in the loaded artifacts"
    )

    mc_draws = config.get("mc_draws")
    seed = config.get("seed")
    pair_n = config.get("duration_pair_n")
    primary = config.get("primary")
    terminology = config.get("duration_terminology")
    test_used = config.get("test_data_used")

    config_lines: list[str] = []
    if mc_draws is not None:
        config_lines.append(f"Monte Carlo draws per case: {_fmt_int(mc_draws)}.")
    if seed is not None:
        config_lines.append(f"Recorded random seed: {_fmt_int(seed)}.")
    if pair_n is not None:
        config_lines.append(f"Paired procurement-process duration observations: {_fmt_int(pair_n)}.")
    config_lines.append(f"Source forecast horizons: {horizon_text}.")
    if terminology:
        config_lines.append(f"Duration terminology recorded by the run: “{terminology}”.")
    if primary:
        config_lines.append(f"Primary representation: {primary}.")
    if test_used is not None:
        config_lines.append(
            "Held-out test data used by this run: "
            + ("yes" if bool(test_used) else "no (validation evidence only)")
            + "."
        )
    if not config_lines:
        config_lines.append("Run configuration artifact was not available for this workspace.")

    provenance_tally: dict[str, list[str]] = {}
    for entry in evidence.provenance:
        cls = str(getattr(_prov_get(entry, "provenance_class"), "value", _prov_get(entry, "provenance_class")) or "")
        role = str(_prov_get(entry, "evidence_role") or "")
        if cls:
            provenance_tally.setdefault(cls, []).append(role)
    prov_lines = [
        f"{cls} — " + " ".join(sorted({r for r in roles if r})) if any(provenance_tally[cls]) else cls
        for cls in provenance_tally
    ]

    rows = [
        _labeled_paragraph(
            "Research objective",
            (
                "RO2 quantifies how predictive uncertainty from RO1 demand forecasts combines with "
                "uncertainty in procurement-process durations, and what shortage exposure that "
                "combination implies for material procurement. It does not make procurement "
                "decisions — that is RO3's role. Every value on this page is read from registered "
                "research artifacts; nothing is re-simulated in the dashboard."
            ),
        ),
        _labeled_paragraph(
            "Relationship to RO1 and RO3",
            (
                "Upstream, RO1 supplies marginal predictive quantiles of demand (CQR-calibrated) for "
                "the demand side of the propagation. Downstream, RO3 consumes the resulting "
                "shortage/service-risk exposure and duration evidence as inputs to procurement "
                "optimization. RO2 is a propagation and exposure stage, not a decision stage."
            ),
        ),
        _labeled_paragraph("Materials propagated", _numbered_list(material_lines)),
        _labeled_paragraph("Run configuration (as recorded)", "\n".join(config_lines)),
        _labeled_paragraph(
            "Evidence provenance",
            "\n".join(prov_lines) if prov_lines else "No provenance metadata attached to the RO2 evidence snapshot.",
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Research question and methodology",
            "What RO2 evaluates, under which recorded configuration, and how it relates to RO1 and RO3.",
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# B. Evidence status
# ---------------------------------------------------------------------------


def build_evidence_status(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)

    nothing_loaded = ctx["artifact_total"] == 0
    cards_ = [
        cards.build_kpi(
            label="RO2 artifacts registered",
            value=str(ctx["artifact_total"]) if not nothing_loaded else formatting.MISSING_DISPLAY,
            description="Registered RO2 artifacts resolved by the 10A.2-B loader for this workspace.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Available",
            value=str(ctx["artifact_available"]) if not nothing_loaded else formatting.MISSING_DISPLAY,
            description="Artifacts loaded successfully with schema validation applied.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Not available",
            value=str(ctx["artifact_unavailable"]) if not nothing_loaded else formatting.MISSING_DISPLAY,
            description=(
                "Missing, invalid, unsupported or oversized artifacts. Their sections render as "
                "honest unavailable states, never as zeros."
            ),
            provenance="DER",
        ),
    ]

    rows: list[Any] = [components.build_kpi_columns(cards=cards_)]

    prov = ctx["provenance_rows"]
    if prov:
        frame = pd.DataFrame(prov)
        rows.append(
            _table_block(
                frame,
                columns=["artifact_id", "status", "provenance", "row_count", "schema_status"],
                headers=["Artifact", "Status", "Provenance", "Rows", "Schema"],
                caption="Loader outcome per registered RO2 artifact (AVAILABLE / MISSING / INVALID / TOO_LARGE / UNSUPPORTED).",
                formatter=lambda col, value: (
                    _fmt_int(value) if col == "row_count" else _fmt_cell(value)
                ),
            )
        )
    else:
        rows.append(
            components.build_unavailable_block(
                "No RO2 artifact provenance loaded",
                body=(
                    "The 10A.2-B loader returned no RO2 artifacts for this workspace, so no RO2 "
                    "evidence can be shown. Nothing is computed in their place."
                ),
            )
        )

    return components.build_section(
        header=_section_header(
            "Evidence status",
            "Which RO2 uncertainty artifacts loaded, and which are unavailable.",
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# C. Demand uncertainty
# ---------------------------------------------------------------------------


def build_demand_uncertainty(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    prop_df: pd.DataFrame = ctx["prop_df"]

    if prop_df.empty:
        return components.build_section(
            header=_section_header(
                "Demand uncertainty",
                "Demand-during-duration quantile evidence from the RO2 propagation run.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Demand-during-duration evidence unavailable",
                    body=(
                        "The registered RO2 propagation summary artifact was not available, so no "
                        "demand-uncertainty quantiles are shown. Missing evidence is never replaced "
                        "with zeros or with validation-split substitutes."
                    ),
                ),
            ],
        )

    joint_repr = "joint_duration_primary" if "joint_duration_primary" in set(ctx["representations"]) else None
    preview_df = prop_df
    if joint_repr is not None and "representation" in prop_df.columns:
        preview_df = prop_df[prop_df["representation"] == joint_repr]
    preview_origin = ctx["first_origin"]
    if preview_origin is not None and "forecast_origin" in preview_df.columns:
        preview_df = preview_df[preview_df["forecast_origin"] == preview_origin]

    cards_ = [
        cards.build_kpi(
            label="Materials propagated",
            value=str(len(ctx["materials"])) if ctx["materials"] else formatting.MISSING_DISPLAY,
            description="Distinct materials present in the propagation summary artifact.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Forecast origins",
            value=str(len(ctx["origins"])) if ctx["origins"] else formatting.MISSING_DISPLAY,
            description="Distinct monthly forecast origins evaluated by the propagation run.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="MC draws per case",
            value=(str(ctx["mc_sizes"][0]) if len(ctx["mc_sizes"]) == 1 else formatting.MISSING_DISPLAY),
            description=(
                "Monte Carlo draws recorded per material/origin case."
                if len(ctx["mc_sizes"]) == 1
                else "Multiple Monte Carlo sizes appear in the artifact; see the convergence section."
            ),
            provenance="DER",
        ),
    ]

    chart = _make_demand_quantile_figure(preview_df)

    rows: list[Any] = [
        components.build_kpi_columns(cards=cards_),
        components.build_chart(
            chart,
            caption=(
                f"Demand-during-duration quantiles for forecast origin {preview_origin} under the "
                f"{(joint_repr or 'recorded primary').replace('_', ' ')} representation. "
                "Values are Monte Carlo summaries, not observed outcomes."
            ),
            chart_config=charts.CHART_CONFIG_FORECAST,
        ),
        _table_block(
            preview_df,
            columns=["material", "mc_n", "mean_demand_during_duration", "median_demand_during_duration", "q50", "q90", "q95", "q99", "mc_se_mean"],
            headers=["Material", "MC n", "Mean", "Median", "q50", "q90", "q95", "q99", "MC SE (mean)"],
            caption=f"Per-material demand-during-duration summary, forecast origin {preview_origin}.",
            formatter=lambda col, value: _fmt_int(value) if col == "mc_n" else _fmt_num(value),
        ),
        components.build_note_bare(
            "Provenance: DER (Monte Carlo summary). Units are each material's native demand "
            "quantity. Demand uncertainty here is RO1's marginal predictive quantile representation "
            "propagated over the recorded duration distribution — it is not a fully joint future "
            "demand-path distribution."
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Demand uncertainty",
            "How demand uncertainty is represented and what the propagation run actually produced.",
        ),
        rows=rows,
    )


def _make_demand_quantile_figure(preview_df: pd.DataFrame) -> Any:
    import plotly.graph_objects as go

    fig = go.Figure()
    palette = theme.CATEGORICAL_PALETTE
    materials = (
        sorted(preview_df["material"].dropna().unique().tolist())
        if not preview_df.empty and "material" in preview_df.columns
        else []
    )
    levels = [lv for lv in _QUANTILE_LEVELS if preview_df.empty or lv in preview_df.columns]

    for idx, material in enumerate(materials):
        sub = preview_df[preview_df["material"] == material]
        if sub.empty:
            continue
        row = sub.iloc[0]
        fig.add_trace(
            go.Scatter(
                x=list(levels),
                y=[row.get(lv) for lv in levels],
                mode="lines+markers",
                name=str(material),
                line=dict(color=palette[idx % len(palette)]),
            )
        )

    fig.update_layout(
        legend_title_text="Material",
        height=360,
    )
    fig.update_xaxes(title_text="Quantile of demand during duration")
    fig.update_yaxes(title_text="Demand quantity (material units)")
    return fig


# ---------------------------------------------------------------------------
# D. Supply / lead-time (procurement-process duration) uncertainty
# ---------------------------------------------------------------------------


def build_supply_duration_uncertainty(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    dur_df: pd.DataFrame = ctx["dur_df"]
    dist_df: pd.DataFrame = ctx["dist_df"]

    rows: list[Any] = []

    if dur_df.empty:
        rows.append(
            components.build_unavailable_block(
                "Observed duration statistics unavailable",
                body=(
                    "The registered observed-duration statistics artifact was not available, so no "
                    "empirical duration evidence is shown. Fixed or assumed durations are never "
                    "presented as estimated distributions."
                ),
            )
        )
    else:
        rows.append(
            _table_block(
                dur_df,
                columns=[
                    "sheet", "leadtime_column", "n_source_rows", "n_numeric",
                    "n_missing_or_unparseable", "n_negative", "median", "mean", "q05", "q95", "max",
                ],
                headers=[
                    "Sheet", "Column", "Source rows", "Numeric", "Missing", "Negative",
                    "Median (d)", "Mean (d)", "q05 (d)", "q95 (d)", "Max (d)",
                ],
                caption="Observed procurement-process SLA/duration column statistics (days), as recorded.",
                formatter=lambda col, value: (
                    _fmt_days(value) if col in ("median", "mean", "q05", "q95", "max")
                    else _fmt_int(value) if col in ("n_source_rows", "n_numeric", "n_missing_or_unparseable", "n_negative")
                    else _fmt_cell(value)
                ),
            )
        )
        rows.append(
            components.build_note_bare(
                "Provenance: OBS. These are observed statistics of procurement-process SLA columns "
                "in the source records. They are NOT supplier-specific material lead-time "
                "distributions, and some columns contain missing or negative realisation values "
                "exactly as recorded."
            )
        )

    if dist_df.empty:
        rows.append(
            components.build_unavailable_block(
                "Distribution selection decision unavailable",
                body=(
                    "The registered provisional distribution-selection artifact was not available, "
                    "so no empirical-versus-parametric decision is shown for the duration "
                    "components."
                ),
            )
        )
    else:
        rows.append(
            _table_block(
                dist_df,
                columns=[
                    "variable", "recommended_status", "empirical_IS80",
                    "best_parametric_candidate", "best_parametric_IS80", "best_parametric_coverage80",
                ],
                headers=[
                    "Duration component", "Recommended status", "Empirical IS80",
                    "Best parametric candidate", "Parametric IS80", "Parametric coverage 80%",
                ],
                caption="Provisional empirical-versus-parametric selection per duration component (higher IS80 is better).",
                formatter=lambda col, value: (
                    _fmt_pct(value) if col == "best_parametric_coverage80"
                    else _fmt_num(value) if col in ("empirical_IS80", "best_parametric_IS80")
                    else _fmt_cell(value)
                ),
            )
        )
        rows.append(
            components.build_note_bare(
                "Provenance: DER. EMPIRICAL_PRIMARY means the empirical distribution outscored the "
                "best parametric candidate on the recorded IS80 criterion; a CANDIDATE status means "
                "the choice was not finalized and remains under review. These decisions are "
                "provisional as recorded by step 27C.2."
            )
        )

    return components.build_section(
        header=_section_header(
            "Supply and lead-time uncertainty",
            "Observed procurement-process duration evidence, with observations, estimates and assumptions kept apart.",
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# E. Joint propagation
# ---------------------------------------------------------------------------


def build_joint_propagation(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    joint_df: pd.DataFrame = ctx["joint_df"]
    audit: dict[str, Any] = ctx["audit"]
    convergence: dict[str, Any] = ctx["convergence"]

    if joint_df.empty:
        return components.build_section(
            header=_section_header(
                "Joint propagation",
                "Whether demand and duration uncertainties are propagated together, as evidenced.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Joint propagation evidence unavailable",
                    body=(
                        "The registered joint-propagation summary artifact was not available, so no "
                        "joint-propagation result is claimed or displayed on this page."
                    ),
                ),
            ],
        )

    row = joint_df.iloc[0]

    cards_ = [
        cards.build_kpi(
            label="Paired duration observations",
            value=_fmt_int(row.get("paired_n")),
            description="Component-paired procurement-process duration rows used by the propagation.",
            provenance="DER",
        ),
        cards.build_kpi(
            label="Pearson r",
            value=_fmt_num(row.get("pearson_r"), decimals=3),
            description=(
                f"p = {_fmt_num(row.get('pearson_p'), decimals=3)}; component pairing correlation "
                "as recorded."
            ),
            provenance="DER",
        ),
        cards.build_kpi(
            label="Spearman ρ",
            value=_fmt_num(row.get("spearman_rho"), decimals=3),
            description=(
                f"p = {_fmt_num(row.get('spearman_p'), decimals=3)}; bootstrap 95% CI "
                f"[{_fmt_num(row.get('spearman_bootstrap_ci_2_5'), decimals=3)}, "
                f"{_fmt_num(row.get('spearman_bootstrap_ci_97_5'), decimals=3)}]."
            ),
            provenance="DER",
        ),
        cards.build_kpi(
            label="Recorded decision",
            value=str(row.get("decision") or formatting.MISSING_DISPLAY).replace("_", " "),
            description=(
                "Independence assumption supported: "
                + ("yes" if str(row.get("independence_assumption_supported")).lower() in ("true", "1") else "no")
                + ", as recorded."
            ),
            provenance="DER",
        ),
    ]

    rows: list[Any] = [components.build_kpi_columns(cards=cards_)]

    if audit:
        interpretation = str(audit.get("interpretation") or "")
        rows.append(
            _labeled_paragraph(
                "What “joint” means here (audit 27D.1)",
                (
                    f"{interpretation}\n"
                    "Joint sampling means the observed internal / third-party / total duration "
                    "components are resampled as preserved pairs. Demand remains RO1's marginal "
                    "predictive quantile representation, so the overall model is a "
                    "marginal-demand / joint-duration propagation, not a fully joint "
                    "demand-and-supply distribution."
                ),
            )
        )
        rows.append(
            components.build_note_bare(
                f"Audit decision: {str(audit.get('decision', 'UNKNOWN')).replace('_', ' ')} "
                f"(distribution checks: {_fmt_cell(audit.get('distribution_checks_pass'))}; "
                f"service-risk checks: {_fmt_cell(audit.get('service_risk_checks_pass'))}; "
                f"structural checks: {_fmt_cell(audit.get('structural_checks_pass'))})."
            )
        )
    else:
        rows.append(
            components.build_unavailable_block(
                "Propagation audit not loaded — joint claim not validated here",
                body=(
                    "The registered 27D.1 propagation-audit artifact was not available, so the "
                    "numbers above are shown as recorded outputs only. This page does not present "
                    "them as a validated joint-propagation result without that audit."
                ),
            )
        )

    if convergence:
        max_change = convergence.get("max_10k_to_25k_relative_change_pct")
        rows.append(
            _labeled_paragraph(
                "Monte Carlo convergence (27D.4)",
                (
                    f"Decision: {str(convergence.get('decision', 'UNKNOWN')).replace('_', ' ')}; "
                    f"locked draws: {_fmt_int(convergence.get('recommended_mc_lock'))}; "
                    f"stable cases at 10k: {_fmt_int(convergence.get('stable_at_10000_n'))}/"
                    f"{_fmt_int(convergence.get('n_cases'))}; "
                    f"max 10k→25k relative change: "
                    f"{_fmt_pct(float(max_change) / 100.0, decimals=2) if max_change is not None else formatting.MISSING_DISPLAY}. "
                    "The nested common-random-number design removes random-stream variation from "
                    "the sample-size comparison; it does not by itself prove statistical convergence "
                    "(recorded note)."
                ),
            )
        )
    else:
        rows.append(
            components.build_unavailable_block(
                "Convergence evidence not loaded",
                body=(
                    "The registered nested-convergence artifact was not available, so the Monte "
                    "Carlo draw count is not presented as convergence-validated."
                ),
            )
        )

    return components.build_section(
        header=_section_header(
            "Joint propagation",
            "Joint demand–duration propagation is claimed only where the audit artifacts support it.",
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# F. Shortage and service-risk outcomes
# ---------------------------------------------------------------------------


def build_service_risk(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    svc_df: pd.DataFrame = ctx["svc_df"]

    if svc_df.empty:
        return components.build_section(
            header=_section_header(
                "Shortage and service-risk outcomes",
                "Conditional shortage exposure implied by the propagated demand-during-duration distributions.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Service-risk curve unavailable",
                    body=(
                        "The registered service-risk curve artifact was not available, so no "
                        "shortage probabilities or service levels are displayed. None are "
                        "recomputed or substituted."
                    ),
                ),
            ],
        )

    origin = _first_origin(svc_df)
    preview = svc_df[svc_df["forecast_origin"] == origin] if origin is not None else svc_df
    representations = sorted(preview["representation"].dropna().unique().tolist()) if "representation" in preview.columns else []
    primary_repr = "joint_duration_primary" if "joint_duration_primary" in representations else (representations[0] if representations else None)
    if primary_repr is not None:
        preview = preview[preview["representation"] == primary_repr]

    chart = _make_service_risk_figure(preview)

    rows: list[Any] = [
        components.build_chart(
            chart,
            caption=(
                f"Conditional shortage-probability curves for forecast origin {origin} "
                f"({(primary_repr or 'recorded representation').replace('_', ' ')}). Each point is "
                "the empirical fraction of Monte Carlo draws in which demand during duration "
                "exceeds the inventory threshold."
            ),
            chart_config=charts.CHART_CONFIG_FORECAST,
        ),
        _table_block(
            preview,
            columns=["material", "inventory_threshold", "shortage_probability", "service_level"],
            headers=["Material", "Inventory threshold (demand units)", "Shortage probability", "Service level"],
            caption=f"Service-risk points at forecast origin {origin}, as recorded.",
            formatter=lambda col, value: (
                _fmt_pct(value) if col in ("shortage_probability", "service_level")
                else _fmt_num(value) if col == "inventory_threshold"
                else _fmt_cell(value)
            ),
        ),
        components.build_note_bare(
            "Provenance: SCN. The threshold grid is the empirical quantile grid of the propagated "
            "demand-during-duration distribution; shortage probability is an empirical exceedance "
            "fraction over the recorded Monte Carlo draws. These are conditional exposure-risk "
            "curves, NOT empirically calibrated operational service levels, and they are not "
            "historical shortage frequencies."
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Shortage and service-risk outcomes",
            "Only actual recorded outputs, with units, denominators and provenance attached.",
        ),
        rows=rows,
    )


def _make_service_risk_figure(preview: pd.DataFrame) -> Any:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    materials = (
        sorted(preview["material"].dropna().unique().tolist())
        if not preview.empty and "material" in preview.columns
        else []
    )
    if not materials:
        return go.Figure()

    cols = min(2, len(materials))
    rows_n = (len(materials) + cols - 1) // cols
    fig = make_subplots(
        rows=rows_n,
        cols=cols,
        subplot_titles=[str(m) for m in materials],
        shared_yaxes=True,
    )
    palette = theme.CATEGORICAL_PALETTE
    for idx, material in enumerate(materials):
        sub = preview[preview["material"] == material].sort_values("inventory_threshold")
        r = (idx // cols) + 1
        c = (idx % cols) + 1
        fig.add_trace(
            go.Scatter(
                x=sub.get("inventory_threshold"),
                y=sub.get("shortage_probability"),
                mode="lines+markers",
                name=str(material),
                showlegend=False,
                line=dict(color=palette[idx % len(palette)]),
            ),
            row=r,
            col=c,
        )

    fig.update_layout(height=340 * rows_n, legend_title_text="Material")
    fig.update_xaxes(title_text="Inventory threshold (demand units)")
    fig.update_yaxes(title_text="Shortage probability")
    return fig


# ---------------------------------------------------------------------------
# G. Material and scenario comparisons
# ---------------------------------------------------------------------------


def build_material_comparison(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    sens_df: pd.DataFrame = ctx["sens_df"]

    if sens_df.empty:
        return components.build_section(
            header=_section_header(
                "Material and scenario comparisons",
                "Joint versus independent duration propagation across materials.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Comparison evidence unavailable",
                    body=(
                        "The registered joint-versus-independent sensitivity artifact was not "
                        "available, so no cross-representation comparison is displayed."
                    ),
                ),
            ],
        )

    origin = _first_origin(sens_df)
    preview = sens_df[sens_df["forecast_origin"] == origin] if origin is not None else sens_df

    chart = _make_sensitivity_figure(preview)

    rows: list[Any] = [
        components.build_chart(
            chart,
            caption=(
                f"Independent-minus-joint difference (percent of joint) across quantiles, forecast "
                f"origin {origin}. Positive values mean the independent assumption produces larger "
                "demand-during-duration quantiles than the joint representation."
            ),
            chart_config=charts.CHART_CONFIG_FORECAST,
        ),
        _table_block(
            preview,
            columns=[
                "material", "quantile",
                "joint_duration_days_q50_q99_distribution",
                "independent_duration_sensitivity", "independent_minus_joint", "independent_vs_joint_pct",
            ],
            headers=["Material", "Quantile", "Joint (demand units)", "Independent (demand units)", "Difference", "Difference (%)"],
            caption=(
                f"Joint versus independent propagation at forecast origin {origin}. The artifact "
                f"holds {len(sens_df)} rows covering all evaluated material/origin cases."
            ),
            formatter=lambda col, value: (
                _fmt_pct(value) if col == "independent_vs_joint_pct"
                else _fmt_num(value) if col in ("joint_duration_days_q50_q99_distribution", "independent_duration_sensitivity", "independent_minus_joint")
                else _fmt_cell(value)
            ),
        ),
        components.build_note_bare(
            "Provenance: DER. All comparisons are within a single propagation run (same recorded "
            "configuration, same Monte Carlo draws), so materials and representations are directly "
            "comparable to each other. Percentages are relative to the joint representation. No "
            "composite ranking across materials is computed."
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Material and scenario comparisons",
            "Only compatible evidence from a single recorded propagation run is compared.",
        ),
        rows=rows,
    )


def _make_sensitivity_figure(preview: pd.DataFrame) -> Any:
    import plotly.graph_objects as go

    fig = go.Figure()
    palette = theme.CATEGORICAL_PALETTE
    materials = (
        sorted(preview["material"].dropna().unique().tolist())
        if not preview.empty and "material" in preview.columns
        else []
    )
    for idx, material in enumerate(materials):
        sub = preview[preview["material"] == material].sort_values("quantile")
        fig.add_trace(
            go.Scatter(
                x=sub.get("quantile"),
                y=sub.get("independent_vs_joint_pct"),
                mode="lines+markers",
                name=str(material),
                line=dict(color=palette[idx % len(palette)]),
            )
        )
    fig.update_layout(height=340, legend_title_text="Material")
    fig.update_xaxes(title_text="Quantile level of demand during duration")
    fig.update_yaxes(title_text="Independent vs joint (%)")
    return fig


# ---------------------------------------------------------------------------
# H. Sensitivity and stress evidence
# ---------------------------------------------------------------------------


def build_sensitivity_stress(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    tail_df: pd.DataFrame = ctx["tail_df"]
    convergence: dict[str, Any] = ctx["convergence"]

    rows: list[Any] = []

    if tail_df.empty:
        rows.append(
            components.build_unavailable_block(
                "Tail comparison unavailable",
                body=(
                    "The registered duration tail-comparison artifact was not available, so no "
                    "tail-quantile evidence is displayed."
                ),
            )
        )
    else:
        chart = _make_tail_figure(tail_df)
        rows.extend(
            [
                components.build_chart(
                    chart,
                    caption=(
                        "Duration quantiles under the observed paired totals, the joint empirical "
                        "component resampling and the independent marginal resampling, as recorded."
                    ),
                    chart_config=charts.CHART_CONFIG_FORECAST,
                ),
                _table_block(
                    tail_df,
                    columns=["quantile", "representation", "quantile_days", "difference_vs_observed", "relative_difference_pct"],
                    headers=["Quantile", "Representation", "Duration (days)", "Difference vs observed (d)", "Difference (%)"],
                    caption="Duration tail comparison exactly as recorded in the registered artifact.",
                    formatter=lambda col, value: (
                        _fmt_pct(value) if col == "relative_difference_pct"
                        else _fmt_days(value) if col in ("quantile_days", "difference_vs_observed")
                        else _fmt_cell(value)
                    ),
                ),
            ]
        )

    if convergence:
        max_change = convergence.get("max_10k_to_25k_relative_change_pct")
        cards_ = [
            cards.build_kpi(
                label="Convergence decision",
                value=str(convergence.get("decision", "UNKNOWN")).replace("_", " "),
                description="Recorded nested-convergence decision from step 27D.4.",
                provenance="DER",
            ),
            cards.build_kpi(
                label="Stable cases at 10k draws",
                value=(
                    f"{_fmt_int(convergence.get('stable_at_10000_n'))}/{_fmt_int(convergence.get('n_cases'))}"
                    if convergence.get("n_cases") is not None
                    else formatting.MISSING_DISPLAY
                ),
                description="Material/origin cases meeting the recorded stability criteria at the locked draw count.",
                provenance="DER",
            ),
            cards.build_kpi(
                label="Max 10k→25k change",
                value=_fmt_pct(float(max_change) / 100.0, decimals=2) if max_change is not None else formatting.MISSING_DISPLAY,
                description="Largest recorded relative change when draws were raised from 10k to 25k.",
                provenance="DER",
            ),
        ]
        rows.append(components.build_kpi_columns(cards=cards_))
        rows.append(
            components.build_note_bare(
                "These are evaluated stress experiments on the Monte Carlo draw count, not "
                "hypothetical scenarios. Earlier non-nested screening (27D.2) held for review; the "
                "nested re-evaluation (27D.4) produced the recorded lock decision shown above."
            )
        )
    else:
        rows.append(
            components.build_unavailable_block(
                "Monte Carlo convergence evidence unavailable",
                body=(
                    "The registered nested-convergence artifact was not available, so no draw-count "
                    "stability result is displayed."
                ),
            )
        )

    return components.build_section(
        header=_section_header(
            "Sensitivity and stress evidence",
            "Evaluated experiments only; hypothetical or planned stress scenarios are not shown as results.",
        ),
        rows=rows,
    )


def _make_tail_figure(tail_df: pd.DataFrame) -> Any:
    import plotly.graph_objects as go

    fig = go.Figure()
    palette = theme.CATEGORICAL_PALETTE
    representations = (
        tail_df["representation"].dropna().unique().tolist()
        if "representation" in tail_df.columns
        else []
    )
    for idx, repr_name in enumerate(representations):
        sub = tail_df[tail_df["representation"] == repr_name].sort_values("quantile")
        fig.add_trace(
            go.Scatter(
                x=sub.get("quantile"),
                y=sub.get("quantile_days"),
                mode="lines+markers",
                name=str(repr_name),
                line=dict(color=palette[idx % len(palette)]),
            )
        )
    fig.update_layout(height=340, legend_title_text="Representation")
    fig.update_xaxes(title_text="Quantile level of procurement-process duration")
    fig.update_yaxes(title_text="Duration (days)")
    return fig


# ---------------------------------------------------------------------------
# I. Uncertainty handoff to RO3
# ---------------------------------------------------------------------------


def build_handoff_to_ro3(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    final_audit = ctx["final_audit"]

    if not final_audit:
        return components.build_section(
            header=_section_header(
                "Uncertainty handoff to RO3",
                "What downstream procurement optimization may consume from RO2.",
            ),
            rows=[
                components.build_unavailable_block(
                    "Handoff summary unavailable",
                    body=(
                        "The registered RO2 final-audit artifact was not available, so the handoff "
                        "contract is described from the propagation artifacts only and no locked "
                        "handoff state is claimed."
                    ),
                ),
            ],
        )

    next_stage = str(final_audit.get("next_stage") or "not recorded")
    audit_27d = final_audit.get("27D") or {}
    audit_27d4 = final_audit.get("27D4") or {}
    primary_repr = str(audit_27d.get("primary_representation") or "not recorded")

    rows: list[Any] = [
        _labeled_paragraph(
            "What RO3 may consume",
            _bulleted(
                [
                    "Per-material demand-during-duration quantile summaries (joint representation) from the propagation run.",
                    "Conditional shortage/service-risk curves per material and forecast origin.",
                    "The joint-versus-independent sensitivity evidence supporting the choice of representation.",
                    f"The convergence-locked Monte Carlo configuration ({_fmt_int(audit_27d4.get('mc_lock'))} draws, {_fmt_int(audit_27d4.get('stable_cases_at_10000'))} stable cases at lock).",
                    "The recorded duration-distribution decisions and their caveats.",
                ]
            ),
        ),
        _labeled_paragraph(
            "What is NOT claimed here",
            (
                "RO2 does not demonstrate improved procurement decisions — that requires "
                "decision-level validation, which RO2 does not perform. The safety-stock quantity "
                "appearing in RO2 outputs is a benchmark/interpretability quantity; RO3 defines "
                "safety stock as an actual decision variable. No cost, award or allocation outcome "
                "is implied by anything on this page."
            ),
        ),
        _labeled_paragraph(
            "Recorded handoff state",
            (
                f"Primary representation: {primary_repr}. "
                f"Calendar overlap between demand and duration windows recorded: "
                f"{_fmt_cell(audit_27d.get('calendar_overlap'))}. "
                f"Next stage recorded by the audit: {next_stage}."
            ),
        ),
    ]

    return components.build_section(
        header=_section_header(
            "Uncertainty handoff to RO3",
            "How supported uncertainty outputs inform procurement decisions — without implying those decisions have been validated.",
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# J. Limitations and next evidence required
# ---------------------------------------------------------------------------


def build_limitations(evidence: RO2Evidence) -> components.SectionBlock:
    ctx = _snapshot_context(evidence)
    final_audit = ctx["final_audit"]
    audit = ctx["audit"]

    caveats = final_audit.get("caveats") if isinstance(final_audit, dict) else None

    rows: list[Any] = []
    if caveats:
        rows.append(
            _labeled_paragraph(
                "Recorded caveats (verbatim from the RO2 final audit)",
                _bulleted([str(c) for c in caveats]),
            )
        )
    else:
        rows.append(
            components.build_unavailable_block(
                "Recorded caveats unavailable",
                body=(
                    "The registered RO2 final-audit artifact was not available, so the recorded "
                    "caveat list is not displayed. The absence of that list must not be read as an "
                    "absence of caveats."
                ),
            )
        )

    if audit:
        mc_status = str(audit.get("mc_stability_status") or "")
        interpretation = str(audit.get("interpretation") or "")
        body = interpretation
        if mc_status:
            body = f"MC stability status recorded as {mc_status}. {interpretation}".strip()
        if body:
            rows.append(
                _labeled_paragraph("Audit-level limitation (27D.1)", body)
            )

    rows.append(
        _labeled_paragraph(
            "Next evidence required",
            _bulleted(
                [
                    "Supplier-specific material lead-time distributions (the current evidence is procurement-process duration, not supplier lead time).",
                    "Empirically calibrated service levels validated against realized shortage outcomes (current curves are conditional exposure only).",
                    "Historical shortage labels to test the exposure curves against reality.",
                    "Price-side (RO1_PRICE) uncertainty propagation — the recorded propagation run covers demand materials only.",
                    "Decision-level validation in RO3 before any claim that propagated uncertainty improves procurement outcomes.",
                ]
            ),
        )
    )

    return components.build_section(
        header=_section_header(
            "Limitations and next evidence required",
            "What this workspace cannot support yet, and which concrete artifacts would change that.",
        ),
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Page wiring
# ---------------------------------------------------------------------------


def build_page_content(evidence: RO2Evidence) -> list[Any]:
    """Return the RO2 page sections, in display order."""
    return [
        build_research_method_context(evidence),
        build_evidence_status(evidence),
        build_demand_uncertainty(evidence),
        build_supply_duration_uncertainty(evidence),
        build_joint_propagation(evidence),
        build_service_risk(evidence),
        build_material_comparison(evidence),
        build_sensitivity_stress(evidence),
        build_handoff_to_ro3(evidence),
        build_limitations(evidence),
    ]
