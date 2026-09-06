# Bayesian Workflow Claude Code Plugin

This plugin provides a workflow that runs in Claude Code.
The workflow is built to be run end to end, but we also provide a set of skills.

Currently the plugin is configured to use Stan and ArviZ.

When run end to end:

```
explore:  profile data → EDA analysts in parallel → synthesize one report
          -- user confirms the analysis goal --
design:   frame the analysis → one designer per structural question → dedup into an experiment plan
          -- user approves the plan --
develop:
  queue = experiments from the plan
  repeat while queue not empty (up to maxRounds):
    for each experiment in queue, in parallel:
      for stage in [prior predictive check, fake-data recovery, fit, posterior predictive check]:
        if stage FAILS and refine budget left: refiner writes a FIX variant, restart from the first stage
        if stage FAILS and budget spent:      skip the experiment
      critic → VIABLE | CONCERNS | BROKEN
    strategist → close questions, propose EXPLORE variants and new questions, or stop
    guards drop proposals that hit the plateau rule, explore budget, new-question slots, or experiment cap
    queue = EXPLORE variants (refiner) + experiments for new questions (designer)
  selector → ranking + coverage audit; if coverage gaps: design and run them once, select again
report:   outline → fact sheet + figures → sections in parallel → assemble
          repeat up to maxRevisions: critic → SHIP, or REVISE and the assembler revises
```

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
