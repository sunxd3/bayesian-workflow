# Likelihood Decisions

Justify these three choices:

- **Support.** The likelihood must not assign probability to impossible values. Match the distribution family to the data's boundaries (counts cannot be Normal; positive quantities need positive-support distributions).
- **Noise geometry.** Is noise additive on the original scale (Normal family) or multiplicative / proportional to the mean (LogNormal/Gamma family)? Signal from EDA: if coefficient of variation is roughly stable, noise is multiplicative.
- **Dispersion.** Is variance constant, or does it vary with covariates or groups? If the EDA shows structured variance (fan shapes, group heterogeneity), model dispersion explicitly — often a better fix than switching to heavy-tailed distributions.

## Specialized zero/boundary processes

- **Hurdle.** Use when zeros come from a single binary decision (one process).
- **Zero-Inflated.** Use when zeros mix structural absence and sampling zeros (two processes).
- **Censored** (`censored_*` in Stan). Use when out-of-bounds values are recorded at the threshold (fixed N).
- **Truncated** (`T[,]` in Stan). Use when out-of-bounds values are simply unobserved (variable N).

Getting this wrong passes recovery checks (same wrong model generates and fits) and only fails at PPC on real data — wasting both a recovery run and a full fit.
