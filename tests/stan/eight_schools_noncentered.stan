// Eight schools, non-centered: a hierarchical model that converges cleanly,
// with a vector-valued transformed parameter to exercise dims in the summary.
data {
  int<lower=0> J;
  vector[J] y;
  vector<lower=0>[J] sigma;
}
parameters {
  real mu;
  real<lower=0> tau;
  vector[J] theta_tilde;
}
transformed parameters {
  vector[J] theta = mu + tau * theta_tilde;
}
model {
  mu ~ normal(0, 5);
  tau ~ cauchy(0, 5);
  theta_tilde ~ std_normal();
  y ~ normal(theta, sigma);
}
generated quantities {
  vector[J] log_lik;
  vector[J] y_rep;
  for (j in 1:J) {
    log_lik[j] = normal_lpdf(y[j] | theta[j], sigma[j]);
    y_rep[j] = normal_rng(theta[j], sigma[j]);
  }
}
