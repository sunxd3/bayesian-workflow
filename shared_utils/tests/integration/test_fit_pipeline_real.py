"""fit_and_summarize against real CmdStan: the artifact contract and the numbers.

The file set, JSON layouts, and InferenceData groups asserted here are what
`agents/model-fitter.md`, the `validation-protocol` audited fields, and the
posterior-predictive / critic / report stages read. Change them deliberately.
"""

from __future__ import annotations

import json
from pathlib import Path

import arviz as az
import numpy as np
import pytest

from .conftest import N_OBS, TRUE_MU, TRUE_SIGMA

pytestmark = pytest.mark.integration

EXPECTED_FILES = {
    "summary.json",
    "diagnostics.json",
    "loo.json",
    "thinned_draws.npz",
    "posterior.nc",
}
LOO_KEYS = {"elpd_loo", "se", "p_loo", "k_good", "k_ok", "k_bad", "k_very_bad"}
CONVERGENCE_KEYS = {"max_rhat", "min_ess_bulk", "min_ess_tail", "n_divergent", "converged"}
DIAGNOSTICS_KEYS = {"num_divergences", "max_treedepth_exceeded", "ebfmi_warnings"}
SUMMARY_COLUMNS = {"mean", "sd", "hdi_3%", "hdi_97%", "ess_bulk", "ess_tail", "r_hat"}


def _load(save_dir: Path, name: str) -> dict:
    return json.loads((save_dir / name).read_text())


# ---------------------------------------------------------------------------
# Artifact contract
# ---------------------------------------------------------------------------


class TestArtifactContract:
    def test_exact_file_set(self, normal_fit):
        _, save_dir, _ = normal_fit
        assert {p.name for p in save_dir.iterdir()} == EXPECTED_FILES

    def test_cmdstan_csvs_are_deleted(self, normal_fit):
        result, _, stan_out = normal_fit
        assert list(stan_out.glob("*.csv")) == []
        assert any("CSV files deleted" in w for w in result.warnings)

    def test_summary_json_layout(self, normal_fit):
        _, save_dir, _ = normal_fit
        summary = _load(save_dir, "summary.json")
        assert set(summary) == {
            "model_name", "param_summary", "convergence", "diagnostics",
            "artifacts", "warnings", "loo",
        }
        assert summary["model_name"] == "normal"
        assert set(summary["convergence"]) == CONVERGENCE_KEYS
        assert set(summary["loo"]) == LOO_KEYS
        assert set(summary["param_summary"]) == SUMMARY_COLUMNS
        assert set(summary["param_summary"]["mean"]) == {"mu", "sigma"}

    def test_loo_json_layout(self, normal_fit):
        _, save_dir, _ = normal_fit
        loo = _load(save_dir, "loo.json")
        assert set(loo) == LOO_KEYS
        assert all(isinstance(loo[k], int) for k in ("k_good", "k_ok", "k_bad", "k_very_bad"))
        assert loo["k_good"] + loo["k_ok"] + loo["k_bad"] + loo["k_very_bad"] == N_OBS

    def test_diagnostics_json_layout(self, normal_fit):
        _, save_dir, _ = normal_fit
        assert set(_load(save_dir, "diagnostics.json")) == DIAGNOSTICS_KEYS

    def test_files_agree_with_each_other(self, normal_fit):
        """Divergences come from two independent sources (ArviZ sample_stats vs
        CmdStan method variables) and LOO is written twice — they must match."""
        result, save_dir, _ = normal_fit
        summary = _load(save_dir, "summary.json")
        diagnostics = _load(save_dir, "diagnostics.json")
        loo = _load(save_dir, "loo.json")
        assert diagnostics["num_divergences"] == summary["convergence"]["n_divergent"]
        assert summary["loo"] == loo
        assert summary["convergence"]["max_rhat"] == result.convergence.max_rhat

    def test_summary_manifest_lists_every_artifact(self, normal_fit):
        result, save_dir, _ = normal_fit
        summary = _load(save_dir, "summary.json")
        listed = {Path(p).name for p in summary["artifacts"]}
        assert listed == EXPECTED_FILES
        assert {Path(p).name for p in result.artifacts} == EXPECTED_FILES

    def test_netcdf_groups_and_shapes(self, normal_fit, normal_data):
        _, save_dir, _ = normal_fit
        idata = az.from_netcdf(save_dir / "posterior.nc")
        assert {
            "posterior", "posterior_predictive", "log_likelihood",
            "sample_stats", "observed_data",
        } <= set(idata.groups())
        assert set(idata["posterior"].data_vars) == {"mu", "sigma"}
        assert idata["posterior"]["mu"].shape == (4, 500)
        assert idata["posterior_predictive"]["y_rep"].shape == (4, 500, N_OBS)
        assert idata["log_likelihood"]["log_lik"].shape == (4, 500, N_OBS)
        np.testing.assert_array_equal(idata["observed_data"]["y"].values, normal_data["y"])

    def test_thinned_draws(self, normal_fit):
        result, save_dir, _ = normal_fit
        on_disk = np.load(save_dir / "thinned_draws.npz")
        assert set(on_disk.files) == {"mu", "sigma"}
        assert on_disk["mu"].shape == (200,)
        assert result.thinned_draws is not None
        np.testing.assert_array_equal(on_disk["sigma"], result.thinned_draws["sigma"])
        # Parameter-only: no generated quantities leak into the thinned set.
        assert "y_rep" not in on_disk.files and "log_lik" not in on_disk.files


# ---------------------------------------------------------------------------
# Statistical correctness
# ---------------------------------------------------------------------------


class TestStatisticalCorrectness:
    def test_recovers_known_parameters(self, normal_fit):
        result, _, _ = normal_fit
        s = result.param_summary
        for name, truth in (("mu", TRUE_MU), ("sigma", TRUE_SIGMA)):
            z = abs(s.loc[name, "mean"] - truth) / s.loc[name, "sd"]
            assert z < 3, f"{name}: posterior mean {s.loc[name, 'mean']:.3f} is {z:.1f} sd from {truth}"

    def test_converges_on_well_behaved_model(self, normal_fit):
        result, _, _ = normal_fit
        c = result.convergence
        assert c.converged is True
        assert c.max_rhat < 1.01
        assert c.min_ess_bulk > 400 and c.min_ess_tail > 400
        assert c.n_divergent == 0
        assert result.diagnostics["max_treedepth_exceeded"] == 0

    def test_posterior_predictive_covers_observations(self, normal_fit, normal_data):
        """The y_rep in posterior.nc is a real predictive distribution: its
        central 90% band should cover roughly 90% of the observed points."""
        _, save_dir, _ = normal_fit
        idata = az.from_netcdf(save_dir / "posterior.nc")
        y_rep = idata["posterior_predictive"]["y_rep"].values.reshape(-1, N_OBS)
        lo, hi = np.quantile(y_rep, [0.05, 0.95], axis=0)
        coverage = np.mean((normal_data["y"] >= lo) & (normal_data["y"] <= hi))
        assert 0.82 <= coverage <= 0.97, coverage

    def test_loo_is_a_real_elpd(self, normal_fit, normal_data):
        """elpd_loo must sit just below the in-sample log score at the MLE:
        never above it, and not more than a few p_loo below it."""
        result, _, _ = normal_fit
        assert result.loo is not None
        y = normal_data["y"]
        mle_sigma = y.std()
        lppd_mle = float(np.sum(-0.5 * np.log(2 * np.pi * mle_sigma**2)
                                - 0.5 * ((y - y.mean()) / mle_sigma) ** 2))
        assert lppd_mle - 10 < result.loo.elpd_loo < lppd_mle + 1
        assert 1.0 < result.loo.p_loo < 4.0  # two parameters
        assert result.loo.se > 0
        assert result.loo.k_bad == 0 and result.loo.k_very_bad == 0


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------


class TestOptions:
    def test_cleanup_false_keeps_csvs_and_thinning_can_be_disabled(
        self, compiled, normal_data, tmp_path
    ):
        from shared_utils import fit_and_summarize

        result = fit_and_summarize(
            compiled("normal"), normal_data, chains=2, iter_warmup=200,
            iter_sampling=200, n_thinned_draws=0, cleanup_csvs=False,
            output_dir=tmp_path, seed=11,
        )
        assert len(list(tmp_path.glob("*.csv"))) == 2
        assert result.thinned_draws is None
        assert result.artifacts == []
        assert not any("CSV files deleted" in w for w in result.warnings)

    def test_explicit_observed_data_coords_and_dims(self, compiled, normal_data, tmp_path):
        from shared_utils import fit_and_summarize

        obs = np.arange(N_OBS)
        fit_and_summarize(
            compiled("normal"), normal_data, chains=2, iter_warmup=200,
            iter_sampling=200, save_dir=tmp_path, save_netcdf=True,
            observed_data={"y_obs": normal_data["y"]},
            coords={"obs": obs},
            dims={"y_rep": ["obs"], "log_lik": ["obs"], "y_obs": ["obs"]},
            output_dir=tmp_path / "csv", seed=12,
        )
        idata = az.from_netcdf(tmp_path / "posterior.nc")
        assert set(idata["observed_data"].data_vars) == {"y_obs"}
        assert idata["posterior_predictive"]["y_rep"].dims == ("chain", "draw", "obs")
        assert idata["log_likelihood"]["log_lik"].dims == ("chain", "draw", "obs")

    def test_empty_observed_data_attaches_nothing(self, compiled, normal_data, tmp_path):
        from shared_utils import fit_and_summarize

        fit_and_summarize(
            compiled("normal"), normal_data, chains=2, iter_warmup=200,
            iter_sampling=200, save_dir=tmp_path, save_netcdf=True,
            observed_data={}, output_dir=tmp_path / "csv", seed=13,
        )
        idata = az.from_netcdf(tmp_path / "posterior.nc")
        assert "observed_data" not in idata.groups()
