# Bayesian Workflow

A Claude Code plugin for end-to-end Bayesian statistical modeling with Stan
and ArviZ. It packages four Workflow scripts, eighteen subagents, and a library
of methodology skills that together run the full workflow —
**EDA → model design → model development → reporting** — around one
architectural rule: **deterministic control flow is code; judgment is an
agent; the orchestrator only holds the seams.**

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) — used for all Python execution.
- A C++ toolchain — CmdStanPy compiles Stan models against CmdStan. The
  `/bayesian-workflow:setup` command installs CmdStan via
  `python -m cmdstanpy.install_cmdstan`.
- The Workflow tool. On harnesses without it, the orchestration skill degrades
  to Agent-tool dispatch at the same file contracts (slower; the scripts are
  preferred).

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

Bootstrap the Python environment once per project:

```
> /bayesian-workflow:setup
```

Then run the workflow with your data path and/or analysis goal:

```
> /bayesian-workflow:run data/sales.csv — model weekly sales and quantify the promotion effect
```

The orchestrator drives four phases, pausing at two user gates (goal
confirmation after EDA, plan approval after design), and writes everything
into a predictable folder structure (`eda/`, `design/`, `experiments/`,
`report/`, `log.md`).

Phase 1 can also run standalone:

```
> /bayesian-workflow:eda data/sales.csv [output_dir] [--focus=<area>]
```

## The three layers

| Layer | Holds | Examples |
|---|---|---|
| **Workflow scripts** (`workflows/*.js`) | Everything a `while` loop or threshold can decide | stage sequencing, FIX budgets, MCMC semaphore, verdict-vs-numbers audits, score plateau rule, question/experiment caps, retry-once, the ledger, token-budget reserve |
| **Agents** (`agents/*.md`) | Judgment over files, behind a typed interface | is this prior plausible, what does this residual mean, which question is resolved, is this the right model class |
| **Skills** (`skills/*`) | Methodology, loaded on demand by agents | Stan idiom, convergence thresholds, SBC, LOO validity, report formats |

The orchestrator (loaded by `/bayesian-workflow:run`) invokes the four scripts
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
every round and persisted as `ledger.json`. The earlier orchestrator's prose
rule "iterate until modifications stop helping" becomes a checkable plateau
guard (latest score gain < 2·SE(diff) → no further EXPLORE); the report
pipeline gets its narrative spine for free. The ledger also records `data_path`
and the ranking metric, so results from different datasets or metrics can never
be silently compared.

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

**Framework questioning is per-round, not per-experiment.** The earlier
`critique` agent did statistical + domain + framework in one pass per
experiment — expensive at the most frequent stage, and anchored by the context
that just validated the model. The `critic` does statistical + domain and
records `surprises`; the `strategist` does framework questioning once per
round over the whole population, where it belongs.

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
agents; the critic audits against its rules by name.

**What agents do NOT contain:** sequencing, budgets, retry policy, output
schemas, or each other's names. An agent is a role, a typed interface
(args / filesystem preconditions / artifacts / structured return), and a
skill-referencing procedure. That is the whole convention.

## What's inside

**Workflow scripts (4)** — `explore.js`, `design.js`, `develop.js`, and
`report.js` under `workflows/`. Every script accepts `model` (per-agent model
override, e.g. `"sonnet"`) and `agentBodies` (map of agent name → role
instructions, prepended to the dispatch prompt and run on the default
subagent — lets you test pipelines and iterate on agent prompts in a session
where the plugin is not loaded). `report.js` additionally supports
`stopAfter` / `outline` / `facts` for stage-isolated runs, including standalone
on a finished analysis project.

**Agents (18)**, by phase:
- *Explore* — `data-profiler`, `eda-analyst`, `synthesist` (`eda` mode)
- *Design* — `analysis-planner`, `model-designer`, `synthesist` (`design` mode)
- *Develop* — `prior-predictive-checker`, `fake-data-checker`, `model-fitter`,
  `posterior-predictive-checker`, `critic`, `strategist`, `model-refiner`
  (FIX | EXPLORE), `model-selector`
- *Report* — `report-planner`, `report-quant`, `section-writer`,
  `report-assembler`, `report-critic`

**Commands (3)**:
- `/bayesian-workflow:setup` — bootstraps the Python environment (copies
  `shared_utils`, creates `pyproject.toml`, runs `uv sync` and
  `cmdstanpy.install_cmdstan`).
- `/bayesian-workflow:run [data-path and/or analysis goal]` — end-to-end
  pipeline. Loads the `orchestration` skill and drives all four phases.
- `/bayesian-workflow:eda <data_path> [output_dir] [--focus=<area>]` — Phase 1
  standalone via `explore.js`.

**Skills (16)** — three workflow skills: `orchestration` (the phase driver,
loaded by `run`), `validation-protocol` (input validation, `status.json`
completion records, structured returns and the audited-numbers table), and
`report-writing` (the report quality bar, with `references/final-report.md` for
the Phase 4 section skeleton and practical contrasts). Thirteen methodology
skills: `python-environment`, `stan` (with `references/ode.md` and
`references/horseshoe.md`), `generative-model-design` (lean index +
`references/` for spec sections, design principles, and the resolution-sequence
pattern), `analysis-design`, `fake-data-simulation` (`references/single-draw.md`,
`references/sbc.md`, `references/decision.md`), `convergence-diagnostics`,
`inferencedata-handling`, `visual-predictive-checks`,
`bayesian-model-diagnostics`, `bayesian-model-selection`, `model-critique`
(index + `references/` for statistical, domain, and framework assessment),
`eda` (`references/process/` for EDA procedures, `references/tests/` for a
diagnostic test library by data shape), and `artifact-guidelines`
(`references/html-report.md`, `references/markdown-report.md`, figure
conventions). Agents load the skills relevant to their role; skills are not
user-invocable directly — use the commands above.

**Bundled library** — `shared_utils`, a Python package with a fit-and-summarize
pipeline, convergence diagnostics, LOO, and ArviZ helpers. The setup command
copies it into the working project as a path dependency.

## Testing

Workflows on this scale are expensive to run end-to-end, so the seams are built
for partial runs: `agentBodies` for prompt iteration without a plugin reload,
`model` to run the pipeline on a cheaper tier, and `report.js`'s `stopAfter`
for stage-isolated report runs. The dispatch seam (`call()`) converts
agent-level failures (a subagent finishing without structured output THROWS
from `agent()`) into the uniform "lost" signal so retry/resubmit machinery
engages instead of a lifecycle dying.

The pipeline was validated end-to-end against `ck63g`, a completed run of the
earlier single-script design: explore/design reproduced that run's framing
independently on sonnet; the report pipeline produced a measurably better
report than the single-shot writer (298- vs 589-word executive summary, zero
dangling promises, three blocking factual errors caught by the critic against
the fact sheet); the develop smoke run exercised the stage contracts, audited
numerics, and crash recovery on a real Stan fit.

## History

The first version of this plugin drove all four phases from orchestrator
prose, with a single Workflow script (`validate-experiments.js`) running one
Phase 3 round at a time and the orchestrator judging between rounds. The
script-led design was rebuilt from scratch on a separate branch, validated
against a completed run of the first version, and consolidated back into this
repository. The thirteen methodology skills and `shared_utils` carried over
unchanged — the rebuild targeted the workflow architecture, not the statistical
methodology. See `CHANGELOG.md`.

## License

MIT — see [LICENSE](LICENSE).
