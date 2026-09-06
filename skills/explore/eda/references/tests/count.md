# Count Data Diagnostics

Use these diagnostics for non-negative integer outcomes and count residual checks. For Bayesian modeling, the goal is to identify exposure, overdispersion, structural zeros, truncation, and hierarchy before choosing a likelihood.

## Implementation

Prefer statsmodels for provisional count models and diagnostics:

Version assumptions: snippets target statsmodels 0.14.6-era APIs. Record `statsmodels.__version__` in the EDA output. Count diagnostic classes around `get_diagnostic()` are newer and may be experimental or absent in older statsmodels releases; if unavailable, fall back to manual Pearson dispersion and observed-vs-expected count probability summaries.

```python
import numpy as np
import statsmodels.api as sm
from statsmodels.discrete.count_model import (
    ZeroInflatedNegativeBinomialP,
    ZeroInflatedPoisson,
)
from statsmodels.discrete.discrete_model import NegativeBinomial

X = sm.add_constant(X)
poisson_res = sm.Poisson(y, X, exposure=exposure).fit()
dia = poisson_res.get_diagnostic()

dia.test_dispersion()
dia.test_poisson_zeroinflation()
dia.plot_probs()

pearson_phi = np.sum(poisson_res.resid_pearson**2) / poisson_res.df_resid
```

For GLM fits, compute Pearson dispersion from `resid_pearson` and `df_resid`. Use `NegativeBinomial`, `ZeroInflatedPoisson`, or `ZeroInflatedNegativeBinomialP` as provisional comparison models when the EDA evidence warrants it.

## Overdispersion

- Marginal `variance > mean` is only a first hint. The relevant question is whether counts are overdispersed conditional on exposure and predictors.
- **Pearson dispersion.** `sum(Pearson residual^2) / df_resid`. Values well above 1 indicate extra-Poisson variation; values above 2 are a strong warning.
- **Cameron-Trivedi / related tests.** Statsmodels `PoissonResults.get_diagnostic().test_dispersion()` includes CT-style alternatives for Poisson post-estimation diagnostics.

Correctness notes:

- Overdispersion can be caused by omitted covariates, unmodeled grouping, serial dependence, exposure errors, zero inflation, or true individual heterogeneity.
- A Negative Binomial likelihood is a common fix, but not the only one. Bayesian alternatives include Poisson-lognormal random effects, group-level intercepts, observation-level random effects, or explicit latent states.
- Quasi-Poisson changes standard errors in frequentist GLMs; it is not a generative likelihood for Bayesian modeling.

## Zero Inflation

- Compare observed zero counts with the expected zero probability from a fitted Poisson or Negative Binomial model.
- Use `dia.test_poisson_zeroinflation()` and probability plots as screens after a reasonable Poisson baseline.

Correctness notes:

- Excess zeros can reflect structural never-event units, a hurdle process, unobserved heterogeneity, missing exposure, truncation/censoring, or omitted predictors.
- Zero-inflation tests can flag lack of fit caused by overdispersion or hierarchy. Check overdispersion and grouping before committing to ZIP/ZINB.
- If positive counts are generated only after crossing a participation hurdle, a hurdle model may be more scientifically meaningful than zero-inflation.

## Model Comparison

- Vuong-style non-nested tests are fragile for common zero-inflated comparisons because models can be overlapping or non-regular at boundaries.
- For Bayesian model design, prefer posterior predictive checks for zeros, tails, and count probabilities, plus LOO or held-out predictive comparison where the validation unit respects grouping/time.

## Bayesian Modeling Implications

- **Exposure or population-at-risk present.** Include an offset or exposure term.
- **Conditional overdispersion.** Compare Poisson, Negative Binomial, Poisson-lognormal, or hierarchical Poisson.
- **Excess zeros after overdispersion is addressed.** Compare zero-inflated or hurdle structure.
- **Upper-bounded counts.** Consider Binomial/Beta-Binomial rather than Poisson/NB.
- **Underdispersion.** Consider Generalized Poisson, Conway-Maxwell-Poisson, Binomial, or missing bounded-support structure.

## Report

Report package versions, count range, fraction zero, exposure handling, marginal and conditional mean/variance, Pearson dispersion, zero-probability comparison, diagnostics run, and which candidate likelihoods or hierarchy are justified. Do not recommend ZIP/ZINB from a raw zero fraction alone.
