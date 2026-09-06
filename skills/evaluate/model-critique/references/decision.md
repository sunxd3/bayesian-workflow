# Verdict & Report Structure

## Verdict categories

**VIABLE.** The model passes statistical validation, its scientific structure is appropriate for the domain, and the framework is defensible given the available data. Even viable models should be improved. Identify:

- **Weaknesses.** Specific patterns in residuals, calibration issues, missing structure.
- **Simplifications.** Could a simpler version work?
- **Extensions.** What structure might improve fit?
- **Domain suggestions.** Domain-motivated improvements (prioritized).
- **New questions.** If the critique reveals something genuinely surprising (unexpected residual structure, a parameter collapsing to zero, a domain mechanism not anticipated by the original structural questions), flag it as a potential new structural question for the orchestrator to explore.

Base suggestions on diagnostic evidence, not arbitrary elaboration. When identifying weaknesses, cite the specific summary statistic or data feature. Each suggested extension should nest the current model.

For inferential or descriptive goals (see `analysis-design > Analysis purpose`), a model with slightly worse PPC calibration may still be preferred if it yields more precise and interpretable estimates of the target estimand. Do not reject a model solely for marginal PPC issues if the core generative structure is sound and the estimand is well-identified.

**CONCERNS.** The model is statistically viable but has domain or framework issues that weaken its scientific validity. List concerns in priority order using the template below.

**BROKEN.** At least one of:

- Persistent computational failures (divergences, non-convergence).
- Fundamental misspecification (cannot reproduce basic data features).
- Unresolvable prior-data conflict.
- Parameters non-identifiable.

Report specific failure modes and whether fixable or needs a fundamentally different approach.

## Report templates

Begin every critique report with one of:

- `DECISION: VIABLE`
- `DECISION: CONCERNS`
- `DECISION: BROKEN`

### CONCERNS template

```
DECISION: CONCERNS

DOMAIN: [identified domain and subfield]

PRIORITY 1 — [Component name]
What the model does: [specific description from the Stan code]
What domain practice expects: [the standard approach and why]
Scientific consequence of the gap: [what goes wrong interpretively, not statistically]
Suggested fix: [concrete modification to the Stan model]

PRIORITY 2 — [Component name]
...

FRAMEWORK CONCERNS (if any):
[Flag if the model ignores available data that could support a better framework.
This is the highest-priority category — a framework mismatch matters more than
any within-framework refinement.]

DOMAIN-SPECIFIC VALIDATION:
[If applicable, suggest a domain-meaningful PPC or diagnostic that standard
statistical checks would miss]

NEW QUESTIONS (if any):
[Genuinely surprising findings that warrant new structural questions,
not just refinements of the current model]
```

## Priority discipline

Distinguish critical from aspirational. Priority 1 concerns should be things that make the model's scientific conclusions unreliable. Lower-priority concerns can be "would improve interpretability" or "standard practice but not essential."

Explain *why* a domain convention exists, not just that it exists. The model-refiner needs to understand the scientific rationale to implement the change correctly.
