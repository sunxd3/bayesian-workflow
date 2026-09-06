# Resolution Sequence

A designer's set of experiments should form a **resolution sequence** — models that, compared against each other, answer one structural question.

## Structure

- **Shared baseline (given).** Do not redesign this. Reference it as the comparison anchor. If the baseline contains mechanistic structure or domain-specific link functions, **preserve them across all variants**. Do not regress to a generic GLM unless your assigned question explicitly tests the removal of those specific components. You may modify the likelihood if necessary, but the mechanistic core must remain identical.
- **Core experiment.** The model that directly tests your question by adding the hypothesized structure to the baseline. This is the key comparison — if it beats the baseline, the structure matters; if not, the answer is "no."
- **Variants (1-2).** Probe the boundaries of the core experiment. Examples: a simpler version that tests whether a cheaper approximation suffices, a richer version that tests whether the structure needs more flexibility, or an alternative parameterization that tests sensitivity to modeling choices.

## Hierarchical progression

When your question involves grouped structure, expand incrementally: complete pooling (single parameter) → varying intercepts → varying slopes. Do not jump to varying slopes directly — the intermediate comparisons are informative (how much does partial pooling buy over no pooling?) and simpler models are cheaper to validate. Each step that fails to improve ELPD provides evidence that the added structure isn't needed.

## Inferential-purpose constraint

If the analysis purpose is inferential (see `analysis-design > Analysis purpose`), the resolution sequence must prioritize parameter interpretability over predictive performance. Do not add flexible structures that absorb the signal of the target estimand unless they serve as necessary controls for confounding. The goal is to isolate the estimand, not maximize ELPD.

## Per-experiment specification

Each experiment in the sequence must specify:

- **Generative story.** Full model specification (see the spec references in this skill — setup, likelihood, pooling-hierarchy, priors).
- **What it tests.** Which specific aspect of the structural question this experiment addresses.
- **Resolution and falsification.** What outcome would answer the question in each direction, and what would invalidate the model (see `references/falsification`).
- **Computational risks.** Expected sampling difficulties and parameterization preferences (see `references/identifiability`).
- **Key quantities of interest.** When the experiment plan defines target estimands, specify which model parameters or derived quantities correspond to them. Ensure these are identifiable and not absorbed by nuisance structure.
