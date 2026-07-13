# Bayesian Statistician Plugin

A Claude Code plugin for end-to-end Bayesian statistical modeling with Stan and
ArviZ. It packages an orchestrator skill, eleven specialized subagents, and a
library of modeling skills that together run a full Bayesian workflow:
**EDA → model design → fitting → validation → reporting**.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) — used for all Python execution.
- A C++ toolchain — CmdStanPy compiles Stan models against CmdStan. The
  `/bayesian-workflow:setup` command installs CmdStan via
  `python -m cmdstanpy.install_cmdstan`.

## Install

**From the marketplace** (the repository is also its own marketplace):

```
/plugin marketplace add sunxd3/bayesian-statistician-plugin
/plugin install bayesian-workflow@sunxd3-plugins
```

**For local development**, clone the repository and load it with `--plugin-dir`:

```bash
git clone https://github.com/sunxd3/bayesian-statistician-plugin.git
claude --plugin-dir ./bayesian-statistician-plugin
```

Run `/reload-plugins` after editing a locally loaded plugin.

## Usage

Bootstrap the Python environment once per project (optional — the orchestrator
will do it on first run if you skip):

```
> /bayesian-workflow:setup
```

Then run the workflow with your data path or analysis goal:

```
> /bayesian-workflow:run Analyze data/sales.csv and build a Bayesian model
```

The orchestrator drives the workflow through four phases, delegating to
subagents and writing all results into a predictable folder structure
(`eda/`, `design/`, `experiments/`, `final_report.html`, `log.md`).

Individual phases can also be run standalone — for example, EDA alone:

```
> /bayesian-workflow:eda data/sales.csv
```

## What's inside

**Orchestration skill** — `orchestration` holds the full workflow protocol
(phases, validation-round semantics, canonical file structure, dispatch logic).
Loaded by the `/bayesian-workflow:run` command.

**Bundled workflow script** — `workflows/validate-experiments.js` runs one
round of the Phase 3 validation pipeline as a deterministic Workflow-tool
script: stage sequencing, the FIX-refine budget, MCMC concurrency throttling,
and verdict-vs-numbers cross-checks are enforced in code, while the
orchestrator keeps every judgment call (critique-driven exploration, new
structural questions, model selection) between rounds. On harnesses without
the Workflow tool, the orchestration skill falls back to a manual task-pool
protocol. Stage agents write a machine-readable `status.json` completion
record, so interrupted rounds resume cheaply — completed stages are verified
in seconds instead of re-fitted.

**Subagents (11)** — `eda-analyst`, `analysis-planner`, `model-designer`,
`prior-predictive-checker`, `fake-data-checker`, `model-fitter`,
`posterior-predictive-checker`, `critique`, `model-refiner`, `model-selector`,
`report-writer`.

**Commands**:
- `/bayesian-workflow:setup` — bootstraps the Python environment (copies
  `shared_utils`, creates `pyproject.toml`, runs `uv sync` and
  `cmdstanpy.install_cmdstan`).
- `/bayesian-workflow:run [data-path-or-analysis-goal]` — end-to-end pipeline.
  Loads the `orchestration` skill and drives all four phases.
- `/bayesian-workflow:eda <data_path> [output_dir] [--focus=<area>]` — run
  EDA on a dataset standalone, without the full workflow pipeline. Wraps
  the `eda-analyst` subagent.

**Modeling skills (13)** — `validation-protocol`, `python-environment`,
`stan` (with `references/ode.md` and `references/horseshoe.md` for ODE-based
dynamics and sparse regression), `generative-model-design` (lean SKILL.md
index + `references/` for spec sections, design principles, and the
resolution-sequence pattern), `fake-data-simulation` (with
`references/single-draw.md`, `references/sbc.md`, `references/decision.md`),
`convergence-diagnostics`, `inferencedata-handling`, `visual-predictive-checks`,
`bayesian-model-diagnostics`, `bayesian-model-selection`, `model-critique`
(SKILL.md index + `references/` for statistical, domain, and framework
assessment plus verdict templates), `eda` (with `references/process/` for EDA
procedures and `references/tests/` for a diagnostic test library by data
shape), `artifact-guidelines` (with `references/html-report.md`,
`references/markdown-report.md`, and `references/final-report.md` for the
Phase-4 narrative structure). Subagents load the skills relevant to their
role; skills are not user-invocable directly — use the commands above.

**Bundled library** — `shared_utils`, a Python package with a fit-and-summarize
pipeline, convergence diagnostics, LOO, and ArviZ helpers. The setup command
copies it into the working project as a path dependency.

## How the workflow runs

1. **Data understanding** (`eda/`) — `eda-analyst` explores the data and
   surfaces competing structural hypotheses about the data-generating process.
2. **Model design** (`design/`) — `analysis-planner` frames the analysis
   (purpose, validation, domain, structural questions) and the shared baseline;
   parallel `model-designer` instances then turn the structural questions into
   an experiment plan.
3. **Model development** (`experiments/`) — each experiment flows through
   `prior-predictive-checker → fake-data-checker → model-fitter →
   posterior-predictive-checker → critique`, with `model-refiner` and
   `model-selector` driving iteration until questions are resolved.
4. **Reporting** (`final_report.html`) — `report-writer` produces a report
   organized around what was learned about the data-generating process.

## Optional settings

Add to your `.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR": "1"
  }
}
```

- `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` — resets the working directory to
  the project root after each bash command, which keeps the canonical folder
  structure consistent across subagents.

The subagents inherit your main session model, so running Claude Code on an
Opus model gives the whole workflow Opus-level quality.

## License

MIT — see [LICENSE](LICENSE).
