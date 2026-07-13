---
name: report-writing
description: The writing quality bar for the final report — skim test, narrative arc, number density, figure discipline, detail tiers, and mechanical hygiene. Loaded by the report-writer agent; audit your draft against these rules before delivering.
user-invocable: false
---

# Report Writing — the quality bar for the final report

`artifact-guidelines > references/final-report` defines the section skeleton
and the practical-contrasts procedure; `references/html-report` the visual
format. This skill defines what makes the writing *good*. Before delivering,
re-read your draft against these rules by name — they are what a cold reader
notices.

## The skim test (the master rule)

Title + section headings + figures with captions + the first sentence of every
section must carry the complete argument on their own. A reader who skims
exactly that should walk away knowing what was found, how strongly, and what
to be careful about. Everything else is elaboration for readers who slow down.

Corollaries:
- Headings state findings, not topics ("The noise is multiplicative on the
  command", not "Noise analysis").
- Every section's first sentence is its conclusion.
- The figure sequence, read alone in order, tells the story: phenomenon →
  evidence per question → mechanism → validation.

## Narrative arc

Phenomenon → question → answer → mechanism → caveats. At every level — report,
section, paragraph — lead with the answer.

- **Show the phenomenon before the model.** The reader must SEE the raw effect
  in the data (an EDA-grade figure) before any model is mentioned. A report
  that opens with model structure is answering a question the reader hasn't
  been made to ask.
- Chronology is for the lab notebook. The reader gets the logical order, not
  the discovery order — except when the discovery story *is* the finding
  (a surprise that redirected the analysis earns a short narrative).

## Density — one load-bearing number per paragraph

Each paragraph advances ONE claim and carries THE number (with uncertainty)
that supports it. Supporting statistics go to a table or the supplementary
tier.

- Hard rule: more than 3 intervals in one paragraph → restructure (split, or
  move numbers to a table).
- Numbers on the original scale where possible; as comparisons, not bare values
  ("+140.6 ± 31.5 over the constant-CV model", never "ELPD −12,304").
- Consistent precision (2–3 significant figures); one convention for intervals
  throughout.
- **Every number traces to a source artifact** (`loo.json`, `summary.json`, a
  stage report, your contrast script's output). Quote values from files, never
  from memory; a number you cannot source does not go in the report.

## Rhythm — don't run a template

Identical section shapes read as machine output. Vary the entry: one section
can open with the figure, another with the contrast that settles it, another
with the anomaly that motivated it. Labels like "Hypothesis." repeated in
every section are outline scaffolding — remove them and let prose carry the
structure. Sentence length should vary; three long compound sentences in a
row is a signal to cut.

## Figures — each earns its place

- One idea per figure. If a sentence can carry the point, no figure.
- The caption states the takeaway ("Participants under-weight the penalty
  ~3.5×"), not the contents ("Posterior distribution of w"). What-to-notice
  belongs in the caption; how-it-was-made belongs in supplementary.
- Every figure is referenced from the text at the exact point of argument, and
  appears adjacent to that point.
- Do not repeat the caption's numbers verbatim in the body text — text argues,
  caption anchors.

## Detail tiers — push down, don't delete

| Tier | Reader | Rules |
|---|---|---|
| Executive summary | anyone | ≤ 300 words; no jargon, no experiment ids, no metric names; findings with plain-language uncertainty |
| Results | domain expert | numbers with uncertainty; minimal method; one caveat sentence where load-bearing |
| Methods / Validation | statistician | enough to trust, not to reproduce line-by-line |
| Supplementary | reproducer | everything else: full spec, diagnostics, population, file paths |

When a section overflows its budget, move detail down a tier rather than
cutting it.

## Hygiene (mechanical — check these literally in your self-audit)

- **No dangling promises.** Every "the table below", "the full specification:",
  "see Figure N" must resolve to content that actually exists, adjacent to the
  reference.
- **Experiment ids are bookkeeping.** Call models by what they claim ("the
  risk-sensitive model"), give the id once in parentheses at first mention,
  and keep the id-to-model map in supplementary.
- **Define before use.** Every acronym/metric defined at first occurrence;
  metric caveats stated once, in one place, and referenced elsewhere.
- **Honesty is structure.** Caveats and informative negative results get their
  own place in the arc — not an apologetic afterthought, not scattered hedges.

## Self-audit before delivering

You have no external critic; be your own. After composing the draft: (1) run
the skim test literally — read only headings, captions, and first sentences,
and write down the story they tell; if it differs from the full report's story
or has holes, fix the skeleton, not the prose; (2) check every hygiene rule
above; (3) recheck three numbers at random against their source files. Only
then write the final file.
