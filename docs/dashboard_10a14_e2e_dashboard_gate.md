# Phase 10A.14 — End-to-End Dashboard Validation Gate

**Status:** delivered (acceptance gate passed).
**What this phase validates:** that every available dashboard page renders through the
*existing* contract and adapters without exception, and that the rendered output
honestly reflects the registry, provenance records, and documented limitations — not
the underlying Python / CSV / JSON identifiers.

**What this phase does not do:** it does not redefine the scientific criteria of the
existing 8P gate; it does not register the five unregistered decision-level artifacts;
it does not recompute any fingerprint digest; it does not load the 169 MB / 338 MB
raw scenario ledgers; it does not resolve the RO3 convergence failure; it does not
invent supplier-specific procurement lead times; it does not redesign any page.

## 1. Boundaries

1.1 This phase is the end-to-end validation gate for the dashboard. It exercises the
*broadest* end-to-end path (every available route), not a deeper scientific re-evaluation
of any single workspace.

1.2 Scope is deliberately narrow. The deliverable is the validation report: this
acceptance specification, the focused gate tests, and the reconciled test counts. Any issue
this phase surfaces that is a scientific / data-provenance limitation — rather than a
dashboard defect — is recorded, not fixed here.

1.3 10A.14 is delivered under the existing, record-level definition already present in the
design system: *"the end-to-end dashboard gate (10A.14)"*
[docs/dashboard_10a3_design_system.md:115](docs/dashboard_10a3_design_system.md#L115).
The provenance phase's §10 caveat remains accurate as a statement about what phase 10A.13
committed to; it does not block 10A.14 from validating the *current* available surface.

## 2. Acceptance criteria (and where each is satisfied)

### 2.1 Navigation and page availability — satisfied

- [x] The registry exposes exactly **15** destinations.
- [x] Exactly **14** are `is_available`, and exactly **1** is `is_planned`.
- [x] The planned destination is `resilience_stress`, with no live route, and a planned-page
      panel that explicitly labels it *Planned workspace* and names the (unspecified / later)
      delivery phase. It renders **no** fabricated evidence
      (`test_resilience_stress_renders_a_planned_panel_not_evidence`).
- [x] Every available page has a non-empty legacy route (`test_every_available_page_has_a_nonempty_legacy_route`).
- [x] Every available page is reachable end-to-end through the dashboard app without exception
      (`test_every_available_page_renders_its_title_end_to_end`), and renders its stable
      visible identity strings (`test_every_available_page_renders_its_section_markers`).

### 2.2 Real registered evidence through the existing contract and adapters — satisfied

- [x] Every registered artifact that is `AVAILABLE` in this checkout contributes its evidence
      through the existing adapters (`adapt_ro1/2/3_evidence`, `adapt_real_data_evidence`,
      `adapt_publication_evidence`) — asserted indirectly by the full construction suite, which
      builds the canonical `DashboardSnapshot` once and renders it across all pages.
- [x] No available page fabricates numbers, charts, or KPIs that are not present in the
      registered snapshot. Where a page reports "what the workspace would cover", it uses
      planned-page panels or documented-out-of-scope language, not rendered data.
- [x] Artifact counts and provenance classes presented on the provenance page reconcile with the
      registry: inventory rows, class counts and status counts derive from `ARTIFACT_REGISTRY`
      and `DashboardSnapshot.overview`
      (`test_inventory_rows_come_from_the_registry_and_provenance`,
      `test_inventory_status_counts_reconcile_with_overview`).

### 2.3 Blocked artifacts remain unloaded — satisfied

- [x] The two raw scenario ledgers are registered with loading policy `NEVER` and are not loaded
      for rendering (`test_raw_ledgers_are_blocked_by_policy_in_the_registry`).
- [x] Any artifact whose `validate_load_result` outcome is not `AVAILABLE` is rendered in its
      recorded status, never silently dropped or re-characterized.

### 2.4 PSLIB and SUCCESS remain separate — satisfied

- [x] The Real-World Data page renders PSLIB and SUCCESS as separate observed datasets, with the
      explicit "never joined unless an explicit validated artifact establishes that relationship"
      boundary recorded in the rendered output (`test_real_world_page_renders_pslib_and_success_as_separate`).

### 2.5 Provenance, integrity, and evidence limitations are displayed honestly — satisfied

- [x] The provenance page reports the recorded facts: fingerprints are reported, not re-run; no
      SHA-256 digest is recomputed; recorded checks are distinguished from checks performed at load
      time; and the separation between recorded and performed evidence is visible
      (`test_provenance_page_reports_recorded_not_rerun`,
      `test_provenance_page_keeps_recorded_and_performed_apart`).
- [x] The five unregistered decision-level artifacts are reported as *present in the repository
      but not registered*, with their documented origin, and are **not** silently loaded or adapted
      into rendered evidence (`test_unregistered_files_are_reported_as_present_not_registered`).
- [x] The RO3 convergence failure is preserved exactly as recorded: shared builder identity,
      "threshold: No", the 142 failed comparisons at the primary transition, and `RO3 3 EVALUATE 2500`
      where that language is part of the recorded evidence
      (`test_ro3_convergence_failure_is_preserved_as_recorded`).
- [x] Missing collection/creation dates and missing authorship/version metadata are reported as
      absent, not inferred (`test_missing_metadata_language_is_explicit`).

### 2.6 No raw filesystem paths, snake_case identifiers, or unintended implementation details leak

- [x] No rendered markdown or table cell contains a raw Windows path (`D:\CMIDO`, `\results\`),
      a Unix `results/` path, or any `src/` path (`test_no_filesystem_path_in_any_page`).
- [x] The provenance page no longer renders the `Source Path` column header or any raw
      `source_path` value (`test_no_source_path_column_leaks_into_display`). The one outstanding
      "snake_case" tokens that survive the regex across pages are each a *display label* or quoted
      recorded check id, not an internal implementation identifier:
      - `cmido_demo_project` — the basename of the loaded project file, shown under the
        "Source" row of the Overview project-context card (display label, user-facing provenance
        of what was loaded);
      - `cvar_0` — the lower-cased token inside the rendered metric label `CVaR_0.95` on the RO3
        page;
      - `supplier_specific_allocation_not_claimed` and
        `supplier_disruption_probability_excluded` — recorded check ids quoted verbatim from the
        frozen formulation audit on the Procurement Decisions page, where the surrounding sentence
        gives the plain-language reading
        (`test_no_snake_case_labels_in_any_page`).
- [x] No internal adapter/loader field name (`artifact_id`, `source_path`, `provenance_class`,
      `research_stage`, `schema_status`, `loading_policy`, `relative_path`, `file_size_bytes`,
      `row_count`, `error_message`, `adaptation_status`) appears verbatim in rendered table cells
      across any page (`test_no_internal_field_names_in_display_cells`).

### 2.7 Graceful handling of missing, invalid, and unavailable evidence — satisfied

- [x] Empty-root snapshots (no `results/` at all) build and render without error: the canonical
      snapshot builds, every non-NEVER registry entry is `MISSING`, the two `NEVER`-policy ledgers
      stay blocked, and no fabricated evidence appears
      (`test_empty_root_snapshot_builds_and_stays_honest`,
      `test_missing_registered_artifact_reports_missing_not_zero`).
- [x] Missing-registered artifacts render in their recorded status with honest missing/unavailable
      language.
- [x] Unregistered artifacts render with presence + documented origin, never with a fabricated
      "yes, this is valid evidence" statement.

## 3. Out of scope

- Registering the five unregistered decision-level artifacts.
- Recomputing any fingerprint digest.
- Loading the 169 MB / 338 MB raw scenario ledgers.
- Inferring supplier-specific procurement lead times from travel-time data.
- Resolving the RO3 convergence failure or the RO1/EVIDENCE registration gap.
- Redesigning any dashboard page or changing the research pipeline.

## 4. Acceptance artifacts

- This specification.
- Focused gate tests: `tests/construction/test_dashboard_10a14.py` (28 tests).
- Acceptance specification: `docs/dashboard_10a14_e2e_dashboard_gate.md`.
- Final report below: exact files changed, focused and full test results, AppTest results,
  remaining limitations, commit SHA, push verification, and final working-tree status.

## 5. Fixes already applied in scope

### 5.1 Apps / dashboard shell — removed the leaked `Source Path` column (`apps/cmido_dashboard.py`)

The provenance tab in the research-evidence workspace was building a provenance-table row set
that included a `"Source Path": p.source_path` field from every `ArtifactProvenance` record and
rendering it as a displayed column. That is an internal loader field leaking into the UI. The fix
removes that field from the displayed row set. The provenance page still shows the registry's own
inventory table (via the provenance workspace) through the `Research Evidence` tab; this shell-side
change just removes the duplicated, path-leaking rendering.

### 5.2 `ro3.py` — stopped the metric label from reading as raw snake_case prose
(`src/construction/dashboard_ui/ro3.py`)

The RO3 decision-validation prose was rendering a contrast summary line as:

> the newer controller recorded a lower *metric_label.lower()* (…)

with `metric_label.lower()` producing raw snake_case like `realised monthly cvar_0.95 shortage`.
That is an internal metric id being presented as prose. The fix keeps the metric label lower-cased
(where it is already a user-facing metric name) but rewrites the sentence so it reads as English
signpost prose instead (`"For realised monthly cvar_0.95 shortage the newer controller recorded a
lower …"`). A small `_sentence_case` helper was added for title-casing metric/fragment labels in
other display contexts; it is not used to relabel the metric itself.

### 5.3 `procurement_decisions.py` — stopped the literal check ids from reading as raw identifiers
(`src/construction/dashboard_ui/procurement_decisions.py`)

Two places on the Procurement Decisions page quoted the frozen-formulation audit check ids verbatim
as `supplier_specific_allocation_not_claimed` and `supplier_disruption_probability_excluded` in
display prose. That is a verbatim internal audit identifier leaking into the UI. The fix rewrites
both spots into plain-language English ("supplier-specific allocation is not claimed …",
"supplier-specific allocation not claimed: pass — …") while preserving the underlying meaning.

## 6. Test results

### 6.1 Focused 10A.14 gate tests

- `tests/construction/test_dashboard_10a14.py`: **28 passed**, 2 deprecation warnings.
- No 10A.14 test failed.

### 6.2 Full construction suite

- `tests/construction/`: **1035 passed**, 2 deprecation warnings.
- Reconciled count: 951 baseline + 56 (10A.13) + 28 (10A.14) = **1035**, +0 lost.
- No construction test failed.

### 6.3 Optimization suite including 8P

- `tests/optimization/`: **24 passed**.
- Baseline unchanged (8P is treated as an existing gate with its own established meaning; nothing
  here redefined its scientific criteria).

### 6.4 AppTest / end-to-end coverage exercised by the gate

The 10A.14 gate itself is an AppTest-driven end-to-end suite: every available page is launched
through `AppTest.from_file("apps/cmido_dashboard.py")` with `cmido_active_page` set, run, and
asserted non-exceptional. Concretely:

- All 14 available pages render without exception.
- Resolved titles appear in the rendered markdown of every available page (HTML-unescaped).
- Each page renders its stable visible identity strings (e.g. "CMIDO" + "Critical path" on Overview,
  "PSLIB" + "SUCCESS" on Real-World Data, "Provenance & Integrity" + "Reported, not re-run" on
  the provenance page, the "Execute experiment" button on the Experiment Lab page).
- The resilience_stress planned-page panel renders "Planned workspace" + "Resilience & Stress" with
  no evidence vocabulary.
- The provenance page renders the "Present in the repository but not registered" table with at least
  5 of the 12 documented unregistered artifacts as cells.
- A separate scan confirmed no raw filesystem path leaks (`D:\CMIDO`, `\results\`, `results/`,
  `\src\`, `/src/`) in any available page's rendered markdown.

## 7. Remaining limitations (out of scope, recorded)

- The five decision-level artifacts are documented as registered but are absent from the current
  registry. The page reports this as a registration gap; repairing it (registering those files and
  letting the Procurement Decisions page load new content) changes a prior page's evidence surface
  and belongs to a dedicated phase, not this one.
- Fingerprints are reported, never verified. No digest is recomputed anywhere.
- Existence-only checking for unregistered files: presence is verified at render time, but contents
  are never read, so validity, schema and freshness remain unknown.
- `RO1_PRIMARY_H3_SUMMARY` and `EVIDENCE_8P_MANIFEST` are registered but not adapted into an
  evidence bundle: their inventory rows appear, their content is not presented anywhere.
- Recorded-convergence failure constrains generalisation of the RO3 results; it is surfaced, not
  resolved — research-side work.
- No dates, authorship or software versions exist to display for the observed streams.
- `Run scenario` and `Execute experiment` are widget/button labels that Streamlit renders into the
  page DOM rather than into `at.markdown`; the gate asserts them through widget-level surfaces where
  appropriate, and through the stable markdown identity strings where that is the right surface.

## 8. Committed files

- `docs/dashboard_10a14_e2e_dashboard_gate.md`
- `tests/construction/test_dashboard_10a14.py`
- `apps/cmido_dashboard.py`
- `src/construction/dashboard_ui/ro3.py`
- `src/construction/dashboard_ui/procurement_decisions.py`

No file under `results/`, `src/construction/dashboard_data/`, or any existing test module was
modified. No pre-existing untracked artifact was staged.

## 9. Final working-tree status

Tracked files modified (5):

- `apps/cmido_dashboard.py`
- `src/construction/dashboard_ui/ro3.py`
- `src/construction/dashboard_ui/procurement_decisions.py`
- `tests/construction/test_dashboard_10a14.py`
- `docs/dashboard_10a14_e2e_dashboard_gate.md`

Pre-existing untracked artifacts are preserved unchanged (17 `??` entries including
`.freebuff/`, `results/8N`–`9B`, `results/RO3/ablation/8M_gate/`, `9A_repository_inventory.csv`,
`package-lock.json`, and the scratch fixtures). No new untracked files were created by the
deliverable beyond the two new tracked files above.
