# Phase 10A.13 — Provenance & Integrity Workspace

Read-only dashboard workspace answering what evidence artifacts exist, how
each is provenance-classified, which fingerprints and integrity checks are
recorded (and what they establish), which loading restrictions apply, and
which evidence is missing, invalid, unregistered or undocumented.

---

## 1. Starting condition

| Item | Value |
|---|---|
| Branch | `main` |
| `HEAD` at start | `276c57129e5fb0e24332dcc71889bc17412ef39b` |
| `origin/main` at start | identical after `git fetch origin` |
| Construction regression baseline | 951 passed |
| Optimization regression baseline (incl. 8P gate) | 24 passed |
| Untracked research artifacts preserved | yes (`results/8N`–`9B`, `results/RO3/ablation/8M_gate/`, `9A_repository_inventory.csv`, scratch scripts, `.freebuff/`, `package-lock.json` untouched) |

---

## 2. Evidence audit (before any UI was written)

Every claim the page makes was checked against the artifact or code that
records it — never against a filename:

- **Registered inventory** — the 10A.2-B registry holds 45 entries; a live
  snapshot build records 43 `AVAILABLE`, 2 `TOO_LARGE` (the blocked raw
  scenario ledgers), 0 missing, 0 invalid. Every entry carries one of the four
  provenance classes (OBS 4, DER 28, EST 4, SCN 9).
- **Recorded fingerprints** — the 8M gate manifest records SHA-256 digests
  for ten step-36 source files; the 9B PSLIB audit records a source-workbook
  digest and a canonical-project fingerprint; the 9A ingestion audit records
  a fixture-bundle digest; the SUCCESS logistics audit records a digest for
  each of its seven tables; the 8Q manifest records a source digest and a
  generation script per publication table; the RO2 27D.4 summary records an
  estimate-table digest.
- **Recorded integrity checks** — 8M gate 20/20 (status PASS); RO3 step-39
  audit 29/29; 8S numerical reconciliation 81/81; 9A generalization gate
  19/19 (PASS); 9B real-project gate 22/22 (PASS); 8Q publication gate 31/31
  (PASS); 8R figure concordance 28/28 (PASS); RO1 final integrity status
  PASS; RO2 final audit all-pass with decision `RO2_FINAL_LOCK`; RO2
  propagation audit decision `PASS_WITH_RECORDED_CAVEATS`.
- **Recorded convergence limitation** — RO3 step 33 records the primary
  500→1000 transition as **failed** (142 failed comparisons, decision
  `RO3_3_EVALUATE_2500`, optimisation-level convergence recorded as a later
  requirement). Reproduced verbatim through the shared convergence builder.
- **Known-unregistered files verified on disk** (all present, none in the
  registry): the canonical PSLIB project JSON and the real-project experiment
  output (9B), the 9A repository inventory CSV and the 9A generalization
  audit CSV, the step-36 controller freeze manifest and the step-36
  origin/material-level results (fingerprinted by 8M but unregistered), and
  the five decision-level artifacts named by the Phase 10A.10 inventory
  (`RO3_O2_SELECTED_DECISIONS`, `RO3_O2_REALIZED_EVALUATION_SUMMARY`,
  `RO3_O4_REALIZED_EVALUATION_LEDGER`, `RO3_MULTI_ORIGIN_SUMMARY`,
  `RO3_DECISION_SENSITIVITY`) — the current registry contains **no entry for
  any of them**, so a live snapshot carries no provenance record for that
  content. This page reports the gap; it does not register anything.
- **Missing metadata** — the PSLIB and SUCCESS audits record no collection
  or creation dates; no registered artifact records authorship, software
  versions, source URLs or environment capture. Shown as undocumented.
- **Registry vs adapter coverage** — `RO1_PRIMARY_H3_SUMMARY` and
  `EVIDENCE_8P_MANIFEST` are registered but not adapted into any evidence
  bundle (their provenance/status still appear in the inventory; their
  content is not surfaced by any page).

No research script was rerun and no scientific output was modified.

---

## 3. Contract / registry / adapter changes

### Registry (`registry.py`) — one new reference structure, zero new loadable entries

- `UnregisteredArtifact` dataclass + `KNOWN_UNREGISTERED_ARTIFACTS` tuple:
  the twelve documented-but-unregistered files with their documented origin.
  These are **not** registry entries — no loading policy, no schema contract,
  no provenance record, never loaded or adapted. They exist so the page can
  report the registration gap honestly while keeping repository paths out of
  the presentation layer (the 10A.6 shell test forbids `results/` literals in
  `dashboard_ui`, and this phase keeps that rule).
- `ARTIFACT_REGISTRY` itself is **unchanged**: the evidence audit found no
  artifact that should become loadable as part of a presentation phase.

### Contract (`contract.py`) and adapters (`adapters.py`) — unchanged

All required evidence already flows through the 10A.2-B contract:
`snapshot.provenance` (full inventory with status, schema outcome, rows,
bytes), `snapshot.overview` (counts), `snapshot.ro3` (8M manifest/audit,
step-39 audit, convergence), `snapshot.real_data` (9A/9B audits and
manifests), `snapshot.evidence` (8S, 8Q, 8R), `snapshot.ro1`/`snapshot.ro2`
(integrity and audit locks), and registry loading policies. Extending the
contract would have added fields nothing could populate.

---

## 4. What is displayed

The page (`route = page/provenance_integrity`, EVIDENCE navigation group)
renders ten sections:

1. **Provenance and integrity evidence** — framing; KPIs (registered,
   available, missing-or-invalid, blocked-from-loading), the four provenance
   classes as recorded, and the five concepts kept apart (file integrity,
   schema validity, reproducibility, statistical significance, scientific
   validity).
2. **Registered artifact inventory** — one row per registry entry with
   component, provenance class, loading policy, recorded status, recorded
   schema outcome, rows and bytes, plus explicit state cards for every
   non-available artifact and a recorded status summary.
3. **Recorded fingerprints** — what a SHA-256 fingerprint does and does not
   establish; observed-source/ingestion digests (PSLIB + 9A); the seven
   SUCCESS table digests in their own table; the ten 8M gate source digests
   with their **live registration state** computed against the registry.
4. **Recorded integrity checks** — ten sources with outcomes read from the
   artifacts' own counters and statuses, under the heading "Reported, not
   re-run".
5. **Checks performed by this dashboard** — what the loader does (presence,
   size cap, parse, column contract, policy enforcement, existence-only
   disclosure) versus what it explicitly does not do (no digest recomputation,
   no gate re-run, no test recompute, no verification of authorship or
   method, no result recomputation).
6. **Loading policy and size restrictions** — policy table for all four
   policies with artifact counts, blocked-ledger state cards (description
   text as recorded, e.g. "NEVER auto-load"), and how the block is enforced.
7. **Documented lineage** — 8Q publication-table lineage (source artifact,
   source digest, generation-script name — never the path) plus recorded
   schema versions and the SUCCESS dataset citation, followed by an explicit
   statement of where the documented chain stops.
8. **Known evidence gaps** — the twelve present-but-unregistered files with
   documented origin and runtime presence, computed registration, and a
   disclosure that presence was checked existence-only; missing metadata
   (no dates, no authorship, no software versions) preserved as missing;
   PSLIB/SUCCESS separation and the travel-time ≠ procurement-lead-time rule;
   the recorded RO3 convergence failure reproduced verbatim.
9. **How to read this evidence** — recorded vs performed, fingerprint ≠
   validity, schema validity ≠ meaningfulness, missing stays missing,
   provenance class ≠ quality.
10. **Handoff and open items** — research-side convergence, registration
    decisions, documentation gaps, and that digest re-verification would
    need an explicit audited tool rather than an implicit UI action.

---

## 5. Scientific-integrity safeguards

- **Fingerprints are identity, not validity.** Every fingerprint section
  states that a digest establishes file identity relative to the recorded
  value only — never scientific validity, methodology, reproducibility or
  authenticity — and that this page never recomputes one to check current
  bytes.
- **Recorded ≠ performed.** Check outcomes are read from artifact-recorded
  counters; dashboard checks are listed in a separate section with an
  explicit "not performed" list. A missing artifact yields
  "Not available in this snapshot", never a pass.
- **Registration ≠ fingerprint.** The 8M source rows display their live
  registration state ("No" for all ten step-36 sources), and the gaps table
  computes registration from the registry rather than assuming it.
- **Existence checks are disclosed** in the section methodology and the
  table subtitle; file contents are never opened.
- **PSLIB and SUCCESS stay separate** — separate builders, separate tables,
  an explicit never-joined statement, and a cross-check that SUCCESS rows
  never carry PSLIB digests.
- **No fabricated metadata** — missing dates, authorship, versions and
  lineage render as undocumented; unknown manifest keys render as humanized
  labels, never invented values.
- **Recorded failure preserved** — the RO3 convergence lines come from the
  same builder the Ablation & Robustness page uses, failure included.
- **Loading hygiene** — the 169 MB / 338 MB ledgers remain `NEVER`-loaded
  (policy enforced before any read, verified by test); no path, project root,
  hex colour, inline CSS or snake_case label reaches the page.

---

## 6. Tests

New file: `tests/construction/test_dashboard_10a13.py` (56 tests) covering:

- module import safety (no research engine, no direct Streamlit import) and
  source hygiene (no `D:\CMIDO`, no `results/`, no hex, component layer only);
- navigation registration, live route, legacy-route resolution, app dispatch;
- registry mapping: every entry inventoried, missing records read MISSING,
  recorded status/schema/size carried verbatim, provenance class from
  records, class/status counts;
- recorded vs performed checks: outcome strings derived from recorded
  counters, unavailable when artifacts are missing, no re-run wording, the
  performed/not-performed lists being disjoint in meaning;
- missing/invalid/unregistered/partially documented evidence, including
  runtime presence (tmp_path), registry-absence of every listed file, and
  documentation coverage of each gap;
- fingerprints: registration computed against the registry, digest format,
  path-free display rows, real-snapshot reconciliation (10 / 3 / 7 / 9 rows);
- PSLIB–SUCCESS separation at builder and page level;
- blocked ledgers: `TOO_LARGE`, `data is None`, `BLOCKED_BY_POLICY`, policy
  counts, inventory status on the real snapshot;
- preservation of the recorded convergence failure (shared builder identity,
  "threshold: No", 142, `RO3 3 EVALUATE 2500`);
- AppTest rendering against the real repository artifacts: no exception, all
  ten sections, recorded-vs-performed language, fingerprint limits, unregistered
  evidence (read from the rendered dataframes), separation and missing-date
  statements, convergence failure, blocked ledgers, ≥ 8 rendered tables, zero
  snake_case leaks, zero path leaks.

Shell tests updated (`test_dashboard_shell.py`) for the IA change: 15
destinations now **14 available, 1 planned** (`resilience_stress` only), and
the provenance placeholder test became an availability test.

### Validation results

| Suite | Result |
|---|---|
| Focused `test_dashboard_10a13.py` | **56 passed** |
| Dashboard shell/contract/registry/adapters/10A.6–10A.12/UI/view | **680 passed** (624 pre-existing + 56 new, +0 lost) |
| `tests/optimization/` incl. 8P publication gate | **24 passed** (baseline unchanged) |
| Full `tests/construction/` | **1007 passed** = 951 baseline + 56 new (reconciled, +0 lost) |

One failure occurred during development and was fixed at the cause: the
10A.6 shell test forbids `results/` literals in any `dashboard_ui` module,
so the known-unregistered file list moved from the page module into
`dashboard_data/registry.py` (its legitimate home alongside the other path
metadata) rather than being suppressed in the test. Two of my own test
assertions were also corrected where they referenced the wrong render string
or the wrong return type.

---

## 7. Navigation / IA changes

- `provenance_integrity` moves from PLANNED to AVAILABLE with
  `route = "page/provenance_integrity"`; description updated to name the
  page's scope; `future_phase = "Phase 10A.13"` retained as the delivery
  record (same convention as 10A.10–10A.12).
- `apps/cmido_dashboard.py` imports the workspace and dispatches the route
  with the established honest-error-state pattern.
- The navigation module docstring now records 15 destinations: 14 available,
  1 planned. EVIDENCE group now exposes all five of its destinations live.

---

## 8. Files created and modified

| File | Change |
|---|---|
| `src/construction/dashboard_ui/provenance_integrity.py` | **created** — the workspace (builders + ten sections) |
| `src/construction/dashboard_data/registry.py` | modified — `UnregisteredArtifact` + `KNOWN_UNREGISTERED_ARTIFACTS` |
| `src/construction/dashboard_ui/navigation.py` | modified — page AVAILABLE with route; docstring counts |
| `apps/cmido_dashboard.py` | modified — import + dispatch branch |
| `tests/construction/test_dashboard_10a13.py` | **created** — 56 focused tests |
| `tests/construction/test_dashboard_shell.py` | modified — counts 14/1, provenance availability test |
| `docs/dashboard_10a13_provenance_integrity.md` | **created** — this report |

No file under `results/` was modified; no scientific artifact was touched.

---

## 9. Known limitations

- **The five decision-level artifacts are documented as registered but are
  absent from the current registry.** The page reports this as a registration
  gap; repairing it (registering those files and letting the Procurement
  Decisions page load new content) changes a prior page's evidence surface
  and belongs to a dedicated phase, not this one.
- **Fingerprints are reported, never verified.** No digest is recomputed
  anywhere, so a changed file would not be detected by this page.
- **Existence-only checking.** Unregistered file presence is verified at
  render time, but contents are never read, so their validity, schema and
  freshness remain unknown.
- **`RO1_PRIMARY_H3_SUMMARY` and `EVIDENCE_8P_MANIFEST`** are registered but
  not adapted into an evidence bundle: their inventory rows appear, their
  content is not presented anywhere.
- **Recorded-convergence failure** constrains generalisation of the RO3
  results; it is surfaced, not resolved — research-side work.
- **No dates, authorship or software versions exist to display** for the
  observed streams; closing that gap requires research-side documentation.
- Screenshot capture is unavailable in this environment; light/dark
  compatibility is inherited structurally through the component layer and
  asserted by the no-inline-style/no-hex tests.

---

## 10. Scope of 10A.14

10A.14 is not defined by this phase. The roadmap's remaining planned
destination is `resilience_stress` (declared as "Beyond Phase 10A.13"); no
phase has committed to it. The provenance findings above — especially the
five unregistered decision-level artifacts and the unverified-fingerprint
limitation — are the natural inputs to whatever phase picks up next.
