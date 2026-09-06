#!/usr/bin/env python
"""Posterior fit → the canonical fit artifacts (fit-pipeline skill).

Copy this file into ``<experiment_dir>/fit/``, rewrite ``build_stan_data()`` for
the model's ``data {}`` block, and run from the project root::

    uv run python experiments/<id>/fit/posterior_fit.py \\
        --model experiments/<id>/model.stan --data eda/data.cleaned.parquet \\
        --out experiments/<id>/fit --name <id>

Probe first (``--chains 4 --warmup 100 --samples 100 --no-netcdf --thin 0``),
then the full run. Stan-JSON ``--data`` passes through unchanged (recovery fits
consume ``fake_data.json`` this way). Everything below the ADAPT section is the
artifact contract — change it deliberately, not per experiment.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np
import pandas as pd
from cmdstanpy import CmdStanMCMC, CmdStanModel

# Convergence thresholds (convergence-diagnostics skill). The dispatching
# workflow audits a PASS against the same numbers.
RHAT_MAX = 1.01
ESS_MIN = 400
DIVERGENCES_MAX = 0
EBFMI_MIN = 0.3

SUMMARY_COLUMNS = ["mean", "sd", "hdi_3%", "hdi_97%", "ess_bulk", "ess_tail", "r_hat"]


# ---------------------------------------------------------------------------
# ADAPT: map the dispatched dataset onto the model's data block.
# ---------------------------------------------------------------------------
def build_stan_data(data_path: Path) -> dict[str, Any]:
    """Return the dict the model's ``data {}`` block declares.

    Stan-JSON input passes through unchanged. For a data frame, build the dict
    explicitly — every model is different, so this is the one function you are
    expected to rewrite. Keep the outcome under the name the model uses (``y``
    by default) so the InferenceData gets an ``observed_data`` group.
    """
    if data_path.suffix == ".json":
        return json.loads(data_path.read_text())
    frame = (
        pd.read_parquet(data_path)
        if data_path.suffix == ".parquet"
        else pd.read_csv(data_path)
    )
    raise NotImplementedError(
        f"build_stan_data: map the {frame.shape[1]} columns of {data_path.name} "
        "onto the model's data block (N, y, covariates, group indices, ...)"
    )


# ---------------------------------------------------------------------------
# Contract: sampling defaults, conversion, diagnostics, artifacts.
# ---------------------------------------------------------------------------
class NumpyEncoder(json.JSONEncoder):
    """numpy scalars and arrays are not JSON-serializable by default."""

    def default(self, o: Any) -> Any:
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, cls=NumpyEncoder))


def sample(
    model: CmdStanModel,
    stan_data: dict[str, Any],
    *,
    chains: int = 4,
    iter_warmup: int = 1000,
    iter_sampling: int = 1000,
    adapt_delta: float = 0.9,
    seed: int | None = None,
    output_dir: Path | str | None = None,
    **kwargs: Any,
) -> CmdStanMCMC:
    """NUTS with the workflow defaults. Progress output is always off.

    Do not pass ``refresh=0``: CmdStanPy >= 1.3 requires a positive integer.
    """
    if iter_warmup <= 0:
        raise ValueError(
            "iter_warmup must be > 0 for NUTS; GQ-only programs belong in "
            "prior_predictive.py / fake_data.py (fixed_param)"
        )
    return model.sample(
        data=stan_data,
        chains=chains,
        iter_warmup=iter_warmup,
        iter_sampling=iter_sampling,
        adapt_delta=adapt_delta,
        seed=seed,
        output_dir=str(output_dir) if output_dir else None,
        show_progress=False,
        show_console=False,  # refresh stays at CmdStan's default: 0 is rejected
        save_warmup=False,
        **kwargs,
    )


def to_inference_data(
    fit: CmdStanMCMC,
    stan_data: dict[str, Any],
    *,
    observed: str = "y",
    posterior_predictive: str = "y_rep",
    log_likelihood: str = "log_lik",
    coords: dict | None = None,
    dims: dict | None = None,
) -> az.InferenceData:
    """Explicit groups — never bare ``az.from_cmdstanpy(fit)``.

    Only variables the program declares are requested; asking ArviZ for a
    missing ``y_rep`` raises. ``observed_data`` is attached from the Stan data
    when the outcome is present under ``observed``.
    """
    declared = set(fit.metadata.stan_vars)
    return az.from_cmdstanpy(
        fit,
        posterior_predictive=(
            [posterior_predictive] if posterior_predictive in declared else None
        ),
        log_likelihood=log_likelihood if log_likelihood in declared else None,
        observed_data=(
            {observed: np.asarray(stan_data[observed])} if observed in stan_data else None
        ),
        coords=coords,
        dims=dims,
    )


def summarize(idata: az.InferenceData) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Parameter summary plus the convergence decision, from ArviZ only."""
    summary = az.summary(idata)
    summary = summary[[c for c in SUMMARY_COLUMNS if c in summary.columns]]
    assert isinstance(summary, pd.DataFrame)
    n_divergent = (
        int(idata["sample_stats"]["diverging"].values.sum())
        if "sample_stats" in idata.groups() and "diverging" in idata["sample_stats"]
        else 0
    )
    max_rhat = float(summary["r_hat"].max())
    min_ess_bulk = float(summary["ess_bulk"].min())
    min_ess_tail = float(summary["ess_tail"].min())
    convergence = {
        "max_rhat": max_rhat,
        "min_ess_bulk": min_ess_bulk,
        "min_ess_tail": min_ess_tail,
        "n_divergent": n_divergent,
        "converged": bool(
            max_rhat < RHAT_MAX
            and min_ess_bulk >= ESS_MIN
            and min_ess_tail >= ESS_MIN
            and n_divergent <= DIVERGENCES_MAX
        ),
    }
    return summary, convergence


def loo(idata: az.InferenceData) -> dict[str, Any] | None:
    """PSIS-LOO with the Pareto-k breakdown; None when there is no log_lik."""
    if "log_likelihood" not in idata.groups():
        return None
    result = az.loo(idata, pointwise=True)
    k = np.asarray(result.pareto_k)
    return {
        "elpd_loo": float(result.elpd_loo),
        "se": float(result.se),
        "p_loo": float(result.p_loo),
        "k_good": int(np.sum(k < 0.5)),
        "k_ok": int(np.sum((k >= 0.5) & (k < 0.7))),
        "k_bad": int(np.sum((k >= 0.7) & (k < 1.0))),
        "k_very_bad": int(np.sum(k >= 1.0)),
    }


def sampler_diagnostics(
    fit: CmdStanMCMC, idata: az.InferenceData
) -> tuple[dict[str, int], list[str]]:
    """CmdStanPy's own counters plus ArviZ E-BFMI, with human-readable warnings."""
    num_divergences = int(np.sum(fit.divergences)) if fit.divergences is not None else 0
    max_treedepth = int(np.sum(fit.max_treedepths)) if fit.max_treedepths is not None else 0
    bfmi = az.bfmi(idata) if "sample_stats" in idata.groups() else np.array([])
    ebfmi_warnings = int(np.sum(bfmi < EBFMI_MIN))
    warnings = []
    if num_divergences:
        warnings.append(f"{num_divergences} divergent transitions")
    if max_treedepth:
        warnings.append(f"{max_treedepth} transitions exceeded max treedepth")
    for i, value in enumerate(bfmi):
        if value < EBFMI_MIN:
            warnings.append(f"Chain {i + 1}: low E-BFMI ({value:.3f})")
    return {
        "num_divergences": num_divergences,
        "max_treedepth_exceeded": max_treedepth,
        "ebfmi_warnings": ebfmi_warnings,
    }, warnings


def thin(idata: az.InferenceData, n: int = 200, seed: int = 0) -> dict[str, np.ndarray]:
    """``n`` parameter-only draws per variable, sample axis first."""
    subset = az.extract(idata, group="posterior", num_samples=n, rng=seed)
    return {name: np.moveaxis(subset[name].values, -1, 0) for name in subset.data_vars}


def cleanup_csvs(fit: CmdStanMCMC) -> int:
    """Delete CmdStan's per-chain CSVs; draws are already in memory."""
    runset = getattr(fit, "runset", None)
    deleted = 0
    for csv in getattr(runset, "csv_files", None) or []:
        path = Path(csv)
        if path.exists():
            path.unlink()
            deleted += 1
    return deleted


def write_artifacts(
    out_dir: Path,
    *,
    model_name: str,
    idata: az.InferenceData,
    param_summary: pd.DataFrame,
    convergence: dict[str, Any],
    diagnostics: dict[str, int],
    loo_result: dict[str, Any] | None,
    thinned: dict[str, np.ndarray] | None,
    save_netcdf: bool = True,
    warnings: list[str] | None = None,
) -> list[str]:
    """Write the contract files; returns their absolute paths (the manifest)."""
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    names = ["summary.json", "diagnostics.json"]
    if loo_result is not None:
        names.append("loo.json")
    if thinned:
        names.append("thinned_draws.npz")
    if save_netcdf:
        names.append("posterior.nc")
    artifacts = [str(out_dir / name) for name in names]

    summary: dict[str, Any] = {
        "model_name": model_name,
        "param_summary": param_summary.to_dict(),
        "convergence": convergence,
        "diagnostics": diagnostics,
        "artifacts": artifacts,
        "warnings": list(warnings or []),
    }
    if loo_result is not None:
        summary["loo"] = loo_result
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "diagnostics.json", diagnostics)
    if loo_result is not None:
        write_json(out_dir / "loo.json", loo_result)
    if thinned:
        np.savez_compressed(
            str(out_dir / "thinned_draws.npz"),
            **thinned,  # pyright: ignore[reportArgumentType]
        )
    if save_netcdf:
        idata.to_netcdf(str(out_dir / "posterior.nc"))
    return artifacts


def run(
    model_path: Path | str,
    stan_data: dict[str, Any],
    out_dir: Path | str,
    *,
    model_name: str = "model",
    save_netcdf: bool = True,
    n_thinned: int = 200,
    cleanup: bool = True,
    observed: str = "y",
    coords: dict | None = None,
    dims: dict | None = None,
    **sample_kwargs: Any,
) -> dict[str, Any]:
    """Compile, sample, diagnose, and write the artifacts. Returns the summary."""
    model = CmdStanModel(stan_file=str(model_path))
    fit = sample(model, stan_data, **sample_kwargs)
    warnings: list[str] = []
    try:
        idata = to_inference_data(
            fit, stan_data, observed=observed, coords=coords, dims=dims
        )
        param_summary, convergence = summarize(idata)
        diagnostics, diag_warnings = sampler_diagnostics(fit, idata)
        warnings.extend(diag_warnings)
        try:
            loo_result = loo(idata)
        except Exception as exc:  # LOO is diagnostic; a failure must not lose the fit
            loo_result = None
            warnings.append(f"LOO computation failed: {exc}")
        thinned = thin(idata, n_thinned) if n_thinned > 0 else None
    finally:
        if cleanup:
            deleted = cleanup_csvs(fit)
            if deleted:
                warnings.append(f"CmdStan CSV files deleted ({deleted} files)")
    artifacts = write_artifacts(
        Path(out_dir),
        model_name=model_name,
        idata=idata,
        param_summary=param_summary,
        convergence=convergence,
        diagnostics=diagnostics,
        loo_result=loo_result,
        thinned=thinned,
        save_netcdf=save_netcdf,
        warnings=warnings,
    )
    return {
        "model_name": model_name,
        "param_summary": param_summary,
        "convergence": convergence,
        "diagnostics": diagnostics,
        "loo": loo_result,
        "artifacts": artifacts,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Posterior fit → canonical artifacts")
    parser.add_argument("--model", required=True, type=Path, help="model.stan")
    parser.add_argument("--data", required=True, type=Path, help="dataset or Stan JSON")
    parser.add_argument("--out", required=True, type=Path, help="stage directory")
    parser.add_argument("--name", default=None, help="model_name (default: model stem)")
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--warmup", type=int, default=1000)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--adapt-delta", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--thin", type=int, default=200, help="thinned draws (0 = skip)")
    parser.add_argument("--no-netcdf", action="store_true", help="skip posterior.nc")
    parser.add_argument("--observed", default="y", help="outcome name in the data block")
    args = parser.parse_args(argv)

    result = run(
        args.model,
        build_stan_data(args.data),
        args.out,
        model_name=args.name or args.model.stem,
        save_netcdf=not args.no_netcdf,
        n_thinned=args.thin,
        observed=args.observed,
        chains=args.chains,
        iter_warmup=args.warmup,
        iter_sampling=args.samples,
        adapt_delta=args.adapt_delta,
        seed=args.seed,
    )
    conv = result["convergence"]
    line = (
        f"{result['model_name']}: {'CONVERGED' if conv['converged'] else 'NOT CONVERGED'}"
        f" rhat_max={conv['max_rhat']:.3f}"
        f" ess_min={min(conv['min_ess_bulk'], conv['min_ess_tail']):.0f}"
        f" divergences={conv['n_divergent']}"
    )
    if result["loo"]:
        line += f" elpd_loo={result['loo']['elpd_loo']:.1f}±{result['loo']['se']:.1f}"
    print(line)
    for warning in result["warnings"]:
        print(f"  warning: {warning}")
    print("artifacts:", ", ".join(Path(p).name for p in result["artifacts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
