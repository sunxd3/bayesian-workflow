"""The three recipes in `skills/python-environment/SKILL.md > Common workflows`,
run as written. If a recipe stops working, the skill is lying to the agents."""

from __future__ import annotations

import arviz as az
import numpy as np
import pytest

from .conftest import N_OBS, STAN_DIR, TRUE_MU, TRUE_SIGMA

pytestmark = pytest.mark.integration


def test_posterior_inference_recipe(compiled, normal_data, tmp_path):
    from shared_utils import compile_model, fit_and_summarize

    model = compile_model(STAN_DIR / "normal.stan")
    result = fit_and_summarize(
        model, normal_data, model_name="exp_1", save_dir=tmp_path / "fit",
        save_netcdf=True, chains=4, iter_warmup=500, iter_sampling=500,
        output_dir=tmp_path / "csv", seed=31,
    )
    assert (tmp_path / "fit" / "posterior.nc").exists()
    assert result.convergence.converged is True


def test_prior_predictive_recipe(compiled, normal_data, tmp_path):
    from shared_utils import cleanup_csv_files, compile_model, fit_model, to_arviz_prior

    prior_stan = compile_model(STAN_DIR / "normal_prior.stan")
    fit = fit_model(
        prior_stan, {"N": N_OBS}, fixed_param=True, iter_warmup=0,
        adapt_engaged=False, chains=1, iter_sampling=500,
        output_dir=tmp_path, seed=41,
    )
    idata = to_arviz_prior(
        fit, prior_predictive=["y_rep"], observed_data={"y_obs": normal_data["y"]},
    )
    deleted = cleanup_csv_files(fit)
    idata.to_netcdf(str(tmp_path / "prior_predictive.nc"))

    assert deleted == 1 and list(tmp_path.glob("*.csv")) == []
    reloaded = az.from_netcdf(tmp_path / "prior_predictive.nc")
    assert {"prior", "prior_predictive", "observed_data"} <= set(reloaded.groups())
    assert reloaded["prior_predictive"]["y_rep"].shape == (1, 500, N_OBS)
    # The GQ program really samples the declared priors: mu ~ normal(0, 10).
    mu = reloaded["prior"]["mu"].values.ravel()
    assert abs(mu.mean()) < 2.0 and 8.0 < mu.std() < 12.0
    assert reloaded["prior"]["sigma"].values.min() > 0


def test_fake_data_recipe_recovers_truth(compiled, tmp_path):
    """Simulator recipe, then fit the inference model to the fake data — the
    single-draw recovery check the fake-data-checker agent performs."""
    from shared_utils import (
        cleanup_csv_files,
        compile_model,
        fit_and_summarize,
        fit_model,
    )

    simulator = compile_model(STAN_DIR / "normal_simulator.stan")
    sim_data = {"N": N_OBS, "mu": TRUE_MU, "sigma": TRUE_SIGMA}
    sim_fit = fit_model(
        simulator, sim_data, fixed_param=True, iter_warmup=0,
        adapt_engaged=False, iter_sampling=1, chains=1,
        output_dir=tmp_path / "sim", seed=51,
    )
    y_synth = sim_fit.stan_variable("y_rep")
    cleanup_csv_files(sim_fit)
    assert y_synth.shape == (1, N_OBS)

    result = fit_and_summarize(
        compiled("normal"), {"N": N_OBS, "y": y_synth[0]}, model_name="recovery",
        chains=4, iter_warmup=500, iter_sampling=500, n_thinned_draws=0,
        output_dir=tmp_path / "rec", seed=52,
    )
    s = result.param_summary
    for name, truth in (("mu", TRUE_MU), ("sigma", TRUE_SIGMA)):
        lo, hi = s.loc[name, "hdi_3%"], s.loc[name, "hdi_97%"]
        assert lo < truth < hi, f"{name}: 94% HDI [{lo:.3f}, {hi:.3f}] misses {truth}"
    assert result.convergence.converged is True
    assert np.isfinite(s["mean"]).all()
