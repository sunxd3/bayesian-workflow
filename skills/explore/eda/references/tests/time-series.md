# Time Series Diagnostics

Use these diagnostics to classify dependence and residual structure. For Bayesian modeling, the output should guide temporal hierarchy, latent state, trend/seasonality, and validation design. Do not pretest away time dependence and then treat observations as exchangeable.

## Implementation

Prefer statsmodels:

Version assumptions: snippets target statsmodels 0.14.6-era APIs. Record `statsmodels.__version__` in the EDA output. If the installed version differs, inspect signatures and defaults for lag selection, returned p-values, and result containers before relying on automated interpretation.

```python
from statsmodels.tsa.stattools import adfuller, kpss, acf, pacf
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.stats.stattools import durbin_watson

adfuller(y, regression="c", autolag="AIC")
kpss(y, regression="c", nlags="auto")
acf(y, nlags=40, fft=True)
pacf(y, nlags=40)
acorr_ljungbox(resid, lags=[10, 20], model_df=0, return_df=True)
het_arch(resid, nlags=12)
durbin_watson(resid)
```

## Stationarity

- **ADF.** Null hypothesis is a unit root. Rejection is evidence against a unit root under the chosen deterministic terms and lag selection.
- **KPSS.** Null hypothesis is level or trend stationarity. Rejection is evidence against that stationarity specification.

Correctness notes:

- Do not hard-code a universal ADF critical value. Use the returned p-value and critical values for the chosen `regression` and lag settings.
- ADF and KPSS can disagree because of structural breaks, deterministic trends, seasonality, lag choice, short samples, or nonlinear dynamics.
- "Both reject" is not automatically trend-stationarity; it is a warning that the simple stationarity/unit-root framing is inadequate.
- Seasonal unit roots, changepoints, irregular timestamps, and panel time series need additional structure beyond these tests.

Bayesian implications:

- **Non-stationary level.** Consider random walk, local linear trend, state-space, Gaussian process, or explicit trend terms.
- **Trend-stationary behavior.** Include deterministic trend or smooth temporal effect.
- **Seasonal structure.** Include seasonal fixed effects, seasonal AR terms, periodic kernels, or hierarchical seasonal effects.

## Autocorrelation

- **Durbin-Watson.** Quick residual screen for first-order autocorrelation. Values near 2 indicate weak AR(1)-style residual autocorrelation; values near 0 or 4 indicate positive or negative autocorrelation.
- **Ljung-Box.** Joint test of autocorrelation up to selected lags. Use on residuals from a provisional model and account for fitted ARMA parameters with `model_df`.
- **ACF/PACF.** Visual diagnostics for lag structure.

Correctness notes:

- Durbin-Watson is narrow: it is mainly an AR(1) residual diagnostic and is not reliable with lagged dependent variables or complex temporal models.
- Ljung-Box p-values depend on lag choice. Do not scan many lags and report only the most significant one.
- ACF/PACF ARMA heuristics assume a roughly stationary linear process. Seasonality, missing timestamps, changepoints, and long memory can mimic simple AR/MA patterns.

ACF/PACF heuristics:

- **ACF gradual decay and PACF cutoff near lag `p`.** AR(`p`) candidate.
- **ACF cutoff near lag `q` and PACF gradual decay.** MA(`q`) candidate.
- **Both decay.** ARMA candidate.
- **Slow ACF decay and very high lag-1 PACF.** Unit-root or strong persistent-state candidate.
- **Spikes at seasonal lags.** Seasonal or calendar structure.

## ARCH Effects

- **ARCH LM (`het_arch`).** Tests whether squared residuals are autocorrelated, indicating volatility clustering or time-varying residual scale.

Correctness notes:

- Rejection does not always imply a financial-style GARCH model. In scientific data, it may indicate regime changes, missing covariates, time-varying measurement error, or group-specific scale.
- Heavy-tailed residuals and volatility clustering are different problems. Student-t likelihoods handle outliers; time-varying scale handles persistent changes in residual variance.

## Report

Report package versions, timestamp regularity, gaps, sample span, whether diagnostics were run on raw data or residuals, lag choices, test statistics and p-values, ACF/PACF patterns, and validation implications. State whether downstream comparison should use blocked, rolling-origin, group-time, or ordinary observation-level validation.
