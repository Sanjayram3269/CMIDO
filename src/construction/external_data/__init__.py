"""CMIDO external-data ingestion.

A Streamlit-free engine that accepts a user-uploaded CSV or JSON table,
profiles it, maps its columns onto declared CMIDO field contracts, validates
that mapping, and — where the required fields and semantics are satisfied —
executes a genuinely supported analysis using the real CMIDO statistical
engines (``summarize_numeric`` / ``bootstrap_mean_ci``).

Nothing here fabricates missing inputs.  Analyses whose required fields,
upstream artifacts or semantics are not satisfied are reported as unavailable
with an explicit reason rather than silently substituted.

Uploaded-data runs are written to an isolated run workspace and are never
allowed to overwrite canonical research artifacts under ``results/``.
"""

from .contracts import (
    ANALYSES,
    MAX_UPLOAD_BYTES,
    SUPPORTED_EXTENSIONS,
    AnalysisSpec,
    FieldSpec,
    MappingSpec,
    ValidationReport,
)
from .parsing import ParsedTable, ParseError, parse_upload
from .profiling import profile_table
from .mapping import build_mapping_spec, validate_mapping
from .analysis import AnalysisError, execute_analysis
from .lineage import RunRecord, RunStore, safe_filename
from .workflow import WorkflowResult, run_workflow

__all__ = [
    "ANALYSES",
    "MAX_UPLOAD_BYTES",
    "SUPPORTED_EXTENSIONS",
    "AnalysisSpec",
    "FieldSpec",
    "MappingSpec",
    "ValidationReport",
    "ParsedTable",
    "ParseError",
    "parse_upload",
    "profile_table",
    "build_mapping_spec",
    "validate_mapping",
    "AnalysisError",
    "execute_analysis",
    "RunRecord",
    "RunStore",
    "safe_filename",
    "WorkflowResult",
    "run_workflow",
]
