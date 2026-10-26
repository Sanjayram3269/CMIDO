# CMIDO — Known Scientific Limitations (frozen disclosure set)

Generated 2026-10-26 during the publication-package build. Every statement below is taken from a
frozen repository artifact listed beside it. **Nothing here was relaxed, softened or removed for
packaging purposes.** These limitations must travel with any use of this package.

---

## 1. RO1 primary-horizon results are mixed / descriptive — no universal ML superiority claim

- Frozen paired statistical evaluation at the primary horizon h=3 reports CQR better on Winkler-80 for
  **6 of 9** series, BH-adjusted p<0.05 in **2 of 9**, mean series-level Δ Winkler-80 = **−17.15**
  → `04_RESULTS/RO1/probabilistic_calibration/analysis_26c3f/RO1_step26c3f_statistical_report.txt`
- Against conventional statistical probabilistic baselines at h=3, the ML-CQR comparison goes the other
  way: mean Δ Winkler-80 = **+110.12**, ML-CQR better **2/9**, worse **7/9**
  → `04_RESULTS/RO1/final_probabilistic_comparison/RO1_step26c3g_primary_h3_aggregate.csv`
- Frozen verdict wording: "**MIXED DESCRIPTIVE EVIDENCE**"; "This analysis is descriptive and does not
  establish statistical significance or overall model superiority."
  → `04_RESULTS/RO1/probabilistic_calibration/analysis_26c3e/RO1_step26c3_preliminary_verdict.txt`
- Integrity audit PASS: 666 paired test rows, test set untouched before frozen CQR application
  → `04_RESULTS/RO1/final_probabilistic_comparison/RO1_step26c3h_final_integrity_audit.json`

**Consequence:** the manuscript must not claim ML/conformal superiority over statistical baselines.

## 2. RO2 procurement-process duration is a proxy, not supplier-specific lead time

- Recorded caveat: "RO2 uses procurement-process duration / procurement-duration proxy, not
  supplier-specific material lead time."
  → `04_RESULTS/RO2/final_audit/RO2_FINAL_AUDIT_SUMMARY.json`

## 3. RO2 service-risk curves are conditional model estimates, not calibrated operational service levels

- Recorded caveat: "Service-risk curves are conditional exposure-risk curves and are not empirically
  calibrated operational service levels." Same file also records: the 37 paired observations preserve
  observed component pairing **but do not prove statistical dependence**; RO2 does not establish
  supplier-disruption probabilities; RO2 does not establish historical shortage labels; RO1 supplies
  marginal predictive quantiles rather than a fully joint future demand-path distribution, so 27D is a
  **marginal-demand / joint-duration** propagation model; and the 27D safety-stock quantity is a
  benchmark/interpretability quantity only.
  → `04_RESULTS/RO2/final_audit/RO2_FINAL_AUDIT_SUMMARY.json`

## 4. RO3.3 and RO3.3A scenario-count convergence remain FAIL / UNRESOLVED under frozen criteria

- RO3.3 status line: "**FAIL under the frozen criteria — convergence UNRESOLVED at every ladder rung
  through 5,000 scenarios.**" Failed comparisons out of 616: 276 (100→250), 178 (250→500),
  **142 (500→1000, primary, max rel 0.176471)**, 111 (1000→2500), 52 (2500→5000).
  → `05_EVIDENCE/CMIDO_RO3_3_CONVERGENCE_REPORT.md`
- The domain-aware variant RO3.3A also fails at every rung (82 / 65 / 27 failures).
  "No existing evaluation of the frozen ladder passes under any recorded criterion set."
- Frozen decisions were **not** edited: `RO3_step33_decision.txt` = `RO3_3_EVALUATE_2500`,
  `RO3_step33A_decision.txt` = `RO3_3A_EVALUATE_2500`
  → `04_RESULTS/RO3/scenario_convergence/`
- Recorded diagnosis (retained, not softened): demand and price marginals are converged (0/88 failures
  each); duration means show textbook 1/√N decay; **q90 duration quantiles are grid-locked by the
  discrete 37-row duration support (18 ↔ 20 days), so the ≤2% relative threshold is unattainable for
  such cases at any N with this representation**; exposure tails converge slowest.

**Consequence:** the manuscript must not claim scenario-count convergence of the RO3 duration/exposure
diagnostics.

## 5. The optimizer was not rerun in the latest verification

- The optimizer/Pareto audit is a **read-only** re-execution of prescribed integrity gates over frozen
  artifacts: 163/163 gates PASS including 64 independent empirical CVaR reconstructions; hypervolume
  recomputed from the frozen fronts reproduces the recorded RO3.3B values with **max |Δ| = 0.0**;
  cardinality 5/5/5; objective movement ≤ 3.17%; decision stability 1.35–2.54% mean.
  → `05_EVIDENCE/smoke_evidence/optimizer_pareto_audit_stdout.txt`
- The 11 origin execution records it reads were produced earlier (2026-09-14) and were **reused, not
  regenerated**: `results/RO3/multi_origin/execution_{20220701..20230501}.json`, each return_code 0 with
  9/9 feasible epsilon solves on the frozen 3×3 grid.
  → mirrored at `04_RESULTS/RO3/multi_origin/`

**Consequence:** "optimizer/Pareto validated" means *integrity gates re-checked over frozen outputs*,
not a fresh optimization run.

## 6. Decision-level materiality thresholds remain unfrozen

- Recorded as `[NOT PRESCRIBED] decision_level_materiality_threshold: Frozen decision-level materiality
  thresholds do not exist (ro3_4_formulation_audit.py: "Decision-level materiality thresholds: NOT YET
  FROZEN"), so decision stability is reported as a measurement and no pass is claimed."
- Likewise hypervolume-movement and objective-movement have **no prescribed acceptance thresholds**, so
  they are REPORTED, not passed.
  → `05_EVIDENCE/smoke_evidence/optimizer_pareto_audit_stdout.txt`
- The uncorrected relative quantity metric in `RO3_step33B_pairwise_sensitivity_*.csv` is **unusable**
  (mean relative quantity difference ≈ 1.94e+08 from near-zero denominators); only the corrected
  zero-safe metric in `RO3_step33B_corrected_summary_*.csv` may be quoted.
  → `04_RESULTS/RO3/decision_sensitivity/`

## 7. Five decision-level artifacts remain unregistered

Registry state re-checked 2026-10-26 in `src/construction/dashboard_data/registry.py`: 45
`ARTIFACT_REGISTRY` entries; the five decision-level artifacts are **not** among them and remain in
`KNOWN_UNREGISTERED_ARTIFACTS`. Their sources exist on disk and are mirrored in this package, but they
are **not** formally registered or decision-gated.
→ full list with exact paths in `08_INDEX/REGISTRY_GAPS.md`

## 8. Formal SLR, verified bibliography, citation-to-claim map and journal choice remain outstanding

- The literature work is **targeted screening to support the professor review — not the formal
  systematic literature review (SLR) required by the master specification §37**; no Scopus/WoS
  screening was performed.
  → `05_EVIDENCE/CMIDO_LITERATURE_REVIEW_AND_NOVELTY.md`
- The manuscript's reference section states references are intentionally not invented and that the
  final reference list must be assembled and checked against the claims it supports.
  → `01_MANUSCRIPT/CMIDO_DRAFT_MANUSCRIPT.md` §13
- No citation-to-claim mapping exists in the repository (see `08_INDEX/CLAIM_REGISTER.md`, "What this
  register does NOT contain").
- No journal has been selected; Cluster C in the literature review lists recent precedents only.

---

## Additional limitations carried from the package build itself

9. **Frozen scenario-ladder inputs are not in this package** and three of the six (N=1000/2500/5000,
   ≈574 MB) are **not tracked in Git at all**. Their hashes are recorded in
   `06_REPRODUCIBILITY/SCENARIO_INPUT_SHA256.txt`; the N=5000 hash is **newly recorded and has no prior
   authoritative counterpart**. Full reproduction requires those files or an authorised regeneration.
10. **The manuscript PDF in this package is newly built** from the current working-tree Markdown and
    therefore contains the citation clusters that the previously committed PDF did not. The previously
    committed PDF in the repository was **not** modified.
11. **Browser end-to-end evidence in `05_EVIDENCE/external_data_e2e/` predates the current HEAD**
    (manifest dated 2026-10-20 vs HEAD 2026-10-22) and `e2e_01_landing_empty_state.png` /
    `e2e_02_preview_profile.png` are newer than the manifest that describes them. It is **REPORTED BUT
    NOT REPRODUCED** in this phase. No browser end-to-end coverage exists for the project-upload →
    Overview-metric refresh behaviour.
12. **`05_EVIDENCE/smoke_evidence/full_test_suite.txt` reports 1130 passed** (2026-10-20) against a
    suite that now collects 1140 tests. That number is historical, not a result for the current HEAD.
13. **`data/projects/cmido_project_a.json` is byte-identical to the tracked demo project**
    (`CMIDO-DEMO-001` "Residential Building Demo"); it is included in `07_SUPPLEMENTARY/fixtures/`
    only because the upload regression tests reference that path.
