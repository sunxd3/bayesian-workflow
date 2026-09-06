---
name: model-critique
description: Three-part critique methodology for a single fitted Bayesian model — statistical, domain, and framework assessment plus the verdict structure and refinement-suggestion conventions.
user-invocable: false
---

# Model Critique

Reference for assessing a single fitted model from three angles: statistical health, domain validity, and framework appropriateness. Read references on demand. For diagnostic interpretation (LOO, Pareto k, LOO-PIT shapes), see `bayesian-model-diagnostics`. For PPC plot types, see `visual-predictive-checks`. For MCMC sampler health, see `convergence-diagnostics`.

## Key Practices

- **Ground every suggestion in diagnostic evidence.** "Consider a more flexible model" is useless; "LOO-PIT shows U-shape (underdispersed); switch Normal → Student-t to accommodate heavy tails" is useful. Each suggestion must trace back to a specific diagnostic pattern.
- **Framework concerns outrank within-framework refinements.** If the model ignores available data that could support a fundamentally different framework, that is the highest-priority issue — above any statistical or domain refinement.
- **Do not hallucinate domain conventions.** "I am uncertain whether this domain has a standard link function" beats fabricating one.
- **Respect statistical achievements.** If the model passes diagnostics and predicts well, do not suggest changes that would break it. Domain suggestions should be nested extensions or reparameterizations that preserve the current model as a special case where possible.

## References

- `references/statistical-assessment.md` — diagnostic evidence checks: LOO validity for grouped/temporal data, Pareto k, LOO-PIT, retrodiction-vs-prediction mismatch, estimand contraction, residual investigation, temporal-gap handling.
- `references/domain-assessment.md` — domain identification and the five sub-dimensions (link function, missing components, parameterization, predictor selection, model structure) with cross-domain examples.
- `references/framework-questioning.md` — the "is this the right framework given all the available data" check: unused data, framework alternatives, data-generating-process completeness.
- `references/decision.md` — VIABLE / CONCERNS / BROKEN verdict criteria and the report-section templates (priorities, framework concerns, new questions).
