# CMIDO — Claim Register

Generated 2026-10-26 from the repository's authoritative claim register at
`docs/CMIDO_EVIDENCE_CONCORDANCE.md`, section 4 ("Master claim register"). The claims below are
reproduced as recorded there; no claim was rewritten, added, removed or strengthened for this package.
The authoritative copy is mirrored at `05_EVIDENCE/CMIDO_EVIDENCE_CONCORDANCE.md`.

All claims are bound to the frozen publication artifact chain: 8Q tables, 8R figures, 8S reconciliation,
and the 8M/8N/8O/8P evidence-package manifests. Claims are drafted for the current review draft and are
**not** framed as universal superiority.

## Master claim register

| Claim ID | Draft claim | RO | Dataset | Experiment | Result source | Statistical evidence | Table | Figure | Manuscript section | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| C-RO1-001 | Retaining predictive uncertainty produces calibrated forecast outputs for the frozen RO1 evaluation design | RO1 | OBS price/demand (Singapore activity) | RO1 rolling-origin backtesting | `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv` → T1 | per-horizon coverage/width/Winkler + prequential metrics | T1 | F1 | §5, §9.1 | DONE-for-draft |
| C-RO1-002 | Point accuracy and uncertainty quality are reported separately; no model is claimed universally best | RO1 | OBS price/demand | RO1 rolling-origin backtesting | T1 + `results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv` | calibration/coverage reporting discipline | T1 | F1 | §5, §9.1, §10 | DONE-for-draft |
| C-RO2-001 | Joint propagation changes shortage/service-risk estimates under the documented admissible representation | RO2 | OBS + EST/SCN duration, RO1 quantiles | RO2 diffusion/aggregation over common scenarios | `results/RO2/propagation/RO2_step27d_propagation_summary.csv` → T3, `results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv` → T2, `results/RO2/propagation/RO2_step27d_service_risk_curve.csv` → T3 | propagation summary + service-risk curve | T2, T3 | F2, F3 | §6, §9.2 | DONE-for-draft |
| C-RO2-002 | Conclusions are sensitive to the joint/independent propagation assumption | RO2 | OBS + EST/SCN duration, RO1 quantiles | RO2 sensitivity analysis | `results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv` → T3 | joint/independent sensitivity | T3 | F4 | §6, §9.2 | DONE-for-draft |
| C-RO3-001 | RO3 optimization produces cost/shortage/service trade-offs under the frozen formulation | RO3 | OBS + SCN scenario, RO1/RO2 inputs | RO3 multi-origin N=2500 optimization | `results/RO3/multi_origin/RO3_step35_*_N2500.csv`, `results/RO3/ablation/final_comparison/RO3_step36_controller_descriptive_statistics.csv` → T5_T6 | controller descriptives, multi-origin Pareto summary | T5_T6 | F5 | §7, §9.3 | DONE-for-draft |
| C-RO3-002 | Controlled contrasts show measurable differences among O1/O2/O3/O4 under the declared design | RO3 | OBS + SCN scenario, common realizations | RO3.6 11-origin paired ablation | `results/RO3/ablation/final_comparison/RO3_step36_statistical_pairwise_comparisons.csv` → T5, `results/RO3/ablation/final_comparison/RO3_step36_primary_ablation_results.csv` → T6 | paired bootstrap + BH correction | T5, T6 | F6 | §7, §9.3, §9.4, §10 | DONE-for-draft |
| C-INT-001 | The forecast → uncertainty → risk → decision chain is empirically represented in the frozen artifacts; it is not claimed universally superior | RO1→RO2→RO3 | OBS/EST/SCN mix | integrated pipeline | T1, T2, T3, T5, T5_T6, T6 + multi-origin artifacts | integrated evidence registration | T1, T2, T3, T5, T5_T6, T6 | F1, F2, F3, F4, F5, F6 | §9.6, §10, §12 | DONE-for-draft |
| C-ROB-001 | Performance varies under declared stress/robustness settings | RO2/RO3 | SCN stress, SCN holding-rate sensitivity | RO3.7/RO3.8 stress/robustness | `results/RO3/ablation/RO3_7_stress/RO3_step37_stress_summary.csv`, `results/RO3/ablation/RO3_8_robustness/RO3_step38_holding_rate_summary.csv` → T4 | stress/robustness descriptive contrasts | T4 | none (no stress figure bound in this draft) | §9.5, §12 | DONE-for-draft |

## Status of each claim's source in this package

Every result source listed above is present in this package under `04_RESULTS/`, mirrored from the
repository path shown. The mapping from repository path to package path is in `08_INDEX/SOURCE_MAP.md`.
"**DONE-for-draft**" is the repository's own status string and means *the evidence chain exists for the
current draft*; it does **not** mean journal-ready.

## What this register does NOT contain (recorded gaps, not inventions)

1. **No citation-to-claim mapping.** Every claim above is bound to a *result artefact*, not to a
   literature reference. No file in the repository maps claims to citations; none was created here.
2. **No verified bibliography.** The manuscript now carries verified screening clusters A1–A5, B1–B4
   and C1–C5 with DOIs (see `01_MANUSCRIPT/CMIDO_DRAFT_MANUSCRIPT.md` §13 and
   `05_EVIDENCE/CMIDO_LITERATURE_REVIEW_AND_NOVELTY.md`). Those DOIs were **not resolved or verified**
   in this phase and must not be described as verified.
3. **No formal systematic literature review.** The literature work is targeted screening only
   (master specification §37 SLR still outstanding).
4. **No statistical-significance claim for RO1 superiority.** The frozen RO1 evidence is descriptive /
   mixed (see `08_INDEX/KNOWN_LIMITATIONS.md`).
5. **No convergence claim for RO3.3.** Scenario-count convergence is FAIL / UNRESOLVED.
