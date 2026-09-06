# Statistical Assessment

Review the diagnostic artifacts produced by the validation pipeline (prior predictive, recovery, fit, posterior predictive). The first pass is mechanical; the substantive judgements come from interpreting the patterns.

## LOO validity

Load the LOO results JSON (the small summary file produced by the model-fitter) for ELPD ± SE and Pareto k summary. Load the full posterior NetCDF only when you need to regenerate `az.plot_khat()` or `az.plot_loo_pit()` visualizations. If the LOO summary is missing, compute `az.loo()` from the posterior.

Read the experiment plan for the data structure and validation strategy. If the data is grouped/panel or temporal and you computed standard observation-level LOO, append a caveat:

> CAVEAT: Standard row-wise LOO used on grouped/temporal data. ELPD gains for hierarchical or time-series components are likely inflated by intra-group interpolation. Do not rely on ELPD differences alone for model ranking.

For Pareto k interpretation and shape-to-diagnosis mappings on LOO-PIT, see `bayesian-model-diagnostics`.

## Temporal gap handling

If the model uses autoregressive terms, time-varying coefficients, or other temporal dependencies, verify that the implementation accounts for irregular spacing (missing hours, gaps in panel). Flag if AR terms assume uniform spacing but the data has gaps — the model should impute, scale the AR coefficient by time delta, or explicitly handle non-contiguous observations.

If the data has time structure, note whether a temporal holdout (rolling-origin, last-N-period) would be informative for the modeling goals. Recommend it if so — advisory, not blocking. Not every time series model is for forecasting.

## Retrodiction vs prediction mismatch

If the model retrodicts well (good PPCs on training data) but predicts poorly (poor LOO or holdout performance), this indicates **overfitting** if the model is excessively flexible relative to the data, **confounding** if it captures associations that don't generalize. If the model is not overparameterized, suspect confounding. Flag this pattern explicitly rather than chasing ELPD improvements with more flexibility.

## Residual investigation

If you detect unexplained residual structure (autocorrelation, heteroskedasticity, systematic patterns), do not guess the cause. Write and execute a short Python script to plot residuals against unused covariates, time indices, or group variables. Base refinement suggestions on what you observe in those plots, not on generic advice.

## Estimand contraction

If the experiment plan specifies key quantities of interest (see `analysis-design > Analysis purpose`), compute prior-to-posterior contraction for those parameters: `az.summary()` on target parameters, compare posterior SD to prior SD. A model that passes PPCs but leaves the target estimand diffuse (contraction ratio < 50%) may be adequate predictively but inadequate for the analysis purpose. Report contraction ratios. Classify each key parameter:

- Contraction ≈ 0 with posterior near prior mean → data uninformative (prior dominates).
- Contraction ≈ 0 with posterior pushed toward prior tails → prior-likelihood conflict (domain thresholds may be wrong or the observational model is misspecified).
- High contraction → data is informative (normal).

## Broken-model gate

If the statistical assessment reveals the model is **BROKEN** (persistent computational failures, fundamental misspecification, unresolvable prior-data conflict, non-identifiable parameters), skip domain and framework assessment and go directly to the verdict.
