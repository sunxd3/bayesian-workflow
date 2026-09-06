# Changelog

Notable changes to this plugin. It is distributed via git without an explicit
`version` in `plugin.json`, so marketplace users receive each pushed commit as
an update; the milestones below summarize the significant changes.

## Unreleased

### Changed
- **Script-led workflow.** The from-scratch, script-led rebuild that was
  developed on the `dynamic-workflow` branch is now the main line.
  Deterministic control flow lives in four Workflow scripts (`explore.js`,
  `design.js`, `develop.js`, `report.js`) with judgment as schema-constrained
  agent calls inside the loops; 18 agents; a machine-readable question ledger
  with a score plateau guard; verdict-vs-numbers audits at every gate stage;
  and report writing as a five-role pipeline (planner → quant/fact-sheet →
  parallel section writers → assembler → cold-read critic with a revision
  loop). The `orchestration` skill shrinks to a thin phase driver that holds
  the two user gates (goal confirmation after EDA, plan approval after
  design), persists `design/ledger.json` and `experiments/ledger.json`, and
  keeps the lab notebook. Validated end-to-end against a real study on sonnet
  subagents; see `README.md`.
- **`report-writing` skill** — the report quality bar (skim test, narrative
  arc, density rule, figure discipline, detail tiers, mechanical hygiene)
  promoted from an `artifact-guidelines` reference file to its own skill,
  with `references/final-report.md` (section skeleton, practical contrasts)
  moved in alongside. All five report agents (planner, quant, section-writer,
  assembler, critic) link it in their frontmatter and cite its rules by name;
  the report-critic audits against it, so the single-writer self-audit is
  gone. `artifact-guidelines` keeps the cross-phase format conventions (HTML/
  Markdown formats, figure files, file minimalism).
- Between-round judgment moved from orchestrator prose into the `strategist`
  agent, dispatched once per round inside `develop.js` and filtered through
  deterministic guards (explore budgets, plateau rule, new-question slots,
  experiment caps). `critique` became `critic` — statistical + domain
  assessment per experiment, recording `surprises` — with framework
  questioning now the strategist's job. `model-selector` rules only on the
  finished population (ADEQUATE/EXHAUSTED + coverage audit); round-to-round
  decisions are no longer its concern.
- Phase 1 is a fan-out: a `data-profiler` returns dataset facts, `explore.js`
  sizes the analyst pool from them, each `eda-analyst` works one focus area
  and writes `findings.md`, and a `synthesist` merges the findings into
  `eda_report.html`. The analyst that owns the canonical deliverables still
  writes `data.cleaned.parquet` (after the `eda > standardization` step) and
  the summary CSVs. In `design` mode the same `synthesist` deduplicates
  designer proposals into the final experiment table.
- `validation-protocol` gains a **Structured returns** section: one
  structured-output call as the final action, audited numeric fields per gate
  stage with thresholds (`extreme_draw_pct`, `coverage_90`, `max_bias_z`,
  R̂/ESS/divergences/score, `pareto_k_bad_pct`), `data_path` provenance in
  every `status.json`, and cache hits returned as `from_cache: true`. Agents
  declare whether they run the full protocol or Steps 1–2 only.
- `prior-predictive-checker` authors `model.stan` from the plan's `spec` when
  absent and measures `extreme_draw_pct` against bounds the plan assigns; it
  may still tune priors within the spec's structure (updating `model.stan`
  and `prior_model.stan` together) before FAILing.
- `model-fitter` computes the plan's ranking metric (`ranking_score.json` when
  it is not observation-level LOO) and records `data_path`; `analysis-planner`
  declares the ranking metric, plausibility bounds, and value-ranked
  questions with a `max_questions` cap.
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
    forbade it for ranking (e.g. LOPO for grouped data).
  - *Dataset provenance is machine-recorded.* `data_path` joins the
    status.json contract, the prior/fit gate schemas, and the ledger; a fit
    PASS reporting a different dataset than dispatched is demoted to FAIL,
    the completed-work short-circuit rejects records from other datasets, and
    the selector excludes cross-dataset comparisons.
  - *Question cap is visible to the planner.* The planner is told
    `max_questions` up front and ranks questions by value; over-cap questions
    are returned as `deferred_questions` (persisted in the ledger, offered at
    Gate 2) and the synthesist must reconcile the plan text against what was
    actually dispatched.
  - *Prior-predictive bounds are assigned, not self-chosen.* The plan declares
    outcome plausibility bounds (`plan.plausibility_bounds`); the checker's
    audited `extreme_draw_pct` is computed against them, so the >10% audit
    flag can actually fire.
  - *Strategist round records carry an as-of header* (timestamp + observed
    evidence state) so records don't silently go stale as detached fits land.
  - *Designers and the planner get a robustness nudge*: EDA kurtosis/outlier
    flags now argue explicitly for Student-t-style likelihood variants.
- `/bayesian-workflow:run` gained `AskUserQuestion` for the gates;
  `/bayesian-workflow:eda` now runs `explore.js` (with a single-analyst +
  synthesist fallback when the Workflow tool is unavailable).

### Added
- **`fit-pipeline` skill** — the artifact contract for the fit stages
  (`summary.json`, `diagnostics.json`, `loo.json`, `thinned_draws.npz`,
  `posterior.nc`; `prior_check.json`; `recovery.json`) plus three runnable
  reference scripts agents copy and adapt instead of importing a library:
  `posterior_fit.py` (probe or full NUTS run → artifacts), `prior_predictive.py`
  (GQ-only prior simulation; `--bounds` → the audited `extreme_draw_pct`), and
  `fake_data.py` (`simulate` one fake dataset; `check` → the audited
  `coverage_90` and `max_bias_z`). The scripts encode the operational rules the
  old library carried: quiet sampling, no `adapt_delta` on `fixed_param` runs,
  explicit InferenceData groups from `fit.metadata.stan_vars`,
  `az.summary`-based convergence (no `diagnose()` OOM), CSV cleanup, numpy-safe
  JSON.
- **Real-CmdStan test suite for the reference scripts** (`tests/`, marker
  `integration`): six small Stan programs are compiled and sampled; the tests
  pin the artifact file set and JSON layouts, cross-file consistency, parameter
  recovery, posterior-predictive coverage, that Neal's funnel is flagged as
  divergent, that LOO ranks a Student-t likelihood above a normal one on
  heavy-tailed data by more than 2 SE of the paired difference, the prior and
  recovery numbers, and each CLI as an agent would invoke it. A pure tier on
  synthetic InferenceData covers the decision logic and the contract without
  CmdStan. With `SHARED_UTILS_REQUIRE_CMDSTAN=1` a missing toolchain fails
  instead of skipping.
- **CI** has six jobs: manifest validation, workflow-script parse check, ruff +
  pyright over the reference scripts and tests, the pure tier on Python 3.10
  and 3.13, and the integration tier with CmdStan (pinned, cached) and cached
  compiled test models.

### Removed
- **`shared_utils`**, the bundled Python library, and the setup step that
  copied it into projects. Its only original code was the fit-and-summarize
  artifact contract and CSV cleanup; everything else was a thin wrapper over
  ArviZ and CmdStanPy. Writing the suite above against it surfaced two bugs
  (`adapt_delta` forwarded with adaptation off, so every GQ-only recipe failed
  on CmdStanPy 1.3; variable names never detected on CmdStanPy ≥ 1.2, so any
  model without `y_rep` crashed conversion) — the reference scripts encode the
  fixes. `/bayesian-workflow:setup` now only writes `pyproject.toml`, syncs,
  and installs CmdStan; `python-environment` documents conventions and points
  at `fit-pipeline` for execution.
- `workflows/validate-experiments.js` (one Phase 3 round per call) —
  superseded by `develop.js`, which contains the same per-experiment
  lifecycle plus the multi-round loop.
- `critique` and `report-writer` agents — replaced by `critic` and the
  five-agent report pipeline.
- The manual task-pool fallback protocol in the orchestration skill —
  replaced by a shorter degraded-mode section at the same file contracts.

*Earlier in this cycle, before the script-led rebuild:*

### Added
- Bundled Workflow script `workflows/validate-experiments.js` — Phase 3 ran as
  deterministic **validation rounds**: the script enforced stage sequencing
  (prior → recovery → fit → ppc → critique), the two-refine FIX budget, MCMC
  concurrency throttling, and a verdict-vs-numbers audit on fit results,
  while the orchestrator kept all judgment calls (EXPLORE refinement, new
  structural questions, selection) between rounds. `/bayesian-workflow:run`
  gained `Workflow` in its allowed tools.
- `status.json` completion records — every pipeline stage agent writes a
  machine-readable record (verdict, key numbers, artifact list) as its last
  file, and short-circuits on re-dispatch when a terminal record with intact
  artifacts already exists ("Step 3 — Completed-work check" and "On
  completion" sections in the `validation-protocol` skill). Interrupted or
  re-run rounds recover in seconds instead of re-running MCMC, and the
  mechanism works across sessions because it is file-based.
- `/bayesian-workflow:setup` command — one-time bootstrap for the Python
  environment (copies `shared_utils`, creates `pyproject.toml`, runs `uv sync`
  and `cmdstanpy.install_cmdstan`).
- Reports (any phase's final deliverable) are HTML instead of Markdown.
  EDA emits `eda_report.html`; the canonical project structure expects
  `final_report.html`. The editorial-magazine design (light theme,
  Fraunces + Source Sans 3 + JetBrains Mono, embedded plot figures,
  full skeleton template) lives in
  `artifact-guidelines > references/html-report.md` so any agent that
  produces a report can use it. Markdown is still used for logs and
  intermediate notes; conventions live in
  `artifact-guidelines > references/markdown-report.md`.
- `/bayesian-workflow:eda <data_path> [output_dir] [--focus=<area>]` command —
  run EDA standalone, without the full workflow pipeline.
- `validation-protocol` skill — the shared two-step input-validation
  protocol used by every subagent (argument check, filesystem check,
  single-line `[EXCEPTION]` output on failure). Each agent's `Input
  Validation` section declares only its specific args and filesystem
  checks, eliminating the boilerplate that had drifted across agents.
- `statistical-diagnostics` split into per-shape references
  (`references/{distribution,regression,time-series,count,missing-and-hierarchical}.md`).
  SKILL.md trimmed to a pointer index plus the thresholds table, so the
  EDA analyst preloads ~28 lines instead of ~119 and reads relevant
  references on demand.
- `statistical-diagnostics` renamed and expanded to `eda`. The new skill
  consolidates EDA process content (data semantics audit, data quality
  checks, standardization, timestamp handling, visualization, modeling
  handoff) with the existing diagnostic-test library under
  `references/process/` and `references/tests/`. `eda-analyst`'s body
  slimmed to role, interface, procedure with pointers, and principles; the
  bulk of operational detail lives in the skill and is read on demand.

### Changed
- Renamed agent `recovery-checker` → `fake-data-checker` to match Gelman's
  canonical "fake-data simulation" vocabulary, with methodology extracted
  into a new `fake-data-simulation` skill (`references/single-draw.md` for
  the cheap pre-fit check, `references/sbc.md` for the rigorous
  Simulation-Based Calibration variant per Talts et al. 2018,
  `references/decision.md` for PASS/FAIL criteria).
- Renamed plugin from `bayesian-statistician` to `bayesian-workflow` —
  matches the canonical name of the methodology (Gelman et al., 2020).
  Install command is `/plugin install bayesian-workflow@sunxd3-plugins`.
- Renamed orchestrator skill `bayesian-workflow` to `run`, later split into
  the `/bayesian-workflow:run` command plus the `orchestration` skill.
- `python-environment` skill trimmed to reference-only content
  (`shared_utils` API, script structure). Setup steps moved to the new
  `setup` command. The bundled `shared_utils/` library lives at the plugin
  root and is referenced via `${CLAUDE_PLUGIN_ROOT}/shared_utils`.
- Consolidated Stan skills via progressive disclosure: `stan-coding`
  renamed to `stan`; `stan-ode-modeler` and `horseshoe-prior` folded in
  as `skills/stan/references/ode.md` and `skills/stan/references/horseshoe.md`.
  Subagent skill lists updated. Net: 12 modeling skills → 10, with the
  previously-orphaned ODE and horseshoe guides now discoverable from the
  umbrella `stan` skill.

## 0.2.0 — 2026-05-21

Full sync with the upstream `bayesian-statistician` agent.

### Added
- Six skills: `bayesian-model-diagnostics`, `bayesian-model-selection`,
  `generative-model-design`, `horseshoe-prior`, `inferencedata-handling`,
  `statistical-diagnostics`.
- `critique` agent — a single integrated review covering statistical health,
  domain validity, and framework appropriateness.

### Changed
- All 9 carried-over subagents (`eda-analyst`, `model-designer`, `model-fitter`,
  `model-refiner`, `model-selector`, `posterior-predictive-checker`,
  `prior-predictive-checker`, `recovery-checker`, `report-writer`) updated to
  upstream parity.
- `bayesian-workflow` orchestrator skill updated: structural-question-driven
  search loop, per-experiment/per-stage task pool, discovery-driven questions.
- `stan-coding`, `visual-predictive-checks`, `artifact-guidelines`,
  `convergence-diagnostics` skills updated to upstream parity.
- Bundled `shared_utils` replaced with the current package, which adds the
  `fit_and_summarize` / `FitResult` pipeline, `to_arviz_prior`, `NumpyEncoder`,
  and `cleanup_csv_files`.
- `python-environment` skill rewritten with a concrete, plugin-local setup
  flow (no sandbox-specific paths).
- `plugin.json` gains `$schema`, `displayName`, `keywords`, and `homepage`.

### Removed
- `model-critique` and `decision-auditor` agents — folded into `critique` and
  `model-selector` respectively.
- Plugin hooks — the skills already instruct `uv`-only execution.

## 0.1.0

- Initial release: orchestrator skill, subagents, and core Stan/ArviZ skills.
