---
name: orchestration
description: Thin phase driver for the Bayesian workflow — invokes the four bundled workflow scripts (explore, design, develop, report), holds the user gates between phases, persists the ledgers, and keeps the lab notebook. Loaded by the `/bayesian-workflow:run` command.
user-invocable: false
---

# Bayesian Workflow Orchestration

Drive the workflow by invoking four bundled Workflow scripts in sequence, with
user gates after exploration and after design. You are deliberately thin:

- **Scripts own control flow.** Stage sequencing, rounds, budgets, retries,
  audits, plateau rules, and the question ledger are code in
  `${CLAUDE_PLUGIN_ROOT}/workflows/`. Do not re-derive or second-guess them.
- **Agents own judgment over files.** Analysts, designers, checkers, the
  critic, the strategist, the report team — all dispatched *inside* the
  scripts with structured output schemas. You do not dispatch pipeline agents
  yourself except in degraded mode.
- **You own the seams:** resolving inputs, the gates, persisting what scripts
  return, the lab notebook, and relaying progress.
- **Context is scarce.** Script returns and (in degraded mode) subagent
  replies land in your context window. Agents write detail to files and
  return short structured results; read the files when you need detail, and
  never ask an agent to embed report content in its reply.

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

Maintain `<project>/log.md` as an append-only lab notebook — a chronological,
honest record of what happened, what was surprising, and what was learned.
Scripts log mechanics; you log meaning. Write entries as work proceeds, not as
a polished retrospective: at phase boundaries, after each gate, and after each
Phase 3 round (the workflow's narrator lines mark them). One to three dense
lines per observation; the log is a working record, not a narrative.

**Failures and dead ends** — enough detail to learn from: the symptom, what
was tried, the outcome. Summarize tracebacks; never paste raw error dumps.
- *Bad.* "Exp 3 recovery check failed, moved to Exp 4."
- *Good.* "Exp 3 recovery: KeyError on '5%' column (CmdStanPy quantile
  labels). Fixed, but beta_temp bias 0.4σ. Skipped; Exp 4 recovered clean."

**Quantitative observations** — not just PASS/FAIL. After fits: wall time,
divergences, treedepth, ESS minimums. After PPCs: coverage, LOO-PIT summary,
residual patterns.
- *Bad.* "Prior predictive check passed."
- *Good.* "Prior PPC: 4% negative draws, prior 95% CI for mu [12, 340] vs
  observed [45, 280]. Reasonable."

**Question status** — what the round taught about each open question, with
numbers, and the evidence that settled a question when it resolves.
- "Q1 (day RE): exp_2 vs exp_1 baseline ELPD +42±8 — day variation real.
  Resolved."
- "Q2 (weather): exp_3 ELPD +3±5, not distinguishable. Critic found residual
  seasonal pattern — strategist raised: annual cycle rather than weather?"

**Surprises** — often more valuable than conclusions: "sigma_group piling up
near zero — day RE may not be needed."

**Phase transitions and key decisions** — why a path was chosen, a model
skipped, or an approach revised; what the user decided at each gate.

**Cross-references** — file paths so the trail is followable:
"See `experiments/exp_2/critique/critique_report.html`."

Never rewrite or delete past entries; dead ends are part of the record.

## Canonical structure

Files are the only persistent channel between agents and across phases. The
scripts enforce these paths; use them when reading, and in degraded mode
when dispatching.

```
data/                                # source data
log.md                               # your lab notebook (append-only)
eda/                                 # Phase 1 — explore.js
  eda_report.html                    # synthesist output (required)
  data.cleaned.parquet               # standardized dataset (analyst_1 writes it)
  data.augmented.parquet             # optional derived columns
  quality_summary.csv, univariate_summary.csv
  analyst_N/                         # one per focus area
    findings.md, status.json, log.md, *.png, *.py
design/                              # Phase 2 — design.js
  experiment_plan.md                 # planner seed + synthesized final table
  ledger.json                        # questions + experiments (you persist)
  log.md                             # planner notebook
  designer_qN/proposal.md, log.md
experiments/                         # Phase 3 — develop.js
  <exp_id>/                          # one folder per experiment/variant
    model.stan                       # single source of truth for every stage
    refinement_notes.md              # variants only (model-refiner)
    prior_predictive/
      prior_model.stan, prior_predictive.nc
      prior_predictive_report.html, status.json
    simulation/
      simulator.stan, recovery_report.html, status.json
    fit/
      posterior.nc, summary.json, diagnostics.json, loo.json
      ranking_score.json             # when the plan's metric is not plain LOO
      thinned_draws.npz, fit_report.html, status.json
    posterior_predictive/
      posterior_predictive_report.html, status.json
    critique/
      critique_report.html, status.json
                                     # every stage dir also holds log.md, *.png, *.py
  strategy/round_N.md                # strategist decision records
  population_assessment.html         # selector output
  log.md                             # selector notebook
  ledger.json                        # final question/experiment state (you persist)
report/                              # Phase 4 — report.js
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

Drive the phases manually with the Agent tool at the same file contracts,
launching independent agents in parallel from a single message and tracking
with TaskCreate/TaskUpdate, one task per experiment-stage. Give every agent
its own output directory and point it at files produced upstream rather than
summarizing content inline.

- **Phase 1:** one `eda-analyst` per focus area (2–3; `analyst_1` owns the
  canonical deliverables), then `synthesist` in mode `eda`.
- **Phase 2:** `analysis-planner`, then one `model-designer` per question,
  then `synthesist` in mode `design`; build the ledger by hand from the final
  table.
- **Phase 3:** per experiment, prior-predictive-checker → fake-data-checker →
  model-fitter → posterior-predictive-checker → critic sequentially (3–5
  experiments in parallel), honoring `status.json` short-circuits; on FAIL,
  model-refiner (FIX, 2 per lifecycle) re-enters at prior. After each sweep,
  dispatch the strategist with a hand-composed digest and apply its decisions
  with the same discipline the script would (respect its constraints; log what
  you drop). When all work is terminal, `model-selector`.
- **Phase 4:** report-planner → report-quant → section-writers →
  report-assembler → report-critic sequentially, with one revision round.

Expect all of it to be slower and sloppier than the scripts — prefer them
whenever the Workflow tool exists.

## Technical stack

- Stan via CmdStanPy, ArviZ for diagnostics; `uv` exclusively (never bare
  `python`/`pip`); scripts self-contained and run with `uv run`.
- Subagents inherit the session model; heavy MCMC cost lives in the fitter and
  fake-data stages — the develop script's `maxMcmcConcurrency` throttles them.
