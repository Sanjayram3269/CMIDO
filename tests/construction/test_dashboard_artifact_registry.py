"""Tests for CMIDO 10A.2-B Central Artifact Registry."""
from __future__ import annotations

from pathlib import Path

from src.construction.dashboard_data.registry import (
    ARTIFACT_REGISTRY,
    ArtifactEntry,
    LoadingPolicy,
    get_blocked_ids,
    get_entry,
    get_required_ids,
    get_safe_ids,
)


def test_registry_contains_entries():
    assert len(ARTIFACT_REGISTRY) >= 15


def test_registry_ids_are_unique():
    ids = [entry.artifact_id for entry in ARTIFACT_REGISTRY]
    assert len(ids) == len(set(ids))


def test_required_artifacts_exist_on_disk():
    root = Path(__file__).resolve().parents[2]
    for entry in ARTIFACT_REGISTRY:
        if entry.required:
            target_path = root / entry.relative_path
            assert target_path.exists(), f"Required artifact {entry.artifact_id} missing at {entry.relative_path}"


def test_get_entry_lookup():
    entry = get_entry("RO1_VALIDATION_METRICS")
    assert entry is not None
    assert entry.artifact_id == "RO1_VALIDATION_METRICS"

    missing = get_entry("NON_EXISTENT_ARTIFACT_ID")
    assert missing is None


def test_blocked_ids():
    blocked = get_blocked_ids()
    assert "RO3_SCENARIOS_2500_RAW" in blocked
    assert "RO3_SCENARIOS_5000_RAW" in blocked
