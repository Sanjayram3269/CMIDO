# CMIDO — Artifact Registry Gaps

Registry state **re-checked against the current checkout on 2026-10-26**, at
`src/construction/dashboard_data/registry.py` (HEAD `89f2e9121463583ce82c3c697d17092680f29459`):

- `ARTIFACT_REGISTRY`: **45 entries**
- `KNOWN_UNREGISTERED_ARTIFACTS`: **12 entries** (present in the repository, deliberately never loaded,
  never rendered, never adapted into the snapshot contract)

Nothing in this file was registered, repaired or silently adapted for packaging. Registration status is
unchanged from the repository.

---

## A. The five decision-level artifacts — **still unregistered**

These are the five named by the Phase 10A.10 decision-level inventory. They are **not** in
`ARTIFACT_REGISTRY`; they sit in `KNOWN_UNREGISTERED_ARTIFACTS` and the dashboard reports them as
*"Present in the repository but not registered"*. Their sources exist on disk and **all five are mirrored
in this package**, but they carry **no** registration and **no** decision gate.

| # | Artifact identifier (registry label) | Repository path | Mirrored in package at | Status |
|---|---|---|---|---|
| 1 | Selected decisions (O2) | `results/RO3/ablation/O2/O2_selected_decisions.csv` | `04_RESULTS/RO3/ablation/O2/O2_selected_decisions.csv` | **UNREGISTERED** |
| 2 | Realized evaluation summary (O2) | `results/RO3/ablation/O2/O2_realized_evaluation_summary.csv` | `04_RESULTS/RO3/ablation/O2/O2_realized_evaluation_summary.csv` | **UNREGISTERED** |
| 3 | Realized evaluation ledger (O4 single origin) | `results/RO3/ablation/O4_single_origin/O4_single_origin_realized_evaluation_ledger.csv` | `04_RESULTS/RO3/ablation/O4_single_origin/…` | **UNREGISTERED** |
| 4 | Per-origin Pareto summary (step 35) | `results/RO3/multi_origin/RO3_step35_origin_summary_N2500.csv` | `04_RESULTS/RO3/multi_origin/…` | **UNREGISTERED** |
| 5 | Decision sensitivity summary (step 33B) | `results/RO3/decision_sensitivity/RO3_step33B_corrected_summary_20220701.csv` | `04_RESULTS/RO3/decision_sensitivity/…` | **UNREGISTERED** |

Each is documented by the registry as `documented_by="Phase 10A.10 decision-level inventory"`.

**Consequence for the manuscript:** decision-level results drawn from these five files may be presented
only as *documented partial substitutes with an explicit registration gap*. They must not be presented as
formally registered, decision-gated evidence. Registering them is a Phase-3+ change to
`src/construction/dashboard_data/registry.py`, not a packaging action.

## B. Other unregistered artifacts (7 further entries)

| Artifact identifier | Documented by | Repository path | In this package? | Status |
|---|---|---|---|---|
| Controller freeze manifest (step 36) | 8M gate manifest fingerprint | `results/RO3/ablation/RO3_step36_controller_freeze_manifest.json` | yes → `04_RESULTS/RO3/ablation/` | **UNREGISTERED** |
| Origin-level results (step 36) | 8M gate manifest fingerprint | `results/RO3/ablation/final_comparison/RO3_step36_origin_level_results.csv` | yes → `04_RESULTS/RO3/ablation/final_comparison/` | **UNREGISTERED** |
| Material-level results (step 36) | 8M gate manifest fingerprint | `results/RO3/ablation/final_comparison/RO3_step36_material_level_results.csv` | yes → `04_RESULTS/RO3/ablation/final_comparison/` | **UNREGISTERED** |
| Canonical PSLIB project JSON | 9B real-project audit phase | `results/9B_real_project_e2e/CMIDO_9B_PSLIB_C2025_02_CANONICAL.json` | **no — outside this package's scope** | **UNREGISTERED** |
| Real-project experiment output | 9B real-project audit phase | `results/9B_real_project_e2e/CMIDO_9B_REAL_PROJECT_EXPERIMENT.json` | **no — outside this package's scope** | **UNREGISTERED** |
| 9A repository inventory | 9A generalization phase | `results/9A_repository_inventory.csv` | **no — outside this package's scope** | **UNREGISTERED** |
| 9A generalization audit table | 9A generalization phase | `results/9A_real_data_generalization/CMIDO_9A_REAL_DATA_GENERALIZATION_AUDIT.csv` | **no — outside this package's scope** | **UNREGISTERED** |

The four 9A/9B artifacts belong to the real-data generalization and real-project end-to-end phases. They
were **deliberately excluded** from this publication package (which covers the frozen RO1/RO2/RO3 research
chain plus gates). This is a **recorded scope gap**, not a claim that they are absent from the repository.

## C. Registered but not adapted into dashboard evidence bundles

Both are present in `ARTIFACT_REGISTRY` (45 entries) but, per
`05_EVIDENCE/CMIDO_EVIDENCE_CONCORDANCE.md` §8 item 3, they are **not yet adapted** into dashboard
evidence bundles, so the corresponding dashboard pages render explicit unavailable states.

| Artifact ID | Registered path | Registered provenance | Status |
|---|---|---|---|
| `RO1_PRIMARY_H3_SUMMARY` | `results/forecasting/probabilistic_calibration/RO1_step26c3_primary_h3_summary.csv` | `provenance_class="DER"`, role "RO1 primary calibration", `LoadingPolicy.SAFE`, `required=False` | **REGISTERED, NOT ADAPTED** (file itself is mirrored at `04_RESULTS/RO1/probabilistic_calibration/`) |
| `EVIDENCE_8P_MANIFEST` | `results/8P_dashboard_e2e/CMIDO_8P_DASHBOARD_E2E_MANIFEST.json` | `provenance_class="DER"`, role "dashboard gate", `LoadingPolicy.SAFE`, `required=False` | **REGISTERED, NOT ADAPTED** (mirrored at `04_RESULTS/gates/8P_dashboard_e2e/`) |

## D. Integrity-chain items that are *not* gaps

For contrast, these were verified as closed on 2026-10-26 and are recorded here so the gap list is not
over-read:

- All 9 8Q source SHA-256 hashes and all 6 8R source SHA-256 hashes match their manifests
  (recomputed in the 2026-10-26 closure audit).
- 8S reconciliation: **PASS, 89/89** → `04_RESULTS/gates/8S_numerical_reconciliation/`
- 8N integrated evidence: **PASS, 13/13** → `04_RESULTS/gates/8N_integrated_evidence/`
- 8O paper evidence: **PASS, 17/17** → `04_RESULTS/gates/8O_paper_evidence/`
- 8P dashboard gate: **PASS, 20/20** (a code gate, **not** a browser run)
  → `04_RESULTS/gates/8P_dashboard_e2e/`
- Frozen scenario inputs N=1000 and N=2500 hash-verified against their recorded values
  → `06_REPRODUCIBILITY/SCENARIO_INPUT_SHA256.txt`
