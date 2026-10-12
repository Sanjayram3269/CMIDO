# ---------------------------------------------------------------------------
# Cached provenance + experiment-condition helpers (mirror of ro3.py)
# ---------------------------------------------------------------------------

from src.construction.dashboard_data.provenance import ProvenanceClass
from src.construction.dashboard_data.contract import ArtifactStatus
from src.construction.dashboard_ui import formatting

import pandas as pd


def _prov_get(entry, key, default=None):
    """Read provenance metadata from a dict or an ArtifactProvenance record."""
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _status_text(value):
    return str(getattr(value, "value", value) or "UNKNOWN")


def _frame(records):
    return pd.DataFrame(records) if records else pd.DataFrame()


def _labeled_paragraph(label, body):
    if isinstance(body, list):
        body = "\n".join(body)
    return {"label": label, "body": body}


def _fmt_num(value, decimals=2):
    try:
        return formatting.format_number(float(value), decimals=decimals)
    except (TypeError, ValueError):
        return formatting.MISSING_DISPLAY


def _fmt_pct(value, decimals=1):
    try:
        return formatting.format_percent(float(value), decimals=decimals)
    except (TypeError, ValueError):
        return formatting.MISSING_DISPLAY


def _fmt_int(value):
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return formatting.MISSING_DISPLAY


def _fmt_cell(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return formatting.MISSING_DISPLAY
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _is_true(value):
    return str(value).strip().lower() in ("true", "yes", "1")


def _clean_audit_detail(detail):
    """Hide filesystem paths from integrity-audit detail text.

    Some audit rows record the path of the file that was checked (e.g. a
    "file exists" check). Surfacing that path would leak raw repository layout
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
        ("/" in text and lowered.startswith("/"))
        or (":" in text and "\\" in text)
    )
    return "" if looks_like_path else text


def _first_origin(frame):
    """Earliest forecast origin present in the frame (honest preview choice)."""
    if frame.empty or "forecast_origin" not in frame.columns:
        return None
    origins = sorted(frame["forecast_origin"].dropna().unique().tolist(), key=str)
    return origins[0] if origins else None


def _material_unit_map():
    """Material -> its native unit (USD for cost models; unit tonnes for qty models).

    This is a research-context mapping derived from the data model, not from the
    optimizer. It is used only to label quantities; it is never used to infer a
    supplier, a cost, or a decision value.
    """
    return {
        "Cement": "tonne",
        "Granite": "tonne",
        "Ready Mixed Concrete": "m3",
        "Steel Reinforcement Bars": "tonne",
    }


def _unit_label(material):
    return _material_unit_map().get(material, "unit")


def _origin_section_label(section_name):
    """Human label for an RO3 ablation / experiment section used in provenance."""
    return section_name


def _decision_sensitivity_label_map():
    """Human-readable labels for the decision-sensitivity summary columns."""
    return {
        "N_A": "scenarios in first sample (N_A)",
        "N_B": "scenarios in second sample (N_B)",
        "matched_solutions": "matched solutions between the two samples",
        "mean_objective_distance": "mean objective distance between matched solutions",
        "max_objective_distance": "max objective distance between matched solutions",
        "mean_abs_quantity_difference": "mean absolute quantity difference (units)",
        "mean_total_procurement_normalized_difference": "mean total procurement normalized difference",
        "max_total_procurement_normalized_difference": "max total procurement normalized difference",
        "mean_zero_safe_quantity_relative_difference": "mean zero-safe-quantity relative difference",
    }


def _decision_sensitivity_note() -> str:
    """Short caveat for the decision-sensitivity panel."""
    return (
        "These comparisons are between modeled epsilon-constraint solution sets under different "
        "scenario sample sizes. They are not observed procurement outcomes and not a substitute "
        "for supplier, storage or disruption evidence."
    )


def _experiment_conditions_from_provenance(provenance_rows):
    """Return the conservative experiment conditions string for the procurement page.

    The procurement-decisions page reports the selected-decisions and realized-evaluation
    artifacts that come from a single RO3 experiment: the O2 single-origin ablation (
    forecast_origin = 2022-07-01, N = 2500 scenarios). This function derives that summary
    from the provenance records alone and never hard-codes a decision value.
    """
    if not provenance_rows:
        return "See provenance for experiment conditions."

    origins = sorted(
        {
            _prov_get(r, "forecast_origin", "")
            for r in provenance_rows
            if _prov_get(r, "forecast_origin", "")
        },
        key=str,
    )
    scenario_counts = sorted(
        {
            _prov_get(r, "scenario_count", "")
            for r in provenance_rows
            if _prov_get(r, "scenario_count", "")
        },
        key=str,
    )
    # Forecast origin / scenario count can be recorded directly by the
    # provenance registry. If an entry carries them, use the recorded values.
    for r in provenance_rows:
        entry = _prov_get(r, "provenance_class", r)
        fo = _prov_get(r, "forecast_origin", None)
        sc = _prov_get(r, "scenario_count", None)
        if fo:
            origins.append(str(fo))
        if sc:
            scenario_counts.append(str(sc))
    # Fall back to deriving scenario count from the multi-origin summary filename
    # (N2500) when no provenance record records it. The forecast origin itself is
    # deliberately not inferred from filenames: the only explicit source of
    # experimental conditions in this repository is the provenance record, and a
    # missing value is reported as "see provenance" rather than invented.
    for r in provenance_rows:
        source_path = str(_prov_get(r, "source_path", ""))
        if not any(c in scenario_counts for c in ["2500", "5000"]):
            import re as _re
            m = _re.search(r"N(\d+)", source_path)
            if m:
                scenario_counts.append(m.group(1))
    parts = ["Forecast origin(s): " + ", ".join(origins)] if origins else ["Forecast origin(s): see provenance"]
    if scenario_counts:
        parts.append("Scenario counts: " + ", ".join(scenario_counts))
    else:
        parts.append("Scenario counts: see provenance")
    return ". ".join(parts) + "."


def _bulleted(lines):
    return [f"- {line}" for line in lines]


def _numbered_list(lines):
    return [f"{i}. {line}" for i, line in enumerate(lines, start=1)]


#: (label, unit, direction) for the realized-evaluation metrics. Mirrors the
#: RO3 page's metric vocabulary so both pages label the same artifact columns
#: identically.
_METRIC_META = {
    "realized_procurement_holding_cost": ("Realised procurement + holding cost", "cost units", "min"),
    "realized_total_shortage": ("Realised total shortage quantity", "units", "min"),
    "realized_shortage_cvar95_monthly": ("Realised monthly CVaR_0.95 shortage", "units", "min"),
    "realized_total_procurement_quantity": ("Realised total procurement quantity", "units", "reported"),
    "realized_mean_ending_inventory": ("Realised mean ending inventory", "units", "reported"),
    "realized_procurement_events": ("Realised procurement events", "count", "reported"),
    "realized_service_level": ("Realised service level", "fraction", "reported (higher=better)"),
}


def _metric_label(metric):
    return _METRIC_META.get(metric, (metric.replace("_", " ").capitalize(), "", "reported"))[0]


def _metric_unit(metric):
    return _METRIC_META.get(metric, (_metric_label(metric), "", "reported"))[1]


def _metric_direction(metric):
    return _METRIC_META.get(metric, (_metric_label(metric), "", "reported"))[2]
