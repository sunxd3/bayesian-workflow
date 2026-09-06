---
name: inferencedata-handling
description: ArviZ InferenceData creation from CmdStanPy — variable naming conventions, conversion arguments, common failures.
user-invocable: false
---

# InferenceData Handling

Use this skill when you need to construct an ArviZ `InferenceData` object
manually from a CmdStanPy fit. **Most workflows do not need to do this
directly** — the `fit-pipeline` reference scripts construct InferenceData with
the right groups. This skill documents (a) the conventions those scripts
follow, so downstream code can rely on them, and (b) the manual conversion
pattern when you need it.

## Conversion pattern

**Never use bare `az.from_cmdstanpy(fit)`.** It dumps everything into the
`posterior` group, breaking downstream PPC, LOO, and prior workflows.

```python
import arviz as az

idata = az.from_cmdstanpy(
    fit,
    posterior_predictive=["y_rep"],         # variables ending in _rep
    log_likelihood="log_lik",               # per-obs log-lik for LOO
    observed_data={"y": y_obs},             # original data
    coords={"obs_id": np.arange(N)},        # dimension labels
    dims={"y_rep": ["obs_id"], "log_lik": ["obs_id"]},
)
```

## Variable naming conventions

| Stan variable | InferenceData group | Notes |
|---|---|---|
| `*_rep` | `posterior_predictive` | Replicated data for PPC |
| `log_lik` | `log_likelihood` | Per-observation log-lik for LOO |
| Parameters | `posterior` | Default location |
| `*_prior` | `prior` | Prior predictive (when sampled separately) |

Use `y_obs` for observed data and `y_rep` for replications throughout the
workflow. Mixing `y`, `y_pred`, `y_sim` causes cascading KeyErrors across
downstream agents.

## Case sensitivity

Stan lowercases all variable names internally. `Y1_rep` in Stan → `y1_rep` in
CmdStanPy output. Always use lowercase when referencing variables in Python.

## Validation

When you construct InferenceData manually, sanity-check the required groups
before saving:

```python
assert "posterior" in idata.groups()
assert "posterior_predictive" in idata.groups()
assert "y_rep" in idata.posterior_predictive
assert "log_likelihood" in idata.groups()
idata.to_netcdf("posterior.nc")
```

`fit-pipeline > references/posterior_fit.py` writes `posterior.nc` with these groups; the repository's tests assert them.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: 'y_rep'` in PPC | `posterior_predictive=` not specified | Pass `posterior_predictive=["y_rep"]` |
| `KeyError: 'log_lik'` from LOO | `log_likelihood=` not specified | Pass `log_likelihood="log_lik"` |
| `KeyError: 'Y_rep'` | Case mismatch (Stan lowercases) | Use lowercase in Python |
| Dimension mismatch in plots | Missing `coords` / `dims` | Provide coordinate labels for indexed variables |

## Loading

```python
idata = az.from_netcdf("posterior.nc")
print("Groups:", idata.groups())
```

## Related skills

- `fit-pipeline` — the reference scripts construct InferenceData for the posterior fit (`posterior_fit.py`) and the prior predictive run (`prior_predictive.py`: `prior` + `prior_predictive` groups from a GQ-only `prior_model.stan` fit).
- `stan > Generated-Quantities-Only Programs` — how to write the GQ-only programs those runs consume.
