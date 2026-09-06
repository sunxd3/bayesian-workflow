// Robust alternative to normal.stan: same location/scale, estimated tail df.
data {
  int<lower=1> N;
  vector[N] y;
}
parameters {
  real mu;
  real<lower=0> sigma;
  real<lower=1> nu;
}
model {
  mu ~ normal(0, 10);
  sigma ~ exponential(1);
  nu ~ gamma(2, 0.1);
  y ~ student_t(nu, mu, sigma);
}
generated quantities {
  vector[N] log_lik;
  vector[N] y_rep;
  for (n in 1:N) {
    log_lik[n] = student_t_lpdf(y[n] | nu, mu, sigma);
    y_rep[n] = student_t_rng(nu, mu, sigma);
  }
}
