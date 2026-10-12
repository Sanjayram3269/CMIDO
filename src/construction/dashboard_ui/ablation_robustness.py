# ---------------------------------------------------------------------------
# CMIDO 10A.12 — Ablation & Robustness workspace
#
# Read-only, schema-validated, provenance-aware rendering of the registered
# ablation, controller-comparison, stress, holding-rate robustness,
# sensitivity, convergence and integrity-gate evidence. This module does NOT
# run research computations, does NOT import research engines, does NOT
# recompute any statistical test, and does NOT rank or score controllers.
#
# Scientific-integrity rules encoded in this module:
#
# * No controller is presented as universally superior. Where a recorded
#   contrast shows a cost-service trade-off, the trade-off is surfaced as
#   recorded; no composite score is computed anywhere.
# * Statistical significance, effect magnitude, practical importance and
#   descriptive difference are kept apart: T5/T6 comparisons are reported with
#   their recorded bootstrap intervals and multiplicity-corrected p-values,
#   while the stress and holding-rate artifacts record descriptive
#   differences only and are labelled as such.
# * Non-significance is never presented as equivalence. The interpretation
#   section says so explicitly.
# * Stress cases and holding-rate cases are controlled scenario perturbations
#   (SCN), never observed real-world disruptions (OBS).
# * Missing or invalid artifacts render as explicit unavailable states, never
#   as zero and never as an inferred value.
# * Scenario-count convergence is reported exactly as its registered artifact
#   recorded it, including the recorded failure of the primary transition.
# * No hard-coded scientific values: every number displayed flows through the
#   10A.2-B snapshot contract from a registered artifact. Controller
#   definitions and contrast attributions are design metadata taken from the
#   documented RO3.6 ablation specification (labels only, no results).
# * Raw repository paths, sha256 source paths and hex colours never reach the
#   rendered page.
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Any

import pandas as pd

from src.construction.dashboard_data.contract import (
    DashboardSnapshot,
    RO2Evidence,
    RO3Evidence,
)
from src.construction.dashboard_ui import charts
from src.construction.dashboard_ui import components
from src.construction.dashboard_ui import formatting
from src.construction.dashboard_ui import theme
from src.construction.dashboard_ui.navigation import (
    page_by_id,
    page_is_planned,
)
from src.construction.dashboard_ui.sections import (
    build_page_header,
)

# Presentation helpers shared with the other registry-driven workspaces:
# honest missing values, provenance record reads, audit-path suppression and
# the shared metric vocabulary.
from ._procurement_helpers import (
    _bulleted,
    _clean_audit_detail,
    _fmt_cell,
    _fmt_int,
    _fmt_num,
    _fmt_pct,
    _frame,
    _is_true,
    _labeled_paragraph,
    _metric_direction,
    _metric_label,
    _prov_get,
    _status_text,
)

PAGE_ID = "ablation_robustness"
RESEARCH_STAGE = "ABLATION"

#: Registered artifacts presented by this workspace, in display order.
ABLATION_ARTIFACT_IDS: tuple[str, ...] = (
    "ABLATION_8M_GATE_MANIFEST",
    "ABLATION_8M_GATE_AUDIT",
    "RO3_CONTROLLER_DESCRIPTIVES",
    "RO3_BASELINE_COMPARISON",
    "RO3_ABLATION",
    "RO3_STRESS_SUMMARY",
    "RO3_STRESS_PAIRED",
    "RO3_ROBUSTNESS_SUMMARY",
    "RO3_HOLDING_CONTRASTS",
    "RO3_HOLDING_SENSITIVITY",
    "RO3_CONVERGENCE_SUMMARY",
    "RO3_FINAL_AUDIT",
    "RO2_SENSITIVITY",
    "RO2_CONVERGENCE_SUMMARY",
)

#: Human titles for the registered artifact ids (presentation only).
_ARTIFACT_TITLES: dict[str, str] = {
    "ABLATION_8M_GATE_MANIFEST": "8M ablation evidence gate manifest",
    "ABLATION_8M_GATE_AUDIT": "8M ablation evidence gate audit",
    "RO3_CONTROLLER_DESCRIPTIVES": "Controller descriptives (T5/T6)",
    "RO3_BASELINE_COMPARISON": "Controller pairwise comparison (T5)",
    "RO3_ABLATION": "2×2 component ablation (T6)",
    "RO3_STRESS_SUMMARY": "Stress-test summary (step 37)",
    "RO3_STRESS_PAIRED": "Stress paired changes (step 37)",
    "RO3_ROBUSTNESS_SUMMARY": "Holding-rate robustness summary (step 38)",
    "RO3_HOLDING_CONTRASTS": "Holding-rate controller contrasts (step 38)",
    "RO3_HOLDING_SENSITIVITY": "Holding-rate sensitivity vs H30 (step 38)",
    "RO3_CONVERGENCE_SUMMARY": "RO3 scenario-count convergence (step 33)",
    "RO3_FINAL_AUDIT": "RO3 final experimental integrity audit (step 39)",
    "RO2_SENSITIVITY": "RO2 joint-vs-independent sensitivity (T3)",
    "RO2_CONVERGENCE_SUMMARY": "RO2 nested Monte-Carlo convergence (27D.4)",
}

#: Recorded 2×2 controller conditions. Source: documented RO3.6 controlled
#: baseline and ablation specification. These are design labels, not results.
_CONTROLLER_DEFS: dict[str, str] = {
    "O1": "Deterministic + heuristic (baseline)",
    "O2": "Deterministic + optimisation",
    "O3": "Probabilistic + heuristic",
    "O4": "Probabilistic + optimisation (CMIDO)",
}

#: Human labels for the recorded T5/T6 contrasts, matching the attribution
#: plan of the documented ablation specification.
_CONTRAST_LABELS: dict[str, str] = {
    "O2_vs_O1": "O2 vs O1 — value of optimisation under deterministic information",
    "O3_vs_O1": "O3 vs O1 — value of probabilistic information under heuristic control",
    "O4_vs_O2": "O4 vs O2 — incremental value of uncertainty-aware optimisation",
    "O4_vs_O3": "O4 vs O3 — incremental value of optimisation under probabilistic information",
    "O4_vs_O1": "O4 vs O1 — integrated CMIDO vs deterministic heuristic baseline",
}


# ---------------------------------------------------------------------------
# Pure presentation builders (no Streamlit, no research engine)
# ---------------------------------------------------------------------------


def _humanize(token: Any) -> str:
    """Display label for a recorded identifier: underscores become spaces.

    This is a display transform only. It never changes a value and never
    derives new meaning from a name.
    """
    return str(token).replace("_", " ")


def _contrast_label(token: Any) -> str:
    """Human label for a recorded contrast id, honest fallback when unknown."""
    key = str(token or "")
    return _CONTRAST_LABELS.get(key, _humanize(key))


def _controller_label(token: Any) -> str:
    """Human label for a recorded controller id, honest fallback when unknown."""
    key = str(token or "")
    return _CONTROLLER_DEFS.get(key, key or formatting.MISSING_DISPLAY)


def provenance_code(value: Any) -> str:
    """The OBS/DER/EST/SCN code recorded for a value, or an honest blank."""
    return str(getattr(value, "value", value) or "")


def build_provenance_rows(evidence: RO3Evidence, ro2: RO2Evidence) -> list[dict[str, Any]]:
    """Curate the provenance inventory of this workspace's artifacts.

    One row per provenance record attached to the RO3 bundle plus the two RO2
    artifacts this page presents. Statuses are carried through exactly as the
    loader and validator recorded them.
    """
    wanted = set(ABLATION_ARTIFACT_IDS)
    rows: list[dict[str, Any]] = []
    for entry in list(evidence.provenance) + list(ro2.provenance):
        artifact_id = str(_prov_get(entry, "artifact_id", ""))
        if artifact_id not in wanted:
            continue
        rows.append(
            {
                "artifact_id": artifact_id,
                "status": _status_text(_prov_get(entry, "status")),
                "provenance_class": provenance_code(
                    _prov_get(entry, "provenance_class")
                ),
                "research_stage": str(_prov_get(entry, "research_stage", "") or ""),
                "row_count": _prov_get(entry, "row_count"),
                "file_size_bytes": _prov_get(entry, "file_size_bytes"),
                "schema_status": str(
                    _prov_get(entry, "schema_status", "UNCHECKED") or "UNCHECKED"
                ),
            }
        )
    return rows


def artifact_status_index(provenance_rows: list[dict[str, Any]]) -> dict[str, str]:
    """Map artifact id -> recorded status; absent artifacts read MISSING."""
    index = {
        row["artifact_id"]: row["status"]
        for row in provenance_rows
        if row.get("artifact_id")
    }
    for artifact_id in ABLATION_ARTIFACT_IDS:
        index.setdefault(artifact_id, "MISSING")
    return index


def _provenance_class_for(
    provenance_rows: list[dict[str, Any]], artifact_id: str
) -> str:
    for row in provenance_rows:
        if row["artifact_id"] == artifact_id:
            return row["provenance_class"]
    return ""


def build_artifact_table_rows(
    provenance_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Display rows for the registered artifact inventory."""
    by_id = {row["artifact_id"]: row for row in provenance_rows}
    rows: list[dict[str, Any]] = []
    for artifact_id in ABLATION_ARTIFACT_IDS:
        record = by_id.get(artifact_id)
        if record is None:
            rows.append(
                {
                    "Artifact": _ARTIFACT_TITLES[artifact_id],
                    "Status": "NOT REGISTERED",
                    "Provenance": formatting.MISSING_DISPLAY,
                    "Rows": formatting.MISSING_DISPLAY,
                    "Schema check": formatting.MISSING_DISPLAY,
                }
            )
            continue
        rows.append(
            {
                "Artifact": _ARTIFACT_TITLES[artifact_id],
                "Status": record["status"],
                "Provenance": record["provenance_class"]
                or formatting.MISSING_DISPLAY,
                "Rows": _fmt_int(record["row_count"])
                if record["row_count"] is not None
                else formatting.MISSING_DISPLAY,
                "Schema check": _humanize(record["schema_status"])
                if record["schema_status"] not in ("", "UNCHECKED")
                else record["schema_status"],
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Design / gate builders
# ---------------------------------------------------------------------------


def build_design_cards(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """KPI row derived entirely from the recorded 8M gate manifest.

    Missing manifest fields render as missing, never as zero.
    """
    controllers = manifest.get("controllers")
    origins = manifest.get("locked_origins")
    materials = manifest.get("common_materials")
    passed = manifest.get("checks_passed")
    total = manifest.get("checks_total")
    unit = manifest.get("inferential_unit")

    gate_value = (
        f"{_fmt_int(passed)} of {_fmt_int(total)}"
        if passed is not None and total is not None
        else formatting.MISSING_DISPLAY
    )
    return [
        {
            "label": "Controllers evaluated",
            "value": _fmt_int(len(controllers))
            if isinstance(controllers, list) and controllers
            else formatting.MISSING_DISPLAY,
            "description": "Controlled 2×2 arms recorded by the ablation evidence gate.",
            "research_stage": RESEARCH_STAGE,
            "provenance": "DER",
        },
        {
            "label": "Locked forecast origins",
            "value": _fmt_int(len(origins))
            if isinstance(origins, list) and origins
            else formatting.MISSING_DISPLAY,
            "description": "Inferential units frozen for the common evaluation.",
            "research_stage": RESEARCH_STAGE,
            "provenance": "DER",
        },
        {
            "label": "Common materials",
            "value": _fmt_int(len(materials))
            if isinstance(materials, list) and materials
            else formatting.MISSING_DISPLAY,
            "description": "Materials shared by every controlled arm.",
            "research_stage": RESEARCH_STAGE,
            "provenance": "DER",
        },
        {
            "label": "Evidence-gate checks",
            "value": gate_value,
            "description": (
                "Artifact-presence and consistency checks recorded by the 8M gate"
                + (
                    f"; inferential unit recorded as {_humanize(unit)}."
                    if unit
                    else "."
                )
            ),
            "research_stage": RESEARCH_STAGE,
            "provenance": "DER",
        },
    ]


def build_design_rows(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Label/value rows describing the recorded experimental design."""
    controllers = manifest.get("controllers")
    origins = manifest.get("locked_origins")
    materials = manifest.get("common_materials")
    rows = [
        {
            "Property": "Controller arms",
            "Recorded value": ", ".join(str(c) for c in controllers)
            if isinstance(controllers, list) and controllers
            else formatting.MISSING_DISPLAY,
        },
        {
            "Property": "Arm definitions",
            "Recorded value": "; ".join(
                f"{cid} = {_CONTROLLER_DEFS[cid]}" if cid in _CONTROLLER_DEFS else str(cid)
                for cid in (controllers or [])
            )
            if isinstance(controllers, list) and controllers
            else formatting.MISSING_DISPLAY,
        },
        {
            "Property": "Locked forecast origins",
            "Recorded value": ", ".join(str(o) for o in origins)
            if isinstance(origins, list) and origins
            else formatting.MISSING_DISPLAY,
        },
        {
            "Property": "Common materials",
            "Recorded value": ", ".join(str(m) for m in materials)
            if isinstance(materials, list) and materials
            else formatting.MISSING_DISPLAY,
        },
        {
            "Property": "Inferential unit",
            "Recorded value": _humanize(manifest["inferential_unit"])
            if manifest.get("inferential_unit")
            else formatting.MISSING_DISPLAY,
        },
    ]
    return rows


def build_gate_audit_rows(manifest: dict[str, Any], audit: dict[str, Any]) -> list[dict[str, str]]:
    """Check/passed/detail rows for the 8M gate audit, with paths suppressed."""
    raw_rows = audit.get("audit_rows") if isinstance(audit, dict) else None
    rows: list[dict[str, str]] = []
    for record in raw_rows or []:
        detail = _clean_audit_detail(str(_prov_get(record, "detail", "") or ""))
        passed = _prov_get(record, "passed")
        rows.append(
            {
                "Check": _humanize(_prov_get(record, "check", "")),
                "Passed": _fmt_cell(passed) if isinstance(passed, bool) else formatting.MISSING_DISPLAY,
                "Recorded detail": detail or formatting.MISSING_DISPLAY,
            }
        )
    return rows


def build_gate_source_rows(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Humanised source-artifact roles and fingerprints from the 8M manifest.

    Only the role name and the recorded sha256 fingerprint are surfaced; the
    recorded filesystem paths and the project root are deliberately dropped.
    """
    sources = manifest.get("source_artifacts")
    if not isinstance(sources, dict):
        return []
    rows: list[dict[str, str]] = []
    for role, payload in sources.items():
        fingerprint = ""
        if isinstance(payload, dict):
            fingerprint = str(payload.get("sha256") or "")
        rows.append(
            {
                "Source artifact": _humanize(role),
                "SHA-256 fingerprint": fingerprint or formatting.MISSING_DISPLAY,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Comparison builders (T5 statistically tested, T6 with effect sizes)
# ---------------------------------------------------------------------------


def build_comparison_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Display rows for the T5 pairwise comparison artifact.

    Every displayed statistic is read from the artifact: means, mean
    difference, recorded bootstrap interval, recorded Wilcoxon p and the
    recorded Benjamini-Hochberg significance flag.
    """
    rows: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        rows.append(
            {
                "Contrast": _contrast_label(record.get("comparison")),
                "Metric": _metric_label(record.get("metric")),
                "Newer mean": _fmt_num(record.get("newer_mean")),
                "Base mean": _fmt_num(record.get("base_mean")),
                "Mean difference (newer − base)": _fmt_num(
                    record.get("mean_difference_newer_minus_base")
                ),
                "95% CI lower": _fmt_num(record.get("bootstrap_ci95_lower")),
                "95% CI upper": _fmt_num(record.get("bootstrap_ci95_upper")),
                "Wilcoxon p (raw)": _fmt_num(record.get("wilcoxon_p_raw"), decimals=4),
                "BH-adjusted q": _fmt_num(record.get("wilcoxon_q_bh"), decimals=4),
                "Corrected significance": _fmt_cell(record.get("significant_bh_0_05")),
            }
        )
    return rows


def build_ablation_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Display rows for the T6 ablation artifact, effect sizes included."""
    rows: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        rows.append(
            {
                "Contrast": _contrast_label(record.get("comparison")),
                "Metric": _metric_label(record.get("metric")),
                "Relative mean difference": _fmt_pct(
                    record.get("relative_mean_difference"), decimals=1
                ),
                "Mean difference (newer − base)": _fmt_num(
                    record.get("mean_difference_newer_minus_base")
                ),
                "Rank-biserial": _fmt_num(record.get("rank_biserial_sign")),
                "Origins improved / worsened / tied": (
                    f"{_fmt_int(record.get('improved_count'))} / "
                    f"{_fmt_int(record.get('worsened_count'))} / "
                    f"{_fmt_int(record.get('tie_count'))}"
                ),
                "BH-adjusted q": _fmt_num(record.get("wilcoxon_q_bh"), decimals=4),
                "Corrected significance": _fmt_cell(record.get("significant_bh_0_05")),
            }
        )
    return rows


def _metric_is_better_when_lower(metric: Any) -> bool:
    """True when the recorded metric direction is minimisation."""
    return _metric_direction(metric) == "min"


def _direction_phrase(metric: Any, difference: float) -> str:
    """Plain-language direction phrase for a recorded mean difference."""
    lower = "lower" if difference < 0 else "higher"
    direction = _metric_direction(metric)
    if direction == "min":
        qualifier = "lower is better for this metric"
    elif "higher=better" in direction:
        qualifier = "higher is better for this metric"
    else:
        qualifier = "reported without a better-direction claim"
    return f"{lower} ({qualifier})"


def build_contrast_findings(frame: pd.DataFrame) -> list[str]:
    """Direction-aware, significance-gated findings per recorded contrast.

    Only rows whose recorded corrected-significance flag is true are
    summarised as differences; rows that did not reach corrected significance
    are listed separately and explicitly NOT interpreted as equivalence.
    """
    findings: list[str] = []
    if frame.empty or "comparison" not in frame.columns:
        return [
            "The registered comparison artifact was unavailable, so no contrast "
            "finding is stated here."
        ]
    for comparison in sorted(frame["comparison"].dropna().unique().tolist()):
        sub = frame[frame["comparison"] == comparison]
        label = _contrast_label(comparison)
        significant: list[str] = []
        not_significant: list[str] = []
        better_count = 0
        worse_count = 0
        for _, record in sub.iterrows():
            metric = record.get("metric")
            # Lowercase only the opening character: lowercasing the whole label
            # would turn recorded tokens like CVaR_0.95 into snake_case.
            raw_label = _metric_label(metric)
            metric_label = (
                raw_label[:1].lower() + raw_label[1:] if raw_label else raw_label
            )
            difference = record.get("mean_difference_newer_minus_base")
            try:
                delta = float(difference)
            except (TypeError, ValueError):
                continue
            if _is_true(record.get("significant_bh_0_05")):
                significant.append(
                    f"the newer controller recorded a {_direction_phrase(metric, delta)} "
                    f"{metric_label} ({_fmt_num(delta)})"
                )
                if _metric_is_better_when_lower(metric):
                    if delta < 0:
                        better_count += 1
                    else:
                        worse_count += 1
                else:
                    if delta > 0:
                        better_count += 1
                    else:
                        worse_count += 1
            else:
                not_significant.append(metric_label)
        lines: list[str] = []
        if significant:
            lines.append("Statistically tested differences: " + "; ".join(significant) + ".")
        else:
            lines.append(
                "No metric in this contrast reached corrected significance in the "
                "recorded artifact."
            )
        if not_significant:
            lines.append(
                "Did not reach corrected significance: "
                + ", ".join(not_significant)
                + ". This is not evidence of equivalence between the arms — the "
                "recorded test simply did not resolve a difference at this sample size."
            )
        if significant and better_count and worse_count:
            lines.append(
                "Trade-off, not a uniform win: within this contrast the newer "
                "controller is significantly better on some recorded metrics and "
                "significantly worse on others. No composite score is computed and "
                "no overall winner is declared."
            )
        elif significant and better_count:
            lines.append(
                "All statistically tested metrics in this contrast moved in the "
                "better direction for the newer controller. This remains a "
                "within-protocol result over the locked evaluation window."
            )
        elif significant and worse_count:
            lines.append(
                "All statistically tested metrics in this contrast moved in the "
                "worse direction for the newer controller."
            )
        findings.append(label + " " + " ".join(lines))
    return findings


def build_descriptive_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Per-controller descriptive rows (means across locked origins)."""
    rows: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        rows.append(
            {
                "Controller": _controller_label(record.get("controller")),
                "Origins": _fmt_int(record.get("n_origins")),
                "Mean cost": _fmt_num(record.get("realized_procurement_holding_cost_mean")),
                "Mean shortage": _fmt_num(record.get("realized_total_shortage_mean")),
                "Mean service level": _fmt_pct(record.get("realized_service_level_mean")),
                "Mean CVaR 95% shortage": _fmt_num(
                    record.get("realized_shortage_cvar95_monthly_mean")
                ),
                "Mean ending inventory": _fmt_num(
                    record.get("realized_mean_ending_inventory_mean")
                ),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Stress and holding-rate builders (descriptive only — no test recorded)
# ---------------------------------------------------------------------------


def build_stress_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Recorded stress-case outcomes per controller (SCN, descriptive)."""
    rows: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        rows.append(
            {
                "Controller": _controller_label(record.get("controller")),
                "Stress case": str(record.get("stress_case") or formatting.MISSING_DISPLAY),
                "Disruption duration (days)": _fmt_num(
                    record.get("duration_days"), decimals=1
                ),
                "Origins": _fmt_int(record.get("n_origins")),
                "Mean cost": _fmt_num(record.get("mean_cost")),
                "Mean shortage": _fmt_num(record.get("mean_shortage")),
                "Mean service level": _fmt_pct(record.get("mean_service")),
                "Mean inventory": _fmt_num(record.get("mean_inventory")),
            }
        )
    return rows


def build_stress_paired_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Recorded paired stress changes per controller (descriptive only)."""
    rows: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        rows.append(
            {
                "Controller": _controller_label(record.get("controller")),
                "Comparison": _humanize(record.get("comparison")),
                "Metric": _humanize(record.get("metric")),
                "Mean difference": _fmt_num(record.get("mean_difference")),
                "Median difference": _fmt_num(record.get("median_difference")),
                "Min difference": _fmt_num(record.get("min_difference")),
                "Max difference": _fmt_num(record.get("max_difference")),
            }
        )
    return rows


def build_holding_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Recorded holding-rate outcomes per controller (SCN, descriptive)."""
    rows: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        rows.append(
            {
                "Controller": _controller_label(record.get("controller")),
                "Holding case": str(record.get("holding_case") or formatting.MISSING_DISPLAY),
                "Annual holding rate": _fmt_pct(record.get("annual_holding_rate")),
                "Origins": _fmt_int(record.get("n_origins")),
                "Mean cost": _fmt_num(record.get("mean_cost")),
                "Mean shortage": _fmt_num(record.get("mean_shortage")),
                "Mean service level": _fmt_pct(record.get("mean_service")),
            }
        )
    return rows


def build_holding_contrast_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Recorded controller contrasts within each holding-rate case."""
    rows: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        rows.append(
            {
                "Holding case": str(record.get("holding_case") or formatting.MISSING_DISPLAY),
                "Contrast": _contrast_label(record.get("contrast")),
                "Metric": _humanize(record.get("metric")),
                "Mean difference": _fmt_num(record.get("mean_difference")),
                "Median difference": _fmt_num(record.get("median_difference")),
                "Min difference": _fmt_num(record.get("min_difference")),
                "Max difference": _fmt_num(record.get("max_difference")),
            }
        )
    return rows


def build_holding_sensitivity_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Recorded per-controller sensitivity of each holding case vs H30."""
    rows: list[dict[str, Any]] = []
    for _, record in frame.iterrows():
        rows.append(
            {
                "Controller": _controller_label(record.get("controller")),
                "Comparison": _humanize(record.get("comparison")),
                "Metric": _humanize(record.get("metric")),
                "Mean difference": _fmt_num(record.get("mean_difference")),
                "Median difference": _fmt_num(record.get("median_difference")),
                "Min difference": _fmt_num(record.get("min_difference")),
                "Max difference": _fmt_num(record.get("max_difference")),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Convergence and sensitivity builders
# ---------------------------------------------------------------------------


def build_ro3_convergence_lines(convergence: dict[str, Any]) -> list[str]:
    """Recorded RO3 scenario-count convergence, including its recorded limits."""
    if not convergence:
        return [
            "The registered RO3 convergence artifact was unavailable, so no "
            "scenario-count convergence status is claimed on this page."
        ]
    sizes = convergence.get("scenario_sizes") or []
    sizes_text = ", ".join(_fmt_int(s) for s in sizes) if sizes else "not recorded"
    decision = _humanize(convergence.get("decision") or "not recorded")
    primary_pass = convergence.get("primary_pass")
    failed = convergence.get("primary_failed_comparisons")
    primary_max = convergence.get("primary_max_relative_change")
    later_max = convergence.get("later_max_relative_change")
    later_required = convergence.get("optimization_level_convergence_required_later")

    lines = [
        f"Scenario sizes evaluated: {sizes_text}.",
        f"Recorded primary transition: {_humanize(convergence.get('primary_transition') or 'not recorded')}.",
        f"Primary transition passed its threshold: {_fmt_cell(primary_pass)}.",
    ]
    if failed is not None:
        lines.append(f"Failed comparisons at the primary transition: {_fmt_int(failed)}.")
    if primary_max is not None:
        lines.append(
            f"Maximum relative change at the primary transition: {_fmt_pct(float(primary_max), decimals=2)}."
        )
    if later_max is not None:
        lines.append(
            f"Maximum relative change over the later transitions: {_fmt_pct(float(later_max), decimals=2)}."
        )
    lines.append(f"Recorded decision: {decision}.")
    if later_required is not None:
        lines.append(
            "Optimisation-level convergence recorded as still required at a later "
            f"stage: {_fmt_cell(later_required)}."
        )
    lines.append(
        "Reported exactly as recorded. The primary scenario-count transition did "
        "not clear its threshold; the recorded decision proceeded at the "
        "evaluated scenario count and the artifact records optimisation-level "
        "convergence as a later requirement. This constrains how strongly the "
        "optimisation results may be generalised beyond the evaluated count."
    )
    return lines


def build_ro2_convergence_lines(convergence: dict[str, Any]) -> list[str]:
    """Recorded RO2 nested Monte-Carlo convergence (27D.4)."""
    if not convergence:
        return [
            "The registered RO2 convergence artifact was unavailable, so no "
            "Monte-Carlo convergence status is claimed on this page."
        ]
    decision = _humanize(convergence.get("decision") or "not recorded")
    lock = convergence.get("recommended_mc_lock")
    stable_n = convergence.get("stable_at_10000_n")
    cases = convergence.get("n_cases")
    change_5k_10k = convergence.get("max_5k_to_10k_relative_change_pct")
    change_10k_25k = convergence.get("max_10k_to_25k_relative_change_pct")
    lines = [
        f"Recorded decision: {decision}.",
        f"Recommended Monte-Carlo lock: {_fmt_int(lock)} draws."
        if lock is not None
        else "Recommended Monte-Carlo lock: not recorded.",
    ]
    if stable_n is not None and cases is not None:
        lines.append(
            f"Cases stable at the lock size: {_fmt_int(stable_n)} of {_fmt_int(cases)}."
        )
    if change_5k_10k is not None:
        lines.append(
            f"Maximum relative change from 5k to 10k draws: {_fmt_pct(float(change_5k_10k), decimals=2)}."
        )
    if change_10k_25k is not None:
        lines.append(
            f"Maximum relative change from 10k to 25k draws: {_fmt_pct(float(change_10k_25k), decimals=2)}."
        )
    lines.append(
        "Monte-Carlo convergence is an evaluated property of the propagation "
        "run; it is reported as recorded, not re-derived here."
    )
    return lines


def build_sensitivity_summary(sensitivity: list[dict[str, Any]]) -> dict[str, Any]:
    """Coverage and recorded range of the RO2 joint-vs-independent sensitivity.

    Only counts and the min/max of an already-recorded column are shown; no
    statistical test is derived and no new quantity is computed.
    """
    summary: dict[str, Any] = {
        "rows": len(sensitivity),
        "materials": [],
        "quantiles": [],
        "pct_min": None,
        "pct_max": None,
    }
    if not sensitivity:
        return summary
    frame = _frame(sensitivity)
    if "material" in frame.columns:
        summary["materials"] = sorted(
            str(m) for m in frame["material"].dropna().unique().tolist()
        )
    if "quantile" in frame.columns:
        summary["quantiles"] = sorted(
            float(q) for q in frame["quantile"].dropna().unique().tolist()
        )
    if "independent_vs_joint_pct" in frame.columns:
        values = pd.to_numeric(frame["independent_vs_joint_pct"], errors="coerce").dropna()
        if not values.empty:
            summary["pct_min"] = float(values.min())
            summary["pct_max"] = float(values.max())
    return summary


def build_sensitivity_preview_rows(
    sensitivity: list[dict[str, Any]], limit: int = 12
) -> list[dict[str, Any]]:
    """A short preview of the recorded sensitivity rows, as recorded."""
    frame = _frame(sensitivity)
    if frame.empty:
        return []
    preview = frame.head(limit)
    rows: list[dict[str, Any]] = []
    for _, record in preview.iterrows():
        rows.append(
            {
                "Material": str(record.get("material") or formatting.MISSING_DISPLAY),
                "Forecast origin": str(
                    record.get("forecast_origin") or formatting.MISSING_DISPLAY
                ),
                "Quantile": _fmt_pct(record.get("quantile"), decimals=2),
                "Joint duration (days)": _fmt_num(
                    record.get("joint_duration_days_q50_q99_distribution")
                ),
                "Independent duration (days)": _fmt_num(
                    record.get("independent_duration_sensitivity")
                ),
                "Independent − joint": _fmt_num(record.get("independent_minus_joint")),
                "Independent vs joint (%)": _fmt_num(
                    record.get("independent_vs_joint_pct")
                ),
            }
        )
    return rows


def build_integrity_rows(audit: dict[str, Any]) -> list[dict[str, str]]:
    """Check/passed/detail rows for the RO3 final audit, paths suppressed."""
    raw_rows = audit.get("audit_rows") if isinstance(audit, dict) else None
    rows: list[dict[str, str]] = []
    for record in raw_rows or []:
        detail = _clean_audit_detail(str(_prov_get(record, "detail", "") or ""))
        passed = _prov_get(record, "passed")
        rows.append(
            {
                "Check": _humanize(_prov_get(record, "check", "")),
                "Passed": _fmt_cell(passed) if isinstance(passed, bool) else formatting.MISSING_DISPLAY,
                "Recorded detail": detail or formatting.MISSING_DISPLAY,
            }
        )
    return rows


def build_integrity_summary(audit: dict[str, Any]) -> list[str]:
    """Honest summary lines of what the recorded integrity audits verify."""
    raw_rows = audit.get("audit_rows") if isinstance(audit, dict) else None
    if not raw_rows:
        return [
            "The registered RO3 integrity-audit artifact was unavailable, so no "
            "audit outcome is claimed on this page."
        ]
    passed = sum(1 for r in raw_rows if _is_true(_prov_get(r, "passed")))
    lines = [
        f"Recorded audit checks: {len(raw_rows)}, passed: {passed}, "
        f"not passed: {len(raw_rows) - passed}.",
        "These audits verify artifact presence, row counts, locked-design "
        "adherence and configuration consistency of the recorded experiment. "
        "They do not validate real-world outcomes and they do not re-run any "
        "statistical test.",
    ]
    return lines


# ---------------------------------------------------------------------------
# Charts (theme-inherited, values straight from recorded artifacts)
# ---------------------------------------------------------------------------


def _make_tradeoff_figure(descriptives: pd.DataFrame) -> Any:
    """Cost-versus-service positioning of the recorded controller means.

    A scatter of already-recorded descriptive means. No ranking, no composite
    score, no optimality claim — pure positioning of recorded values.
    """
    import plotly.graph_objects as go

    fig = go.Figure()
    if (
        descriptives.empty
        or "realized_procurement_holding_cost_mean" not in descriptives.columns
        or "realized_service_level_mean" not in descriptives.columns
    ):
        return fig
    fig.add_trace(
        go.Scatter(
            x=descriptives["realized_procurement_holding_cost_mean"],
            y=descriptives["realized_service_level_mean"],
            mode="markers+text",
            name="Recorded controller means",
            text=[
                str(c) for c in descriptives.get("controller", [""] * len(descriptives))
            ],
            textposition="top center",
            marker=dict(size=12, color=theme.ACCENT),
        )
    )
    fig.update_layout(height=380, showlegend=False)
    fig.update_xaxes(title_text="Mean realised procurement + holding cost (min)")
    fig.update_yaxes(title_text="Mean realised service level (higher is better)")
    return fig


def _make_stress_figure(stress: pd.DataFrame) -> Any:
    """Recorded mean service level per controller across stress durations."""
    import plotly.graph_objects as go

    fig = go.Figure()
    if (
        stress.empty
        or "controller" not in stress.columns
        or "duration_days" not in stress.columns
        or "mean_service" not in stress.columns
    ):
        return fig
    colors = charts.get_categorical_colors(int(stress["controller"].nunique()) or 1)
    for index, controller in enumerate(
        sorted(stress["controller"].dropna().unique().tolist())
    ):
        sub = stress[stress["controller"] == controller].sort_values("duration_days")
        fig.add_trace(
            go.Scatter(
                x=sub["duration_days"],
                y=sub["mean_service"],
                mode="lines+markers",
                name=_controller_label(controller),
                line=dict(color=colors[index % len(colors)], width=2),
            )
        )
    fig.update_layout(height=380, showlegend=True)
    fig.update_xaxes(title_text="Recorded disruption duration (days)")
    fig.update_yaxes(title_text="Mean realised service level (higher is better)")
    return fig


# ---------------------------------------------------------------------------
# Render sections
# ---------------------------------------------------------------------------


def _render_overview(
    evidence: RO3Evidence,
    provenance_rows: list[dict[str, Any]],
) -> None:
    """Top-level framing: what the 2×2 design is and what this page reports."""
    total = len(provenance_rows)
    available = sum(1 for row in provenance_rows if row["status"] == "AVAILABLE")
    if total and available == total:
        state = "available"
    elif available:
        state = "partial"
    else:
        state = "empty"

    components.render_section_header(
        title="Ablation and robustness evidence",
        subtitle=(
            "The controlled 2×2 controller design, its statistically tested "
            "comparisons, the scenario-based stress and holding-rate evidence, "
            "and the convergence and integrity gates behind them."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state=state,
        methodology=(
            "Registry-driven (10A.2-B). Statistically tested comparisons are "
            "reported with their recorded intervals and corrected p-values; "
            "stress and holding-rate artifacts record descriptive differences "
            "only and are labelled as such. Nothing is recomputed in the UI."
        ),
        provenance="See the artifact inventory and each section's provenance note.",
        uncertainty=(
            "All outcomes are realised under the recorded evaluation protocol "
            "over the locked forecast origins; they are not observed "
            "procurement operations."
        ),
    )

    components.render_kpi_columns(build_design_cards(evidence.ablation_gate_manifest))

    components.render_paragraph(
        {
            "label": "What this page reports",
            "body": [
                "Four controlled arms of the documented RO3.6 design — O1 deterministic + heuristic,",
                "O2 deterministic + optimisation, O3 probabilistic + heuristic, O4 probabilistic +",
                "optimisation (CMIDO) — evaluated over the same locked forecast origins, materials",
                "and horizon, plus the robustness evidence around that experiment:",
                "",
                "- Statistically tested controller comparisons and the 2×2 component ablation, each",
                "  reported with recorded bootstrap intervals and Benjamini-Hochberg corrected significance.",
                "- Descriptive controller statistics across the locked origins.",
                "- Scenario-based stress cases (disrupted procurement durations) and holding-rate",
                "  cases — controlled perturbations, not observed disruptions.",
                "- Scenario-count and Monte-Carlo convergence diagnostics, reported as recorded.",
                "- The ablation evidence gate and the final experimental integrity audit.",
                "",
                "No controller is ranked or scored on this page. Where the recorded evidence shows a",
                "cost-service trade-off, the trade-off is shown as recorded.",
            ],
        }
    )


def _render_artifact_inventory(
    evidence: RO3Evidence,
    provenance_rows: list[dict[str, Any]],
    status_index: dict[str, str],
) -> None:
    """Registered-artifact inventory plus explicit states for anything absent."""
    components.render_section_header(
        title="Registered ablation and robustness artifacts",
        subtitle=(
            "Every artifact behind this page, with the status, provenance class "
            "and schema outcome the loader and validator recorded."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE" if provenance_rows else "empty",
        methodology=(
            "Loaded through the 10A.2-B artifact registry within the recorded "
            "size caps; the raw scenario ledgers remain blocked by policy."
        ),
        provenance="Registry provenance records (schema status included).",
    )

    rows = build_artifact_table_rows(provenance_rows)
    components.render_table(
        pd.DataFrame(rows),
        source="10A.2-B artifact registry and provenance records",
        research_stage=RESEARCH_STAGE,
        empty_message="No ablation or robustness artifacts were registered for this snapshot.",
    )

    for artifact_id in ABLATION_ARTIFACT_IDS:
        status = status_index.get(artifact_id, "MISSING")
        if status != "AVAILABLE":
            components.render_artifact_state(
                artifact_id,
                status,
                description=_ARTIFACT_TITLES[artifact_id],
                stage=RESEARCH_STAGE,
                provenance=_provenance_class_for(provenance_rows, artifact_id),
            )


def _render_design_section(evidence: RO3Evidence) -> None:
    """The recorded experimental design and the 8M evidence gate."""
    manifest = evidence.ablation_gate_manifest
    components.render_section_header(
        title="Experimental design and evidence gate",
        subtitle=(
            "The controlled design frozen before evaluation, and the gate that "
            "verified its artifacts were present and consistent."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE" if manifest else "empty",
        methodology=(
            "Design properties are read from the registered 8M gate manifest; "
            "the gate verifies artifact presence, row counts and configuration "
            "consistency — it does not validate scientific conclusions."
        ),
        provenance="DER (validation gate over recorded experiment artifacts).",
    )

    if not manifest:
        components.render_artifact_state(
            "ABLATION_8M_GATE_MANIFEST",
            "MISSING",
            description=_ARTIFACT_TITLES["ABLATION_8M_GATE_MANIFEST"],
            stage=RESEARCH_STAGE,
        )
        components.render_paragraph(
            {
                "label": "Why this matters",
                "body": [
                    "Without the gate manifest the frozen design (controller arms, locked",
                    "origins, common materials, inferential unit) cannot be independently",
                    "confirmed from registered evidence, so no design property is asserted here.",
                ],
            }
        )
        return

    components.render_inline_label_values(
        [
            {
                "label": row["Property"],
                "body": row["Recorded value"],
            }
            for row in build_design_rows(manifest)
        ]
    )

    audit_rows = build_gate_audit_rows(manifest, evidence.ablation_gate_audit)
    if audit_rows:
        components.render_table(
            pd.DataFrame(audit_rows),
            title="8M gate checks",
            caption=(
                "Per-check outcomes recorded by the ablation evidence gate. "
                "Recorded filesystem paths are suppressed."
            ),
            source="8M ablation evidence gate audit",
            research_stage=RESEARCH_STAGE,
        )

    source_rows = build_gate_source_rows(manifest)
    if source_rows:
        components.render_table(
            pd.DataFrame(source_rows),
            title="Source artifacts and fingerprints",
            caption=(
                "Roles and recorded SHA-256 fingerprints of the artifacts the "
                "gate verified. Recorded paths and the project root are "
                "deliberately not displayed."
            ),
            source="8M ablation evidence gate manifest",
            research_stage=RESEARCH_STAGE,
        )

    components.render_paragraph(
        {
            "label": "What the gate does and does not establish",
            "body": [
                "The gate establishes that the frozen experiment's artifacts exist, carry the",
                "expected schema and cover the locked arms, origins and materials. It does not",
                "establish external validity, deployment readiness or real-world performance,",
                "and it does not re-run any statistical test.",
            ],
        }
    )


def _render_comparison_section(evidence: RO3Evidence) -> None:
    """T5 pairwise comparisons: statistically tested, direction-aware."""
    frame = _frame(evidence.baseline_comparison)
    components.render_section_header(
        title="Statistically tested controller comparisons",
        subtitle=(
            "Pairwise contrasts of realised outcomes with recorded bootstrap "
            "intervals and multiplicity-corrected significance."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE" if not frame.empty else "empty",
        methodology=(
            "Paired per-forecast-origin comparisons over the locked evaluation "
            "population, with recorded bootstrap 95% intervals and recorded "
            "Benjamini-Hochberg correction at 0.05. Tests are reported as "
            "recorded; none is re-run here."
        ),
        provenance="EST (recorded statistical comparison over realised outcomes).",
        uncertainty=(
            "Statistical significance is not practical importance; effect "
            "magnitudes are in the metric's own units and are shown alongside."
        ),
    )

    if frame.empty:
        components.render_artifact_state(
            "RO3_BASELINE_COMPARISON",
            "MISSING",
            description=_ARTIFACT_TITLES["RO3_BASELINE_COMPARISON"],
            stage=RESEARCH_STAGE,
            provenance="EST",
        )
        components.render_paragraph(
            {
                "label": "Why this matters",
                "body": [
                    "Without the registered comparison artifact no statistically tested",
                    "controller claim is made on this page. Nothing is computed in its place.",
                ],
            }
        )
        return

    components.render_paragraph(
        {
            "label": "Recorded findings, per contrast",
            "body": build_contrast_findings(frame),
        }
    )
    components.render_table(
        pd.DataFrame(build_comparison_rows(frame)),
        title="Pairwise comparison detail",
        caption=(
            "Every column is read from the registered comparison artifact. "
            "Corrected significance is the artifact's own Benjamini-Hochberg flag."
        ),
        source="T5 controller pairwise comparison",
        research_stage=RESEARCH_STAGE,
    )
    components.render_html(
        components.build_note_bare(
            "Provenance: EST. Differences are newer controller minus base "
            "controller. Cost and shortage are minimised objectives; service "
            "level is a realised outcome where higher is better. A "
            "non-significant row is not evidence of equivalence between the "
            "arms."
        )
    )


def _render_ablation_section(evidence: RO3Evidence) -> None:
    """T6 component ablation: incremental value with recorded effect sizes."""
    frame = _frame(evidence.ablation)
    components.render_section_header(
        title="2×2 component ablation",
        subtitle=(
            "Incremental decision value of each component, with recorded "
            "relative effect sizes and per-origin direction counts."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE" if not frame.empty else "empty",
        methodology=(
            "Contrasts follow the documented attribution plan: O2−O1 isolates "
            "optimisation under deterministic information, O3−O1 isolates "
            "probabilistic information under heuristic control, O4−O2 and "
            "O4−O3 isolate the incremental contributions inside CMIDO."
        ),
        provenance="EST (recorded statistical ablation over realised outcomes).",
        uncertainty=(
            "Effect magnitudes are relative to the base arm's recorded mean; "
            "significance is the artifact's corrected flag."
        ),
    )

    if frame.empty:
        components.render_artifact_state(
            "RO3_ABLATION",
            "MISSING",
            description=_ARTIFACT_TITLES["RO3_ABLATION"],
            stage=RESEARCH_STAGE,
            provenance="EST",
        )
        components.render_paragraph(
            {
                "label": "Why this matters",
                "body": [
                    "Without the registered ablation artifact no component-attribution claim",
                    "is made on this page. Nothing is computed in its place.",
                ],
            }
        )
        return

    components.render_table(
        pd.DataFrame(build_ablation_rows(frame)),
        caption=(
            "Recorded ablation statistics per contrast and metric. Improved / "
            "worsened / tied counts are the artifact's own per-origin direction "
            "counts under the metric's recorded direction."
        ),
        source="T6 2×2 component ablation",
        research_stage=RESEARCH_STAGE,
    )
    components.render_html(
        components.build_note_bare(
            "Provenance: EST. Attribution is conditional on the recorded "
            "design: each contrast isolates one factor while holding the "
            "others as recorded. Attribution does not imply universal "
            "superiority — see the recorded trade-offs in the comparison "
            "section above."
        )
    )


def _render_descriptives_section(evidence: RO3Evidence) -> None:
    """Per-controller descriptive statistics (no inference attached)."""
    frame = _frame(evidence.controller_descriptives)
    components.render_section_header(
        title="Controller descriptives",
        subtitle=(
            "Recorded per-controller means across the locked forecast origins."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE" if not frame.empty else "empty",
        methodology=(
            "Descriptive statistics only. No significance test is attached to "
            "these values; use the comparison and ablation sections for "
            "tested statements."
        ),
        provenance="DER (recorded descriptive aggregation).",
    )

    if frame.empty:
        components.render_artifact_state(
            "RO3_CONTROLLER_DESCRIPTIVES",
            "MISSING",
            description=_ARTIFACT_TITLES["RO3_CONTROLLER_DESCRIPTIVES"],
            stage=RESEARCH_STAGE,
            provenance="DER",
        )
        return

    components.render_chart(
        _make_tradeoff_figure(frame),
        title="Recorded cost-service positioning",
        caption=(
            "Each point is one controller's recorded mean cost and mean "
            "service level across the locked origins. The chart positions "
            "recorded values; it does not rank arms and no composite score is "
            "computed."
        ),
        research_stage=RESEARCH_STAGE,
        provenance="DER",
        chart_config=charts.CHART_CONFIG_FORECAST,
    )
    components.render_table(
        pd.DataFrame(build_descriptive_rows(frame)),
        caption="Recorded per-controller descriptives, as aggregated by the source artifact.",
        source="T5/T6 controller descriptives",
        research_stage=RESEARCH_STAGE,
    )


def _render_stress_section(evidence: RO3Evidence) -> None:
    """Scenario-based stress evidence: simulated perturbations, descriptive."""
    summary = _frame(evidence.stress_summary)
    paired = _frame(evidence.stress_paired)
    components.render_section_header(
        title="Stress testing (scenario-based)",
        subtitle=(
            "Recorded outcomes under disrupted procurement durations, per "
            "controller and stress case."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE" if not (summary.empty and paired.empty) else "empty",
        methodology=(
            "Stress cases re-evaluate the recorded decisions under perturbed "
            "procurement-process durations. The paired-change artifact records "
            "descriptive differences only — no significance test is recorded "
            "in it, and none is derived here."
        ),
        provenance="SCN (controlled scenario perturbations, not observed disruptions).",
        uncertainty=(
            "These are simulated stress scenarios. They are not observed "
            "real-world disruption outcomes."
        ),
    )

    if summary.empty and paired.empty:
        components.render_artifact_state(
            "RO3_STRESS_SUMMARY",
            "MISSING",
            description=_ARTIFACT_TITLES["RO3_STRESS_SUMMARY"],
            stage=RESEARCH_STAGE,
            provenance="SCN",
        )
        components.render_paragraph(
            {
                "label": "Why this matters",
                "body": [
                    "Without the registered stress artifacts no stress behaviour is claimed",
                    "for any controller on this page. Nothing is computed in its place.",
                ],
            }
        )
        return

    if not summary.empty:
        components.render_chart(
            _make_stress_figure(summary),
            title="Recorded service level under stress",
            caption=(
                "Mean realised service level per controller at each recorded "
                "stress duration. Values are read from the registered stress "
                "summary; no trend is fitted and no extrapolation is shown."
            ),
            research_stage=RESEARCH_STAGE,
            provenance="SCN",
            chart_config=charts.CHART_CONFIG_FORECAST,
        )
        components.render_table(
            pd.DataFrame(build_stress_rows(summary)),
            title="Stress-case outcomes",
            caption="Recorded per-controller, per-case stress outcomes (SCN).",
            source="RO3 step 37 stress summary",
            research_stage=RESEARCH_STAGE,
        )

    if not paired.empty:
        components.render_table(
            pd.DataFrame(build_stress_paired_rows(paired)),
            title="Paired stress changes vs the P50 case",
            caption=(
                "Recorded per-origin paired differences of each stress case "
                "versus the P50 case. Descriptive statistics only — the "
                "artifact records no significance test."
            ),
            source="RO3 step 37 stress paired changes",
            research_stage=RESEARCH_STAGE,
        )

    components.render_html(
        components.build_note_bare(
            "Provenance: SCN. A stress result shows how recorded decisions "
            "behave under perturbed assumptions; it is not evidence of "
            "observed disruption performance, and a descriptive difference is "
            "not a statistically tested one."
        )
    )


def _render_robustness_section(evidence: RO3Evidence) -> None:
    """Holding-rate robustness: parameter sensitivity, descriptive."""
    summary = _frame(evidence.robustness_summary)
    contrasts = _frame(evidence.holding_contrasts)
    sensitivity = _frame(evidence.holding_sensitivity)
    components.render_section_header(
        title="Holding-rate robustness",
        subtitle=(
            "Recorded outcomes and controller contrasts across annual "
            "holding-rate cases, plus sensitivity versus the base case."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE"
        if not (summary.empty and contrasts.empty and sensitivity.empty)
        else "empty",
        methodology=(
            "Holding-rate cases vary a cost parameter of the evaluation; the "
            "recorded artifacts hold everything else as recorded. All three "
            "artifacts record descriptive differences only — no significance "
            "test is recorded in them, and none is derived here."
        ),
        provenance="SCN (controlled parameter variation, not observed economics).",
        uncertainty=(
            "Holding-rate variation is a sensitivity over a cost assumption, "
            "not an observed economic measurement."
        ),
    )

    if summary.empty and contrasts.empty and sensitivity.empty:
        components.render_artifact_state(
            "RO3_ROBUSTNESS_SUMMARY",
            "MISSING",
            description=_ARTIFACT_TITLES["RO3_ROBUSTNESS_SUMMARY"],
            stage=RESEARCH_STAGE,
            provenance="SCN",
        )
        components.render_paragraph(
            {
                "label": "Why this matters",
                "body": [
                    "Without the registered robustness artifacts no holding-rate sensitivity",
                    "is claimed for any controller on this page. Nothing is computed in its place.",
                ],
            }
        )
        return

    if not summary.empty:
        components.render_table(
            pd.DataFrame(build_holding_rows(summary)),
            title="Holding-rate outcomes",
            caption="Recorded per-controller, per-case holding-rate outcomes (SCN).",
            source="RO3 step 38 holding-rate summary",
            research_stage=RESEARCH_STAGE,
        )
    if not contrasts.empty:
        components.render_table(
            pd.DataFrame(build_holding_contrast_rows(contrasts)),
            title="Controller contrasts within each holding-rate case",
            caption=(
                "Recorded controller contrasts per case. Descriptive statistics "
                "only — the artifact records no significance test."
            ),
            source="RO3 step 38 holding-rate controller contrasts",
            research_stage=RESEARCH_STAGE,
        )
    if not sensitivity.empty:
        components.render_table(
            pd.DataFrame(build_holding_sensitivity_rows(sensitivity)),
            title="Sensitivity versus the H30 base case",
            caption=(
                "Recorded per-controller changes of each holding-rate case "
                "versus the H30 base case. Descriptive statistics only."
            ),
            source="RO3 step 38 holding-rate sensitivity vs H30",
            research_stage=RESEARCH_STAGE,
        )

    components.render_html(
        components.build_note_bare(
            "Provenance: SCN. Holding-rate cases are a controlled parameter "
            "variation. A descriptive difference between cases is not a "
            "statistically tested difference, and holding-rate robustness "
            "does not establish robustness to other parameters."
        )
    )


def _render_sensitivity_section(ro2: RO2Evidence) -> None:
    """RO2 joint-vs-independent duration sensitivity (assumption sensitivity)."""
    sensitivity = list(ro2.sensitivity or [])
    components.render_section_header(
        title="Upstream assumption sensitivity (RO2)",
        subtitle=(
            "How much the recorded demand-during-duration results move when "
            "the dependence assumption changes from joint to independent."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE" if sensitivity else "empty",
        methodology=(
            "The registered T3 artifact records joint and independent "
            "propagation results side by side. Only coverage counts and the "
            "range of an already-recorded percentage column are shown; no "
            "statistical test is derived."
        ),
        provenance="SCN (recorded propagation sensitivity).",
        uncertainty=(
            "Sensitivity to one assumption does not establish overall "
            "robustness of the downstream optimisation."
        ),
    )

    if not sensitivity:
        components.render_artifact_state(
            "RO2_SENSITIVITY",
            "MISSING",
            description=_ARTIFACT_TITLES["RO2_SENSITIVITY"],
            stage=RESEARCH_STAGE,
            provenance="SCN",
        )
        return

    summary = build_sensitivity_summary(sensitivity)
    quantile_text = (
        ", ".join(_fmt_pct(q, decimals=2) for q in summary["quantiles"])
        if summary["quantiles"]
        else formatting.MISSING_DISPLAY
    )
    range_text = (
        f"{_fmt_num(summary['pct_min'])}% to {_fmt_num(summary['pct_max'])}%"
        if summary["pct_min"] is not None and summary["pct_max"] is not None
        else formatting.MISSING_DISPLAY
    )
    components.render_paragraph(
        {
            "label": "Recorded coverage",
            "body": [
                f"Recorded rows: {_fmt_int(summary['rows'])}.",
                "Materials covered: "
                + (", ".join(summary["materials"]) if summary["materials"] else formatting.MISSING_DISPLAY)
                + ".",
                f"Quantile levels covered: {quantile_text}.",
                f"Recorded range of the independent-vs-joint percentage difference: {range_text}.",
                "",
                "The recorded differences quantify how sensitive the upstream duration",
                "conclusions are to modelling the material durations jointly versus",
                "independently. This is an assumption sensitivity of the upstream stage,",
                "not a robustness guarantee for the optimisation built on top of it.",
            ],
        }
    )
    components.render_table(
        pd.DataFrame(build_sensitivity_preview_rows(sensitivity)),
        title="Recorded sensitivity rows (preview)",
        caption=(
            "A short preview of the registered artifact, exactly as recorded. "
            "The full artifact contains the complete recorded row set."
        ),
        source="T3 RO2 joint-vs-independent sensitivity",
        research_stage=RESEARCH_STAGE,
    )
    components.render_html(
        components.build_note_bare(
            "Provenance: SCN. Values are recorded propagation results; the "
            "range above is the range of a recorded column, not a new "
            "statistic."
        )
    )


def _render_convergence_section(evidence: RO3Evidence, ro2: RO2Evidence) -> None:
    """Scenario-count and Monte-Carlo convergence, reported as recorded."""
    components.render_section_header(
        title="Convergence diagnostics",
        subtitle=(
            "How the scenario counts behind RO3 and the Monte-Carlo draw "
            "count behind RO2 were settled — as recorded."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE"
        if (evidence.convergence_summary or ro2.convergence_summary)
        else "empty",
        methodology=(
            "Both diagnostics are read from their registered artifacts. "
            "Nothing is re-derived; recorded pass/fail outcomes are reported "
            "including recorded failures."
        ),
        provenance="DER (recorded convergence evaluations).",
    )

    ro3_lines = build_ro3_convergence_lines(evidence.convergence_summary)
    ro2_lines = build_ro2_convergence_lines(ro2.convergence_summary)
    components.render_inline_label_values(
        [
            _labeled_paragraph("RO3 scenario-count convergence", ro3_lines),
            _labeled_paragraph("RO2 Monte-Carlo convergence", ro2_lines),
        ]
    )


def _render_integrity_section(evidence: RO3Evidence) -> None:
    """Final experimental integrity audit — what it verifies and what it does not."""
    audit = evidence.final_audit
    rows = build_integrity_rows(audit)
    components.render_section_header(
        title="Final experimental integrity audit",
        subtitle=(
            "The recorded end-of-experiment checks over the RO3 evidence chain."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE" if rows else "empty",
        methodology=(
            "Check outcomes are read from the registered audit artifact; "
            "recorded filesystem paths are suppressed."
        ),
        provenance="DER (validation audit over recorded experiment artifacts).",
    )

    if not rows:
        components.render_artifact_state(
            "RO3_FINAL_AUDIT",
            "MISSING",
            description=_ARTIFACT_TITLES["RO3_FINAL_AUDIT"],
            stage=RESEARCH_STAGE,
            provenance="DER",
        )
        return

    components.render_paragraph(
        {
            "label": "What the recorded audit says",
            "body": build_integrity_summary(audit),
        }
    )
    components.render_table(
        pd.DataFrame(rows),
        caption="Recorded audit checks, with filesystem paths suppressed.",
        source="RO3 step 39 final experimental integrity audit",
        research_stage=RESEARCH_STAGE,
    )


def _render_interpretation_section() -> None:
    """Interpretation rules and limitations, stated plainly."""
    components.render_section_header(
        title="How to read this evidence",
        subtitle=(
            "The difference between tested, descriptive and not-inferable "
            "claims — and the limitations that bind all of them."
        ),
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
    )

    components.render_paragraph(
        {
            "label": "Evidential tiers used on this page",
            "body": _bulleted(
                [
                    "Statistically tested — the T5 comparison and T6 ablation artifacts. "
                    "Reported with recorded bootstrap intervals, raw p-values and "
                    "Benjamini-Hochberg corrected significance.",
                    "Descriptive only — controller descriptives, stress paired changes, "
                    "holding-rate contrasts and holding-rate sensitivity. These artifacts "
                    "record differences without any significance test; they describe "
                    "direction and magnitude, nothing more.",
                    "Not inferable from the available evidence — real-world deployment "
                    "performance, supplier-specific lead-time behaviour, calibrated "
                    "shortage frequency, and any claim of universal controller "
                    "superiority. No registered artifact tests these.",
                ]
            ),
        }
    )

    components.render_paragraph(
        {
            "label": "Standing limitations",
            "body": _bulleted(
                [
                    "Non-significance is not equivalence. Where a recorded contrast did not "
                    "reach corrected significance, the evidence did not resolve a "
                    "difference at this sample size; it did not prove the arms identical.",
                    "Statistical significance is not practical importance. A corrected "
                    "significance flag says a difference was resolved; the effect "
                    "magnitudes in the tables say how large it was, in each metric's own "
                    "units. The two must be read together.",
                    "No universal superiority. The recorded evidence is a set of "
                    "cost-service trade-offs. No single controller is established as best "
                    "under every objective, and no composite score is computed anywhere on "
                    "this page.",
                    "Simulated, not observed. Every outcome on this page is realised under "
                    "the recorded evaluation protocol — including all stress and "
                    "holding-rate cases. None is an observed procurement operation.",
                    "Sample coverage. All comparisons hold for the recorded locked "
                    "forecast origins, common materials and evaluation horizon only. "
                    "Cross-window, cross-dataset and cross-horizon generalisation are not "
                    "established by these artifacts.",
                    "Scenario-count convergence. The registered convergence artifact "
                    "records that the primary transition did not clear its threshold and "
                    "that optimisation-level convergence was recorded as a later "
                    "requirement; see the convergence section for the recorded values.",
                    "Unavailable evidence. Any artifact shown as unavailable in the "
                    "inventory above supports no claim on this page, and nothing is "
                    "computed in its place.",
                ]
            ),
        }
    )


def _render_handoff() -> None:
    """Where this evidence is used in the rest of the dashboard."""
    components.render_section_header(
        title="Where this evidence is used",
        subtitle="How the ablation and robustness evidence relates to the rest of CMIDO.",
        research_stage=RESEARCH_STAGE,
        evidence_state="AVAILABLE",
    )
    components.render_paragraph(
        {
            "label": "Handoff",
            "body": [
                "This workspace is read-only evidence about a controlled experiment and its "
                "robustness surrounds. It does not feed the optimizer and does not recompute "
                "any research result.",
                "",
                "The RO3 · Optimization workspace presents the Pareto trade-off evidence and "
                "decision-level outcomes from the same research stage; the Procurement "
                "Decisions workspace interprets the recorded decision vectors; the Research "
                "Evidence page remains the home for the publication-grade evidence package. "
                "The planned Provenance & Integrity workspace will cover registry-level "
                "loading policies and cross-component provenance.",
            ],
        }
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
    """Render the Ablation & Robustness workspace.

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
    ro2 = snapshot.ro2
    provenance_rows = build_provenance_rows(evidence, ro2)

    if not provenance_rows:
        components.render_error_state(
            "No ablation or robustness evidence registered",
            description=(
                "The snapshot carries no provenance records for the ablation "
                "and robustness artifacts, so this workspace is empty. Nothing "
                "is computed or inferred in its place."
            ),
        )
        return

    status_index = artifact_status_index(provenance_rows)

    _render_overview(evidence, provenance_rows)
    _render_artifact_inventory(evidence, provenance_rows, status_index)
    _render_design_section(evidence)
    _render_comparison_section(evidence)
    _render_ablation_section(evidence)
    _render_descriptives_section(evidence)
    _render_stress_section(evidence)
    _render_robustness_section(evidence)
    _render_sensitivity_section(ro2)
    _render_convergence_section(evidence, ro2)
    _render_integrity_section(evidence)
    _render_interpretation_section()
    _render_handoff()


def inject_and_route(snapshot: DashboardSnapshot) -> None:
    """Inject the design system CSS and the page header for this workspace."""
    components.inject_css()

    page_info = page_by_id(PAGE_ID)
    header = build_page_header(
        title=_page_title(),
        subtitle=_page_subtitle(),
        research_stage=RESEARCH_STAGE,
        evidence_state=page_info.implementation.value,
    )
    components.render_html(header)


def _page_title() -> str:
    return "Ablation & Robustness"


def _page_subtitle() -> str:
    return (
        "Controlled 2×2 controller ablation, statistically tested comparisons, "
        "scenario-based stress and holding-rate robustness, convergence and "
        "integrity-gate evidence."
    )


def page_description() -> str:
    """Zero-argument public export consumed by page tests."""
    from src.construction.dashboard_ui.navigation import (
        page_description as _nav_page_description,
    )

    return _nav_page_description(PAGE_ID)


def page_future_phase() -> str:
    """Zero-argument public export consumed by page tests."""
    from src.construction.dashboard_ui.navigation import (
        page_future_phase as _nav_page_future_phase,
    )

    return str(_nav_page_future_phase(PAGE_ID) or "")


def page_by_id_local() -> dict[str, Any]:
    return page_by_id(PAGE_ID)


def page_is_planned_local() -> bool:
    return page_is_planned(PAGE_ID)
