# CMIDO Dashboard — 10A.10: Procurement Decisions Workspace

**Status:** complete
**Checkpoint at start:** `93701ff6cb9e226dee3d8863104a5349fecdc594` (branch `main`, 10A.9 RO3 workspace)
**Baseline regression at start:** 820 passed, 0 failed (796 construction + 24 optimization/8P gate)
**Baseline regression at end:** 860 passed, 0 failed (836 construction + 24 optimization/8P gate; +40 focused 10A.10 tests)

This phase builds the **Procurement Decisions Workspace** in the existing
Streamlit dashboard. Like every 10A workspace it is presentation-only: every
displayed number flows through the 10A.2-B data contract (`RO3Evidence`), the
artifact registry and its pure adapters. No optimisation, simulation or
statistical result is recomputed, re-solved or invented inside the dashboard,
and the module does not import the research engine.

---

## 1. Starting condition

| Check | Result |
|---|---|
| Branch | `main` |
| `HEAD` at start | `93701ff6cb9e226dee3d8863104a5349fecdc594` |
| Baseline test suite | 820 passed, 0 failed |
| Untracked research artifacts preserved | yes (`results/8N`–`9B`, scratch scripts, `.freebuff/`, `package-lock.json` untouched) |

---

## 2. Decision-level artifact inventory

The five decision-level artifacts were **already registered** in the 10A.2-B
registry (registered alongside the RO3 artifacts in 10A.9); this phase did not
add registry entries. Paths resolve through the registry only — the page module
performs no filesystem access.

| Artifact id | Role on the page |
|---|---|
| `RO3_O2_SELECTED_DECISIONS` | Material-level procurement quantities q(i,t) |
| `RO3_O2_REALIZED_EVALUATION_SUMMARY` | Per-material realized cost / shortage / service |
| `RO3_O4_REALIZED_EVALUATION_LEDGER` | Per-period ledger, **size-gated** (see §6) |
| `RO3_MULTI_ORIGIN_SUMMARY` | Per-origin Pareto cardinality and objective range |
| `RO3_DECISION_SENSITIVITY` | Sample-size sensitivity of the decision vectors |

---

## 3. What is displayed, and why

The page (`route = page/procurement_decisions`, DECISION navigation group)
renders twelve sections:

1. **Procurement decision evidence** — page framing.
2. **Decision evidence status** — per-artifact available/unavailable state with schema.
3. **Material-level procurement quantities** — one row per selected decision (material × calendar period).
4. **Procurement timing** — periods receiving a non-zero quantity under the selected candidate.
5. **Per-origin Pareto summary** — nondominated-solution counts and objective ranges per forecast origin.
6. **Supplier allocation and capacity** — honest *not-an-output* state (excluded from the frozen RO3 formulation scope).
7. **Inventory and safety-stock decisions** — honest *not-an-output* state (same reason).
8. **Feasibility, shortage and constraint status** — shortage only where realized evaluation exists; feasibility never asserted without constraint evidence.
9. **Cost–service–resilience trade-offs** — cost vs expected shortage vs CVaR_0.95 from Pareto evidence.
10. **Scenario sensitivity** — how decisions change with scenario sample size, with an explicit "not observed outcomes" caveat.
11. **Provenance, assumptions and limitations** — every value traced to a registered, schema-validated artifact.
12. **Handoff back to RO3 optimization** — states that this page is one view of the same RO3 evidence.

---

## 4. Scientific-integrity safeguards

- No hard-coded KPI values: a dead `_kpi_meta()` block that would have shown
  hard-coded numbers was removed during review.
- Supplier allocation, safety stock and constraint rows are reported as
  *excluded from the optimisation scope*, never as missing dashboard data.
- Scenario-sensitivity comparisons are labelled as modelled epsilon-constraint
  solution sets, not observed procurement outcomes.
- The page renders decision quantities only when the schema-validated artifact
  is AVAILABLE; otherwise it renders an explicit unavailable state.

---

## 5. Layering

- Streamlit is imported **only** by `components.py`; the page module uses the
  approved component layer (`render_section_block`, `render_paragraph`,
  `render_inline_label_values`, `render_table`, banner/status APIs).
- Two small helpers were added to `components.py` (`render_paragraph`,
  `render_inline_label_values`) that delegate to the existing
  `{"label", "body"}` block contract — no new styling primitives, no hex colors.
- No direct `import streamlit` in the page module (enforced by the layering test).

---

## 6. Loading policies and safeguards

- The realized-evaluation ledger passes through `_ledger_is_safe_for_ui()`
  (max 1,000 rows): the small O4 single-origin ledger renders; any larger
  ledger (e.g. a multi-origin raw ledger) keeps its provenance row but never
  surfaces rows in the UI.
- The 169 MB / 338 MB raw RO3 scenario ledgers are not registered for UI
  loading and are never read by the dashboard.
- Snapshot failure at runtime renders an honest error state with diagnostics —
  the shell never shows fabricated fallback numbers.

---

## 7. Tests

| Suite | Result |
|---|---|
| Focused 10A.10 (`tests/construction/test_dashboard_10a10.py`) | 40 passed |
| Full construction suite | 836 passed |
| Optimization/8P gate (`tests/optimization/`) | 24 passed |

Recount note: the 10A.9 figure of 820 counted construction + optimization
together (796 + 24). Construction alone is now 836 (796 + 40 new).

Six placeholder-policy tests in `test_dashboard_shell.py` and the AppTest
exemplar in `test_dashboard_overview.py` were repointed because
`procurement_decisions` became AVAILABLE; `resilience_stress` is now the
planned-page exemplar (11 available / 4 planned).

---

## 8. Live UI validation

Validated through Streamlit's `AppTest` (the same interface users hit):

- Procurement page renders with no exception and expected content.
- Overview, RO3 and the `resilience_stress` placeholder render clean.
- Render-path bugs invisible to unit tests (missing helper imports, wrong
  banner/table/error-state call signatures) were found this way and fixed.

---

## 9. Files created and modified

**Created**

- `src/construction/dashboard_ui/procurement_decisions.py` — workspace module.
- `src/construction/dashboard_ui/_procurement_helpers.py` — pure formatting/metadata helpers.
- `tests/construction/test_dashboard_10a10.py` — 40 focused tests.
- `docs/dashboard_10a10_procurement_decisions.md` — this document.

**Modified**

- `src/construction/dashboard_data/contract.py` — decision-level `RO3Evidence`
  fields; `ProcurementDecisionsEvidence` + `snapshot.procurement` declared.
- `src/construction/dashboard_data/adapters.py` — decision-level wiring and
  the size gate for the realized-evaluation ledger.
- `src/construction/dashboard_ui/navigation.py` — page AVAILABLE, `pages_by_id()`,
  placeholder-reason fallback, route-validation allowance for phase-scoped routes.
- `src/construction/dashboard_ui/components.py` — two block-rendering helpers.
- `apps/cmido_dashboard.py` — dispatch branch for `page/procurement_decisions`.
- `tests/construction/test_dashboard_shell.py`, `tests/construction/test_dashboard_overview.py` — exemplar repointing.

`package-lock.json`, `.freebuff/` and unrelated `results/` artifacts were **not**
staged.

---

## 10. Known limitation

`ProcurementDecisionsEvidence` and `snapshot.procurement` are declared in the
contract but not populated by the snapshot builder — the page reads
`snapshot.ro3` instead. Harmless dead weight, noted for a future cleanup.

---

## 11. Scope of 10A.11

10A.11 is the **Real-World Data Workspace** (PSLIB / SUCCESS evidence streams,
9A generalization + 9B real-project artifacts, `real_data` contract). It is a
planned page in the EVIDENCE group and must preserve the PSLIB/SUCCESS source
distinction with honest missing/invalid/oversized states. 10A.11 is **not**
started by this phase.
