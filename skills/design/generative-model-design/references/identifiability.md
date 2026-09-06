# Identifiability Risks

Flag expected computational problems for downstream agents:

- **Sample-size aliasing.** Are there parameter combinations that produce indistinguishable data at your sample size? Note what the recovery checker should watch for.
- **Funnel geometry.** Does the hierarchy create funnel geometry (sparse groups)? Note the parameterization preference (centered vs non-centered).
- **Separation.** Can coefficients diverge (separation in logistic models with rare events)? Regularizing priors are mandatory.
- **Redundant intercepts.** Never include both a global intercept and unconstrained group-level intercepts (e.g., `alpha_0 + alpha[group]` where `alpha ~ normal(mu, sigma)`). This creates a non-identifiable sum. Either use a non-centered parameterization (`alpha_0 + sigma * z[group]`) or constrain group effects to sum-to-zero via `sum_to_zero_vector`.
