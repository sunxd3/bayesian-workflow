---
name: generative-model-design
description: Required decisions for complete generative model specifications, the experiment-design discipline behind a resolution sequence, and the cross-cutting modeling principles that apply to every spec.
user-invocable: false
---

# Generative Model Design

Reference for specifying generative models and organizing experiments around a structural question. Read references on demand — each section below is a required decision when specifying a model; the principles and resolution-sequence references apply across the whole proposal.

For the upstream analysis-level decisions (analysis purpose, validation strategy, domain context, and the structural questions themselves), see `analysis-design`.

## Key Practices

- **Mixture model discipline.** Every component must correspond to a named physical process. Never propose "K Normal components with unknown K" — it produces permutation symmetry and component collapse. Always require `ordered[K]` constraints on component location parameters. Use Hurdle vs Zero-Inflated, Censored vs Truncated based on the real generative story, not what's convenient.
- **Prior geometry hazards.** Never use `inv_gamma` for variance/scale hyperpriors (creates funnel + artificial lower bound) — prefer `exponential`, `normal<lower=0>`, or `student_t(3, 0, s)<lower=0>`. For correlation matrices use `lkj_corr_cholesky(eta)` with `eta >= 2`.
- **Process model vs observation model.** Separate the noiseless latent truth from the observation process (censoring, truncation, rounding, selection). Most likelihood mistakes conflate the two.

## Spec references

Each section below is a required decision in a complete spec. Read on demand while specifying an experiment.

- `references/setup.md` — measurement story and observation-unit independence (§1-§2)
- `references/likelihood.md` — likelihood family, noise geometry, dispersion, zero/boundary processes (§3)
- `references/pooling-hierarchy.md` — pooling structure, grouping factors, what's hierarchical and why (§4)
- `references/priors.md` — prior implications on the observable scale, containment calibration, prior pushforward check (§5)
- `references/identifiability.md` — non-identifiability and computational risks; flag for downstream agents (§6)
- `references/falsification.md` — what would break this model — targeted PPC, ELPD resolution, parameter resolution (§7)

## Design-discipline references

Cross-cutting principles and structure for experiment sets:

- `references/design-principles.md` — mechanistic parameterization, Recipe du Variate, broad family consideration, mixture discipline (deep dive). Apply to every spec.
- `references/resolution-sequence.md` — how to organize a set of experiments (shared baseline → core → variants; hierarchical progression; inferential-purpose constraints) so that comparisons answer a structural question.
