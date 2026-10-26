# CMIDO — Supervisor Review Message

**From:** CMIDO research packaging
**Repository:** `Sanjayram3269/CMIDO`
**Branch:** `feat/external-data-ingestion`
**HEAD:** `ba1ee71`
**Package path:** `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/`
**Date:** 2026-10-20 (supersedes the 2026-10-14 message, which reported `main` @ `c100b47`)

## Research objective

The CMIDO project asks whether predictive uncertainty can be propagated through supply/process-duration uncertainty
to produce measurably better construction-material procurement decisions.

The framework links three stages: probabilistic price and demand forecasting, joint uncertainty propagation into
shortage and service risk, and multi-objective procurement optimization. The intended contribution is the
controlled, uncertainty-preserving chain from forecast to uncertainty to risk to decision, not a claim that any
individual component is novel.

## What is implemented and validated

The following are implemented and validated against frozen result artifacts:

- RO1 probabilistic forecasting with calibration/uncertainty evaluation.
- RO2 joint uncertainty propagation with an admissible supply/process-duration representation.
- RO3 multi-objective procurement optimization with a controlled O1/O2/O3/O4 ablation.
- Stress and robustness artifacts for declared conditions.
- A frozen dashboard roadmap through Phase 10A.15, plus the External Data ingestion workspace.

The publication-facing evidence chain has been regenerated and reconciled:

- 8Q publication tables: PASS (31/31)
- 8R publication figures: PASS (28/28)
- 8S numerical reconciliation: PASS (81/81)
- 8M controlled-evidence gate: PASS (20/20)
- 8N integrated evidence: PASS (13/13)
- 8O paper-facing package: PASS (17/17)
- 8P dashboard e2e: PASS (20/20, regenerated 2026-10-20 through its own documented entry point and
  byte-identical to the committed evidence)
- Full documented suite `python -m pytest tests/ -q`: **1130 passed, exit 0** (2026-10-20)
- Targeted dashboard + upload suites (engine, page, shell, UI, browser E2E): **270 passed, exit 0**

## Dashboard verified in a real browser (2026-10-19 → 2026-10-20)

The interactive surface was driven with Playwright/Chromium against the running Streamlit app; the
harness record is `smoke_evidence/browser_report_phase2.json` (**46/46 checks PASS**) with one
screenshot per destination.

- **CSV upload rejection — root cause.** The reported `Error: text/csv files are not allowed.` was
  never produced by the External Data uploader. The failed smoke run fed the fixture to the *first*
  `input[type=file]` in the DOM, which is the sidebar's "Load project JSON" loader declared with
  `type=["json"]`; Streamlit's frontend `file-invalid-type` check rejected it there. The External Data
  uploader (`types=("csv", "json")`, 10 MiB, unchanged) accepts the same file and profiles it.
  Both halves are now pinned by browser regression tests (External Data E2E manifest: **18/18**).
- **Navigation.** All **16** registry destinations reached and identified by their rendered page title
  (15 available + the planned `resilience_stress` panel labelled "Planned workspace").
- **Provenance & Integrity.** Opened through its real navigation label; the corrected clauses
  ("No SHA-256 digest is recomputed.", "No recorded gate, audit or reconciliation is redone.",
  "Performed at load time", "Not performed by this dashboard", "Reported, not redone,") were asserted
  against that workspace's text, with an Overview-specific negative control so a wrong page can no
  longer satisfy the check.
- **Both upload analyses end to end.** `descriptive_statistics` and `forecast_coverage` were mapped,
  validated, executed, rendered and exported; displayed values were reconciled against the persisted
  run record, the input SHA-256 (computed == recorded) and the exported result table
  (**byte-identical**). A deliberately incomplete mapping is rejected with the Run control disabled,
  and unsupported/empty/malformed files fail honestly.
- **A real export defect was found and fixed.** Persisted CSV exports were written through Windows
  text-mode translation, turning the pandas CRLF into CR-CRLF, so the on-disk result table no longer
  matched the table the page offers for download. The line terminator is now pinned and exports are
  written verbatim, with byte-fidelity regression tests for both analyses.

## Optimizer / Pareto-front convergence audit (read-only, 2026-10-20)

This is deliberately **separate from RO3.3 scenario-count convergence**, whose frozen verdict is
untouched (`primary_pass: false`, 142 failed comparisons at the primary transition,
`decision: RO3_3_EVALUATE_2500`).

Executed only the checks the repository prescribes (RO3.5 §7 integrity gates, RO3.3B frozen
decision-sensitivity design, master spec §26 hypervolume metrics). Nothing frozen was rewritten; the
audit record is `smoke_evidence/optimizer_pareto_convergence_audit.json` (8 PASS / 6 REPORTED /
1 NOT PRESCRIBED, 0 FAIL).

- **Feasibility:** RO3.5 audit re-run → **163/163 PASS**, including 64/64 independent empirical CVaR
  reconstructions of reported Z3; all 11 locked origins have `return_code 0`, 9/9 feasible epsilon
  solves on the frozen 3×3 grid and a non-empty Pareto set.
- **Frozen configuration identical across N:** model `CMIDO_RO3_4_4_v1.1_corrected_cvar_reporting`,
  HiGHS, α = 0.95, 2.5% monthly holding rate, ε-grid 3×3 for N ∈ {1000, 2500, 5000}.
- **Pareto-front stability:** cardinality 5 / 5 / 5; hypervolume recomputed from the frozen fronts with
  the frozen normalization and reference point reproduces the recorded values exactly (max |Δ| = 0.0):
  0.42122 → 0.41228 → 0.39053, i.e. −2.1% (1000→2500), −5.3% (2500→5000), −7.3% (1000→5000).
- **Objective movement:** across N, the largest relative change in min/median/max/mean of Z1, Z2, Z3
  is **3.17%**.
- **Decision stability:** on the corrected zero-safe primary metric, mean total-procurement normalized
  difference is 2.04% (1000 vs 2500), 1.35% (2500 vs 5000), 2.54% (1000 vs 5000); maxima 4.07%,
  2.96%, 5.02%.
- **No pass is claimed for convergence.** The repository prescribes *measurements* for
  hypervolume/cardinality/objective movement and records decision-level materiality thresholds as
  **NOT YET FROZEN** (`src/optimization/ro3_4_formulation_audit.py`), so those items are REPORTED /
  NOT PRESCRIBED rather than passed. Freezing those thresholds (or deciding to accept the measured
  values as the convergence evidence) is a supervisor decision.

## What is delivered in this package

- An editable draft manuscript:
  `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/01_MANUSCRIPT/CMIDO_DRAFT_MANUSCRIPT.md`
- A rendered review copy:
  `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/01_MANUSCRIPT/CMIDO_DRAFT_MANUSCRIPT_REVIEW_COPY.md`
- Publication figures and table inventory:
  `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/02_FIGURES/`
  `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/03_TABLES/`
- Supplementary pointers:
  `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/04_SUPPLEMENTARY/`
- Evidence and audit index:
  `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/05_EVIDENCE_AND_AUDITS/`
- Reproducibility statement and package manifest:
  `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/06_REPRODUCIBILITY/`
- Supervisor message and demo outline:
  `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/07_PROFESSOR_REVIEW/`
- Targeted literature screening and novelty positioning (with a 2026-10-20 verification addendum):
  `docs/CMIDO_LITERATURE_REVIEW_AND_NOVELTY.md`

The frozen publication artifacts are also available in the repository:

- `results/8Q_publication_artifacts/`
- `results/8R_publication_figures/`
- `results/8S_numerical_reconciliation/`

## Exact remaining scientific limitations

The package is a review draft, not a submission claim, because the following remain open:

1. Five decision-level artifacts are registered but not present in the artifact inventory:
   `RO3_O2_SELECTED_DECISIONS`, `RO3_O2_REALIZED_EVALUATION_SUMMARY`,
   `RO3_O4_REALIZED_EVALUATION_LEDGER`, `RO3_MULTI_ORIGIN_SUMMARY`, `RO3_DECISION_SENSITIVITY`.
2. `RO1_PRIMARY_H3_SUMMARY` and `EVIDENCE_8P_MANIFEST` are registered but not adapted into evidence bundles.
3. Reported SHA-256 fingerprints have not been recomputed and verified in this packaging session.
4. Presence checks for unregistered files are existence-only.
5. RO3 scenario-count convergence remains FAIL/UNRESOLVED under its frozen criteria (diagnosed in
   `docs/CMIDO_RO3_3_CONVERGENCE_REPORT.md`); the recorded next evaluation is 2500, then 5000 if needed.
   Not resolved here.
6. **Optimizer/Pareto convergence has no frozen acceptance thresholds.** The measurements above are
   reported as measured; decision-level materiality thresholds are explicitly "NOT YET FROZEN", so no
   optimizer-convergence pass can be claimed yet.
7. Observed-stream dates, authorship, and software-version metadata are unavailable.
8. Additional master-spec stress scenarios have no recorded results; none were fabricated.
9. Simulated/derived/scenario results are never presented as observed real-world outcomes.
10. The manuscript still carries no reference list: `docs/CMIDO_LITERATURE_REVIEW_AND_NOVELTY.md` is a
    verified targeted screening (not the formal SLR required by master spec §37), and the 2026-10-20
    addendum found no full-chain or conformal-in-construction counterexample but explicitly does not
    substitute for database-level screening.

## Package location and repository commit

- Package folder: `deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/`
- Repository commit: `ba1ee71`
- Branch: `feat/external-data-ingestion`
- The branch is synchronized with `origin/feat/external-data-ingestion` at this commit.

## Request

Could we schedule a review meeting, or could you send feedback on the draft manuscript and package structure?

I would especially value feedback on:

- whether the numerical claims are adequately tied to the frozen sources;
- whether the uncertainty and multiplicity handling is presented honestly;
- whether the open research items are acceptable for the current review stage or need earlier resolution;
- whether to freeze decision-level materiality thresholds (or accept the reported optimizer/Pareto
  measurements as the convergence evidence), and how to dispose of the unresolved RO3.3 scenario-count
  convergence;
- the target journal (the screening ranks JCEM first, Automation in Construction second);
- whether the package structure is suitable for the next revision.

## Demo outline

If useful, I can walk through:

1. the frozen evidence chain from RO1 forecasts to RO2 propagation to RO3 optimization;
2. the 8Q tables and 8R figures and their source pointers, including the new T4 stress/robustness table
   (RO3.7 + RO3.8, dual-source 8S reconciliation) and the reproducible F7 pipeline diagram (stage 8T);
3. the 8S reconciliation and what it does and does not establish;
4. the External Data workspace live: upload a CSV, map it to a declared contract, run a real analysis on the
   uploaded rows, and inspect the persisted lineage and exports (walkthrough in the root README §28) — with the
   browser evidence that every destination, the corrected provenance clauses and both upload analyses were
   verified end to end;
5. the optimizer/Pareto-front audit: feasibility, hypervolume, cardinality, objective movement and decision
   stability, and the threshold decision that is still yours to make;
6. the remaining open items and the plan to close them;
7. the manuscript draft and where the reviewer's input is most needed.

<!-- End of supervisor message. -->
