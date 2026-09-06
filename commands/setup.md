---
description: Bootstrap the Python environment for the Bayesian workflow — creates `pyproject.toml`, syncs dependencies with `uv`, and installs CmdStan.
allowed-tools: Bash, Read, Write, Edit
---

Bootstrap the Python environment for the Bayesian workflow. Run once per project, from the working directory.

**Always use `uv`.** Never use bare `python`/`pip`, never create a virtual environment by hand.

## Idempotency check

If `./pyproject.toml` already exists and `uv run python -c "import cmdstanpy; print(cmdstanpy.cmdstan_path())"` succeeds, the environment is set up — report this and stop.

## Steps

1. Create `pyproject.toml` in the project root. If one already exists, merge the `dependencies` list into it rather than overwriting:

   ```toml
   [project]
   name = "bayesian-analysis"
   version = "0.0.0"
   requires-python = ">=3.11"
   dependencies = [
       "arviz>=0.17.0,<1.0.0",
       "cmdstanpy>=1.2.0",
       "numpy>=1.26.0",
       "pandas>=2.0.0",
       "pyarrow>=15.0.0",
       "matplotlib>=3.8.0",
       "scipy>=1.11.0",
       "seaborn>=0.13.0",
   ]
   ```

2. Sync the environment and install the CmdStan toolchain (CmdStanPy compiles Stan models against it):

   ```bash
   uv sync
   uv run python -m cmdstanpy.install_cmdstan
   ```

After setup, see the `python-environment` skill for script conventions and the `fit-pipeline` skill for the runnable Stan execution recipes and the artifact contract.
