# Distribution Diagnostics

Use these tests to screen the marginal target distribution and residuals from a minimal model. For Bayesian modeling, the goal is not to "prove normality"; it is to identify support, skew, tail behavior, boundary mass, transformations, and likelihood families that deserve consideration.

## Implementation

Prefer SciPy for standalone distribution checks:

Version assumptions: snippets target SciPy 1.17-era APIs. Record `scipy.__version__` in the EDA output when a diagnostic result depends on package behavior. If the installed SciPy is older, check availability and signatures before using `goodness_of_fit`; in SciPy 1.15+, prefer the `rng` keyword over legacy `random_state` for Monte Carlo goodness-of-fit.

```python
from scipy import stats

stats.shapiro(x)
stats.jarque_bera(x)
stats.anderson(x, dist="norm")
stats.kstest(x, "norm", args=(mu, sigma))  # only valid for fully specified null
stats.goodness_of_fit(stats.norm, x)       # use when parameters are fit to data
stats.probplot(x, dist="norm")
stats.skew(x, nan_policy="omit")
stats.kurtosis(x, fisher=True, nan_policy="omit")
```

Statsmodels also has residual-oriented normality helpers:

Version assumptions: snippets target statsmodels 0.14.6-era APIs. Record `statsmodels.__version__` if using statsmodels residual tests because return containers and helper locations can vary across releases.

```python
from statsmodels.stats.diagnostic import normal_ad, kstest_normal, lilliefors
from statsmodels.stats.stattools import jarque_bera, omni_normtest
```

## Correctness Notes

- Most formal tests assume independent draws from a continuous distribution. Dependence, grouping, truncation, censoring, rounding, and duplicated values can invalidate the nominal p-value.
- Large samples make tiny, modeling-irrelevant deviations significant. Small samples often miss consequential tail behavior. Always pair test output with QQ plots and robust summaries.
- Shapiro-Wilk is useful for small to moderate samples, but its p-value is not reliable for very large samples. Use it as a screen, not a gate.
- Jarque-Bera is an asymptotic skewness/kurtosis test. It can miss non-normal structure that preserves the first four moments.
- Anderson-Darling weights tails more strongly than KS, which is useful when outliers or tail risk affect likelihood choice.
- A one-sample KS test against a distribution whose parameters were estimated from the same data is not the usual KS null. Use `stats.goodness_of_fit` or `statsmodels` Lilliefors-style helpers when fitting parameters before testing.
- Rules such as `abs(skewness) < 2` and `abs(kurtosis) < 7` are descriptive rough cuts, not evidence that a Gaussian likelihood is correct.

## QQ Plot Patterns

- **Straight line.** Proposed distribution is plausible at the plotted scale.
- **Reverse S-shape.** Heavier tails than the reference distribution.
- **S-shape.** Lighter tails than the reference distribution.
- **Curving upward.** Right skew or positive-support process.
- **Curving downward.** Left skew or ceiling effects.
- **Flat segments or piles.** Rounding, censoring, or boundary mass.

## Bayesian Modeling Implications

- **Heavy tails.** Compare Normal vs Student-t or robust observation models.
- **Skewed positive data.** Consider Lognormal, Gamma, Weibull, or transformed outcome models.
- **Boundary mass.** Consider hurdle, zero/one-inflated, censored, or truncated likelihoods.
- **Multimodality.** Look for latent groups, mixture structure, or missing covariates before choosing a single global likelihood.
- **Residual non-normality after strong structural controls.** More actionable than marginal non-normality of the raw target.

## Report

Report package versions, sample size after missing-value handling, the exact variable or residuals tested, statistic and p-value where applicable, QQ-plot interpretation, descriptive skew/tail evidence, and the modeling implication. Do not report `p < 0.05` as a model-selection decision.
