---
name: orchestration
description: End-to-end Bayesian modeling workflow orchestration — phases (EDA → design → development → reporting), task-pool semantics for the validation pipeline, canonical file structure, and dispatch protocol for the eleven subagents. Loaded by the `/bayesian-workflow:run` command.
user-invocable: false
---

# Bayesian Workflow Orchestration

Drive the Bayesian workflow through four phases by dispatching the eleven subagents and writing all results into the canonical folder structure. The invoking command supplies a dataset and/or analysis goal via `$ARGUMENTS`.

If no dataset or analysis goal is provided, look for data files (CSV, JSON, Parquet) in `data/`, `analysis/data/`, or the working directory and proceed with the most relevant one. If the goal is unspecified, synthesize one from the data and state it explicitly before starting.

## Objective

The final deliverable must be a Bayesian model: specify priors, perform posterior inference, and evaluate via posterior predictive checks. Non-Bayesian methods may be explored as baselines/context but must not be selected or reported as the solution.

Core principles:
- Start from generative stories: think data-generating process, not just prediction
- Specify priors explicitly and validate via prior predictive checks
- Use full posterior inference (not MLE/MAP)
- Validate models with posterior predictive checks and parameter recovery checks
- Check diagnostics (R-hat, ESS, divergences, trace plots)
- Compare models via predictive performance (LOO, WAIC)
- Consider hierarchical structures when data has grouping/repeated measures
- Flag computational issues (identifiability, convergence, misspecification) when relevant

## Communication

Outputs serve two purposes:

Terminal output:
- Keep users and developers informed of progress in real-time
- Report current actions and key decisions as they happen
- Be concise but informative

Written artifacts (reports, logs):
- These are the primary deliverables that users will read retrospectively
- Invoke the `artifact-guidelines` skill to get the full guidelines

### Subagent responses

Subagent responses share the orchestrator's context window. Each subagent
writes all detail to files and returns a short verdict plus key numbers; the
exact response shape is defined in each subagent's `Interface > Returns`. Do
not ask subagents to embed report content in their reply — read the report
file for detail.

## Persistent Log

Use TaskCreate/TaskUpdate for real-time task tracking (ephemeral, current session). Separately, maintain `log.md` as a lab notebook — a chronological, honest record of what happened, what was surprising, and what was learned. Write entries as work proceeds, not as a polished retrospective.

**Append-only.** Never rewrite or delete past entries to make the process look cleaner. Mistakes and dead ends are part of the record.

### What to record

**Failures and dead ends.** Record with enough detail to learn from — the actual error or symptom, what was tried, and the outcome. Summarize tracebacks; do not paste raw error dumps.
- **Bad.** "Exp 3 recovery check failed, moved to Exp 4."
- **Good.** "Exp 3 recovery: KeyError on '5%' column (CmdStanPy quantile labels). Fixed, but beta_temp bias 0.4σ. Skipped; Exp 4 recovered clean."

**Quantitative observations.** Not just PASS/FAIL. After fits: wall time, divergences, treedepth, ESS minimums. After PPCs: coverage, LOO-PIT summary, residual patterns.
- **Bad.** "Prior predictive check passed."
- **Good.** "Prior PPC: 4% negative draws, prior 95% CI for mu [12, 340] vs observed [45, 280]. Reasonable."

**Surprises and intermediate observations.** Things that weren't expected. These are often more valuable than conclusions.
- "sigma_group piling up near zero — day RE may not be needed"
- "EDA suggested AR(1) but day-level RE absorbed most autocorrelation — didn't expect that"

**Cross-references.** Link to files so the trail is followable.
- "See `experiments/exp2/critique/critique_report.html` for full diagnostics"

**Phase transitions and key decisions.** Why a path was chosen, a model skipped, or an approach revised.

**Question status.** Track what is being learned about each structural question. When evidence accumulates (a model passes or fails, a critique reveals something), note what it means for the question. When a question is resolved — either answered or shown to be unresolvable with the available data — record the answer and the evidence that settled it.
- "Q1 (day-level RE): exp_1 baseline vs exp_2 with day RE — ELPD +42±8, day RE clearly needed. Resolved: yes, day-level variation matters."
- "Q2 (weather effects): exp_3 added weather → ELPD +3±5, not distinguishable. Critique found residual seasonal pattern — new question: is it annual cycle, not weather?"

### Style

Keep entries dense — one to three lines per observation. The log is a working record, not a narrative. Log after each substantive step (fits, checks, design decisions), not just at phase boundaries.

## Tool Usage

- Proactively use the Agent tool with specialized subagents when the task matches the subagent's description
- When calling multiple tools, invoke independent tools in parallel for efficiency
- For tools with dependencies, call them sequentially - never use placeholders or guess missing parameters
- To run multiple subagents in parallel, send a single message with multiple Agent tool uses
- Use specialized file tools (Read, Edit, Write) instead of bash commands (cat, sed, echo)
- Reserve bash exclusively for system commands (git, uv)

### Parallel Subagents
Use parallel subagents to explore multiple perspectives simultaneously, particularly for EDA and model design where uncertainty is high. Each instance needs isolated workspace and files to avoid conflicts. Launch all instances at once using multiple Agent tool calls in a single message.

Setup: Prepare separate data copies if needed and assign each instance its own output directory (e.g., `eda/analyst_1/`, `eda/analyst_2/`). Give each instance a different focus area.

Execution: Typical count is 2-3 instances. If an instance fails, relaunch once; if it fails again, proceed with successful instances.

After completion: Synthesize findings from all instances and document convergent patterns (all agree) and divergent insights (unique to one).

## Validation Rounds for Pipeline Flow

Model development involves many experiments (model classes × variants, often 7-10+). Instead of synchronizing at each stage, experiments flow independently through the validation pipeline:

```
Experiment lifecycle:
prior → recovery → fit → ppd → critique → ✓ complete
   ↓ fail    ↓ fail    ↓ fail  ↓ fail    ↓ BROKEN
 refine (FIX) → new variant → re-enter at prior (or skip if budget exhausted)

Back-edges from critique:
  A  VIABLE/CONCERNS + suggestions → refiner (EXPLORE) → new variant → prior
  D  new structural question discovered → designer → new experiments → prior

Back-edges from model-selector (after all experiments terminal):
  E  CONTINUE_QUESTION → refiner (EXPLORE) → new variant → prior
  D  new structural question discovered → designer → new experiments → prior
     COVERAGE: GAPS → designer → gap experiments → prior
```

Phase 3 runs as **rounds**. Within a round, the bundled workflow script executes the mechanical pipeline over the current experiment list — stage sequencing, budgeted FIX refinement, MCMC throttling — deterministically. Between rounds, you make every judgment call: which critique suggestions to explore, which new structural questions to pursue, when to invoke the selector. The lifecycle back-edges above are yours to drive; the straight-line pipeline and its FAIL→FIX edge belong to the script.

### Running a round

```
Workflow({
  scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/validate-experiments.js",
  args: {
    projectDir: "<absolute project root>",
    dataPath: "<absolute path to the dataset>",
    experiments: [{ id: "exp_1", spec: "<model spec from experiment_plan.md>",
                    context: "<optional carry-forward notes>" }, ...]
  }
})
```

Optional args: `experimentPlanPath`, `edaReportPath` (default to canonical locations under `projectDir`), `maxMcmcConcurrency` (default 3), `refineBudget` (default 2). Pass args as a plain JSON object with absolute paths. Do not edit the script file, and do not launch overlapping rounds that share an experiment directory.

Per experiment the script enforces: stage order; FAIL → `model-refiner` (FIX) → variant `{id}_fixN` re-enters at the prior stage; maximum `refineBudget` refiner invocations per experiment lifecycle, then skip; and a verdict-vs-numbers audit on fits (a PASS whose reported R̂/ESS/divergences violate thresholds is flagged `cross_check: "INCONSISTENT"`).

The round returns `{terminal, skipped, counts}`: each `terminal` entry carries the full stage trail plus the critique result (verdict, suggestions, `new_structural_question`); `skipped` entries name the failed stage and carry the trail for triage.

### Between rounds — your decisions

Read the round's results, log observations to `log.md`, then build the next round's experiment list:

- **Critique VIABLE/CONCERNS with suggestions** → invoke `model-refiner` (EXPLORE) via the Agent tool with the priority suggestions; add the resulting variant to the next round.
- **Critique BROKEN** → decide whether one FIX attempt is warranted (invoke `model-refiner`, add the variant) or the experiment should be dropped.
- **`new_structural_question`** (from critique or the selector) → invoke `model-designer` with the current best model as `baseline_spec`; add the resulting experiments.
- **Skipped / agent-lost experiments** → triage from the trail. Re-running an experiment is cheap — completed stages short-circuit on their `status.json` — so a transient failure can simply be resubmitted. Apply the baseline special case: if a structural question's baseline variant failed pre-fit (prior or recovery) after its refine attempt, drop all experiments for that question.
- **`cross_check: "INCONSISTENT"`** → read the fit report before trusting the experiment; re-dispatch or treat as failed.
- **No new work** → all experiments terminal → invoke `model-selector`.

Track rounds with `TaskCreate`/`TaskUpdate` at round granularity (e.g. "Round 2: exp_1_v2, exp_4, exp_5"), not per stage — the script owns stage tracking within a round.

### Recovery

- **Round interrupted or crashed:** re-invoke the same round with the same args. Stage agents follow the `validation-protocol` completed-work check, so finished stages return their recorded verdicts in seconds instead of re-fitting.
- **Same session:** pass `resumeFromRunId` from the interrupted invocation to also replay completed agent calls from the workflow journal.

### Fallback: task-pool protocol (no Workflow tool)

If the Workflow tool is unavailable, drive the same pipeline manually with the Agent tool, tracked via `TaskCreate`/`TaskUpdate`/`TaskList` — one task per experiment per stage (never coarse phase-level tasks). Two states only: task exists and incomplete → needs launching; task completed → done, never re-launch.

1. Initialize: `TaskCreate("prior-predictive-checker {exp_id}")` per experiment.
2. While any task is incomplete: `TaskList` first — **always check before dispatching** — then launch up to 3-5 incomplete tasks as parallel Agent calls. As each returns, mark it completed and: **PASS** → `TaskCreate` for the next stage; **FAIL** → `model-refiner` (FIX) → `TaskCreate("prior-predictive-checker {variant}")`, or skip if the refine budget (2 per experiment lifecycle) is exhausted; **critique results** → handle per "Between rounds" above.
3. All tasks completed → `model-selector`.

Sync only after all experiments reach terminal state — fast experiments finish while slow ones are still being refined. After context compaction, `TaskList` and the `status.json` files in the canonical locations are the ground truth; read them before dispatching anything.

## Technical Stack

- **Bayesian inference.** Stan via CmdStanPy, ArviZ for diagnostics.
- **Package management.** `uv` exclusively (never bare `python` or `pip`).
- **First run.** Set up the Python environment (dependencies + bundled `shared_utils`) by running the `/bayesian-workflow:setup` command. Check for `./pyproject.toml` and `./shared_utils/` first — the user may have already run it.
- **Scripts.** Self-contained and run with `uv run`.

Every accepted Bayesian model must use Stan via CmdStanPy for posterior inference with NUTS. Do not substitute MLE/MAP for full Bayesian inference, use non-PPL implementations as final models, or label bootstrap-based checks as posterior predictive checks.

## File-Based Communication and Folder Structure

Files are the only persistent communication channel between subagents and across phases. Always specify exact paths when invoking subagents: where to read inputs and where to write outputs.

### Canonical Structure
Use this structure unless the task requires deviation:

```
data/                           # source data and copies
eda/                            # Phase 1: Data Understanding
  eda_report.html                 # final synthesis (required)
  quality_summary.csv           # data quality table (required)
  univariate_summary.csv        # per-variable summary stats (required)
  analyst_1/                    # if parallel: each instance gets own folder
  analyst_2/
design/                         # Phase 2: Model Design
  designer_1/
    designer_proposal.md        # (required)
  designer_2/
    designer_proposal.md        # (required)
  experiment_plan.md            # synthesized plan (required)
experiments/                    # Phase 3: Model Development
  experiment_1/                 # one folder per model attempt
    model.stan                  # main inference model
    prior_predictive/
      prior_model.stan          # GQ-only: mirrors priors, generates y_rep
      prior_predictive_report.html  # (required)
      prior_predictive.nc       # ArviZ InferenceData (prior + prior_predictive)
      status.json               # completion record (validation-protocol)
      *.png, *.py
    simulation/
      simulator.stan            # GQ-only: true params as data, generates y_rep
      recovery_report.html      # (required)
      status.json               # completion record
      *.png, *.py
    fit/
      fit_report.html           # convergence diagnostics, assessment (required)
      posterior.nc              # ArviZ InferenceData (needed through reporting)
      thinned_draws.npz         # parameter draws only (lightweight)
      loo.json                  # LOO results: ELPD, Pareto k (needed by selector)
      status.json               # completion record
      *.png, *.py
    posterior_predictive/
      posterior_predictive_report.html  # (required)
      status.json               # completion record
      *.png, *.py
    critique/
      critique_report.html      # statistical + domain + framework (required)
      status.json               # completion record
      *.png, *.py
  experiment_2/
  population_assessment.html    # model-selector output (required)
final_report.html               # Phase 4 output (required)
log.md                          # append-only workflow log
```

### Subagent Communication
Point subagents to files produced by previous subagents rather than summarizing content inline (e.g., tell model-designer to "Read the EDA report at `eda/eda_report.html`" rather than summarizing EDA findings). Ask subagents to report what files they created so the next dispatch can reference them along the chain.

## Modeling Workflow

### Phase 1: Data Understanding → `eda/`
Invoke `eda-analyst` to explore the data. For complex datasets, run 1-3 instances in parallel with different focus areas, then synthesize results into `eda/eda_report.html`.

### Phase 2: Model Design → `design/`

**Step 1: Plan the analysis.** Invoke `analysis-planner` with the EDA directory and `design/` as output. It produces the seed `design/experiment_plan.md` with analysis purpose + KQIs, validation strategy, domain context, 2-3 contrastive structural questions, and a domain-aware shared baseline. All downstream agents read this file.

**Step 2: Assign questions to designers.** Run 2-3 `model-designer` instances in parallel. Give each: the EDA directory, the path to `design/experiment_plan.md` (so they can read analysis purpose, validation strategy, domain context, and the shared baseline from the planner's output), their assigned structural question, the baseline spec, the other designers' questions, and their output directory. Encourage designers to consider structurally different model families (not just parametric extensions of the baseline) if they better match the data-generating process. Each designer produces a resolution sequence that answers their question.

**Step 3: Synthesize.** Read all designer proposals and append the final experiments table to `design/experiment_plan.md` (preserving the planner-seeded sections above). De-duplicate overlapping models, add cross-cutting experiments where designer questions interact, order by information value, and set total experiment count (typically 6-10).

### Phase 3: Model Development and Selection → `experiments/`

Validate all experiments from the experiment plan in rounds (see "Validation Rounds for Pipeline Flow"). Each experiment flows through 5 stages: `prior-predictive-checker` → `fake-data-checker` → `model-fitter` → `posterior-predictive-checker` → `critique`.

The `critique` agent performs statistical assessment, domain assessment, and framework questioning in a single pass.

**Failure handling** (enforced by the round script; replicate manually only in fallback mode):
- Any stage fails → `model-refiner` (FIX) → new variant re-enters at the prior stage
- Refiner reports exhaustion or fails → skip experiment
- **Global budget.** Each experiment has a maximum of TWO `model-refiner` invocations across its entire lifecycle (all stages combined). If it fails a third time at any stage, it is skipped.
- **Special case (yours, between rounds).** If a structural question's baseline variant fails pre-fit (prior or recovery), drop all experiments for that question after one refine attempt.

**Critique-driven iteration (REQUIRED).**
When `critique` returns VIABLE or CONCERNS with improvement suggestions:
1. Invoke `model-refiner` in EXPLORE mode with the specific suggestions (prioritize PRIORITY 1 concerns — especially framework concerns)
2. Create a modified variant (e.g., `exp_1_v2`, `exp_1_robust`)
3. Add the new variant to the next round for validation
4. Compare the modified variant against its parent via LOO/ELPD
5. If the modification improved the model, critique it again and repeat
6. Stop iterating when: modifications no longer improve ELPD, or suggestions become unreasonable/impractical

The goal is to **iterate until reasonable modifications stop helping**, not just validate pre-designed experiments. Each structural question should have multiple iterations showing progressive refinement or evidence that simpler versions suffice.

Do NOT skip directly to model selection after initial experiments. Do NOT stop after one iteration if the modification helped and critique suggests further improvements.

**Discovery-driven questions.**
Critique and selection are not just quality gates — they are sources of new hypotheses. When critique reveals something genuinely surprising (unexpected residual structure, a parameter collapsing to zero, a domain mechanism that the original questions didn't anticipate, or unused data that could support a better framework), this may warrant a **new structural question** rather than a tactical refinement of the existing model.

Distinguish between:
- **Refinement suggestion** → model-refiner creates a variant within the current question
- **New structural question** → model-designer designs new experiments with the current best model as baseline

When a new question is identified from critique or selection insights:
1. Invoke `model-designer` with the new question and the **current best model** as `baseline_spec` (not the original Phase 2 baseline — build on what has been learned)
2. Add the resulting experiments to the next round
3. The new experiments flow through the same validation pipeline as the original ones

This is the scientific process: hypothesize → test → observe → generate new hypotheses. A finite dataset has finite structure, so the questions will converge naturally. Do not artificially limit discovery — if the agent keeps finding genuine structure, that is valuable work.

**When all experiments terminal** → invoke `model-selector` with experiments that completed critique with VIABLE or CONCERNS verdict (exclude BROKEN — they were sent to refinement or skipped):
- Compares validated experiments using the comparison method appropriate to the data structure
- **CONTINUE_QUESTION.** `model-refiner` generates new variants → add to the next round.
- **SWITCH_QUESTION.** This question is resolved; move focus to next question.
- **ADEQUATE / EXHAUSTED.** The selector's assessment includes a **Coverage Audit** section.

The selector may also report **new structural questions** discovered from model comparison (unexpected patterns, discriminating features) alongside any of the above decisions. If present, invoke `model-designer` with each new question, using the current best model as `baseline_spec`.

**Coverage audit.** When the `model-selector` subagent returns ADEQUATE or EXHAUSTED, read its `COVERAGE:` section from `experiments/population_assessment.html`. If `COVERAGE: GAPS`, invoke `model-designer` for each gap (using the current best model as `baseline_spec`) and add the resulting experiments to the next round. If `COVERAGE: COMPLETE`, proceed to reporting.

### Phase 4: Reporting → `final_report.html`
Invoke `report-writer` with the selected model's experiment directory (`selected_model_dir`). The `report-writer` subagent will compute practical contrasts and write the final report.
