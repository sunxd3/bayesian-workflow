---
description: Run exploratory data analysis standalone — profile, parallel analysts, synthesized report — without the full modeling pipeline.
argument-hint: "<data_path> [output_dir] [--focus=<area>]"
allowed-tools: Workflow, Agent, Bash, Read, Write
---

Run Phase 1 of the Bayesian workflow standalone via the bundled script:

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

Resolve `data_path` to an absolute path first; if it does not exist, say so and stop. When the run completes, present the synthesis: report location, structural hypotheses, modeling implications, and data quality flags.

If the Workflow tool is unavailable, dispatch a single `bayesian-workflow:eda-analyst` Agent directly with `data_path`, `output_dir`, and the focus area (default: "data quality, distributions, and variable relationships"), then present its findings.

## User input

$ARGUMENTS
