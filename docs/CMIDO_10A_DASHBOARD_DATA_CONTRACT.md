# CMIDO 10A.2-B — Dashboard Data Contract & Validated Artifact Adapter Layer

## Overview

Milestone **10A.2-B** establishes a production-grade presentation/decision-intelligence layer between CMIDO's validated research engines and the Streamlit web dashboard.

```
CMIDO RESEARCH / EXPERIMENT ENGINES
        ↓
VALIDATED RESULT ARTIFACTS
        ↓
10A.2-B DASHBOARD ARTIFACT ADAPTER
        ↓
CANONICAL DASHBOARD DATA CONTRACT
        ↓
STREAMLIT UI
```

---

## Architectural Principles

1. **Source of Truth**: The dashboard does NOT duplicate, rewrite, re-compute, or fabricate research results. It acts strictly as a presentation/decision-intelligence adapter over existing validated result artifacts.
2. **Provenance Awareness**: Every displayed research evidence item carries explicit provenance classification (`OBS`, `DER`, `EST`, `SCN`).
3. **Large-File Protection**: Multi-hundred megabyte raw scenario ledgers (such as `RO3_step32_scenarios_2500.csv` [~161 MB] and `RO3_step32_scenarios_5000.csv` [~323 MB]) are explicitly marked with `LoadingPolicy.NEVER` to prevent accidental in-memory loading.
4. **Failure Tolerance**: Missing optional research artifacts transition cleanly to `ArtifactStatus.MISSING` without crashing the application.
5. **No Dataset Fabrication**: Real-world datasets (`PSLIB` and `SUCCESS`) are presented as complementary observed evidence sources without fake joins.

---

## Package Structure (`src/construction/dashboard_data/`)

| Module | Description |
|---|---|
| `contract.py` | Typed, immutable dataclass structures (`DashboardSnapshot`, `RO1Evidence`, `RO2Evidence`, `RO3Evidence`, `RealDataEvidence`, `PublicationEvidence`, `ArtifactProvenance`). |
| `registry.py` | Central catalogue (`ARTIFACT_REGISTRY`) defining relative paths, schema requirements, provenance classes, and loading policies. |
| `loaders.py` | Safe artifact loader with file size caps, policy enforcement, format parsing (CSV/JSON/TEXT), and exception handling. |
| `validation.py` | Column and schema integrity validator. |
| `adapters.py` | Research artifact transformers converting validated raw data into contract structures. |
| `provenance.py` | Metadata builder for provenance tracking. |
| `snapshot.py` | Master snapshot orchestrator `build_dashboard_snapshot()`. |

---

## Central Artifact Registry

All dashboard-relevant artifacts are registered in `ARTIFACT_REGISTRY` in `src/construction/dashboard_data/registry.py`.

### Registered Components
- **RO1 Forecasting**: Validation metrics (`T1_RO1_validation_metrics.csv`), calibration scores, paired bootstrap results, final integrity audit.
- **RO2 Uncertainty Propagation**: Joint propagation summary (`T2_RO2_joint_propagation_summary.csv`), tail comparison, service-risk curves, joint/independent sensitivity, final audit.
- **RO3 Optimisation**: Baseline comparison (`T5_RO3_baseline_comparison.csv`), ablation (`T6_RO3_ablation.csv`), controller descriptives, stress summary, robustness holding-rate summary, convergence summary.
- **Real-Data Evidence**: 9A SUCCESS canonical fixture & ingestion audit, 9B PSLIB project audit & experiment manifest.
- **Publication & Reconciliation**: 8S numerical reconciliation audit (`CMIDO_8S_RECONCILIATION_AUDIT.csv`), 8Q publication manifest, 8R figure concordance.

---

## Usage in Streamlit

```python
from src.construction.dashboard_data import build_dashboard_snapshot

# Load snapshot
snapshot = build_dashboard_snapshot(ROOT)

# Access typed evidence
ro1_metrics = snapshot.ro1.validation_metrics
ro2_joint = snapshot.ro2.joint_propagation_summary
ro3_ablation = snapshot.ro3.ablation
provenance_list = snapshot.provenance
```

---

## Adding a New Dashboard Artifact

1. Open `src/construction/dashboard_data/registry.py`.
2. Add a new `ArtifactEntry` to `ARTIFACT_REGISTRY`:
```python
ArtifactEntry(
    artifact_id="MY_NEW_ARTIFACT",
    name="Human Readable Name",
    component=ResearchComponent.RO3,
    relative_path="results/path/to/artifact.csv",
    artifact_type=ArtifactType.CSV,
    loading_policy=LoadingPolicy.SAFE,
    required=False,
    description="Description of the artifact",
    expected_columns=("col1", "col2"),
    provenance_class="DER",
),
```
3. Update the corresponding adapter in `src/construction/dashboard_data/adapters.py`.
4. Run tests: `python -m pytest tests/construction/test_dashboard_artifact_registry.py`.
