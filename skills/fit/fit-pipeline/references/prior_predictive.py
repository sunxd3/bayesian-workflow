#!/usr/bin/env python
"""Prior predictive simulation from a GQ-only program (fit-pipeline skill).

Copy into ``<experiment_dir>/prior_predictive/`` and run from the project root::

    uv run python experiments/<id>/prior_predictive/prior_predictive.py \\
        --model experiments/<id>/prior_predictive/prior_model.stan \\
        --data experiments/<id>/stan_data.json --out experiments/<id>/prior_predictive \\
        --draws 1000 --bounds <lo> <hi>

``prior_model.stan`` mirrors the priors of ``model.stan`` via ``_rng`` and
generates ``y_rep`` (stan skill, Pattern 1). The data file is the inference
data dict — extra entries such as the outcome are ignored by Stan, and the
outcome is attached as ``observed_data`` for the plots. With ``--bounds`` the
script also writes ``prior_check.json`` with the audited ``extreme_draw_pct``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np
from cmdstanpy import CmdStanMCMC, CmdStanModel


class NumpyEncoder(json.JSONEncoder):
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


def load_stan_data(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def simulate(
    model_path: Path | str,
    stan_data: dict[str, Any],
    *,
    draws: int = 1000,
    seed: int | None = None,
    output_dir: Path | str | None = None,
) -> CmdStanMCMC:
    """One chain of ``draws`` fixed_param iterations — no warmup, no adaptation,
    and no ``adapt_delta`` (CmdStanPy rejects adapt_* when adaptation is off)."""
    model = CmdStanModel(stan_file=str(model_path))
    return model.sample(
        data=stan_data,
        chains=1,
        iter_sampling=draws,
        iter_warmup=0,
        fixed_param=True,
        adapt_engaged=False,
        seed=seed,
        output_dir=str(output_dir) if output_dir else None,
        show_progress=False,
        show_console=False,
    )


def to_inference_data(
    fit: CmdStanMCMC,
    stan_data: dict[str, Any],
    *,
    observed: str = "y",
    prior_predictive: str = "y_rep",
) -> az.InferenceData:
    """``prior`` + ``prior_predictive`` groups, observed data attached when present."""
    declared = set(fit.metadata.stan_vars)
    return az.from_cmdstanpy(
        prior=fit,
        prior_predictive=[prior_predictive] if prior_predictive in declared else None,
        observed_data=(
            {observed: np.asarray(stan_data[observed])} if observed in stan_data else None
        ),
    )


def extreme_draw_pct(
    idata: az.InferenceData, lo: float, hi: float, *, var: str = "y_rep"
) -> float:
    """Percent of prior predictive draws outside the assigned [lo, hi] bounds."""
    y = np.asarray(idata["prior_predictive"][var].values)
    return float(100.0 * np.mean((y < lo) | (y > hi)))


def cleanup_csvs(fit: CmdStanMCMC) -> int:
    runset = getattr(fit, "runset", None)
    deleted = 0
    for csv in getattr(runset, "csv_files", None) or []:
        path = Path(csv)
        if path.exists():
            path.unlink()
            deleted += 1
    return deleted


def run(
    model_path: Path | str,
    stan_data: dict[str, Any],
    out_dir: Path | str,
    *,
    draws: int = 1000,
    seed: int | None = None,
    bounds: tuple[float, float] | None = None,
    observed: str = "y",
    var: str = "y_rep",
    cleanup: bool = True,
) -> dict[str, Any]:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    fit = simulate(model_path, stan_data, draws=draws, seed=seed)
    try:
        idata = to_inference_data(fit, stan_data, observed=observed, prior_predictive=var)
    finally:
        if cleanup:
            cleanup_csvs(fit)
    nc_path = out_dir / "prior_predictive.nc"
    idata.to_netcdf(str(nc_path))
    result: dict[str, Any] = {"n_draws": draws, "artifacts": [str(nc_path)]}
    if bounds is not None:
        lo, hi = bounds
        pct = extreme_draw_pct(idata, lo, hi, var=var)
        check = {
            "variable": var,
            "bounds": [lo, hi],
            "n_draws": draws,
            "extreme_draw_pct": pct,
        }
        check_path = out_dir / "prior_check.json"
        check_path.write_text(json.dumps(check, indent=2, cls=NumpyEncoder))
        result["extreme_draw_pct"] = pct
        result["artifacts"].append(str(check_path))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prior predictive simulation")
    parser.add_argument("--model", required=True, type=Path, help="prior_model.stan (GQ-only)")
    parser.add_argument("--data", required=True, type=Path, help="Stan JSON data")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--draws", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--bounds", type=float, nargs=2, metavar=("LO", "HI"),
        help="assigned plausibility bounds; writes prior_check.json",
    )
    parser.add_argument("--observed", default="y")
    parser.add_argument("--var", default="y_rep")
    args = parser.parse_args(argv)

    result = run(
        args.model, load_stan_data(args.data), args.out,
        draws=args.draws, seed=args.seed,
        bounds=tuple(args.bounds) if args.bounds else None,
        observed=args.observed, var=args.var,
    )
    line = f"prior predictive: {result['n_draws']} draws"
    if "extreme_draw_pct" in result:
        line += f", extreme_draw_pct={result['extreme_draw_pct']:.2f}"
    print(line)
    print("artifacts:", ", ".join(Path(p).name for p in result["artifacts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
