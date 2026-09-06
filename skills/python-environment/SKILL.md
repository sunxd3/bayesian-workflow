---
name: python-environment
description: Reference for the Bayesian workflow Python environment — uv usage, dependencies, script structure conventions, and where the Stan execution recipes live. Assumes the environment has been bootstrapped via `/bayesian-workflow:setup`.
user-invocable: false
---

# Python Environment

**Always use `uv`.** Never use bare `python`/`pip`, never search for a Python interpreter, never create a virtual environment by hand. `uv run` resolves the environment from the nearest `pyproject.toml` up the directory tree.

If `pyproject.toml` is not present in the project root, the environment has not been bootstrapped — run `/bayesian-workflow:setup`.

After setup, run every script from the project root:

```bash
uv run python experiments/experiment_X/fit/posterior_fit.py --model ... --data ... --out ...
```

The environment provides `arviz`, `cmdstanpy`, `numpy`, `pandas`, `pyarrow`, `matplotlib`, `scipy`, and `seaborn`. `scikit-learn`, `statsmodels`, and deep-learning frameworks are intentionally excluded — the workflow is Stan-based (see `orchestration > Technical stack`). Add a dependency to `pyproject.toml` only if a model genuinely requires it.

## Stan execution

There is no shared library to import. The three canonical recipes — posterior inference, prior predictive simulation, fake-data simulation with a recovery check — are runnable reference scripts in the `fit-pipeline` skill (`references/posterior_fit.py`, `prior_predictive.py`, `fake_data.py`). Copy the one you need into the stage directory, adapt the marked section (for the posterior fit, `build_stan_data()`), run it with `uv run`, and keep it. The artifact contract those scripts honor is documented in the same skill; do not change file names or JSON layouts per experiment.

## Script structure

Write small, focused scripts — not monolithic files. Separate concerns:

```
experiments/experiment_X/
  fit/
    posterior_fit.py  # adapted copy of the fit-pipeline reference (entry point)
    plots.py          # diagnostic visualisation
  model.stan
```

Each script should:
- Do one thing well
- Be runnable via `uv run python script.py` from the project root
- Start from the `fit-pipeline` reference whenever it samples, converts, or writes fit artifacts, instead of re-deriving those steps
- Use paths relative to the project root and write outputs into the canonical folder structure

## Long runs

For fits likely to exceed a few minutes, launch detached and poll the log rather than blocking one foreground command:

```bash
nohup uv run python experiments/experiment_X/fit/posterior_fit.py ... > experiments/experiment_X/fit/run.log 2>&1 &
```

Progress output stays off inside the reference scripts (`show_progress=False`, `show_console=False`); never turn it on — it floods the transcript.
