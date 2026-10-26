# CMIDO — Publication Freeze Package (research-freeze candidate)

**Built:** 2026-10-26 · **Source repository:** `D:\CMIDO` · **Branch:** `feat/external-data-ingestion`
**Source HEAD at build time:** `89f2e9121463583ce82c3c697d17092680f29459` ("Fix dashboard project upload state handling")

> **This is a research-freeze candidate, not a submission-ready paper.**
> It is a self-contained, traceable working copy of the current CMIDO research and publication
> artifacts. It is explicitly **not** a journal package: the bibliography is unverified, no formal
> systematic literature review has been done, no journal has been chosen, and the scientific
> limitations in `08_INDEX/KNOWN_LIMITATIONS.md` remain open.

---

## 1. What this package contains

| Folder | Contents | Files |
|---|---|---|
| `01_MANUSCRIPT/` | Authoritative Markdown source (with the 2026-10 citation-cluster edits), the PDF renderer, and a **newly built** PDF | 3 |
| `02_FIGURES/` | Canonical publication figures F1–F7 (PNG) + `FIGURE_LIST.md` | 8 |
| `03_TABLES/` | Canonical publication tables T1–T6 (10 CSV) + `TABLE_LIST.md` | 11 |
| `04_RESULTS/` | `RO1/` `RO2/` `RO3/` result trees and `gates/` (8M/8N/8O/8P/8S/8T manifests and audits) | 393 |
| `05_EVIDENCE/` | Evidence concordance, package audits, convergence report, literature review, dashboard fix report, smoke/gate evidence, figure-table audits, E2E manifest + screenshots, 3 evidence-cited external-data runs | 51 |
| `06_REPRODUCIBILITY/` | Reproducibility guide, package manifest, build/dependency files, and the frozen scenario-input SHA-256 manifest | 7 |
| `07_SUPPLEMENTARY/` | Supplementary index, status/verification notes, professor-review message, examples, and the three project fixtures the regression tests require | 14 |
| `08_INDEX/` | Figure index, table index, claim register, known limitations, registry gaps, source map, `MANIFEST.sha256` | 8 |

Total **~495 files, ~18 MB**.

## 2. How provenance is preserved

1. **Every copied file is byte-identical to its repository source.** Each copy was SHA-256 verified
   against the source at copy time; the build reported **0 mismatches**.
2. **`08_INDEX/SOURCE_MAP.md` maps all 485 copied files to their exact repository path**, and lists the
   10 package-generated files with how each was produced.
3. **`08_INDEX/MANIFEST.sha256`** covers every file in this folder (except itself), so the package can
   be re-verified at any time.
4. **Nothing in the repository was moved, deleted, modified, staged, committed or tagged** to build
   this package. Only additions inside this new folder were made.
5. **Provenance classes are preserved as recorded** (`OBS` observed, `DER` derived, `EST` estimated,
   `SCN` scenario-generated) — see `05_EVIDENCE/CMIDO_8O_PAPER_EVIDENCE_PACKAGE.md` and the claim
   register in `08_INDEX/CLAIM_REGISTER.md`.
6. **Absolute local machine paths inside copied evidence files are reproduced verbatim** (for example
   `D:\CMIDO\...`) and must be read as local-only references. No path was rewritten.

## 3. Which artifacts are authoritative

| Artifact | Authoritative copy in this package | Notes |
|---|---|---|
| Manuscript text | `01_MANUSCRIPT/CMIDO_DRAFT_MANUSCRIPT.md` | Markdown is the source of truth; the PDF is a build product |
| Publication figures | `02_FIGURES/` | The `results/8R_publication_figures/` duplicates were **not** copied (verified byte-identical) |
| Publication tables | `03_TABLES/` | The `results/8Q_publication_artifacts/` duplicates were **not** copied (verified byte-identical) |
| Claim → evidence mapping | `08_INDEX/CLAIM_REGISTER.md` | Reproduced verbatim from `docs/CMIDO_EVIDENCE_CONCORDANCE.md` §4 |
| Frozen scenario inputs | **NOT in this package** — see `06_REPRODUCIBILITY/SCENARIO_INPUT_SHA256.txt` | Six ladder CSVs (~594 MB) remain in the repository only |
| Registry state | `08_INDEX/REGISTRY_GAPS.md` | Re-read from source on 2026-10-26 |

## 4. Known scientific limitations (summary — read the full file)

`08_INDEX/KNOWN_LIMITATIONS.md` is mandatory reading. In short:

- **RO1** primary-horizon (h=3) evidence is **mixed / descriptive**; CQR beats the statistical
  baseline on Winkler-80 for only 2 of 9 series. **No universal ML/conformal superiority is claimed.**
- **RO2** uses procurement-process duration as a **proxy**, not supplier-specific lead time.
- **RO2** service-risk curves are **conditional model estimates**, not calibrated operational service
  levels; the 37 paired observations do not prove statistical dependence.
- **RO3.3 and RO3.3A scenario-count convergence remain FAIL / UNRESOLVED** under the frozen criteria,
  at every ladder rung through 5,000 scenarios. Thresholds were not relaxed and decisions were not edited.
- The **optimizer was not rerun** in the latest verification; its integrity gates were re-checked over
  frozen outputs (163/163 PASS, hypervolume max |Δ| = 0.0).
- **Decision-level materiality thresholds remain unfrozen**, so decision stability is reported, not passed.
- **Five decision-level artifacts remain unregistered** (`08_INDEX/REGISTRY_GAPS.md`).
- **Formal SLR, verified bibliography, citation-to-claim map and journal choice remain outstanding.**

## 5. Large inputs NOT included

The six frozen RO3 scenario-ladder CSVs (N = 100 / 250 / 500 / 1000 / 2500 / 5000, ~594 MB total) are
**not** copied here. They remain at `results/RO3/scenario_generation/` in the repository, where three of
them (N=1000/2500/5000, ~574 MB) are **gitignored and therefore not in version control at all**.

Their sizes and SHA-256 hashes are recorded in `06_REPRODUCIBILITY/SCENARIO_INPUT_SHA256.txt`:

- N=1000 and N=2500 **match** their previously recorded authoritative hashes.
- **N=5000 has no prior authoritative hash anywhere in the repository**; the hash recorded there is
  **newly recorded on 2026-10-26** and must not be described as previously verified.
- N=100/250/500 are git-tracked and were clean against HEAD, so their integrity is guaranteed by Git.

Full reproduction of the reported RO3 experiments requires access to those inputs, or an **authorised**
regeneration from the frozen contract (master seed 32027, 11 origins, 4 materials, horizons 1/3/6/12).
Regeneration was **not** attempted and is an expensive research experiment.

Also excluded: intermediate forecasting experiment outputs, the 9A/9B real-data phases, debug scripts,
npm/Playwright dependency and runner residue, caches, virtual environments and runtime logs.

## 6. Verification performed for this build (2026-10-26)

- Every copy hash-verified against its source — **0 mismatches, 0 missing sources**.
- New PDF built from the working-tree Markdown: **16 pages, 7 embedded images, 0 missing figures,
  no blank pages**, citation clusters A1–A5 / B1–B4 / C1–C5 present.
- The previously committed PDF in the repository was **left untouched**.
- Figure/table indexes computed from the actual files in this folder (7 figures, 10 tables).
- Artifact registry re-read: 45 registered entries, 12 known-unregistered entries — unchanged.
- **No test suite was run** in this phase (Phase 2 rule), and **no browser end-to-end verification was
  performed**. Prior browser evidence in `05_EVIDENCE/external_data_e2e/` and
  `05_EVIDENCE/smoke_evidence/browser_report_phase2.json` is **REPORTED BUT NOT REPRODUCED** and
  predates the source HEAD.

## 7. Integrity check

```bash
cd CMIDO_PUBLICATION_FREEZE
sha256sum -c 08_INDEX/MANIFEST.sha256      # on Linux/macOS
# or on Windows (PowerShell):
Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notlike '*MANIFEST.sha256' } |
  ForEach-Object { "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(),
    (Resolve-Path $_.FullName -Relative) }
```
