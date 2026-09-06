---
name: validation-protocol
description: Entry/exit contract for workflow subagents — input validation, the completed-work short-circuit, structured returns with audited numeric fields, and the status.json completion record.
user-invocable: false
---

# Validation Protocol

Validate inputs FIRST, before any other work. The agent body declares its
specific args and filesystem checks under `## Interface > Input`; this protocol
defines how to perform the checks, what to return on failure, and the exit
contract on success.

The protocol covers **existence and presence** only. Malformed inputs (corrupt
data, wrong format) are agent-body discretion — abort with an `[EXCEPTION]`
and an informative label, or proceed if salvageable.

## Step 1 — Arguments

Verify the input prompt contains every **required** argument from your
`**Args:**` line. Arguments marked `?` are optional. If a required argument is
missing or ambiguous, return ONLY:

`[EXCEPTION] InvalidInput: Missing '<name>'. Expected: <what it should be>.`

## Step 2 — Filesystem

Use `ls` (via the Bash tool) to verify the paths in your `**Filesystem**`
line(s). Choose the exception type by source:

- **Direct input path missing.** `[EXCEPTION] PreconditionFailed: '<path>' does not exist.`
- **Upstream artifact missing** (produced by a prior stage). `[EXCEPTION] DependencyMissing: '<path>' — <reason>.`

**Stop rule.** Return the single `[EXCEPTION]` line and nothing else. Stop
immediately.

## Step 3 — Completed-work check (`status.json`)

Applies only to agents whose Interface says "full protocol". Stages get
re-dispatched after interruptions — a crashed session, a resumed workflow run —
and this record makes re-dispatch cheap. After the input checks pass, look for
`<output_dir>/status.json`. Short-circuit if BOTH hold:

- The recorded verdict is **terminal for your stage**: `PASS` for gate stages
  (a recorded `FAIL` is *not* terminal — the model may have been refined since,
  so redo the work), or any verdict for critique.
- Every file in its `artifacts` list exists and is non-empty.
- The record's `data_path` (when present) matches the one you were dispatched
  with — a mismatch means the record describes a run against different data;
  treat it as stale and redo the work.

Then return the recorded verdict, numbers, and rationale via your structured
output with `from_cache: true`, and stop — do not redo the work. If the check
fails in any way (missing, unparseable, artifacts gone), proceed normally; your
run overwrites the stale record.

## Structured returns

Pipeline agents are dispatched by workflow scripts that supply a structured
output schema — that schema is the contract, and the `rationale` field always
comes first so reasoning is committed before the verdict. Call the structured
output tool **exactly once, as your final action, with your real results** —
never call it early, with placeholders, or "to test it": the first call IS your
return value, and a placeholder return discards your completed work (the
dispatching script will re-run you). Report paths exactly as assigned — a
`report_path` outside your `output_dir` is rejected. Two more rules:

- **Numbers as numbers.** Never prose like "R-hat fine". The script audits
  verdicts against the numeric fields deterministically.
- **Report honestly.** An inconsistent PASS is flagged to the strategist or, for
  fit hard thresholds, demoted to FAIL by the script. The audit exists to catch
  optimistic self-grading — writing numbers that contradict your own artifacts
  defeats the workflow.

### Audited numeric fields

| Stage | Field | Definition | Audit guard |
|---|---|---|---|
| prior-predictive | `extreme_draw_pct` | % of prior predictive draws outside the plausibility bounds **assigned in the dispatch** (fall back to self-derived, documented bounds only when none are assigned) | PASS flagged if > 10 |
| fake-data | `coverage_90` | fraction of parameters whose true value lies in the posterior 90% CI | PASS flagged if < 0.6 |
| fake-data | `max_bias_z` | max over parameters of \|posterior mean − true\| / posterior sd | PASS flagged if > 3 |
| fit | `rhat_max`, `ess_min`, `divergences` | standard convergence numbers (ref: `convergence-diagnostics`) | PASS **demoted to FAIL** if R̂ > 1.01, divergences > 0, or ESS < 400 |
| fit | `metric`, `score`, `score_se` | the ranking metric named in the dispatch, computed as it defines; drives the ledger's trajectories and plateau rule | score excluded from ranking if `metric` ≠ the assigned one — any deviation must be argued in `metric_note`, never silent |
| fit | `pareto_k_bad_pct` | % of observations with Pareto k > 0.7 (observation-level LOO is always computed as a diagnostic) | PASS flagged if > 10 |
| posterior-predictive | `coverage_90` | fraction of observations inside their 90% posterior predictive interval | PASS flagged if < 0.5 |
| posterior-predictive | `loo_pit_extreme_pct` | % of LOO-PIT values < 0.05 or > 0.95 | — |
| prior-predictive, fit | `data_path` | absolute path of the dataset file the stage actually read | fit PASS **demoted to FAIL** on mismatch with the dispatched path; flagged if missing |

These numbers are **mandatory on PASS** — a PASS without them is demoted or
flagged by the dispatching script. On an early FAIL (e.g. a probe that never
sampled, so there is no LOO), omit the numbers you never computed; never invent
a value to satisfy the schema.

Flag thresholds are deliberately loose — they catch verdict-vs-numbers
contradictions, not marginal judgment calls. Your verdict should rest on the
full evidence, not on gaming these bounds.

## On completion — write `status.json`

Write `<output_dir>/status.json` as the **last** file, after the report —
writing it last is what makes its existence a completion marker.

```json
{
  "stage": "<agent name>",
  "experiment": "<experiment id>",
  "verdict": "PASS | FAIL | VIABLE | CONCERNS | BROKEN",
  "key_numbers": "<one dense line: the numbers behind the verdict>",
  "data_path": "<absolute path of the dataset file this stage read — omit only if none>",
  "artifacts": ["<files under output_dir that must exist for this record to be trusted>"]
}
```

Add your stage's audited numeric fields (table above) as top-level keys with
the SAME values you returned via structured output; critique additionally
records `suggestions` and `surprises`. Downstream tooling reads these fields —
keep them machine-parseable. `data_path` is what makes results from different
runs distinguishable — experiments fitted to different datasets (a subsample,
a revision) must never be silently compared.
