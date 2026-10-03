"""Tests for CMIDO 10A.2-B Artifact Adapters and Safe Loader."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.construction.dashboard_data.contract import ArtifactStatus
from src.construction.dashboard_data.loaders import LoadResult, load_artifact
from src.construction.dashboard_data.registry import get_entry
from src.construction.dashboard_data.validation import validate_load_result
from src.construction.dashboard_data.adapters import (
    adapt_ro1_evidence,
    adapt_ro2_evidence,
    adapt_ro3_evidence,
    adapt_real_data_evidence,
)


def test_safe_loader_handles_missing_file(tmp_path: Path):
    entry = get_entry("RO1_VALIDATION_METRICS")
    assert entry is not None
    # Using tmp_path where file does not exist
    result = load_artifact(entry, tmp_path)
    assert result.status == ArtifactStatus.MISSING
    assert result.data is None
    assert "File missing" in result.error_message


def test_schema_validator_catches_missing_columns():
    entry = get_entry("RO1_VALIDATION_METRICS")
    assert entry is not None
    
    # Create incomplete dataframe missing expected columns
    bad_df = pd.DataFrame({"col_a": [1], "col_b": [2]})
    raw_result = LoadResult(
        entry=entry,
        status=ArtifactStatus.AVAILABLE,
        data=bad_df,
        provenance=None,
    )
    # Temporarily construct fake provenance to test validator
    from src.construction.dashboard_data.provenance import build_provenance_record
    prov = build_provenance_record(entry, Path("."), ArtifactStatus.AVAILABLE)
    raw_result = LoadResult(
        entry=entry,
        status=ArtifactStatus.AVAILABLE,
        data=bad_df,
        provenance=prov,
    )
    
    val_result, is_valid = validate_load_result(raw_result)
    assert is_valid is False
    assert val_result.status == ArtifactStatus.INVALID
    assert "MISSING_COLUMNS" in val_result.provenance.schema_status


def test_adapters_populate_evidence_structures():
    root = Path(__file__).resolve().parents[2]
    
    ro1_entry = get_entry("RO1_VALIDATION_METRICS")
    assert ro1_entry is not None
    ro1_load = load_artifact(ro1_entry, root)
    
    ro1_ev = adapt_ro1_evidence({"RO1_VALIDATION_METRICS": ro1_load})
    assert len(ro1_ev.validation_metrics) > 0
    assert len(ro1_ev.provenance) == 1
    assert ro1_ev.validation_metrics[0]["dataset"] == "RO1_DEMAND"
