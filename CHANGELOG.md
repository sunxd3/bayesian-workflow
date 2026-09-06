# Changelog

Notable changes to this plugin. It is distributed via git without an explicit
`version` in `plugin.json`, so marketplace users receive each pushed commit as
an update; the milestones below summarize the significant changes.

## Unreleased

### Added
- **`report-writing` skill** — the report quality bar (skim test, narrative
  arc, density rule, figure discipline, detail tiers, mechanical hygiene)
  promoted from an `artifact-guidelines` reference file to its own skill,
  with `references/final-report.md` (section skeleton, practical contrasts)
  moved in alongside. All five report agents (planner, quant, section-writer,
  assembler, critic) link it in their frontmatter and cite its rules by name;
  `artifact-guidelines` keeps the cross-phase format conventions (HTML/
  Markdown formats, figure files, file minimalism).
- **Standalone plugin** — moved out of
  [`sunxd3/bayesian-statistician-plugin`](https://github.com/sunxd3/bayesian-statistician-plugin)
  (archived), where this codebase lived as `v2/`, and renamed
  `bayesian-workflow-v2` → `bayesian-workflow` (commands are now
  `/bayesian-workflow:setup|run|eda`).
- **The workflow itself** — a from-scratch, script-led rebuild of the
  predecessor plugin. Deterministic control flow lives in four Workflow
  scripts (`explore.js`, `design.js`, `develop.js`, `report.js`) with judgment
  as schema-constrained agent calls inside the loops; 18 agents; a
  machine-readable question ledger with a score plateau guard;
  verdict-vs-numbers audits at every gate stage; and report writing as a
  five-role pipeline (planner → quant/fact-sheet → parallel section writers →
  assembler → cold-read critic with a revision loop) with the shared quality
  bar in the `report-writing` skill. Validated
  end-to-end against a real study on sonnet subagents; see `README.md`.
- **Audit fixes** from an independent adversarial review of the test-run
  artifacts (22/22 recomputed claims reproduced; the defects were in the
  frame, not the numbers):
  - *Ranking metric is plan-declared, not hardcoded.* The planner names the
    comparison metric implementing its validation strategy
    (`plan.ranking_metric`); `develop.js` hardcodes only the shape
    (`{metric, score, score_se}`) and audits the echoed metric name — a score
    computed under a different metric is excluded from trajectories and
    ranking, with the fitter's own `metric_note` reason logged (deviation must
    be argued, never silent). Previously observation-level `elpd_loo` was
    baked into the ledger, plateau rule, and selection even when the plan
    forbade it for ranking (e.g. LOPO for grouped data). The fitter computes
    the assigned metric (writing `ranking_score.json` when it is not plain
    LOO) and the selector ranks on it.
  - *Dataset provenance is machine-recorded.* `data_path` joins the
    status.json contract, the prior/fit gate schemas, and the ledger; a fit
    PASS reporting a different dataset than dispatched is demoted to FAIL,
    the completed-work short-circuit rejects records from other datasets, and
    the selector excludes cross-dataset comparisons. (Found when a full-data
    and a subsample experiment sat side by side with incomparable ELPDs and
    no machine-readable trace of which data each used.)
  - *Question cap is visible to the planner.* The planner is told
    `max_questions` up front and ranks questions by value; over-cap questions
    are returned as `deferred_questions` (persisted in the ledger, offered at
    Gate 2) and the synthesist must reconcile the plan text against what was
    actually dispatched. Previously the cap silently orphaned the plan's
    fourth question while its success criteria still referenced it.
  - *Prior-predictive bounds are assigned, not self-chosen.* The plan declares
    outcome plausibility bounds (`plan.plausibility_bounds`); the checker's
    audited `extreme_draw_pct` is computed against them, so the >10% audit
    flag can actually fire.
  - *Strategist round records carry an as-of header* (timestamp + observed
    evidence state) so records don't silently go stale as detached fits land.
  - *Designers and the planner get a robustness nudge*: EDA kurtosis/outlier
    flags now argue explicitly for Student-t-style likelihood variants.
