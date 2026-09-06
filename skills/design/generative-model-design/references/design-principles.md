# Design Principles

Apply these to every experiment spec.

## Mechanistic parameterization

Map parameters to physical or domain-meaningful quantities rather than generic regression coefficients. When extending a model, formulate new effects as targeted modifications to mechanistic components (e.g., scaling a rate, shifting a threshold) rather than adding additive linear predictors. Use the domain's canonical response functions over default GLM links.

## Recipe du Variate

When specifying a likelihood, follow two steps:

1. **Choose the density family from the variate's support** — counts → Poisson/NegBin, positive reals → LogNormal/Gamma, bounded [0,1] → Beta, ordered categories → ordinal, etc.
2. **Replace the location parameter with a function of covariates.**

Do not start from "linear regression" and then try to fix the likelihood family afterward.

## Broad family consideration

Do not only extend the baseline parametrically. Consider whether a fundamentally different model family better matches the data-generating process — GP regression for smooth nonlinear relationships, state-space models for temporal dynamics, spline-based models for flexible but structured trends, nonparametric density models for complex distributions. The baseline anchors comparison, but the best answer to a structural question may come from a different family entirely, not just a richer version of the same one.

## Mixture model discipline

When proposing mixture models, each component must correspond to a named physical process (e.g., "structural zeros from non-customers" vs "sampling zeros from low-activity customers"). Never propose "K normal components with unknown K" — this creates intractable permutation symmetry and component collapse. Use inflation models (zero-inflated, boundary-inflated) when the extra process is structural absence. Always require `ordered[K]` constraints on component location parameters.
