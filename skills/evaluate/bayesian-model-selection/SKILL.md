---
name: bayesian-model-selection
description: Comparing model populations via ELPD, decision rules for selection vs stacking, and metric validity
user-invocable: false
---

# Bayesian Model Selection

Operational guide for comparing a population of validated Bayesian models. Covers `az.compare()` interpretation, ELPD-based decision rules, and when to stack vs pick a winner.

For single-model diagnostics (LOO-PIT, Pareto k), see `bayesian-model-diagnostics`. For MCMC sampler health, see `convergence-diagnostics`.

## Metric Validity Precondition

**Check BEFORE trusting `az.compare()` rankings:**

Do not trust ELPD rankings if the underlying LOO estimates were computed on dependent data (time-series, spatial, grouped) using standard `az.loo()`. Standard LOO assumes conditional independence — on dependent data it will overstate predictive performance and can flip model rankings. The per-model LOO-validity check lives in `bayesian-model-diagnostics > Data Structure Precondition`; the table below is the per-comparison check.

| Data structure | ELPD rankings valid? | Action |
|---|---|---|
| **i.i.d.** | Yes | Proceed with `az.compare()` |
| **Time-series** | Only if LOO used LFO-CV or rolling-origin | If standard LOO was used, demand rolling forecast metrics before declaring a winner |
| **Grouped** | Only if LOO matches prediction target | If generalizing to new groups, LOO must leave out entire groups |

### Implementation Note

For non-standard comparison methods (rolling CV, Diebold-Mariano, grouped LOO), write minimal custom code from `posterior.nc`'s `log_likelihood` rather than a full ad-hoc framework; mirror `loo()` in `fit-pipeline > references/posterior_fit.py` for the observation-level shape and write `ranking_score.json`.

## ELPD Comparison Rules

Run `az.compare()` on all validated models. This produces ELPD differences (Δ ELPD) with standard errors (SE) and stacking weights.

### Rule 1: Clear Winner (ΔELPD > 4×SE)

The top model's ELPD exceeds the second-best by more than 4× the SE of the difference.

- **Action.** Pick the winner. This is strong evidence of superior predictive performance.
- **Report.** "Model X is the clear winner (ΔELPD = 15.2, SE = 3.1). Recommend proceeding with Model X."

### Rule 2: Likely Winner (2×SE < ΔELPD < 4×SE)

Moderate evidence favoring the top model.

- **Action.** Prefer the top model, but note the uncertainty. If the runner-up is substantially simpler, consider it.
- **Report.** "Model X is favored (ΔELPD = 7.4, SE = 2.8) but the difference is moderate. Model Y is simpler and within striking distance."

### Rule 3: Indistinguishable (ΔELPD < 2×SE)

The top models overlap — the nominal ranking is not meaningful.

- **Sub-rule 3A (Occam's razor).** If one model is substantially simpler (fewer parameters, no unnecessary hierarchical structure), prefer it. Equal predictive performance with less complexity is better.
- **Sub-rule 3B (Stacking).** If `az.compare()` assigns significant weight (>0.15) to multiple models, they capture different aspects of the data. Recommend stacking.
- **Report.** "Models X and Y are statistically indistinguishable (ΔELPD = 1.2, SE = 2.4). Stacking weights: X = 0.6, Y = 0.4. Recommend stacked ensemble."

## Stacking Weight Interpretation

`az.compare()` produces stacking weights that minimize leave-one-out predictive loss. These are more useful than raw ELPD rankings when models are close.

| Weight pattern | Meaning | Action |
|---|---|---|
| One model has weight ≈ 1.0 | Single model dominates predictive performance | Pick the winner — stacking offers no benefit |
| 2-3 models share weight (e.g., 0.5/0.3/0.2) | Models capture complementary data features | Recommend stacked ensemble. Note which aspects each model captures |
| Weights spread thinly across many models | No model stands out; high model uncertainty | Consider whether models are all slight variants (→ simplify the candidate set) or structurally different (→ genuine ensemble value) |

Prefer stacking over Bayesian Model Averaging (BMA). BMA assumes one true model exists and is prior-sensitive. Stacking is robust to all models being wrong.

## Complexity Ceiling Detection

Track the improvement trajectory across model variants within a structural question:

| Pattern | Signal | Recommendation |
|---|---|---|
| Each variant improves ELPD over its predecessor | Question has room to grow | CONTINUE_QUESTION — try next suggested refinement |
| Recent variants show diminishing ELPD gains (<1 SE improvement) | Approaching ceiling | One more attempt, then SWITCH_QUESTION or declare ADEQUATE |
| Added complexity *hurts* ELPD (more parameters, worse score) | Overfitting or misspecified extension | Revert to simpler variant. SWITCH_QUESTION if baseline was already the best |
| All classes explored, best models identified, no variant improves | Modeling exhausted | EXHAUSTED — accept best model(s) and proceed to reporting |

## Pareto k in Population Context

Before comparing models, verify that each model's LOO is trustworthy:

- If a model has >5% of observations with Pareto k > 0.7, its ELPD is unreliable. Either refit with `az.reloo()` or exclude it from the comparison and note why.
- If *all* models have high Pareto k, the comparison is unreliable. Flag this and recommend k-fold CV for the entire population.

## Goal-Aware Selection

ELPD is the primary criterion only for predictive goals. The analysis purpose (see `analysis-design > Analysis purpose`) determines which criterion to weight:

- **Inferential goals.** Do not select a model solely because it has the best ELPD. A model with slightly worse ELPD but much better estimand contraction (more precise, interpretable target parameter) is preferred. Report contraction ratios for the key quantities of interest defined in the experiment plan.
- **Descriptive goals.** Weight PPC quality (variance decomposition, between-group vs within-group fit) alongside ELPD.

## Strategic Decisions

After comparison, recommend one of four directions for the orchestrator.

**CONTINUE_QUESTION.** Current structural question has room to improve.

- Recent variants improving on earlier ones.
- Diagnostics suggest specific extensions worth trying.
- Haven't reached complexity ceiling (no unidentifiable parameters, reasonable computation).
- **Action.** Provide specific suggestions for next variants.

**SWITCH_QUESTION.** Current question is resolved or plateaued.

- Recent extensions show no improvement on the primary comparison metric.
- Computational issues persist despite reparameterization.
- Clear ceiling reached (added complexity doesn't help).
- **Action.** Recommend moving focus to next structural question in the plan.

**ADEQUATE.** Population contains strong model(s).

- Top model(s) pass all validation cleanly.
- Attempted extensions show no improvement.
- Predictive performance acceptable for the task.
- For inferential goals, the target estimand posterior is precise enough to answer the analysis question (substantial contraction from prior, credible interval excludes practically meaningless values).
- **Action.** Can stop iteration, or continue other classes for comparison.

**EXHAUSTED.** All classes explored, no further improvement.

- All model classes from plan attempted.
- Best models identified, improvement plateaued.
- **Action.** Accept best and proceed to reporting. If multiple competitive models exist (ΔELPD < 2×SE), consider stacking.

## Coverage Audit

Required before finalizing an ADEQUATE or EXHAUSTED recommendation. Not needed for CONTINUE_QUESTION / SWITCH_QUESTION (iteration continues).

1. **Read the EDA report**, focusing on Modeling Implications and Competing Structural Hypotheses.
2. **Extract recommended approaches**: response scales, likelihood families, variance structures, or explicitly suggested specifications.
3. **Cross-check against validated experiments**: for each substantive EDA recommendation, was at least one model of that type validated? If a recommended approach was proposed but failed validation, that's not a gap — it was explored and found wanting.
4. **Check analysis purpose alignment**: did the top-ranked model achieve the analysis purpose (see `analysis-design > Analysis purpose`)? For inferential goals, verify sufficient estimand contraction. If the best model has good predictive performance but fails to isolate the target estimand precisely, that's a coverage gap.
5. **Identify gaps**: recommendations that were NOT addressed by validated models. Focus on **structurally different approaches**, not minor variations. Missing a different parameterization of variance is minor; missing an entire response scale (e.g., log vs original) is major. Distinguish primary recommendations ("use X") from alternatives ("consider Y") — gaps in primary recommendations are critical; gaps in alternatives are worth noting but not blocking.

Report as `COVERAGE: COMPLETE` (list how each substantive recommendation was addressed) or `COVERAGE: GAPS` (list unaddressed recommendations with specific structural questions that would fill them).

## Meta Considerations

If persistent issues across all classes (none reaching ADEQUATE):

- Data quality problems that modeling can't fix.
- Problem inherently more complex than available data supports.
- Need different data or methods entirely.

Surface these in the assessment rather than recommending more iteration.

## Output Checklist

When writing the population assessment report, include:

1. ELPD ranking table (all validated models, with ΔELPD ± SE). **Always report both the ELPD difference AND its standard error** — an ELPD difference without SE is uninterpretable. Also report p_loo and number of high Pareto k observations per model.
2. Stacking weights from `az.compare()`.
3. `az.plot_compare()` visualization.
4. Best model per structural question.
5. Improvement trajectory (did variants help?).
6. Strategic recommendation: CONTINUE_QUESTION / SWITCH_QUESTION / ADEQUATE / EXHAUSTED.
7. If ADEQUATE/EXHAUSTED: whether to pick a single winner or stack, with justification, plus a `COVERAGE:` section (COMPLETE / GAPS).
8. Any new structural questions discovered from model comparison (unexpected patterns, discriminating features).
9. `az.plot_elpd()` for pointwise ELPD differences — shows WHICH observations drive model comparison results, not just aggregate scores. Critical for diagnosing whether one model is uniformly better or only better on specific subgroups/outliers.
