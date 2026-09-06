# Horseshoe Prior for Sparse Bayesian Regression

Reference for sparse regression models with horseshoe priors. The horseshoe prior provides automatic variable selection with heavy tails for large effects and strong shrinkage for small effects. Combine with the core `stan` skill for general program structure.

## When to Use

- High-dimensional regression (p >> n or p ≈ n)
- Sparse signal (most coefficients near zero, few large effects)
- Variable selection without threshold decisions
- Continuous shrinkage (no discrete inclusion indicators)

## Stable Implementation (Recommended)

The naive horseshoe using Cauchy(0,1) priors can produce NaN values due to extreme tail samples where `tau² × lambda²` overflows. Use this **stable bounded parameterization**:

```stan
data {
  int<lower=0> N;           // number of observations
  int<lower=0> P;           // number of predictors
  matrix[N, P] X;           // predictor matrix (standardized)
  vector[N] y;              // outcome
  real<lower=0> scale_global;  // expected number of non-zero coefficients
}

parameters {
  real alpha;                              // intercept
  vector[P] z;                             // standard normal
  vector<lower=0, upper=1>[P] lambda_raw;  // local shrinkage (bounded)
  real<lower=0, upper=1> tau_raw;          // global shrinkage (bounded)
  real<lower=0.001> sigma;                 // error SD (never exactly 0)
}

transformed parameters {
  // Stable parameterization: bounded lambda/tau prevent overflow
  real tau = tau_raw * scale_global / (P - scale_global);  // scale to prior belief
  vector[P] lambda = lambda_raw;  // local scales
  vector[P] beta = z .* lambda * tau;  // non-centered: beta = z * lambda * tau
}

model {
  // Priors
  alpha ~ normal(0, 5);
  z ~ std_normal();

  // Regularized horseshoe: Student-t(nu, 0, 1) is more stable than Cauchy
  lambda_raw ~ beta(0.5, 0.5);  // induces heavy-tailed prior on lambda
  tau_raw ~ beta(0.5, 0.5);     // induces heavy-tailed prior on tau
  sigma ~ exponential(1);

  // Likelihood
  y ~ normal(alpha + X * beta, sigma);
}

generated quantities {
  vector[N] y_rep;
  vector[N] log_lik;

  for (n in 1:N) {
    real mu = alpha + X[n] * beta;
    y_rep[n] = normal_rng(mu, sigma);
    log_lik[n] = normal_lpdf(y[n] | mu, sigma);
  }
}
```

## Alternative: Student-t Regularization

For more stability, replace Cauchy with Student-t(nu, 0, 1):

```stan
parameters {
  real alpha;
  vector[P] beta_raw;
  vector<lower=0.001>[P] lambda;  // positive lower bound
  real<lower=0.001> tau;          // positive lower bound
  real<lower=0.001> sigma;
}

transformed parameters {
  vector[P] beta = beta_raw .* lambda * tau;
}

model {
  alpha ~ normal(0, 5);
  beta_raw ~ std_normal();

  // Student-t(3) is more stable than Cauchy (Student-t(1))
  lambda ~ student_t(3, 0, 1);
  tau ~ student_t(3, 0, scale_global);
  sigma ~ exponential(1);

  y ~ normal(alpha + X * beta, sigma);
}
```

## Hyperparameter Selection

**`scale_global` (expected number of non-zero effects).**
- **Meaning.** Prior belief about sparsity.
- **Rule of thumb.** `scale_global = expected_p0 / sqrt(N)`.
- **Example.** Expect 5 of 100 predictors non-zero with N=200 → `scale_global = 5/sqrt(200) ≈ 0.35`.
- **Sensitivity.** Results often robust to values between `p0/(2*sqrt(N))` and `p0*2/sqrt(N)`.

**Student-t degrees of freedom (nu).**
- **`nu=1` (Cauchy).** Maximum heavy tails, most aggressive selection, can cause NaN.
- **`nu=3`.** Good balance of heavy tails and stability (recommended).
- **`nu=7`.** Lighter tails, more regularization.
- **Higher nu.** Closer to normal prior → less sparsity.

## Convergence and Diagnostics

Horseshoe models can be challenging to sample:

**Sampling settings:**
```python
fit = model.sample(
    data=data,
    iter_warmup=2000,    # longer warmup for horseshoe
    iter_sampling=2000,
    chains=4,
    adapt_delta=0.95,    # higher adapt_delta reduces divergences
    max_treedepth=12,    # may need deeper trees
)
```

**Check for issues.**
- **Divergent transitions.** Increase `adapt_delta` to 0.98 or use bounded parameterization.
- **NaN in `lambda` or `tau`.** Switch to bounded or Student-t parameterization.
- **Poor ESS for `lambda`.** Non-centered parameterization helps (use `z ~ normal(0,1)`).
- **Rhat > 1.01.** Run longer chains or increase warmup.

## Post-Processing: Credible Intervals for Selection

Horseshoe doesn't provide binary selection, but you can assess importance:

```python
import arviz as az

# Posterior means and credible intervals
summary = az.summary(idata, var_names=["beta"])

# Identify "significant" predictors (95% CI excludes zero)
mask = (summary["hdi_2.5%"] * summary["hdi_97.5%"]) > 0
selected = summary[mask].index.tolist()
```

## Common Failure Modes

1. **NaN in `lambda_tilde` or `tau`.** Cauchy tails caused overflow.
   - **Fix.** Use bounded parameterization or Student-t(3).

2. **Divergent transitions.** Posterior has sharp boundaries.
   - **Fix.** Increase `adapt_delta` to 0.95 or 0.98.
   - **Fix.** Use non-centered parameterization.

3. **All coefficients shrunk to zero.** Prior too strong.
   - **Fix.** Increase `scale_global`.
   - **Fix.** Reduce tau prior strength.

4. **Insufficient ESS.** Non-centered parameterization not used.
   - **Fix.** Use `beta = z .* lambda * tau` with `z ~ std_normal()`.

## References

- Piironen & Vehtari (2017). "Sparsity information and regularization in the horseshoe and other shrinkage priors." Electronic Journal of Statistics.
- Piironen & Vehtari (2017). "On the Hyperprior Choice for the Global Shrinkage Parameter in the Horseshoe Prior." AISTATS.
- Stan case study: https://mc-stan.org/users/documentation/case-studies/bayes_sparse_regression.html

For other approaches, consider spike-and-slab or regularized horseshoe priors.
