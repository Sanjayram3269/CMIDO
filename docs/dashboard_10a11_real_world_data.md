# CMIDO Dashboard — 10A.11: Real-World Data Workspace

**Status:** complete
**Checkpoint at start:** `b8a9abefceb80051f5ef5f8832fdf5fb7e413460` (branch `main`, 10A.10 Procurement Decisions workspace, committed and synchronized before this phase began)
**Baseline regression at start:** 860 passed, 0 failed (836 construction + 24 optimization/8P gate)
**Baseline regression at end:** 908 passed, 0 failed (884 construction + 24 optimization/8P gate; +48 focused 10A.11 tests)

This phase builds the **Real-World Data Workspace** in the existing Streamlit
dashboard. Like every 10A workspace it is presentation-only: every displayed
count, coverage figure, fingerprint and gate result flows through the 10A.2-B
data contract (`RealDataEvidence`), the artifact registry and its pure
adapters. No statistical result is recomputed and, critically, the PSLIB and
SUCCESS evidence streams are never joined — the page renders them as the
separate observed datasets the 9B gate recorded them to be.

---

## 1. Starting condition

| Check | Result |
|---|---|
| Branch | `main` |
| `HEAD` at start | `b8a9abefceb80051f5ef5f8832fdf5fb7e413460` |
| Baseline test suite | 860 passed, 0 failed |
| Untracked research artifacts preserved | yes (`results/8N`–`9B`, scratch scripts, `.freebuff/`, `package-lock.json` untouched) |

---

## 2. Evidence audit (before any UI was written)

Six registered real-data artifacts were audited against their actual on-disk
schemas and against the phase documentation (`docs/CMIDO_9A_REAL_DATA_GENERALIZATION.md`,
`docs/CMIDO_9B_REAL_PROJECT_E2E.md`):

| Artifact | Content actually recorded |
|---|---|
| `REAL_9A_CANONICAL` | Civil-project fixture (project + 4 activities + 3 dependencies, planned dates, SHA-256 fingerprint) |
| `REAL_9A_INGESTION_AUDIT` | Fixture row counts, rejected-record count, fingerprint |
| `REAL_9A_MANIFEST` | 9A gate: PASS 19/19 checks |
| `REAL_9B_PSLIB_AUDIT` | PSLIB C2025-02 workbook: 100 activities, 94 dependencies, 146 risk profiles, 3 control snapshots, 6 resource rows, 6 rejected dependencies, fingerprints |
| `REAL_9B_LOGISTICS_AUDIT` | **NEWLY REGISTERED** — SUCCESS bundle: 7 tables with row/column/invalid counts, per-table SHA-256, DOI 10.5281/zenodo.1249519, derived summary |
| `REAL_9B_MANIFEST` | 9B gate: PASS 22/22 checks + the recorded integration boundary |

### 2.1 Integrity finding

The registry described `REAL_9A_CANONICAL` as a "SUCCESS-derived" fixture and
`REAL_9A_INGESTION_AUDIT` as an audit of "SUCCESS data ingestion". **No
documentation or gate source supports a SUCCESS connection** — the 9A doc
describes a plain civil-project CSV-bundle fixture, and the 9A gate code
contains no SUCCESS reference. The contract field that stored the 9A
ingestion audit was even named `success_ingestion_audit`. Left as-is, the
page would have had to present the fixture as SUCCESS evidence, violating the
PSLIB/SUCCESS separation rule. Resolved in this phase:

- Registry descriptions corrected (the new text *denies* the SUCCESS
  connection; a regression test forbids re-claiming it).
- Contract field renamed `success_ingestion_audit` → `ingestion_audit_9a`,
  with the `RealDataEvidence` docstring now spelling out the three streams.
- A regression test (`test_registry_no_longer_calls_the_fixture_success_derived`)
  locks this in.

---

## 3. Contract / registry / adapter changes

- **Registry:** added `REAL_9B_LOGISTICS_AUDIT` (JSON, SAFE, `required=False`,
  provenance OBS). This was the only missing artifact needed to present the
  SUCCESS stream with real coverage evidence.
- **Contract (`RealDataEvidence`):** renamed `success_ingestion_audit` →
  `ingestion_audit_9a`; added `generalization_manifest_9a` (the 9A gate
  result, previously loaded but dropped) and `logistics_audit`.
- **Adapter (`adapt_real_data_evidence`):** maps the two new artifacts,
  appends provenance for all six (the 9A manifest's provenance was previously
  not attached), and keeps every stream in its own field. Missing / INVALID /
  non-dict data leaves fields empty so the UI renders honest unavailable
  states.

No other contract or snapshot change was needed: `snapshot.py` already loads
every registered artifact, so the new entry flows through automatically.

---

## 4. What is displayed

The page (`route = page/real_world_data`, EVIDENCE group) renders nine
sections:

1. **Real-world evidence** — framing, availability KPI row (artifacts,
   9A gate, 9B gate, SUCCESS table count — all derived at render time), the
   three streams, and the 9B manifest's integration boundary quoted verbatim.
2. **Registered real-data artifacts** — six-artifact inventory table (status,
   provenance class, rows, size, schema check) plus explicit artifact-state
   panels for anything not AVAILABLE.
3. **9A ingestion fixture** — identity, all activities with recorded planned
   dates, the min/max planned date range (2026-01-05 to 2026-01-20 on the
   real artifact), row-count accounting, traceability and normalization —
   with a fixture-scope banner stating it is not PSLIB, not SUCCESS and not
   the user's actual dataset.
4. **PSLIB empirical project stream** — workbook identity + recorded coverage
   counts, with an explicit "time range not recorded" note (the audit carries
   no dates, so none is shown).
5. **SUCCESS construction-logistics stream** — bundle identity (DOI), the
   seven-table coverage table, the gate's derived summary, a top-materials
   bar chart, and an explicit "time range not recorded" note.
6. **Gate evidence** — 9A and 9B manifests: status banner, per-check tables
   (humanized check names, path details suppressed), scope / frozen-phase /
   boundary notes.
7. **Provenance classes and stream separation** — OBS/DER/EST/SCN legend,
   the classes actually recorded here (OBS and DER only; EST/SCN explicitly
   said to live in RO1/RO3), the separation rule, and a note that unregistered
   on-disk files are deliberately not shown.
8. **Limitations and what is missing** — fixture scope, no cross-dataset
   join, no generalization/deployment claims, absent time coverage, counts
   without row-level rejection detail, suppressed paths — plus what would
   strengthen the evidence.
9. **Where this evidence is used** — read-only ingestion evidence; RO1→RO3
   integration requires a documented mapping or must remain separate.

---

## 5. Scientific-integrity safeguards

- No cross-stream fallback: builders fed the *wrong* stream's dict return no
  numbers (tested). PSLIB metrics can never be populated from SUCCESS
  evidence or vice versa.
- Time ranges are shown only for the fixture, whose artifact records dates.
  For PSLIB and SUCCESS the page states that no date values are recorded
  rather than inferring ranges from file names or headers.
- Gate check details that name filesystem paths are suppressed (same policy
  as the RO3/procurement pages).
- The 169 MB / 338 MB raw scenario ledgers remain unregistered for UI
  loading; nothing on this page reads them.
- KPI values are computed from provenance records and manifests at render
  time; nothing scientific is hard-coded.

## 6. Layering and formatting

- Streamlit is imported only by `components.py`; the page module uses the
  shared component layer exclusively. A structural test asserts the page
  source contains no inline styling (`style=`, `<div`, `light-dark(`), so
  light/dark parity is inherited from the 10A.3 design system rather than
  re-specified.
- Recorded snake_case identifiers (check names, table file names, recorded
  metadata values in prose) are humanized for display via one documented
  transform; an AppTest-level test asserts no raw lowercase snake_case token
  reaches the rendered page.

---

## 7. Tests

| Suite | Result |
|---|---|
| Focused 10A.11 (`tests/construction/test_dashboard_10a11.py`) | 48 passed |
| Full construction suite | 884 passed |
| Optimization suite (incl. 8P publication gate) | 24 passed |

Test count reconciliation: 836 (10A.10 baseline) + 48 new = 884. No existing
test was removed; the two shell placeholder-policy tests were updated for the
IA transition (12 available / 3 planned; `real_world_data` removed from the
planned exemplar set, `resilience_stress` remains the placeholder exemplar).

Coverage includes: artifact availability, schema variation (non-dict JSON →
empty field), MISSING/INVALID/TOO_LARGE honest states, stream-separation
guards, no-filename-inference guards, path/hex/snake-case hygiene, provenance
vocabulary, and end-to-end AppTest rendering of the live page (which loads
the real on-disk artifacts).

## 8. Live UI validation

The AppTest fixture runs the actual dashboard app with the real snapshot
(all six artifacts AVAILABLE on disk):

- Page renders with no exception; all three streams, the boundary quote, the
  artifact inventory, the provenance legend and the limitations render.
- Rendered markdown passes the snake-case leak check and contains no
  filesystem paths.
- Overview, RO1, RO2, RO3 and Procurement Decisions still render (their
  suites ran inside the 884).

Screenshot capture in this environment previously failed ("produced no
frames", per the 10A.9 record); the light/dark guarantee here is structural
(design-system-only rendering + `light-dark()` CSS tokens), matching how the
10A.9 contrast audit substituted computed-style checks.

---

## 9. Files created and modified

**Created**

- `src/construction/dashboard_ui/real_world_data.py` — workspace module with
  pure presentation builders.
- `tests/construction/test_dashboard_10a11.py` — 48 focused tests.
- `docs/dashboard_10a11_real_world_data.md` — this document.

**Modified**

- `src/construction/dashboard_data/registry.py` — `REAL_9B_LOGISTICS_AUDIT`
  entry; corrected the two 9A descriptions.
- `src/construction/dashboard_data/contract.py` — `RealDataEvidence` field
  rename + two new fields.
- `src/construction/dashboard_data/adapters.py` — real-data adapter mapping.
- `src/construction/dashboard_ui/navigation.py` — page AVAILABLE with route;
  module docstring counts corrected (12 available / 3 planned).
- `apps/cmido_dashboard.py` — dispatch branch for `page/real_world_data`.
- `tests/construction/test_dashboard_shell.py` — IA-transition updates.

`package-lock.json`, `.freebuff/` and unrelated `results/` artifacts were
**not** staged.

---

## 10. Known limitations

- PSLIB and SUCCESS time ranges are absent because the registered audits
  record no date values; strengthening this requires gate-level changes, not
  dashboard changes.
- The canonical PSLIB project JSON, the real-project experiment output and
  the 9A generalization audit CSV exist on disk but remain unregistered, so
  execution-level detail is summarized by the gate manifests only.
- `ProcurementDecisionsEvidence` / `snapshot.procurement` dead weight from
  10A.10 remains (noted there; out of scope here).

---

## 11. Scope of 10A.12

10A.12 is the **Ablation & Robustness** workspace (`ablation_robustness`,
EVIDENCE group, planned, future phase 10A.12) covering the 8M ablation gate
evidence. 10A.12 is **not** started by this phase.
