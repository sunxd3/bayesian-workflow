---
name: analysis-design
description: Methodology for setting up a Bayesian analysis — analysis purpose, validation strategy, domain context, structural questions. Read before specifying any models.
user-invocable: false
---

# Analysis Design

Reference for the design-phase decisions that precede model specification: what
is this analysis trying to do, how will it be evaluated, what domain
conventions apply, and what structural questions about the data-generating
process should the candidate models address.

These are the choices a competent statistician makes once per analysis, before
any individual model is specified. For specifying generative models within a
structural question, see `generative-model-design`.

## Key Practices

- **Assume loudly.** When the user's prompt lacks a specific question,
  synthesize a purpose from the data's nature and state it explicitly. A sharp
  answer to an assumed question beats a generic answer to no question.
- **Validation discipline.** Standard observation-level LOO is only appropriate
  for i.i.d. data. For grouped data it interpolates within known groups; for
  temporal data it overstates future predictive performance. Pick the hold-out
  scheme that matches the prediction target.
- **Domain over generic.** Do not default to generic GLMs when the domain has
  mechanistic structure — use the domain's standard response model.

## Analysis purpose

Determine the goal type from the user's prompt and the data's nature:

- **Descriptive** (default for minimal prompts). Characterize the
  data-generating process with honest uncertainty.
- **Inferential.** Estimate a specific causal or conditional effect. Prioritize
  unconfounded estimation of target parameters; do not add flexible structures
  that absorb the estimand's signal.
- **Predictive.** Maximize out-of-sample performance; parameter
  interpretability is secondary.

Define 1-3 **key quantities of interest** and state what **adequate** means —
when is the model good enough to stop?

## Validation strategy

Choose the hold-out scheme based on the data's dependence structure:

| Data structure | Standard LOO valid? | Recommended hold-out |
|---|---|---|
| i.i.d. | Yes | Standard observation-level LOO |
| Grouped (predicting new obs in known groups) | Yes | Standard LOO |
| Grouped (generalizing to new groups) | No | Leave-out-group CV (entire groups out) |
| Temporal | No (overstates predictive performance) | Leave-future-out (LFO-CV) or rolling-origin |

State the chosen scheme up front. Downstream critique and selection trust this
declaration when deciding whether ELPD rankings are interpretable.

## Domain context

Identify the scientific domain and its canonical modeling frameworks.
Different domains have different standard response models, parameterizations,
and baseline components — e.g., pharmacokinetics defaults to ODE compartmental
models, psychophysics to psychometric functions, epidemiology to SIR/SEIR.
Use the domain's canonical framework as a starting point rather than defaulting
to a generic GLM.

If no strong domain conventions are recognizable from training or the EDA,
state so explicitly and proceed with empirical-first design.

## Structural questions

Extract 2-3 **contrastive** structural questions — each pits two explanations
of the data-generating process against each other, framed in terms of the key
quantities of interest and domain theory where possible.

Good question shape:
- "Does response variance differ by group (hierarchical) or is it pooled?"
- "Does the temporal trend follow domain X's mechanistic ODE, or is a flexible
  spline sufficient?"
- "Is the apparent zero-inflation a true two-stage process, or thin-tailed
  observation noise?"

Bad question shape:
- "What model fits best?" (not contrastive)
- "Should we use Student-t?" (just a likelihood swap, not structural)

Each question should be answerable by comparing models with different
structural commitments.

## Output

The analysis design produces four sections — analysis purpose (with key
quantities of interest), validation strategy, domain context, structural
questions — that downstream model specification depends on. Be precise; vague
analysis design propagates as vague modeling.
