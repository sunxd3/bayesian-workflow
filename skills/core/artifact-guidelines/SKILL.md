---
name: artifact-guidelines
description: Style and format conventions for subagent artifacts — reports, logs, figures.
user-invocable: false
---

# Artifact Guidelines

This skill defines the **form** of artifacts subagents produce.
For *what* to write, see the relevant methodology skill.
For *which folder*, see `orchestration > Canonical Structure`.

## Format choice

- **Final reports.** Any phase deliverable — EDA, critique, posterior predictive,
  population assessment, final synthesis — uses HTML. See `references/html-report.md`.
- **Logs and intermediate notes.** `log.md`, README notes, working scratch — use
  Markdown. See `references/markdown-report.md`.
- Never use plain `.txt`.

## Figure conventions

- Use descriptive filenames (`group_washout_curves.png`, not `fig1.png`).
- One concept per figure; multi-panel only when the comparison demands it (max 2×2).
- Save next to the report that cites them; reference via relative path in `<img src>`.
- 300 DPI for report figures, 150 DPI for exploratory plots.

## File minimalism

Generate fewer, better files:

- One Stan model per `.stan` file.
- One logical step per Python script (compile, fit, diagnose, plot), not one
  monolithic analysis. See `python-environment > Script Structure`.
- Use descriptive script names (`fit_hierarchical_model.py`, not `model.py`).
- One consolidated report per phase, not ten partial analyses.
- Combine related visualisations into multi-panel figures when comparison is
  the point.
- Remove intermediate scratch after consolidating insights into the report.

Every file you create should justify its existence: will this be read? Does it
convey unique information?
