# Modeling Handoff

This is the primary handoff from EDA to model designers. Its purpose is not just to describe data properties but to identify the structural questions that model design must resolve.

## Variance decomposition

Quantify how target variance distributes across structural levels. The goal is to show where the signal lives so designers know what structure matters most.

- For grouped/panel data: compute between-group vs. within-group variance at each natural grouping level (e.g., between-day vs. within-day, between-site vs. within-site)
- For time series: decompose into trend, seasonal/cyclical, and residual components at the most informative scales
- Report the approximate fraction of variance each level explains. This directly tells designers where added model complexity has the most potential payoff and where it will be wasted.

## Residual analysis after minimal model

Fit the simplest defensible model for the target (e.g., group means, fixed effects for the strongest predictor). Examine the residuals for:

- Autocorrelation structure (ACF/PACF of residuals)
- Heteroskedasticity (residual variance across groups, time, or predicted values)
- Distributional departures (heavy tails, skewness, zero-inflation in residuals)
- Remaining predictable structure (do other covariates predict residuals?)

This is the critical bridge between "what patterns exist" and "what a model needs beyond the obvious." The residual structure after minimal controls is what designers must explain.

## Competing structural hypotheses

State 2-3 competing stories about the data-generating process. Each story should:

- Describe a different structural mechanism (not just different parameter values on the same model)
- Make at least one distinct prediction that can be tested by comparing model fits
- Be grounded in specific EDA findings — cite the evidence for and against each story

Example: "Story A: traffic is deterministic by hour and day-type with i.i.d. noise (evidence: hour×weekend explains 93% of variance). Story B: there are day-level latent states that shift the baseline (evidence: residual lag-1 autocorrelation is 0.83 after temporal controls, and between-day variance is X% of total). Story C: weather disrupts traffic in real-time (evidence against: weather explains <2% after temporal controls; evidence for: conditional on rush hours, heavy rain reduces volume by Y%)."

These stories become the candidate structural questions in `analysis-design > Structural questions`, which the orchestrator finalizes and hands to model designers.

## Dependence classification

Explicitly classify the primary data structure. This determines the validation strategy downstream — getting it wrong invalidates all model comparisons.

- **i.i.d.** Observations are exchangeable given covariates. Standard observation-level LOO is valid.
- **Grouped / panel.** Observations are nested within entities (subjects, sites, stores). State the grouping variable(s), number of groups, and observations per group. Standard LOO overstates performance by interpolating within known groups.
- **Temporal.** Observations have a time ordering that carries information (autocorrelation, trends). State the time resolution and whether gaps exist.
- **Spatial.** Observations have spatial adjacency structure.
- **Combinations.** E.g., "grouped + temporal" (panel data with time ordering within each group).

State this classification at the top of the Dependence Classification section, before any nuance. This is a critical handoff to the orchestrator and feeds `analysis-design > Validation strategy`.

## Likelihood and scale guidance

Map observed target properties to candidate likelihoods:
- Continuous symmetric → Normal or Student-t (heavy tails)
- Positive skewed → Gamma, Lognormal
- Counts → Poisson or Negative Binomial (overdispersion)
- Counts with excess zeros → Zero-inflated or hurdle
- Proportions in (0,1) → Beta
- Ordered categories → Ordinal
- Values at boundaries → Truncated or censored

Report typical magnitude of target and key predictors. Note whether standardization, centering, or log transforms would help for setting priors.

## Modeling-ready recommendations

- **Encoding choices.** For each categorical/indicator variable, recommend a specific encoding (dummy, effect, hierarchical partial pooling, etc.) and justify why.
- **Pooling strategy.** For variables with rare levels, recommend whether to pool rare levels into an "other" category, use a hierarchical prior, or drop them. State the threshold and rationale.
- **Candidate interactions.** Based on observed conditional patterns (e.g., an effect that varies across subgroups or time periods), list specific interactions worth testing in the model.
- **Variables to exclude or transform.** Flag any variables that are redundant, near-collinear, or need transformation before entering the model, with specific recommendations.
