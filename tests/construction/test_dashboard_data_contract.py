"""Tests for CMIDO 10A.2-B Dashboard Data Contract and Snapshot Builder."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.construction.dashboard_data import (
    ARTIFACT_REGISTRY,
    build_dashboard_snapshot,
)
from src.construction.dashboard_data.contract import (
    ArtifactProvenance,
    ArtifactStatus,
    DashboardSnapshot,
    ProvenanceClass,
)


def test_build_dashboard_snapshot_returns_valid_instance():
    snapshot = build_dashboard_snapshot()
    assert isinstance(snapshot, DashboardSnapshot)
    assert snapshot.overview.total_artifacts_registered > 0
    assert snapshot.overview.total_artifacts_available > 0
    assert len(snapshot.provenance) == len(ARTIFACT_REGISTRY)


def test_snapshot_contains_all_components():
    snapshot = build_dashboard_snapshot()
    assert snapshot.ro1 is not None
    assert snapshot.ro2 is not None
    assert snapshot.ro3 is not None
    assert snapshot.real_data is not None
    assert snapshot.evidence is not None


def test_large_files_are_blocked_from_loading():
    snapshot = build_dashboard_snapshot()
    raw_2500_prov = next(
        p for p in snapshot.provenance if p.artifact_id == "RO3_SCENARIOS_2500_RAW"
    )
    assert raw_2500_prov.status == ArtifactStatus.TOO_LARGE
    assert raw_2500_prov.schema_status == "BLOCKED_BY_POLICY"

    raw_5000_prov = next(
        p for p in snapshot.provenance if p.artifact_id == "RO3_SCENARIOS_5000_RAW"
    )
    assert raw_5000_prov.status == ArtifactStatus.TOO_LARGE
    assert raw_5000_prov.schema_status == "BLOCKED_BY_POLICY"


def test_provenance_records_have_valid_classes():
    snapshot = build_dashboard_snapshot()
    for prov in snapshot.provenance:
        assert isinstance(prov.provenance_class, ProvenanceClass)
        assert isinstance(prov.status, ArtifactStatus)
        assert prov.artifact_id != ""
        assert prov.source_path != ""
