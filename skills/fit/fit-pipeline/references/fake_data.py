#!/usr/bin/env python
"""Fake-data simulation and parameter recovery check (fit-pipeline skill).

Copy into ``<experiment_dir>/simulation/`` and run from the project root.

1. Simulate one dataset from ``simulator.stan`` (GQ-only; true parameters
   enter as data, stan skill Pattern 2)::

       uv run python experiments/<id>/simulation/fake_data.py simulate \\
           --simulator experiments/<id>/simulation/simulator.stan \\
           --data experiments/<id>/stan_data.json \\
           --true '{"mu": 2.0, "sigma": 1.5}' --out experiments/<id>/simulation

   writes ``fake_data.json`` (the data dict with the outcome replaced by the
   simulated draw) and ``true_params.json``.

2. Fit the inference model to it with the posterior_fit reference::

       uv run python .../posterior_fit.py --model experiments/<id>/model.stan \\
           --data experiments/<id>/simulation/fake_data.json \\
           --out experiments/<id>/simulation/fit --name recovery --no-netcdf

3. Check recovery — the audited ``coverage_90`` and ``max_bias_z``::

       uv run python experiments/<id>/simulation/fake_data.py check \\
           --fit experiments/<id>/simulation/fit \\
           --true experiments/<id>/simulation/true_params.json \\
           --out experiments/<id>/simulation
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np
from cmdstanpy import CmdStanModel


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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, cls=NumpyEncoder))


def load_json_or_literal(value: str) -> dict[str, Any]:
    """``--true`` accepts a JSON object literal or a path to a JSON file."""
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text())
    return json.loads(value)


def simulate(
    simulator_path: Path | str,
    stan_data: dict[str, Any],
    true_params: dict[str, Any],
    *,
    seed: int | None = None,
    var: str = "y_rep",
    output_dir: Path | str | None = None,
) -> np.ndarray:
    """One fixed_param draw of ``var`` with the true parameters passed as data."""
    model = CmdStanModel(stan_file=str(simulator_path))
    fit = model.sample(
        data={**stan_data, **true_params},
        chains=1,
        iter_sampling=1,
        iter_warmup=0,
        fixed_param=True,
        adapt_engaged=False,
        seed=seed,
        output_dir=str(output_dir) if output_dir else None,
        show_progress=False,
        show_console=False,
    )
    draw = np.asarray(fit.stan_variable(var))[0]
    for csv in getattr(getattr(fit, "runset", None), "csv_files", None) or []:
        Path(csv).unlink(missing_ok=True)
    return draw


def write_fake_dataset(
    stan_data: dict[str, Any],
    y_synth: np.ndarray,
    true_params: dict[str, Any],
    out_dir: Path | str,
    *,
    observed: str = "y",
) -> tuple[Path, Path]:
    out_dir = Path(out_dir).resolve()
    data_path = out_dir / "fake_data.json"
    true_path = out_dir / "true_params.json"
    write_json(data_path, {**stan_data, observed: y_synth})
    write_json(true_path, true_params)
    return data_path, true_path


def _load_draws(fit_dir: Path) -> dict[str, np.ndarray]:
    """Posterior draws with the sample axis first, from posterior.nc when it
    exists (full posterior) and from thinned_draws.npz otherwise."""
    nc = fit_dir / "posterior.nc"
    if nc.exists():
        posterior = az.from_netcdf(nc)["posterior"]
        return {
            str(name): np.asarray(posterior[name].values).reshape(-1, *posterior[name].shape[2:])
            for name in posterior.data_vars
        }
    npz = np.load(fit_dir / "thinned_draws.npz")
    return {name: npz[name] for name in npz.files}


def recovery(
    fit_dir: Path | str,
    true_params: dict[str, Any],
    *,
    interval: float = 0.90,
) -> dict[str, Any]:
    """``coverage_90``: share of true values inside the central 90% posterior
    interval; ``max_bias_z``: max |posterior mean − true| / posterior sd. Data
    entries in ``true_params`` that are not parameters are ignored."""
    draws = _load_draws(Path(fit_dir))
    alpha = (1.0 - interval) / 2.0
    per_parameter: dict[str, Any] = {}
    covered: list[bool] = []
    zs: list[float] = []
    for name, truth in true_params.items():
        if name not in draws:
            continue
        arr = draws[name]
        t = np.asarray(truth, dtype=float)
        lo, hi = np.quantile(arr, [alpha, 1.0 - alpha], axis=0)
        mean, sd = arr.mean(axis=0), arr.std(axis=0, ddof=1)
        inside = (lo <= t) & (t <= hi)
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.abs(mean - t) / sd
        covered.extend(np.ravel(inside).tolist())
        zs.extend(np.ravel(z).tolist())
        per_parameter[name] = {
            "true": t, "mean": mean, "sd": sd, "lo": lo, "hi": hi,
            "covered": inside, "bias_z": z,
        }
    if not covered:
        raise ValueError("no true_params entry matches a posterior variable")
    return {
        "interval": interval,
        "n_parameters": len(covered),
        "coverage_90": float(np.mean(covered)),
        "max_bias_z": float(np.nanmax(zs)),
        "per_parameter": per_parameter,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fake-data simulation and recovery")
    sub = parser.add_subparsers(dest="command", required=True)

    sim = sub.add_parser("simulate", help="draw one fake dataset from simulator.stan")
    sim.add_argument("--simulator", required=True, type=Path)
    sim.add_argument("--data", required=True, type=Path, help="Stan JSON data")
    sim.add_argument("--true", required=True, help="JSON object literal or path")
    sim.add_argument("--out", required=True, type=Path)
    sim.add_argument("--seed", type=int, default=None)
    sim.add_argument("--observed", default="y")
    sim.add_argument("--var", default="y_rep")

    chk = sub.add_parser("check", help="coverage and bias of a recovery fit")
    chk.add_argument("--fit", required=True, type=Path, help="recovery fit directory")
    chk.add_argument("--true", required=True, help="true_params.json or literal")
    chk.add_argument("--out", required=True, type=Path)

    args = parser.parse_args(argv)
    if args.command == "simulate":
        stan_data = json.loads(args.data.read_text())
        true_params = load_json_or_literal(args.true)
        y = simulate(args.simulator, stan_data, true_params, seed=args.seed, var=args.var)
        data_path, true_path = write_fake_dataset(
            stan_data, y, true_params, args.out, observed=args.observed
        )
        print(f"simulated {y.size} observations → {data_path.name}, {true_path.name}")
        return 0

    result = recovery(args.fit, load_json_or_literal(args.true))
    out_path = Path(args.out).resolve() / "recovery.json"
    write_json(out_path, result)
    print(
        f"recovery: coverage_90={result['coverage_90']:.2f} "
        f"max_bias_z={result['max_bias_z']:.2f} ({result['n_parameters']} parameters)"
        f" → {out_path.name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
