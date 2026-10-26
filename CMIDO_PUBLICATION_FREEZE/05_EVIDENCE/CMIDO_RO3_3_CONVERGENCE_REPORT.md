# CMIDO RO3.3 — Scenario-Set Convergence Report (Evaluated)

**Status: FAIL under the frozen criteria — convergence UNRESOLVED at every ladder rung through 5,000 scenarios.**

This report records the actual execution of the prescribed RO3.3 convergence evaluation, including
the 2,500-scenario evaluation that the prior session recorded as "next required". It does not
relax any threshold and does not edit any prior output: all four step33 artifacts were
re-generated from the frozen scenario inputs and verified byte-identical to the committed state
(SHA-256 below).

---

## 1. Authority and frozen acceptance criteria

- **Specification:** `docs/CMIDO_RO3_3_Scenario_Convergence_Specification_v1.0.md`
  (title: *Corrected Scenario-Set Convergence Specification v1.1*).
- **Frozen workflow:** `src/optimization/ro3_scenario_convergence.py` (implementation "RO3.3").
- **Frozen scenario ladder:** 100, 250, 500, 1000, 2500, 5000. Primary transition: 500 → 1000.
- **Metrics (14 per material-origin case, 44 cases, 616 comparisons per transition):**
  mean and q90 of demand, price, internal duration, PODN duration, total duration;
  mean, q90, q95, q99 of demand-during-procurement-duration exposure.
- **Comparison semantics (unchanged):** `relative_change = abs(B - A) / max(abs(A), 1e-12)`
  on consecutive (nested) scenario-set sizes.
- **Thresholds (unchanged):** means ≤ 1%; q90 metrics ≤ 2%; q95 exposure ≤ 2%; q99 exposure ≤ 5%.
  The frozen script additionally binds `mean_exposure ≤ 1%` and `q90_exposure ≤ 2%`, consistent
  with the specification's metric list.
- **Spec decision rule:** if the primary gate passes, candidate lock is 1000; otherwise evaluate
  2500, then 5000 if required. Passing establishes convergence of the scenario representation and
  propagation diagnostics only — **not** optimizer/Pareto-frontier convergence.

## 2. Inputs, configuration, seed

| Item | Value |
|---|---|
| Scenario files | `results/RO3/scenario_generation/RO3_step32_scenarios_{100,250,500,1000,2500,5000}.csv` |
| Master seed (generation) | `32027` (all run configs) |
| Origins / materials | 11 (2022-07-01 … 2023-05-01) / 4 (Cement, Granite, Ready Mixed Concrete, Steel Reinforcement Bars) |
| Row counts | 11 × 4 × 12 × N (e.g. 1,320,000 rows at N=2,500; 2,640,000 at N=5,000) |
| Generation audits | `RO3_step32_audit_{2500,5000}.csv` — 10/10 checks PASS, `RO3_2_AUDIT_PASS` |
| Nestedness | Ladder is prefix-nested per stream; nestedness audit PASS on every run |
| Input SHA-256 (1000) | `43be2ea2f78a0e6ce59e3541f8ab8dc9555de5a39666d544dc586caf84ab2ca4` |
| Input SHA-256 (2500) | `5fc3b74e16cab7cfc29a37d278072a9629f48bd96e0208eacfe96e6607b7be70` |

No scenario file was regenerated. The 2,500- and 5,000-scenario files pre-existed; artifact
existence alone was **not** treated as a result — the evaluation below was executed.

## 3. Execution record

```bash
environment/.venv/Scripts/python.exe src/optimization/ro3_scenario_convergence.py
# exit status: 0   (log: results/RO3/scenario_convergence/_step33_rerun_20261015.log)
```

Environment: `environment/.venv`, pandas 2.3.3, numpy 2.5.3 (Windows, 15.7 GiB RAM).

**Determinism check (before/after re-run, SHA-256):**

| Artifact | SHA-256 | Match |
|---|---|---|
| `RO3_step33_convergence_metrics.csv` | `eba18203b0ec89fa0f94cc3d62a9def1b9616cd56847118360bfa6fd2b0e29b2` | ✓ byte-identical |
| `RO3_step33_convergence_comparisons.csv` | `a4bd779aa98538688b286552239b8c7bd95d0bcb5d2befee7339e955b1081eb8` | ✓ byte-identical |
| `RO3_step33_summary.json` | `7e7ea0bae9809c87c7c1e68cfe9f27cf84f1ae4e5f4b2e7924ab092e1d65052e` | ✓ byte-identical |
| `RO3_step33_decision.txt` | `0f042bb34ae6c109ba637cef37ef3a9e6cb1e2f4f46fe29dab4c9e6801e295b8` | ✓ byte-identical |

The re-run reproduced the recorded failure fingerprint exactly (142 primary failed comparisons,
max relative change 0.176471) and produced outputs identical to the committed state. Input
scenario files were verified unchanged after the run.

## 4. Numerical results — all consecutive transitions (frozen criteria)

| Transition | Failed / 616 | Max relative change | Gate |
|---|---|---|---|
| 100 → 250 | 276 | 0.221134 | FAIL |
| 250 → 500 | 178 | 0.200000 | FAIL |
| **500 → 1000 (primary)** | **142** | **0.176471** | **FAIL** |
| **1000 → 2500 (prescribed 2,500 evaluation)** | **111** | **0.120627** | **FAIL** |
| **2500 → 5000 (final ladder rung)** | **52** | **0.111111** | **FAIL** |

Failures by metric family:

| Transition | demand | price | duration (6 metrics) | exposure (4 metrics) |
|---|---|---|---|---|
| 500 → 1000 | 0/88 | 0/88 | 91/264 | 51/176 |
| 1000 → 2500 | 0/88 | 0/88 | 68/264 | 43/176 |
| 2500 → 5000 | 0/88 | 0/88 | 32/264 | 20/176 |

Worst single comparison at the 2,500 rung: `q95_exposure`, Granite, origin 2022-11-01,
4737.31 → 5308.76 (relative change 0.120627, threshold 0.02).

The step33 summary `decision` field remains `RO3_3_EVALUATE_2500` because the frozen script's
decision logic is primary-gate only; the adjudication of the later rungs is performed in this
report against the same frozen thresholds and the same comparisons CSV
(`RO3_step33_convergence_comparisons.csv`, which contains every transition).

## 5. Diagnosis (evidence-backed)

**Not an implementation defect.** The nestedness audit passes on every run; all generation
audits pass 10/10; the ladder is prefix-nested per stream; the frozen script re-run is
byte-deterministic. No numerical instability (all values finite, duration reconstruction exact
to 1e-9) and no near-zero-denominator artifact: failing duration baselines are 11.5–86.0 days,
not values near the 1e-12 floor.

**Not Pareto/optimizer instability.** This gate contains no optimization quantities: it is
defined over scenario-representation metrics and propagation diagnostics only (spec §Metrics).
Optimizer/Pareto convergence is a separate, explicitly out-of-scope requirement
(`optimization_level_convergence_required_later: true`).

**What the failures actually are:**

1. **Demand and price marginals are converged.** 0 of 88 demand and 0 of 88 price comparisons
   fail at every transition, including the primary. The RO1-forecast-driven quantities satisfy
   the frozen thresholds comfortably.
2. **Duration means show textbook Monte Carlo decay.** Mean-internal-duration failures shrink
   31 → 17 → 11 across the ladder with relative changes of ~1.0–3.1% against the 1% threshold;
   the observed shrinkage (e.g. 2.38% → 1.49% from 1,000 → 2,500 → 5,000 scenarios) matches the
   expected 1/√N rate. These are slow convergence against tight thresholds, not instability.
3. **q90 duration quantiles are grid-locked by the discrete 37-row representation.** The
   worst persistent failures flip between exactly 18.0 and 20.0 days — integer support values of
   the empirical procurement-process-duration representation — giving relative changes of
   exactly 0.111111 (= 2/18) and 0.100000 at both 1000 → 2500 *and* 2500 → 5000. Where the
   population quantile lies near a step of the discrete support, no scenario count resolves it
   below the grid spacing: **the ≤2% relative threshold is unattainable for such cases at any
   N with this representation.**
4. **Exposure tails converge slowest.** Exposure compounds demand with duration, and its q95/q90
   failures concentrate in Granite origins (heavy tail); counts decay 51 → 43 → 20 but remain
   above zero at 5,000 scenarios.

The monotone ladder-wide decay of both failure counts (276 → 178 → 142 → 111 → 52) and maximum
relative change (0.221 → 0.200 → 0.176 → 0.121 → 0.111) is the signature of slow Monte Carlo
convergence of discrete-support duration statistics and heavy-tailed exposure quantiles against
1–5% relative thresholds — **not** of a coding error, rare stress events leaking into unrelated
metrics, or numerical breakdown.

## 6. The already-versioned domain-aware variant (RO3.3A) also fails

`src/optimization/ro3_scenario_convergence_domain_aware.py` ("RO3.3A") is an existing versioned
experiment that applies absolute-day thresholds to duration metrics (mean ≤ 1 day, q90 ≤ 2 days)
and relative thresholds elsewhere. Its frozen outputs
(`RO3_step33A_*`) show:

| Transition | Failed / 616 | Max change (days or relative) |
|---|---|---|
| 500 → 1000 (primary) | 82 | 10.0 |
| 1000 → 2500 | 65 | 6.0 |
| 2500 → 5000 | 27 | 6.0 |

RO3.3A therefore also FAILS at every rung (`RO3_3A_EVALUATE_2500`). The grid-locked 18 ↔ 20 day
flips alone exceed its 2-day q90 threshold. **No existing evaluation of the frozen ladder passes
under any recorded criterion set.**

## 7. Final status and disposition

**RO3.3 status: FAIL / UNRESOLVED.**

- Primary 500 → 1000 gate: FAIL (142 failures, max rel 0.176471) — recovered and reproduced
  exactly.
- Prescribed 1000 → 2500 evaluation: FAIL (111 failures, max rel 0.120627) — executed this
  session, exit 0, byte-deterministic.
- Final 2500 → 5000 rung (permitted by the spec ladder): FAIL (52 failures, max rel 0.111111).
- No thresholds were loosened; no prior outputs were edited; no scenario file was regenerated.

**Defensible disposition (recommended):**

1. **Record convergence as an explicitly unresolved limitation.** The manuscript must not claim
   scenario-count convergence of the RO3 duration/exposure diagnostics. Demand and price
   marginals *do* satisfy the frozen thresholds at every rung and may be reported as converged
   with the exact counts above.
2. **Structural incompatibility is now identified:** for q90 duration metrics whose population
   quantile sits on the 37-row empirical support boundary, the frozen ≤2% relative criterion is
   unattainable at any scenario count. Meeting it would require either (a) a higher-resolution
   duration representation — a methodological change requiring a new versioned experiment and
   professor sign-off, or (b) resolution-scale-aware criteria (e.g. one-grid-step tolerance),
   which would be a **new** criterion set, not a pass of this one.
3. **Additional computation is not justified by the evidence.** The failure structure (discrete
   grid-lock + 1/√N decay of means) does not predict a pass at N > 5,000: the grid-locked cases
   are count-invariant, and the ladder already ends at the spec maximum.

## 8. Reproducibility

```bash
# Full frozen evaluation (all six ladder rungs), exit status 0:
environment/.venv/Scripts/python.exe src/optimization/ro3_scenario_convergence.py
# Verify outputs match the frozen state:
sha256sum -c results/RO3/scenario_convergence/_preflight_hashes/step33_before.sha256
# Failure-family analysis:
python - <<'EOF'
import pandas as pd
c = pd.read_csv('results/RO3/scenario_convergence/RO3_step33_convergence_comparisons.csv')
print(c.groupby(['n_from','n_to']).agg(
    failures=('pass', lambda s: int((~s).sum())), max_rel=('relative_change','max')))
EOF
```

---

*Generated during the Final Scientific Closure Sprint (2026-10-15). Evidence:
`results/RO3/scenario_convergence/RO3_step33_*` (frozen, re-verified),
`RO3_step33A_*` (frozen variant), `results/RO3/scenario_generation/RO3_step32_*` (inputs),
`_preflight_hashes/` (determinism record), `_step33_rerun_20261015.log` (execution log).*
