# Dashboard 10A.7 — RO1 Forecasting Workspace

**Research objective:** Can probabilistic forecasting provide not only a point
estimate of future material price/demand, but also a calibrated representation
of predictive uncertainty that can subsequently be propagated into procurement
decisions?

This page is a **presentation layer only**. It exposes the RO1 forecasting
evidence that already exists in the repository through the 10A.2-B dashboard
data contract. No model is trained, no metric is recomputed, and no forecast
value is generated at runtime.

## 1. Forecast target(s)

Read directly from the registered RO1 artifacts (not hard-coded):

- **Target series** — the price/demand series named in each artifact row
  (`series` / material identifier).
- **Horizon** — the forecast horizon recorded per row (`horizon`, in evaluation
  periods as defined by the source experiment).
- **Evaluation window** — the validation split recorded by the source artifact.

If an artifact does not record one of these fields, the dashboard shows
`NOT REPORTED` for that field rather than inferring it.

## 2. Dataset / evidence streams

RO1 evidence streams keep their source identities. The dashboard never joins
datasets that the repository does not explicitly join. Each artifact row
carries its `dataset` value and filters operate per stream; comparison views
clearly label which stream a row belongs to.

Provenance uses the fixed CMIDO vocabulary:

| Class | Meaning on this page |
|-------|----------------------|
| OBS   | Observed source data (actuals) |
| DER   | Metrics/calculations derived from evaluation data |
| EST   | Estimated model outputs (forecasts, conformal adjustments) |
| SCN   | Scenario-generated outputs |

Model forecasts are never labelled OBS; evaluation metrics are never labelled
OBS; scenario outputs are never presented as observed evidence.

## 3. Registered artifact sources (10A.2-B)

The page loads only registry entries — no globbing, no runtime repository
scans, no ad-hoc CSV reads:

| Registry key | Role on the page |
|--------------|------------------|
| `RO1_VALIDATION_METRICS` | Point-metric model comparison |
| `RO1_VALIDATION_FORECASTS` | Actual vs predicted, predictive intervals |
| `RO1_CALIBRATION_SCORES` | Calibration / coverage evidence |
| `RO1_PAIRED_BOOTSTRAP` | Paired uncertainty comparison evidence |
| `RO1_FINAL_INTEGRITY` | Experiment integrity/status badge |

Large artifacts respect the 10A.3 loading policy: they are represented by
their curated summary (or shown as unavailable) rather than loaded raw.

## 4. Evidence available on the page

### Point metrics
Whatever metric columns the registered validation-metrics artifact actually
contains (e.g. MAE, RMSE, sMAPE — as recorded). Columns absent from the
artifact render as `NOT AVAILABLE` cells, never as `0`.

### Probabilistic evidence
Shown only when the forecasts artifact contains interval columns
(`raw_lower_50` / `raw_upper_50`, `raw_lower_80` / `raw_upper_80` or the
artifact's own recorded equivalents). When only point forecasts exist, the
chart and table are explicitly labelled *point forecast*.

### Calibration
Rendered only from `RO1_CALIBRATION_SCORES`. If the artifact is missing or
contains no coverage columns, the section shows a clear
"Calibration evidence not available" state. Calibration is **never** estimated
from point-forecast errors.

### Sharpness / interval width
Shown only when interval-width or sharpness columns exist in the source
artifacts. The page text states the correct interpretation: narrower intervals
are useful only when they retain appropriate coverage — narrower ≠ better.

### Material / temporal stability
Rendered from per-series and per-window rows in the registered artifacts. The
page shows the actual distribution of results and makes no "generalizes across
all materials" claim. If per-material rows are absent, the section states that
material-level evidence is not available.

## 5. Model comparison semantics

The comparison table lists only columns that exist, with friendly headers (no
snake_case). No composite score and no automatic "winner" is computed. Where
the artifact itself records an official ranking it is preserved; otherwise the
page uses precise language such as "Lowest MAE in the evaluated set" and shows
disagreements between metrics rather than collapsing them.

## 6. RO1 → RO2 handoff

The handoff block separates:

- **AVAILABLE NOW** — handoff elements actually produced by RO1 artifacts
  (point forecast, interval bounds, calibration rows — depending on what
  loaded).
- **EXPECTED INPUT FOR RO2** — listed separately and never presented as
  already produced.

If the current artifacts contain only point predictions, the page explicitly
states that no probabilistic handoff is currently evidenced.

## 7. Research pipeline visual

Observed/historical data → RO1 forecasting → point forecast + predictive
uncertainty → calibration/distributional evaluation → RO2 uncertainty
propagation → RO3 procurement optimization. Existing research-stage badges are
used; future phases are shown with their actual repository stage labels, not
as implemented capabilities.

## 8. Dashboard limitations (by design)

- No model training, fitting, cross-validation, or experiment regeneration.
- No metric recomputation — adapters transform, they do not calculate.
- Missing CRPS, pinball loss, coverage, or interval columns remain missing.
- Evidence states (AVAILABLE / PARTIAL / MISSING / INVALID / TOO_LARGE /
  UNSUPPORTED) come from the 10A.3 state system.
- Presentation code (`src/construction/dashboard_ui/ro1.py`) imports no
  forecasting or research engines.

## 9. Architecture

- **Contract:** `RO1Evidence` in `src/construction/dashboard_data/contract.py`
- **Adapter:** `adapt_ro1_evidence` in
  `src/construction/dashboard_data/adapters.py` (pure transform over registry
  `LoadResult`s)
- **Presentation:** `src/construction/dashboard_ui/ro1.py` (pure builders, no
  Streamlit)
- **Routing:** app dispatch in `apps/cmido_dashboard.py`
- **Theme:** all colours come from `dashboard_ui/theme.py` tokens

## 10. Tests

`tests/construction/test_dashboard_10a7.py` covers page rendering, breadcrumb,
adapter behaviour, missing-evidence honesty, no-fabricated-metrics guards,
model-comparison semantics, provenance, stage badges, and AppTest rendering of
the routed page.

## 11. Deferred to 10A.8

- Any RO1 artifact types not yet registered in the validated dashboard
  artifact layer (registered first, then surfaced — never read ad-hoc).
- Deeper per-horizon and rolling-window drill-downs if the source artifacts
  gain those columns.
- Any probabilistic handoff evidence that RO1 experiments produce after this
  checkpoint.
