# Tests

Tests for the reference scripts in `skills/fit/fit-pipeline/references/`. Agents copy and adapt those scripts during runs, so they're the one part of the plugin you can actually test.

This folder is its own uv project. It doesn't ship with the plugin and the loader ignores it.

## Run

```
cd tests
uv sync
uv run pytest -m "not integration" -q   # synthetic InferenceData, no CmdStan
uv run pytest -m integration -v         # compiles and samples tests/stan/*.stan
uv run ruff check --config pyproject.toml . ../skills/fit/fit-pipeline/references
uv run pyright
```

The integration tests need CmdStan (`uv run python -m cmdstanpy.install_cmdstan`) and skip without it. Set `REQUIRE_CMDSTAN=1` to make a missing toolchain a failure instead — CI does this so skipped tests can't show up as green.

## Layout

| path | what |
|---|---|
| `conftest.py` | loads scripts by path; session-scoped fits and fixtures |
| `test_reference_pure.py` | encoding, convergence, LOO, thinning, artifact contract |
| `test_reference_real.py` | real fits: recovery, PPC coverage, LOO ranking, CLIs |
| `stan/` | small models; binaries gitignored, cached in CI |
| `fixtures/` | eight schools data |

CI also validates the manifest, syntax-checks the workflow scripts, and runs ruff and pyright on Python 3.10 and 3.13.
