// Neal's funnel, centered: reliably produces divergent transitions under NUTS.
// Used to prove the diagnostics flag real sampler pathology, not synthetic
// fixtures. No data block, no log_lik — also exercises the "LOO unavailable"
// path.
parameters {
  real y;
  vector[9] x;
}
model {
  y ~ normal(0, 3);
  x ~ normal(0, exp(y / 2));
}
