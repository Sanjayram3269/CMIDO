"""CMIDO 10A.2-B — Typed Dashboard Data Contract.

Every field consumed by Streamlit passes through one of the typed
structures defined here.  Provenance classes follow the existing CMIDO
convention: OBS, DER, EST, SCN.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ------------------------------------------------------------------
# Provenance classes
# ------------------------------------------------------------------

class ProvenanceClass(str, Enum):
    """Provenance classification for dashboard evidence."""
    OBS = "OBS"   # Observed / raw data
    DER = "DER"   # Deterministic derivation
    EST = "EST"   # Statistical estimate
    SCN = "SCN"   # Scenario-generated


# ------------------------------------------------------------------
# Artifact availability
# ------------------------------------------------------------------

class ArtifactStatus(str, Enum):
    """Loading outcome for a single artifact."""
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    INVALID = "INVALID"
    UNSUPPORTED = "UNSUPPORTED"
    TOO_LARGE = "TOO_LARGE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ------------------------------------------------------------------
# Provenance record
# ------------------------------------------------------------------

@dataclass(frozen=True)
class ArtifactProvenance:
    """Provenance metadata for a loaded dashboard artifact."""
    artifact_id: str
    source_path: str
    provenance_class: ProvenanceClass
    research_stage: str
    status: ArtifactStatus
    row_count: int | None = None
    file_size_bytes: int | None = None
    schema_status: str = "UNCHECKED"
    notes: str = ""


# ------------------------------------------------------------------
# RO1 — Forecasting evidence
# ------------------------------------------------------------------

@dataclass(frozen=True)
class RO1Evidence:
    """Publication-grade RO1 forecasting validation evidence."""
    validation_metrics: list[dict[str, Any]] = field(default_factory=list)
    calibration_summary: list[dict[str, Any]] = field(default_factory=list)
    paired_comparison: list[dict[str, Any]] = field(default_factory=list)
    integrity_audit: dict[str, Any] = field(default_factory=dict)
    provenance: list[ArtifactProvenance] = field(default_factory=list)


# ------------------------------------------------------------------
# RO2 — Uncertainty propagation evidence
# ------------------------------------------------------------------

@dataclass(frozen=True)
class RO2Evidence:
    """Publication-grade RO2 uncertainty-propagation evidence."""
    joint_propagation_summary: list[dict[str, Any]] = field(
        default_factory=list,
    )
    tail_comparison: list[dict[str, Any]] = field(default_factory=list)
    service_risk_curve: list[dict[str, Any]] = field(default_factory=list)
    sensitivity: list[dict[str, Any]] = field(default_factory=list)
    final_audit: dict[str, Any] = field(default_factory=dict)
    provenance: list[ArtifactProvenance] = field(default_factory=list)


# ------------------------------------------------------------------
# RO3 — Optimization evidence
# ------------------------------------------------------------------

@dataclass(frozen=True)
class RO3Evidence:
    """Publication-grade RO3 optimisation / ablation evidence."""
    baseline_comparison: list[dict[str, Any]] = field(
        default_factory=list,
    )
    ablation: list[dict[str, Any]] = field(default_factory=list)
    controller_descriptives: list[dict[str, Any]] = field(
        default_factory=list,
    )
    stress_summary: list[dict[str, Any]] = field(default_factory=list)
    robustness_summary: list[dict[str, Any]] = field(
        default_factory=list,
    )
    convergence_summary: dict[str, Any] = field(default_factory=dict)
    pareto_summary: list[dict[str, Any]] = field(default_factory=list)
    final_audit: dict[str, Any] = field(default_factory=dict)
    provenance: list[ArtifactProvenance] = field(default_factory=list)


# ------------------------------------------------------------------
# Real-data evidence
# ------------------------------------------------------------------

@dataclass(frozen=True)
class RealDataEvidence:
    """Evidence from PSLIB / SUCCESS real-data ingestion.

    PSLIB and SUCCESS are complementary observed datasets.
    They are NOT joined unless an explicit validated artifact
    establishes that relationship.
    """
    pslib_audit: dict[str, Any] = field(default_factory=dict)
    success_ingestion_audit: dict[str, Any] = field(
        default_factory=dict,
    )
    canonical_9a: dict[str, Any] = field(default_factory=dict)
    experiment_9b: dict[str, Any] = field(default_factory=dict)
    provenance: list[ArtifactProvenance] = field(default_factory=list)


# ------------------------------------------------------------------
# Publication / reconciliation evidence
# ------------------------------------------------------------------

@dataclass(frozen=True)
class PublicationEvidence:
    """Publication-readiness and reconciliation evidence."""
    reconciliation_audit: list[dict[str, Any]] = field(
        default_factory=list,
    )
    publication_manifest: dict[str, Any] = field(default_factory=dict)
    figure_concordance: dict[str, Any] = field(default_factory=dict)
    provenance: list[ArtifactProvenance] = field(default_factory=list)


# ------------------------------------------------------------------
# Pipeline overview
# ------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineOverview:
    """High-level research pipeline status."""
    pipeline_stages: list[str] = field(default_factory=lambda: [
        "Historical / Observed Data",
        "Probabilistic Price & Demand Forecasting",
        "Predictive Uncertainty",
        "Supply / Lead-Time Uncertainty",
        "Joint Uncertainty Propagation",
        "Shortage / Service-Risk Distribution",
        "Multi-Objective Procurement Optimization",
        "Quantity + Timing + Supplier Allocation + Safety Stock",
        "Cost / Service / Resilience Trade-offs",
        "Ablation / Stress / Robustness",
        "Decision-Level Validation",
    ])
    total_artifacts_registered: int = 0
    total_artifacts_available: int = 0
    total_artifacts_missing: int = 0
    total_artifacts_invalid: int = 0


# ------------------------------------------------------------------
# Canonical dashboard snapshot
# ------------------------------------------------------------------

@dataclass(frozen=True)
class DashboardSnapshot:
    """Canonical, read-only dashboard snapshot.

    Every Streamlit page should read from this structure
    rather than parsing individual CSV schemas directly.
    """
    overview: PipelineOverview = field(
        default_factory=PipelineOverview,
    )
    ro1: RO1Evidence = field(default_factory=RO1Evidence)
    ro2: RO2Evidence = field(default_factory=RO2Evidence)
    ro3: RO3Evidence = field(default_factory=RO3Evidence)
    real_data: RealDataEvidence = field(
        default_factory=RealDataEvidence,
    )
    evidence: PublicationEvidence = field(
        default_factory=PublicationEvidence,
    )
    provenance: list[ArtifactProvenance] = field(
        default_factory=list,
    )
