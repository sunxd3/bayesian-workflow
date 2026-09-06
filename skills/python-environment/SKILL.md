---
name: python-environment
description: Reference for the Bayesian workflow Python environment — `shared_utils` API and script structure conventions. Assumes the environment has been bootstrapped via `/bayesian-workflow:setup`.
user-invocable: false
---

# Python Environment

**Always use `uv`.** Never use bare `python`/`pip`, never search for a Python interpreter, never create a virtual environment by hand. `uv run` resolves the environment from the nearest `pyproject.toml` up the directory tree.

If `./shared_utils/` and `pyproject.toml` are not yet present, the environment has not been bootstrapped — run `/bayesian-workflow:setup`.

After setup, run every script from the project root:

```bash
uv run python experiments/experiment_X/fit/run_fit.py
```

The environment provides `arviz`, `cmdstanpy`, `numpy`, `pandas`, `matplotlib`, `scipy`, `seaborn`, and `shared_utils`. `scikit-learn`, `statsmodels`, and deep-learning frameworks are intentionally excluded — the workflow is Stan-based (see `orchestration > Technical Stack`). Add a dependency to `pyproject.toml` only if a model genuinely requires it.

## Shared Utilities

`shared_utils` is the bundled helper library. Import directly — do not modify it:

```python
# Preferred: fit-and-summarize pipeline (auto-cleans CSVs, returns structured results)
from shared_utils import fit_and_summarize, FitResult

# Stan/CmdStanPy utilities (lower-level, use when you need manual control)
from shared_utils import compile_model, fit_model

# Diagnostics
from shared_utils import check_convergence, compute_loo, get_divergences
from shared_utils import ConvergenceResult, LOOResult

# Prior predictive (ArviZ conversion for GQ-only Stan programs)
from shared_utils import to_arviz_prior

# JSON I/O (auto mkdir, handles numpy types) and CSV cleanup
from shared_utils import write_json, NumpyEncoder, cleanup_csv_files

# Path utilities
from shared_utils import ensure_dir, resolve_path, project_root
```

**Key features:**
- `fit_and_summarize(model, stan_data, model_name=..., save_dir=...)` — preferred workflow for posterior fitting. Fits the model, computes summary/diagnostics/LOO, returns a `FitResult`. The InferenceData gets an `observed_data` group from `stan_data["y"]` automatically; pass `observed_data={...}` when the outcome has another name, and `coords=`/`dims=` to label dimensions (e.g. `dims={"y_rep": ["obs"], "log_lik": ["obs"]}`). CSVs are always cleaned up after extraction (5-500 MB/chain, nothing lost). Pass `save_netcdf=True` for main data fits — the `.nc` (5-50 MB) preserves `y_rep` and `log_lik` draws needed for PPC, LOO-PIT, and `az.compare()`. Skip `.nc` for probes and recovery runs.
- `FitResult` fields: `param_summary` (DataFrame), `convergence` (ConvergenceResult), `loo` (LOOResult or None), `thinned_draws` (dict of parameter-only arrays — NO `y_rep` or `log_lik`), `diagnostics` (dict), `warnings` (list). Call `result.save(dir)` to write JSON artifacts.
- `to_arviz_prior(fit, prior_predictive=["y_rep"], observed_data=...)` — converts a `fixed_param` fit of a GQ-only `prior_model.stan` to ArviZ InferenceData with `prior` and `prior_predictive` groups. See the `stan` skill for the full workflow.
- `fit_model(model, data, iter_warmup=1000, iter_sampling=1000, ...)` — lower-level, matches the CmdStanPy API. Use when you need the raw `CmdStanMCMC` object. Validates `iter_warmup > 0` when `adapt_engaged=True`, and that `data` is a dict.
- `write_json(path, data)` — write JSON to disk (auto-creates parent directories, uses `NumpyEncoder` for numpy types, indent=2). Prefer over raw `json.dump()` + `open()`.
- `NumpyEncoder` handles `numpy.bool_` and other numpy scalars for JSON serialization (used internally by `write_json`).

For the full API, read the package source at `./shared_utils/src/shared_utils/` in your project (copied there by `/bayesian-workflow:setup`).

## Script Structure

Write small, focused scripts — not monolithic files. Separate concerns:

```
experiments/experiment_X/
  fit/
    run_fit.py        # Main entry point
    diagnostics.py    # Convergence checks
    plots.py          # Visualization
  model.stan          # Stan model
```

Each script should:
- Do one thing well
- Be runnable via `uv run python script.py` from the project root
- Import shared logic from `shared_utils` instead of rewriting common patterns
- Use paths relative to the project root and write outputs into the canonical folder structure

**Common imports pattern:**
```python
#!/usr/bin/env python
"""Model fitting script."""
from pathlib import Path

from shared_utils import compile_model, fit_and_summarize

# Script logic here...
```

## Common workflows

Three canonical Stan-execution recipes via `shared_utils`. The Stan-language
side of the GQ-only programs referenced below lives in
`stan > Generated-Quantities-Only Programs`.

### Posterior inference (main path)

`fit_and_summarize` handles compile + sample + diagnostics + LOO + InferenceData
+ CSV cleanup in one call:

```python
from shared_utils import compile_model, fit_and_summarize

model = compile_model(experiment_dir / "model.stan")
result = fit_and_summarize(model, stan_data, model_name="exp_1",
                           save_dir=experiment_dir / "fit",
                           save_netcdf=True)
```

Pass `save_netcdf=True` for main data fits — the `.nc` preserves `y_rep` and
`log_lik` draws needed for PPC, LOO-PIT, and `az.compare()`. Skip for probes
and recovery runs.

### Prior predictive simulation

Compile a GQ-only `prior_model.stan` (see `stan > Pattern 1`), run with
`fixed_param=True`, convert via `to_arviz_prior`:

```python
from shared_utils import compile_model, fit_model, to_arviz_prior, cleanup_csv_files

prior_stan = compile_model(prior_dir / "prior_model.stan")
fit = fit_model(prior_stan, stan_data, fixed_param=True,
                iter_warmup=0, adapt_engaged=False)
idata = to_arviz_prior(fit, prior_predictive=["y_rep"],
                       observed_data={"y_obs": y_obs})
cleanup_csv_files(fit)
idata.to_netcdf(prior_dir / "prior_predictive.nc")
```

### Recovery / fake-data simulation

Compile a GQ-only `simulator.stan` (see `stan > Pattern 2`), pass true
parameters as `data`, extract `y_rep`:

```python
from shared_utils import compile_model, fit_model, cleanup_csv_files

simulator = compile_model(sim_dir / "simulator.stan")
sim_fit = fit_model(simulator, sim_data, fixed_param=True,
                    iter_warmup=0, adapt_engaged=False, iter_sampling=1)
y_synth = sim_fit.stan_variable("y_rep")
cleanup_csv_files(sim_fit)
```

Then fit `model.stan` to `y_synth` via `fit_and_summarize` (Posterior
inference, above).
