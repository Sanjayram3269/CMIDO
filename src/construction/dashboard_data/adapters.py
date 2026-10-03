"""CMIDO 10A.2-B — Research Artifact Adapters.

Transforms validated raw research artifacts into stable, typed dashboard structures
(RO1Evidence, RO2Evidence, RO3Evidence, RealDataEvidence, PublicationEvidence).
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.construction.dashboard_data.contract import (
    ArtifactProvenance,
    ArtifactStatus,
    PublicationEvidence,
    RealDataEvidence,
    RO1Evidence,
    RO2Evidence,
    RO3Evidence,
)
from src.construction.dashboard_data.loaders import LoadResult


def adapt_ro1_evidence(results: dict[str, LoadResult]) -> RO1Evidence:
    """Adapt RO1 forecasting artifacts into RO1Evidence contract."""
    validation_metrics: list[dict[str, Any]] = []
    calibration_summary: list[dict[str, Any]] = []
    paired_comparison: list[dict[str, Any]] = []
    integrity_audit: dict[str, Any] = {}
    provenance_list: list[ArtifactProvenance] = []

    # 1. Validation metrics
    res = results.get("RO1_VALIDATION_METRICS")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            validation_metrics = res.data.to_dict(orient="records")

    # 2. Calibration scores / summary
    res = results.get("RO1_CALIBRATION_SCORES")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            calibration_summary = res.data.to_dict(orient="records")

    # 3. Paired comparison
    res = results.get("RO1_PAIRED_BOOTSTRAP")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            paired_comparison = res.data.to_dict(orient="records")

    # 4. Integrity audit
    res = results.get("RO1_FINAL_INTEGRITY")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, dict):
            integrity_audit = res.data

    return RO1Evidence(
        validation_metrics=validation_metrics,
        calibration_summary=calibration_summary,
        paired_comparison=paired_comparison,
        integrity_audit=integrity_audit,
        provenance=provenance_list,
    )


def adapt_ro2_evidence(results: dict[str, LoadResult]) -> RO2Evidence:
    """Adapt RO2 uncertainty-propagation artifacts into RO2Evidence contract."""
    joint_propagation_summary: list[dict[str, Any]] = []
    tail_comparison: list[dict[str, Any]] = []
    service_risk_curve: list[dict[str, Any]] = []
    sensitivity: list[dict[str, Any]] = []
    final_audit: dict[str, Any] = {}
    provenance_list: list[ArtifactProvenance] = []

    # 1. Joint propagation summary
    res = results.get("RO2_JOINT_PROPAGATION")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            joint_propagation_summary = res.data.to_dict(orient="records")

    # 2. Tail comparison
    res = results.get("RO2_TAIL_COMPARISON")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            tail_comparison = res.data.to_dict(orient="records")

    # 3. Service risk curve
    res = results.get("RO2_SERVICE_RISK")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            service_risk_curve = res.data.to_dict(orient="records")

    # 4. Sensitivity
    res = results.get("RO2_SENSITIVITY")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            sensitivity = res.data.to_dict(orient="records")

    # 5. Final audit
    res = results.get("RO2_FINAL_AUDIT")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, dict):
            final_audit = res.data

    return RO2Evidence(
        joint_propagation_summary=joint_propagation_summary,
        tail_comparison=tail_comparison,
        service_risk_curve=service_risk_curve,
        sensitivity=sensitivity,
        final_audit=final_audit,
        provenance=provenance_list,
    )


def adapt_ro3_evidence(results: dict[str, LoadResult]) -> RO3Evidence:
    """Adapt RO3 optimisation artifacts into RO3Evidence contract."""
    baseline_comparison: list[dict[str, Any]] = []
    ablation: list[dict[str, Any]] = []
    controller_descriptives: list[dict[str, Any]] = []
    stress_summary: list[dict[str, Any]] = []
    robustness_summary: list[dict[str, Any]] = []
    convergence_summary: dict[str, Any] = {}
    pareto_summary: list[dict[str, Any]] = []
    final_audit: dict[str, Any] = {}
    provenance_list: list[ArtifactProvenance] = []

    # 1. Baseline comparison
    res = results.get("RO3_BASELINE_COMPARISON")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            baseline_comparison = res.data.to_dict(orient="records")

    # 2. Ablation
    res = results.get("RO3_ABLATION")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            ablation = res.data.to_dict(orient="records")

    # 3. Controller descriptives
    res = results.get("RO3_CONTROLLER_DESCRIPTIVES")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            controller_descriptives = res.data.to_dict(orient="records")

    # 4. Stress summary
    res = results.get("RO3_STRESS_SUMMARY")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            stress_summary = res.data.to_dict(orient="records")

    # 5. Robustness summary
    res = results.get("RO3_ROBUSTNESS_SUMMARY")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            robustness_summary = res.data.to_dict(orient="records")

    # 6. Convergence summary
    res = results.get("RO3_CONVERGENCE_SUMMARY")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, dict):
            convergence_summary = res.data

    # 7. Final audit
    res = results.get("RO3_FINAL_AUDIT")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            final_audit = {"audit_rows": res.data.to_dict(orient="records")}

    # Also capture blocked scenario files into provenance if present
    for blocked_id in ("RO3_SCENARIOS_2500_RAW", "RO3_SCENARIOS_5000_RAW"):
        b_res = results.get(blocked_id)
        if b_res:
            provenance_list.append(b_res.provenance)

    return RO3Evidence(
        baseline_comparison=baseline_comparison,
        ablation=ablation,
        controller_descriptives=controller_descriptives,
        stress_summary=stress_summary,
        robustness_summary=robustness_summary,
        convergence_summary=convergence_summary,
        pareto_summary=pareto_summary,
        final_audit=final_audit,
        provenance=provenance_list,
    )


def adapt_real_data_evidence(results: dict[str, LoadResult]) -> RealDataEvidence:
    """Adapt real-data ingestion artifacts into RealDataEvidence contract.

    Maintains clear boundary between PSLIB and SUCCESS.
    """
    pslib_audit: dict[str, Any] = {}
    success_ingestion_audit: dict[str, Any] = {}
    canonical_9a: dict[str, Any] = {}
    experiment_9b: dict[str, Any] = {}
    provenance_list: list[ArtifactProvenance] = []

    res = results.get("REAL_9A_CANONICAL")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, dict):
            canonical_9a = res.data

    res = results.get("REAL_9A_INGESTION_AUDIT")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, dict):
            success_ingestion_audit = res.data

    res = results.get("REAL_9B_PSLIB_AUDIT")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, dict):
            pslib_audit = res.data

    res = results.get("REAL_9B_MANIFEST")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, dict):
            experiment_9b = res.data

    return RealDataEvidence(
        pslib_audit=pslib_audit,
        success_ingestion_audit=success_ingestion_audit,
        canonical_9a=canonical_9a,
        experiment_9b=experiment_9b,
        provenance=provenance_list,
    )


def adapt_publication_evidence(results: dict[str, LoadResult]) -> PublicationEvidence:
    """Adapt publication & numerical reconciliation artifacts."""
    reconciliation_audit: list[dict[str, Any]] = []
    publication_manifest: dict[str, Any] = {}
    figure_concordance: dict[str, Any] = {}
    provenance_list: list[ArtifactProvenance] = []

    res = results.get("EVIDENCE_8S_RECONCILIATION")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, pd.DataFrame):
            reconciliation_audit = res.data.to_dict(orient="records")

    res = results.get("EVIDENCE_8Q_MANIFEST")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, dict):
            publication_manifest = res.data

    res = results.get("EVIDENCE_8R_CONCORDANCE")
    if res:
        provenance_list.append(res.provenance)
        if res.status == ArtifactStatus.AVAILABLE and isinstance(res.data, dict):
            figure_concordance = res.data

    return PublicationEvidence(
        reconciliation_audit=reconciliation_audit,
        publication_manifest=publication_manifest,
        figure_concordance=figure_concordance,
        provenance=provenance_list,
    )
