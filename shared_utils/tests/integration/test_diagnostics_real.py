"""Diagnostics and LOO on real sampler output: pathology must be flagged,
clean hierarchical fits must pass, and LOO must rank the right likelihood."""

from __future__ import annotations

import json
from typing import Any

import arviz as az
import numpy as np
import pytest

pytestmark = pytest.mark.integration


class TestRealPathology:
    def test_funnel_is_flagged(self, funnel_fit):
        result, _ = funnel_fit
        c = result.convergence
        assert c.n_divergent > 0, "Neal's funnel at adapt_delta=0.8 should diverge"
        assert c.converged is False
        assert result.diagnostics["num_divergences"] == c.n_divergent
        assert any("divergent transitions" in w for w in result.warnings)

    def test_model_without_log_lik_has_no_loo(self, funnel_fit):
        result, save_dir = funnel_fit
        assert result.loo is None
        assert not (save_dir / "loo.json").exists()
        assert "loo" not in json.loads((save_dir / "summary.json").read_text())
        assert {p.name for p in save_dir.iterdir()} == {"summary.json", "diagnostics.json"}


class TestHierarchical:
    def test_noncentered_eight_schools_converges(self, eight_schools_fit):
        result, _ = eight_schools_fit
        assert result.convergence.converged is True, str(result.convergence)

    def test_vector_parameters_flow_through(self, eight_schools_fit, eight_schools_data):
        result, save_dir = eight_schools_fit
        j = eight_schools_data["J"]
        index = set(result.param_summary.index)
        assert {"mu", "tau", "theta[0]", f"theta[{j - 1}]"} <= index
        assert result.thinned_draws is not None
        assert result.thinned_draws["theta"].shape == (200, j)
        draws = np.load(save_dir / "thinned_draws.npz")
        assert draws["theta_tilde"].shape == (200, j)
        assert result.loo is not None
        assert result.loo.k_good + result.loo.k_ok + result.loo.k_bad + result.loo.k_very_bad == j


class TestLooRanking:
    def test_loo_prefers_the_correct_likelihood(self, compiled, heavy_tailed_data, tmp_path):
        """On Student-t(3) data the t model must beat the normal model by more
        than 2 SE — the decision rule the workflow's plateau guard and selector
        apply — and its Pareto-k diagnostics must be healthy."""
        from shared_utils import fit_and_summarize

        kwargs: dict[str, Any] = dict(
            chains=4, iter_warmup=500, iter_sampling=500, n_thinned_draws=0,
            save_netcdf=True,
        )
        normal = fit_and_summarize(
            compiled("normal"), heavy_tailed_data, model_name="normal",
            save_dir=tmp_path / "n", output_dir=tmp_path / "n" / "csv", seed=21, **kwargs,
        )
        student = fit_and_summarize(
            compiled("student_t"), heavy_tailed_data, model_name="student_t",
            save_dir=tmp_path / "t", output_dir=tmp_path / "t" / "csv", seed=22, **kwargs,
        )
        assert normal.loo is not None and student.loo is not None
        assert student.loo.elpd_loo > normal.loo.elpd_loo

        # The selector's decision rule is the paired difference against its own
        # SE (az.compare's elpd_diff / dse), not the marginal SEs — heavy tails
        # inflate the normal model's marginal SE far beyond the paired one.
        cmp = az.compare({
            "normal": az.from_netcdf(tmp_path / "n" / "posterior.nc"),
            "student_t": az.from_netcdf(tmp_path / "t" / "posterior.nc"),
        })
        assert cmp.index[0] == "student_t"
        elpd_diff, dse = cmp.loc["normal", "elpd_diff"], cmp.loc["normal", "dse"]
        assert elpd_diff > 2 * dse, f"elpd diff {elpd_diff:.1f} vs dse {dse:.1f}"
        # compute_loo and az.compare must agree on the numbers they share.
        assert abs(cmp.loc["student_t", "elpd_loo"] - student.loo.elpd_loo) < 1e-6
        assert abs(cmp.loc["normal", "elpd_loo"] - normal.loo.elpd_loo) < 1e-6

        n = heavy_tailed_data["N"]
        assert student.loo.k_good + student.loo.k_ok >= 0.95 * n
        nu = student.param_summary.loc["nu"]
        assert nu["hdi_3%"] < 3.0 < nu["hdi_97%"], f"nu HDI {nu['hdi_3%']:.2f}-{nu['hdi_97%']:.2f} misses 3"
        assert student.convergence.converged is True, str(student.convergence)
