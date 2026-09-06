// GQ-only fake-data simulator for normal.stan (stan skill, Pattern 2):
// true parameters enter as data, one draw of y_rep comes out.
data {
  int<lower=1> N;
  real mu;
  real<lower=0> sigma;
}
generated quantities {
  vector[N] y_rep;
  for (n in 1:N) y_rep[n] = normal_rng(mu, sigma);
}
