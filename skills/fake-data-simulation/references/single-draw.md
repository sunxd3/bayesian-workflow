# Single-Draw Fake-Data Simulation

One true-param set, simulate once, refit, check recovery. Cheap pre-fit gate. Catches obvious model bugs, Stan-program errors, and gross non-identifiability without the cost of full Simulation-Based Calibration.

## Procedure

### 1. Choose true parameter values

Pick **one** realistic set of parameter values (optionally a second set if the model has known identifiability risks). Informed by domain knowledge and EDA summaries. Avoid corner cases — the goal is "can the model recover *plausible* truth," not "can it recover edge cases."

### 2. Write `simulator.stan`

A generated-quantities-only Stan program at `<output_dir>/simulator.stan`. Takes the true parameter values as `data{}` input and generates synthetic `y_rep`. No `parameters` block, no `model` block.

The transformed-parameter computation and `_rng` calls **must be a line-by-line mirror** of the corresponding blocks in `model.stan`. Any divergence between simulator and model invalidates the check.

See the `stan` skill for full GQ-only patterns and pitfalls.

### 3. Generate synthetic data in Stan

Pass the true parameters as part of the `data` dict to `simulator.stan` and run
it in fixed-param mode. The Stan `_rng` calls produce one draw of synthetic
`y_rep`.

Run `fit-pipeline > references/fake_data.py simulate` with `--simulator`, the
inference `--data` (Stan JSON), and `--true` (the parameter values as a JSON
object). It merges the true parameters into the data, runs one `fixed_param`
draw, and writes `fake_data.json` (the data dict with the outcome replaced by
the draw) and `true_params.json`.

### 4. Fit `model.stan` to the synthetic data

Build a fresh `stan_data` dict with `y_obs` replaced by the simulated `y_rep`,
then run the standard posterior inference flow.

Run `fit-pipeline > references/posterior_fit.py` with
`--data <sim_dir>/fake_data.json` and `--out <sim_dir>/fit` (`--no-netcdf` is
fine here). Then `fake_data.py check --fit <sim_dir>/fit --true
<sim_dir>/true_params.json --out <sim_dir>` writes `recovery.json` with the
audited `coverage_90` and `max_bias_z` and a per-parameter breakdown.

### 5. Check recovery

Compare the fitted posterior to the truth:

- **Recovery.** Posterior means/medians within a few standard errors of the true values.
- **Coverage.** Posterior credible intervals contain the true values.
- **Convergence.** MCMC converges on the synthetic data without major issues (R-hat, ESS, divergences).
- **Identifiability.** No wild parameter uncertainty or correlations that prevent recovery.
- **Computational stability.** Fits complete without errors.

## Visualization

- **Scatter.** Posterior mean (y) vs true value (x), one point per parameter. Should track near the identity line with mild shrinkage.
- **Interval plot.** For each parameter, plot the posterior credible interval with the true value overlaid as a point or vertical line.

Look for:
- Catastrophic failures (flat line, no learning of the truth)
- Wild scatter (non-identifiability)
- Convergence issues visible in trace plots or pair plots

See `references/decision.md` for full PASS/FAIL criteria and failure-mode triage.
