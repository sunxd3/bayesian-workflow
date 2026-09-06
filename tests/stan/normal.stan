// Normal likelihood with pointwise log_lik and y_rep — the canonical layout
// every model in the workflow follows (fit → LOO → PPC).
data {
  int<lower=1> N;
  vector[N] y;
}
parameters {
  real mu;
  real<lower=0> sigma;
}
model {
  mu ~ normal(0, 10);
  sigma ~ exponential(1);
  y ~ normal(mu, sigma);
}
generated quantities {
  vector[N] log_lik;
  vector[N] y_rep;
  for (n in 1:N) {
    log_lik[n] = normal_lpdf(y[n] | mu, sigma);
    y_rep[n] = normal_rng(mu, sigma);
  }
}
