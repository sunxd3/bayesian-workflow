---
name: validation-protocol
description: Standard entry/exit protocol for pipeline subagents — input validation (arguments, filesystem, strict single-line [EXCEPTION] output on failure), the completed-work short-circuit, and the status.json completion record.
user-invocable: false
---

# Validation Protocol

Validate inputs FIRST, before any other work. The agent body declares its
specific args and filesystem checks under `## Interface > Input`; this protocol
defines how to perform the checks and what to return on failure.

The protocol covers **existence and presence** only. Malformed inputs (corrupt
data, wrong format, unreadable file) are agent-body discretion — abort with an
`[EXCEPTION]` and an informative label, or proceed if the input is salvageable.

## Step 1 — Arguments

Verify the input prompt contains every **required** argument from your
`**Args:**` line. Arguments marked with `?` (e.g., `focus_area?: Text`) are
optional — their absence is not a failure. If a required argument is missing or
ambiguous, return ONLY:

`[EXCEPTION] InvalidInput: Missing '<name>'. Expected: <what it should be>.`

## Step 2 — Filesystem

Use `ls` (via the Bash tool) to verify the paths listed in your
`**Filesystem (...):**` line(s). Choose the exception type by source:

- **Direct input path missing.** Return `[EXCEPTION] PreconditionFailed: '<path>' does not exist.`
- **Upstream artifact missing** (a file produced by a prior phase/subagent). Return `[EXCEPTION] DependencyMissing: '<path>' — <reason>.`

## Stop rule

Return the single `[EXCEPTION]` line and nothing else — no explanations, no
suggestions, no follow-up questions. Stop immediately.

## Step 3 — Completed-work check (`status.json`)

Pipeline stages get re-dispatched after interruptions — a crashed session, a
resumed workflow run, a re-invoked command. The `status.json` record makes
re-dispatch cheap. After the input checks pass, look for
`<output_dir>/status.json`. Short-circuit if BOTH hold:

- The recorded verdict is **terminal for your stage**: `PASS` for gate stages
  (a recorded `FAIL` is *not* terminal — the model may have been refined since,
  so redo the work), or any verdict (`VIABLE`/`CONCERNS`/`BROKEN`) for critique.
- Every file in its `artifacts` list exists and is non-empty.

Then return the recorded verdict, key numbers, and rationale, stating that they
come from a completed prior run, and stop — do not redo the work. If the check
fails in any way (no `status.json`, unparseable, missing artifacts), proceed
normally; your run will overwrite the stale record.

## On completion — write `status.json`

Write `<output_dir>/status.json` as the **last** file, after the report —
writing it last is what makes its existence a completion marker.

```json
{
  "stage": "<agent name>",
  "experiment": "<experiment id>",
  "verdict": "PASS | FAIL | VIABLE | CONCERNS | BROKEN",
  "key_numbers": "<one dense line: the numbers behind the verdict>",
  "artifacts": ["<files under output_dir that must exist for this record to be trusted>"]
}
```

Add stage-specific keys where they exist as numbers — `rhat_max`, `ess_min`,
`divergences` for MCMC stages; `suggestions` (list) and
`new_structural_question` for critique. Downstream tooling reads these fields;
keep them machine-parseable (numbers as numbers, not strings).
