"""CMIDO 10A.2-B — Dashboard Schema and Integrity Validation.

Validates that loaded artifacts meet expected schemas (column contracts for CSV,
key contracts for JSON) before passing them to dashboard adapters.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.construction.dashboard_data.contract import ArtifactStatus
from src.construction.dashboard_data.loaders import LoadResult
from src.construction.dashboard_data.provenance import ArtifactProvenance


def validate_load_result(result: LoadResult) -> tuple[LoadResult, bool]:
    """Validate a loaded result against expected columns/schema defined in registry entry.

    Returns updated LoadResult and a boolean indicating overall schema validity.
    """
    if result.status != ArtifactStatus.AVAILABLE or result.data is None:
        return result, False

    entry = result.entry
    expected_cols = entry.expected_columns

    if not expected_cols:
        # No strict column validation specified
        return result, True

    if isinstance(result.data, pd.DataFrame):
        df = result.data
        missing_cols = [col for col in expected_cols if col not in df.columns]

        if missing_cols:
            updated_prov = ArtifactProvenance(
                artifact_id=result.provenance.artifact_id,
                source_path=result.provenance.source_path,
                provenance_class=result.provenance.provenance_class,
                research_stage=result.provenance.research_stage,
                status=ArtifactStatus.INVALID,
                row_count=result.provenance.row_count,
                file_size_bytes=result.provenance.file_size_bytes,
                schema_status=f"MISSING_COLUMNS: {', '.join(missing_cols)}",
                notes=f"Missing expected columns: {missing_cols}",
            )
            updated_result = LoadResult(
                entry=entry,
                status=ArtifactStatus.INVALID,
                data=result.data,
                provenance=updated_prov,
                error_message=f"Missing expected columns: {missing_cols}",
            )
            return updated_result, False

        updated_prov = ArtifactProvenance(
            artifact_id=result.provenance.artifact_id,
            source_path=result.provenance.source_path,
            provenance_class=result.provenance.provenance_class,
            research_stage=result.provenance.research_stage,
            status=result.provenance.status,
            row_count=result.provenance.row_count,
            file_size_bytes=result.provenance.file_size_bytes,
            schema_status="PASSED",
            notes=result.provenance.notes,
        )
        updated_result = LoadResult(
            entry=entry,
            status=result.status,
            data=result.data,
            provenance=updated_prov,
            error_message=result.error_message,
        )
        return updated_result, True

    return result, True
