# CMIDO — Reproducibility Statement

**Repository:** `Sanjayram3269/CMIDO`
**Branch:** `main`
**Frozen dashboard checkpoint:** `c100b477ed8b79e8cdf1384ecfddd80b136adb78`
**Packaging session:** 2026-10-14

This statement records how the final package was produced and how it can be reproduced.

## How the package was produced

1. The frozen dashboard checkpoint was verified to be synced with `origin/main`.
2. The 8M, 8N, 8O, 8P, 8Q, 8R, and 8S gates were executed from the frozen result files.
3. The 8Q publication tables and 8R publication figures were verified against their declared sources.
4. The 8S reconciliation was used as the stronger numeric check.
5. The full construction + optimization regression suite was run as the final verification.
6. The editable manuscript and review copy were assembled from the frozen evidence and existing documentation.
7. The package folder was populated with figures, tables, supplementary pointers, audit pointers, reproducibility
   notes, and the supervisor-review message.

## What is source of truth

The source of truth for the manuscript’s numbers is the frozen result files and the 8Q/8R publication artifacts
generated from them.

Reproducibility does not depend on this package folder alone; it depends on the repository plus the result files
under `results/` plus the generation scripts.

## Results not recomputed in this packaging step

No new scientific results were generated in this packaging step. The tables and figures in this package are copies
of the already-frozen 8Q/8R artifacts for convenience.

## Environment summary

- Repository root: `D:/CMIDO`
- Branch: `main`
- HEAD: `c100b477ed8b79e8cdf1384ecfddd80b136adb78`
- `origin/main`: same SHA
- Python: 3.12.10
- OS: Windows
- Architecture: AMD64
- Tracked working tree at packaging time: clean
- Pre-existing untracked artifacts: preserved

## Seeds and configuration references

- RO3.6 uses 11 locked forecast origins, 4 common materials, and 12 realized months per origin/material.
- The inference unit is the forecast origin.
- Uncertainty uses paired bootstrap and Benjamini–Hochberg multiplicity control.
- Exact seeds and configuration details are recorded with the result artifacts and generation scripts.

## Source/result manifest

A machine-readable manifest is recorded at:

- `results/CMIDO_FINAL_PACKAGE_MANIFEST.json`

It records the repo head, origin head, repo sync status, environment summary, and the status of each evidence gate.

## Final verification command

```bash
cd /d/CMIDO
git fetch origin main
git checkout main
git rev-parse HEAD
git rev-parse origin/main
git status --short

python -m pytest tests/construction/ tests/optimization/ -q --tb=line
```

The final regression result for this packaging session was:

- 1059 passed
- exit code 0

A more focused freeze-relevant suite also passes:

```bash
cd /d/CMIDO
python -m pytest \
  tests/construction/test_dashboard_10a14.py \
  tests/construction/test_dashboard_10a13.py \
  tests/construction/test_dashboard_shell.py \
  tests/construction/test_dashboard_ui.py \
  tests/construction/test_dashboard_artifact_adapters.py \
  tests/construction/test_dashboard_app_contract.py \
  tests/construction/test_dashboard_10a9.py \
  tests/construction/test_dashboard_10a10.py \
  tests/construction/test_dashboard_10a11.py \
  tests/construction/test_dashboard_10a12.py \
  tests/optimization/ \
  -q --tb=line
```

## Limitations of reproducibility here

- This package is delivered as markdown plus figures and tables. A rendered PDF may be requested separately if a
  confirmed PDF toolchain is available.
- Some dashboard widget/button labels render only at runtime and are not asserted as visible labels in the
  headless AppTest surface.
- Reported SHA-256 fingerprints in prior artifacts have not been recomputed and verified in this packaging session;
  8S verifies source/file consistency under the declared rules, but that is not the same as recomputing every
  previously reported fingerprint from scratch.

## Stop condition

This reproducibility statement supports a review draft, not a submission claim. It is not sufficient on its own to
claim journal-submission readiness.

<!-- End of reproducibility statement. -->
