"""CMIDO external-data contracts.

Declares the field schemas, supported analyses, upload limits and validation
report shape for the external-data ingestion workflow.  These contracts are the
single source of truth for what the dashboard will accept and which analyses it
can genuinely run on uploaded data.

Two analyses are genuinely supported on uploaded tabular data:

* ``descriptive_statistics`` — CMIDO's seeded descriptive + bootstrap engine
  (``summarize_numeric`` / ``bootstrap_mean_ci``) applied to one mapped numeric
  measure column.
* ``forecast_coverage`` — CMIDO's calibration/coverage discipline applied to an
  observed column and a set of predictive-interval bound columns.

Every other research stage (full RO1 model training, RO2 joint propagation,
RO3 multi-objective optimization) requires frozen upstream artifacts and is
therefore reported as unavailable for uploaded data rather than simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------

#: Largest accepted upload, in bytes (10 MiB).
MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024

#: Accepted file extensions (lower-case, without the dot).
SUPPORTED_EXTENSIONS: tuple[str, ...] = ("csv", "json")

#: Refuse tables wider or taller than these guards after parsing.
MAX_COLUMNS: int = 512
MAX_ROWS: int = 200_000


class ProvenanceClass(str, Enum):
    """Provenance classification, mirroring the dashboard contract."""

    OBS = "OBS"
    DER = "DER"
    EST = "EST"
    SCN = "SCN"


# ---------------------------------------------------------------------------
# Field contracts
# ---------------------------------------------------------------------------


class FieldType(str, Enum):
    """The semantic role a mapped column plays in an analysis."""

    NUMERIC = "numeric"
    DATETIME = "datetime"
    CATEGORY = "category"
    IDENTIFIER = "identifier"


@dataclass(frozen=True)
class FieldSpec:
    """One declared CMIDO field that a user column may be mapped onto."""

    key: str
    label: str
    field_type: FieldType
    required: bool
    description: str
    unit: str = ""

    def describe(self) -> str:
        req = "required" if self.required else "optional"
        unit = f" ({self.unit})" if self.unit else ""
        return f"{self.label} — {self.description} [{req}{unit}]"


@dataclass(frozen=True)
class AnalysisSpec:
    """A single analysis that can (or cannot) run on uploaded data."""

    key: str
    label: str
    summary: str
    fields: tuple[FieldSpec, ...]
    supported: bool = True
    unavailable_reason: str = ""
    output_description: str = ""

    def required_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(f for f in self.fields if f.required)

    def optional_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(f for f in self.fields if not f.required)


# ---------------------------------------------------------------------------
# Concrete analysis definitions
# ---------------------------------------------------------------------------

DESCRIPTIVE_STATISTICS = AnalysisSpec(
    key="descriptive_statistics",
    label="Descriptive statistics + bootstrap interval",
    summary=(
        "Count, mean, standard deviation, median, quartiles and a seeded "
        "bootstrap 95% confidence interval for the mean of one numeric column. "
        "Uses CMIDO's deterministic bootstrap engine (fixed seed, reproducible)."
    ),
    fields=(
        FieldSpec(
            key="measure",
            label="Measure column",
            field_type=FieldType.NUMERIC,
            required=True,
            description="A numeric column to summarise",
            unit="declared by the user",
        ),
        FieldSpec(
            key="group",
            label="Group-by column",
            field_type=FieldType.CATEGORY,
            required=False,
            description=(
                "Optional categorical column; the measure is summarised per group"
            ),
        ),
    ),
    output_description=(
        "Per-group descriptive statistics and a bootstrap 95% CI for the mean, "
        "computed only from the uploaded rows."
    ),
)

FORECAST_COVERAGE = AnalysisSpec(
    key="forecast_coverage",
    label="Forecast interval coverage",
    summary=(
        "Empirical coverage and mean interval width for one or more predictive "
        "intervals against an observed column, plus pinball loss for any "
        "quantile columns. Mirrors CMIDO's RO1 calibration/coverage discipline "
        "on the uploaded rows."
    ),
    fields=(
        FieldSpec(
            key="observed",
            label="Observed column",
            field_type=FieldType.NUMERIC,
            required=True,
            description="The realised / observed value each row is scored against",
        ),
        FieldSpec(
            key="interval_lower",
            label="Interval lower bound column",
            field_type=FieldType.NUMERIC,
            required=True,
            description="Lower bound of the predictive interval",
        ),
        FieldSpec(
            key="interval_upper",
            label="Interval upper bound column",
            field_type=FieldType.NUMERIC,
            required=True,
            description="Upper bound of the predictive interval",
        ),
        FieldSpec(
            key="quantile",
            label="Quantile column",
            field_type=FieldType.NUMERIC,
            required=False,
            description=(
                "Optional point quantile (e.g. median) used for pinball loss"
            ),
        ),
        FieldSpec(
            key="quantile_level",
            label="Quantile level",
            field_type=FieldType.NUMERIC,
            required=False,
            description="The probability level of the quantile column (0-1)",
        ),
    ),
    output_description=(
        "Empirical coverage rate, mean interval width and (when a quantile is "
        "mapped) pinball loss, computed only from the uploaded rows."
    ),
)

#: Analyses that require frozen upstream artifacts and are NOT run on uploads.
_RO1_UNAVAILABLE = (
    "Full RO1 probabilistic model training requires the frozen rolling-origin "
    "backtest harness and observed price/demand streams; it is not retrained on "
    "uploaded data. The forecast-coverage analysis above scores uploaded "
    "intervals using the same discipline instead."
)
_RO2_UNAVAILABLE = (
    "RO2 joint uncertainty propagation requires defensible demand and "
    "supply/lead-time representations plus the frozen scenario ledger; these "
    "are not derivable from an arbitrary uploaded table and are never "
    "fabricated."
)
_RO3_UNAVAILABLE = (
    "RO3 multi-objective procurement optimization requires the frozen scenario "
    "set, supplier constraints, objective definitions and compatible upstream "
    "RO2 outputs; these are not derivable from an arbitrary uploaded table and "
    "are never fabricated."
)

RO1_UNAVAILABLE = AnalysisSpec(
    key="ro1_model_training",
    label="RO1 probabilistic model training",
    summary="Train/calibrate an RO1 forecasting model on the uploaded data.",
    fields=(),
    supported=False,
    unavailable_reason=_RO1_UNAVAILABLE,
)
RO2_UNAVAILABLE = AnalysisSpec(
    key="ro2_propagation",
    label="RO2 joint uncertainty propagation",
    summary="Run RO2 joint demand/supply uncertainty propagation.",
    fields=(),
    supported=False,
    unavailable_reason=_RO2_UNAVAILABLE,
)
RO3_UNAVAILABLE = AnalysisSpec(
    key="ro3_optimization",
    label="RO3 multi-objective procurement optimization",
    summary="Run RO3 procurement optimization on the uploaded data.",
    fields=(),
    supported=False,
    unavailable_reason=_RO3_UNAVAILABLE,
)

#: Ordered registry of every analysis the workflow knows about.
ANALYSES: tuple[AnalysisSpec, ...] = (
    DESCRIPTIVE_STATISTICS,
    FORECAST_COVERAGE,
    RO1_UNAVAILABLE,
    RO2_UNAVAILABLE,
    RO3_UNAVAILABLE,
)

ANALYSES_BY_KEY: dict[str, AnalysisSpec] = {a.key: a for a in ANALYSES}


def analysis_by_key(key: str) -> AnalysisSpec:
    """Return the :class:`AnalysisSpec` for ``key`` or raise ``KeyError``."""
    if key not in ANALYSES_BY_KEY:
        raise KeyError(f"unknown analysis: {key}")
    return ANALYSES_BY_KEY[key]


# ---------------------------------------------------------------------------
# Mapping + validation shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MappingSpec:
    """An explicit analysis choice plus field->column assignments."""

    analysis_key: str
    column_by_field: dict[str, str]

    @property
    def analysis(self) -> AnalysisSpec:
        return analysis_by_key(self.analysis_key)


@dataclass
class ValidationIssue:
    """A single validation finding."""

    severity: str  # "error" | "warning"
    field_key: str
    message: str


@dataclass
class ValidationReport:
    """The outcome of validating a mapping against the uploaded table."""

    analysis_key: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, field_key: str, message: str) -> None:
        self.issues.append(ValidationIssue("error", field_key, message))

    def add_warning(self, field_key: str, message: str) -> None:
        self.issues.append(ValidationIssue("warning", field_key, message))

    def as_dict(self) -> dict[str, Any]:
        return {
            "analysis_key": self.analysis_key,
            "ok": self.ok,
            "errors": [
                {"field": i.field_key, "message": i.message} for i in self.errors
            ],
            "warnings": [
                {"field": i.field_key, "message": i.message} for i in self.warnings
            ],
        }
