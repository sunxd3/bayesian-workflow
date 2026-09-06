# Workflows

Four scripts, one per phase. The Workflow tool runs them by path from the `orchestration` skill behind `/bayesian-workflow:run` (or `/bayesian-workflow:explore` for Phase 1 alone). Each script's header comment documents its args and return value.

The scripts handle the mechanical parts: caps, budgets, retries, and checking the numbers agents return. Anything that needs a decision is an `agent()` call with a JSON schema, so scripts never read prose.

| script | phase | key args | returns |
|---|---|---|---|
| `explore.js` | 1 | `projectDir`, `dataPath`, `goal?`, `edaDir?` | profile, findings, synthesis |
| `design.js` | 2 | `projectDir`, `dataPath`, `goal`, `maxQuestions?` | plan and seed ledger |
| `develop.js` | 3 | `projectDir`, `dataPath`, `questions`, `experiments`, `limits?` | selection, stop reason, final ledger |
| `report.js` | 4 | `projectDir`, artifact paths, `audience?`, `stopAfter?` | report path, reviews, open issues |

## Agent roster

The 18 agents in `agents/` are only useful because these scripts call them.

| script | agents, in dispatch order |
|---|---|
| `explore.js` | `data-profiler`; `eda-analyst` per focus area; `synthesist` (`eda`) |
| `design.js` | `analysis-planner`; `model-designer` per question; `synthesist` (`design`) |
| `develop.js` | gate stages: `prior-predictive-checker`, `fake-data-checker`, `model-fitter`, `posterior-predictive-checker`; then `critic`; per round `strategist`, which dispatches `model-refiner` and `model-designer`; finally `model-selector` |
| `report.js` | `report-planner`; `report-quant`; `section-writer` per section; `report-assembler`; `report-critic` in a loop |

## Working on a script

- Every script calls agents through a `call(name, prompt, opts)` helper. Pass `args.agentBodies[name]` to swap in your own prompt and a plain subagent — useful when you're tweaking prompts and don't want to reload the plugin.
- Scripts use top-level `return` and `await`, so `node --check` rejects them directly. Wrap the body like CI does:

  ```
  { echo "(async () => {"; sed 's/^export const meta/const meta/' workflows/develop.js; echo "})()"; } > /tmp/check.mjs && node --check /tmp/check.mjs
  ```
