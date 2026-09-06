// Phase 4 — Report writing as a pipeline: plan → evidence → parallel section
// drafts → assemble → review loop.
//
// The writing is the deliverable, so the pipeline mirrors how a good writing
// team works: a narrative architect decides the story and what to omit; an
// evidence compiler builds the fact sheet (the wall against hallucinated
// numbers) and the figure set; section writers draft in parallel from briefs;
// an assembler makes one voice and writes the executive summary LAST; a critic
// cold-reads and audits, and the assembler revises until SHIP or the revision
// budget is spent.
//
// Deterministic logic owned here: stage sequencing, section/figure/word/
// revision budgets, writer retry-once, figures-used ⊆ manifest check,
// missing-fact propagation, and the review loop. Judgment (story, prose,
// verdicts) is entirely in the agents.
//
// Invoked by the orchestrator (see the `orchestration` skill) as:
//
//   Workflow({
//     scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/report.js",
//     args: {
//       projectDir: "/abs/path",
//       reportDir: "...",            // default: <projectDir>/report
//       outputPath: "...",           // default: <reportDir>/final_report.html
//       edaDir, experimentsDir, assessmentPath, planPath, ledgerPath, logPath,
//       selectedModelDir, dataPath,  // optional; contrasts need selectedModelDir
//       audience: "...",             // default below
//       limits: { maxSections: 8, figureBudget: 12, maxWords: 3500, maxRevisions: 2 },
//       // --- modular testing knobs ---
//       model: "sonnet",             // per-agent model override (default: inherit session)
//       stopAfter: "plan" | "facts" | "draft" | "assemble",   // run partially
//       outline: {...},              // skip Plan: reuse a previous run's outline
//       facts: {...},                // skip Evidence: reuse {facts_path, figures}
//     },
//   })
//
// Modular testing: run with stopAfter to inspect a stage's product (each stage
// also writes its product as a file under reportDir), then either feed the
// returned object back via outline/facts, or re-run with resumeFromRunId to
// replay completed agent calls from the journal.

export const meta = {
  name: 'write-report',
  description: 'Phase 4: multi-agent report writing — plan, fact sheet + figures, parallel section drafts, assembly, critic review loop',
  whenToUse: 'Dispatched by the bayesian-workflow orchestrator after selection, or standalone on any completed analysis project. Supports stopAfter/outline/facts args for modular runs.',
  phases: [
    { title: 'Plan', detail: 'narrative architecture: headline, section briefs, figure story, omissions' },
    { title: 'Evidence', detail: 'practical contrasts, fact sheet, report-quality figure set' },
    { title: 'Draft', detail: 'one writer per section, in parallel' },
    { title: 'Assemble', detail: 'one voice, transitions, executive summary last' },
    { title: 'Review', detail: 'cold-read critic → assembler revisions, until SHIP' },
  ],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
if (!A || !A.projectDir) {
  throw new Error('args must be {projectDir, reportDir?, outputPath?, edaDir?, experimentsDir?, assessmentPath?, planPath?, ledgerPath?, logPath?, selectedModelDir?, dataPath?, audience?, limits?, model?, stopAfter?, outline?, facts?}')
}
const P = A.projectDir
const REPORT = A.reportDir || `${P}/report`
const OUT = A.outputPath || `${REPORT}/final_report.html`
const EDA = A.edaDir || `${P}/eda`
const EXPS = A.experimentsDir || `${P}/experiments`
const ASSESS = A.assessmentPath || `${EXPS}/population_assessment.html`
const PLANMD = A.planPath || `${P}/design/experiment_plan.md`
const AUDIENCE = A.audience || 'domain experts who did not watch the analysis, reviewed by statisticians'
const L = { maxSections: 8, figureBudget: 12, maxWords: 3500, maxRevisions: 2, ...(A.limits || {}) }
const AGENT = (name) => `bayesian-workflow:${name}`
const M = A.model ? { model: A.model } : {}

// Dispatch seam. Normally resolves the plugin agent by type; when the caller
// supplies A.agentBodies[name] (testing outside a plugin-loaded session, or
// prompt iteration without a plugin reload), the role instructions are
// prepended to the prompt and the default workflow subagent runs them.
// agent() THROWS (not null) when a subagent completes without structured
// output — catch so callers get the uniform "lost" signal (null) and retry.
const call = async (name, prompt, opts) => {
  try {
    return A.agentBodies && A.agentBodies[name]
      ? await agent(`${A.agentBodies[name]}\n\n=== DISPATCH ===\n\n${prompt}`, { ...opts, ...M })
      : await agent(prompt, { ...opts, agentType: AGENT(name), ...M })
  } catch (e) {
    log(`⚠ ${opts.label || name}: agent failed (${String(e && e.message || e).slice(0, 140)}) — treating as lost`)
    return null
  }
}

// ---------------------------------------------------------------------------
// Schemas — `rationale` first, as everywhere in this plugin.
// ---------------------------------------------------------------------------
const OUTLINE_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string', description: 'The story you chose and the main things you decided to omit' },
    headline: { type: 'string', description: 'The one-sentence answer a reader should repeat to a colleague' },
    title: { type: 'string' },
    dek: { type: 'string', description: 'One-sentence subtitle under the title' },
    sections: {
      type: 'array', minItems: 3,
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'Short slug, becomes sections/<id>.md' },
          title: { type: 'string', description: 'States a finding, not a topic' },
          intent: { type: 'string', description: 'What the reader should BELIEVE after this section, and why' },
          key_points: { type: 'array', items: { type: 'string' }, minItems: 1, description: 'Each names its one load-bearing number by description' },
          evidence: { type: 'array', items: { type: 'string' }, description: 'Artifact paths behind the key points' },
          figure_ids: { type: 'array', items: { type: 'string' }, description: 'Ids from the figure story placed in this section' },
          target_words: { type: 'integer' },
          tier: { enum: ['executive', 'results', 'methods', 'supplementary'] },
        },
        required: ['id', 'title', 'intent', 'key_points', 'evidence', 'figure_ids', 'target_words', 'tier'],
      },
    },
    figure_story: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          purpose: { type: 'string', description: 'What this figure argues, one line' },
          source: { type: 'string', description: 'Path to an existing image, or "REGENERATE: <what to plot from which data>"' },
        },
        required: ['id', 'purpose', 'source'],
      },
      description: 'Ordered so captions alone tell the story; opens with a raw-data phenomenon figure',
    },
    contrast_specs: { type: 'array', items: { type: 'string' }, description: '1-3 practical contrasts: predictor settings and quantity to report, empty if no posterior available' },
    omissions: { type: 'array', items: { type: 'string' }, description: 'What was deliberately left out or demoted to supplementary, with reasons' },
  },
  required: ['rationale', 'headline', 'title', 'dek', 'sections', 'figure_story', 'contrast_specs', 'omissions'],
}

const FACTS_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string' },
    facts_path: { type: 'string' },
    figures: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          path: { type: 'string', description: 'Final path under report_dir/figures/' },
          caption: { type: 'string', description: 'Takeaway sentence, not contents description' },
          note_for_writer: { type: 'string', description: 'What to point the reader at' },
        },
        required: ['id', 'path', 'caption', 'note_for_writer'],
      },
    },
    contrasts_summary: { type: 'string', description: 'One line per computed contrast with value and HDI' },
    missing: { type: 'array', items: { type: 'string' }, description: 'Outline needs that could NOT be sourced, empty if none' },
  },
  required: ['rationale', 'facts_path', 'figures', 'contrasts_summary', 'missing'],
}

const DRAFT_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string' },
    draft_path: { type: 'string' },
    words: { type: 'integer' },
    figures_used: { type: 'array', items: { type: 'string' } },
    missing_facts: { type: 'array', items: { type: 'string' }, description: 'Numbers the brief needed but the fact sheet lacks (placeholders left in draft)' },
  },
  required: ['rationale', 'draft_path', 'words', 'figures_used', 'missing_facts'],
}

const ASSEMBLE_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string' },
    report_path: { type: 'string' },
    word_count: { type: 'integer' },
    dispositions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          issue: { type: 'string' },
          action: { enum: ['fixed', 'declined'] },
          note: { type: 'string' },
        },
        required: ['issue', 'action', 'note'],
      },
      description: 'Revise mode only: one entry per critic issue',
    },
  },
  required: ['rationale', 'report_path', 'word_count', 'dispositions'],
}

const REVIEW_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string', description: 'The cold-read experience: where you stumbled, what you still did not know' },
    verdict: { enum: ['SHIP', 'REVISE'] },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          location: { type: 'string', description: 'Section + short quote' },
          type: { type: 'string', description: 'e.g. dangling-promise, unsourced-number, density, flow, skim-test, caption, jargon' },
          severity: { enum: ['blocking', 'major', 'minor'] },
          issue: { type: 'string' },
          fix: { type: 'string', description: 'Concrete and actionable' },
        },
        required: ['location', 'type', 'severity', 'issue', 'fix'],
      },
    },
    skim_test_story: { type: 'string', description: 'The story told by headings+figures+first sentences alone' },
  },
  required: ['rationale', 'verdict', 'issues', 'skim_test_story'],
}

// ---------------------------------------------------------------------------
// Stage 1 — Plan
// ---------------------------------------------------------------------------
let outline = A.outline || null
if (!outline) {
  outline = await call('report-planner', `project_dir: ${P}
report_dir: ${REPORT}
eda_dir: ${EDA}
experiments_dir: ${EXPS}
assessment_path: ${ASSESS}
plan_path: ${PLANMD}
${A.ledgerPath ? `ledger_path: ${A.ledgerPath}` : 'ledger_path: NOT AVAILABLE — reconstruct question state per your instructions'}
${A.logPath ? `log_path: ${A.logPath}` : `log_path: ${P}/log.md`}
${A.selectedModelDir ? `selected_model_dir: ${A.selectedModelDir}` : ''}
audience: ${AUDIENCE}
limits: max_sections=${L.maxSections}, figure_budget=${L.figureBudget}, max_words=${L.maxWords}

Design the report. Write outline.md, then return the structured outline.`, {
    schema: OUTLINE_RESULT, phase: 'Plan', label: 'plan',
  })
  if (!outline) throw new Error('report-planner lost — no outline to execute')
} else {
  log('outline supplied by caller — Plan stage skipped')
}

// Deterministic guards on the outline.
if (outline.sections.length > L.maxSections) {
  log(`✂ section cap ${L.maxSections}: dropping ${outline.sections.slice(L.maxSections).map((s) => s.id).join(', ')}`)
  outline.sections = outline.sections.slice(0, L.maxSections)
}
if (outline.figure_story.length > L.figureBudget) {
  log(`✂ figure budget ${L.figureBudget}: dropping ${outline.figure_story.slice(L.figureBudget).map((f) => f.id).join(', ')}`)
  outline.figure_story = outline.figure_story.slice(0, L.figureBudget)
}
const plannedWords = outline.sections.reduce((n, s) => n + s.target_words, 0)
if (plannedWords > L.maxWords * 1.2) log(`⚠ outline plans ${plannedWords} words against a ${L.maxWords} budget — writers hold section targets; assembler trims`)
log(`Outline: "${outline.title}" — ${outline.sections.length} sections, ${outline.figure_story.length} figures, ~${plannedWords} words`)
if (A.stopAfter === 'plan') return { outline }

// ---------------------------------------------------------------------------
// Stage 2 — Evidence
// ---------------------------------------------------------------------------
let facts = A.facts || null
if (!facts) {
  facts = await call('report-quant', `project_dir: ${P}
report_dir: ${REPORT}
${A.selectedModelDir ? `selected_model_dir: ${A.selectedModelDir}` : 'selected_model_dir: NOT SUPPLIED — skip contrasts that need a posterior and record them in missing'}
${A.dataPath ? `data_path: ${A.dataPath}` : ''}
figure_budget: ${L.figureBudget}

OUTLINE (source every key point, execute the figure story and contrast specs):
${JSON.stringify({ sections: outline.sections.map((s) => ({ id: s.id, key_points: s.key_points, evidence: s.evidence })), figure_story: outline.figure_story, contrast_specs: outline.contrast_specs }, null, 1)}`, {
    schema: FACTS_RESULT, phase: 'Evidence', label: 'evidence',
  })
  if (!facts) throw new Error('report-quant lost — no fact sheet, writers cannot proceed')
} else {
  log('facts supplied by caller — Evidence stage skipped')
}
if (facts.missing.length) log(`⚠ evidence gaps (writers will see placeholders): ${facts.missing.join(' | ')}`)
if (facts.figures.length > L.figureBudget) {
  log(`✂ figure budget ${L.figureBudget}: manifest trimmed from ${facts.figures.length}`)
  facts.figures = facts.figures.slice(0, L.figureBudget)
}
log(`Evidence: fact sheet at ${facts.facts_path}, ${facts.figures.length} figures${facts.contrasts_summary ? '; contrasts: ' + facts.contrasts_summary : ''}`)
if (A.stopAfter === 'facts') return { outline, facts }

// ---------------------------------------------------------------------------
// Stage 3 — Draft (parallel, one writer per section)
// ---------------------------------------------------------------------------
const figById = Object.fromEntries(facts.figures.map((f) => [f.id, f]))
async function draftSection(s, i) {
  const neighbors = {
    previous: i > 0 ? { title: outline.sections[i - 1].title, intent: outline.sections[i - 1].intent } : null,
    next: i < outline.sections.length - 1 ? { title: outline.sections[i + 1].title, intent: outline.sections[i + 1].intent } : null,
  }
  const figs = s.figure_ids.map((id) => figById[id]).filter(Boolean)
  const prompt = `output_path: ${REPORT}/sections/${s.id}.md
facts_path: ${facts.facts_path}
report_headline: ${outline.headline}
audience: ${AUDIENCE}

YOUR SECTION BRIEF:
${JSON.stringify(s, null, 1)}

NEIGHBOR BRIEFS (continuity only — do not write their content):
${JSON.stringify(neighbors, null, 1)}

YOUR FIGURES (place with [[FIG:id]] at the point of argument):
${JSON.stringify(figs, null, 1)}`
  const sane = (r) => r && typeof r.draft_path === 'string' && r.draft_path.startsWith(REPORT) && r.words > 50
  let r = await call('section-writer', prompt, { schema: DRAFT_RESULT, phase: 'Draft', label: `draft:${s.id}` })
  if (!sane(r)) {
    log(`writer ${s.id} ${r ? `returned an invalid result (draft_path: ${r.draft_path}, words: ${r.words})` : 'lost'} — relaunching once`)
    r = await call('section-writer', `${prompt}

NOTE: a previous attempt returned an invalid structured result (placeholder values or a draft_path outside the report dir). Write the real section and return honestly.`, { schema: DRAFT_RESULT, phase: 'Draft', label: `draft:${s.id}:retry` })
  }
  return sane(r) ? { section: s, draft: r } : null
}

const drafts = (await parallel(outline.sections.map((s, i) => () => draftSection(s, i)))).filter(Boolean)
const missingSections = outline.sections.filter((s) => !drafts.some((d) => d.section.id === s.id))
if (missingSections.length) throw new Error(`sections never drafted after retry: ${missingSections.map((s) => s.id).join(', ')}`)

// Deterministic post-draft checks.
for (const { section, draft } of drafts) {
  const unknown = draft.figures_used.filter((id) => !figById[id])
  if (unknown.length) log(`⚠ ${section.id}: references figures not in manifest: ${unknown.join(', ')} — assembler must drop them`)
  if (draft.missing_facts.length) log(`⚠ ${section.id}: missing facts: ${draft.missing_facts.join(' | ')}`)
  if (draft.words > section.target_words * 1.5) log(`⚠ ${section.id}: ${draft.words} words vs target ${section.target_words} — assembler trims`)
}
const placedFigs = new Set(drafts.flatMap((d) => d.draft.figures_used))
const orphanFigs = facts.figures.filter((f) => !placedFigs.has(f.id)).map((f) => f.id)
if (orphanFigs.length) log(`⚠ figures in manifest but placed by no writer: ${orphanFigs.join(', ')} — assembler decides`)
const totalWords = drafts.reduce((n, d) => n + d.draft.words, 0)
log(`Drafts: ${drafts.length} sections, ${totalWords} words total`)
if (A.stopAfter === 'draft') return { outline, facts, drafts: drafts.map((d) => d.draft) }

// ---------------------------------------------------------------------------
// Stage 4 — Assemble
// ---------------------------------------------------------------------------
const draftNotes = drafts.map((d) => ({
  id: d.section.id, path: d.draft.draft_path, words: d.draft.words,
  missing_facts: d.draft.missing_facts,
})).concat(orphanFigs.length ? [{ id: '_orphan_figures', note: `unplaced figures: ${orphanFigs.join(', ')}` }] : [])

let assembled = await call('report-assembler', `mode: assemble
report_dir: ${REPORT}
output_path: ${OUT}
facts_path: ${facts.facts_path}
word_budget: ${L.maxWords}
audience: ${AUDIENCE}

OUTLINE:
${JSON.stringify({ headline: outline.headline, title: outline.title, dek: outline.dek, sections: outline.sections.map((s) => ({ id: s.id, title: s.title, intent: s.intent, tier: s.tier })) }, null, 1)}

DRAFT NOTES (per-section paths and flags):
${JSON.stringify(draftNotes, null, 1)}`, { schema: ASSEMBLE_RESULT, phase: 'Assemble', label: 'assemble' })
if (!assembled) throw new Error('report-assembler lost — no document produced')
log(`Assembled: ${assembled.report_path}, ${assembled.word_count} words`)
if (A.stopAfter === 'assemble') return { outline, facts, assembled }

// ---------------------------------------------------------------------------
// Stage 5 — Review loop
// ---------------------------------------------------------------------------
const reviews = []
let lastReview = null
for (let round = 1; round <= L.maxRevisions + 1; round++) {
  const review = await call('report-critic', `report_path: ${assembled.report_path}
facts_path: ${facts.facts_path}
manifest_path: ${REPORT}/figures/manifest.json
report_dir: ${REPORT}
round: ${round}
audience: ${AUDIENCE}

OUTLINE (intent-vs-execution check):
${JSON.stringify({ headline: outline.headline, sections: outline.sections.map((s) => ({ id: s.id, title: s.title, intent: s.intent })), omissions: outline.omissions }, null, 1)}`, { schema: REVIEW_RESULT, phase: 'Review', label: `review:${round}` })
  if (!review) { log('critic lost — shipping the current draft with no verdict'); break }
  lastReview = review
  reviews.push({ round, verdict: review.verdict, issues: review.issues.length })
  const blocking = review.issues.filter((i) => i.severity !== 'minor')
  log(`Review ${round}: ${review.verdict} (${review.issues.length} issues, ${blocking.length} blocking/major)`)

  if (review.verdict === 'SHIP') break
  if (round > L.maxRevisions) { log(`✂ revision budget ${L.maxRevisions} spent — shipping with ${blocking.length} open issues (see review_round_${round}.md)`); break }

  const revised = await call('report-assembler', `mode: revise
report_dir: ${REPORT}
output_path: ${OUT}
facts_path: ${facts.facts_path}
word_budget: ${L.maxWords}

OUTLINE:
${JSON.stringify({ headline: outline.headline, title: outline.title }, null, 1)}

CRITIC ISSUES (address each — fixed or declined with reason):
${JSON.stringify(review.issues, null, 1)}`, { schema: ASSEMBLE_RESULT, phase: 'Review', label: `revise:${round}` })
  if (!revised) { log('assembler lost during revision — shipping the pre-revision draft'); break }
  const declined = revised.dispositions.filter((d) => d.action === 'declined')
  if (declined.length) log(`revise ${round}: ${declined.length} issue(s) declined with reasons`)
  assembled = revised
}

return {
  report_path: assembled.report_path,
  word_count: assembled.word_count,
  outline: { headline: outline.headline, title: outline.title, sections: outline.sections.map((s) => s.id) },
  facts_path: facts.facts_path,
  figures: facts.figures.length,
  reviews,
  // Issues still open when the loop ended — empty on a SHIP. The orchestrator
  // relays these to the user instead of presenting the report as fully clean.
  open_issues: lastReview && lastReview.verdict === 'REVISE' ? lastReview.issues : [],
}
