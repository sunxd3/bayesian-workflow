# Regression Diagnostics

Use these diagnostics on a minimal, defensible baseline model. For Bayesian modeling, residual structure is a map of missing likelihood or hierarchy, not a command to drop variables or force an OLS-style final model.

## Implementation

Prefer statsmodels for regression diagnostics:

Version assumptions: snippets target statsmodels 0.14.6-era APIs. Record `statsmodels.__version__` in the EDA output. If the installed version differs, inspect function signatures before running diagnostics, especially for return types and default options such as robust Breusch-Pagan behavior.

```python
import statsmodels.api as sm
from statsmodels.stats import diagnostic as smdiag
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor

X = sm.add_constant(X)
res = sm.OLS(y, X).fit()

smdiag.het_breuschpagan(res.resid, res.model.exog)
smdiag.het_white(res.resid, res.model.exog)
smdiag.het_goldfeldquandt(res.resid, res.model.exog)
smdiag.linear_reset(res, power=2, use_f=True)
influence = OLSInfluence(res)
```

For Mahalanobis distance, SciPy is sufficient if a non-robust covariance estimate is acceptable:

Version assumptions: the SciPy distance API is stable, but report `scipy.__version__` when using it for reproducibility.

```python
from scipy.spatial.distance import mahalanobis
```

## Heteroscedasticity

- **Breusch-Pagan / Koenker-Bassett.** Tests whether residual variance is related to covariates. In statsmodels, `het_breuschpagan(..., robust=True)` is the default Koenker version.
- **White's test.** Uses regressors, squares, and cross-products to detect more general variance patterns. It does not require manually adding cubic terms.
- **Goldfeld-Quandt.** Compares residual variance across ordered subsamples. It is only meaningful when the ordering variable is scientifically plausible.

Correctness notes:

- These tests assume the residuals came from a fitted conditional mean model. Running them on raw outcomes usually confounds mean structure with variance structure.
- A significant result says the provisional model has non-constant residual scale, not that Bayesian inference is invalid.
- Heteroscedasticity can imply a variance model, group-specific scale, log transform, Student-t likelihood, mixture, or missing covariate.

## Multicollinearity

- **VIF.** `variance_inflation_factor(exog, j)` measures how predictable predictor `j` is from the others. Values above 5 are worth inspecting; values above 10 often indicate unstable separate coefficient estimates.
- **Condition number.** Large values indicate near-linear dependence or severe scaling differences. Standardize before interpreting.

Correctness notes:

- Collinearity is not automatically a reason to drop predictors in a Bayesian model. It is a prior, identifiability, and interpretation issue.
- Strong priors, reparameterization, hierarchical pooling, or combining redundant predictors can be better than deletion.
- Report whether collinearity affects prediction, coefficient interpretability, or both.

## Specification

- **Ramsey RESET.** Adds powers of fitted values or regressors to detect neglected nonlinear conditional mean structure.

Correctness notes:

- RESET is a broad alarm. It does not identify the missing structure.
- Follow up with residual-vs-fitted plots, residuals by candidate covariates, interaction screens, and domain-informed transformations.
- In Bayesian model design, a RESET failure suggests candidate nonlinear terms, interactions, splines, latent groups, or a different likelihood/link.

## Influence Diagnostics

Use `OLSInfluence(res)` for:

- **Leverage (`hat_matrix_diag`).** Unusual covariate location. Rule of thumb: `h_ii > 2(p + 1) / n`.
- **Cook's D (`cooks_distance`).** Overall effect on fitted values. Rules of thumb: `D > 1` or `D > 4 / n`.
- **DFBETAS (`dfbetas`).** Effect on individual coefficients. Rule of thumb: `abs(DFBETAS) > 2 / sqrt(n)`.
- **Studentized residuals.** Outcome outliers conditional on the model. Rule of thumb: absolute value above 3.
- **Mahalanobis distance.** Multivariate covariate outlier. Compare squared distance to a chi-square reference only when covariance assumptions are plausible.

Correctness notes:

- Influence flags are triage, not deletion rules.
- Check whether flagged observations are data errors, rare but valid regimes, missing covariates, or scientifically important cases.
- For Bayesian modeling, influence can motivate robust likelihoods, measurement-error models, mixture components, or leave-one-observation/group sensitivity checks.

## Report

Report package versions, the baseline model formula, residual definition, diagnostics run, statistic and p-value where applicable, the largest flagged observations/groups, and the concrete modeling implication. Avoid saying a test "proves" an assumption is met.
