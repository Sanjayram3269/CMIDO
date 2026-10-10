# CMIDO Dashboard — 10A.9: RO3 Optimization Workspace

**Status:** complete
**Checkpoint at start:** `e0fc4e0062579cbc89ee5e4b702b5f0d91e36dbe` (branch `main`)
**Baseline regression at start:** 786 passed, 0 failed
**Baseline regression at end:** 820 passed, 0 failed (+34 focused 10A.9 tests)

This phase builds the **RO3 Optimization Workspace** in the existing Streamlit
dashboard. It is a presentation-only phase: every displayed number flows through
the 10A.2-B data contract (`RO3Evidence`), the artifact registry and its pure
adapters. No optimisation, simulation or statistical result is recomputed,
re-solved or invented inside the dashboard.

---

## 1. Starting condition

| Check | Result |
|---|---|
| Branch | `main` |
| `HEAD` at start | `e0fc4e0062579cbc89ee5e4b702b5f0d91e36dbe` |
| Baseline test suite | 786 passed, 0 failed |
| Untracked research artifacts preserved | yes (14 untracked paths untouched) |

---

## 2. RO3 artifact inventory

Ten RO3 artifacts are registered. Paths are relative to the repository root and
resolve through the registry only — `ro3.py` performs no filesystem access.

| Artifact id | Source path | Type | Policy | Provenance | Rows loaded |
|---|---|---|---|---|---|
| `RO3_BASELINE_COMPARISON` | `results/8Q_publication_artifacts/T5_RO3_baseline_comparison.csv` | CSV | SAFE | EST | 35 |
| `RO3_ABLATION` | `results/8Q_publication_artifacts/T6_RO3_ablation.csv` | CSV | SAFE | EST | 20 |
| `RO3_CONTROLLER_DESCRIPTIVES` | `results/8Q_publication_artifacts/T5_T6_controller_descriptives.csv` | CSV | SAFE | DER | 4 |
| `RO3_STRESS_SUMMARY` | `results/RO3/ablation/RO3_7_stress/RO3_step37_stress_summary.csv` | CSV | SAFE | SCN | 16 |
| `RO3_ROBUSTNESS_SUMMARY` | `results/RO3/ablation/RO3_8_robustness/RO3_step38_holding_rate_summary.csv` | CSV | SAFE | SCN | 12 |
| `RO3_CONVERGENCE_SUMMARY` | `results/RO3/scenario_convergence/RO3_step33_summary.json` | JSON | SAFE | DER | 9 keys |
| `RO3_FINAL_AUDIT` | `results/RO3/ablation/RO3_9_final_audit/RO3_step39_final_experimental_integrity_audit.csv` | CSV | SAFE | DER | 29 |
| `RO3_PARETO_ALL_ORIGINS` | `results/RO3/multi_origin/RO3_step35_pareto_all_origins_N2500.csv` | CSV | SAFE | DER | 64 |
| `RO3_PARETO_DECISIONS` | `results/RO3/multi_origin/RO3_step35_decisions_all_origins_N2500.csv` | CSV | SAFE | DER | 3072 |

Eleven provenance entries reach the workspace: the nine loaded artifacts above,
plus two `TOO_LARGE` entries for the blocked raw scenario ledgers (§2.1).

### 2.1 Raw scenario ledgers are blocked by policy

The two large raw scenario-generation ledgers are registered **explicitly so
that policy can forbid them**. Both carry `LoadingPolicy.NEVER`, and
`load_artifact()` short-circuits on that policy *before* the file-existence
check, so the file is never opened:

| Artifact id | Source path | Size on disk | Policy | Loader result |
|---|---|---|---|---|
| `RO3_SCENARIOS_2500_RAW` | `results/RO3/scenario_generation/RO3_step32_scenarios_2500.csv` | 168,946,676 bytes (~161 MiB) | `NEVER` | `TOO_LARGE`, `data=None`, schema `BLOCKED_BY_POLICY` |
| `RO3_SCENARIOS_5000_RAW` | `results/RO3/scenario_generation/RO3_step32_scenarios_5000.csv` | 338,474,450 bytes (~323 MiB) | `NEVER` | `TOO_LARGE`, `data=None`, schema `BLOCKED_BY_POLICY` |

Verified empirically in §8.1. Registering them is deliberate: it records their
existence and blocked status in provenance rather than hiding them, while the
`NEVER` policy guarantees no byte is read.

`ro3.py` itself contains no reference to these paths: a grep for the raw ledger
filenames and for `read_csv`/`glob`/`rglob` over the module returns no matches,
and the live DOM audit finds no snake_case leak tokens (§10).

---

## 3. Schema and provenance findings

### 3.1 Pareto evidence (DER)

`RO3_PARETO_ALL_ORIGINS` columns:
`forecast_origin, pareto_id, Z1, Z2, Z3, eps2, eps3, runtime_sec, scenario_count`.

64 nondominated points across 11 forecast origins (2022-07-01 → 2023-05-01),
solved by the epsilon-constraint method. Objective directions, as formulated:

- **Z1** = expected procurement + holding cost — minimise
- **Z2** = expected total shortage quantity — minimise
- **Z3** = CVaR₀.₉₅ of total shortage quantity — minimise

All three are minimisation objectives. The page states this explicitly on every
Pareto view; service level is reported alongside as a realised outcome and is
labelled "reported (higher=better)" — it is **not** an optimised objective.

### 3.2 Procurement decisions (DER)

`RO3_PARETO_DECISIONS` columns:
`forecast_origin, pareto_id, material, month_ahead, q`.

3,072 rows = per-Pareto-solution, per-material monthly-ahead procurement
quantity `q(i,t)`. The artifact contains **quantities only**. It does not contain
supplier-selection `y(i,s,t)`, safety stock `ss(i,t)`, supplier allocation or
explicit capacity/inventory constraint values, so those are shown as honest
unavailable states rather than implied. This respects the rule that a variable's
existence in the mathematical formulation is not evidence that it is available
as an artifact field.

### 3.3 Baseline / controller comparison (EST)

35 rows. Comparisons: `O2_vs_O1`, `O3_vs_O1`, `O4_vs_O1`, `O4_vs_O2`, `O4_vs_O3`.
Metrics: realised procurement+holding cost, total shortage, monthly CVaR₀.₉₅
shortage, total procurement quantity, mean ending inventory, procurement events,
service level.

Each row carries `newer_mean`, `base_mean`, `mean_difference_newer_minus_base`,
bootstrap CI bounds, Wilcoxon p and a Benjamini-Hochberg corrected
`significant_bh_0_05` flag. Non-significant contrasts are reported as such.

### 3.4 2×2 controller design

The recorded conditions (from the RO3.6 ablation specification) are:

| Controller | Information | Control |
|---|---|---|
| O1 | Deterministic | Heuristic (baseline) |
| O2 | Deterministic | Optimisation |
| O3 | Probabilistic | Heuristic |
| O4 | Probabilistic | Optimisation (= CMIDO) |

The five contrasts are attributed per-pair, never as a single ranking.

### 3.5 Ablation, stress, robustness, convergence, audit

- **Ablation** (EST, 20 rows) — same five contrasts, relative mean differences
  with BH-corrected significance.
- **Stress** (SCN, 16 rows) — factor perturbations. Scenario-defined, not
  observed disruptions.
- **Robustness** (SCN, 12 rows) — holding-rate sensitivity. A sensitivity
  result is labelled as such and is not relabelled proof of robustness.
- **Convergence** (DER, 9 keys) — scenario-count convergence decision, primary
  pass/fail, and later-stage maximum relative change.
- **Final audit** (DER, 29 rows) — integrity gate checks, surfaced as a
  passing/total KPI.

---

## 4. What is displayed, and why

`src/construction/dashboard_ui/ro3.py` builds ten section groups (A–J),
returned by `build_page_content()` in display order:

| # | Section | Backed by | Gating |
|---|---|---|---|
| A | Research objective & methodology | static + registry counts | always |
| B | Optimization evidence snapshot | all 11 provenance entries | KPI values become `—` when nothing loaded |
| C | Procurement decision outputs | `RO3_PARETO_DECISIONS` | unavailable state when absent |
| D | Objective & trade-off analysis | `RO3_BASELINE_COMPARISON` | per-metric direction + units |
| E | Pareto evidence | `RO3_PARETO_ALL_ORIGINS` | Plotly figure only when points exist |
| F | Baseline & controller comparison | `RO3_BASELINE_COMPARISON` | per-contrast, no ranking |
| G | Ablation evidence | `RO3_ABLATION` | significance gated on artifact |
| H | Robustness & stress | stress + robustness summaries | SCN labels preserved |
| I | RO2 → RO3 uncertainty handoff | final audit + convergence | states RO2 linkage only when recorded |
| J | Decision-level validation & limitations | baseline comparison + static caveats | explicit unvalidated list |

Every KPI count is derived from real registered evidence. No placeholder zeroes.

---

## 5. Controller and baseline compatibility

Comparisons are restricted to the recorded within-protocol contrasts. The page
uses the source-defined phrasing — "lower reported cost in this experiment",
"higher reported service measure under this configuration" — and never asserts
that O4 (or any controller) is universally superior.

The recorded findings are genuinely mixed, and the page surfaces them as mixed:

- **O2 vs O1** — optimisation under deterministic information lowers realised
  cost (−18.7%, BH-significant) but raises realised shortage (+13.5%,
  BH-significant) and lowers service level; the CVaR₀.₉₅ shortage difference is
  **not** BH-significant (q=0.146).
- **O4 vs O2** — adding uncertainty-aware optimisation raises cost (+176.3%)
  while cutting shortage (−72.3%) and raising service level (+110.9%), all
  BH-significant; the CVaR₀.₉₅ difference is again **not** BH-significant
  (q=0.273).
- **O4 vs O3 / O4 vs O1** — cost rises while shortage falls and service level
  rises, all BH-significant, including CVaR₀.₉₅ (q=0.019 and q=0.005).

Every CVaR₀.₉₅ contrast is directionally a small reduction, but only O4 vs O3
and O4 vs O1 clear the BH-corrected threshold. The page reports the recorded
flag rather than inferring significance from point estimates.

No composite score is constructed anywhere in the module.

---

## 6. Decision-level validation status

Supported: within the locked evaluation protocol and origins, the recorded
contrasts show statistically corrected differences on several metrics.

Explicitly **not** claimed:

- Real-world deployment performance (all outcomes are simulation realisations).
- Supplier-specific lead time (optimisation uses procurement-process duration,
  consistent with RO2's duration≠lead-time caveat).
- Historical shortage calibration (shortage labels are simulated exposures).
- Cross-protocol generalisation beyond the locked window and materials.
- Universal optimality of any controller.

---

## 7. Scientific-integrity safeguards

Encoded in `ro3.py` and enforced by tests:

1. Missing evidence renders as an explicit unavailable state, never zero.
2. Objective direction and units travel with every metric; cost from one
   experiment is never compared with an incompatible metric or configuration.
3. Pareto points are the solver's recorded nondominated set — never
   reclassified, never manufactured from unrelated aggregates, never shown
   without objective definitions.
4. Stress/robustness outputs stay SCN; scenarios are never labelled
   observations, and sensitivity is not relabelled proof of robustness.
5. No composite score, no cross-experiment ranking, no universal-optimum claim.
6. Statistical significance is only stated where BH-corrected flags record it.
7. No research-engine imports, no filesystem access, no globbing in `ro3.py`.
8. Raw scenario ledgers are registered with `LoadingPolicy.NEVER`, so the
   loader returns `TOO_LARGE` without opening them.

### 7.1 Audit-detail path suppression (new in 10A.9)

The integrity audit records absolute filesystem paths in some `detail` fields
(e.g. `D:\CMIDO\results\RO2\data_audit\RO2_step27b4_admissible_modelling_view.csv`).
Displaying them would leak raw repository layout into the research page. The new
`_clean_audit_detail()` helper suppresses path-like details while preserving
genuine values (`37`, `163/163`, `n=2500 scenarios`, `P50=47`). The check label
(e.g. "RO2 27B.4 file exists") still records what was verified.

This was found by a live DOM audit: after the workspace rendered, three
snake_case tokens (`data_audit`, `admissible_modelling_view`, and a
filename-list detail) were visible in the page text. All are now suppressed;
a re-check of the live DOM returns zero snake_case leak tokens.

---

## 8. Loading policies and safeguards

- Registry-driven loading exclusively; `ro3.py` reads only `RO3Evidence`.
- Declared `max_safe_bytes` limits respected (Pareto 500 KB, decisions 2 MB).
- `LoadingPolicy.NEVER` blocks the raw scenario ledgers before any file access.
- `AVAILABLE` / `MISSING` / `INVALID` / `TOO_LARGE` / `UNSUPPORTED` states
  preserved end to end.
- Raw-file access stays out of presentation modules.
- No second calculation pipeline; no artifact discovery or globbing.

### 8.1 Raw-ledger blocking verified empirically

```text
RO3_SCENARIOS_2500_RAW -> ArtifactStatus.TOO_LARGE | data is None: True
RO3_SCENARIOS_5000_RAW -> ArtifactStatus.TOO_LARGE | data is None: True
```

Both files are present on disk at ~161 MiB and ~323 MiB, yet `data is None`,
confirming no bytes were read.

---

## 9. Tests

`tests/construction/test_dashboard_10a9.py` — **34 focused tests** covering:

1. Registry entries and loading policies for all RO3 artifacts.
2. Valid / missing / invalid / oversized artifact handling.
3. Schema validation and missing-column behaviour.
4. Provenance classifications (EST / DER / SCN).
5. No raw scenario-ledger loading; no filesystem access in `ro3.py`.
6. Procurement decision fields shown only when supported.
7. Objective direction and units preserved.
8. Pareto visualisation gated on valid evidence.
9. Controller/baseline comparisons respecting compatibility constraints.
10. Ablation and stress-test claims gated on actual artifacts.
11. No fabricated values or arbitrary rankings.
12. Missing values remaining unavailable rather than becoming zero.
13. No dataset-boundary violations.
14. No engine imports or research calculations in `ro3.py`.
15. Complete / partial / absent evidence rendering.
16. Correct navigation and breadcrumbs.
17. RO1 and RO2 regressions unchanged.
18. Light/dark theme compatibility (no literal hex colours; theme tokens only).

Two pre-existing tests were updated rather than weakened: they used
`ro3_optimization` as their "planned page" exemplar, which is now AVAILABLE.
Both were repointed at `procurement_decisions` (still planned, Phase 10A.10):

- `tests/construction/test_dashboard_shell.py` — `TestPlaceholderPolicy`,
  `TestNoFabricatedResearchDataInShell`, `TestIntendedIACoverage`
  (available/planned counts corrected 9/6 → 10/5).
- `tests/construction/test_dashboard_overview.py` —
  `test_planned_page_still_shows_honest_placeholder`.

### 9.1 Verification sequence

| Step | Result |
|---|---|
| Focused 10A.9 tests | 34 passed |
| RO1 / RO2 regression | passed (unchanged) |
| Dashboard contract, registry, adapter, UI tests | passed |
| 8P dashboard gate (`tests/optimization/test_8p_dashboard_e2e_gate.py`) | 3 passed |
| Full repository regression | **820 passed, 0 failed** |

---

## 10. Live browser validation

Streamlit served at `http://localhost:8509` (`apps/cmido_dashboard.py`, fresh
process). Navigation path Overview → RO1 → RO2 → RO3 → Schedule → Materials &
Resources → RO3 exercised.

| Check | Result |
|---|---|
| RO3 renders without exceptions | yes |
| Breadcrumb + navigation group | `Overview → Research → RO3 · Optimization`, RESEARCH group, single destination |
| All 10 sections render | A–J present, verified via DOM text |
| Metrics agree with artifacts | Pareto 64 points / 11 origins, decisions 3,072 rows, audit 29 checks — matched to §2 |
| Unavailable evidence explained | supplier allocation, safety stock, `y(i,s,t)` shown as honest unavailable states |
| No raw snake_case in main content | zero leak tokens after the §7.1 fix |
| Interactive tables / charts | 16 tables + 1 Plotly figure with modebar; Pareto origin selector functional |
| Application errors / failed requests | none |
| RO1 and RO2 still render | yes |

### 10.1 Light/dark contrast

Screenshot capture was **not possible** in this environment — the preview webview
returned "produced no frames" on every attempt, across two fresh tabs and both
reload and reopen. This limitation is stated rather than worked around.

Instead, validation used accessibility snapshots, DOM inspection and
computed-style measurements:

| Theme | Background | Foreground | Contrast ratio | WCAG AA (4.5:1) |
|---|---|---|---|---|
| Dark | `rgb(14, 17, 23)` | `rgb(250, 250, 250)` | ~18.0:1 | pass |
| Light | `rgb(255, 255, 255)` | `rgb(49, 51, 63)` | ~12.5:1 | pass |

Both themes render correctly with no clipped or low-contrast text.

---

## 11. Files created and modified

**Created**

- `src/construction/dashboard_ui/ro3.py` — RO3 workspace presentation module.
- `tests/construction/test_dashboard_10a9.py` — 34 focused tests.
- `docs/dashboard_10a9_ro3_optimization.md` — this document.

**Modified**

- `src/construction/dashboard_data/registry.py` — 9 RO3 artifact entries.
- `src/construction/dashboard_data/contract.py` — `RO3Evidence` fields
  (`pareto_summary`, `pareto_decisions`).
- `src/construction/dashboard_data/adapters.py` — `adapt_ro3_evidence` wiring.
- `src/construction/dashboard_ui/navigation.py` — RO3 set AVAILABLE, RESEARCH
  group, counts 10 available / 5 planned, stale docstring corrected.
- `apps/cmido_dashboard.py` — RO3 dispatch branch.
- `tests/construction/test_dashboard_shell.py` — planned exemplar repointed.
- `tests/construction/test_dashboard_overview.py` — planned exemplar repointed.

`package-lock.json`, `.freebuff/` and unrelated `results/` artifacts were **not**
staged.

---

## 12. Scope of 10A.10

10A.10 is the **Procurement Decisions Workspace** (`procurement_decisions`,
DECISION group, currently planned). It is now the planned-page exemplar used by
the placeholder-policy tests, and will need those tests repointed again when it
becomes AVAILABLE. 10A.10 is **not** started by this phase.
