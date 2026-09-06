# Bayesian Workflow Claude Code Plugin

This plugin provides a workflow that runs in Claude Code.
The workflow is built to be run end to end, but we also provide a set of skills.

Currently the plugin is configured to use Stan and ArviZ.

When run end to end, it has four phases:

1. Explore: check data missingness, run exploratory data analysis to discover patterns
2. Design: given the patterns, plan what models should be explored
3. Develop: per experiment, the stages are:
   1. prior predictive check: simulate data from the priors to check that they are reasonable and how informative they are
   2. fake-data check: simulate data from reasonable parameter values, then fit the model to the simulated data to check that it is identifiable
   3. fit: run HMC and check the sampler diagnostics to make sure the sampling is valid
   4. posterior predictive check
   5. model comparison and critique
4. Report

## Install

```
/plugin marketplace add sunxd3/bayesian-statistician-plugin
/plugin install bayesian-workflow@sunxd3-plugins
```

Needs [`uv`](https://docs.astral.sh/uv/) and a C++ toolchain for CmdStan.

## Use

```
/bayesian-workflow:setup                  # once per project: Python env + CmdStan
/bayesian-workflow:run <data file>
/bayesian-workflow:explore <data file>    # exploratory data analysis only
```
