"""Pure tests of the reference scripts: no CmdStan, synthetic InferenceData.

These pin the artifact contract (file set, JSON layouts) and the decision
logic (thresholds, Pareto-k buckets, coverage/bias) independently of sampling.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from conftest import N_SCHOOLS

EXPECTED_FILES = {"summary.json", "diagnostics.json", "loo.json", "thinned_draws.npz", "posterior.nc"}
LOO_KEYS = {"elpd_loo", "se", "p_loo", "k_good", "k_ok", "k_bad", "k_very_bad"}
CONVERGENCE_KEYS = {"max_rhat", "min_ess_bulk", "min_ess_tail", "n_divergent", "converged"}
DIAGNOSTICS_KEYS = {"num_divergences", "max_treedepth_exceeded", "ebfmi_warnings"}
SUMMARY_COLUMNS = {"mean", "sd", "hdi_3%", "hdi_97%", "ess_bulk", "ess_tail", "r_hat"}


class TestJson:
    def test_numpy_encoder_round_trip(self, posterior_fit, tmp_path):
        payload = {
            "flag": np.bool_(True), "count": np.int64(3), "value": np.float32(1.5),
            "arr": np.arange(3), "nested": {"x": np.float64(2.0)},
        }
        posterior_fit.write_json(tmp_path / "a" / "b.json", payload)
        back = json.loads((tmp_path / "a" / "b.json").read_text())
        assert back == {"flag": True, "count": 3, "value": 1.5, "arr": [0, 1, 2], "nested": {"x": 2.0}}


class TestDecisions:
    def test_converged_on_well_behaved(self, posterior_fit, well_behaved_idata):
        summary, conv = posterior_fit.summarize(well_behaved_idata)
        assert set(conv) == CONVERGENCE_KEYS
        assert conv["converged"] is True and conv["n_divergent"] == 0
        assert conv["max_rhat"] < 1.01
        assert set(summary.columns) == SUMMARY_COLUMNS
        assert {"mu", "tau", "theta[0]"} <= set(summary.index)

    def test_flags_divergent_and_offset_chains(self, posterior_fit, divergent_idata):
        _, conv = posterior_fit.summarize(divergent_idata)
        assert conv["converged"] is False
        assert conv["n_divergent"] == 60  # 15 per chain × 4
        assert conv["max_rhat"] > 1.01

    def test_ess_threshold_alone_fails(self, posterior_fit, well_behaved_idata):
        """Too few draws → ESS below 400 → not converged, even with r_hat ~ 1."""
        small = well_behaved_idata.isel(draw=slice(0, 40))
        _, conv = posterior_fit.summarize(small)
        assert conv["max_rhat"] < 1.05 and conv["converged"] is False

    def test_loo_buckets(self, posterior_fit, well_behaved_idata):
        result = posterior_fit.loo(well_behaved_idata)
        assert result is not None and set(result) == LOO_KEYS
        assert result["k_good"] + result["k_ok"] + result["k_bad"] + result["k_very_bad"] == N_SCHOOLS
        assert result["elpd_loo"] < 0 and result["se"] > 0

    def test_loo_is_none_without_log_lik(self, posterior_fit, prior_idata):
        assert posterior_fit.loo(prior_idata) is None

    def test_thin_is_parameter_only_with_sample_axis_first(self, posterior_fit, well_behaved_idata):
        thinned = posterior_fit.thin(well_behaved_idata, 200)
        assert set(thinned) == {"mu", "tau", "theta"}
        assert thinned["mu"].shape == (200,) and thinned["theta"].shape == (200, N_SCHOOLS)
        assert np.array_equal(thinned["mu"], posterior_fit.thin(well_behaved_idata, 200)["mu"])

    def test_extreme_draw_pct(self, prior_predictive, prior_idata):
        pct = prior_predictive.extreme_draw_pct(prior_idata, -1e9, 1e9)
        assert pct == 0.0
        pct = prior_predictive.extreme_draw_pct(prior_idata, -20.0, 20.0)
        assert 20.0 < pct < 60.0  # mu ~ N(0, 20) plus noise sd 10: a fair share is outside ±20


class TestArtifactContract:
    @pytest.fixture
    def written(self, posterior_fit, well_behaved_idata, tmp_path):
        summary, conv = posterior_fit.summarize(well_behaved_idata)
        loo = posterior_fit.loo(well_behaved_idata)
        thinned = posterior_fit.thin(well_behaved_idata, 200)
        diagnostics = {"num_divergences": 0, "max_treedepth_exceeded": 0, "ebfmi_warnings": 0}
        artifacts = posterior_fit.write_artifacts(
            tmp_path, model_name="synthetic", idata=well_behaved_idata, param_summary=summary,
            convergence=conv, diagnostics=diagnostics, loo_result=loo, thinned=thinned,
            warnings=["note"],
        )
        return artifacts, tmp_path

    def test_exact_file_set_and_manifest(self, written):
        artifacts, out = written
        assert {p.name for p in out.iterdir()} == EXPECTED_FILES
        assert {Path(p).name for p in artifacts} == EXPECTED_FILES
        assert all(Path(p).is_absolute() and Path(p).exists() for p in artifacts)

    def test_json_layouts(self, written):
        _, out = written
        summary = json.loads((out / "summary.json").read_text())
        assert set(summary) == {"model_name", "param_summary", "convergence", "diagnostics", "artifacts", "warnings", "loo"}
        assert set(summary["param_summary"]) == SUMMARY_COLUMNS
        assert set(summary["convergence"]) == CONVERGENCE_KEYS
        assert set(summary["loo"]) == LOO_KEYS
        assert {Path(p).name for p in summary["artifacts"]} == EXPECTED_FILES
        assert summary["warnings"] == ["note"]
        assert set(json.loads((out / "diagnostics.json").read_text())) == DIAGNOSTICS_KEYS
        assert json.loads((out / "loo.json").read_text()) == summary["loo"]

    def test_optional_files_are_omitted(self, posterior_fit, prior_idata, well_behaved_idata, tmp_path):
        summary, conv = posterior_fit.summarize(well_behaved_idata)
        artifacts = posterior_fit.write_artifacts(
            tmp_path, model_name="m", idata=well_behaved_idata, param_summary=summary,
            convergence=conv, diagnostics={}, loo_result=None, thinned=None, save_netcdf=False,
        )
        assert {Path(p).name for p in artifacts} == {"summary.json", "diagnostics.json"}
        assert "loo" not in json.loads((tmp_path / "summary.json").read_text())


class TestRecovery:
    def test_coverage_and_bias_from_netcdf(self, fake_data, well_behaved_idata, tmp_path):
        well_behaved_idata.to_netcdf(str(tmp_path / "posterior.nc"))
        post = well_behaved_idata["posterior"]
        truth_at_means = {"mu": float(post["mu"].mean()), "theta": post["theta"].mean(("chain", "draw")).values, "N": 8}
        result = fake_data.recovery(tmp_path, truth_at_means)
        assert result["n_parameters"] == 1 + N_SCHOOLS  # N is data, not a parameter
        assert result["coverage_90"] == 1.0 and result["max_bias_z"] < 0.05
        far = {"mu": float(post["mu"].mean() + 10 * post["mu"].std())}
        result = fake_data.recovery(tmp_path, far)
        assert result["coverage_90"] == 0.0 and result["max_bias_z"] > 9

    def test_falls_back_to_thinned_draws(self, fake_data, posterior_fit, well_behaved_idata, tmp_path):
        np.savez_compressed(str(tmp_path / "thinned_draws.npz"), **posterior_fit.thin(well_behaved_idata, 200))
        result = fake_data.recovery(tmp_path, {"tau": 5.0})
        assert result["n_parameters"] == 1 and 0.0 <= result["coverage_90"] <= 1.0

    def test_rejects_unmatched_truth(self, fake_data, well_behaved_idata, tmp_path):
        well_behaved_idata.to_netcdf(str(tmp_path / "posterior.nc"))
        with pytest.raises(ValueError, match="no true_params entry"):
            fake_data.recovery(tmp_path, {"not_a_param": 1.0})

    def test_true_literal_or_path(self, fake_data, tmp_path):
        assert fake_data.load_json_or_literal('{"mu": 1}') == {"mu": 1}
        p = tmp_path / "t.json"
        p.write_text('{"sigma": 2}')
        assert fake_data.load_json_or_literal(str(p)) == {"sigma": 2}
