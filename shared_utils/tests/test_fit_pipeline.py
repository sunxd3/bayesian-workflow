"""Tests for shared_utils.fit_pipeline module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from shared_utils.diagnostics import ConvergenceResult, LOOResult
from shared_utils.fit_pipeline import (
    FitResult,
    _thin_draws,
    cleanup_csv_files,
    fit_and_summarize,
)

# ---------------------------------------------------------------------------
# cleanup_csv_files
# ---------------------------------------------------------------------------

class TestCleanupCsvFiles:
    """Tests for cleanup_csv_files()."""

    def test_deletes_csv_files(self, fake_cmdstan_fit, csv_files):
        """cleanup_csv_files() deletes temp CSV files and returns count."""
        # Verify files exist first
        for p in csv_files:
            assert Path(p).exists()

        n = cleanup_csv_files(fake_cmdstan_fit)
        assert n == 4

        # Verify files are gone
        for p in csv_files:
            assert not Path(p).exists()

    def test_handles_missing_runset(self):
        """cleanup_csv_files() handles missing runset gracefully."""
        fit = MagicMock(spec=[])  # no runset attribute
        fit.runset = None
        # Need to actually set it up properly
        obj = type("Fit", (), {"runset": None})()
        n = cleanup_csv_files(obj)
        assert n == 0

    def test_handles_no_runset_attr(self):
        """cleanup_csv_files() returns 0 when object has no runset."""
        obj = object()
        n = cleanup_csv_files(obj)
        assert n == 0

    def test_csv_files_fallback(self, tmp_path: Path):
        """cleanup_csv_files() tries csv_files attr then _csv_files fallback."""
        csv_path = tmp_path / "chain_0.csv"
        csv_path.write_text("lp__\n-5.0\n")

        runset = MagicMock(spec=[])
        runset.csv_files = None
        runset._csv_files = [str(csv_path)]
        fit = MagicMock()
        fit.runset = runset

        n = cleanup_csv_files(fit)
        assert n == 1
        assert not csv_path.exists()

    def test_empty_csv_files_does_not_fallback(self, tmp_path: Path):
        """cleanup_csv_files() with csv_files=[] does NOT fall through to _csv_files."""
        secret_path = tmp_path / "stale.csv"
        secret_path.write_text("lp__\n-1.0\n")

        runset = MagicMock(spec=[])
        runset.csv_files = []  # empty list, not None
        runset._csv_files = [str(secret_path)]
        fit = MagicMock()
        fit.runset = runset

        n = cleanup_csv_files(fit)
        assert n == 0
        # _csv_files should NOT have been touched
        assert secret_path.exists()

    def test_handles_already_deleted_files(self, tmp_path: Path):
        """cleanup_csv_files() handles files that don't exist."""
        runset = MagicMock()
        runset.csv_files = [str(tmp_path / "nonexistent.csv")]
        fit = MagicMock()
        fit.runset = runset

        n = cleanup_csv_files(fit)
        assert n == 0


# ---------------------------------------------------------------------------
# _thin_draws
# ---------------------------------------------------------------------------

class TestThinDraws:
    """Tests for _thin_draws()."""

    def test_produces_correct_shape(self, eight_schools_posterior_idata):
        """_thin_draws() produces correct shape from real InferenceData."""
        thinned = _thin_draws(eight_schools_posterior_idata, n_thinned_draws=50)
        assert isinstance(thinned, dict)
        assert "mu" in thinned
        assert "tau" in thinned
        assert "theta" in thinned
        # mu is scalar per draw
        assert thinned["mu"].shape == (50,)
        # theta has 8 schools
        assert thinned["theta"].shape == (50, 8)

    def test_n_thinned_draws_larger_than_total(self, eight_schools_posterior_idata):
        """_thin_draws() handles n_thinned_draws larger than total draws."""
        posterior = eight_schools_posterior_idata.posterior
        total = posterior.sizes["chain"] * posterior.sizes["draw"]
        thinned = _thin_draws(eight_schools_posterior_idata, n_thinned_draws=total + 500)
        # Should get at most total draws
        assert thinned["mu"].shape[0] <= total


# ---------------------------------------------------------------------------
# FitResult
# ---------------------------------------------------------------------------

class TestFitResult:
    """Tests for FitResult."""

    @pytest.fixture
    def fit_result(self) -> FitResult:
        """Create a FitResult with realistic data."""
        import pandas as pd

        param_summary = pd.DataFrame(
            {
                "mean": {"mu": 7.5, "tau": 5.0},
                "sd": {"mu": 4.5, "tau": 3.5},
                "r_hat": {"mu": 1.0, "tau": 1.0},
            }
        )
        convergence = ConvergenceResult(
            max_rhat=1.0,
            min_ess_bulk=5000.0,
            min_ess_tail=4000.0,
            n_divergent=0,
            converged=True,
        )
        loo = LOOResult(
            elpd_loo=-30.8,
            se=1.0,
            p_loo=1.2,
            k_good=5,
            k_ok=3,
            k_bad=0,
            k_very_bad=0,
        )
        thinned = {
            "mu": np.random.randn(200),
            "tau": np.abs(np.random.randn(200)),
        }
        return FitResult(
            param_summary=param_summary,
            convergence=convergence,
            loo=loo,
            diagnostics={"num_divergences": 0, "max_treedepth_exceeded": 0, "ebfmi_warnings": 0},
            thinned_draws=thinned,
            model_name="test_model",
        )

    def test_save_writes_expected_files(self, fit_result, tmp_path: Path):
        """FitResult.save() writes summary.json, diagnostics.json, loo.json, thinned_draws.npz."""
        saved = fit_result.save(tmp_path)

        assert len(saved) == 4
        assert (tmp_path / "summary.json").exists()
        assert (tmp_path / "diagnostics.json").exists()
        assert (tmp_path / "loo.json").exists()
        assert (tmp_path / "thinned_draws.npz").exists()

    def test_save_without_loo(self, fit_result, tmp_path: Path):
        """FitResult.save() skips loo.json when loo is None."""
        fit_result.loo = None
        saved = fit_result.save(tmp_path)

        assert (tmp_path / "loo.json").exists() is False
        assert len(saved) == 3

    def test_save_without_thinned_draws(self, fit_result, tmp_path: Path):
        """FitResult.save() skips thinned_draws.npz when draws are None."""
        fit_result.thinned_draws = None
        saved = fit_result.save(tmp_path)

        assert (tmp_path / "thinned_draws.npz").exists() is False
        assert len(saved) == 3

    def test_to_dict_serializes(self, fit_result):
        """FitResult.to_dict() serializes correctly."""
        d = fit_result.to_dict()

        assert d["model_name"] == "test_model"
        assert "param_summary" in d
        assert d["convergence"]["converged"] is True
        assert d["convergence"]["max_rhat"] == 1.0
        assert d["convergence"]["n_divergent"] == 0
        assert d["loo"]["elpd_loo"] == -30.8
        assert d["loo"]["k_good"] == 5
        assert d["diagnostics"]["num_divergences"] == 0

    def test_to_dict_without_loo(self, fit_result):
        """FitResult.to_dict() omits loo when None."""
        fit_result.loo = None
        d = fit_result.to_dict()
        assert "loo" not in d

    def test_save_updates_artifacts(self, fit_result, tmp_path: Path):
        """FitResult.save() updates the artifacts list."""
        assert len(fit_result.artifacts) == 0
        fit_result.save(tmp_path)
        assert len(fit_result.artifacts) == 4



# ---------------------------------------------------------------------------
# fit_and_summarize (orchestration, heavily mocked)
# ---------------------------------------------------------------------------

class TestFitAndSummarize:
    """Tests for fit_and_summarize()."""

    @patch("shared_utils.fit_pipeline.cleanup_csv_files")
    @patch("shared_utils.fit_pipeline.to_arviz")
    @patch("shared_utils.fit_pipeline.fit_model")
    def test_orchestration(
        self,
        mock_fit_model,
        mock_to_arviz,
        mock_cleanup,
        eight_schools_posterior_idata,
    ):
        """fit_and_summarize() orchestrates fit, convert, check, summarize."""
        # Setup mocks
        mock_fit = MagicMock()
        mock_fit.method_variables.return_value = {
            "divergent__": np.zeros(400),
            "treedepth__": np.full(400, 5),
            "energy__": np.random.randn(100, 4) + 100,
        }
        mock_fit.metadata.cmdstan_config = {"max_depth": 10}
        mock_fit_model.return_value = mock_fit
        mock_to_arviz.return_value = eight_schools_posterior_idata
        mock_cleanup.return_value = 4

        model = MagicMock()
        data = {"N": 8}
        result = fit_and_summarize(
            model, data, model_name="test", n_thinned_draws=50
        )

        assert isinstance(result, FitResult)
        assert result.model_name == "test"
        assert isinstance(result.convergence, ConvergenceResult)
        assert result.convergence.n_divergent == 0
        mock_fit_model.assert_called_once()
        mock_to_arviz.assert_called_once()
        assert mock_to_arviz.call_args.args == (mock_fit,)
        mock_cleanup.assert_called_once_with(mock_fit)

    @patch("shared_utils.fit_pipeline.cleanup_csv_files")
    @patch("shared_utils.fit_pipeline.to_arviz")
    @patch("shared_utils.fit_pipeline.fit_model")
    def test_saves_to_dir(
        self,
        mock_fit_model,
        mock_to_arviz,
        mock_cleanup,
        eight_schools_posterior_idata,
        tmp_path: Path,
    ):
        """fit_and_summarize() saves results when save_dir is provided."""
        mock_fit = MagicMock()
        mock_fit.method_variables.return_value = {
            "divergent__": np.zeros(400),
            "treedepth__": np.full(400, 5),
            "energy__": np.random.randn(100, 4) + 100,
        }
        mock_fit.metadata.cmdstan_config = {"max_depth": 10}
        mock_fit_model.return_value = mock_fit
        mock_to_arviz.return_value = eight_schools_posterior_idata
        mock_cleanup.return_value = 0

        model = MagicMock()
        fit_and_summarize(model, {"N": 1}, save_dir=tmp_path, n_thinned_draws=50)

        assert (tmp_path / "summary.json").exists()
        assert (tmp_path / "diagnostics.json").exists()


