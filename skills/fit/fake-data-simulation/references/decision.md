# PASS / FAIL Criteria and Failure Modes

## PASS

All of:

- Posterior means/medians approximately recover the true values (within a few standard errors)
- Posterior credible intervals contain the true values
- MCMC converges reliably (R-hat < 1.01, ESS adequate, no divergences or low BFMI)
- No wild parameter correlations or non-identifiability signals
- Computation completes without numerical errors

## FAIL

Any of, plus a triage hypothesis:

| Symptom | Likely cause | Action |
|---|---|---|
| Posteriors systematically miss true values | Model misspecification, simulator/model divergence | Re-check that `simulator.stan` is a line-by-line mirror of `model.stan`; check the prior/likelihood for the parameter |
| Parameters non-identifiable (wild posterior, strong correlations) | Reparameterization needed, redundant parameters, or insufficient data | Reparameterize, simplify, or accept that the data cannot distinguish those parameters |
| Convergence failures (divergences, low BFMI, R-hat > 1.1) | Computational geometry — funnels, multimodality, scale issues | Reparameterize (centered ↔ non-centered), tighten priors, increase `adapt_delta` |
| Numerical errors (initialization, overflow, NaN) | Fundamental model problems — improper priors, log/exp overflows, missing constraints | Fix the Stan program; do not proceed to real data |

**If recovery fails, do not proceed to fit real data.** Document the failure mode in the recovery report and hand back to model design / refinement.

## Sensitivity

A FAIL on a non-essential parameter (e.g., a nuisance scale that's known to be weakly identified) may be acceptable if the parameters of interest pass. Note this explicitly in the report — do not silently downgrade FAIL to PASS.

A PASS for a single-draw fake-data check is necessary but not sufficient: it tells you the model can recover ONE truth in the parameter space, not that it's well-calibrated across the prior. Escalate to SBC (`references/sbc.md`) when calibration matters.
