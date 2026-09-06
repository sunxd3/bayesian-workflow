---
name: bayesian-model-diagnostics
description: Interpreting LOO diagnostics, PIT calibration, and Pareto k for single-model evaluation
user-invocable: false
---

# Bayesian Model Diagnostics

Operational guide for interpreting single-model diagnostic outputs. Covers LOO validity, Pareto k, and LOO-PIT calibration — the artifacts produced during model critique.

For MCMC sampler health (R-hat, ESS, BFMI, divergences), see `convergence-diagnostics`. For generating PPC/PIT plots, see `visual-predictive-checks`.

## Data Structure Precondition

**Check BEFORE computing or trusting `az.loo()`:**

| Data structure | Standard `az.loo()` valid? | Action |
|---|---|---|
| **i.i.d.** | Yes | Proceed normally |
| **Time-series / temporal** | No — LOO assumes independence, will overstate predictive performance | Flag as warning. Recommend Leave-Future-Out CV (LFO-CV) or rolling-origin evaluation |
| **Grouped / hierarchical** (e.g., patients, stores) | Depends on prediction target | If generalizing to *new groups*: use grouped LOO (leave-out entire groups). If predicting new observations within known groups: standard LOO is acceptable |

This check is non-negotiable. Standard LOO on dependent data produces misleading ELPD estimates. The data structure should have been declared up front (see `analysis-design > Validation strategy`); if not, infer it from the data here and flag the gap.

### Implementation Note

For non-standard CV methods (LFO-CV, grouped LOO), write minimal custom code from `posterior.nc`'s `log_likelihood` rather than a full ad-hoc framework; mirror `loo()` in `fit-pipeline > references/posterior_fit.py` for the observation-level shape.

## Pareto k Diagnostics

After computing `az.loo()`, inspect Pareto k values via `az.plot_khat()`.

| Condition | Meaning | Action |
|---|---|---|
| All k < 0.5 | LOO approximation is reliable | Trust ELPD estimate |
| Some k in 0.5–0.7 | Marginal — approximation may be noisy | Acceptable if few observations affected. Note in report |
| k > 0.7 for isolated observations (<5%) | Those specific observations are highly influential | Inspect them — they may be outliers. Consider heavier-tailed likelihood (Normal → Student-t) or observation-level effects |
| k > 0.7 for >5% of observations | LOO approximation is unreliable for this model | Do not trust ELPD. Recommend: (1) k-fold CV with `az.reloo()`, (2) structural simplification, or (3) heavier-tailed likelihood to reduce influence of extreme observations |

**Common structural causes of high Pareto k:**
- Thin-tailed likelihood with outliers (Normal when Student-t is needed)
- Missing group-level variation (pooled when hierarchical is needed)
- Overly flexible model that overfits individual observations
- Near-boundary predictions (e.g., probabilities near 0 or 1 in logistic models)

### Refitting High-k Observations (az.reloo)

`az.reloo()` exists but requires implementing a `CmdStanPySamplingWrapper` subclass with custom `sample()`, `sel_observations()`, and `log_likelihood__i()` methods. It is NOT a drop-in replacement for `az.loo()`. Only use it when the number of high-k observations is small (< 10); otherwise the refitting cost is prohibitive. For many high-k observations, prefer structural fixes (heavier tails, hierarchical effects) over brute-force refitting.

## LOO-PIT Calibration

LOO-PIT (Probability Integral Transform) assesses whether the model's predictive distribution is well-calibrated. Generate with `az.plot_loo_pit()`. Map the shape to a diagnosis:

| PIT shape | Diagnosis | Model problem | Suggested fix |
|---|---|---|---|
| **Uniform (flat)** | Well-calibrated | None — predictive distribution matches data variance | No action needed |
| **U-shape** (excess mass at 0 and 1) | Underdispersed | Model is too confident; data has heavier tails or more variance than the likelihood allows | Heavier-tailed likelihood (Normal → Student-t, Poisson → NegBin), add variance parameters, or add unmodeled group-level effects |
| **Inverted U / arch** (deficit at 0 and 1) | Overdispersed | Model predicts wider variance than data actually has | Tighten priors on variance parameters, remove unnecessary hierarchical levels, check for zero-inflation masking true variance |
| **Left-skewed** (mass concentrated near 1) | Systematic underprediction | Model consistently predicts too low | Check for missing baseline predictors, add nonlinear trends (splines, GPs), or use asymmetric likelihood |
| **Right-skewed** (mass concentrated near 0) | Systematic overprediction | Model consistently predicts too high | Same as left-skewed — missing structure or wrong mean function |
| **S-shape or wiggly** | Localized miscalibration | Model is well-calibrated in some regions but not others | Investigate which observations contribute — may need varying coefficients, interaction terms, or mixture components |

**Important:** LOO-PIT is preferred over regular PIT for posterior checks because it approximates the leave-one-out predictive distribution and avoids double-dipping (using the same data for fitting and evaluation).

## Connecting Diagnostics to Refinement

When writing critique suggestions for `model-refiner`, be specific about the diagnostic evidence:

- **Bad.** "Consider a more flexible model"
- **Good.** "LOO-PIT shows U-shape (underdispersed). Recommend Student-t likelihood instead of Normal to accommodate the heavy tails visible in the PIT"
- **Good.** "Pareto k > 0.7 for 12% of observations (mostly in group C). Recommend adding group-level intercepts to reduce influence concentration"

Each suggestion should trace back to a specific diagnostic pattern and propose a concrete structural change.
