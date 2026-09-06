# Markdown Format

Use Markdown (GitHub-flavored CommonMark) for artifacts that are **append-only, machine-friendly, or intermediate** rather than final shareable deliverables. See `html-report.md` for final reports.

## When to use Markdown

- **`log.md`.** Append-only running notebook, one entry per major workflow step. Append entries live as work proceeds; do not batch.
- **README-style notes.** Alongside data or experiments (`experiments/exp_X/README.md`). Short context for a future reader.
- **Inline working notes.** Short documents that document a decision or trade-off where rendering in a browser would be overkill.

Do not use Markdown for the final report of any phase. Reports use HTML (see `html-report.md`).

## Markdown conventions

- Short paragraphs with complete sentences.
- Favor insight over exhaustiveness.
- Lists sparingly, only when they genuinely clarify (e.g., model assumptions, validation criteria).
- Minimal headers and bold; no excessive formatting.

In logs:
- Capture decisions and reasoning, not play-by-play execution.
- Record why you chose certain paths or skipped alternatives.
- Note failures and how you addressed them.

## Log entry format

```markdown
## <UTC timestamp> — <agent-name>: <action>

Short paragraph or bullet list of what was done, what was found, and any
decision that affects later steps. Reference produced files by relative
path. Do not paste long output; cite the file that contains it.
```

Example:

```markdown
## 2026-05-25T12:52:00Z — eda-analyst: semantic audit + standardization complete

Scientific domain: psychophysics / pain learning (Onysk et al. 2024). Condition
codes decompose into volatility × signal_strength factors. Wrote
`data.cleaned.parquet` with 14 columns. Two issues flagged: trial-type
sequence non-alternation (1–49 same-type pairs per cell) and 1–2 trimmed
trials per cell.
```

UTC timestamps. Action is a short verb phrase that survives reordering. The entry stands on its own; a later reader should not need to reconstruct context.
