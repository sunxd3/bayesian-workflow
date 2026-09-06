---
name: eda
description: Exploratory data analysis reference for Bayesian modeling — operational EDA procedures (data semantics audit, quality checks, timestamp handling, visualization, modeling handoff) plus a diagnostic test library indexed by data shape.
user-invocable: false
---

# Exploratory Data Analysis

Reference for performing EDA in service of Bayesian modeling. Read references on demand based on what the data and current step require.

## Key Practices

- **Confounder-aware comparisons.** Any claimed association or "effect" must condition on the strongest available confounder — typically the most granular temporal unit, or the variable with the highest marginal association to both predictor and outcome. Never report unconditional means as effects. Always report sample size per arm.

## Process references

Operational checklists and procedures for each step of the EDA workflow:

- `references/process/data-semantics-audit.md` — understanding what columns **mean** (scientific domain, column roles, granularity, sparsity, encoding sanity, suspicious patterns)
- `references/process/standardization.md` — mechanical cleanup driven by the audit (snake_case names, NaN harmonization, type coercion, categorical normalization) that produces the canonical cleaned dataset
- `references/process/data-quality-checks.md` — missingness, duplicates, invalid values, type issues
- `references/process/timestamp-handling.md` — parsing timestamps, frequency inference, gaps, panel coverage
- `references/process/visualization.md` — plot quantity, structure, and documentation requirements
- `references/process/modeling-handoff.md` — variance decomposition, residual analysis, competing structural hypotheses, dependence classification, likelihood mapping, modeling-ready recommendations

For the HTML report format (design, palette, fonts, skeleton template), see `artifact-guidelines > references/html-report`. For log format, see `artifact-guidelines > references/markdown-report`.

## Test references

Statistical diagnostic tests organized by data shape. Load only what your data needs:

- `references/tests/distribution.md` — normality tests (Shapiro-Wilk, Jarque-Bera, Anderson-Darling), QQ-plot patterns, formal goodness-of-fit (KS, AD)
- `references/tests/regression.md` — heteroscedasticity (Breusch-Pagan, White, Goldfeld-Quandt), multicollinearity (VIF, condition number), specification (Ramsey RESET), influence diagnostics (leverage, Cook's D, DFBETAS, Studentized residuals, Mahalanobis)
- `references/tests/time-series.md` — stationarity (ADF, KPSS), autocorrelation (Durbin-Watson, Ljung-Box), ACF/PACF patterns, ARCH effects
- `references/tests/count.md` — overdispersion (Cameron-Trivedi, dispersion parameter), zero-inflation, Vuong test for non-nested models
- `references/tests/missing-and-hierarchical.md` — MCAR/MAR/MNAR mechanisms, Little's test, ICC, design effect

## Key Thresholds Summary

| Test | Threshold | Interpretation |
|------|-----------|----------------|
| Shapiro-Wilk W | > 0.95 | Approximately normal |
| VIF | > 10 | Severe multicollinearity |
| Durbin-Watson | 1.5-2.5 | No serious autocorrelation |
| ADF critical | -2.86 | 5% significance |
| Cook's D | > 1 | High influence |
| ICC | > 0.05 | Use multilevel model |
| Dispersion φ | > 2 | Overdispersion |
