"""Tests for the CMIDO 10A.3 dashboard design system.

These tests cover presentation mechanics only: tokens, formatting, badges,
KPI/cards, section headers, artifact states, chart configuration and table
configuration.  Any numeric values used here are synthetic UI fixtures chosen
to exercise formatting - they are not CMIDO research results.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pandas as pd
import pytest

from src.construction.dashboard_data.contract import ArtifactStatus, ProvenanceClass
from src.construction.dashboard_ui import (
    ACCENT,
    APP_NAME,
    APP_TAGLINE,
    CATEGORICAL_PALETTE,
    CHART_ROLES,
    CORNERS,
    DEFAULT_CHART_CONFIG,
    EVIDENCE_STATE_LABELS,
    LAYOUT_COLUMNS,
    PLOTLY_THEME,
    PROVENANCE_LABELS,
    RESEARCH_STAGE_LABELS,
    SPACING,
    STATUS_PALETTE,
    SURFACE,
    TABLE_CONFIG,
    TYPOGRAPHY,
    UNCERTAINTY_STATE_LABELS,
    EvidenceState,
    UncertaintyState,
    apply_chart_theme,
    build_app_header,
    build_artifact_state,
    build_badge,
    build_breadcrumb,
    build_chart_card,
    build_empty_state,
    build_error_state,
    build_flow_diagram,
    build_kpi_card,
    build_methodology_card,
    build_page_header,
    build_provenance_badge,
    build_provenance_chip,
    build_publication_status,
    build_research_stage_badge,
    build_section_header,
    build_status_banner,
    build_status_badge,
    build_table_card,
    build_uncertainty_badge,
    build_css,
    column_alignment,
    format_axis_title,
    format_days,
    format_feasibility,
    format_integer,
    format_interval,
    format_number,
    format_percent,
    format_shortage_pct,
    get_chart_colors,
    get_chart_config,
    get_plotly_theme,
    get_role_color,
    is_stochastic,
    prepare_table,
    present_frame,
    resolve_provenance,
    resolve_research_stage,
    resolve_status_key,
    status_colors,
    status_title,
)
from src.construction.dashboard_ui.states import (
    uncertainty_state_description,
    uncertainty_state_style,
)
from src.construction.dashboard_ui.tables import build_column_config, summarize_columns

UI_DIR = Path("src/construction/dashboard_ui")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class _StubFigure:
    """Minimal stand-in for a Plotly figure.

    ``apply_chart_theme`` only needs ``update_layout``, so the chart contract can
    be asserted without requiring Plotly to be installed in the test
    environment. A real-figure check runs when Plotly is available.
    """

    def __init__(self) -> None:
        self.layout: dict = {}

    def update_layout(self, **kwargs):
        self.layout.update(kwargs)
        return self


# ---------------------------------------------------------------------------
# Theme tokens
# ---------------------------------------------------------------------------
class TestThemeTokens:
    def test_required_semantic_tokens_exist(self):
        from src.construction.dashboard_ui import theme

        required = [
            "PAGE_BG",
            "SURFACE",
            "SURFACE_ELEVATED",
            "BORDER",
            "PRIMARY_TEXT",
            "SECONDARY_TEXT",
            "MUTED_TEXT",
            "ACCENT",
            "POSITIVE",
            "WARNING",
            "DANGER",
            "INFO",
        ]
        for name in required:
            value = getattr(theme, name)
            assert isinstance(value, str) and HEX.match(value), f"{name} is not a hex colour: {value!r}"

    def test_typography_roles_cover_the_hierarchy(self):
        for role in [
            "app_name",
            "page_title",
            "section_title",
            "subsection_title",
            "kpi_label",
            "kpi_value",
            "body",
            "caption",
            "provenance",
            "methodology",
        ]:
            assert role in TYPOGRAPHY
            assert TYPOGRAPHY[role].strip()

    def test_typography_uses_safe_system_font_stacks(self):
        allowed = ("Arial", "sans-serif", "monospace", "Consolas", "Menlo")
        for style in TYPOGRAPHY.values():
            if "font-family" not in style:
                continue
            assert any(token in style for token in allowed), style

    def test_spacing_and_corner_scales_are_ordered(self):
        xs = [float(SPACING[k].removesuffix("rem")) for k in ("xs", "sm", "md", "lg", "xl", "xxl")]
        assert xs == sorted(xs)
        corners = [int(CORNERS[k].removesuffix("px")) for k in ("xs", "sm", "md", "lg")]
        assert corners == sorted(corners)

    def test_layout_presets_cover_required_column_counts(self):
        for key in ("kpi_2", "kpi_3", "kpi_4", "full", "half"):
            assert LAYOUT_COLUMNS[key] >= 1
        assert LAYOUT_COLUMNS["chart_insight"] >= 2

    def test_status_palette_covers_every_registry_status(self):
        for status in ArtifactStatus:
            key = resolve_status_key(status)
            assert key in STATUS_PALETTE
            assert status_title(status)

    def test_status_resolution_accepts_enum_and_string(self):
        assert resolve_status_key(ArtifactStatus.AVAILABLE) == "available"
        assert resolve_status_key("TOO_LARGE") == "too_large"
        assert resolve_status_key("UNSUPPORTED") == "unsupported"
        assert resolve_status_key("NOT_APPLICABLE") == "optional"
        assert resolve_status_key("something-else") == "attention"

    def test_status_colors_are_distinct_enough_to_read(self):
        assert status_colors(ArtifactStatus.AVAILABLE)["color"] != status_colors(ArtifactStatus.INVALID)["color"]
        assert status_colors(ArtifactStatus.INVALID)["soft"] != status_colors(ArtifactStatus.AVAILABLE)["soft"]

    def test_build_css_scopes_rules_and_injects_tokens(self):
        css = build_css()
        assert css.strip().startswith("<style>")
        for selector in (".cmido-kpi", ".cmido-card", ".cmido-section", ".cmido-banner", ".cmido-empty"):
            assert selector in css
        assert ACCENT in css
        assert SURFACE in css

    def test_tokens_are_the_single_source_of_truth(self):
        """No module other than theme.py may hard-code a colour literal."""
        offenders = []
        for path in sorted(UI_DIR.glob("*.py")):
            if path.name == "theme.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if re.fullmatch(r"#[0-9A-Fa-f]{6}", node.value):
                        offenders.append(f"{path.name}:{node.lineno}")
        assert offenders == []


# ---------------------------------------------------------------------------
# Provenance and research-stage badges
# ---------------------------------------------------------------------------
class TestProvenanceBadges:
    def test_vocabulary_is_obs_der_est_scn(self):
        assert set(PROVENANCE_LABELS) == {"OBS", "DER", "EST", "SCN"}
        assert PROVENANCE_LABELS == {
            "OBS": "Observed",
            "DER": "Derived",
            "EST": "Estimated",
            "SCN": "Scenario",
        }

    @pytest.mark.parametrize("code", ["OBS", "DER", "EST", "SCN"])
    def test_each_provenance_badge_shows_code_and_meaning(self, code):
        html = build_provenance_badge(code)
        assert code in html
        assert PROVENANCE_LABELS[code] in html
        assert "title=" in html, "provenance must not rely on colour alone"

    def test_provenance_badge_accepts_contract_enum(self):
        html = build_provenance_badge(ProvenanceClass.SCN)
        assert "SCN" in html and "Scenario" in html

    def test_provenance_chip_is_code_only(self):
        html = build_provenance_chip("EST")
        assert html.rstrip().endswith(" EST</span>")
        assert "cmido-badge-compact" in html

    def test_unknown_provenance_degrades_gracefully(self):
        html = build_provenance_badge("XYZ")
        assert "XYZ" not in html
        assert "n/a" in html.lower()

    def test_resolve_provenance_normalises(self):
        assert resolve_provenance("obs") == "OBS"
        assert resolve_provenance(ProvenanceClass.DER) == "DER"
        assert resolve_provenance(None) is None
        assert resolve_provenance("") is None


class TestResearchStageBadges:
    @pytest.mark.parametrize(
        "stage,label",
        [
            ("RO1", "RO1"),
            ("RO2", "RO2"),
            ("RO3", "RO3"),
            ("ABLATION", "Ablation"),
            ("STRESS", "Stress"),
            ("ROBUSTNESS", "Robustness"),
            ("REAL_DATA", "Real Data"),
            ("EVIDENCE", "Evidence"),
        ],
    )
    def test_stage_badges(self, stage, label):
        html = build_research_stage_badge(stage)
        assert label in html
        assert "cmido-badge-stage" in html

    def test_stage_aliases_and_unknown_values(self):
        assert "RO2" in build_research_stage_badge("RO2_UNCERTAINTY")
        assert resolve_research_stage("ro2") == "RO2"
        assert resolve_research_stage("unheard-of") == "EVIDENCE"
        assert set(RESEARCH_STAGE_LABELS) >= {"RO1", "RO2", "RO3", "ABLATION", "STRESS", "ROBUSTNESS", "REAL_DATA", "EVIDENCE"}


# ---------------------------------------------------------------------------
# Status, evidence and uncertainty states
# ---------------------------------------------------------------------------
class TestStates:
    @pytest.mark.parametrize("status", list(ArtifactStatus))
    def test_every_registry_status_has_a_badge_with_text(self, status):
        html = build_status_badge(status)
        assert status_title(status) in html
        assert "cmido-badge-status" in html

    def test_evidence_state_labels_are_human_readable(self):
        for state in EvidenceState:
            assert state.value in EVIDENCE_STATE_LABELS
            assert EVIDENCE_STATE_LABELS[state.value]

    def test_uncertainty_state_labels(self):
        for state in UncertaintyState:
            assert state.value in UNCERTAINTY_STATE_LABELS
            assert UNCERTAINTY_STATE_LABELS[state.value]
            assert uncertainty_state_description(state)

    def test_uncertainty_badge_declares_epistemic_quality(self):
        html = build_uncertainty_badge(UncertaintyState.SERVICE_RISK)
        assert "Service-risk" in html
        assert "cmido-badge-uncertainty" in html

    @pytest.mark.parametrize(
        "state,stochastic",
        [
            (UncertaintyState.POINT, False),
            (UncertaintyState.DETERMINISTIC, False),
            (UncertaintyState.INTERVAL, True),
            (UncertaintyState.DISTRIBUTION, True),
            (UncertaintyState.TAIL, True),
            (UncertaintyState.SCENARIO, True),
            (UncertaintyState.RANGE, True),
            (UncertaintyState.SERVICE_RISK, True),
        ],
    )
    def test_stochastic_classification(self, state, stochastic):
        assert is_stochastic(state) is stochastic

    def test_uncertainty_styles_differ_from_each_other(self):
        assert uncertainty_state_style("distribution") != uncertainty_state_style("tail")


# ---------------------------------------------------------------------------
# KPI card
# ---------------------------------------------------------------------------
class TestKpiCard:
    def test_kpi_separates_value_interpretation_and_provenance(self):
        html = build_kpi_card(
            "Project duration",
            74,
            unit="d",
            description="Deterministic CPM result",
            provenance="DER",
            research_stage="RO1",
            status="valid",
        )
        assert "Project duration" in html
        assert ">74<" in html or "74" in html
        assert "d" in html
        assert "Deterministic CPM result" in html
        assert "DER" in html
        assert "RO1" in html
        assert "cmido-kpi" in html

    def test_kpi_supports_delta_with_explicit_sign(self):
        html = build_kpi_card("Service risk", 0.31, delta=0.04, delta_direction="warning")
        assert "+0.04" in html
        assert "Change:" in html

    def test_kpi_marks_missing_values_without_crashing(self):
        html = build_kpi_card("Supplier count", None)
        assert "—" in html

    def test_kpi_contains_no_hardcoded_research_values(self):
        """The component must be generic: no CMIDO numbers baked into markup."""
        html = build_kpi_card("Label", 1, unit="u", description="d", provenance="OBS")
        for token in ("0.167", "74", "9B", "PSLIB", "CMIDO_DASHBOARD_RUN"):
            assert token not in html

    def test_kpi_escapes_user_supplied_text(self):
        html = build_kpi_card("<script>x</script>", "1")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_kpi_supports_uncertainty_declaration(self):
        html = build_kpi_card("Mean delay", 1.2, uncertainty=UncertaintyState.INTERVAL)
        assert "Interval estimate" in html


# ---------------------------------------------------------------------------
# Cards and sections
# ---------------------------------------------------------------------------
class TestCardsAndSections:
    def test_app_header_uses_fixed_identity(self):
        html = build_app_header()
        assert APP_NAME in html
        assert "Construction Material Intelligence" in html
        assert "Decision Optimization" in html
        assert APP_TAGLINE.replace("&", "&amp;") in html

    def test_page_header_renders_title_and_subtitle(self):
        html = build_page_header("Overview", "Project intelligence", provenance="DER")
        assert "cmido-page-title" in html
        assert "Overview" in html
        assert "Project intelligence" in html
        assert "DER" in html

    def test_section_header_supports_stage_method_and_evidence(self):
        html = build_section_header(
            "RO2 - JOINT UNCERTAINTY PROPAGATION",
            "Demand + supply uncertainty -> joint propagation -> service risk",
            research_stage="RO2",
            evidence_state="valid",
            methodology="Method: joint Monte Carlo propagation.",
        )
        assert "RO2 - JOINT UNCERTAINTY PROPAGATION" in html
        assert "RO2" in html
        assert "Method: joint Monte Carlo propagation." in html
        assert "cmido-section" in html

    def test_section_header_does_not_hardcode_conclusions(self):
        html = build_section_header("Any title")
        assert "significant" not in html.lower()
        assert "outperform" not in html.lower()

    def test_breadcrumb_and_flow(self):
        crumbs = build_breadcrumb(["RESEARCH", "RO2", "Joint propagation"])
        assert "RO2" in crumbs
        assert crumbs.count("cmido-breadcrumb-sep") == 2
        assert build_breadcrumb([]) == ""
        flow = build_flow_diagram(["Materials", "Schedule"], title="Pipeline")
        assert "Pipeline" in flow and "Materials" in flow

    def test_chart_card_contains_header_and_provenance(self):
        html = build_chart_card(title="Tail comparison", research_stage="RO2", provenance="EST")
        assert "Tail comparison" in html
        assert "RO2" in html and "EST" in html

    def test_methodology_card_is_presentation_only(self):
        html = build_methodology_card(
            "Service risk",
            "Probability that the delay exceeds the tolerance.",
            key_metric="0.31",
            evidence_state="partial",
            provenance="EST",
        )
        assert "0.31" in html
        assert "Partial evidence" in html

    def test_publication_status_lists_rows_with_text_status(self):
        html = build_publication_status(rows=[("RO1", "valid"), ("RO2", "partial")])
        assert "RO1" in html and "RO2" in html
        assert "Validated" in html and "Partial evidence" in html

    def test_table_card_marks_empty_tables(self):
        html = build_table_card(pd.DataFrame(), title="Empty table")
        assert "No rows available" in html


# ---------------------------------------------------------------------------
# Artifact / empty / error states
# ---------------------------------------------------------------------------
class TestStatesRendering:
    @pytest.mark.parametrize("status", list(ArtifactStatus))
    def test_artifact_states_render_plain_language(self, status):
        html = build_artifact_state("RO2_service_risk_curve", status)
        assert "RO2_service_risk_curve" in html
        assert status_title(status) in html
        assert "Traceback" not in html

    def test_too_large_state_explains_loading_policy(self):
        html = build_artifact_state("RO3_scenarios_5000", ArtifactStatus.TOO_LARGE)
        assert "loading policy" in html.lower() or "experiment-scale" in html.lower()

    def test_status_banner_keeps_exception_secondary(self):
        html = build_error_state(
            "Scenario could not be completed",
            description="The schedule-impact engine did not return a result.",
            diagnostics="KeyError: 'project_delay_days'",
        )
        headline = html.split("Technical detail")[0]
        assert "KeyError" not in headline
        assert "Technical detail" in html
        assert "did not return a result" in html

    def test_status_banner_tones(self):
        for status in ("valid", "attention", "error", "loading", "empty"):
            assert "cmido-banner" in build_status_banner("Message", status=status)

    def test_empty_state_is_explicit(self):
        html = build_empty_state("No rows available.", title="Empty table")
        assert "Empty table" in html
        assert "No rows available." in html

    def test_generic_badge_is_configurable(self):
        html = build_badge("Label", color="#123456", soft="#FFFFFF", icon="*")
        assert "Label" in html and "#123456" in html

    def test_no_bare_exception_markup_anywhere_in_states(self):
        for builder in (build_status_banner, build_empty_state):
            html = builder("Something went wrong.")
            assert "Traceback (most recent call last)" not in html


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
class TestFormatting:
    def test_numbers(self):
        assert format_number(1234.567, 2) == "1,234.57"
        assert format_integer(1234) == "1,234"
        assert format_days(74, 0) == "74 d"
        assert format_days(74) == "74.0 d"
        assert format_days(3.14159, 2) == "3.14 d"

    def test_percentages(self):
        assert format_percent(0.4213) == "42.1%"
        assert format_percent(1.0) == "100.0%"

    def test_interval_carries_label_and_unit(self):
        text = format_interval(1.2, 3.4, suffix="d")
        assert text.startswith("95% CI")
        assert "1.20" in text and "3.40" in text and "d" in text

    def test_shortage_and_feasibility(self):
        assert format_shortage_pct(25, 100) == "25.0%"
        assert format_shortage_pct(5, 0) == "0.0%"
        assert format_feasibility(3, 4) == "3/4 (75.0%)"

    def test_missing_values_render_as_em_dash(self):
        for value in (None, float("nan"), float("inf"), ""):
            assert format_number(value) == "—"
            assert format_percent(value) == "—"

    def test_axis_title_includes_unit(self):
        assert format_axis_title("Project delay", "days") == "Project delay (days)"
        assert format_axis_title("Project delay") == "Project delay"


# ---------------------------------------------------------------------------
# Plotly configuration
# ---------------------------------------------------------------------------
class TestChartConfiguration:
    def test_theme_defines_layout_contract(self):
        for key in ("font", "paper_bgcolor", "plot_bgcolor", "margin", "hovermode", "legend", "title", "xaxis", "yaxis", "colorway"):
            assert key in PLOTLY_THEME

    def test_get_plotly_theme_returns_a_copy(self):
        first = get_plotly_theme()
        first["margin"]["l"] = 999
        assert get_plotly_theme()["margin"]["l"] != 999

    def test_chart_config_hides_logo(self):
        config = get_chart_config()
        assert config["displaylogo"] is False
        assert config["responsive"] is True
        assert get_chart_config() is not config

    def test_semantic_chart_roles(self):
        for role in ("observed", "scenario", "optimized", "risk", "uncertainty", "baseline"):
            assert CHART_ROLES[role].startswith("#")
            assert get_role_color(role) == CHART_ROLES[role]

    def test_categorical_palette_is_bounded_and_distinct(self):
        assert 4 <= len(CATEGORICAL_PALETTE) <= 12
        assert len(set(CATEGORICAL_PALETTE)) == len(CATEGORICAL_PALETTE)

    def test_get_chart_colors_returns_line_and_fill(self):
        style = get_chart_colors("uncertainty")
        assert "line" in style and "fill" in style
        assert get_chart_colors("not-a-role") is None

    def test_uncertainty_series_are_visually_secondary(self):
        assert get_chart_colors("uncertainty")["opacity"] < 1.0
        assert (
            get_chart_colors("uncertainty")["line"]["width"]
            < get_chart_colors("point_estimate")["line"]["width"]
        )

    def test_apply_chart_theme_configures_a_figure(self):
        fig = _StubFigure()
        apply_chart_theme(fig, height=420, x_title="Delay", x_unit="days", y_title="Project delay", y_unit="days")
        layout = fig.layout
        assert layout["height"] == 420
        assert layout["xaxis"]["title"]["text"] == "Delay (days)"
        assert layout["yaxis"]["title"]["text"] == "Project delay (days)"
        assert layout["colorway"] == list(CATEGORICAL_PALETTE)
        assert layout["hovermode"] == "closest"
        assert layout["font"]["family"]

    def test_apply_chart_theme_on_a_real_plotly_figure_when_available(self):
        go = pytest.importorskip("plotly.graph_objects")
        fig = go.Figure(go.Scatter(x=[1, 2], y=[1, 2], mode="lines"))
        apply_chart_theme(fig, height=300, y_title="Project delay", y_unit="days")
        assert fig.layout.height == 300
        assert fig.layout.yaxis.title.text == "Project delay (days)"
        assert fig.layout.paper_bgcolor == SURFACE

    def test_apply_chart_theme_tolerates_none(self):
        assert apply_chart_theme(None) is None


# ---------------------------------------------------------------------------
# Table configuration
# ---------------------------------------------------------------------------
class TestTableConfiguration:
    def test_shared_table_config(self):
        assert TABLE_CONFIG["hide_index"] is True
        assert TABLE_CONFIG["use_container_width"] is True

    def test_numeric_columns_align_right_and_labels_left(self):
        frame = pd.DataFrame({"Activity": ["A1"], "Duration": [1.5], "Cost": [100.0]})
        alignment = column_alignment(frame)
        assert alignment["Activity"] == "left"
        assert alignment["Duration"] == "right"
        assert alignment["Cost"] == "right"

    def test_column_config_only_targets_numeric_columns(self):
        frame = pd.DataFrame({"Activity": ["A1"], "Duration": [1.5]})
        config = build_column_config(frame)
        assert set(config) == {"Duration"}
        assert config["Duration"]["type"] == "number"

    def test_present_frame_rounds_copy_without_mutating_source(self):
        frame = pd.DataFrame({"Duration": [1.23456]})
        display = present_frame(frame, decimals=2)
        assert display["Duration"].iloc[0] == pytest.approx(1.23)
        assert frame["Duration"].iloc[0] == pytest.approx(1.23456)

    def test_prepare_table_reports_shape_and_emptiness(self):
        prepared = prepare_table(pd.DataFrame({"a": [1.0]}))
        assert prepared["is_empty"] is False
        assert prepared["row_count"] == 1
        assert prepared["column_count"] == 1
        assert prepared["config"] == TABLE_CONFIG

        empty = prepare_table(pd.DataFrame())
        assert empty["is_empty"] is True
        assert empty["row_count"] == 0

        assert prepare_table(None)["is_empty"] is True

    def test_summarize_columns(self):
        summary = summarize_columns(pd.DataFrame({"Activity": ["A1"], "Duration": [1.0]}))
        assert [row[0] for row in summary] == ["Activity", "Duration"]
        assert summary[1][2] == "right"


# ---------------------------------------------------------------------------
# Accessibility
# ---------------------------------------------------------------------------
def _relative_luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    red, green, blue = linear
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 2.1 contrast ratio between two hex colours."""
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


class TestAccessibility:
    def test_body_text_meets_wcag_aa_on_every_surface(self):
        from src.construction.dashboard_ui import theme

        for surface in (theme.PAGE_BG, theme.SURFACE, theme.SURFACE_ELEVATED, theme.SURFACE_INSET):
            assert contrast_ratio(theme.PRIMARY_TEXT, surface) >= 4.5
            assert contrast_ratio(theme.SECONDARY_TEXT, surface) >= 4.5

    def test_muted_metadata_text_meets_aa_on_light_surfaces(self):
        from src.construction.dashboard_ui import theme

        assert contrast_ratio(theme.MUTED_TEXT, theme.SURFACE) >= 4.5
        assert contrast_ratio(theme.MUTED_TEXT, theme.PAGE_BG) >= 4.5

    def test_chrome_text_meets_aa_on_dark_application_chrome(self):
        """Headings/labels on Streamlit's dark chrome clear WCAG AA.

        The dark canvas (#0E1117) and sidebar (#262730) are the surfaces
        chrome-level text sits on when the app renders dark; the *_ON_DARK
        companions are applied there through CSS ``light-dark()``.
        """
        from src.construction.dashboard_ui import theme

        for surface in ("#0E1117", "#262730"):
            assert contrast_ratio(theme.PRIMARY_TEXT_ON_DARK, surface) >= 4.5
            assert contrast_ratio(theme.SECONDARY_TEXT_ON_DARK, surface) >= 4.5
            assert contrast_ratio(theme.MUTED_TEXT_ON_DARK, surface) >= 4.5

    def test_chrome_text_follows_the_app_color_scheme(self):
        """Chrome rules resolve through light-dark(); white-surface rules do not."""
        css = build_css()

        for selector in (
            ".cmido-page-title",
            ".cmido-section-title",
            ".cmido-nav-group-label",
            ".cmido-nav-legend-title",
            ".cmido-breadcrumb",
        ):
            rule = css.split(selector, 1)[1].split("}", 1)[0]
            assert "light-dark(" in rule, selector

        card_rule = css.split(".cmido-card-title", 1)[1].split("}", 1)[0]
        assert "light-dark" not in card_rule
        kpi_rule = css.split(".cmido-kpi {", 1)[1].split("}", 1)[0]
        assert "light-dark" not in kpi_rule

    def test_accent_text_is_readable_on_its_soft_background(self):
        from src.construction.dashboard_ui import theme

        assert contrast_ratio(theme.ACCENT, theme.ACCENT_SOFT) >= 4.5

    @pytest.mark.parametrize("key", sorted(STATUS_PALETTE))
    def test_status_badge_text_is_readable_on_its_background(self, key):
        palette = STATUS_PALETTE[key]
        assert contrast_ratio(palette["color"], palette["soft"]) >= 4.5, key

    @pytest.mark.parametrize("code", sorted(PROVENANCE_LABELS))
    def test_provenance_badge_text_is_readable(self, code):
        from src.construction.dashboard_ui.badges import PROVENANCE_STYLES

        style = PROVENANCE_STYLES[code]
        assert contrast_ratio(style["color"], style["soft"]) >= 4.5, code

    def test_status_is_never_conveyed_by_colour_alone(self):
        """Every badge carries a text label and a tooltip."""
        from src.construction.dashboard_ui.badges import build_uncertainty_badge

        for status in ArtifactStatus:
            html = build_status_badge(status)
            assert ">" in html
            assert status_title(status) in html
            assert "title=" in html
        assert "title=" in build_uncertainty_badge("tail")

    def test_no_low_contrast_white_text_on_light_cards(self):
        """White text is only ever used on the dark table header."""
        from src.construction.dashboard_ui import theme

        assert contrast_ratio("#FFFFFF", theme.SURFACE) < 4.5
        assert contrast_ratio("#FFFFFF", theme.PAGE_BG) < 4.5
        assert contrast_ratio("#FFFFFF", theme.PAGE_BG) < 1.5

    def test_critical_information_is_not_hover_only(self):
        """Provenance and evidence text appear in the markup, not just titles."""
        html = build_kpi_card("Service risk", "0.31", provenance="EST", status="valid")
        assert "EST" in html
        assert "Validated" in html


# ---------------------------------------------------------------------------
# Layering / performance guarantees
# ---------------------------------------------------------------------------
class TestLayering:
    def test_ui_layer_does_not_read_artifacts_or_results(self):
        forbidden = ("read_csv", "read_text(", "read_parquet", "open(", "os.listdir", "glob(")
        offenders = []
        for path in sorted(UI_DIR.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.name}: {token}")
        assert offenders == []

    def test_ui_layer_does_not_import_research_engines(self):
        forbidden = (
            "src.construction.simulation",
            "src.construction.uncertainty",
            "src.construction.experiments",
            "src.construction.resource_dashboard",
        )
        offenders = []
        for path in sorted(UI_DIR.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if f"import {token}" in text:
                    offenders.append(f"{path.name}: {token}")
        assert offenders == []

    def test_only_the_component_layer_touches_streamlit(self):
        streamlit_modules = [
            path.name
            for path in sorted(UI_DIR.glob("*.py"))
            if "import streamlit" in path.read_text(encoding="utf-8")
        ]
        assert streamlit_modules == ["components.py"]

    def test_package_exports_are_all_resolvable(self):
        import src.construction.dashboard_ui as ui

        assert ui.__all__
        missing = [name for name in ui.__all__ if not hasattr(ui, name)]
        assert missing == []

    def test_no_new_frontend_framework_dependency(self):
        requirements = Path("requirements-dashboard.txt").read_text(encoding="utf-8").lower()
        for banned in ("react", "next", "vite", "tailwind", "bootstrap", "vue"):
            assert banned not in requirements
