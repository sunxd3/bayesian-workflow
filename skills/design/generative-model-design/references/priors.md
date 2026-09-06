# Prior Implications

Do not just list prior distributions — state their implications on the observable scale. For parameters on transformed scales (logit, log), translate the prior to the natural scale and verify the implied range covers plausible values without extending to physical absurdities.

For hierarchical models, explicitly define the hyperprior on the group-level standard deviation. It must be strictly positive and control the degree of shrinkage.

## Containment prior calibration

For any parameter with plausible domain bounds [L, U], calibrate the prior so ~98% of mass falls inside. Quick formula for Normal prior: σ ≈ (U - L) / 4.64. For positive parameters, use lognormal or gamma tuned via quantile matching to the containment targets.

## Prior pushforward check

After setting priors, draw parameters from the prior, compute derived/transformed quantities (probabilities, rates, observable-scale predictions), and verify they don't pile up at boundaries (0 or 1 for probabilities, 0 or ∞ for scales). If they do, iteratively tighten the prior until the pushforward is sensible. This catches geometry problems that direct prior checks miss — a prior that looks reasonable in parameter space can produce absurd predictions.

## Prior anti-patterns that cause geometry problems (not caught by prior predictive checks)

- Never use `inv_gamma` for variance/scale hyperpriors — it creates artificial lower bounds on group-level variation and funnel geometry. Prefer `exponential`, `normal<lower=0>`, or `student_t(3, 0, s)<lower=0>`.
- For correlation matrices, use `lkj_corr_cholesky(eta)` with `eta >= 2` to regularize toward identity. `eta = 1` is uniform over correlation matrices (often too diffuse); `eta < 1` favors extreme correlations.
