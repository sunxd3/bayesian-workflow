# Changelog

Notable changes to this plugin. It is distributed via git without an explicit
`version` in `plugin.json`, so marketplace users receive each pushed commit as
an update; the milestones below summarize the significant changes.

## Unreleased

### Moved
- The from-scratch, script-led rebuild that briefly lived here as `v2/` is now
  its own plugin and repository:
  [`sunxd3/bayesian-workflow`](https://github.com/sunxd3/bayesian-workflow).
  This repository is archived; new development (research agent, knowledge
  store / world model) happens there.

### Added
- **`report-writing` skill** — the writing quality bar for the final report
  (skim test, narrative arc, one-load-bearing-number density rule, figure
  discipline, detail tiers, mechanical hygiene, and a mandatory self-audit),
  linked by the `report-writer` agent alongside the existing
  `artifact-guidelines` format references. Backported from the successor
  plugin's report pipeline, adapted for a single writer with no external
  critic: every number must trace to a source artifact, and the writer runs
  the skim test on its own draft before delivering.
- Bundled Workflow script `workflows/validate-experiments.js` — Phase 3 now
  runs as deterministic **validation rounds**: the script enforces stage
  sequencing (prior → recovery → fit → ppc → critique), the two-refine FIX
  budget, MCMC concurrency throttling, and a verdict-vs-numbers audit on
  fit results, while the orchestrator keeps all judgment calls (EXPLORE
  refinement, new structural questions, selection) between rounds. The
  orchestration skill documents the round protocol and retains the manual
  task-pool protocol as a fallback for harnesses without the Workflow tool.
  `/bayesian-workflow:run` gained `Workflow` in its allowed tools.
- `status.json` completion records — every pipeline stage agent now writes
  a machine-readable record (verdict, key numbers, artifact list) as its
  last file, and short-circuits on re-dispatch when a terminal record with
  intact artifacts already exists (new "Step 3 — Completed-work check" and
  "On completion" sections in the `validation-protocol` skill). Interrupted
  or re-run rounds recover in seconds instead of re-running MCMC, and the
  mechanism works across sessions because it is file-based.

### Changed
- Renamed agent `recovery-checker` → `fake-data-checker` to match Gelman's
  canonical "fake-data simulation" vocabulary. Restructured the agent body
  to the new Interface (Input / Returns / Side effects) + pseudocode
  pattern, with methodology extracted into a new `fake-data-simulation`
  skill (`references/single-draw.md` for the cheap pre-fit check,
  `references/sbc.md` for the rigorous Simulation-Based Calibration
  variant per Talts et al. 2018, `references/decision.md` for PASS/FAIL
  criteria).

### Added
- `/bayesian-workflow:setup` command — one-time bootstrap for the Python
  environment (copies `shared_utils`, creates `pyproject.toml`, runs `uv sync`
  and `cmdstanpy.install_cmdstan`).
- Reports (any phase's final deliverable) are now HTML instead of Markdown.
  EDA emits `eda_report.html`; canonical project structure now expects
  `final_report.html`. The editorial-magazine design (light theme,
  Fraunces + Source Sans 3 + JetBrains Mono, embedded plot figures,
  full skeleton template) lives in
  `artifact-guidelines > references/html-report.md` so any agent that
  produces a report can use it. Markdown is still used for logs and
  intermediate notes; conventions live in
  `artifact-guidelines > references/markdown-report.md`.
  Dependent agents (`model-designer`, `report-writer`) and the `run`
  orchestrator updated to reference the new filenames.
- `/bayesian-workflow:eda <data_path> [output_dir] [--focus=<area>]` command —
  run EDA standalone, without the full workflow pipeline. Wraps the
  `eda-analyst` subagent so it can be invoked directly by the user.
- `validation-protocol` skill — the shared two-step input-validation
  protocol used by every subagent (argument check, filesystem check,
  single-line `[EXCEPTION]` output on failure). Each agent's `Input
  Validation` section now declares only its specific args and filesystem
  checks, eliminating the boilerplate that had drifted across agents.
- `statistical-diagnostics` split into per-shape references
  (`references/{distribution,regression,time-series,count,missing-and-hierarchical}.md`).
  SKILL.md trimmed to a pointer index plus the thresholds table, so the
  EDA analyst preloads ~28 lines instead of ~119 and reads relevant
  references on demand.
- `statistical-diagnostics` renamed and expanded to `eda`. The new skill
  consolidates EDA process content (data semantics audit, data quality
  checks, timestamp handling, visualization, modeling handoff) with the
  existing diagnostic-test library under `references/process/` and
  `references/tests/`. `eda-analyst`'s body slimmed from ~179 lines to
  ~55: role, interface, 8-step procedure with pointers, and the agent's
  principles. The bulk of operational detail now lives in the skill and
  is read on demand.

### Changed
- Renamed plugin from `bayesian-statistician` to `bayesian-workflow` —
  matches the canonical name of the methodology (Gelman et al., 2020).
  Install command is now `/plugin install bayesian-workflow@sunxd3-plugins`.
- Renamed orchestrator skill `bayesian-workflow` to `run`. Invoke as
  `/bayesian-workflow:run`.
- `python-environment` skill trimmed to reference-only content
  (`shared_utils` API, script structure). Setup steps moved to the new
  `setup` command. The bundled `shared_utils/` library now lives at the
  plugin root and is referenced via `${CLAUDE_PLUGIN_ROOT}/shared_utils`.
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
