---
name: fit-pipeline
description: How a Stan fit becomes the canonical artifacts the workflow audits — sampling defaults, InferenceData construction, convergence and LOO numbers, the file contract — with three runnable reference scripts (posterior fit, prior predictive, fake-data simulation + recovery) to copy and adapt.
user-invocable: false
---

# Fit Pipeline

Every experiment's stages must leave behind the same files with the same
layouts: `develop.js` audits them, the selector ranks on them, and report-quant
sources numbers from them. This skill is that contract plus reference code that
honors it. **There is no library to import.** Copy the script you need into the
stage directory, adapt the marked section, run it with `uv run` from the
project root, and keep it — `*.py` is an artifact.

## Reference scripts

| Script | Used by | Writes |
|---|---|---|
| `references/posterior_fit.py` | model-fitter (probe and full run); recovery fits | `summary.json`, `diagnostics.json`, `loo.json`, `thinned_draws.npz`, `posterior.nc` |
| `references/prior_predictive.py` | prior-predictive-checker | `prior_predictive.nc`; `prior_check.json` when `--bounds` given |
| `references/fake_data.py` | fake-data-checker (`simulate`, then `check` after a recovery fit) | `fake_data.json`, `true_params.json`, `recovery.json` |

CLI usage is at the top of each file. `posterior_fit.py` is the only one with a
part you are expected to rewrite — `build_stan_data()`, which maps the dispatched
dataset onto the model's `data {}` block. Stan-JSON input passes through
unchanged, which is how the recovery fit consumes `fake_data.json`.

## Artifact contract

`posterior_fit.py` writes, under the stage directory:

| File | Layout |
|---|---|
| `summary.json` | `model_name`; `param_summary` (`az.summary` columns `mean`, `sd`, `hdi_3%`, `hdi_97%`, `ess_bulk`, `ess_tail`, `r_hat`, keyed column → parameter); `convergence`; `diagnostics`; `loo` (absent without `log_lik`); `artifacts` (absolute path of every file of the save, itself included); `warnings` |
| `diagnostics.json` | `num_divergences`, `max_treedepth_exceeded`, `ebfmi_warnings` — CmdStanPy's own counters plus ArviZ E-BFMI |
| `loo.json` | `elpd_loo`, `se`, `p_loo`, `k_good` (k < 0.5), `k_ok` (< 0.7), `k_bad` (< 1), `k_very_bad` (≥ 1) |
| `thinned_draws.npz` | 200 parameter-only draws per variable, sample axis first — never `y_rep` or `log_lik` |
| `posterior.nc` | InferenceData with `posterior`, `posterior_predictive` (`y_rep`), `log_likelihood` (`log_lik`), `sample_stats`, `observed_data` (`y`) |

`convergence` is `{max_rhat, min_ess_bulk, min_ess_tail, n_divergent, converged}`
where `converged` applies the thresholds below. `prior_check.json` carries
`extreme_draw_pct` against the assigned bounds; `recovery.json` carries
`coverage_90` and `max_bias_z` with a per-parameter breakdown.

**Audited fields** (`validation-protocol > Audited numeric fields`) map onto these
files directly: `rhat_max` ← `convergence.max_rhat`; `ess_min` ←
`min(min_ess_bulk, min_ess_tail)`; `divergences` ← `n_divergent`; `score`,
`score_se` ← `loo.elpd_loo`, `loo.se` when the plan's metric is observation-level
LOO; `pareto_k_bad_pct` ← `100 · (k_bad + k_very_bad) / N`; `extreme_draw_pct`,
`coverage_90`, `max_bias_z` ← the prior and recovery JSON files.

## Rules the scripts encode — keep them when you adapt

- **Quiet sampling.** `show_progress=False, show_console=False`, always;
  leave `refresh` at its default (CmdStanPy ≥ 1.3 rejects `refresh=0`).
  Progress output floods the agent transcript and can crash the session.
- **NUTS needs warmup > 0.** GQ-only programs run with `fixed_param=True,
  iter_warmup=0, adapt_engaged=False` and **no `adapt_delta`** — CmdStanPy
  rejects any `adapt_*` setting once adaptation is off.
- **Never bare `az.from_cmdstanpy(fit)`.** Name `posterior_predictive`,
  `log_likelihood`, and `observed_data` explicitly, and only pass variables the
  program declares (`fit.metadata.stan_vars`), or conversion crashes.
- **Convergence from `az.summary`, not `fit.diagnose()`**, which OOMs above
  ~10K observations. Thresholds: R̂ < 1.01, ESS ≥ 400 bulk and tail, 0
  divergences, E-BFMI ≥ 0.3 (ref: `convergence-diagnostics`).
- **Delete the CmdStan CSVs** once draws are in memory. They are 5–500 MB per
  chain and nothing in them is lost after conversion.
- **JSON through `NumpyEncoder`.** numpy scalars are not serializable.
- **Subsample N > 2000** before prior simulation (ref: `stan > GQ-only pitfalls`).
- **Non-LOO ranking metrics** (grouped, leave-future-out) are computed in your
  own script from `posterior.nc`'s `log_likelihood`; mirror `loo()` in
  `posterior_fit.py` for the observation-level shape and write
  `ranking_score.json` as the model-fitter agent describes.

## Tests

The reference scripts are executed in CI against real CmdStan (repository
`tests/`): the artifact contract, parameter recovery, divergence flagging, LOO
ranking, the prior and recovery numbers, and each CLI are asserted. If you change
a layout here, change the tests.
