# Bayesian Workflow

A Claude Code plugin for Bayesian modeling with Stan and ArviZ. It runs one
particular workflow, inspired by [Gelman et al., *Bayesian Workflow*
(2020)](https://arxiv.org/abs/2011.01808), in four phases:

1. **Explore**: profile the data, run parallel EDA analysts, synthesize one report.
2. **Design**: frame the analysis and turn its structural questions into a plan of model experiments.
3. **Develop**: per experiment, prior predictive check, fake-data recovery, fit, posterior predictive check, critique; a strategist steers rounds of refinement and a selector compares the final population.
4. **Report**: outline, fact sheet and figures, parallel section drafts, assembly, critic review loop.

Control flow lives in four Workflow scripts; judgment lives in subagents.

## Install

```
/plugin marketplace add sunxd3/bayesian-statistician-plugin
/plugin install bayesian-workflow@sunxd3-plugins
```

Needs [`uv`](https://docs.astral.sh/uv/) and a C++ toolchain for CmdStan.

## Use

```
/bayesian-workflow:setup                       # once per project: Python env + CmdStan
/bayesian-workflow:run data/sales.csv — model weekly sales and quantify the promotion effect
/bayesian-workflow:explore data/sales.csv      # Phase 1 only
```

The run pauses at two gates (goal after EDA, plan after design) and writes to
`eda/`, `design/`, `experiments/`, `report/`, and `log.md`.

## Layout

`skills/`, `workflows/`, and `tests/` each have a README. `agents/` and
`commands/` do not, because every `.md` file there loads as a component.
