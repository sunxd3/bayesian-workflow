# Skills

## Rules from Claude Code and folder organization

- Claude Code finds a skill at `<root>/<name>/SKILL.md`, one level below a skill root. The roots are `skills/` itself plus whatever groups are listed under `skills` in `.claude-plugin/plugin.json`, so a new group has to be added there.
- Skill names don't include the group — it's just `bayesian-workflow:<name>`. Agents refer to skills by name, so you can move a skill between groups without breaking anything.
- At session start, only each skill's `description` is in context. When an agent spawns, it gets the full body of every skill it lists, so long bodies cost tokens on every spawn. `references/` files are free until an agent actually reads one, so keep bodies short and move detail into references.
- A plain `.md` file here (like this one) is just a file. In `agents/` and `commands/` it's different — every `.md` there becomes an agent or a command.
- After adding or moving a skill, run `claude --plugin-dir . plugin details bayesian-workflow` to check what the loader found and what each skill costs in tokens.

## Groups

| group | skill | what it holds | preloaded by |
|---|---|---|---|
| core | validation-protocol | entry/exit contract for every agent: input checks, structured returns, `status.json` | all 18 agents |
| core | artifact-guidelines | report, log, and figure formats; HTML/markdown references | 17 agents |
| core | python-environment | uv usage, dependencies, script conventions | 12 agents |
| core | orchestration | the phase driver: runs the scripts, holds the user gates, keeps the ledgers | `/bayesian-workflow:run` only |
| explore | eda | EDA procedures and a diagnostic test library | eda-analyst, synthesist |
| design | analysis-design | analysis purpose, validation strategy, structural questions | analysis-planner, model-designer, strategist, synthesist |
| design | generative-model-design | generative specs and modeling principles; eight references | analysis-planner, model-designer, model-refiner, prior-predictive-checker |
| fit | stan | Stan structure, parameterization, pitfalls; ODE and horseshoe references | model-designer, model-fitter, model-refiner, prior/fake-data checkers |
| fit | fit-pipeline | the fit artifact contract plus three runnable scripts; exercised by `tests/` | model-fitter, prior/fake-data checkers |
| fit | inferencedata-handling | building ArviZ InferenceData from CmdStanPy | model-fitter, checkers, model-selector, report-quant |
| fit | convergence-diagnostics | R-hat, ESS, divergences, HMC pathologies | model-fitter, fake-data-checker, critic |
| fit | fake-data-simulation | single-draw recovery vs SBC, and when each applies | fake-data-checker |
| evaluate | bayesian-model-diagnostics | LOO, PIT calibration, Pareto k | critic, model-refiner, posterior-predictive-checker |
| evaluate | model-critique | statistical, domain, and framework assessment | critic, strategist |
| evaluate | visual-predictive-checks | predictive check plots per Säilynoja et al. | posterior/prior predictive checkers |
| evaluate | bayesian-model-selection | ELPD, selection vs stacking, metric validity | model-selector, strategist |
| report | report-writing | the quality bar for the report pipeline; `references/final-report.md` | all five report agents |
