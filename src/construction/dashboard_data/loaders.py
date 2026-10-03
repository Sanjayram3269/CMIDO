"""CMIDO 10A.2-B — Safe Artifact Loader.

Responsible for safely loading registered research artifacts without crashing
the Streamlit application on missing/invalid files or accidentally ingesting
multi-hundred-megabyte raw scenario ledgers.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.construction.dashboard_data.contract import ArtifactStatus
from src.construction.dashboard_data.provenance import build_provenance_record
from src.construction.dashboard_data.registry import (
    ArtifactEntry,
    ArtifactType,
    LoadingPolicy,
)


@dataclass(frozen=True)
class LoadResult:
    """Outcome of attempting to load a registered artifact."""
    entry: ArtifactEntry
    status: ArtifactStatus
    data: Any | None
    provenance: Any  # ArtifactProvenance
    error_message: str = ""


def load_artifact(entry: ArtifactEntry, root_path: Path) -> LoadResult:
    """Safely load a single artifact according to its policy, type, and size caps."""
    abs_path = (root_path / entry.relative_path).resolve()

    # Policy Check: NEVER load
    if entry.loading_policy == LoadingPolicy.NEVER:
        prov = build_provenance_record(
            entry,
            root_path,
            status=ArtifactStatus.TOO_LARGE,
            schema_status="BLOCKED_BY_POLICY",
            notes="Loading blocked by policy (large raw scenario file).",
        )
        return LoadResult(
            entry=entry,
            status=ArtifactStatus.TOO_LARGE,
            data=None,
            provenance=prov,
            error_message="Loading blocked by policy (large raw scenario file).",
        )

    # File Existence Check
    if not abs_path.exists() or not abs_path.is_file():
        status = ArtifactStatus.MISSING
        prov = build_provenance_record(
            entry,
            root_path,
            status=status,
            schema_status="FILE_NOT_FOUND",
            notes=f"File not found at {entry.relative_path}",
        )
        return LoadResult(
            entry=entry,
            status=status,
            data=None,
            provenance=prov,
            error_message=f"File missing: {entry.relative_path}",
        )

    # Size Check
    file_size = abs_path.stat().st_size
    if entry.max_safe_bytes > 0 and file_size > entry.max_safe_bytes:
        prov = build_provenance_record(
            entry,
            root_path,
            status=ArtifactStatus.TOO_LARGE,
            file_size_bytes=file_size,
            schema_status="EXCEEDS_SIZE_LIMIT",
            notes=f"File size {file_size} B exceeds cap {entry.max_safe_bytes} B",
        )
        return LoadResult(
            entry=entry,
            status=ArtifactStatus.TOO_LARGE,
            data=None,
            provenance=prov,
            error_message=f"File exceeds max safe limit ({file_size} > {entry.max_safe_bytes} bytes)",
        )

    # Read Contents
    try:
        if entry.artifact_type == ArtifactType.CSV:
            df = pd.read_csv(abs_path)
            row_count = len(df)
            prov = build_provenance_record(
                entry,
                root_path,
                status=ArtifactStatus.AVAILABLE,
                row_count=row_count,
                file_size_bytes=file_size,
                schema_status="LOADED",
            )
            return LoadResult(
                entry=entry,
                status=ArtifactStatus.AVAILABLE,
                data=df,
                provenance=prov,
            )

        elif entry.artifact_type == ArtifactType.JSON:
            with open(abs_path, encoding="utf-8") as f:
                data = json.load(f)
            row_count = len(data) if isinstance(data, list) else None
            prov = build_provenance_record(
                entry,
                root_path,
                status=ArtifactStatus.AVAILABLE,
                row_count=row_count,
                file_size_bytes=file_size,
                schema_status="LOADED",
            )
            return LoadResult(
                entry=entry,
                status=ArtifactStatus.AVAILABLE,
                data=data,
                provenance=prov,
            )

        elif entry.artifact_type == ArtifactType.TEXT:
            text = abs_path.read_text(encoding="utf-8")
            prov = build_provenance_record(
                entry,
                root_path,
                status=ArtifactStatus.AVAILABLE,
                file_size_bytes=file_size,
                schema_status="LOADED",
            )
            return LoadResult(
                entry=entry,
                status=ArtifactStatus.AVAILABLE,
                data=text,
                provenance=prov,
            )

        else:
            prov = build_provenance_record(
                entry,
                root_path,
                status=ArtifactStatus.UNSUPPORTED,
                file_size_bytes=file_size,
                schema_status="UNSUPPORTED_TYPE",
            )
            return LoadResult(
                entry=entry,
                status=ArtifactStatus.UNSUPPORTED,
                data=None,
                provenance=prov,
                error_message=f"Unsupported artifact type: {entry.artifact_type}",
            )

    except Exception as exc:
        prov = build_provenance_record(
            entry,
            root_path,
            status=ArtifactStatus.INVALID,
            file_size_bytes=file_size,
            schema_status="READ_ERROR",
            notes=str(exc),
        )
        return LoadResult(
            entry=entry,
            status=ArtifactStatus.INVALID,
            data=None,
            provenance=prov,
            error_message=f"Error parsing artifact: {exc}",
        )
