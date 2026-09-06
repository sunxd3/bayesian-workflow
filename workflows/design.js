// Phase 2 — Model design. Plan → parallel designers → synthesize → ledger.
//
// Invoked by the orchestrator (see the `orchestration` skill) as:
//
//   Workflow({
//     scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/design.js",
//     args: {
//       projectDir: "/abs/path/to/project",
//       dataPath: "/abs/path/to/data.csv",
//       goal: "the confirmed analysis goal",
//       edaDir: "...",                 // default: <projectDir>/eda
//       maxQuestions: 3,               // structural questions cap
//       maxExperimentsPerQuestion: 3,  // initial experiments per question
//     },
//   })
//
// Deterministic logic owned here: question/experiment caps, canonical id
// assignment (q1, q1_e1, ...), baseline flagging (first experiment of each
// question), guarded application of the synthesist's drop/add decisions.
// Judgment (framing, specs, dedup calls) lives in planner/designer/synthesist.
//
// Returns the seed LEDGER — the machine-readable question/experiment state that
// develop.js consumes and the orchestrator persists as design/ledger.json.

export const meta = {
  name: 'design-experiments',
  description: 'Phase 2: frame the analysis, design per-question experiments, synthesize the plan and seed the ledger',
  whenToUse: 'Dispatched by the bayesian-workflow orchestrator after EDA. Not intended for direct use.',
  phases: [
    { title: 'Plan', detail: 'purpose, validation strategy, domain, structural questions, shared baseline' },
    { title: 'Design', detail: 'one designer per structural question, in parallel' },
    { title: 'Synthesize', detail: 'dedup, cross-cutting experiments, final plan table' },
  ],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
if (!A || !A.projectDir || !A.dataPath || !A.goal) {
  throw new Error('args must be {projectDir, dataPath, goal, edaDir?, maxQuestions?, maxExperimentsPerQuestion?}')
}
const EDA_DIR = A.edaDir || `${A.projectDir}/eda`
const DESIGN_DIR = `${A.projectDir}/design`
const PLAN_PATH = `${DESIGN_DIR}/experiment_plan.md`
const MAX_Q = A.maxQuestions ?? 3
const MAX_E = A.maxExperimentsPerQuestion ?? 3
const AGENT = (name) => `bayesian-workflow:${name}`
const M = A.model ? { model: A.model } : {}

// Dispatch seam. Normally resolves the plugin agent by type; A.agentBodies[name]
// (testing outside a plugin-loaded session, or prompt iteration without a
// plugin reload) prepends the role instructions and uses the default subagent.
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

const PLAN_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string' },
    purpose: { enum: ['descriptive', 'inferential', 'predictive'] },
    key_quantities: { type: 'array', items: { type: 'string' }, description: '1-3 key quantities of interest with adequacy criteria' },
    validation_strategy: { type: 'string', description: 'Hold-out scheme matched to the dependence structure' },
    ranking_metric: {
      type: 'object',
      description: 'THE metric model comparison will rank on — must implement the validation strategy (e.g. grouped data → a grouped score, not observation-level LOO)',
      properties: {
        name: { type: 'string', description: 'Short id, e.g. "elpd_loo", "elpd_lopo" (leave-one-participant-out), "elpd_lfo" (leave-future-out)' },
        definition: { type: 'string', description: 'One line telling a fitter exactly how to compute score ± se (higher is better)' },
      },
      required: ['name', 'definition'],
    },
    plausibility_bounds: { type: 'string', description: 'Outcome-scale plausibility bounds for prior predictive checks, with justification from observed scales/domain (e.g. "launch speed in (0.2, 8) m/s: observed 1.0–3.9, rig limits"). Tight enough to be falsifiable — bounds orders of magnitude wider than the data cannot fail anything' },
    domain_context: { type: 'string', description: 'Canonical framework for this domain, or "no strong conventions"' },
    questions: {
      type: 'array', minItems: 2, maxItems: 6,
      items: {
        type: 'object',
        properties: {
          statement: { type: 'string', description: 'Contrastive: pits two explanations of the DGP against each other' },
          contrast: { type: 'string', description: 'The two explanations being pitted, one line' },
        },
        required: ['statement', 'contrast'],
      },
      description: 'ORDERED by expected scientific value — only the first maxQuestions are dispatched to designers; the rest are recorded as deferred',
    },
    baseline_spec: { type: 'string', description: 'Full generative spec of the shared baseline: likelihood, structure, priors' },
    plan_path: { type: 'string' },
  },
  required: ['rationale', 'purpose', 'key_quantities', 'validation_strategy', 'ranking_metric', 'plausibility_bounds', 'domain_context', 'questions', 'baseline_spec', 'plan_path'],
}

const DESIGN_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string' },
    experiments: {
      type: 'array', minItems: 1, maxItems: 5,
      items: {
        type: 'object',
        properties: {
          spec: { type: 'string', description: 'Full model spec: likelihood, structure, priors — enough to author the Stan program from' },
          purpose_in_sequence: { type: 'string', description: 'What this experiment resolves within the question, one line' },
        },
        required: ['spec', 'purpose_in_sequence'],
      },
      description: 'Resolution sequence, ordered. Experiment 1 MUST be the minimal contrast against the shared baseline.',
    },
    proposal_path: { type: 'string' },
  },
  required: ['rationale', 'experiments', 'proposal_path'],
}

const SYNTH_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string' },
    drop: { type: 'array', items: { type: 'string' }, description: 'Experiment ids that duplicate another experiment, empty if none' },
    cross_cutting: {
      type: 'array', maxItems: 2,
      items: {
        type: 'object',
        properties: {
          question_id: { type: 'string', description: 'The EXISTING question this experiment primarily informs' },
          spec: { type: 'string' },
          rationale: { type: 'string' },
        },
        required: ['question_id', 'spec', 'rationale'],
      },
      description: 'Experiments where two designers\' questions interact, empty if none',
    },
    plan_path: { type: 'string' },
  },
  required: ['rationale', 'drop', 'cross_cutting', 'plan_path'],
}

// --- Plan ----------------------------------------------------------------------
const plan = await call('analysis-planner',
  `eda_dir: ${EDA_DIR}
data_path: ${A.dataPath}
output_dir: ${DESIGN_DIR}
goal: ${A.goal}
max_questions: ${MAX_Q} — only the ${MAX_Q} most valuable questions get designers this round. Rank yours by expected scientific value; anything beyond the cap goes in the plan's Deferred Questions section, and NO adequacy criterion or key quantity may depend on a deferred question.

Frame the analysis and seed ${PLAN_PATH} per your instructions. Leave the final experiments table for the synthesis step.`,
  { schema: PLAN_RESULT, phase: 'Plan', label: 'plan' },
)
if (!plan) throw new Error('analysis-planner agent lost — cannot design without framing')

const questions = plan.questions.slice(0, MAX_Q).map((q, i) => ({ id: `q${i + 1}`, ...q }))
const deferred = plan.questions.slice(MAX_Q)
if (deferred.length) {
  log(`✂ question cap ${MAX_Q}: deferred (recorded, not designed): ${deferred.map((q) => q.statement).join(' | ')}`)
}
log(`Framing: ${plan.purpose}; ${questions.length} structural questions; ranking metric ${plan.ranking_metric.name}`)

// --- Design ----------------------------------------------------------------------
// Catch placeholder/misdirected returns by path; retry once (cheap — the
// designer's written proposal survives on disk).
const saneDesign = (r, outDir) =>
  r && typeof r.proposal_path === 'string' && r.proposal_path.startsWith(outDir)

async function runDesigner(q, i) {
  const outDir = `${DESIGN_DIR}/designer_${q.id}`
  const siblings = questions.filter((s) => s.id !== q.id).map((s) => `${s.id}: ${s.statement}`).join('\n')
  const prompt = `question_id: ${q.id}
question: ${q.statement}
contrast: ${q.contrast}
baseline_spec:
${plan.baseline_spec}

plan_path: ${PLAN_PATH}
eda_dir: ${EDA_DIR}
output_dir: ${outDir}
max_experiments: ${MAX_E}

Other designers' questions (avoid overlapping their territory; note interactions in your proposal):
${siblings}

Consider structurally different model families when they better match the data-generating process — not just parametric extensions of the baseline.`
  let r = await call('model-designer', prompt, { schema: DESIGN_RESULT, phase: 'Design', label: `design:${q.id}` })
  if (!saneDesign(r, outDir)) {
    log(`designer ${q.id} ${r ? `returned an invalid result (proposal_path: ${r.proposal_path})` : 'lost'} — relaunching once`)
    r = await call('model-designer', `${prompt}

NOTE: a previous attempt returned an invalid structured result (placeholder values or a proposal_path outside output_dir). Redo per your instructions and return your REAL design with proposal_path under ${outDir}.`, { schema: DESIGN_RESULT, phase: 'Design', label: `design:${q.id}:retry` })
  }
  if (!saneDesign(r, outDir)) {
    log(`✂ designer ${q.id}: invalid after retry — question will have no experiments`)
    return null
  }
  return { question: q, design: r }
}

const designs = (await parallel(questions.map((q, i) => () => runDesigner(q, i)))).filter((d) => d && d.design)
if (!designs.length) throw new Error('all designers lost — no experiments to run')

// Canonical ids + caps + baseline flags — pure policy, applied in code.
const experiments = []
for (const { question, design } of designs) {
  const kept = design.experiments.slice(0, MAX_E)
  if (design.experiments.length > kept.length) {
    log(`✂ ${question.id}: capped at ${MAX_E} experiments (designer proposed ${design.experiments.length})`)
  }
  kept.forEach((e, j) => experiments.push({
    id: `${question.id}_e${j + 1}`,
    questionId: question.id,
    baseline: j === 0, // question's entry point — if it fails pre-fit, the question is abandoned (develop.js rule)
    spec: e.spec,
    context: e.purpose_in_sequence,
  }))
}

// --- Synthesize --------------------------------------------------------------------
const synth = await call('synthesist',
  `mode: design
inputs: ${designs.map((d) => d.design.proposal_path).join(', ')}
plan_path: ${PLAN_PATH}
output_path: ${PLAN_PATH}

Current experiment table (ids are canonical — refer to them exactly):
${experiments.map((e) => `${e.id}${e.baseline ? ' [baseline]' : ''} (${e.questionId}): ${e.context}`).join('\n')}
${deferred.length ? `
Deferred questions (planner ranked below the dispatch cap — NO experiments exist for these): ${deferred.map((q) => q.statement).join(' | ')}
Reconcile the plan text: mark these as deferred and rewrite any adequacy criterion, key quantity, or promise that depends on them — the plan must not claim coverage its experiment table cannot deliver.` : ''}
Append the final experiments table to the plan (preserve the planner-seeded sections). Flag true duplicates in \`drop\` and propose at most 2 cross-cutting experiments where designer questions interact.`,
  { schema: SYNTH_RESULT, phase: 'Synthesize', label: 'synthesize' },
)

if (synth) {
  for (const id of synth.drop) {
    const i = experiments.findIndex((e) => e.id === id)
    if (i === -1) { log(`✂ synthesist drop '${id}' ignored: unknown id`); continue }
    if (experiments[i].baseline) { log(`✂ synthesist drop '${id}' ignored: baselines are never dropped`); continue }
    log(`dedup: dropping ${id} (${synth.rationale ? 'see synthesis rationale' : 'duplicate'})`)
    experiments.splice(i, 1)
  }
  synth.cross_cutting.forEach((x, j) => {
    if (!questions.some((q) => q.id === x.question_id)) {
      log(`✂ cross-cutting experiment ignored: unknown question '${x.question_id}'`)
      return
    }
    // Max existing suffix, not count — drops may have left gaps (e1,e3 → next is e4).
    const n = experiments.filter((e) => e.questionId === x.question_id)
      .reduce((m, e) => Math.max(m, parseInt((e.id.match(/_e(\d+)$/) || [])[1] || '0', 10)), 0)
    experiments.push({
      id: `${x.question_id}_e${n + 1}`,
      questionId: x.question_id,
      baseline: false,
      spec: x.spec,
      context: `cross-cutting: ${x.rationale}`,
    })
  })
} else {
  log('synthesist lost — proceeding with the un-deduplicated designer table')
}

log(`Plan: ${questions.length} questions, ${experiments.length} experiments`)

return {
  plan: {
    purpose: plan.purpose,
    key_quantities: plan.key_quantities,
    validation_strategy: plan.validation_strategy,
    ranking_metric: plan.ranking_metric,     // → develop.js args.metric
    plausibility_bounds: plan.plausibility_bounds, // → develop.js args.bounds
    domain_context: plan.domain_context,
    baseline_spec: plan.baseline_spec,
    plan_path: plan.plan_path,
  },
  ledger: {
    data_path: A.dataPath,
    questions: questions.map((q) => ({ id: q.id, statement: q.statement, contrast: q.contrast })),
    deferred_questions: deferred.map((q) => ({ statement: q.statement, contrast: q.contrast })),
    experiments,
  },
}
