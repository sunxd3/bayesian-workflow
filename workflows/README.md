# Workflows

Four scripts, one per phase. The Workflow tool runs them by path,
`scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/<phase>.js"`, from the
`orchestration` skill behind `/bayesian-workflow:run`, or from
`/bayesian-workflow:explore` for Phase 1 alone. The loader also registers
each `workflows/*.js` under its `meta.name` (`explore-data`,
`design-experiments`, `develop-models`, `write-report`), so they show up in
the session listing, but nothing in the plugin relies on that: every caller
passes a path. This file is not a component.

## The rule

Deterministic control flow is code, judgment is an agent, and the orchestrator
only holds the seams. A script owns caps, budgets, id assignment, retries,
audits of the numbers agents return, and the ledger. Every judgment call is
`agent()` with a JSON schema, dispatched to the plugin agent type
`bayesian-workflow:<name>`; scripts never parse prose. Each script's header
comment is the authoritative description of its `args` and return value.

| script | phase | key args | returns |
|---|---|---|---|
| `explore.js` | 1 | `projectDir`, `dataPath`, `goal?`, `edaDir?`, `maxAnalysts?`, `focusAreas?` | profile, per-analyst findings, synthesis |
| `design.js` | 2 | `projectDir`, `dataPath`, `goal`, `edaDir?`, `maxQuestions?`, `maxExperimentsPerQuestion?` | plan (ranking metric, bounds, baseline) and the seed ledger the orchestrator saves as `design/ledger.json` |
| `develop.js` | 3 | `projectDir`, `dataPath`, `questions`, `experiments`, `metric?`, `bounds?`, `limits?` | selection, stop reason, final ledger (`experiments/ledger.json`), counts |
| `report.js` | 4 | `projectDir`, `reportDir?`, `outputPath?`, artifact paths, `audience?`, `limits?`, `stopAfter?`, `outline?`, `facts?` | report path, outline, fact-sheet path, reviews, open issues |

## Agent roster

The 18 agents in `agents/` exist to be dispatched from here. Every `.md` in
that folder is loaded as an agent, which is why the roster lives in this file.

| script | agents, in dispatch order |
|---|---|
| `explore.js` | `data-profiler`; `eda-analyst` once per focus area, retried once; `synthesist` in mode `eda` |
| `design.js` | `analysis-planner`; `model-designer` once per structural question; `synthesist` in mode `design` |
| `develop.js` | gate stages per experiment: `prior-predictive-checker`, `fake-data-checker`, `model-fitter`, `posterior-predictive-checker`; then `critic`; per round `strategist`, whose decisions dispatch `model-refiner` (FIX or EXPLORE) and `model-designer` (new questions); finally `model-selector` |
| `report.js` | `report-planner`; `report-quant`; `section-writer` once per section, retried once; `report-assembler` (assemble, then revise); `report-critic` in a review loop |

## Working on a script

- Every script has a `call(name, prompt, opts)` seam. Passing
  `args.agentBodies[name]` prepends that text to the prompt and uses the
  default subagent instead of the plugin agent type, which allows prompt
  iteration or testing without reloading the plugin.
- Scripts use top-level `return` and `await`, so plain `node --check` rejects
  them. Wrap the body the way CI does:

  ```
  { echo "(async () => {"; sed 's/^export const meta/const meta/' workflows/develop.js; echo "})()"; } > /tmp/check.mjs && node --check /tmp/check.mjs
  ```

- Stage agents follow the `validation-protocol` status.json contract, so
  re-running a script with the same args re-verifies completed work from
  disk. Within a session, `resumeFromRunId` replays completed agent calls from
  the journal. Do not edit a script while a run that references it is in
  flight.
- A full run is expensive. Review changes by reading, syntax-check, and use
  `stopAfter` (report.js) or `agentBodies` for partial runs before spending a
  real workflow.
