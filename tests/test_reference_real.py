"""The reference scripts against real CmdStan: contract, numbers, and CLIs.

The file set, JSON layouts, and InferenceData groups asserted here are what
`agents/model-fitter.md`, the `validation-protocol` audited fields, and the
posterior-predictive / critic / report stages read. Change them deliberately.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import arviz as az
import numpy as np
import pytest

from conftest import N_OBS, REFERENCES_DIR, STAN_DIR, TRUE_MU, TRUE_SIGMA

pytestmark = pytest.mark.integration

EXPECTED_FILES = {"summary.json", "diagnostics.json", "loo.json", "thinned_draws.npz", "posterior.nc"}


def _load(save_dir: Path, name: str) -> dict:
    return json.loads((save_dir / name).read_text())


def _write_stan_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps({k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in data.items()}))
    return path


def _cli(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REFERENCES_DIR / script), *args],
        check=True, capture_output=True, text=True,
    )


# ---------------------------------------------------------------------------
# posterior_fit: artifact contract
# ---------------------------------------------------------------------------


class TestArtifactContract:
    def test_exact_file_set(self, normal_fit):
        _, save_dir, _ = normal_fit
        assert {p.name for p in save_dir.iterdir()} == EXPECTED_FILES

    def test_cmdstan_csvs_are_deleted(self, normal_fit):
        result, _, stan_out = normal_fit
        assert list(stan_out.glob("*.csv")) == []
        assert any("CSV files deleted" in w for w in result["warnings"])

    def test_files_agree_with_each_other(self, normal_fit):
        """Divergences come from two independent sources (ArviZ sample_stats vs
        CmdStanPy counters) and LOO is written twice — they must match."""
        result, save_dir, _ = normal_fit
        summary = _load(save_dir, "summary.json")
        assert _load(save_dir, "diagnostics.json")["num_divergences"] == summary["convergence"]["n_divergent"]
        assert _load(save_dir, "loo.json") == summary["loo"]
        assert summary["convergence"] == result["convergence"]
        assert {Path(p).name for p in summary["artifacts"]} == EXPECTED_FILES
        assert summary["model_name"] == "normal"
        assert set(summary["param_summary"]["mean"]) == {"mu", "sigma"}

    def test_netcdf_groups_and_shapes(self, normal_fit, normal_data):
        _, save_dir, _ = normal_fit
        idata = az.from_netcdf(save_dir / "posterior.nc")
        assert {"posterior", "posterior_predictive", "log_likelihood", "sample_stats", "observed_data"} <= set(idata.groups())
        assert set(idata["posterior"].data_vars) == {"mu", "sigma"}
        assert idata["posterior"]["mu"].shape == (4, 500)
        assert idata["posterior_predictive"]["y_rep"].shape == (4, 500, N_OBS)
        assert idata["log_likelihood"]["log_lik"].shape == (4, 500, N_OBS)
        np.testing.assert_array_equal(idata["observed_data"]["y"].values, normal_data["y"])

    def test_thinned_draws(self, normal_fit):
        _, save_dir, _ = normal_fit
        on_disk = np.load(save_dir / "thinned_draws.npz")
        assert set(on_disk.files) == {"mu", "sigma"}
        assert on_disk["mu"].shape == (200,)
        assert on_disk["mu"].std() > 0


# ---------------------------------------------------------------------------
# posterior_fit: statistical correctness
# ---------------------------------------------------------------------------


class TestStatisticalCorrectness:
    def test_recovers_known_parameters(self, normal_fit):
        result, _, _ = normal_fit
        s = result["param_summary"]
        for name, truth in (("mu", TRUE_MU), ("sigma", TRUE_SIGMA)):
            z = abs(s.loc[name, "mean"] - truth) / s.loc[name, "sd"]
            assert z < 3, f"{name}: posterior mean {s.loc[name, 'mean']:.3f} is {z:.1f} sd from {truth}"

    def test_converges_on_well_behaved_model(self, normal_fit):
        result, _, _ = normal_fit
        c = result["convergence"]
        assert c["converged"] is True and c["max_rhat"] < 1.01 and c["n_divergent"] == 0
        assert c["min_ess_bulk"] >= 400 and c["min_ess_tail"] >= 400
        assert result["diagnostics"]["max_treedepth_exceeded"] == 0
        assert result["diagnostics"]["ebfmi_warnings"] == 0

    def test_posterior_predictive_covers_observations(self, normal_fit, normal_data):
        _, save_dir, _ = normal_fit
        idata = az.from_netcdf(save_dir / "posterior.nc")
        y_rep = idata["posterior_predictive"]["y_rep"].values.reshape(-1, N_OBS)
        lo, hi = np.quantile(y_rep, [0.05, 0.95], axis=0)
        coverage = np.mean((normal_data["y"] >= lo) & (normal_data["y"] <= hi))
        assert 0.82 <= coverage <= 0.97, coverage

    def test_loo_is_a_real_elpd(self, normal_fit, normal_data):
        """elpd_loo sits just below the in-sample log score at the MLE."""
        result, _, _ = normal_fit
        loo = result["loo"]
        y = normal_data["y"]
        sd = y.std()
        lppd_mle = float(np.sum(-0.5 * np.log(2 * np.pi * sd**2) - 0.5 * ((y - y.mean()) / sd) ** 2))
        assert lppd_mle - 10 < loo["elpd_loo"] < lppd_mle + 1
        assert 1.0 < loo["p_loo"] < 4.0 and loo["se"] > 0
        assert loo["k_bad"] == 0 and loo["k_very_bad"] == 0


class TestRealPathology:
    def test_funnel_is_flagged(self, funnel_fit):
        result, _ = funnel_fit
        c = result["convergence"]
        assert c["n_divergent"] > 0, "Neal's funnel at adapt_delta=0.8 should diverge"
        assert c["converged"] is False
        assert result["diagnostics"]["num_divergences"] == c["n_divergent"]
        assert any("divergent transitions" in w for w in result["warnings"])

    def test_model_without_log_lik_or_y_rep(self, funnel_fit):
        result, save_dir = funnel_fit
        assert result["loo"] is None
        assert {p.name for p in save_dir.iterdir()} == {"summary.json", "diagnostics.json"}


class TestHierarchical:
    def test_noncentered_eight_schools_converges(self, eight_schools_fit):
        result, _ = eight_schools_fit
        assert result["convergence"]["converged"] is True, result["convergence"]

    def test_vector_parameters_flow_through(self, eight_schools_fit, eight_schools_data):
        result, save_dir = eight_schools_fit
        j = eight_schools_data["J"]
        assert {"mu", "tau", "theta[0]", f"theta[{j - 1}]"} <= set(result["param_summary"].index)
        draws = np.load(save_dir / "thinned_draws.npz")
        assert draws["theta"].shape == (200, j) and draws["theta_tilde"].shape == (200, j)
        loo = result["loo"]
        assert loo["k_good"] + loo["k_ok"] + loo["k_bad"] + loo["k_very_bad"] == j


class TestLooRanking:
    def test_loo_prefers_the_correct_likelihood(self, require_cmdstan, posterior_fit, heavy_tailed_data, tmp_path):
        """On Student-t(3) data the t model must beat the normal model by more
        than 2 SE of the paired difference — the selector's decision rule."""
        kw = dict(iter_warmup=500, iter_sampling=500, n_thinned=0)
        normal = posterior_fit.run(STAN_DIR / "normal.stan", heavy_tailed_data, tmp_path / "n", model_name="normal", seed=21, **kw)
        student = posterior_fit.run(STAN_DIR / "student_t.stan", heavy_tailed_data, tmp_path / "t", model_name="student_t", seed=22, **kw)
        assert student["loo"]["elpd_loo"] > normal["loo"]["elpd_loo"]
        cmp = az.compare({
            "normal": az.from_netcdf(tmp_path / "n" / "posterior.nc"),
            "student_t": az.from_netcdf(tmp_path / "t" / "posterior.nc"),
        })
        assert cmp.index[0] == "student_t"
        elpd_diff, dse = cmp.loc["normal", "elpd_diff"], cmp.loc["normal", "dse"]
        assert elpd_diff > 2 * dse, f"elpd diff {elpd_diff:.1f} vs dse {dse:.1f}"
        assert abs(cmp.loc["student_t", "elpd_loo"] - student["loo"]["elpd_loo"]) < 1e-6
        n = heavy_tailed_data["N"]
        assert student["loo"]["k_good"] + student["loo"]["k_ok"] >= 0.95 * n
        nu = student["param_summary"].loc["nu"]
        assert nu["hdi_3%"] < 3.0 < nu["hdi_97%"]
        assert student["convergence"]["converged"] is True


# ---------------------------------------------------------------------------
# prior_predictive and fake_data
# ---------------------------------------------------------------------------


class TestPriorPredictive:
    def test_run_with_bounds(self, require_cmdstan, prior_predictive, normal_data, tmp_path):
        result = prior_predictive.run(
            STAN_DIR / "normal_prior.stan", normal_data, tmp_path, draws=500, seed=41, bounds=(-20.0, 20.0),
        )
        assert {Path(p).name for p in result["artifacts"]} == {"prior_predictive.nc", "prior_check.json"}
        assert list(tmp_path.glob("*.csv")) == []
        idata = az.from_netcdf(tmp_path / "prior_predictive.nc")
        assert {"prior", "prior_predictive", "observed_data"} <= set(idata.groups())
        assert idata["prior_predictive"]["y_rep"].shape == (1, 500, N_OBS)
        # The GQ program really samples the declared priors: mu ~ normal(0, 10).
        mu = idata["prior"]["mu"].values.ravel()
        assert abs(mu.mean()) < 2.0 and 8.0 < mu.std() < 12.0
        check = json.loads((tmp_path / "prior_check.json").read_text())
        assert check["bounds"] == [-20.0, 20.0] and check["extreme_draw_pct"] == result["extreme_draw_pct"]
        assert 1.0 < check["extreme_draw_pct"] < 12.0  # P(|mu| > 20) ≈ 4.6%


class TestFakeData:
    def test_simulate_fit_check(self, require_cmdstan, fake_data, posterior_fit, tmp_path):
        """The fake-data-checker's single-draw recovery, end to end."""
        stan_data = {"N": N_OBS, "y": np.zeros(N_OBS)}
        truth = {"mu": TRUE_MU, "sigma": TRUE_SIGMA}
        y = fake_data.simulate(STAN_DIR / "normal_simulator.stan", stan_data, truth, seed=51)
        assert y.shape == (N_OBS,) and abs(y.mean() - TRUE_MU) < 0.5
        data_path, true_path = fake_data.write_fake_dataset(stan_data, y, truth, tmp_path)
        fake = json.loads(data_path.read_text())
        assert fake["N"] == N_OBS and np.allclose(fake["y"], y)

        fit = posterior_fit.run(
            STAN_DIR / "normal.stan", fake, tmp_path / "fit", model_name="recovery",
            iter_warmup=500, iter_sampling=500, save_netcdf=False, seed=52,
        )
        assert fit["convergence"]["converged"] is True
        result = fake_data.recovery(tmp_path / "fit", json.loads(true_path.read_text()))
        assert result["n_parameters"] == 2
        assert result["max_bias_z"] < 3.0
        assert result["coverage_90"] >= 0.5


# ---------------------------------------------------------------------------
# CLIs, as an agent would invoke them
# ---------------------------------------------------------------------------


class TestCli:
    def test_posterior_fit_cli(self, require_cmdstan, normal_data, tmp_path):
        data = _write_stan_json(tmp_path / "data.json", normal_data)
        proc = _cli(
            "posterior_fit.py", "--model", str(STAN_DIR / "normal.stan"), "--data", str(data),
            "--out", str(tmp_path / "fit"), "--name", "cli", "--chains", "4",
            "--warmup", "500", "--samples", "500", "--seed", "5",
        )
        first, *rest = proc.stdout.splitlines()
        assert first.startswith("cli: ") and "rhat_max=" in first and "elpd_loo=" in first
        assert rest[-1].startswith("artifacts: ")
        assert {p.name for p in (tmp_path / "fit").iterdir()} == EXPECTED_FILES
        summary = json.loads((tmp_path / "fit" / "summary.json").read_text())
        assert summary["model_name"] == "cli" and summary["convergence"]["converged"] is True

    def test_probe_flags(self, require_cmdstan, normal_data, tmp_path):
        data = _write_stan_json(tmp_path / "data.json", normal_data)
        _cli(
            "posterior_fit.py", "--model", str(STAN_DIR / "normal.stan"), "--data", str(data),
            "--out", str(tmp_path / "probe"), "--warmup", "100", "--samples", "100",
            "--no-netcdf", "--thin", "0", "--seed", "6",
        )
        assert {p.name for p in (tmp_path / "probe").iterdir()} == {"summary.json", "diagnostics.json", "loo.json"}

    def test_prior_and_fake_data_clis(self, require_cmdstan, normal_data, tmp_path):
        data = _write_stan_json(tmp_path / "data.json", normal_data)
        proc = _cli(
            "prior_predictive.py", "--model", str(STAN_DIR / "normal_prior.stan"), "--data", str(data),
            "--out", str(tmp_path / "prior"), "--draws", "300", "--bounds", "-20", "20", "--seed", "7",
        )
        assert "extreme_draw_pct=" in proc.stdout
        assert (tmp_path / "prior" / "prior_check.json").exists()

        proc = _cli(
            "fake_data.py", "simulate", "--simulator", str(STAN_DIR / "normal_simulator.stan"),
            "--data", str(data), "--true", '{"mu": 2.0, "sigma": 1.5}', "--out", str(tmp_path / "sim"), "--seed", "8",
        )
        assert proc.stdout.startswith(f"simulated {N_OBS} observations")
        _cli(
            "posterior_fit.py", "--model", str(STAN_DIR / "normal.stan"),
            "--data", str(tmp_path / "sim" / "fake_data.json"), "--out", str(tmp_path / "sim" / "fit"),
            "--name", "recovery", "--no-netcdf", "--warmup", "300", "--samples", "300", "--seed", "9",
        )
        proc = _cli(
            "fake_data.py", "check", "--fit", str(tmp_path / "sim" / "fit"),
            "--true", str(tmp_path / "sim" / "true_params.json"), "--out", str(tmp_path / "sim"),
        )
        assert proc.stdout.startswith("recovery: coverage_90=")
        recovery = json.loads((tmp_path / "sim" / "recovery.json").read_text())
        assert set(recovery) == {"interval", "n_parameters", "coverage_90", "max_bias_z", "per_parameter"}
        assert set(recovery["per_parameter"]) == {"mu", "sigma"}
