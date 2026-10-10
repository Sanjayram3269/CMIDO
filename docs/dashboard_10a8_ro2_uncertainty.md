# CMIDO Dashboard — 10A.8: RO2 Uncertainty Workspace

**Status:** complete
**Checkpoint:** `d8141bbe52202502027e8875d896d4809ff310b6` (branch `main`)
**Baseline regression at start:** 734 passed, 0 failed

This phase builds the **RO2 Uncertainty Workspace** in the existing Streamlit
dashboard, audits the RO1 metric evidence one more time, and integrates only
artifacts that genuinely exist on disk. No research metric is recomputed,
re-simulated or invented inside the dashboard.

---

## 1. Starting condition

| Check | Result |
|---|---|
| `HEAD == origin/main` at start | yes (`d8141bb`) |
| Tracked working tree clean | yes (12 untracked research artifacts preserved) |
| Baseline test suite | 734 passed, 0 failed |

---

## 2. RO1 metric-artifact audit (10A.8)

The mission required re-auditing whether any genuine RO1 CRPS, pinball-loss,
predictive-interval calibration or related artifacts exist but were not yet
registered.

### 2.1 Findings

| Metric | Genuine artifact exists? | Registered in 10A.8? |
|---|---|---|
| **CRPS** | **No.** Zero occurrences of `crps` (case-insensitive) across `results/`. | n/a — stays "Not reported" |
| **Pinball loss** | **Yes** — held-out test-split scores (q10–q90) in `RO1_step26c3_test_metrics.csv` (36 rows). Not present in the registered validation artifact. | **Yes** — `RO1_TEST_METRICS` |
| **sMAPE / MAPE** | **Yes** — Naive / SeasonalNaive baselines in `RO1_step23_test_metrics.csv` (72 rows). | **Yes** — `RO1_BASELINE_METRICS` |
| Coverage / width / Winkler | Yes (validation + test splits), already registered via `RO1_VALIDATION_METRICS`. | unchanged |
| Calibration flags | Only the already-registered calibration-score artifact; no new flag columns. | unchanged |

### 2.2 What changed for RO1

* Registry gained two entries (both `SAFE`, 200 KB caps, `DER`):
  * `RO1_TEST_METRICS` → `results/forecasting/probabilistic_calibration/RO1_step26c3_test_metrics.csv`
  * `RO1_BASELINE_METRICS` → `results/forecasting/baselines/RO1_step23_test_metrics.csv`
* `RO1Evidence` gained `test_metrics` and `baseline_metrics` lists.
* RO1 page gained one section — **"Test-split scores and baselines"** — showing
  held-out pinball / coverage / width / Winkler scores and the naive sMAPE/MAPE
  baselines, each with provenance and the explicit note that the test split is
  *not* the validation split shown elsewhere on the page.
* The honest "CRPS / pinball / sMAPE" missing card was narrowed: pinball and
  sMAPE now render from their artifacts; **CRPS remains a "Not reported" card**
  because no artifact carries it.

---

## 3. RO2 artifact inventory and schemas

11 RO2 artifacts are registered (6 new in 10A.8). Every new entry carries a
tight size cap and a declared provenance class.

| Artifact | Path | Class | Rows | Cap |
|---|---|---|---|---|
| `RO2_JOINT_PROPAGATION` | `results/8Q_publication_artifacts/T2_RO2_joint_propagation_summary.csv` | DER | 1 | 5 MB |
| `RO2_TAIL_COMPARISON` | `results/8Q_publication_artifacts/T2_RO2_tail_comparison.csv` | DER | 15 | 5 MB |
| `RO2_SERVICE_RISK` | `results/8Q_publication_artifacts/T3_RO2_service_risk_curve.csv` | SCN | 240 | 5 MB |
| `RO2_SENSITIVITY` | `results/8Q_publication_artifacts/T3_RO2_joint_independent_sensitivity.csv` | SCN | 240 | 5 MB |
| `RO2_FINAL_AUDIT` | `results/RO2/final_audit/RO2_FINAL_AUDIT_SUMMARY.json` | DER | — | 5 MB |
| **`RO2_PROPAGATION_CONFIG`** *(new)* | `results/RO2/propagation/RO2_step27d_run_config.json` | DER | — | 100 KB |
| **`RO2_PROPAGATION_SUMMARY`** *(new)* | `results/RO2/propagation/RO2_step27d_propagation_summary.csv` | DER | 96 | 500 KB |
| **`RO2_DISTRIBUTION_DECISION`** *(new)* | `results/RO2/distribution_selection/RO2_step27c2_provisional_distribution_decision.csv` | DER | 3 | 100 KB |
| **`RO2_DURATION_OBSERVED_STATS`** *(new)* | `results/RO2/data_audit/RO2_step27b_leadtime_distribution.csv` | **OBS** | 21 | 100 KB |
| **`RO2_PROPAGATION_AUDIT`** *(new)* | `results/RO2/propagation_audit/RO2_step27d1_summary.json` | DER | — | 100 KB |
| **`RO2_CONVERGENCE_SUMMARY`** *(new)* | `results/RO2/propagation_convergence_nested/RO2_step27d4_summary.json` | DER | — | 100 KB |

### 3.1 Methodology as recorded

* **Demand uncertainty representation:** RO1 marginal predictive quantiles
  (CQR-calibrated), propagated over the duration distribution. *Not* a fully
  joint future demand-path distribution — this caveat travels with the numbers.
* **Supply / duration uncertainty:** the field is **procurement-process
  duration**, drawn from paired component records (`n = 37`), **not**
  supplier-specific material lead time. Observed SLA column statistics are
  `OBS`; the empirical-vs-parametric selection (`EMPIRICAL_PRIMARY` for
  Total_DN and PO_GR_DN, `LOGNORMAL_CANDIDATE_FOR_FINAL_REVIEW` for Internal)
  is `DER` and explicitly **provisional**.
* **Joint vs separate propagation:** duration *components* (internal /
  third-party / total) are resampled as preserved pairs — genuine joint
  propagation of the duration side. Demand remains marginal, so the overall
  model is **marginal-demand / joint-duration**. Recorded decision:
  `JOINT_EMPIRICAL_PRIMARY`; `independence_assumption_supported = True` yet the
  conservative paired representation was retained.
* **Monte Carlo:** 10,000 draws per case, seed 2701, 48 material/origin cases
  (4 materials × 12 monthly origins), nested common-random-number convergence
  locked at 10k (`LOCK_10000`; max 10k→25k relative change 0.31%).
  `test_data_used = false` throughout.
* **Not propagated:** price side (`RO1_PRICE`); the recorded run covers demand
  materials only (Cement, Granite, Ready Mixed Concrete, Steel Reinforcement
  Bars). Concreting Sand appears in RO1 but not in the RO2 run.

---

## 4. What the dashboard displays

New page **RO2 · Uncertainty** (`RO2 · Uncertainty` route; navigation flipped
from PLANNED to AVAILABLE), built in
`src/construction/dashboard_ui/ro2.py` — a pure presentation module (no
Streamlit import, no engines, no file reads, no training).

Ten sections, all evidence-driven with honest unavailable states:

1. **Research question and methodology** — objective, RO1/RO3 relationship,
   materials, run configuration (draws, seed, duration pairs, horizons,
   terminology, `test_data_used`), provenance tally.
2. **Evidence status** — registered/available/not-available KPIs plus a
   per-artifact table of loader status, provenance class, row count, schema
   status. Counts hide behind "—" when nothing is loaded (never `0`).
3. **Demand uncertainty** — quantile curves (q50–q99) and table of
   demand-during-duration summaries per material at the earliest origin,
   labelled as Monte Carlo summaries, not observed outcomes.
4. **Supply and lead-time uncertainty** — observed SLA/duration statistics
   (days, with missing/negative counts shown as recorded) and the provisional
   distribution-selection table, each with "NOT supplier-specific lead time"
   and "provisional" notes.
5. **Joint propagation** — paired_n, Pearson/Spearman with p-values and
   bootstrap CI, recorded decision, the 27D.1 audit interpretation, and the
   convergence lock. **The joint claim is gated:** without the audit artifact
   the section states the result is "not validated here".
6. **Shortage and service-risk outcomes** — small-multiple shortage-probability
   curves per material and a threshold table, labelled `SCN` and explicitly
   "conditional exposure-risk curves, NOT calibrated operational service
   levels".
7. **Material and scenario comparisons** — joint-vs-independent differences
   across quantiles within the single recorded run; no cross-run or
   cross-dataset comparison, no composite ranking.
8. **Sensitivity and stress evidence** — duration tail comparison
   (observed/joint/independent) and the evaluated Monte Carlo draw-count stress
   (27D.2 hold → 27D.4 lock), marked as evaluated experiments, not hypotheticals.
9. **Uncertainty handoff to RO3** — what RO3 may consume, and an explicit
   "what is NOT claimed" block (no demonstrated decision improvement;
   safety-stock quantity is a benchmark, RO3 makes it a decision variable).
10. **Limitations and next evidence required** — the final-audit caveats
    verbatim, the 27D.1 audit limitation, and concrete missing evidence
    (supplier lead-time distributions, calibrated service levels, historical
    shortage labels, price-side propagation, RO3 decision-level validation).

---

## 5. Sections that remain unavailable and why

| Section content | State | Reason |
|---|---|---|
| CRPS anywhere | Not reported | No artifact in the repository contains CRPS (audited). |
| Calibrated service levels | Not claimed | Exposure curves are conditional MC exceedance fractions; no operational calibration evidence exists. |
| Supplier-specific lead-time distributions | Not claimed | Only procurement-process duration evidence exists. |
| Price-side (RO1_PRICE) propagation | Not claimed | Recorded 27D run covers demand materials only. |
| Any section's numbers when its artifact is missing | Honest unavailable block | Loader status MISSING/INVALID/TOO_LARGE/UNSUPPORTED propagates to an explicit unavailable state, never zero. |

---

## 6. Scientific-integrity safeguards added

* Missing evidence renders as unavailable states, never as `0` (tests assert
  `">0<" not in rendered` for the empty snapshot).
* The joint-propagation claim is **gated on the registered 27D.1 audit
  artifact**; without it the page withholds the claim.
* Procurement-process duration is never relabelled as supplier lead time; the
  disclaimer appears in the section and the caveats.
* Provisional distribution decisions are labelled provisional.
* Service-risk outputs are labelled `SCN` conditional exposure, not calibrated
  service levels.
* No composite uncertainty score, risk index or cross-material ranking is
  computed (phrase-scan guard in tests).
* The handoff section states explicitly that decision improvement is **not**
  demonstrated.
* Dataset boundary: RO2 never touches `RO1_PRICE`; the limitations section says
  so explicitly.
* Presentation purity: AST guards prove `ro2.py` performs no raw file reads
  (`open/read_csv/read_json/glob/rglob/load_artifact`), no model training
  (`fit/predict/train/...`), imports no research engines
  (`simulation/uncertainty/experiments/models/quantity`, sklearn, torch, …) and
  no Streamlit.

---

## 7. Tests

* **Focused:** `tests/construction/test_dashboard_10a8.py` — **52 tests**
  covering registry entries (safe policy, size caps, OBS/DER classification,
  expected columns vs real headers), adapter behaviour for
  valid/missing/invalid/oversized/unsupported statuses, real-artifact
  integration (representations, `test_data_used`, terminology, audit decision,
  convergence lock, distribution components), representation boundaries,
  joint-claim gating, missing-evidence-never-zero, presentation purity,
  honest-language guards, the RO1 metric audit (CRPS genuinely absent, pinball
  and sMAPE registered and separate from validation), runtime AppTest for the
  RO2 page (all sections, provenance vocabulary, no snake_case) and RO1
  regression.
* **Updated stale tests:** `test_dashboard_shell.py` (RO2 now available:
  routing, placeholder policy re-pointed to RO3, IA counts 9 available / 6
  planned, planned-destination set) and `test_dashboard_overview.py`
  (planned-placeholder check re-pointed to RO3).
* **Full regression:** `python -m pytest tests -q` → **786 passed, 0 failed**
  (734 baseline + 52 new). No assertion was weakened; the only edits were the
  stale planned-page expectations that 10A.8 intentionally changes.

---

## 8. End-to-end validation (live Streamlit, port 8502)

* Navigation round-trip: Overview → RO1 → RO2 → Schedule → Materials &
  Resources → RO2 — all render, breadcrumb resolves, sections re-render intact
  after the round-trip (all 10 headings + 4 real-evidence probes present).
* Real evidence on the live page: `PASS WITH RECORDED CAVEATS`, `LOCK 10000`,
  `JOINT EMPIRICAL PRIMARY`, `procurement-process`, paired n = 37, 10,000 draws.
* RO1 regression live: all previous sections unchanged; new "Test-split scores
  and baselines" section present with pinball and sMAPE tables
  (canvas-rendered data grids; values verified via AppTest at the block level).
* No snake_case labels in the main content region (the only DOM match was
  Streamlit's own sidebar-collapse Material-Icons ligature).
* Network: all requests 200; console: no app errors (one benign browser
  Canvas2D perf warning).
* **Light/dark:** measured computed contrast on 141 text nodes in dark mode —
  section titles ≈ 15.8:1, KPI/body text 5.22:1, lowest sample (large section
  heading) 3.3:1, which meets WCAG AA for large text. Light mode is the
  default and was verified in 10A.7.
* **Screenshot capture:** unavailable in this webview (no frames produced);
  validation was performed via accessibility snapshots, DOM evaluation and
  computed-style measurement instead. No screenshots are claimed.

---

## 9. Files

**Created**

* `src/construction/dashboard_ui/ro2.py` — RO2 presentation module (10 sections).
* `tests/construction/test_dashboard_10a8.py` — focused 10A.8 tests.
* `docs/dashboard_10a8_ro2_uncertainty.md` — this document.

**Modified**

* `src/construction/dashboard_data/registry.py` — +8 artifacts (2 RO1, 6 RO2).
* `src/construction/dashboard_data/contract.py` — `RO1Evidence` (+2 fields), `RO2Evidence` (+6 fields).
* `src/construction/dashboard_data/adapters.py` — populate the new fields.
* `src/construction/dashboard_ui/ro1.py` — test-scores section, narrowed CRPS card.
* `src/construction/dashboard_ui/navigation.py` — RO2 → AVAILABLE with route.
* `apps/cmido_dashboard.py` — RO2 dispatch branch.
* `tests/construction/test_dashboard_shell.py`, `tests/construction/test_dashboard_overview.py` — stale planned-page expectations updated.

---

## 10. Deferred to 10A.9 (RO3 workspace)

* Register and present RO3 controller/ablation/robustness evidence through the
  same 10A.2-B path (RO3 registry entries already exist; the workspace page
  does not).
* Surface any future RO1 CRPS artifact, supplier-specific lead-time
  distributions, calibrated service levels or historical shortage labels if
  research produces and registers them — the RO2 sections will render them
  without further UI work beyond registration.
* RO3 is the last remaining RESEARCH-group planned page.
