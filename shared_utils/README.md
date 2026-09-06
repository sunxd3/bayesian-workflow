# shared_utils

Helper library bundled with the `bayesian-workflow` plugin. `/bayesian-workflow:setup`
copies it into each analysis project as a path dependency; agents import it
rather than re-deriving the fit pipeline per experiment.

Its job is to make the **artifact contract deterministic**: every experiment's
`summary.json`, `diagnostics.json`, `loo.json`, `thinned_draws.npz`, and
`posterior.nc` have the same layout, because the workflow scripts audit those
files and the selector ranks on them.

## API

```python
from shared_utils import compile_model, fit_and_summarize      # main path
from shared_utils import fit_model, to_arviz_prior, cleanup_csv_files  # GQ-only recipes
from shared_utils import check_convergence, compute_loo, get_divergences
from shared_utils import write_json, NumpyEncoder, ensure_dir, resolve_path, project_root
```

`fit_and_summarize(model, data, *, save_dir=..., save_netcdf=True)` compiles
nothing (pass a compiled model), samples with NUTS, computes the ArviZ summary,
convergence result, and PSIS-LOO, thins parameter draws, writes the artifacts,
and deletes the CmdStan CSVs. The InferenceData gets an `observed_data` group
from `data["y"]` by default; pass `observed_data=`, `coords=`, `dims=` for
other layouts. Full docstrings in `src/shared_utils/`.

## Tests

Two tiers, both run in CI:

| Tier | Command | What it proves |
|---|---|---|
| Unit (mocked, synthetic InferenceData) | `uv run --extra dev pytest -m "not integration"` | branch logic, JSON encoding, CSV cleanup, argument validation |
| Integration (real CmdStan) | `SHARED_UTILS_REQUIRE_CMDSTAN=1 uv run --extra dev pytest -m integration` | the six models under `tests/stan/` compile and sample; the exact artifact file set and JSON layouts; parameter recovery on known truth; real divergences are flagged; LOO ranks the correct likelihood; the three recipes in the `python-environment` skill run as written |

Without a CmdStan installation the integration tier is skipped locally. With
`SHARED_UTILS_REQUIRE_CMDSTAN=1` (as in CI) a missing toolchain is an error, so
a skipped suite can never read as a passing one. Install with
`uv run python -m cmdstanpy.install_cmdstan`.

Lint and types: `uv run --extra dev ruff check .` and `uv run --extra dev pyright`.
