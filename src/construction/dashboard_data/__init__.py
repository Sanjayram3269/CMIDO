"""CMIDO 10A.2-B — Dashboard Data Contract and Artifact Adapter Layer.

This package provides a validated, provenance-aware presentation layer
over CMIDO's research artifacts.  It does NOT duplicate or replace the
underlying research engines.  Every dashboard KPI originates from an
existing validated artifact or a deterministic derivation thereof.

Architecture
------------
ArtifactRegistry  →  SafeLoader  →  SchemaValidator  →  Adapters  →  DashboardSnapshot

Public API
----------
build_dashboard_snapshot  — canonical entry-point
ARTIFACT_REGISTRY         — central artifact catalogue
"""
from __future__ import annotations

from src.construction.dashboard_data.snapshot import (
    build_dashboard_snapshot,
)
from src.construction.dashboard_data.registry import (
    ARTIFACT_REGISTRY,
)

__all__ = [
    "build_dashboard_snapshot",
    "ARTIFACT_REGISTRY",
]
