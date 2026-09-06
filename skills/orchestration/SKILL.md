---
name: orchestration
description: Thin phase driver for the Bayesian workflow — invokes the three bundled workflow scripts (explore, design, develop), holds the user gates between phases, persists the ledger, and dispatches the final report. Loaded by the `/bayesian-workflow:run` command.
user-invocable: false
---

# Bayesian Workflow Orchestration

Drive the workflow by invoking three bundled Workflow scripts in sequence, with
a user gate between design and development. You are deliberately thin:

- **Scripts own control flow.** Stage sequencing, rounds, budgets, retries,
  audits, plateau rules, and the question ledger are code in
  `${CLAUDE_PLUGIN_ROOT}/workflows/`. Do not re-derive or second-guess them.
- **Agents own judgment over files.** Analysts, designers, checkers, the
  critic, the strategist — all dispatched *inside* the scripts with structured
  output schemas. You do not dispatch pipeline agents yourself except in
  degraded mode.
- **You own the seams:** resolving inputs, the gates, persisting what scripts
  return, the lab notebook, relaying progress, and Phase 4.

The invoking command supplies a dataset and/or analysis goal via `$ARGUMENTS`.
If no dataset is given, look for data files (CSV, JSON, Parquet) in `data/`,
`analysis/data/`, or the working directory and proceed with the most relevant
one, stating the choice.

## Objective

The final deliverable must be a Bayesian model: explicit priors validated by
prior predictive checks, full posterior inference via Stan/CmdStanPy with NUTS
(never MLE/MAP, never a non-PPL implementation as the final model), posterior
predictive checks (never bootstrap checks labeled as such), model comparison
via predictive performance (LOO or the grouped/temporal variant the plan's
validation strategy demands), hierarchical structure considered when data
has grouping. Non-Bayesian methods may appear as baselines/context only.

## Phase runbook

All paths absolute. `<project>` is the project root; the canonical folder
structure is below.

**Phase 0 — Environment.** Check `./pyproject.toml` and `./shared_utils/`
exist; if not, run the `/bayesian-workflow:setup` steps first.

**Phase 1 — Explore.**

```
Workflow({ scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/explore.js",
           args: { projectDir, dataPath, goal? } })
```

Returns `{profile, analyst_findings, synthesis}`. Log the structural
hypotheses to `log.md`.

**Gate 1 — Goal.** If the user supplied no goal, the synthesis includes
`suggested_goal`. Confirm it with the user (AskUserQuestion) when they are
present; otherwise adopt it and state it explicitly before continuing.

**Phase 2 — Design.**

```
Workflow({ scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/design.js",
           args: { projectDir, dataPath, goal } })
```

Returns `{plan, ledger}`. Persist the ledger verbatim to
`<project>/design/ledger.json` (Write tool, pretty-printed). Log the framing.

**Gate 2 — Plan approval.** Present purpose, questions, experiment count, the
ranking metric, and any `ledger.deferred_questions` (questions the planner
ranked below the dispatch cap — the user may swap one in for a dispatched
question). This is the highest-leverage moment for user input and the last
cheap one — everything after burns MCMC time. When the user is present, ask
(AskUserQuestion): proceed / adjust questions / trim experiments. Apply
adjustments by editing the ledger object (and `experiment_plan.md` to match)
before Phase 3. When running unattended, proceed and state the plan and the
deferred questions.

**Phase 3 — Develop.**

```
Workflow({ scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/develop.js",
           args: { projectDir, dataPath,
                   questions: <ledger.questions>, experiments: <ledger.experiments>,
                   metric: <plan.ranking_metric>,        // the plan's comparison metric
                   bounds: <plan.plausibility_bounds>,   // the plan's prior-check bounds
                   limits?: { maxRounds, refineBudget, maxMcmcConcurrency,
                              explorePerQuestion, maxNewQuestions,
                              maxTotalExperiments } } })
```

`metric` and `bounds` come from the Phase 2 return — pass them through
verbatim. The develop script hardcodes only the *shape* of a comparison
(score ± se, higher is better); the metric's *identity* is the plan's call,
and omitting it silently reverts to observation-level LOO, which grouped or
temporal data usually forbids.

The script runs the entire multi-round loop — validation pipeline, per-round
strategist, refiners/designers, selection, coverage-gap pass — and returns
`{selection, stop_reason, ledger, counts}`. While it runs, relay its narrator
lines; do not dispatch competing work into `experiments/`.

Afterwards: persist the returned ledger to `<project>/experiments/ledger.json`;
log per-question resolutions and the stop reason. If `selection` is null (no
viable models), read the ledger's skipped experiments, report honestly what
failed and why, and stop — do not force a report from nothing.

**Phase 4 — Report.** The writing is the deliverable, so it runs as its own
pipeline (plan → fact sheet + figures → parallel section drafts → assemble →
critic review loop):

```
Workflow({ scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/report.js",
           args: { projectDir, ledgerPath: <project>/experiments/ledger.json,
                   selectedModelDir: <project>/experiments/<selection.best_model_id>,
                   dataPath } })
```

Returns `{report_path, word_count, reviews, ...}`. The pipeline writes its
working products under `report/` (outline, fact sheet, figures, section
drafts, critic reviews) — they are the audit trail for the prose. If the final
review verdict was not SHIP, read the last `report/review_round_N.md` and tell
the user what remained open.

Then summarize for the user: per-question findings, the selected model, caveats,
and where every artifact lives.

## Persistent log (`log.md`)

Maintain `<project>/log.md` as an append-only lab notebook. Scripts log
mechanics; you log meaning. Write entries at phase boundaries and after each
Phase 3 round (the workflow's narrator lines mark them), one to three dense
lines per observation:

- **Question status** — what the round taught about each open question, with
  numbers: "Q1 (day RE): exp ELPD +42±8 over baseline — day variation real."
- **Surprises** — often more valuable than conclusions: "sigma_group piling up
  near zero — day RE may not be needed."
- **Failures with enough detail to learn from** — symptom, attempt, outcome;
  never bare "failed, moved on".
- **Cross-references** — file paths so the trail is followable.

Never rewrite or delete past entries; dead ends are part of the record.

## Canonical structure

```
data/                                # source data
log.md                               # your lab notebook (append-only)
eda/
  eda_report.html                    # synthesist output (required)
  quality_summary.csv, univariate_summary.csv
  analyst_N/findings.md              # per-analyst findings + plots
design/
  experiment_plan.md                 # planner seed + synthesized final table
  ledger.json                        # questions + experiments (you persist)
  designer_qN/proposal.md
experiments/
  <exp_id>/                          # one folder per experiment/variant
    model.stan
    prior_predictive/  simulation/  fit/  posterior_predictive/  critique/
                                     # each: report + status.json + artifacts
  strategy/round_N.md                # strategist decision records
  population_assessment.html         # selector output
  ledger.json                        # final question/experiment state (you persist)
report/
  outline.md                         # report-planner: story, briefs, omissions
  fact_sheet.md                      # report-quant: every reportable number + source
  figures/ (+ manifest.json)         # the report's figure set with captions
  sections/<id>.md                   # section-writer drafts
  review_round_N.md                  # report-critic reviews (kept even on SHIP)
  final_report.html                  # the deliverable
```

## Recovery

- **Interrupted phase:** re-invoke the same script with the same args. Stage
  agents short-circuit on `status.json`, so completed MCMC work re-verifies in
  seconds. Same session: also pass `resumeFromRunId` to replay the journal.
- **After compaction:** the two `ledger.json` files, `status.json` records, and
  `log.md` are ground truth. Read them before dispatching anything.
- Do not launch overlapping runs that share `experiments/`.

## Degraded mode (no Workflow tool)

Drive Phase 3 manually with the Agent tool at the same contracts: per
experiment, dispatch prior-predictive-checker → fake-data-checker →
model-fitter → posterior-predictive-checker → critic sequentially (3–5
experiments in parallel), honoring `status.json` short-circuits; on FAIL,
model-refiner (FIX, 2 per lifecycle) re-enters at prior. After each sweep,
dispatch the strategist with a hand-composed digest and apply its decisions
with the same discipline the script would (respect its constraints; log what
you drop). Track with TaskCreate/TaskUpdate, one task per experiment-stage.
For the report, dispatch report-planner → report-quant → section-writers →
report-assembler → report-critic sequentially at the same file contracts, with
one revision round. Expect all of it to be slower and sloppier than the
scripts — prefer them whenever the Workflow tool exists.

## Technical stack

- Stan via CmdStanPy, ArviZ for diagnostics; `uv` exclusively (never bare
  `python`/`pip`); scripts self-contained and run with `uv run`.
- Subagents inherit the session model; heavy MCMC cost lives in the fitter and
  fake-data stages — the develop script's `maxMcmcConcurrency` throttles them.
