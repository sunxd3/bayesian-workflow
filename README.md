# Bayesian Workflow

A Claude Code plugin for end-to-end Bayesian statistical modeling with Stan
and ArviZ, built around one architectural rule: **deterministic control flow
is code; judgment is an agent; the orchestrator only holds the seams.**

It began as a from-scratch rebuild ("v2") of the archived
[bayesian-statistician-plugin](https://github.com/sunxd3/bayesian-statistician-plugin);
the v1/v2 comparisons below refer to that predecessor.

v1 split Phase 3 as "mechanics in a workflow script, judgment in the
orchestrator's main loop between rounds". v2 inverts the remainder: the *entire*
multi-round development loop — including the between-round judgment — runs
inside one Workflow script, with judgment delegated to schema-constrained
agents (`strategist`, `critic`) *inside* the loop. The main-loop orchestrator
shrinks to a thin phase driver whose only real jobs are the user gates,
persistence, and the lab notebook.

## The three layers

| Layer | Holds | Examples |
|---|---|---|
| **Workflow scripts** (`workflows/*.js`) | Everything a `while` loop or threshold can decide | stage sequencing, FIX budgets, MCMC semaphore, verdict-vs-numbers audits, score plateau rule, question/experiment caps, retry-once, the ledger, token-budget reserve |
| **Agents** (`agents/*.md`) | Judgment over files, behind a typed interface | is this prior plausible, what does this residual mean, which question is resolved, is this the right model class |
| **Skills** (`skills/*`) | Methodology, loaded on demand by agents | Stan idiom, convergence thresholds, SBC, LOO validity, report formats |

The orchestrator (loaded by `/bayesian-workflow:run`) invokes three scripts
in order and gates between them:

```
explore.js   Profile → N parallel analysts → synthesist        → EDA report
   ▼  Gate 1: confirm the analysis goal
design.js    Planner → parallel designers → synthesist          → plan + LEDGER
   ▼  Gate 2: plan approval (last cheap moment for user input)
develop.js   ┌─ round: [prior → recovery → fit → ppc → critic]×N experiments
             │         strategist: close / explore / new questions / stop
             │         refiners + designers build next round
             └─ loop → selector → coverage-gap pass             → selection + LEDGER
report.js    Planner → quant (fact sheet + figures) → N parallel
             section writers → assembler → critic review loop   → final_report.html
```

## Design decisions (and why)

**The question ledger is first-class data.** The unit of scientific progress is
the structural question, so `develop.js` maintains a machine-readable ledger —
question → status → variants → score trajectory → resolution — threaded through
every round and persisted as `ledger.json`. The "iterate until modifications
stop helping" rule of v1 prose becomes a checkable plateau guard
(latest score gain < 2·SE(diff) → no further EXPLORE); the report writer gets
its narrative spine for free. The ledger also records `data_path` and the
ranking metric, so results from different datasets or metrics can never be
silently compared.

**Hardcode the shape, not the semantics.** A deterministic loop needs to
*compare* experiments, so the script fixes only the shape a comparison
requires — `{metric, score, score_se}`, higher is better — while the metric's
*identity* is declared once by the planner (observation-level LOO by default;
grouped or leave-future-out when the validation strategy demands it) and
threaded through fitter, ledger, plateau rule, and selector. A free-text
`reason` field would be too soft for a while-loop to act on; a hardcoded
`elpd_loo` field was too rigid — it silently overruled the plan's own
validation strategy. The same granularity rule governs the prior gate: the
audited `extreme_draw_pct` is measured against bounds the *plan* assigns, not
bounds the checked agent picks for itself.

**The strategist proposes; the script disposes.** Between-round judgment is an
agent call with a structured schema (`close/explore/new_questions/stop`), but
every decision passes deterministic guards — explore budgets, plateau rule,
new-question slots, experiment caps — and every dropped decision is logged.
Judgment runs in a fresh context each round instead of the main loop's most
degraded one.

**Verdicts are audited against self-reported numbers at every stage.** Each
gate stage's schema *requires* numeric fields (`extreme_draw_pct`,
`coverage_90`/`max_bias_z`, R̂/ESS/divergences/score, PPC coverage) plus
`data_path` provenance on the prior and fit gates. Fit thresholds are hard, so
an inconsistent fit PASS — including one that read a different dataset than
dispatched — is demoted to FAIL and enters the FIX loop; the other stages'
thresholds are heuristics, so inconsistencies are flagged for the strategist.
Definitions live in the `validation-protocol` skill's table.

**Framework questioning moved from per-experiment to per-round.** v1's critique
did statistical + domain + framework in one pass per experiment — expensive at
the most frequent stage, and anchored by the context that just validated the
model. v2's `critic` does statistical + domain and records `surprises`; the
`strategist` does framework questioning once per round over the whole
population, where it belongs.

**Facts→policy profiling.** `explore.js` sizes the EDA fan-out by having a
cheap profiler agent return dataset *facts*, then applying a deterministic
policy in code — instead of prose like "run 2–3 analysts for complex data".

**Cost is bounded and legible.** `develop.js` takes explicit `limits` (rounds,
refine/explore budgets, new-question slots, experiment cap, MCMC concurrency)
and honors the Workflow token budget with a reserve — discovery is real but no
longer unbounded by design. All caps log what they drop.

**Recovery is layered.** Stage agents write `status.json` completion records
(work-level, cross-session), the Workflow journal replays completed agent calls
(`resumeFromRunId`, same-session), and the persisted ledgers let the
orchestrator re-enter at any phase after compaction.

**Report writing is a pipeline, not an agent.** The writing is the deliverable,
so `report.js` mirrors a writing team: a **planner** decides the story, the
figure narrative, and — explicitly — what to omit; a **quant** builds the fact
sheet (every reportable number with its source file — the wall against
hallucinated statistics) and the report-quality figure set; **section writers**
draft in parallel from briefs, allowed to use only fact-sheet numbers; an
**assembler** makes one voice and writes the executive summary last; a
**critic** cold-reads as the target reader and runs mechanical audits (skim
test, numbers-vs-fact-sheet, dangling promises, paragraph density), looping
back to the assembler until SHIP or the revision budget is spent. The shared
quality bar lives in the `report-writing` skill, linked by all five report
agents; the critic audits against its rules by name. The
script supports `stopAfter` / `outline` / `facts` args, so any stage can be run
and inspected in isolation — including standalone on a finished analysis
project.

**What agents do NOT contain:** sequencing, budgets, retry policy, output
schemas, or each other's names. An agent is a role, a typed interface
(args / filesystem preconditions / artifacts / structured return), and a
skill-referencing procedure. That is the whole convention.

## Agents (18)

`data-profiler`, `eda-analyst`, `synthesist` (eda|design modes),
`analysis-planner`, `model-designer`, `prior-predictive-checker`,
`fake-data-checker`, `model-fitter`, `posterior-predictive-checker`, `critic`,
`strategist`, `model-refiner` (FIX|EXPLORE), `model-selector`,
`report-planner`, `report-quant`, `section-writer`, `report-assembler`,
`report-critic`.

## Testing seams (validated on a real project)

Every workflow script accepts two test knobs: `model` (per-agent model override,
e.g. `"sonnet"`) and `agentBodies` (map of agent name → role instructions,
prepended to the dispatch prompt and run on the default subagent — lets you
test pipelines and iterate on agent prompts in a session where the plugin is
not loaded). `report.js` additionally supports `stopAfter` / `outline` /
`facts` for stage-isolated runs. The dispatch seam (`call()`) also converts
agent-level failures (a subagent finishing without structured output THROWS
from `agent()`) into the uniform "lost" signal so retry/resubmit machinery
engages instead of a lifecycle dying.

The pipeline was validated end-to-end against `ck63g` (a completed v1 run):
explore/design reproduced the original run's framing independently on sonnet;
the report pipeline produced a measurably better report than v1's single-shot
writer (298- vs 589-word executive summary, zero dangling promises, three
blocking factual errors caught by the critic against the fact sheet); the
develop smoke run exercised the stage contracts, audited numerics, and crash
recovery on a real Stan fit.

## Install & use

```bash
git clone https://github.com/sunxd3/bayesian-workflow.git
claude --plugin-dir ./bayesian-workflow
```

```
> /bayesian-workflow:setup                 # once per project
> /bayesian-workflow:run data/sales.csv    # end-to-end
> /bayesian-workflow:eda data/sales.csv    # Phase 1 standalone
```

Requires `uv` and a C++ toolchain (CmdStan). On harnesses without the Workflow
tool, the orchestration skill degrades to Agent-tool dispatch at the same file
contracts (slower; the scripts are preferred).

## Layout

```
workflows/  explore.js  design.js  develop.js  report.js   # the deterministic skeleton
agents/     18 role definitions                  # judgment over files
skills/     orchestration, validation-protocol,  # rewritten for v2
            report-writing                       # the report quality bar
            + 13 methodology skills              # carried over from v1
commands/   run, setup, eda
shared_utils/                                    # bundled Python lib (carried over)
```

The 13 methodology skills and `shared_utils` are copied from v1 verbatim — the
rebuild targets the workflow architecture, not the statistical methodology.
