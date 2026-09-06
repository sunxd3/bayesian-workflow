# Missing Data and Hierarchical Structure

Use these diagnostics to decide whether observations are plausibly exchangeable and whether missingness needs to be modeled, imputed, or handled by sensitivity analysis. For Bayesian modeling, missingness and clustering are structural features, not nuisance bookkeeping.

## Implementation

Use pandas, SciPy, and statsmodels first. Do not add a dependency just for Little's MCAR test; write a small helper only if its assumptions are appropriate.

Version assumptions: snippets target pandas plus SciPy 1.17-era and statsmodels 0.14.6-era APIs. Record `pandas.__version__`, `scipy.__version__`, and `statsmodels.__version__` when reporting these diagnostics. If versions differ, check `MixedLM`, `Logit`, and SciPy contingency-test signatures before relying on exact output fields.

```python
import pandas as pd
import statsmodels.api as sm
from scipy import stats

missing = df.isna()
missing_rates = missing.mean().sort_values(ascending=False)
pattern_counts = missing.astype(int).value_counts()
stats.chi2_contingency(pd.crosstab(missing["target_col"], df["group_col"]))

# Probe whether observed covariates predict missingness in one variable.
r = missing["target_col"].astype(int)
X = sm.add_constant(df[observed_predictors])
logit_res = sm.Logit(r, X, missing="drop").fit(disp=False)

# One-way Gaussian ICC from a random-intercept model.
mixed = sm.MixedLM.from_formula("y ~ 1", groups="group", data=df).fit()
var_between = float(mixed.cov_re.iloc[0, 0])
var_within = float(mixed.scale)
icc = var_between / (var_between + var_within)
```

## Missing Data Mechanisms

- **MCAR.** Missingness is unrelated to observed and unobserved values. Complete-case analysis is less likely to bias estimates, but can still waste information.
- **MAR.** Missingness depends on observed variables. This is usable only if the model or imputation conditions on the variables that explain missingness.
- **MNAR.** Missingness depends on unobserved or missing values. This cannot be confirmed or ruled out from the observed data alone.

Correctness notes:

- Missingness mechanisms are assumptions about the data-generating process. Diagnostics can falsify simple stories but cannot prove MCAR/MAR/MNAR.
- Little's MCAR test checks whether means differ across missingness patterns under restrictive assumptions, commonly multivariate normality. `p < 0.05` is evidence against MCAR; `p >= 0.05` does not prove MCAR.
- Little's test can be unstable with many variables, sparse patterns, nonnumeric variables, nonnormal data, and small pattern counts.
- Logistic/probit missingness models are often more useful for EDA: ask whether observed covariates predict each missingness indicator.
- "MAR can be handled with imputation" is too broad. The imputation or Bayesian model must include predictors of missingness and preserve hierarchy/time structure.

Bayesian implications:

- **MCAR plausible and low missingness.** Complete-case or simple imputation may be acceptable, with sample-size loss reported.
- **MAR plausible.** Model missing values jointly or impute using the variables and hierarchy that predict missingness.
- **MNAR plausible.** Require sensitivity analysis, selection models, pattern-mixture models, or explicit measurement process assumptions.

## Hierarchical Data

- **ICC.** Fraction of outcome variance attributable to between-group variation in a one-way random-intercept approximation.
- **Design effect.** `1 + (mean_cluster_size - 1) * ICC`, a rough warning about loss of independent information under clustered sampling.

Correctness notes:

- A Gaussian ICC from ANOVA or `MixedLM` is appropriate for continuous outcomes under a simple random-intercept approximation.
- For binary, ordinal, count, or survival outcomes, ICC depends on the link and latent scale. Do not blindly reuse the Gaussian formula.
- ICC near zero does not rule out random slopes, group-specific treatment effects, temporal dependence within groups, or sparse-level partial pooling needs.
- Unequal cluster sizes weaken the simple design-effect formula. Report the cluster-size distribution, not only the mean.
- Thresholds such as `ICC > 0.05` are rough EDA triggers. Scientific grouping, validation leakage, and rare levels can justify multilevel modeling even with small ICC.

Bayesian implications:

- **Meaningful between-group variance.** Use hierarchical intercepts and group-aware validation.
- **Effects that vary by group.** Consider random slopes or hierarchical interactions.
- **Sparse groups or rare categories.** Prefer partial pooling over dropping or one-hot fixed effects.
- **Grouped observations.** Invalidate ordinary observation-level LOO when the target task is prediction for new groups.

## Report

Report package versions, missingness rates, dominant missingness patterns, predictors of missingness, any MCAR-style test assumptions, group variables, number of groups, cluster-size distribution, ICC/design-effect estimates, and the validation unit implied by the structure.
