---
name: stan
description: Best practices for writing efficient, clean Stan programs. Covers structure, parameterization, prior/posterior predictive blocks, and pitfalls. Sub-references handle specialized cases.
user-invocable: false
---

# Stan

Use this skill when writing or modifying Stan programs to ensure clean, efficient code.

**Specialized patterns.** Read the reference on demand:
- `references/ode.md` — ODE-based dynamics (SIR/SEIR, PK/PD, population, biochemical, growth models) using Stan 2.24+ modern interfaces (`ode_rk45`, `ode_bdf`, `ode_adams`, adjoint).
- `references/horseshoe.md` — horseshoe priors for sparse regression (automatic variable selection, regularized horseshoe).

## Program Structure

Use canonical block order: `functions`, `data`, `transformed data`, `parameters`, `transformed parameters`, `model`, `generated quantities`.

Follow Stan style:
- **Indentation.** Two-space, no tabs, ≤80 character lines.
- **Braces.** Opening brace at end of line: `for (n in 1:N) {`.
- **Spacing.** Spaces around operators and after commas.
- **Variable names.** Lowercase with underscores (`sigma_y`, `mu_group`).
- **Dimension constants.** Single uppercase letters (`N`, `K`, `J`).
- **Local declarations.** Close to use; scalars inside loops, reused containers outside.

## Types and Containers

Use appropriate types:
- **Linear algebra.** `matrix`, `vector`, `row_vector` with matrix operations (`x * beta`).
- **Indexing/containers.** `array[N] real y` (not legacy `real y[N]`).
- **Repeated row access.** `array[M] row_vector[N] x` over `matrix[M, N]`.
- **Heterogeneous returns.** `tuple(...)` for multiple values.
- **Sum-to-zero.** `sum_to_zero_vector`, `sum_to_zero_matrix` instead of manual constraints.
- **Stochastic matrices.** `row_stochastic_matrix[M, N]` (each row is a simplex), `column_stochastic_matrix[M, N]` (each column is a simplex) — use for HMM transition/emission matrices.
- **Mixtures.** Declare component location parameters as `ordered[K]` to break label-switching symmetry. Without this, the posterior has K! equivalent modes and NUTS wastes hours producing unusable samples. Even with ordering, components with the same functional form can still exhibit continuous degeneracies (component collapse) — each component should correspond to a distinct physical process. Label-switching causes catastrophic R-hat (>10) without divergences; the fix is ordering constraints, not longer chains.

Memory layout: matrices are column-major, arrays are row-major.

## Distributions and Vectorization

Always use log form:
- **Density notation.** Write `y ~ normal(mu, sigma)` or `target += normal_lpdf(y | mu, sigma)`.
- **Vectorization.** `y ~ normal(mu, sigma)` for arrays, not loops.
- **GLM functions.** Use `bernoulli_logit_glm`, `poisson_log_glm`, `normal_id_glm`.
- **Precomputation.** Compute shared expressions once (e.g., `mu = X * beta`) and reuse.
- **Finite mixtures.** Use `log_sum_exp` on log scale.

**Boolean aggregation in generated quantities.**
Stan does NOT support vectorized boolean comparisons. Use loops:
```stan
// ❌ WRONG - causes semantic error
int n_below = sum(to_vector(p_pred) < 0.01);

// ✓ CORRECT - loop over elements
int n_below = 0;
for (n in 1:N) {
  if (p_pred[n] < 0.01) n_below += 1;
}
```

## Parameterization

Use constrained types over manual checks:
- **Common constraints.** `<lower=0>`, `<upper=...>`, `ordered`, `positive_ordered`, `simplex`, `unit_vector`.
- **Covariance (K≥3).** `cholesky_factor_corr[K] L_Omega` with `multi_normal_cholesky`.
- **Sum-to-zero.** Use built-in types, not "last element = minus sum".

**Non-centered via offset/multiplier.**
```stan
// Instead of manual non-centered:
//   vector[J] z; ... theta = mu + sigma * z;
// Use built-in syntax:
vector<offset=mu, multiplier=sigma>[J] theta;
// Stan samples as (theta - mu) / sigma ~ N(0,1) automatically
```
Works on `real`, `vector`, `row_vector`, `matrix`. Prefer this over manual non-centered parameterization.

**Mixed centered/non-centered for unbalanced hierarchies:**
When group sizes vary widely, neither monolithic centered nor non-centered works. Use mixed parameterization:
```stan
data {
  int<lower=1> K_cp;                // number of centered groups
  int<lower=1> K_ncp;               // number of non-centered groups
  array[K_cp] int cp_idx;           // indices of data-rich groups
  array[K_ncp] int ncp_idx;         // indices of data-sparse groups
}
parameters {
  vector[K_cp] theta_cp;            // centered: direct group effects
  vector[K_ncp] eta_ncp;            // non-centered: standardized offsets
  real mu;
  real<lower=0.001> tau;
}
transformed parameters {
  vector[K_cp + K_ncp] theta;
  theta[cp_idx] = theta_cp;
  theta[ncp_idx] = mu + tau * eta_ncp;
}
model {
  theta_cp ~ normal(mu, tau);       // centered likelihood
  eta_ncp ~ std_normal();           // non-centered likelihood
}
```
Heuristic: histogram observation counts per group. Groups with >25 observations → centered; sparse groups → non-centered. Split at natural gaps in the count distribution.

**Tau prior and parameterization are coupled decisions:**
- **Non-centered + infinity-suppressing tau prior** (`half_normal`, `exponential`). Most robust default when testing whether heterogeneity exists (expanding from homogeneous model).
- **Centered + zero-suppressing tau prior.** Appropriate when testing whether groups share information (expanding from unpooled model).
- **Coupling discipline.** Never choose parameterization and tau prior independently — they are complementary.

**QR reparameterization for correlated predictors:**
When predictors are correlated, coefficient posteriors have difficult geometry. Decorrelate via QR:
```stan
transformed data {
  matrix[N, K] Q = qr_thin_Q(X) * sqrt(N - 1);
  matrix[K, K] R_inv = inverse(qr_thin_R(X) / sqrt(N - 1));
}
parameters {
  vector[K] theta;  // coefficients in decorrelated space
}
generated quantities {
  vector[K] beta = R_inv * theta;  // recover original-scale coefficients
}
```

**CRITICAL: Scale parameters must have positive lower bounds:**
```stan
// ❌ WRONG - sigma can reach exactly 0 and crash sampling
real<lower=0> sigma;

// ✓ CORRECT - prevents sigma=0 crashes in hierarchical models
real<lower=0.001> sigma;
real<lower=0.01> sigma_group[J];
```
This is especially important for hierarchical priors where scale parameters can collapse to zero.

For custom transforms, use built-in `*_constrain`, `*_unconstrain`, `*_jacobian` functions.

## Parallelization

For large-N models with independent terms, use `reduce_sum`:
- Write partial sum function that takes data slice and returns log-density contribution
- Keep partial sum vectorized internally
- No side effects (no printing, no mutation)

## Functions

Modularize complex logic in `functions` block:
- **Use cases.** Reused operations, complex math, custom likelihoods.
- **Argument order.** Data first, then parameters, then tuning constants.
- **Multiple returns.** Use `tuple` for heterogeneous outputs.

**Common function name errors:**
- Use `abs()` NOT `fabs()` - Stan renamed it from C conventions
- Use `sqrt()` NOT `sqrtf()` - Stan uses full precision names
- Use `exp()` NOT `expf()` - all Stan functions are full precision

## Preventing Crashes

Both compilation and sampling can crash or OOM.

**Defensive Stan patterns:**
- Always use tight bounds: `int<lower=1, upper=K> id[N]`
- Guard math: check parameters before `log`, `sqrt`, division
- Add explicit bounds for dispersion: `real<lower=0.01> phi` (never exactly 0)
- Never use `<lower=0>` for scale parameters in hierarchical models — use `<lower=0.001>` or higher

**Execution:**
- Wrap `CmdStanModel()` and sampling in try-except
- Probe with short runs before full sampling
- Always ensure warmup > 0 when `adapt_engaged=True` (minimum 50-100 iterations) — Stan needs warmup to adapt the mass matrix
- NEVER use the Read tool on large Stan CSV files (>256KB) — use `cmdstanpy` summary methods or head/tail commands instead

**CRITICAL: Suppress Stan progress output.**
Stan progress bars (tqdm + CmdStan stdout) accumulate in the agent transcript and can crash the session when the transcript exceeds buffer limits. Always suppress them:
- The `fit-pipeline` reference scripts already pass `show_progress=False, show_console=False` — keep that when adapting them
- If calling `model.sample()` directly: always pass `show_progress=False, show_console=False` (leave `refresh` at its default — CmdStanPy ≥ 1.3 rejects `refresh=0`)
- If running a Stan binary from the command line: pass `refresh=0`
- NEVER set `show_progress=True` or `show_console=True` — they produce megabytes of output that bloats the transcript

**On crash/OOM:**
- Reduce `parallel_chains` (4 → 2 → 1)
- Reduce `max_treedepth` (10 → 8)
- Subsample data or simplify model

For the Python fitting workflow (posterior fit, prior and recovery recipes, artifact contract), see the `fit-pipeline` skill.

## ArviZ Integration

Design Stan programs for downstream ArviZ workflow:

**Generated quantities:**
- Always include pointwise log-likelihood: `vector[N] log_lik` — required for model comparison and downstream workflow
- Always include posterior predictive draws: `vector[N] y_rep` — required for all predictive checks
- Use CONSISTENT naming: `y_obs` for observed data, `y_rep` for replications — avoid mixing `y`, `y_pred`, `y_sim`
- For multiple observed variables, use one vector per variable: `log_lik_y1`, `log_lik_y2`
- This will incur modest overhead, but might be worth workflow simplicity

**Transformed parameters:**
- Put reusable intermediate quantities here (e.g., `vector[N] mu = alpha + X * beta`)
- Avoids recomputation in Python and makes them available in posterior samples

**Extending without refitting:**
- To add new derived quantities, use `generate_quantities` mode with original posterior draws
- Write new Stan file with same data/parameters/transformed parameters but extended generated quantities
- Call `model.generate_quantities(data=data, mcmc_sample=fit)` — orders of magnitude faster than refitting

For InferenceData group structure and naming conventions, see `inferencedata-handling`.

## Generated-Quantities-Only (GQ-Only) Programs

GQ-only programs are Stan programs without `parameters` or `model` blocks. They run via `fixed_param=True` (with `iter_warmup=0, adapt_engaged=False`) and produce synthetic data via `_rng` calls. Two patterns:

- **Prior simulation.** Sample parameters from priors, generate `y_rep` (Pattern 1).
- **Data simulator.** Take known parameter values as `data{}` input, generate `y_rep` (Pattern 2).

For the methodology (why Stan must own data generation, what the line-by-line mirror invariant means), see `fake-data-simulation > Key Practice — Stan is the single source of truth`. For the Python workflow (compile, run with `fixed_param`, convert, save), see `fit-pipeline > references/prior_predictive.py` and `references/fake_data.py`.

### Pattern 1: Prior Simulation (`prior_model.stan`)

Samples parameters from their priors via `_rng` functions, then generates synthetic data. Place in `prior_predictive/prior_model.stan`.

```stan
// prior_model.stan — mirrors priors from model.stan
data {
  int<lower=1> N;
  // ... same data declarations as model.stan (dimensions, covariates)
  // Do NOT include observed y — this generates it
}
generated quantities {
  // 1. Draw parameters from priors (MUST match model.stan exactly)
  real alpha = normal_rng(0, 10);
  real<lower=0> sigma = lognormal_rng(0, 1);

  // 2. Compute transformed parameters (same logic as model.stan)
  vector[N] mu;
  for (n in 1:N)
    mu[n] = alpha;  // + beta * x[n], etc.

  // 3. Generate replicated data (same likelihood as model.stan)
  array[N] real y_rep;
  for (n in 1:N)
    y_rep[n] = normal_rng(mu[n], sigma);
}
```

Every `_rng` call must mirror the corresponding `~` statement in `model.stan`. If you change a prior in `model.stan`, update `prior_model.stan` to match.

### Pattern 2: Data Simulator (`simulator.stan`)

Takes known parameter values as `data{}` input, generates synthetic data. Place in `simulation/simulator.stan`. Used for parameter recovery checks.

```stan
// simulator.stan — generates data from known parameters
data {
  int<lower=1> N;
  // ... same data declarations as model.stan (dimensions, covariates)

  // True parameter values (passed in from Python)
  real alpha_true;
  real<lower=0> sigma_true;
}
generated quantities {
  // Compute transformed parameters (same logic as model.stan)
  vector[N] mu;
  for (n in 1:N)
    mu[n] = alpha_true;

  // Generate synthetic data (same likelihood as model.stan)
  array[N] real y_rep;
  for (n in 1:N)
    y_rep[n] = normal_rng(mu[n], sigma_true);
}
```

### GQ-Only Pitfalls

- `_rng` functions are only available in `generated quantities` and `transformed data` blocks
- For `<lower=0>` parameters: use `lognormal_rng()`, `exponential_rng()`, or `fabs(normal_rng())` — not manual truncation
- For `ordered` vectors: draw independently and `sort_asc()`
- For `simplex` vectors: `dirichlet_rng(alpha)`
- For `cholesky_factor_corr`: `lkj_corr_cholesky_rng(K, eta)` (Stan ≥ 2.32)
- For multivariate normals: `multi_normal_rng(mu, Sigma)` or `multi_normal_cholesky_rng(mu, L)`
- **Subsampling for large N.** When N > 2000, subsample the data dict in Python before passing to Stan (fewer rows, adjusted N). The Stan program is unchanged.

**Do NOT** run the main inference model with `fixed_param=True` for prior simulation — `fixed_param=True` does not sample from priors in the `parameters{}` block; it holds them at their initial values. Always use a GQ-only `prior_model.stan`.

## Known Issues

- **CmdStanPy `diagnose()` OOMs.** Fails on large data (N > 10K). Compute R̂/ESS from `az.summary` the way `fit-pipeline > references/posterior_fit.py` does instead.
- **ArviZ column names.** Lowercase (`r_hat`, `ess_bulk`). CmdStanPy uses uppercase (`R_hat`, `ESS_bulk`).
- **CmdStanPy summary columns renamed.** `N_Eff` → `ESS_bulk`, `N_eff` → `ESS_tail`. Use the ESS_* names.
- **Stan CSV columns.** Use dots: `beta.1` not `beta[1]`.
- **ArviZ expects specific group names.** Ensure `y` in `observed_data` and `y_rep` in `posterior_predictive` exist.
- **NumPy 2.x removed `np.trapz`.** Use `scipy.integrate.trapezoid` instead.

## Numerical Stability

When writing custom log-density functions or user-defined functions:
- Use Stan's stable math functions: `log_sum_exp`, `log1p_exp`, `log1m_exp`, `log_diff_exp`, `log1m` instead of manual `log(exp(...))` or `log(1-x)` expressions
- Check for degenerate parameter configurations where both numerator and denominator approach zero (0/0 indeterminate forms). Derive a first-order Taylor approximation at the degenerate limit and implement a piecewise function: `if (fabs(x) < 1e-8) { use_taylor_approx; } else { use_exact; }`
- Guard against `log(0)` at parameter boundaries: use `log1m(x)` instead of `log(1-x)` when x can approach 1
- For interval-censored likelihoods, use `log_diff_exp(log_cdf_upper, log_cdf_lower)` — never compute `cdf_upper - cdf_lower` and then take `log()`

## References

If stuck on Stan patterns or ArviZ usage, search these resources:
- Stan case studies: https://mc-stan.org/learn-stan/case-studies.html
- ArviZ API documentation: https://python.arviz.org/en/latest/api/index.html

Use WebSearch or WebFetch to find specific examples.
