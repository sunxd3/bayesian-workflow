# Skills

Methodology and reference material that agents receive at spawn time. Each
skill is `<group>/<name>/SKILL.md` plus optional `references/` files. Groups
follow the workflow's phases; they exist for people reading the repo, not for
the loader.

## How the loader treats this folder

- A skill is discovered only at `<root>/<name>/SKILL.md`, exactly one level
  below a skill root. The roots are `skills/` itself plus the group directories
  listed under `skills` in `.claude-plugin/plugin.json`. A new group must be
  added there; a `SKILL.md` two levels below a root is silently ignored.
- Names are flat: `bayesian-workflow:<name>`, no group prefix. Agents name
  skills in their `skills:` frontmatter, so moving a skill between groups
  changes nothing for them.
- At session start only each skill's `description` is in context. The full
  `SKILL.md` body is injected into every agent that lists the skill, so body
  length is paid on every spawn. `references/` files are never loaded
  automatically; they cost nothing until an agent reads them. Keep bodies
  short and push detail into references.
- Plain `.md` files at this level and inside skill folders (this file, for
  instance) are not components. That is not true of `agents/` and
  `commands/`, where every `.md` file becomes an agent or a command.
- `claude --plugin-dir . plugin details bayesian-workflow` prints what was
  discovered and an estimated token cost per skill. Run it after adding or
  moving anything.

## Groups

| group | skill | what it holds | preloaded by |
|---|---|---|---|
| core | validation-protocol | entry/exit contract for every agent: input checks, completed-work short-circuit, structured returns with audited numeric fields, `status.json` | all 18 agents |
| core | artifact-guidelines | format conventions for reports, logs, figures; `references/html-report.md`, `markdown-report.md` | 17 agents (all but data-profiler) |
| core | python-environment | uv usage, dependencies, script conventions, where the Stan recipes live | 12 agents |
| core | orchestration | the phase driver: runs the four workflow scripts, holds the two user gates, persists the ledgers, keeps the lab notebook | `/bayesian-workflow:run` only |
| explore | eda | EDA procedures (`references/process/`) and a diagnostic test library indexed by data shape (`references/tests/`) | eda-analyst, synthesist |
| design | analysis-design | analysis purpose, validation strategy, domain context, structural questions | analysis-planner, model-designer, strategist, synthesist |
| design | generative-model-design | complete generative specs, resolution sequences, cross-cutting modeling principles; eight references | analysis-planner, model-designer, model-refiner, prior-predictive-checker |
| fit | stan | Stan program structure, parameterization, predictive blocks, pitfalls; `references/ode.md`, `horseshoe.md` | model-designer, model-fitter, model-refiner, prior-predictive-checker, fake-data-checker |
| fit | fit-pipeline | the artifact contract a fit must produce, with three runnable scripts under `references/` (posterior fit, prior predictive, fake-data simulate and check); exercised by `tests/` | model-fitter, prior-predictive-checker, fake-data-checker |
| fit | inferencedata-handling | building ArviZ InferenceData from CmdStanPy | model-fitter, prior-predictive-checker, fake-data-checker, posterior-predictive-checker, model-selector, report-quant |
| fit | convergence-diagnostics | R-hat, ESS, divergence thresholds and HMC pathologies | model-fitter, fake-data-checker, critic |
| fit | fake-data-simulation | single-draw recovery versus SBC, and when each applies | fake-data-checker |
| evaluate | bayesian-model-diagnostics | LOO, PIT calibration, Pareto k for a single model | critic, model-refiner, posterior-predictive-checker |
| evaluate | model-critique | statistical, domain, and framework assessment; verdict structure | critic, strategist |
| evaluate | visual-predictive-checks | predictive check plots per Säilynoja et al. | posterior-predictive-checker, prior-predictive-checker |
| evaluate | bayesian-model-selection | comparing a model population: ELPD, selection versus stacking, metric validity | model-selector, strategist |
| report | report-writing | the quality bar the report pipeline writes to and the critic audits against; `references/final-report.md` | all five report agents |
