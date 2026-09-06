// GQ-only prior predictive program for normal.stan (stan skill, Pattern 1):
// mirrors the priors via _rng, generates y_rep, never sees the outcome.
data {
  int<lower=1> N;
}
generated quantities {
  real mu = normal_rng(0, 10);
  real sigma = exponential_rng(1);
  vector[N] y_rep;
  for (n in 1:N) y_rep[n] = normal_rng(mu, sigma);
}
