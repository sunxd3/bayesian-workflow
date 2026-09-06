---
name: convergence-diagnostics
description: MCMC convergence diagnostics — thresholds, visual checks, and interpretation of HMC pathologies.
user-invocable: false
---

# Convergence Diagnostics

Use this skill when checking MCMC convergence after fitting Stan models.
Convergence means chains mixed and explored the same target, and you have
enough effective draws.

## Running diagnostics

The canonical workflow computes convergence from `az.summary` — see
`summarize()` in `fit-pipeline > references/posterior_fit.py`, which applies the
thresholds below and writes them to `summary.json`. It avoids the OOM that raw
`fit.diagnose()` can hit on large datasets (N > 10K).

For raw access: `fit.summary()` returns `R_hat` / `ESS_bulk` / `ESS_tail` /
`MCSE` per parameter; `fit.diagnose()` checks for divergences, max treedepth,
low E-BFMI, low ESS, high R-hat. If diagnose reports no problems, you still
need the visual checks below.

For ArviZ-side numerical diagnostics on an InferenceData object:
- `az.rhat(idata)` — rank-normalized split R-hat
- `az.ess(idata)` — bulk and tail effective sample size
- `az.bfmi(idata)` — Bayesian fraction of missing information
- `az.mcse(idata)` — Monte Carlo standard error
- `az.summary(idata)` — all diagnostics in one table

See `inferencedata-handling` for converting `fit` → InferenceData.

## Thresholds

Must achieve:
- **R̂ < 1.01** (all parameters). Measures chain agreement.
- **ESS bulk and tail ≥ 400** per parameter. Enough effective draws.
- **BFMI ≥ 0.3** per chain. Adequate energy exploration.
- **MCSE << posterior SD.** Monte Carlo error small relative to uncertainty.
- **No divergent transitions** after warmup.

## Visual Diagnostics

**Chain mixing and stationarity:**
- `az.plot_trace()` — should show "fat fuzzy caterpillars", no trends or stuck chains. Divergences shown as vertical lines.
- `az.plot_rank()` — rank histograms should be uniform and similar across chains. U-shapes or skew indicate poor mixing.

**Autocorrelation and ESS:**
- `az.plot_autocorr()` — slow decay indicates high correlation and low ESS
- `az.plot_ess(kind="evolution")` — ESS growth over draws; should keep climbing
- `az.plot_ess(kind="local")` — ESS in local windows/quantiles; checks tail exploration

**HMC-specific pathologies:**
- `az.plot_energy()` — overlays energy transitions vs marginal energy. Low BFMI shows mismatch.
- `az.plot_pair(divergences=True)` — localizes divergences in parameter space (funnels, tight correlations). For hierarchical models: plot each group-level parameter vs `log(population_scale)` with divergent transitions highlighted. Divergences near small scale = centered funnel (use non-centered). Divergences near large scale = inverted funnel (use centered).
- `az.plot_parallel()` — parallel coordinates showing divergent vs non-divergent draws

## Common Issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Divergences + low BFMI | Geometry problems (funnels, stiff regions) | Reparameterize or increase `adapt_delta` to 0.95–0.98 |
| High R̂, good visuals | Chains haven't run long enough | Extend iterations |
| Low ESS, good R̂ | High autocorrelation | Reparameterize (non-centered) or run longer |
| Max treedepth warnings | Strong correlations | Reparameterize or simplify model |
| Multimodality in `plot_posterior` | Identification problem or multiple modes | See *Convergence Without Identifiability* below |

For tooling pitfalls (ArviZ lowercase vs CmdStanPy uppercase column names;
KeyErrors on conversion), see `stan > Known Issues` and
`inferencedata-handling > Common failures`.

## Convergence Without Identifiability

A model can have R-hat < 1.01, zero divergences, and adequate ESS while being
structurally non-identified. Convergence diagnostics only verify the sampler
explored its target — they do not verify the target is well-posed.

Signs of non-identifiability despite clean convergence:
- Pairs plots show ridge, surface, or circular structures (parameters trade off against each other)
- Posterior SDs do not shrink proportional to 1/√N when data size increases
- Parameter pairs with |correlation| > 0.95
- Mixture-model components show R-hat > 10 without divergences (label-switching); fix with ordering constraints, not longer chains.

If suspected: classify the degeneracy (additive redundancy `a+b=const`,
multiplicative `a×b=const`, label symmetry) and reparameterize to identified
quantities (anchor one reference level, use contrasts instead of absolute
effects, apply ordering constraints for mixture components).

You never prove convergence, only build a strong circumstantial case. The
sampler tells you about your model — listen to it.
