---
description: Run exploratory data analysis standalone — profile, parallel analysts, synthesized report — without the full modeling pipeline.
argument-hint: "<data_path> [output_dir] [--focus=<area>]"
allowed-tools: Workflow, Agent, Bash, Read, Write
---

Run Phase 1 of the Bayesian workflow standalone via the bundled script.

## Parse arguments

From `$ARGUMENTS`, extract:
- `data_path` (required, first positional) — path to the dataset (CSV, JSON, Parquet)
- `output_dir` (optional, second positional; default `eda/`) — directory to write outputs into
- `focus_area` (optional, `--focus=<area>` or trailing prose) — aspect of the data to emphasize

Resolve `data_path` to an absolute path; if `$ARGUMENTS` is empty, `data_path` cannot be identified, or the file does not exist, say so and stop.

## Verify environment

Use Bash to check that `./pyproject.toml` exists in the current working directory. If it is missing, tell the user to run `/bayesian-workflow:setup` first and stop.

## Run explore.js

```
Workflow({
  scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/explore.js",
  args: {
    projectDir: "<absolute working directory>",
    dataPath: "<absolute path to the data file>",
    edaDir: "<absolute output_dir, if the user gave one>",
    focusAreas: ["<focus>"],   // only when --focus given: pins a single analyst to it
  }
})
```

If the Workflow tool is unavailable, dispatch a single `bayesian-workflow:eda-analyst` Agent with `data_path`, `output_dir: <output_dir>/analyst_1`, the focus area (default: "data quality, distributions, and variable relationships"), and ownership of the canonical deliverables (`<output_dir>/data.cleaned.parquet`, `quality_summary.csv`, `univariate_summary.csv`); then dispatch `bayesian-workflow:synthesist` in mode `eda` with `inputs: [<output_dir>/analyst_1/findings.md]`, `output_path: <output_dir>/eda_report.html`, `data_path`, and `goal` (or `goal: NOT SUPPLIED — propose one in suggested_goal`).

## Present results

When the run completes, present the synthesis: structural hypotheses, modeling implications, and data quality flags. Point the user at:
- `<output_dir>/eda_report.html` — full narrative report (open in a browser)
- `<output_dir>/data.cleaned.parquet` — canonical standardized dataset (what `/bayesian-workflow:run` models in later phases)
- `<output_dir>/analyst_N/findings.md` and `log.md` — per-analyst findings and running trace

## User input

$ARGUMENTS
