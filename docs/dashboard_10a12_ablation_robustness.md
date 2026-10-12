# Phase 10A.12 — Ablation & Robustness Workspace

**Status:** DONE. Committed on `origin/main` after the full validation battery
(focused 10A.12 suite, contract/registry/adapter/navigation suites, the 8P
publication gate, the optimization suite and the complete construction suite,
all green).

---

## 1. Starting condition

- Branch `main`, HEAD == `origin/main` == `d5f07a4` (Phase 10A.11, Real-World
  Data) verified before any edit, and re-verified after fetch.
- 10A.10 (`b8a9abe`, Procurement Decisions) and 10A.11 (`d5f07a4`) both
  committed and synchronized.
- All untracked research artifacts (`results/8N`–`9B`, scratch scripts,
  `.freebuff/`, `package-lock.json`) preserved untouched and never staged.

---

## 2. Evidence audit (before any UI was written)

Every candidate artifact's schema, source documentation and semantics were
verified against the generating scripts and specifications — not inferred from
filenames.

| Artifact | Verified semantics | Provenance |
|---|---|---|
| `T5_RO3_baseline_comparison.csv` | 5 pairwise contrasts × 7 realised metrics; recorded bootstrap 95% CI, raw Wilcoxon p, BH-adjusted q, corrected-significance flag | EST |
| `T6_RO3_ablation.csv` | Same contrasts with relative mean difference, rank-biserial, improved/worsened/tie per-origin counts | EST |
| `T5_T6_controller_descriptives.csv` | Per-controller (O1–O4) mean/median/std across the 11 locked origins | DER |
| `RO3_step37_stress_summary.csv` | 4 controllers × 4 stress cases (P50/P75/P90/P95 disruption durations 47.0/70.0/82.4/98.8 days) | SCN |
| `RO3_step37_stress_paired_changes.csv` | Per-origin paired changes vs the P50 case. **No significance test is recorded in this artifact** — descriptive only | SCN |
| `RO3_step38_holding_rate_summary.csv` | 4 controllers × 3 holding cases (H20/H30/H40 at 0.2/0.3/0.4) | SCN |
| `RO3_step38_holding_rate_controller_contrasts.csv` | Controller contrasts within each holding case. **Descriptive only — no test recorded** | SCN |
| `RO3_step38_holding_rate_sensitivity_vs_H30.csv` | Per-controller changes vs the H30 base case. **Descriptive only — no test recorded** | SCN |
| `RO3_step33_summary.json` (RO3 convergence) | Scenario sizes 100…5000; **primary transition 500→1000 did NOT pass** (142 failed comparisons, max relative change 17.65%); recorded decision `RO3_3_EVALUATE_2500`; optimisation-level convergence recorded as still required later | DER |
| `RO3_step39_final_experimental_integrity_audit.csv` | 29 recorded checks (artifact presence, row counts, locked-design adherence) | DER |
| `CMIDO_8M_GATE_MANIFEST.json` + `CMIDO_8M_GATE_AUDIT.csv` | 4 controllers, 11 locked origins, 4 common materials, inferential unit `forecast_origin`, 20/20 checks, 10 source artifacts with SHA-256 fingerprints | DER |
| `T3_RO2_joint_independent_sensitivity.csv` (RO2) | 240 recorded rows: joint vs independent duration propagation per material/origin/quantile; recorded percentage difference range −5.97% to +9.35% | SCN |
| `RO2_step27d4_summary.json` (RO2 convergence) | Recorded decision `LOCK_10000`; 48/48 cases stable at the lock size; max relative change 0.67% (5k→10k) | DER |

The O1–O4 2×2 design and the contrast attribution plan were verified from
`docs/CMIDO RO3.6 — Controlled Baseline and 2×2 Ablation Specification v1.0.md`
(O1 deterministic+heuristic, O2 deterministic+optimisation, O3
probabilistic+heuristic, O4 probabilistic+optimisation = CMIDO). The stress and
holding-rate case definitions were verified from the generating scripts
(`ro3_7_stress_duration_sensitivity.py`, `ro3_8_robustness_holding_rate.py`).

**RO1 evidence was examined and deliberately excluded**: RO1's paired
comparison and calibration artifacts concern forecast accuracy, not decision
robustness, so they do not contribute to this workspace's narrative. RO2
sensitivity and convergence were included because they directly quantify the
robustness of the assumptions the optimisation consumes.

---

## 3. Contract / registry / adapter changes

### Registry (`registry.py`) — 5 new entries

- `ABLATION_8M_GATE_MANIFEST` (JSON, SAFE, DER) and `ABLATION_8M_GATE_AUDIT`
  (CSV, SAFE, DER, columns `check/passed/detail`) — the ablation evidence gate.
- `RO3_STRESS_PAIRED`, `RO3_HOLDING_CONTRASTS`, `RO3_HOLDING_SENSITIVITY`
  (CSV, SAFE, SCN) — the descriptive robustness artifacts, each with an
  explicit column contract and descriptions stating that no significance test
  is recorded in them.

Total registered artifacts: 40 → 45.

### Contract (`contract.py`)

- `RO3Evidence` gains `ablation_gate_manifest`, `ablation_gate_audit`,
  `stress_paired`, `holding_contrasts`, `holding_sensitivity` (all with empty
  defaults so missing evidence renders as unavailable, never zero).
- **Dead abstraction resolved**: `ProcurementDecisionsEvidence` and the
  never-populated `snapshot.procurement` field were removed. Nothing in `src/`,
  `apps/` or `tests/` ever wrote or read them — the 10A.10 page consumes the
  decision-level fields of `RO3Evidence` directly. The 10A.11 report flagged
  this as dead weight; it is now gone, with a regression test locking its
  absence.

### Adapter (`adapters.py`)

- `adapt_ro3_evidence` wires the five new artifacts with the established
  AVAILABLE-and-DataFrame guards; missing or invalid artifacts leave the
  fields empty and their provenance is still attached.

---

## 4. What is displayed

The page (`src/construction/dashboard_ui/ablation_robustness.py`, route
`page/ablation_robustness`, EVIDENCE group) renders thirteen sections:

1. **Overview** — recorded design KPIs (controllers, locked origins, common
   materials, gate checks) from the 8M manifest, plus what the page reports.
2. **Artifact inventory** — all 14 workspace artifacts with recorded status,
   provenance class, row count and schema outcome; non-AVAILABLE artifacts get
   explicit state panels.
3. **Experimental design and evidence gate** — recorded design properties
   (humanised), the 20 gate checks, and the 10 source-artifact fingerprints
   (paths and project root deliberately dropped).
4. **Statistically tested controller comparisons** — direction-aware findings
   per contrast (significance-gated, intervals shown) and the full T5 table.
5. **2×2 component ablation** — T6 with relative effect sizes, rank-biserial
   and per-origin direction counts.
6. **Controller descriptives** — a recorded cost-service positioning scatter
   (no ranking, no composite score) and the descriptive table.
7. **Stress testing (scenario-based)** — recorded service-level-under-stress
   chart, the case table and the paired-change table (labelled descriptive).
8. **Holding-rate robustness** — outcomes, within-case contrasts and
   sensitivity vs H30 (all labelled descriptive).
9. **Upstream assumption sensitivity (RO2)** — coverage counts and the range
   of the already-recorded joint-vs-independent percentage column, plus a
   preview table.
10. **Convergence diagnostics** — RO3 and RO2 convergence, reported exactly as
    recorded (including the recorded primary-transition failure).
11. **Final experimental integrity audit** — check outcomes with paths
    suppressed, plus what the audit does and does not establish.
12. **How to read this evidence** — the evidential tiers (statistically
    tested / descriptive only / not inferable) and the standing limitations.
13. **Handoff** — where this evidence is used in the rest of the dashboard.

---

## 5. Scientific-integrity safeguards

- **No universal superiority.** `build_contrast_findings` is direction- and
  significance-aware: a contrast whose significant metrics move in both
  directions (e.g. O4 vs O1: higher cost *and* higher service) is labelled a
  recorded **trade-off** with "no composite score is computed and no overall
  winner is declared".
- **Non-significance ≠ equivalence.** Every contrast explicitly lists metrics
  that did not reach corrected significance and states "this is not evidence
  of equivalence between the arms".
- **Tested vs descriptive kept apart.** T5/T6 are reported with their recorded
  intervals and BH-corrected flags; the stress paired changes, holding
  contrasts and holding sensitivity say "the artifact records no significance
  test" in their captions; the interpretation section names all three
  evidential tiers.
- **Scenario ≠ observation.** Stress and holding-rate sections carry SCN
  provenance and state that they are controlled perturbations, not observed
  disruptions or observed economics.
- **Recorded failure survives.** The RO3 scenario-count convergence section
  reports "Primary transition passed its threshold: No", the 142 failed
  comparisons, and the recorded later requirement — it is not smoothed over.
- **No hard-coded science.** Every displayed number flows through the 10A.2-B
  snapshot contract. Controller definitions and contrast attributions are
  design labels sourced from the documented RO3.6 specification.
- **Missing evidence is explicit.** Each section degrades to an artifact-state
  panel with a "why this matters" note; the design KPIs show `—`, never `0`.
- **Hygiene.** No raw paths (the 8M manifest's `project_root` and source
  paths are dropped; audit details are path-suppressed via the shared
  helper), no hex colours, no inline styling (light/dark inherited from the
  design system), no snake_case labels in rendered text (a first-pass bug
  that lowercased "CVaR_0.95" into a snake token was caught by the render
  probe and fixed).
- The 169 MB / 338 MB raw scenario ledgers remain `NEVER`-loaded and are
  asserted blocked in the test suite.

---

## 6. Tests

`tests/construction/test_dashboard_10a12.py` — **67 tests** covering:

- module import purity (no research engine, no Streamlit), navigation
  registration (AVAILABLE, route, group, phase), the stale
  `resilience_stress` phase label, and the removed dead abstraction;
- registry entries and blocked ledgers; adapter mapping, missing and invalid
  behaviour, provenance attachment;
- provenance curation, status indexing (INVALID preserved verbatim), artifact
  inventory rows;
- design cards/rows (humanised inferential unit, honest empties), gate audit
  and fingerprint rows (paths dropped, non-bool passes read as missing);
- comparison/ablation rows (recorded statistics, effect sizes), contrast
  findings (significance gating, non-equivalence language, trade-off
  surfacing, snake-free output);
- stress/holding builders, convergence builders (recorded failure survives,
  tokens humanised), RO2 sensitivity summary/preview, integrity rows
  (paths suppressed);
- charts (one trace per controller, empty-safe);
- source hygiene (no paths, no hex, no inline CSS, integrity language
  present);
- **AppTest runtime**: the live page renders exception-free with all sections,
  states the integrity rules, reports the recorded convergence failure,
  labels stress as scenario-based, and leaks neither snake_case nor
  filesystem paths.

### Validation results

| Suite | Result |
|---|---|
| Focused `test_dashboard_10a12.py` | **67 passed** |
| Shell + contract + registry + adapters + 10A.9/10A.10/10A.11 | **220 passed** |
| `tests/optimization/` incl. 8P publication gate | **24 passed** |
| Complete `tests/construction/` | **951 passed** (884 baseline + 67 new; +0 lost) |

**UI validation**: AppTest runs the real dashboard with the actual on-disk
artifacts — the page renders exception-free (66k characters of rendered
content), all thirteen sections present, zero snake-case leaks, zero path
leaks, and every recorded value (35 comparison rows, 20 ablation rows, 48
paired rows, 27 contrast rows, 24 sensitivity rows, 29 audit rows) reconciles
with the source files.

---

## 7. Navigation / IA changes

- `ablation_robustness`: PLANNED → **AVAILABLE**, route
  `page/ablation_robustness`, description updated to name the evidence scope.
  Navigation is now **13 available / 2 planned** (module docstring and shell
  tests updated).
- `resilience_stress`: stale `future_phase="Phase 10A.10"` corrected to
  "Beyond Phase 10A.13" — 10A.10 delivered Procurement Decisions only, and no
  current phase is committed to this workspace. The label now says so
  honestly.
- App dispatch (`apps/cmido_dashboard.py`): new `page/ablation_robustness`
  branch with the established honest-fallback error state.

---

## 8. Files created and modified

**Created**

- `src/construction/dashboard_ui/ablation_robustness.py` — the workspace page.
- `tests/construction/test_dashboard_10a12.py` — the focused test suite.
- `docs/dashboard_10a12_ablation_robustness.md` — this report.

**Modified**

- `src/construction/dashboard_data/registry.py` — 5 new artifact entries.
- `src/construction/dashboard_data/contract.py` — 5 new `RO3Evidence` fields;
  dead `ProcurementDecisionsEvidence`/`snapshot.procurement` removed.
- `src/construction/dashboard_data/adapters.py` — wire the 5 new artifacts.
- `src/construction/dashboard_ui/navigation.py` — page AVAILABLE, stale
  `resilience_stress` label fixed, docstring counts updated.
- `apps/cmido_dashboard.py` — import and dispatch branch.
- `tests/construction/test_dashboard_shell.py` — IA counts (13/2), planned-id
  set, stale comments refreshed.

No scientific artifact under `results/` was modified.

---

## 9. Known limitations

- The `RO3_step36_*` origin/material-level ablation results and the controller
  freeze manifest referenced by the 8M manifest remain unregistered (the gate
  manifest/audit carry their fingerprints instead); execution-level detail is
  manifest-level only.
- The stress paired-changes, holding contrasts and holding sensitivity
  artifacts record **no** significance tests, so all stress/holding statements
  remain descriptive. Registering inferential stress evidence would require
  new research outputs, not dashboard work.
- The recorded RO3 scenario-count convergence failure (primary transition)
  constrains how strongly the optimisation results may generalised beyond the
  evaluated scenario count; the page surfaces this rather than resolving it —
  resolution is a research-side task.
- RO1 forecast-robustness evidence is not presented here (out of scope for a
  decision-robustness narrative); if wanted, it should get its own registered
  section rather than being folded into this page.
- Screenshot capture is unavailable in this environment; light/dark
  compatibility is guaranteed structurally (component-layer-only rendering,
  verified by test).

---

## 10. Scope of 10A.13

10A.13 is the **Provenance & Integrity** workspace (`provenance_integrity`,
EVIDENCE group, planned, future phase 10A.13) covering registry-level
artifact provenance, loading policies and the cross-component integrity
audit. 10A.13 is **not** started by this phase.
