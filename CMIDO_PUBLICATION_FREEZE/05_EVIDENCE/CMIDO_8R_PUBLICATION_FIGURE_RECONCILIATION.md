# CMIDO 8R — Publication Figure + Numerical Reconciliation

## Purpose

8R converts the frozen 8Q publication tables into publication-facing figures and records a source concordance for every generated figure.

The figure generator does **not** recompute scientific results from raw data. It reads only the frozen CSV artifacts under `results/8Q_publication_artifacts/`.

## Figure set

| Figure | Frozen source | Purpose |
|---|---|---|
| F1 | T1 RO1 validation metrics | Probabilistic forecast coverage |
| F2 | T2 RO2 tail comparison | Tail behaviour by representation |
| F3 | T3 RO2 propagation summary | Propagated demand tail |
| F4 | T3 RO2 joint/independent sensitivity | Dependence sensitivity |
| F5 | T5/T6 controller descriptives | Controller-level descriptive evidence |
| F6 | T6 RO3 ablation | Controlled ablation effects |

## Reconciliation rules

1. A figure may only be generated when its declared 8Q source exists.
2. Required source columns are checked before plotting.
3. The RO2 sensitivity artifact is locked to its verified 240-row cardinality.
4. Every generated figure is linked to the exact source CSV.
5. The source SHA-256 is recorded in `CMIDO_8R_FIGURE_CONCORDANCE.json`.
6. The audit is written to `CMIDO_8R_FIGURE_AUDIT.csv`.
7. Figures are generated at 300 DPI for publication use.
8. No figure should be treated as manuscript-final until the 8R gate passes and the resulting concordance has been reviewed.

## Run

```powershell
python -m src.optimization.cmido_8r_publication_figures
pytest -q
```

Output directory:

`results/8R_publication_figures/`
