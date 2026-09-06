// Phase 1 — Data understanding. Profile → fan out analysts → synthesize.
//
// Invoked by the orchestrator (see the `orchestration` skill) as:
//
//   Workflow({
//     scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/explore.js",
//     args: {
//       projectDir: "/abs/path/to/project",
//       dataPath: "/abs/path/to/data.csv",
//       goal: "optional analysis goal from the user",
//       edaDir: "...",          // default: <projectDir>/eda
//       maxAnalysts: 3,         // cap on parallel analysts
//       focusAreas: ["..."],    // optional override: skip profiling, use these
//     },
//   })
//
// Deterministic logic owned here: fan-out sizing (a policy applied to facts the
// profiler returns), analyst retry-once, focus-area assignment, and which
// analyst owns the canonical CSV deliverables. Judgment (what the data means)
// lives in the analyst and synthesist agents.

export const meta = {
  name: 'explore-data',
  description: 'Phase 1: profile the dataset, run parallel EDA analysts, synthesize one report',
  whenToUse: 'Dispatched by the bayesian-workflow orchestrator (or /bayesian-workflow:eda). Not intended for direct use.',
  phases: [
    { title: 'Profile', detail: 'cheap facts pass to size the fan-out' },
    { title: 'Explore', detail: 'one analyst per focus area, in parallel' },
    { title: 'Synthesize', detail: 'merge findings into eda_report.html' },
  ],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
if (!A || !A.projectDir || !A.dataPath) {
  throw new Error('args must be {projectDir, dataPath, goal?, edaDir?, maxAnalysts?, focusAreas?}')
}
const EDA_DIR = A.edaDir || `${A.projectDir}/eda`
const MAX_ANALYSTS = A.maxAnalysts ?? 3
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

// `rationale` first: models emit properties in schema order, so reasoning is
// committed before conclusions. Same convention in every schema in this plugin.
const PROFILE_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string', description: 'One short paragraph on what was inspected' },
    n_rows: { type: 'integer' },
    n_cols: { type: 'integer' },
    columns_summary: { type: 'string', description: 'One dense line: names, dtypes, ranges of the key columns' },
    candidate_group_vars: { type: 'array', items: { type: 'string' }, description: 'Columns that look like grouping/hierarchy candidates' },
    has_time_index: { type: 'boolean' },
    missingness_pct: { type: 'number' },
    focus_areas: {
      type: 'array', items: { type: 'string' }, minItems: 1, maxItems: 4,
      description: 'Distinct EDA focus areas this dataset warrants, most important first. The first MUST cover data quality + distributions.',
    },
  },
  required: ['rationale', 'n_rows', 'n_cols', 'columns_summary', 'candidate_group_vars', 'has_time_index', 'missingness_pct', 'focus_areas'],
}

const FINDINGS_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string' },
    summary: { type: 'string', description: 'One paragraph: the most modeling-relevant findings for this focus area' },
    hypotheses: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          statement: { type: 'string', description: 'A competing structural hypothesis about the data-generating process' },
          evidence: { type: 'string', description: 'The observation backing it, with numbers' },
        },
        required: ['statement', 'evidence'],
      },
    },
    quality_flags: { type: 'array', items: { type: 'string' }, description: 'Data quality issues that constrain modeling, empty if none' },
    report_path: { type: 'string' },
  },
  required: ['rationale', 'summary', 'hypotheses', 'quality_flags', 'report_path'],
}

const SYNTH_RESULT = {
  type: 'object',
  properties: {
    rationale: { type: 'string' },
    report_path: { type: 'string' },
    structural_hypotheses: { type: 'array', items: { type: 'string' }, description: 'Competing DGP hypotheses, deduplicated across analysts' },
    modeling_implications: { type: 'array', items: { type: 'string' } },
    quality_flags: { type: 'array', items: { type: 'string' } },
    suggested_goal: { type: 'string', description: 'Proposed analysis goal — set ONLY if no goal was supplied' },
  },
  required: ['rationale', 'report_path', 'structural_hypotheses', 'modeling_implications', 'quality_flags'],
}

// --- Profile (skipped when the caller pins focus areas) -----------------------
let focusAreas = A.focusAreas
let profile = null
if (!focusAreas || !focusAreas.length) {
  profile = await call('data-profiler',
    `data_path: ${A.dataPath}

Profile this dataset: shape, column types, grouping candidates, time structure, missingness. Report FACTS only — no modeling judgments. Propose 1-4 distinct EDA focus areas per your instructions; the first must cover data quality + distributions.`,
    { schema: PROFILE_RESULT, effort: 'low', phase: 'Profile', label: 'profile' },
  )
  if (!profile) throw new Error('data-profiler agent lost — cannot size the EDA fan-out')
  focusAreas = profile.focus_areas.slice(0, MAX_ANALYSTS)
  if (profile.focus_areas.length > focusAreas.length) {
    log(`✂ fan-out capped at ${MAX_ANALYSTS}: dropped focus areas: ${profile.focus_areas.slice(MAX_ANALYSTS).join('; ')}`)
  }
} else {
  focusAreas = focusAreas.slice(0, MAX_ANALYSTS)
  log(`focus areas pinned by caller: ${focusAreas.join('; ')}`)
}

// --- Explore -----------------------------------------------------------------
// Placeholder/misdirected returns (e.g. a StructuredOutput "test" call) look
// like success to the schema — catch them by path and substance, and retry
// once: completed work short-circuits via status.json, so retries are cheap.
const saneFindings = (r, outDir) =>
  r && typeof r.report_path === 'string' && r.report_path.startsWith(outDir) && (r.summary || '').length > 40

async function runAnalyst(focus, i) {
  const outDir = `${EDA_DIR}/analyst_${i + 1}`
  // Analyst 1 always owns the canonical CSV deliverables — a deterministic
  // assignment so the tables exist exactly once regardless of fan-out size.
  const canonical = i === 0
    ? `\nYou own the canonical deliverables: also write ${EDA_DIR}/quality_summary.csv and ${EDA_DIR}/univariate_summary.csv.`
    : ''
  const prompt = `data_path: ${A.dataPath}
output_dir: ${outDir}
focus_area: ${focus}
${A.goal ? `goal: ${A.goal}` : ''}${profile ? `\ndataset_profile: ${profile.n_rows} rows × ${profile.n_cols} cols; ${profile.columns_summary}; groups: ${profile.candidate_group_vars.join(', ') || 'none'}; time index: ${profile.has_time_index}` : ''}${canonical}`
  let r = await call('eda-analyst', prompt, { schema: FINDINGS_RESULT, phase: 'Explore', label: `analyst_${i + 1}` })
  if (!saneFindings(r, outDir)) {
    log(`analyst_${i + 1} ${r ? `returned an invalid result (report_path: ${r.report_path}) — completed work will short-circuit` : 'lost'} — relaunching once`)
    r = await call('eda-analyst', `${prompt}

NOTE: a previous attempt returned an invalid structured result (placeholder values or a report_path outside output_dir). Redo per your instructions — the completed-work check on status.json makes finished work cheap — and return your REAL findings with report_path under ${outDir}.`, { schema: FINDINGS_RESULT, phase: 'Explore', label: `analyst_${i + 1}:retry` })
  }
  if (!saneFindings(r, outDir)) {
    log(`✂ analyst_${i + 1}: invalid after retry — dropped from synthesis`)
    return null
  }
  return r
}

const findings = (await parallel(focusAreas.map((f, i) => () => runAnalyst(f, i)))).filter(Boolean)
if (!findings.length) throw new Error('all EDA analysts lost — nothing to synthesize')
if (findings.length < focusAreas.length) log(`proceeding with ${findings.length}/${focusAreas.length} analysts`)

// --- Synthesize ----------------------------------------------------------------
const synthesis = await call('synthesist',
  `mode: eda
inputs: ${findings.map((f) => f.report_path).join(', ')}
output_path: ${EDA_DIR}/eda_report.html
data_path: ${A.dataPath}
${A.goal ? `goal: ${A.goal}` : 'goal: NOT SUPPLIED — propose one in suggested_goal'}

Merge the analyst findings into the canonical EDA report: convergent patterns (analysts agree), divergent insights (unique to one), competing structural hypotheses, modeling implications, data quality constraints.`,
  { schema: SYNTH_RESULT, phase: 'Synthesize', label: 'synthesize' },
)
if (!synthesis) throw new Error('synthesist agent lost — eda_report.html not produced')

return { profile, analyst_findings: findings, synthesis }
