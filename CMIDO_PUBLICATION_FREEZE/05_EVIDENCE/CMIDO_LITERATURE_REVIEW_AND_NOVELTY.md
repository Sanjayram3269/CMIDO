# CMIDO — Targeted Literature Screening, Novelty Positioning, and Journal Readiness

**Date:** 2026-10-18 (research-closure sprint)
**Status:** targeted screening to support the professor review — **not** the formal systematic literature
review (SLR) required by the master specification §37. The manuscript's conditional-novelty stance
(master spec §33 prohibited wording) is unchanged and remains in force until a formal SLR is completed.
**Evidence rule:** every source below was located and verified via web research during this sprint with a
resolvable DOI or URL. No reference is invented. Where a source could not be verified beyond its record
abstract, that limitation is stated inline.

---

## 1. What this screening was designed to test

Three gap statements drive CMIDO (master spec §4):

- **G1** — calibrated predictive distributions from construction-material forecasting are rarely handed
  off to downstream procurement decisions in a decision-active form.
- **G2** — joint propagation of demand uncertainty with supply/process-duration uncertainty into a
  decision-dependent shortage/service-risk distribution is not fully established in construction.
- **G3** — the incremental decision value of predictive uncertainty vs. formal optimization vs. their
  integration is rarely isolated by controlled ablation in construction procurement.

Each was screened for **counterexamples** (studies that already do it), because a gap claim that ignores
the closest prior art will not survive review.

---

## 2. Screened sources by cluster

### Cluster A — Probabilistic / interval forecasting of construction-material prices and demand

| # | Source | Verified identifier | What it establishes | Downstream decision use |
|---|--------|--------------------|---------------------|-------------------------|
| A1 | Mir, Kabir, Nasirzadeh & Khosravi (2021), *Journal of Building Engineering* — "Neural network-based interval forecasting of construction material prices" | doi:10.1016/j.jobe.2021.102288 | LUBE interval forecasts for US asphalt/steel; intervals outperform point estimates on their metrics | None (cost-risk framing only); calibration details not verified from the record |
| A2 | Assaf, Assaad, El-adaway & Nabi (2024), *Construction Research Congress 2024* — DeepAR probabilistic construction-cost forecasting | doi:10.1061/9780784485286.026 | DeepAR Monte-Carlo price samples for four material categories (conference paper) | None; no calibration/coverage reporting verified |
| A3 | Jezzini, Assaad & El-Adaway (2025), *J. Construction Engineering and Management* 151(7) — probabilistic deep learning → project cost-risk from material price volatility | doi:10.1061/JCEMD4.COENG-16055 | Predictive price distributions feed stochastic contract price-escalation risk analysis | **Yes — contract/escalation-clause risk**, not procurement ordering; calibration not verified from the record |
| A4 | Fouad, Wefki & Kouta (2025), *J. Supply Chain Management Science* — AI-driven raw-material demand forecasting | doi:10.59490/jscms.2025.8136 | XGBoost/LSTM/RF demand models on 4 years of construction-project consumption; reported 66.5% overstock reduction in planning | **Yes — inventory planning**, but point forecasts; no probabilistic calibration |
| A5 | Shiha & El-Adaway (2024), *J. Management in Engineering* 40(5) — material prices from trading-partner macro indicators | doi:10.1061/JMENEA.MEENG-6106 | VECM price forecasting, 18-month horizon | None; probabilistic |
| A6 | Ma, Tam, Le & Osei-Kyei (2024), *Int. J. Construction Management* 24(11) — SLR on price-forecasting models in construction | doi:10.1080/15623599.2023.2241761 | 34 studies 2012–2022; VECM/ANN/ARIMA dominate | Review; documents that probabilistic calibration is not a recurring practice |

**Cluster A finding.** Probabilistic/interval construction-material forecasting **exists** (A1–A3). No
verified study in this screening applies conformal prediction / CQR or gradient-boosting quantile
regression to construction-material prices or demand, and no verified peer-reviewed **Singapore**
material-price/demand probabilistic forecasting study was found (Singapore BCA publishes aggregate
demand projections, not material-level predictive distributions:
https://www1.bca.gov.sg/resources/newsroom/steady-demand-for-the-construction-sector-projected-for-2024/).
**Honest caveat:** A3 is a real counterexample to any blanket "probabilistic forecasts never reach
downstream decisions" claim — it propagates price distributions into contract-escalation risk. CMIDO's
G1 must therefore be worded as a *procurement-decision* handoff gap, which is how the manuscript already
frames it.

### Cluster B — Joint demand/supply-uncertainty propagation and procurement optimization

| # | Source | Verified identifier | What it establishes | Relation to CMIDO chain |
|---|--------|--------------------|---------------------|--------------------------|
| B1 | Presbitero, Syrén, Dippel, Awasthi, Dev & Nie (2025), *Scientific Reports* — replenishment optimization with extended (R,s,Q) and probabilistic models | doi:10.1038/s41598-025-32537-2 | LightGBM forecasts + **conformal-prediction quantiles** consumed by a simulation-assisted replenishment optimizer with ablations | **Closest forecast-to-decision integration found — but e-commerce, not construction**; no joint material-demand/supply-duration/project-duration distribution |
| B2 | Lu, Liu & Li (2024), *J. Civil Engineering and Management* — buffering policies for prefabricated supply chains under material lead-time and activity-duration uncertainty | doi:10.3846/jcem.2024.20809 | Joint stochastic material delay + activity duration; buffer-policy comparison | Construction-side joint-uncertainty precedent; buffer sizing, not calibrated-distribution consumption or MOO |
| B3 | Kouvelis, Chen & Xia (2023), *Production and Operations Management* — material shortages in project supply chains | doi:10.1111/poms.14059 | Advance ordering + due dates under uncertain activity times/material consumption with supplier flexibility | Project-procurement decision theory without an upstream probabilistic forecasting stage |
| B4 | Thevenin, Ben-Ammar & Brahimi (2022), *EJOR* 303(3) — purchase planning with supplier selection under lead-time uncertainty | doi:10.1016/j.ejor.2022.03.029 | Robust optimization with budgeted lead-time uncertainty sets | Robust-OT counterpart; no calibrated demand distributions |
| B5 | Dadaneh, Moradi & Alizadeh (2023), *IJPE* 265 — simultaneous purchase/production/inventory planning under demand uncertainty | doi:10.1016/j.ijpe.2023.109012 | Robust multi-period procurement/inventory planning | Demand-only uncertainty; single-cost objective |
| B6 | Wang, Kang & Petropoulos (2024), *EJOR* — combining probabilistic forecasts of intermittent demand | doi:10.1016/j.ejor.2024.01.032 | Probabilistic forecasts evaluated by **inventory-control utility**, not only accuracy | Supports the decision-utility evaluation philosophy; no lead-time joint propagation |
| B7 | Tu, Zhang, Li, Duan & Kong (2025), *PLOS ONE* — demand forecasting + inventory optimization fusion | doi:10.1371/journal.pone.0336026 | ML demand prediction + GA inventory model with procurement/holding/stockout costs | Prediction-to-inventory example without calibrated distributions or service-risk propagation |
| B8 | Lu, Wang, Xie & Li (2016), *IEEE Trans. Engineering Management* — construction-material safety stock under nonstationary demand and random yield | doi:10.1109/TEM.2016.2536146 | Construction stochastic safety-stock against a service-level constraint | Older construction baseline outside the date window |

**Cluster B finding.** Among the verified sources, **no study performs the complete construction
end-to-end chain**: calibrated material-demand distributions from a separately trained forecasting stage,
jointly propagated with uncertain supply/process duration into shortage/service risk, then consumed by a
multi-objective procurement optimizer with controlled component ablation. This is a *scoped* literature
finding from a targeted screening, **not proof that no such paper exists**; the formal SLR must confirm it.

### Cluster C — Target journals (see §5)

Verified recent precedents inside candidate journals include: material-price prediction with a sliding-window
CatBoost model, *JCEM* 2025 (doi:10.1061/JCEMD4.COENG-16748); bid/change-order cost-uncertainty detection,
*JCEM* 2025 (doi:10.1061/JCEMD4.COENG-15689); BIM/blockchain automatic procurement system, *Automation in
Construction* 2024 (doi:10.1016/j.autcon.2024.105779); ML cost-overrun prediction, *ECAM* 2025
(doi:10.1108/ECAM-09-2024-1209); multi-channel procurement planning under disruption, *IJPE* 2024
(doi:10.1016/j.ijpe.2024.109346); supply-chain multi-project scheduling, *C&IE* 2024
(doi:10.1016/j.cie.2024.110380).

---

## 3. Defensible novelty positioning

What the screened evidence supports CMIDO claiming (wording kept inside master spec §33):

1. **A controlled, uncertainty-preserving forecast → propagation → risk → decision chain for
   construction-material procurement, evaluated with paired forecast origins and multiplicity control.**
   No verified screened study implements this complete chain in construction (Cluster B finding).
2. **CQR-calibrated (prequential, time-aware) probabilistic forecasts of construction-material price and
   demand on Singapore public data, with rolling-origin evaluation and explicit calibration reporting.**
   No verified screened study applies conformal/CQR or gradient-boosting quantile methods to
   construction-material series (Cluster A finding).
3. **Decision-level attribution via a controlled O1/O2/O3/O4 ablation** isolating optimization,
   predictive uncertainty, and their integration — construction studies in the screened set compare
   policies or conservatism settings rather than factorial components (Cluster B finding).

What CMIDO must **not** claim (unchanged prohibitions, now evidence-backed):

- Not "first" or "novel for the first time" — A3 and B1 are direct counterexamples to broad versions of
  the handoff claim; B1 in particular already consumes conformal quantiles in a (non-construction)
  replenishment setting and ablates them.
- Not "probabilistic construction forecasting does not exist" (A1–A3).
- Not universal superiority of O4 — the frozen T5/T6 evidence shows a cost/service **trade-off**, not
  dominance, and two recorded contrasts are non-significant.

---

## 4. Closest prior art a reviewer will raise (must be cited proactively)

1. **Jezzini, Assaad & El-Adaway (2025, JCEM)** — probabilistic material-price distributions propagated
   into contract cost-risk. Distinction: price-escalation contract risk, not procurement quantity/timing
   decisions; no joint demand–duration propagation; calibration reporting not verified.
2. **Presbitero et al. (2025, Scientific Reports)** — conformal-quantile demand forecasts consumed by a
   replenishment optimizer with ablation. Distinction: e-commerce single-echelon replenishment, not
   construction; no joint supply/project-duration uncertainty; no multi-objective Pareto decision layer.
3. **Lu, Liu & Li (2024, J. Civ. Eng._mgmt)** and **Kouvelis, Chen & Xia (2023, POM)** — joint
   uncertainty in project/construction supply chains. Distinction: buffer/ordering decision theory
   without an upstream calibrated forecasting stage or decision-level ablation chain.

---

## 5. Target-journal assessment (ranked)

Ranking from verified scope pages and 2024–2025 precedent papers. Publisher pages for several journals
blocked retrieval, so **no unverified review-time statistics or APC amounts are reported**.

| Rank | Journal | Fit | Verified recent precedent | Biggest scope risk |
|------|---------|-----|---------------------------|--------------------|
| 1 | **J. Construction Engineering and Management (JCEM)** | Closest problem match; editor emphasizes AI/ML + theory-to-practice | Material-price CatBoost (2025, doi:10.1061/JCEMD4.COENG-16748); cost/schedule impact detection (2025, doi:10.1061/JCEMD4.COENG-15689) | Must add construction-engineering/management knowledge, not just assemble ML + optimization |
| 2 | **Automation in Construction** | Fits if framed as computational decision support across the lifecycle | BIM/blockchain procurement system (2024, doi:10.1016/j.autcon.2024.105779) | Insufficient automation/IT contribution if framed as pure procurement policy |
| 3 | **Engineering, Construction and Architectural Management** | Strong management framing; publisher guidance (general, not journal-specific) states ~60-day first decision, ~170-day acceptance | ML cost-overrun prediction (2025, doi:10.1108/ECAM-09-2024-1209) | Too much algorithm, too little managerial insight |
| 4 | **Construction Management and Economics** | Good for procurement-resilience/economic argument | No close verified 2024–2025 precedent found in this screening | Needs construction-management/economic theory beyond an applied pipeline |
| 5 | **Computers & Industrial Engineering** | Plausible if the methodology is sold as generalizable | Multi-project supply-chain scheduling (2024, doi:10.1016/j.cie.2024.110380) | Singapore construction application may read as too case-specific |
| 6 | **Int. J. Production Economics** | Most demanding reframing; emphasizes economic consequences | Multi-channel procurement under disruption (2024, doi:10.1016/j.ijpe.2024.109346) | Insufficient general production-economics contribution |

**Recommendation:** JCEM first, Automation in Construction second with a decision-support framing. Both
have verified 2024–2025 precedent for exactly the material-price/uncertainty territory CMIDO occupies.

---

## 6. Unresolved questions the formal SLR must answer

1. Does any 2024–2026 study propagate **calibrated** (coverage-verified) construction-material demand
   distributions into procurement ordering decisions? (None found; must be confirmed by database-level
   screening: Scopus/WoS, Construction Data Base, ASCE/Elsevier/Emerald full-text.)
2. Is the Presbitero et al. (2025) e-commerce pipeline the effective state of the art for
   conformal-forecast-to-inventory integration, and has any construction analogue appeared since?
3. How do reviewers in the chosen journal treat scenario-simulation evidence without a field/industry
   partner deployment? (Determines how prominently the Singapore empirical anchoring must be framed.)
4. Are there published reporting standards for probabilistic forecasting evaluation in construction
   (coverage/pinball/Winkler) that CMIDO should explicitly conform to?

---

## 7. Journal-readiness assessment (candid)

**Does the current evidence support submission?** Not yet — **conditionally, after a bounded revision
cycle**. The evidence chain itself is publication-grade (frozen artifacts, reconciled tables/figures,
paired inference with multiplicity control, honest non-significance reporting). Three things block a
submission claim today:

1. **RO3 scenario-count convergence is an unresolved limitation** (every frozen-ladder rung fails;
   diagnosed in `docs/CMIDO_RO3_3_CONVERGENCE_REPORT.md`). Journals in this space will ask how
   simulation results stabilize with sample size. Options: (a) present the domain-aware RO3.3A variant
   and the monotone 1/√N decay as the convergence evidence with the grid-lock explanation, or
   (b) run a separately versioned higher-resolution duration experiment. This needs a supervisor
   decision, not a silent threshold change.
2. **No reference list.** The manuscript intentionally carries no citations; §13 must be populated from
   a formal SLR screen. The sources in this document are a verified starting set, not the SLR.
3. **RO1 H1 is not supported as originally hypothesized** (statistical probabilistic baselines beat
   ML-CQR on aggregate Winkler at h=3). This is honest and reportable — and arguably a *stronger*
   paper for it — but the abstract/introduction must be framed around "measurably different
   uncertainty quality" rather than "ML improves forecasting", and the current manuscript already does
   this.

**Before submission, in order:** supervisor decisions on (1) convergence disposition and (2) target
journal → formal SLR screen → populate references + tighten G1–G3 wording against Cluster A/B counter-
examples → decide whether to add the RO1 test-split table (currently validation-only in T1) as
supplementary → rebuild PDF → submit.

---

---

## 8. Verification addendum (2026-10-20)

A second, narrower screen was run to re-test §6 question 1 and the conformal sub-question before the
supervisor review. **Method:** Google-indexed queries (not Scopus/WoS — no database access), e.g.
`"conformal" construction materials price forecasting`, `"construction material" probabilistic
forecasting demand shortage procurement stochastic optimization`, `"construction material demand"
conformal prediction`, `"conformalized quantile regression" construction`, `"material sourcing"
construction two-stage stochastic`; publisher/primary records checked where reachable (ASCE, ACM,
TU Delft, institutional repositories).

**Result — both questions answered the same way as §2:**

1. **Full chain (a) calibrated/coverage-verified forecasts → (b) joint demand + supply/process-duration
   propagation into shortage/service risk → (c) multi-objective procurement optimizer with controlled
   ablation:** no qualifying 2024–2026 construction study located.
2. **Conformal prediction / CQR applied to construction-material price or demand series:** none
   located. The closest conformal construction work found concerns concrete-strength prediction, not
   price or demand series.

This is a search outcome, not proof of absence: full text was blocked for several publisher records
and no Scopus/WoS screening was performed. The formal SLR (§6, master spec §37) remains required.

**New sources to cite proactively (none changes §3 wording):**

| Source | Verified identifier | Why a reviewer may raise it | Still outside CMIDO's claim because |
|--------|--------------------|-----------------------------|-------------------------------------|
| Tian (2024), *Application of Deep Learning for Material Price Prediction in Construction Risk Forecasting* (ACM) | doi:10.1145/3690407.3690470 | Material-price prediction with Monte-Carlo-style forecasting for construction risk | Calibrated/coverage-verified forecasts and any shortage-risk optimizer link could not be verified from the accessible record |
| Chen et al. (2025), *Integrating environmental considerations and resilience in material sourcing for construction projects* (Computers & Industrial Engineering) | doi:10.1016/j.cie.2025.111027 | Construction material sourcing with stochastic/resilience optimization | No evidence located that its inputs are coverage-verified material price/demand distributions propagated into service risk |
| Shiha & El-Adaway (2026), *Prediction of Construction Material Prices Using Recurrent Neural Networks and Ensemble Batch Intervals* (ASCE CRC) | doi:10.1061/9780784486436.008 | Interval material-price forecasting, the closest recent interval-price construction item | Could **not** be verified as conformal or empirically coverage-calibrated, and no downstream optimizer link |

Two items already screened (Assaf et al. 2024 doi:10.1061/9780784485286.026, A2; Fouad et al. 2025
doi:10.59490/jscms.2025.8136, A4) were re-identified independently, which is a consistency signal for
the Cluster A/B tables above.

**Effect on the positioning:** novelty claims 1–3 in §3 are unchanged (no counterexample located), and
§7 blocker 2 (no reference list; formal SLR not yet done) also stands unchanged — this addendum is
screening evidence, not an SLR substitute.

*All identifiers above were verified during the 2026-10-18 screening via DOI/URL resolution, and the
§8 addendum during 2026-10-20. Records verified only at abstract level are marked. This document
supersedes nothing; it supplements the evidence concordance and the manuscript §2/§13.

--- (verification addendum ends)

## 8b. 2026-10-20 verification addendum (post-supervisor review)

A second, narrower screen was run to re-test §6 question 1 and the conformal sub-question before the
supervisor review. **Method:** Google-indexed queries (not Scopus/WoS — no database access), e.g.
`"conformal" construction materials price forecasting`, `"construction material" probabilistic
forecasting demand shortage procurement stochastic optimization`, `"construction material demand"
conformal prediction`, `"conformalized quantile regression" construction`, `"material sourcing"
construction two-stage stochastic`; publisher/primary records checked where reachable (ASCE, ACM,
TU Delft, institutional repositories).

**Result — both questions answered the same way as §2:**

1. **Full chain (a) calibrated/coverage-verified forecasts → (b) joint demand + supply/process-duration
   propagation into shortage/service risk → (c) multi-objective procurement optimizer with controlled
   ablation:** no qualifying 2024–2026 construction study located.
2. **Conformal prediction / CQR applied to construction-material price or demand series:** none
   located. The closest conformal construction work found concerns concrete-strength prediction, not
   price or demand series.

This is a search outcome, not proof of absence: full text was blocked for several publisher records
and no Scopus/WoS screening was performed. The formal SLR (§6, master spec §37) remains required.

**New sources to cite proactively (none changes §3 wording):**

| Source | Verified identifier | Why a reviewer may raise it | Still outside CMIDO's claim because |
|--------|--------------------|-----------------------------|-------------------------------------|
| Tian (2024), *Application of Deep Learning for Material Price Prediction in Construction Risk Forecasting* (ACM) | doi:10.1145/3690407.3690470 | Material-price prediction with Monte-Carlo-style forecasting for construction risk | Calibrated/coverage-verified forecasts and any shortage-risk optimizer link could not be verified from the accessible record |
| Chen et al. (2025), *Integrating environmental considerations and resilience in material sourcing for construction projects* (Computers & Industrial Engineering) | doi:10.1016/j.cie.2025.111027 | Construction material sourcing with stochastic/resilience optimization | No evidence located that its inputs are coverage-verified material price/demand distributions propagated into service risk |
| Shiha & El-Adaway (2026), *Prediction of Construction Material Prices Using Recurrent Neural Networks and Ensemble Batch Intervals* (ASCE CRC) | doi:10.1061/9780784486436.008 | Interval material-price forecasting, the closest recent interval-price construction item | Could **not** be verified as conformal or empirically coverage-calibrated, and no downstream optimizer link |

Two items already screened (Assaf et al. 2024 doi:10.1061/9780784485286.026, A2; Fouad et al. 2025
doi:10.59490/jscms.2025.8136, A4) were re-identified independently, which is a consistency signal for
the Cluster A/B tables above.

**Effect on the positioning:** novelty claims 1–3 in §3 are unchanged (no counterexample located), and
§7 blocker 2 (no reference list; formal SLR not yet done) also stands unchanged — this addendum is
screening evidence, not an SLR substitute.

*All identifiers above were verified during the 2026-10-18 screening via DOI/URL resolution, and the
§8 addendum during 2026-10-20. Records verified only at abstract level are marked. This document
supersedes nothing; it supplements the evidence concordance and the manuscript §2/§13.*
