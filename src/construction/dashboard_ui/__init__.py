"""CMIDO 10A.3 - Premium research-grade dashboard design system.

Layering (10A.3 scope)::

    research engines
        -> validated result artifacts            (10A.2-B, dashboard_data)
            -> dashboard_ui                       (this package)
                -> Streamlit pages                 (apps/cmido_dashboard.py)

Contract for this layer:

* **No research logic.** Components render values that are already computed.
* **No artifact access.** Nothing here reads a CSV or a results directory.
* **No inference.** A component never guesses provenance, evidence quality or a
  scientific conclusion; the caller supplies it.
* **No heavy work.** Builders are pure string/``dict`` factories, so rendering
  stays cheap on every Streamlit rerun.

Module map:

============== ==========================================================
``theme``      Centralised colour / typography / spacing tokens + CSS.
``states``     Evidence and uncertainty vocabularies with safe labels.
``formatting`` Pure number, percent, interval and axis formatting.
``badges``     Provenance, research-stage, status and uncertainty chips.
``cards``      KPI, chart card, table card, methodology, publication status.
``sections``   Branding, page/section headers, banners, artifact states.
``charts``     Shared Plotly layout, palettes and figure helpers.
``tables``     Shared table configuration and dataframe presentation.
``components`` Thin Streamlit adapters (``render_*``).
============== ==========================================================
"""

from __future__ import annotations

from .badges import (
    build_badge,
    build_badge_row,
    build_evidence_state_badge,
    build_entity_chip,
    build_provenance_badge,
    build_provenance_chip,
    build_research_stage_badge,
    build_status_badge,
    build_uncertainty_badge,
)
from .cards import (
    build_chart_card,
    build_kpi_grid,
    build_legacy_kpi,
    build_methodology_card,
    build_publication_status,
    build_table_card,
)
from .cards import build_kpi as build_kpi_card
from .charts import (
    CONTINUOUS_SCALES,
    DEFAULT_CHART_CONFIG,
    DISTRIBUTION_STYLES,
    PLOTLY_THEME,
    apply_chart_theme,
    axis_reference,
    get_categorical_colors,
    get_chart_config,
    get_chart_colors,
    get_plotly_theme,
    get_role_color,
)
from .formatting import (
    MISSING_DISPLAY,
    format_axis_title,
    format_currency,
    format_days,
    format_duration,
    format_feasibility,
    format_integer,
    format_interval,
    format_kpi_value,
    format_number,
    format_percent,
    format_percent_points,
    format_shortage_pct,
    format_signed,
    format_value_with_unit,
    format_yes_no,
    is_missing,
)
from .sections import (
    build_app_header,
    build_artifact_state,
    build_breadcrumb,
    build_empty_state,
    build_error_state,
    build_flow_diagram,
    build_footer,
    build_loading_state,
    build_page_header,
    build_section_header,
    build_sidebar_group,
    build_status_banner,
)
from .states import (
    EVIDENCE_STATE_LABELS,
    STOCHASTIC_UNCERTAINTY_STATES,
    UNCERTAINTY_STATE_LABELS,
    EvidenceState,
    UncertaintyState,
    evidence_state_label,
    evidence_state_style,
    is_stochastic,
    uncertainty_state_description,
    uncertainty_state_label,
    uncertainty_state_style,
)
from .tables import (
    TABLE_CONFIG,
    build_column_config,
    column_alignment,
    numeric_columns,
    prepare_table,
    present_frame,
    summarize_columns,
)
from .theme import (
    ACCENT,
    APP_NAME,
    APP_TAGLINE,
    BORDER,
    CATEGORICAL_PALETTE,
    CHART_ROLES,
    CORNERS,
    DANGER,
    INFO,
    LAYOUT_COLUMNS,
    MUTED_TEXT,
    PAGE_BG,
    POSITIVE,
    PRIMARY_TEXT,
    PROVENANCE_COLORS,
    PROVENANCE_LABELS,
    RESEARCH_STAGE_COLORS,
    RESEARCH_STAGE_LABELS,
    RESEARCH_STAGE_TITLES,
    SECONDARY_TEXT,
    SPACING,
    STATUS_PALETTE,
    STATUS_TITLES,
    SURFACE,
    TYPOGRAPHY,
    WARNING,
    build_css,
    resolve_provenance,
    resolve_research_stage,
    resolve_status_key,
    status_colors,
    status_title,
)

__all__ = [
    # tokens
    "ACCENT",
    "APP_NAME",
    "APP_TAGLINE",
    "BORDER",
    "CATEGORICAL_PALETTE",
    "CHART_ROLES",
    "CORNERS",
    "DANGER",
    "INFO",
    "LAYOUT_COLUMNS",
    "MUTED_TEXT",
    "PAGE_BG",
    "POSITIVE",
    "PRIMARY_TEXT",
    "PROVENANCE_COLORS",
    "PROVENANCE_LABELS",
    "RESEARCH_STAGE_COLORS",
    "RESEARCH_STAGE_LABELS",
    "RESEARCH_STAGE_TITLES",
    "SECONDARY_TEXT",
    "SPACING",
    "STATUS_PALETTE",
    "STATUS_TITLES",
    "SURFACE",
    "TYPOGRAPHY",
    "WARNING",
    "build_css",
    "resolve_provenance",
    "resolve_research_stage",
    "resolve_status_key",
    "status_colors",
    "status_title",
    # states
    "EVIDENCE_STATE_LABELS",
    "EvidenceState",
    "STOCHASTIC_UNCERTAINTY_STATES",
    "UNCERTAINTY_STATE_LABELS",
    "UncertaintyState",
    "evidence_state_label",
    "evidence_state_style",
    "is_stochastic",
    "uncertainty_state_description",
    "uncertainty_state_label",
    "uncertainty_state_style",
    # formatting
    "MISSING_DISPLAY",
    "format_axis_title",
    "format_currency",
    "format_days",
    "format_duration",
    "format_feasibility",
    "format_integer",
    "format_interval",
    "format_kpi_value",
    "format_number",
    "format_percent",
    "format_percent_points",
    "format_shortage_pct",
    "format_signed",
    "format_value_with_unit",
    "format_yes_no",
    "is_missing",
    # badges
    "build_badge",
    "build_badge_row",
    "build_entity_chip",
    "build_evidence_state_badge",
    "build_provenance_badge",
    "build_provenance_chip",
    "build_research_stage_badge",
    "build_status_badge",
    "build_uncertainty_badge",
    # cards
    "build_chart_card",
    "build_kpi_card",
    "build_kpi_grid",
    "build_legacy_kpi",
    "build_methodology_card",
    "build_publication_status",
    "build_table_card",
    # sections
    "build_app_header",
    "build_artifact_state",
    "build_breadcrumb",
    "build_empty_state",
    "build_error_state",
    "build_flow_diagram",
    "build_footer",
    "build_loading_state",
    "build_page_header",
    "build_section_header",
    "build_sidebar_group",
    "build_status_banner",
    # charts
    "CONTINUOUS_SCALES",
    "DEFAULT_CHART_CONFIG",
    "DISTRIBUTION_STYLES",
    "PLOTLY_THEME",
    "apply_chart_theme",
    "axis_reference",
    "get_categorical_colors",
    "get_chart_config",
    "get_chart_colors",
    "get_plotly_theme",
    "get_role_color",
    # tables
    "TABLE_CONFIG",
    "build_column_config",
    "column_alignment",
    "numeric_columns",
    "prepare_table",
    "present_frame",
    "summarize_columns",
]
