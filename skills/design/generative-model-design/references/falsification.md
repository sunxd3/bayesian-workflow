# Falsification Criteria

State what would **break** this model:

- **Targeted PPC.** Name one specific data feature the model *must* reproduce to be valid (e.g., "must capture the zero rate," "must reproduce lag-1 autocorrelation"). See `bayesian-model-diagnostics` for LOO-PIT shape-to-diagnosis mappings.
- **ELPD resolution.** How does this compare to the baseline? For i.i.d. data, see `bayesian-model-selection` for standard thresholds. For dependent data, specify the appropriate comparison method (rolling-origin, LFO-CV) as flagged in the observation-unit decision.
- **Parameter resolution.** Which parameter's credible interval answers the structural question?
