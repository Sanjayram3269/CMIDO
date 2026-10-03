"""CMIDO 10A.2-B — Provenance Representation and Tracking.

Provides utilities for creating, validating, and attaching provenance records
to loaded dashboard artifacts.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.construction.dashboard_data.contract import (
    ArtifactProvenance,
    ArtifactStatus,
    ProvenanceClass,
)
from src.construction.dashboard_data.registry import ArtifactEntry


def build_provenance_record(
    entry: ArtifactEntry,
    root_path: Path,
    status: ArtifactStatus,
    row_count: int | None = None,
    file_size_bytes: int | None = None,
    schema_status: str = "UNCHECKED",
    notes: str = "",
) -> ArtifactProvenance:
    """Construct a clean, immutable ArtifactProvenance record for a registry entry."""
    abs_path = (root_path / entry.relative_path).resolve()
    
    # Try parsing string provenance class into enum
    prov_cls = ProvenanceClass.DER
    if entry.provenance_class:
        try:
            prov_cls = ProvenanceClass(entry.provenance_class.upper())
        except ValueError:
            prov_cls = ProvenanceClass.DER

    # Get file size if not provided but file exists
    if file_size_bytes is None and abs_path.exists() and abs_path.is_file():
        try:
            file_size_bytes = abs_path.stat().st_size
        except OSError:
            file_size_bytes = None

    return ArtifactProvenance(
        artifact_id=entry.artifact_id,
        source_path=entry.relative_path,
        provenance_class=prov_cls,
        research_stage=entry.component.value,
        status=status,
        row_count=row_count,
        file_size_bytes=file_size_bytes,
        schema_status=schema_status,
        notes=notes,
    )
