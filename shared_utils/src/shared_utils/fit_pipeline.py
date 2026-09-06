"""Fit pipeline: one-call model fitting with diagnostics and artifact management."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import arviz as az
import numpy as np
import pandas as pd
from cmdstanpy import CmdStanModel

from .diagnostics import ConvergenceResult, LOOResult, check_convergence, compute_loo
from .io import to_arviz, write_json
from .paths import ensure_dir
from .stan import fit_model

logger = logging.getLogger(__name__)


@dataclass
class FitResult:
    """Result of a Stan model fit with diagnostics and optional thinned draws."""

    param_summary: pd.DataFrame
    convergence: ConvergenceResult
    loo: LOOResult | None
    diagnostics: dict
    thinned_draws: dict[str, np.ndarray] | None
    model_name: str
    artifacts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def loo_dict(self) -> dict[str, float | int] | None:
        """LOO results as the flat dict written to loo.json (None if no LOO)."""
        if self.loo is None:
            return None
        return {
            "elpd_loo": self.loo.elpd_loo,
            "se": self.loo.se,
            "p_loo": self.loo.p_loo,
            "k_good": self.loo.k_good,
            "k_ok": self.loo.k_ok,
            "k_bad": self.loo.k_bad,
            "k_very_bad": self.loo.k_very_bad,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        result: dict[str, Any] = {
            "model_name": self.model_name,
            "param_summary": self.param_summary.to_dict(),
            "convergence": {
                "max_rhat": self.convergence.max_rhat,
                "min_ess_bulk": self.convergence.min_ess_bulk,
                "min_ess_tail": self.convergence.min_ess_tail,
                "n_divergent": self.convergence.n_divergent,
                "converged": self.convergence.converged,
            },
            "diagnostics": self.diagnostics,
            "artifacts": self.artifacts,
            "warnings": self.warnings,
        }
        loo = self.loo_dict()
        if loo is not None:
            result["loo"] = loo
        return result

    def save(self, output_dir: Path | str) -> list[str]:
        """Save results to output directory.

        Writes summary.json, diagnostics.json, loo.json (if available),
        and thinned_draws.npz (if available).

        Returns list of saved file paths.
        """
        output_dir = ensure_dir(output_dir)
        summary_path = output_dir / "summary.json"
        diag_path = output_dir / "diagnostics.json"
        loo = self.loo_dict()
        loo_path = output_dir / "loo.json" if loo is not None else None
        draws_path = (
            output_dir / "thinned_draws.npz" if self.thinned_draws is not None else None
        )
        saved = [str(p) for p in (summary_path, diag_path, loo_path, draws_path) if p]

        # Register the files BEFORE writing summary.json so the manifest it
        # carries lists every artifact of this save, itself included.
        existing = set(self.artifacts)
        self.artifacts.extend(p for p in saved if p not in existing)

        write_json(summary_path, self.to_dict())
        write_json(diag_path, self.diagnostics)
        if loo_path is not None:
            write_json(loo_path, loo)
        if draws_path is not None and self.thinned_draws is not None:
            np.savez_compressed(
                str(draws_path),
                **self.thinned_draws,  # pyright: ignore[reportArgumentType]
            )
        return saved


def _extract_sampler_diagnostics(
    fit: Any,
) -> tuple[dict[str, Any], list[str]]:
    """Extract sampler diagnostics from CmdStanMCMC fit."""
    warnings: list[str] = []
    method_vars = fit.method_variables()

    # Divergences
    divergent = method_vars.get("divergent__", np.array([0]))
    num_divergences = int(divergent.sum())

    # Max treedepth exceeded
    treedepths = method_vars.get("treedepth__", np.array([0]))
    max_td = 10
    try:
        max_td = fit.metadata.cmdstan_config.get("max_depth", 10)
    except (AttributeError, KeyError):
        pass
    max_treedepth_exceeded = int((treedepths >= max_td).sum())

    # E-BFMI per chain
    energies = method_vars.get("energy__", None)
    ebfmi_warnings = 0
    if energies is not None and energies.size > 1:
        n_chains = energies.shape[1] if energies.ndim > 1 else 1
        for chain_idx in range(n_chains):
            chain_e = energies[:, chain_idx] if energies.ndim > 1 else energies
            diff = np.diff(chain_e)
            var_e = np.var(chain_e)
            if var_e > 0:
                ebfmi = float(np.mean(diff**2) / var_e)
                if ebfmi < 0.3:
                    ebfmi_warnings += 1
                    warnings.append(
                        f"Chain {chain_idx + 1}: low E-BFMI ({ebfmi:.3f})"
                    )

    if num_divergences > 0:
        warnings.append(f"{num_divergences} divergent transitions")
    if max_treedepth_exceeded > 0:
        warnings.append(
            f"{max_treedepth_exceeded} transitions exceeded max treedepth"
        )

    diagnostics = {
        "num_divergences": num_divergences,
        "max_treedepth_exceeded": max_treedepth_exceeded,
        "ebfmi_warnings": ebfmi_warnings,
    }
    return diagnostics, warnings


def _thin_draws(
    idata: Any,
    n_thinned_draws: int,
) -> dict[str, np.ndarray]:
    """Thin posterior draws by stacking chains and taking every Nth draw."""
    posterior = idata.posterior
    n_chains = posterior.sizes["chain"]
    n_draws = posterior.sizes["draw"]
    total = n_chains * n_draws
    step = max(1, total // n_thinned_draws)

    thinned: dict[str, np.ndarray] = {}
    for var_name in posterior.data_vars:
        arr = posterior[var_name].values  # (chains, draws, ...)
        shape = arr.shape
        combined = arr.reshape(shape[0] * shape[1], *shape[2:])
        thinned[var_name] = combined[::step][:n_thinned_draws]

    return thinned


def cleanup_csv_files(fit: Any) -> int:
    """Delete CmdStan CSV output files to reclaim disk space.

    CmdStan writes one CSV per chain containing all draws + method variables.
    Typical sizes: ~5-20 MB/chain for small models (< 100 params), 50-500 MB/chain
    for models with large generated quantities (log_lik[N], y_rep[N] with N > 1000).
    A 4-chain fit can easily produce 200 MB - 2 GB of CSVs. In a containerized
    environment with limited disk (typically 5-10 GB workspace), this adds up fast
    across multiple model fits.

    Prints each deletion so the agent sees exactly what was removed.
    Returns number of files deleted.
    """
    runset = getattr(fit, "runset", None)
    if runset is None:
        return 0
    csv_files = getattr(runset, "csv_files", None)
    if csv_files is None:
        csv_files = getattr(runset, "_csv_files", None)
    if csv_files is None:
        return 0
    deleted = 0
    total_bytes = 0
    for csv_path in csv_files:
        p = Path(csv_path)
        try:
            if p.exists():
                size = p.stat().st_size
                p.unlink()
                mb = size / (1024 * 1024)
                print(f"[fit_pipeline] Deleted {p.name} ({mb:.1f} MB)")
                total_bytes += size
                deleted += 1
        except OSError as e:
            print(f"[fit_pipeline] WARNING: Failed to delete {csv_path}: {e}")
            logger.warning("Failed to delete CSV %s: %s", csv_path, e)
    if deleted:
        mb = total_bytes / (1024 * 1024)
        print(f"[fit_pipeline] Cleaned up {deleted} CmdStan CSV file(s), freed {mb:.1f} MB total.")
    return deleted


# Backward-compatible alias
_cleanup_csv_files = cleanup_csv_files



def fit_and_summarize(
    model: CmdStanModel,
    data: Mapping[str, Any] | str | Path,
    *,
    model_name: str = "model",
    chains: int = 4,
    iter_warmup: int = 1000,
    iter_sampling: int = 1000,
    adapt_delta: float = 0.9,
    n_thinned_draws: int = 200,
    cleanup_csvs: bool = True,
    save_netcdf: bool = False,
    save_dir: Path | str | None = None,
    observed_data: dict[str, Any] | None = None,
    log_likelihood: str = "log_lik",
    posterior_predictive: list[str] | str | None = None,
    coords: dict | None = None,
    dims: dict | None = None,
    **sample_kwargs: Any,
) -> FitResult:
    """Fit a Stan model and return a comprehensive result with diagnostics.

    Args:
        model: Compiled CmdStanModel
        data: Stan data dictionary
        model_name: Name for identification in results
        chains: Number of MCMC chains
        iter_warmup: Warmup iterations per chain
        iter_sampling: Sampling iterations per chain
        adapt_delta: Target acceptance rate
        n_thinned_draws: Number of thinned draws to keep (0 to skip)
        cleanup_csvs: Delete CmdStan CSV files after extraction (default True).
            CmdStan writes ~5-20 MB/chain for small models, 50-500 MB/chain for
            models with large generated quantities. In the containerized workspace
            (typically 5-10 GB), leaving CSVs from multiple fits quickly exhausts
            disk. The draws are fully extracted before deletion — nothing is lost
            that isn't already in memory. There is almost never a reason to keep
            CSVs.
        save_netcdf: Save full InferenceData as posterior.nc (default False).
            The .nc file (typically 5-50 MB) preserves the full posterior including
            log_lik and y_rep draws that are NOT in thinned_draws.npz. You need
            this when downstream steps require:
            - Stan-generated y_rep for posterior predictive checks
            - Per-observation log_lik for LOO-PIT calibration
            - Full log_lik draws for az.compare() model comparison
            Rule of thumb: save_netcdf=True for main data fits, False for probe
            runs, simulation recovery, and prior predictive checks.
        save_dir: If provided, save results to this directory
        observed_data: Arrays for the InferenceData ``observed_data`` group.
            Defaults to ``{"y": data["y"]}`` when the Stan data mapping has a
            ``y`` entry, so the canonical model layout gets its observed data
            attached (needed downstream for PPC overlays and LOO-PIT). Pass
            explicitly when the outcome has another name, or ``{}`` to attach
            nothing.
        log_likelihood: Name of the pointwise log-likelihood variable.
        posterior_predictive: Posterior predictive variable names (default:
            ``["y_rep"]`` when the model declares it).
        coords: ArviZ coordinate labels, forwarded to ``to_arviz``.
        dims: ArviZ dimension names per variable, forwarded to ``to_arviz``.
        **sample_kwargs: Additional arguments passed to fit_model()

    Returns:
        FitResult with summary, diagnostics, and optional thinned draws
    """
    # Strip keys that are set explicitly to avoid duplicate-keyword TypeError
    _reserved = {"chains", "iter_warmup", "iter_sampling", "adapt_delta"}
    sample_kwargs = {k: v for k, v in sample_kwargs.items() if k not in _reserved}

    result_warnings: list[str] = []
    artifacts: list[str] = []
    fit = None

    try:
        # Fit the model
        fit = fit_model(
            model,
            data,
            chains=chains,
            iter_warmup=iter_warmup,
            iter_sampling=iter_sampling,
            adapt_delta=adapt_delta,
            **sample_kwargs,
        )

        # Convert to ArviZ
        if observed_data is None and isinstance(data, Mapping) and "y" in data:
            observed_data = {"y": np.asarray(data["y"])}
        idata = to_arviz(
            fit,
            observed_data=observed_data or None,
            log_likelihood=log_likelihood,
            posterior_predictive=posterior_predictive,
            coords=coords,
            dims=dims,
        )

        # Parameter summary
        param_summary = az.summary(idata)
        summary_cols = [
            "mean", "sd", "hdi_3%", "hdi_97%",
            "ess_bulk", "ess_tail", "r_hat",
        ]
        available_cols = [c for c in summary_cols if c in param_summary.columns]
        param_summary = param_summary[available_cols]
        assert isinstance(param_summary, pd.DataFrame)

        # Convergence
        convergence = check_convergence(idata)

        # LOO-CV (graceful if no log_lik)
        loo_result: LOOResult | None = None
        if hasattr(idata, "log_likelihood"):
            try:
                loo_result = compute_loo(idata)
            except Exception as e:
                result_warnings.append(f"LOO computation failed: {e}")
                logger.warning("LOO computation failed: %s", e)

        # Sampler diagnostics
        diagnostics, diag_warnings = _extract_sampler_diagnostics(fit)
        result_warnings.extend(diag_warnings)

        # Thin draws
        thinned_draws: dict[str, np.ndarray] | None = None
        if n_thinned_draws > 0:
            thinned_draws = _thin_draws(idata, n_thinned_draws)

        # Save full InferenceData if requested
        if save_netcdf and save_dir is not None:
            nc_dir = ensure_dir(save_dir)
            nc_path = nc_dir / "posterior.nc"
            idata.to_netcdf(str(nc_path))
            artifacts.append(str(nc_path))

    finally:
        if fit is not None and cleanup_csvs:
            try:
                n_deleted = cleanup_csv_files(fit)
            except Exception as exc:
                logger.warning("CSV cleanup failed: %s", exc)
                n_deleted = 0
            if n_deleted:
                result_warnings.append(
                    f"CmdStan CSV files deleted ({n_deleted} files). "
                    f"Raw draws are no longer on disk. Use thinned_draws "
                    f"for posterior access, or re-fit with cleanup_csvs=False "
                    f"to keep CSVs."
                )

    result = FitResult(
        param_summary=param_summary,
        convergence=convergence,
        loo=loo_result,
        diagnostics=diagnostics,
        thinned_draws=thinned_draws,
        model_name=model_name,
        artifacts=artifacts,
        warnings=result_warnings,
    )

    if save_dir is not None:
        result.save(save_dir)

    return result
