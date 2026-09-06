"""I/O utilities for saving and loading results."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np
from cmdstanpy import CmdStanMCMC

from .paths import resolve_path


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy scalar types.

    Fixes TypeError: Object of type bool_ is not JSON serializable
    by converting numpy scalars to native Python types.
    """

    def default(self, o: Any) -> Any:
        """Convert numpy scalars to native Python types."""
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)



def write_json(
    path: Path | str,
    payload: Any,
    *,
    indent: int = 2,
    base: Path | str | None = None,
) -> None:
    """Write JSON to disk, creating parent directories if needed.

    Uses NumpyEncoder to handle numpy scalar types (bool_, int64, etc.)
    that aren't natively JSON serializable.
    """
    path = resolve_path(path, base=base)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=indent, cls=NumpyEncoder)


def _stan_var_names(fit: CmdStanMCMC) -> set[str]:
    """Get the Stan variable names a fit declares, or an empty set if unknown.

    CmdStanPy >= 1.2 exposes them as ``fit.metadata.stan_vars``; older
    releases used ``stan_vars_cols`` (on the fit or its metadata). An empty
    set means "unknown" and disables downstream variable filtering.
    """
    metadata = getattr(fit, "metadata", None)
    for holder in (metadata, fit):
        if holder is None:
            continue
        for attr in ("stan_vars", "stan_vars_cols"):
            variables = getattr(holder, attr, None)
            if not variables:
                continue
            try:
                return set(variables.keys())
            except Exception:
                continue
    return set()



def _filter_present(names: Iterable[str], *, available: set[str]) -> list[str]:
    """Filter names to only those present in available set."""
    if not available:
        return list(names)
    return [name for name in names if name in available]


def _sanitize_coords_dims(coords_or_dims: dict | None) -> dict | None:
    """Convert numpy arrays to lists in coords/dims to prevent unhashable type errors.

    ArviZ conversion can fail with "TypeError: unhashable type: 'numpy.ndarray'"
    when coords or dims contain numpy arrays. This function recursively converts
    arrays to lists.
    """
    if coords_or_dims is None:
        return None

    sanitized = {}
    for key, value in coords_or_dims.items():
        if isinstance(value, np.ndarray):
            sanitized[key] = value.tolist()
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_coords_dims(value)
        elif isinstance(value, (list, tuple)):
            # Handle lists/tuples that might contain arrays
            sanitized[key] = [
                item.tolist() if isinstance(item, np.ndarray) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def to_arviz(
    fit: CmdStanMCMC,
    *,
    y_obs: np.ndarray | None = None,
    observed_data: dict[str, Any] | None = None,
    log_likelihood: str = "log_lik",
    posterior_predictive: list[str] | str | None = None,
    coords: dict | None = None,
    dims: dict | None = None,
) -> az.InferenceData:
    """Convert CmdStanPy fit to ArviZ InferenceData.

    Handles common edge cases:
    - Converts numpy arrays in coords/dims to lists (prevents unhashable type errors)
    - Validates variable names against Stan model outputs
    - Provides sensible defaults for posterior_predictive

    Args:
        fit: CmdStanMCMC fit object
        y_obs: Observed y values, stored as ``observed_data["y"]`` (shorthand)
        observed_data: Arrays for the observed_data group, keyed by name. Merged
            with ``y_obs`` (an explicit ``"y"`` here wins).
        log_likelihood: Name of log_lik variable in Stan model
        posterior_predictive: Names of posterior predictive variables
        coords: Coordinate labels (numpy arrays will be converted to lists)
        dims: Dimension names for variables (numpy arrays will be converted to lists)

    Returns:
        ArviZ InferenceData object

    Raises:
        ValueError: If fit is not a valid CmdStanMCMC object
    """
    if not isinstance(fit, CmdStanMCMC):
        raise ValueError(f"fit must be CmdStanMCMC, got {type(fit).__name__}")

    observed: dict[str, Any] = dict(observed_data) if observed_data else {}
    if y_obs is not None:
        observed.setdefault("y", y_obs)
    available = _stan_var_names(fit)

    if posterior_predictive is None:
        posterior_predictive = (
            ["y_rep"] if ("y_rep" in available or not available) else None
        )
    elif isinstance(posterior_predictive, str):
        posterior_predictive = [posterior_predictive]

    if posterior_predictive:
        posterior_predictive = _filter_present(
            posterior_predictive, available=available
        )
        if not posterior_predictive:
            posterior_predictive = None

    log_likelihood_name = (
        log_likelihood
        if log_likelihood and (log_likelihood in available or not available)
        else None
    )

    # Sanitize coords and dims to prevent unhashable type errors
    coords = _sanitize_coords_dims(coords)
    dims = _sanitize_coords_dims(dims)

    return az.from_cmdstanpy(
        fit,
        log_likelihood=log_likelihood_name,
        posterior_predictive=posterior_predictive,
        observed_data=observed or None,
        coords=coords,
        dims=dims,
    )



def to_arviz_prior(
    fit: CmdStanMCMC,
    *,
    observed_data: dict[str, Any] | None = None,
    prior_predictive: list[str] | str | None = None,
    coords: dict | None = None,
    dims: dict | None = None,
) -> az.InferenceData:
    """Convert CmdStanPy prior predictive fit to ArviZ InferenceData.

    Similar to to_arviz() but places draws in the prior group instead of posterior.

    Args:
        fit: CmdStanMCMC fit object (from prior predictive simulation)
        observed_data: Dict of observed data arrays
        prior_predictive: Names of prior predictive variables.
            Defaults to ["y_rep"] if "y_rep" is in available vars.
        coords: Coordinate labels (numpy arrays will be converted to lists)
        dims: Dimension names for variables (numpy arrays will be converted to lists)

    Returns:
        ArviZ InferenceData with prior and prior_predictive groups

    Raises:
        ValueError: If fit is not a valid CmdStanMCMC object
    """
    if not isinstance(fit, CmdStanMCMC):
        raise ValueError(f"fit must be CmdStanMCMC, got {type(fit).__name__}")

    available = _stan_var_names(fit)

    if prior_predictive is None:
        prior_predictive = (
            ["y_rep"] if ("y_rep" in available or not available) else None
        )
    elif isinstance(prior_predictive, str):
        prior_predictive = [prior_predictive]

    if prior_predictive:
        prior_predictive = _filter_present(prior_predictive, available=available)
        if not prior_predictive:
            prior_predictive = None

    # Sanitize coords and dims to prevent unhashable type errors
    coords = _sanitize_coords_dims(coords)
    dims = _sanitize_coords_dims(dims)

    return az.from_cmdstanpy(
        prior=fit,
        prior_predictive=prior_predictive,
        observed_data=observed_data,
        coords=coords,
        dims=dims,
    )



