# An Uncertainty-Aware Machine Learning and Multi-Objective Optimization Framework for Resilient Construction Material Procurement

**Working title**

*An Uncertainty-Aware Machine Learning and Multi-Objective Optimization Framework for Resilient
Construction Material Procurement*

**Type of document:** draft manuscript for supervisor review
**Status:** review draft, built from frozen evidence
**Repository:** `Sanjayram3269/CMIDO`, branch `main`
**Frozen dashboard checkpoint:** `c100b477ed8b79e8cdf1384ecfddd80b136adb78`
**Session packaged:** 2026-10-14

> This is a draft manuscript assembled for supervisor review. It is built from frozen result artifacts and
> existing project documentation. It is not a submission-ready claim. Open research-side limitations are
> recorded in §12 and in the package README.

---

## Abstract

Construction-material procurement is made under several interacting uncertainties: material prices vary over
time, material demand is uncertain, and supply-side behaviour including delivery performance and disruption
can affect availability. This paper develops and evaluates an uncertainty-aware framework that links
probabilistic price and demand forecasting with joint uncertainty propagation and multi-objective procurement
optimization.

The framework has three stages. First, probabilistic machine-learning forecasts for construction-material price
and demand are produced with calibrated predictive uncertainty rather than point predictions only. Second, the
predictive demand uncertainty is propagated jointly with an admissible supply/process-duration representation to
estimate shortage and service risk. Third, the resulting risk information is consumed by a multi-objective
procurement optimization formulation producing cost, shortage and supply-risk trade-offs.

The empirical environment combines Singapore construction-material price and demand activity with the SUCCESS
construction logistics benchmark used as an operational simulation environment. The controlled evaluation uses
11 locked forecast origins, 4 common materials, and a common realized realization path, with paired
bootstrap inference and Benjamini–Hochberg multiplicity control at the forecast-origin level.

The central empirical question is whether retaining predictive uncertainty through the forecast, propagation,
and decision layers produces measurably different procurement outcomes under the declared evaluation design —
with the direction, magnitude, and desirability of those differences reported explicitly per objective, and with
the cases where effects are statistically supported distinguished from the cases where they are not. The evidence
is reported honestly across multiple objectives and configurations, including cases where effects are significant
and cases where they are not. No single controller is claimed universally optimal, and scenario-based results are
not presented as observed real-world outcomes.

**Keywords:** construction-material procurement; probabilistic forecasting; uncertainty propagation;
shortage and service risk; multi-objective optimization; resilience; reproducibility.

---

## 1. Introduction and research problem

Procurement of construction materials is exposed to several interacting sources of uncertainty. Prices for
materials such as cement, aggregates, ready-mixed concrete and steel reinforcement evolve over time. Material
demand on a project is uncertain. Supplier and logistics performance, including delivery timing and possible
disruption, affects what can actually be supplied when it is needed. Procurement decisions — what to buy, when,
in what quantity, and from which sources — affect cost, inventory, shortage, excess material, and the ability
of a project to maintain its planned service and schedule.

A broad construction supply-chain and forecasting literature exists around price forecasting, demand forecasting,
supply-chain risk, uncertain lead times, stochastic and robust procurement, supplier selection, and
multi-objective optimization. This project does not claim novelty in any of those components individually.

The narrower research problem is the **decision-centric handoff of predictive uncertainty**. Predictive
information is not necessarily retained and propagated in a decision-active form from forecasting through
supply uncertainty and into procurement decisions. This project therefore asks whether predictive distributions,
rather than only point forecasts, can produce measurably different procurement outcomes when transformed into
shortage/service risk and consumed by a procurement decision model.

The central research question is:

> Can predictive uncertainty be propagated through supply and process-duration uncertainty to produce measurably
> different construction-material procurement outcomes under a controlled evaluation design?

The intended contribution is the controlled, uncertainty-preserving chain from forecasting to uncertainty to risk
to decision, not a claim that forecasting, risk modelling, supplier selection, or optimization is individually
novel.

---

## 2. Related work and evidence-supported research gaps

Related work in this area includes: construction-material price and demand forecasting; probabilistic,
interval, and quantile prediction; construction supply-chain risk and disruption modelling; uncertain lead times
and supplier reliability; stochastic, robust, and chance-constrained procurement and inventory formulations;
supplier selection; and multi-objective procurement and cost–service trade-off analysis.

CMIDO does not treat any of those bodies of work as unobserved. The project’s contribution is narrower and is
framed around three gaps that are provisionally frozen from the current evidence audit and remain conditional on
final formal literature screening:

**Gap 1 — Predictive uncertainty propagation.** Although probabilistic and interval construction forecasting
exists, the direct propagation of empirically calibrated predictive distributions into downstream
construction-material procurement decisions is not fully established. The question is not whether probabilistic
forecasting exists, but whether retaining predictive uncertainty produces measurably different procurement
outcomes compared with equivalent point forecasts.

**Gap 2 — Joint demand–supply/process-duration propagation into shortage/service risk.** Existing studies model
demand uncertainty and supply-side uncertainty in various forms, but the joint propagation into a
decision-dependent shortage/service-risk distribution is not fully established. Shortage is treated primarily as
a derived consequence of interacting uncertainties rather than as a separately trained classifier.

**Gap 3 — Decision-level incremental validation.** Whether predictive uncertainty creates additional procurement
decision value is not fully isolated through controlled component-level and decision-level comparisons. The
question is how much of the final difference comes from forecasting uncertainty, formal optimization, and their
integration.

These gaps map to three research objectives: probabilistic forecasting, joint uncertainty propagation, and
multi-objective procurement optimization.

---

## 3. Research objectives, questions, and contributions

**RO1 — Probabilistic forecasting.** To develop and evaluate probabilistic forecasting models for
construction-material price and demand, producing calibrated predictive distributions for downstream use.

RQ1: To what extent do probabilistic machine-learning forecasting models improve predictive accuracy, calibration,
and uncertainty representation for construction-material price and demand compared with statistical and
point-forecast baselines?

**RO2 — Joint uncertainty propagation.** To develop a joint uncertainty-propagation mechanism that combines
predictive demand uncertainty with an admissible supply/process-duration representation to quantify
construction-material shortage and service risk.

RQ2: How does jointly propagating demand and supply/process-duration uncertainty affect shortage and
service-risk estimates compared with deterministic, demand-only, and supply-only representations?

**RO3 — Procurement decision optimization.** To develop and evaluate an uncertainty-aware multi-objective
procurement optimization framework that converts predictive and supply-risk information into procurement
quantity, timing, and supplier-allocation decisions.

RQ3: Does integrating predictive uncertainty and joint supply-risk information into procurement optimization
produce measurably different cost–service–resilience trade-offs than deterministic and component-wise alternatives
under normal and stressed conditions?

The intended contribution is the controlled forecast → uncertainty → risk → decision chain, evaluated with
paired origins and explicit uncertainty and multiplicity handling, without claiming universal superiority.

---

## 4. Data sources, provenance, and admissible modelling constructs

Three data environments are used.

**Dataset A — Singapore construction-material prices.** Monthly construction-material price activity is the
primary empirical RO1 environment. Prices are treated as observed quantities where the source supports that
interpretation.

**Dataset B — Singapore construction-material demand.** Monthly construction-material demand activity is the
primary empirical RO1 demand environment.

**Dataset C — SUCCESS construction logistics.** The SUCCESS benchmark is used as an operational construction
simulation environment for RO2/RO3. It provides sites, suppliers, material demand, origin/destination structure,
distances and travel times, and truck/capacity information. It is used for network structure, supplier/site
relationships, operational demand, transport/logistics structure, and scenario/simulation behaviour. It is not
treated as a complete historical procurement-order/delivery dataset.

This distinction matters: **SUCCESS travel time is not relabeled as historical procurement lead time**, and
static supplier/catalog lead times are not represented as realized historical delivery lead times. Where a
required construct is not observed, it is modeled as estimated or scenario-generated only, and that provenance is
made explicit.

**Provenance taxonomy.** Every quantity is labeled as one of:

- **OBS** — directly observed/raw dataset quantity
- **DER** — deterministically derived from observed or frozen inputs
- **EST** — estimated or model-generated quantity
- **SCN** — scenario-generated quantity used for simulation/stress analysis

These labels are preserved in manuscript tables, figures, and supplementary material. OBS, DER, EST, and SCN are
not silently interchanged.

**Admissible modelling view.** The RO2 propagation uses an explicitly documented admissible duration/process
representation. Its semantic role is preserved: process-duration data support the propagation construct they are
documented for, and are not promoted to supplier-specific historical lead time without independent evidence.

---

## 5. RO1 probabilistic forecasting methodology and evaluation

RO1 develops probabilistic forecasts for construction-material price and demand. The forecasting role is to
produce point predictions together with predictive uncertainty, so that downstream stages can consume distributions
rather than only point estimates.

The candidate modelling space includes statistical baselines such as seasonal naive, ETS, and ARIMA/SARIMA where
appropriate, and machine-learning baselines such as gradient boosting and XGBoost/LightGBM, with probabilistic or
quantile extensions where supported. Deep or sequence models are used only where justified by the data and the
forecasting role. Model selection is justified by literature, data characteristics, computational cost, forecasting
role, and fairness of comparison rather than by maximizing the number of algorithms.

Forecast validation uses expanding-window rolling-origin backtesting rather than random train/test splits. The
evaluation design uses multiple forecast horizons, with a primary tactical horizon unless the final application
analysis justifies another. Exact training/validation/test boundaries are generated from the final cleaned dataset
rather than hard-coded.

Forecast evaluation separates **point accuracy** from **uncertainty quality**. Point metrics include MAE, RMSE,
and sMAPE where appropriate. Probabilistic quality includes pinball loss, CRPS where supported, prediction-interval
coverage, interval width/sharpness, and calibration. Where appropriate, forecast comparison uses Diebold–Mariano
testing.

The manuscript does not conflate point accuracy with uncertainty quality. A model can be useful for uncertainty
representation even when its point accuracy is not uniformly best, and vice versa. The conclusion reports both and
does not equate non-significance with equivalence.

**Frozen source.** The calibrated forecast representation used downstream is
`results/forecasting/probabilistic_calibration/RO1_step26c3_validation_forecasts.csv`. The forecast evaluation
metrics are reported in `results/8Q_publication_artifacts/T1_RO1_validation_metrics.csv` and reconciled against
`results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv`.

---

## 6. RO2 joint uncertainty propagation and shortage/service-risk methodology

RO2 links predictive demand uncertainty with an admissible supply/process-duration representation to estimate
shortage and service risk.

The conceptual mechanism is that demand during an uncertain lead/process duration is the accumulation of
uncertain demand over an uncertain interval, which produces a distribution of required supply, an available-supply
distribution, a shortage distribution, and a service probability. This is treated as a derived consequence of
interacting uncertainties, not as a separately trained shortage classifier.

Propagation is implemented primarily through Monte Carlo methods, with documented convergence evidence for the
Monte Carlo draw lock. Demand and process-duration dependence is not assumed independent automatically; dependence
is tested where data permit.

The RO2 result families used in this manuscript are:

- joint propagation summary,
- tail comparison by representation,
- propagation summary across the evaluated population,
- service-risk curve,
- joint/independent sensitivity.

The frozen source result files are:

- `results/RO2/distribution/RO2_step27c3_joint_propagation_summary.csv`
- `results/RO2/distribution/RO2_step27c3_tail_comparison.csv`
- `results/RO2/propagation/RO2_step27d_propagation_summary.csv`
- `results/RO2/propagation/RO2_step27d_service_risk_curve.csv`
- `results/RO2/propagation/RO2_step27d_joint_vs_independent_sensitivity.csv`

The admissible process/duration representation is documented in
`results/RO2/data_audit/RO2_step27b4_admissible_modelling_view.csv`.

**Interpretation boundary.** The propagation evidence reports how the frozen demand uncertainty and admissible
duration representation propagate into shortage/service-risk outcomes under the documented modelling view. It does
not establish supplier-specific historical lead-time behaviour unless independently supported.

---

## 7. RO3 multi-objective procurement formulation, constraints, and evaluation

RO3 converts predictive and supply-risk information into procurement decisions through multi-objective
optimization.

The decision vector includes procurement quantities, order activation, and safety stock. Supplier allocation is
derived from procurement quantities. The formulation treats cost, shortage, and supply-risk exposure as distinct
objectives and produces a Pareto set rather than an arbitrarily weighted single optimum.

**Constraints and data support.** Where supported by the data, constraints such as supplier capacity, minimum
order quantity, storage capacity, and budget are considered. Feasibility is not asserted where constraint evidence
is absent. Supplier allocation, safety stock, and storage/supplier capacity constraints that are not supported by
registered evidence are explicitly unavailable rather than assumed zero.

**Important scope note.** Supplier allocation `y(i,s,t)` and safety stock `ss(i,t)` are **not** decision outputs of
the experiment reported here unless supported by registered evidence. The formulation notes that these variables
are deliberately excluded from the decision surface in this experiment, not inferred from procurement quantities.

**Controller freeze and controlled experiment.** The RO3.6 controlled ablation uses four arms:

- O1 — deterministic information + heuristic control
- O2 — deterministic information + formal optimization
- O3 — probabilistic information + heuristic control
- O4 — probabilistic information + formal uncertainty-aware optimization

The common design uses 11 locked forecast origins, 4 common materials, and 12 realized months per origin/material,
with common realized demand and price paths, an origin-level inferential unit, paired bootstrap uncertainty, and
Benjamini–Hochberg multiplicity correction.

The controlled experiment is an attribution study. It can establish empirical differences among the predefined
configurations, but it does not by itself establish broad causal or population-level superiority beyond the declared
design.

**Frozen sources.** The RO3 optimization evidence is drawn from the multi-origin decision and Pareto artifacts in
`results/RO3/multi_origin/`, the controlled ablation sources in
`results/RO3/ablation/final_comparison/`, and the stress/robustness artifacts in
`results/RO3/ablation/RO3_7_stress/` and `results/RO3/ablation/RO3_8_robustness/`.

The publication tables used in this manuscript are:

- `results/8Q_publication_artifacts/T5_RO3_baseline_comparison.csv`
- `results/8Q_publication_artifacts/T5_T6_controller_descriptives.csv`
- `results/8Q_publication_artifacts/T6_RO3_ablation.csv`

These are reconciled against:

- `results/RO3/ablation/final_comparison/RO3_step36_statistical_pairwise_comparisons.csv`
- `results/RO3/ablation/final_comparison/RO3_step36_primary_ablation_results.csv`
- `results/RO3/ablation/final_comparison/RO3_step36_controller_descriptive_statistics.csv`

---

## 8. Experimental setup, baselines, ablations, statistical methods, and reproducibility

**Evaluation population.** RO3.6 uses 11 locked forecast origins and 4 common materials, with a common realized
demand and price path across configurations. The inferential unit is the forecast origin, not individual monthly
observations within an origin.

**Baselines and arms.** O1 and O3 are intentionally transparent heuristic benchmarks, not state-of-the-art
heuristic optimizers. O2 is a deterministic ablation of the formal optimization pipeline, not an independently
developed optimization method. O4 is the integrated uncertainty-aware configuration.

**Statistical methods.** Origin-level contrasts use paired structure with bootstrap uncertainty intervals and
Benjamini–Hochberg multiple-comparison control. Results report effect direction, uncertainty intervals, and
significance status, without overstating population-level generalization from 11 repeated temporal cases.

**Reproducibility.** The manuscript relies on the frozen result files above. The final reproducibility package
records the environment, seeds where available, result paths, table/figure generation paths, and the exact
regression command used for final verification.

---

## 9. Results

This section reports the frozen publication results. All numbers come from the 8Q publication tables and their
declared source files. No new experiments are run in this packaging step.

### 9.1 RO1 forecasting and calibration

The RO1 evidence is reported from `results/8Q_publication_artifacts/T1_RO1_validation_metrics.csv`. The table
reports dataset, series, horizon, sample sizes, point-accuracy metrics, and prequential coverage/width/Winkler
results for the calibrated forecasts.

Key reporting discipline:

- Point accuracy and uncertainty quality are reported separately.
- Coverage and interval width are interpreted together, not in isolation.
- No claim is made that a forecasting model is universally best; performance is reported for the declared horizons,
  series, and evaluation design.

The publication table is a calibrated-forecast-facing projection of the broader
`results/forecasting/probabilistic_calibration/RO1_step26c3_validation_metrics.csv` source. It drops the `raw_*`
coverage/width/Winkler columns and retains the prequential-calibrated columns; the shared numeric values are intact.

### 9.2 RO2 propagation and service risk

The RO2 evidence is reported from the 8Q publication tables derived from the RO2 source files listed in §6.

- `T2_RO2_joint_propagation_summary.csv` — joint propagation summary.
- `T2_RO2_tail_comparison.csv` — tail behaviour by representation.
- `T3_RO2_propagation_summary.csv` — propagated demand/shortage/service behaviour over the evaluated population.
- `T3_RO2_service_risk_curve.csv` — service-risk curve.
- `T3_RO2_joint_independent_sensitivity.csv` — sensitivity to joint versus independent propagation assumptions.

The manuscript does not claim that the admissible duration representation equals supplier-specific historical lead
time. It reports the propagation behaviour under the documented admissible representation and notes the sensitivity
of conclusions to the joint/independent assumption.

### 9.3 RO3 baseline comparison and controller descriptives

The RO3 controlled evidence is reported from:

- `results/8Q_publication_artifacts/T5_RO3_baseline_comparison.csv`
- `results/8Q_publication_artifacts/T5_T6_controller_descriptives.csv`

The controller descriptive table reports, for each controller, the realized holding cost, shortage, service level,
shortage CVaR, procurement quantity, ending inventory, and procurement-event summaries across the 11 locked
origins.

The baseline comparison table reports the planned contrasts among O1, O2, O3, and O4. The contrasts reported
include:

- O2 versus O1 — optimization under deterministic information
- O3 versus O1 — probabilistic information under heuristic control
- O4 versus O2 — incremental uncertainty under optimization
- O4 versus O3 — incremental optimization under probabilistic information
- O4 versus O1 — integrated O4 versus deterministic heuristic

The reported contrasts distinguish **differences in one objective** from **trade-offs in another**. For example,
the O2 versus O1 contrast can show lower holding cost with higher shortage, while the O4 contrasts show materially
different cost/shortage/service trade-offs from the deterministic and probabilistic-heuristic configurations.

The publication baseline table is a projection of the source
`results/RO3/ablation/final_comparison/RO3_step36_statistical_pairwise_comparisons.csv`. It keeps the core
contrast/metric/estimate/inference columns and drops additional per-contrast control columns; the shared numeric
values are identical.

### 9.4 RO3 ablation

The RO3 ablation evidence is reported from `results/8Q_publication_artifacts/T6_RO3_ablation.csv`. The ablation
table reports the same contrasts as the baseline table but with the richer per-contrast detail needed for the
ablation interpretation: relative change, bootstrap bounds, improved/worsened/tie counts, rank-biserial sign, and
significance after multiplicity correction.

The ablation interpretation emphasizes attribution: which component changes are associated with which objective
changes, and where significance is and is not achieved. The manuscript does not treat non-significance as evidence
of equivalence.

The ablation table is generated from
`results/RO3/ablation/final_comparison/RO3_step36_primary_ablation_results.csv` and shares its schema and values.

### 9.5 Stress and robustness

Stress and robustness results exist in the repository and are reported as available evidence, with the limitation
that their manuscript wording and table/figure binding are completed as part of the final concordance work.

Stress artifacts:

- `results/RO3/ablation/RO3_7_stress/RO3_step37_stress_summary.csv`
- `results/RO3/ablation/RO3_7_stress/RO3_step37_stress_paired_changes.csv`
- `results/RO3/ablation/RO3_7_stress/RO3_step37_stress_audit.csv`

Robustness artifacts:

- `results/RO3/ablation/RO3_8_robustness/RO3_step38_holding_rate_summary.csv`
- `results/RO3/ablation/RO3_8_robustness/RO3_step38_holding_rate_controller_contrasts.csv`
- `results/RO3/ablation/RO3_8_robustness/RO3_step38_holding_rate_sensitivity_vs_H30.csv`
- `results/RO3/ablation/RO3_8_robustness/RO3_step38_holding_rate_audit.csv`

These are used to report variation under declared stress and holding-rate sensitivity settings, not to claim that
all procurement behaviour under all regimes is established.

### 9.6 Integrated decision-value summary

The integrated claim reports whether the complete forecast → uncertainty → risk → decision chain is supported by
the combined evidence set, with explicit scope. The current evidence supports reporting that the chain is
empirically represented in the frozen artifacts and that the controlled contrasts show measurable differences among
the predefined configurations. The manuscript does not claim universal superiority or claim that the result
generalizes beyond the declared evaluation design without additional evidence.

---

## 10. Discussion and interpretation of incremental decision value

The discussion interprets the results as an attribution study.

The O1 → O2 contrast isolates the effect of formal optimization under deterministic information. The O1 → O3
contrast isolates the effect of probabilistic information under heuristic control. The O2 → O4 and O3 → O4
contrasts isolate the incremental effect of integrating uncertainty-aware information with optimization. The O1 → O4
contrast reports the integrated effect against the deterministic heuristic baseline.

Interpretation discipline:

- A contrast that differs in one objective may differ in another; this is reported as a trade-off, not as
  unambiguous improvement.
- Significance is reported per contrast and per metric with multiplicity control.
- Non-significant results are reported honestly and not treated as equivalence.
- The O4 configuration does not dominate every objective in every contrast; the result is a Pareto-relevant set of
  trade-offs rather than a single winner.
- The controlled experiment uses 11 origins; generalization claims are therefore limited and explicitly scoped.

The framing of incremental decision value is therefore: under the declared evaluation design, the uncertainty-aware
configuration changes the cost, shortage, and service trade-off surface relative to the deterministic and
probabilistic-heuristic configurations in ways that are measurable and, for several contrasts, statistically
supported. The magnitude and desirability of those trade-offs depend on the objective weighting and on the
evaluation scope, which are not claimed to be universal.

---

## 11. Limitations, assumptions, and threats to validity

### Assumptions requiring explicit disclosure

1. The selected RO1 predictive representation is treated as the frozen input to downstream decision experiments.
2. The RO2 admissible duration representation is used according to its documented semantic role; it is not
   relabeled as supplier-specific historical lead time unless independently supported.
3. Scenario-generated uncertainty is distinguished from direct observation.
4. The RO3.6 comparison uses paired forecast origins rather than treating monthly observations within an origin as
   independent replicates.
5. O1 and O3 are intentionally transparent heuristic benchmarks, not state-of-the-art heuristic optimizers.
6. O2 is a deterministic ablation of the formal optimization pipeline, not an independently developed optimization
   method.
7. O4 realized-policy evaluation and O4 stochastic optimization objectives are distinct analytical layers and are
   not conflated.
8. Any final manuscript aggregation preserves the exact evaluation population and frozen controller/configuration.

### Threats to validity

- **Construct validity.** Forecast uncertainty, process duration, shortage, service, and resilience are represented
  through operational variables and model constructs; their correspondence to real procurement phenomena must be
  documented rather than assumed.
- **Internal validity.** Temporal leakage, outcome-based tuning, inconsistent evaluation populations, and post-hoc
  origin removal would undermine attribution. The frozen controller and common-realization gates are designed to
  constrain these risks.
- **Statistical validity.** 11 origins are repeated temporal cases; small-sample paired inference should be reported
  with uncertainty intervals and multiple-comparison control, without overstating population-level generalization.
- **External validity.** The primary empirical environment is Singapore construction-material activity and the
  SUCCESS construction logistics benchmark. Results should not be presented as automatically representative of all
  geographies, contractors, suppliers, materials, or market regimes.
- **Implementation validity.** Result-producing scripts should remain executable from a clean checkout; hard-coded
  developer-specific absolute paths are treated as reproducibility defects.

### Explicit data limitations

- SUCCESS travel time is not relabeled as historical procurement lead time.
- Static supplier/catalog lead times are not represented as realized historical delivery lead times.
- Supplier capacity, minimum order quantities, storage capacity, and disruption/partial-delivery probabilities are
  treated as estimated or scenario-generated where not observed, and their provenance is kept explicit.

### Package-level limitations

1. Five decision-level artifacts are registered but not present in the artifact inventory:
   `RO3_O2_SELECTED_DECISIONS`, `RO3_O2_REALIZED_EVALUATION_SUMMARY`,
   `RO3_O4_REALIZED_EVALUATION_LEDGER`, `RO3_MULTI_ORIGIN_SUMMARY`, `RO3_DECISION_SENSITIVITY`.
2. `RO1_PRIMARY_H3_SUMMARY` and `EVIDENCE_8P_MANIFEST` are registered but not adapted into evidence bundles.
3. Reported SHA-256 fingerprints have not been recomputed and verified in this packaging session.
4. Presence checks for unregistered files are existence-only.
5. RO3 500→1,000 scenario convergence failed; the recorded next required evaluation is 2,500, then 5,000.
6. Observed-stream dates, authorship, and software-version metadata are unavailable.
7. Additional master-spec stress scenarios have no recorded results; none were fabricated.
8. Simulated/derived/scenario results are never described as observed real-world outcomes.

---

## 12. Conclusion and future work

This paper developed and evaluated an uncertainty-aware forecast → propagation → risk → decision framework for
construction-material procurement. The framework links probabilistic price and demand forecasting, joint
uncertainty propagation with an admissible supply/process-duration representation, and multi-objective procurement
optimization.

Under the declared evaluation design, the evidence supports reporting measurable differences among the predefined
O1/O2/O3/O4 configurations and explicit trade-offs among cost, shortage, and service objectives. The integrated
uncertainty-aware configuration changes the procurement trade-off surface relative to deterministic and
probabilistic-heuristic configurations in ways that are measurable and, for several contrasts, statistically
supported. The work does not claim universal superiority, does not relabel travel-time data as historical lead
time, and does not present scenario results as observed real-world outcomes.

Future work should include:

- resolving the remaining decision-level evidence registration and adaptation gaps;
- completing the RO3 scenario-convergence evaluation path specified for the failed 500→1,000 gate;
- establishing supplier-specific historical lead-time evidence only where independently supported;
- broadening the empirical environments if broader claims are to be made;
- completing the final manuscript claim-to-evidence concordance and a rendered review copy;
- freezing the final repository state and reproducibility package.

---

## 13. References and supplementary-material index

References are intentionally not invented in this draft. Any citation used in the final manuscript must support the
statement it is attached to. The final reference list will be assembled from the actual literature used during the
research and will be checked against the claims it supports.

The supplementary-material index will point to:

- the frozen publication tables in `results/8Q_publication_artifacts/`;
- the frozen publication figures in `results/8R_publication_figures/`;
- the upstream RO1/RO2/RO3 source files listed above;
- the 8M/8N/8O/8P/8Q/8R/8S manifests and audit files;
- the reproducibility package in `06_REPRODUCIBILITY/` of this folder.

---

## 14. Data/code availability and reproducibility statement

The frozen result files used in this manuscript are stored in the CMIDO repository under `results/`. The publication
tables and figures are generated from those sources by the scripts:

- `src/optimization/cmido_8q_publication_artifacts.py`
- `src/optimization/cmido_8r_publication_figures.py`
- `src/optimization/cmido_8s_numerical_reconciliation.py`

The final regression suite used for verification is:

```bash
cd /d/CMIDO
python -m pytest tests/construction/ tests/optimization/ -q --tb=line
```

The current full regression result for this packaging session was 1059 passed with exit code 0.

The final package manifest is recorded in `06_REPRODUCIBILITY/` and in
`results/CMIDO_FINAL_PACKAGE_MANIFEST.json`. It records the repository commit, environment summary, and the status
of each evidence gate.

**Reproducibility caveat.** This package reports the frozen artifact chain as internally consistent under the
manifest-defined checks and the numeric reconciliation in 8S. It does not claim that every result is externally
validated, causally established, or transferable beyond the declared evaluation design. Readers should treat
scenario, estimated, and derived quantities according to their provenance labels.

---

## Change log / conditional items

- Tables and figures: frozen 8Q/8R artifacts, reconciled in 8S. No new scientific results generated in this
  packaging session.
- Manuscript: draft assembled from existing evidence package and frozen artifacts. Numerical claims are traceable to
  the 8Q tables and their declared source files.
- Wording fixes applied in this packaging step:
  - the central empirical claim was tightened so that the manuscript reports *measurably different procurement
    outcomes with explicit direction, magnitude, desirability, and significance status per objective*;
  - the abstract no longer implies a directional overall superiority claim; it reports *measurably different
    outcomes* and explicitly distinguishes statistically supported effects from non-significant ones.
- Remaining open items: see §11 and the package README.

<!-- End of editable draft. Review copy is separate. -->
