# Tests

Real tests for the runnable reference scripts in
`skills/fit/fit-pipeline/references/`. Those scripts are what agents copy and
adapt during a run, so they are the one part of the plugin that can be tested
without spending a workflow.

This folder is a standalone uv project (`pyproject.toml`, `uv.lock`). It is
not shipped to users and the plugin loader ignores it.

## Run

```
cd tests
uv sync
uv run pytest -m "not integration" -q   # pure tier: synthetic InferenceData, no CmdStan
uv run pytest -m integration -v         # real tier: compiles and samples tests/stan/*.stan
uv run ruff check --config pyproject.toml . ../skills/fit/fit-pipeline/references
uv run pyright
```

The real tier needs CmdStan (`uv run python -m cmdstanpy.install_cmdstan`).
Without it those tests skip. With `REQUIRE_CMDSTAN=1` a missing toolchain is
an error instead; CI sets it, so a skipped tier can never pass as green.

## Layout

| path | what |
|---|---|
| `conftest.py` | loads the scripts by path; session-scoped real fits (normal, funnel, eight schools); synthetic InferenceData fixtures |
| `test_reference_pure.py` | JSON encoding, convergence decisions, LOO buckets, thinning, artifact contract, recovery arithmetic |
| `test_reference_real.py` | artifact contract on real fits, parameter recovery, PPC coverage, LOO ranking via `az.compare`, funnel flagged, prior bounds, the three CLIs via subprocess |
| `stan/` | small models; compiled binaries are gitignored here and cached in CI |
| `fixtures/` | eight schools data |

CI (`.github/workflows/ci.yml`) runs manifest validation, a syntax check of
the workflow scripts, ruff and pyright, the pure tier on Python 3.10 and 3.13,
and the real tier with CmdStan cached.
