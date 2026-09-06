---
name: visual-predictive-checks
description: Guidelines for visual predictive checks following Säilynoja et al. recommendations using ArviZ
user-invocable: false
---

# Visual Predictive Checks

Use this skill when running prior or posterior predictive checks to validate Bayesian models. These checks compare simulated data from the model to observed data (or plausible ranges for prior predictive checks).

## Workflow

1. Fit the model with `generated quantities { vector[N] y_rep; vector[N] log_lik; }` — see `stan > ArviZ Integration`.
2. Convert to ArviZ InferenceData — see `inferencedata-handling`. Use the conventions `y_obs` (observed) and `y_rep` (replications); mixing `y_pred`/`y_sim` causes downstream KeyErrors.
3. Generate visual checks (sections below) appropriate to the data type and the analysis purpose.

## Visual Checks by Data Type

### Continuous Data
- **Distribution.** `plot_ppc_dist` with `kind="ecdf"` and `kind="kde"`.
- **PIT ECDF.** `plot_ppc_pit` — shows calibration with simultaneous bands.
- **Coverage.** `plot_ppc_pit(coverage=True)` — equal-tailed interval coverage.
- **Summary statistics.** `plot_ppc_tstat` for median, MAD, IQR combined with `combine_plots`.
- **LOO-PIT.** `plot_loo_pit` — avoids double-dipping by using leave-one-out.

### Count Data
- **Rootogram.** `plot_ppc_rootogram` — emphasizes discreteness and dispersion.
- **Histogram.** `plot_ppc_dist(kind="hist")`.
- **PIT ECDF and coverage.** Same as continuous.

### Binary/Categorical/Ordinal Data
- **Calibration.** `plot_ppc_pava` — PAV-adjusted calibration curves.
- **Intervals.** `plot_ppc_interval` — posterior predictive intervals with observed overlay.
- **PIT ECDF and coverage.** Same as continuous.

### Censored/Survival Data
- **Survival curves.** `plot_ppc_censored` — Kaplan-Meier style PPC.
- **PIT ECDF and coverage.** Same as continuous.

## Conditional and Residual Checks

Marginal PPCs (overall distribution checks) can pass while the model is seriously misspecified at the covariate level. Always supplement marginal checks with:

**Conditional PPCs.** Stratify posterior predictive checks by key covariates identified in EDA.
- **Discrete covariates.** Compute posterior predictive mean/proportion within each level and compare to observed.
- **Continuous covariates.** Bin into 5-10 intervals and check whether posterior predictive summaries in each bin cover the observed values.
- **Grouped/hierarchical data.** Generate per-group PPCs in addition to overall — outlier groups or groups with poor coverage suggest inadequate population model.

**Residual panels.** For every posterior retrodictive comparison, generate BOTH the overlay plot (predictive intervals over data) AND a residual plot (`y_rep - y_obs`). Residual plots magnify systematic deviations that are invisible in overlays. Bin residuals by time, group, or predictor to reveal structure.

**Location-function retrodiction.** For regression-type models, plot the posterior distribution of the fitted function f(x; θ) (spaghetti lines or quantile ribbons) overlaid on observed data, WITHOUT observation noise. This isolates systematic misfit from noise absorption. If the full PPC passes but the location-function check shows systematic bias, the model's σ is absorbing structural error — the model retrodicts for the wrong reasons.

## Purpose-Conditional Emphasis

When an analysis purpose is stated (descriptive / inferential / predictive), the PPC must emphasize the features the purpose hinges on, not just marginal fit:

- **Inferential goals.** Write custom PPC plots that condition on the estimand variables. If the estimand is a group contrast, plot observed vs replicated group summaries side by side. A model can have perfect marginal calibration while missing the conditional structure the analysis cares about — marginal checks alone are insufficient.
- **Predictive goals.** Focus on tail calibration and coverage at decision-relevant thresholds (the values where downstream decisions change).
- **Descriptive goals.** Focus on reproducing the variance decomposition (between-group vs within-group patterns).

For the underlying analysis purposes, see `analysis-design > Analysis purpose`.

## Key Principles

Use multiple complementary views rather than relying on a single plot. For example, for continuous outcomes, combine ECDF (shows full distribution) with PIT ECDF (shows calibration) and t-stat PPCs (shows specific features like central tendency and spread).

LOO-PIT is preferred over regular PIT for posterior checks as it approximates leave-one-out predictive distribution and avoids overfitting concerns. For interpreting LOO-PIT and PPC patterns (shape-to-diagnosis mappings), see `bayesian-model-diagnostics`.

Avoid double-dipping: use test statistics not directly fit by the model (e.g., skewness for Gaussian models, zero-proportion for Poisson).

Name plots descriptively: `prior_predictive_ecdf.png`, `loo_pit_calibration.png`, `posterior_rootogram.png`.

## Pitfalls

- **Naming.** Variable naming errors across files cause cascading KeyErrors — stick to `y_obs` / `y_rep`. See `inferencedata-handling > Common failures`.
- **NumPy 2.x removed `np.trapz`.** Use `scipy.integrate.trapezoid` for any PPD (posterior predictive density) integration. Same signature: `trapezoid(y, x)`.
