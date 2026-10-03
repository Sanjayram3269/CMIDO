"""CMIDO 10A.2-B — Canonical Snapshot Orchestration.

Main entry-point for assembling a read-only, schema-validated, provenance-aware
DashboardSnapshot from registered repository result artifacts.
"""
from __future__ import annotations

import os
from pathlib import Path

from src.construction.dashboard_data.adapters import (
    adapt_publication_evidence,
    adapt_real_data_evidence,
    adapt_ro1_evidence,
    adapt_ro2_evidence,
    adapt_ro3_evidence,
)
from src.construction.dashboard_data.contract import (
    ArtifactStatus,
    DashboardSnapshot,
    PipelineOverview,
)
from src.construction.dashboard_data.loaders import LoadResult, load_artifact
from src.construction.dashboard_data.registry import ARTIFACT_REGISTRY
from src.construction.dashboard_data.validation import validate_load_result


def get_default_root() -> Path:
    """Resolve project root directory from environment or file location."""
    override = os.getenv("CMIDO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    # dashboard_data is at src/construction/dashboard_data -> root is 3 levels up
    return Path(__file__).resolve().parents[3]


def build_dashboard_snapshot(root_path: Path | None = None) -> DashboardSnapshot:
    """Orchestrate safe loading, validation, adaptation and provenance assembly.

    Returns a typed, canonical DashboardSnapshot containing all research evidence
    ready for Streamlit rendering. Does NOT run expensive research computations.
    """
    root = (root_path or get_default_root()).resolve()

    load_results: dict[str, LoadResult] = {}
    total_reg = len(ARTIFACT_REGISTRY)
    avail_count = 0
    missing_count = 0
    invalid_count = 0

    # 1. Safe Load & Validate all registered entries
    for entry in ARTIFACT_REGISTRY:
        res = load_artifact(entry, root)
        validated_res, is_valid = validate_load_result(res)
        load_results[entry.artifact_id] = validated_res

        if validated_res.status == ArtifactStatus.AVAILABLE:
            avail_count += 1
        elif validated_res.status == ArtifactStatus.MISSING:
            missing_count += 1
        elif validated_res.status == ArtifactStatus.INVALID:
            invalid_count += 1

    # 2. Adapt evidence by component
    ro1 = adapt_ro1_evidence(load_results)
    ro2 = adapt_ro2_evidence(load_results)
    ro3 = adapt_ro3_evidence(load_results)
    real_data = adapt_real_data_evidence(load_results)
    evidence = adapt_publication_evidence(load_results)

    # 3. Assemble master provenance list
    all_provenance = [r.provenance for r in load_results.values()]

    # 4. Pipeline overview metrics
    overview = PipelineOverview(
        total_artifacts_registered=total_reg,
        total_artifacts_available=avail_count,
        total_artifacts_missing=missing_count,
        total_artifacts_invalid=invalid_count,
    )

    return DashboardSnapshot(
        overview=overview,
        ro1=ro1,
        ro2=ro2,
        ro3=ro3,
        real_data=real_data,
        evidence=evidence,
        provenance=all_provenance,
    )
