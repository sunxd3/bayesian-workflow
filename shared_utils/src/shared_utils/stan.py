"""Stan/CmdStanPy utilities."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cmdstanpy import CmdStanModel


def compile_model(stan_file: Path | str) -> CmdStanModel:
    """Compile a Stan model."""
    return CmdStanModel(stan_file=str(stan_file))


def fit_model(
    model: CmdStanModel,
    data: Mapping[str, Any] | str | Path,
    *,
    chains: int = 4,
    iter_warmup: int = 1000,
    iter_sampling: int = 1000,
    adapt_delta: float = 0.9,
    adapt_engaged: bool = True,
    output_dir: Path | str | None = None,
    show_progress: bool = False,
    show_console: bool = False,
    refresh: int = 100,
    fixed_param: bool = False,
    **kwargs: Any,
):
    """Fit a Stan model with sensible defaults.

    Returns the CmdStanMCMC fit object.

    Args:
        model: Compiled Stan model
        data: Stan data — a mapping of variable name to value, or the path
            to a JSON data file. Callables are rejected (a common mistake is
            passing a data-building function instead of calling it).
        chains: Number of MCMC chains
        iter_warmup: Number of warmup iterations (matches CmdStanPy API)
        iter_sampling: Number of sampling iterations (matches CmdStanPy API)
        adapt_delta: Target acceptance rate
        adapt_engaged: Whether adaptation is enabled
        output_dir: Directory for Stan output (defaults to /workspace/stan_output to prevent /tmp exhaustion)
        show_progress: Whether to show tqdm progress bar (default False to avoid
            bloating subprocess output captured by the parent agent)
        show_console: Whether to stream CmdStan stdout (default False)
        refresh: CmdStan progress refresh interval (default 1; CmdStanPy >=1.3.0 requires positive int)
        fixed_param: Use fixed_param algorithm (for prior predictive simulation).
            When True, the adapt_engaged + iter_warmup validation guard is skipped.
            The caller is responsible for passing iter_warmup=0, adapt_engaged=False.

    Raises:
        ValueError: If iter_warmup is 0 when adaptation is enabled
        TypeError: If data is not a dict, Mapping, or file path
    """
    # Validate data type - accept dict/Mapping and file paths, but block callables
    # CmdStanPy accepts dicts, Mappings, and JSON file paths (str/Path)
    if callable(data):
        raise TypeError(f"data cannot be a callable, got {type(data).__name__}")
    if not isinstance(data, (Mapping, str, Path)):
        raise TypeError(f"data must be a dict, Mapping, or file path, got {type(data).__name__}")

    # Validate warmup when adaptation is enabled (skip for fixed_param mode)
    if not fixed_param and adapt_engaged and iter_warmup <= 0:
        raise ValueError(
            f"iter_warmup must be > 0 when adapt_engaged=True, got {iter_warmup}"
        )

    # Default output_dir to /workspace/stan_output to prevent /tmp disk exhaustion
    if output_dir is None:
        workspace_output = Path("/workspace/stan_output")
        if workspace_output.parent.exists():
            workspace_output.mkdir(exist_ok=True)
            output_dir = workspace_output

    # CmdStanPy rejects any adapt_* setting when adaptation is disabled, and a
    # fixed_param run (GQ-only prior / fake-data simulation) never adapts —
    # so only forward adapt_delta when it can apply.
    adapt_delta_arg = adapt_delta if (adapt_engaged and not fixed_param) else None

    return model.sample(
        data=data,
        chains=chains,
        iter_warmup=iter_warmup,
        iter_sampling=iter_sampling,
        adapt_delta=adapt_delta_arg,
        adapt_engaged=adapt_engaged,
        show_progress=show_progress,
        show_console=show_console,
        refresh=refresh,
        output_dir=str(output_dir) if output_dir else None,
        save_warmup=False,
        fixed_param=fixed_param,
        **kwargs,
    )
