"""Tests for shared_utils.io module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import arviz as az
import numpy as np
import pytest

from shared_utils.io import (
    NumpyEncoder,
    _filter_present,
    _sanitize_coords_dims,
    _stan_var_names,
    to_arviz,
    to_arviz_prior,
    write_json,
)

# ---------------------------------------------------------------------------
# Helper: create a mock fit that passes isinstance(fit, CmdStanMCMC)
# ---------------------------------------------------------------------------

class _MockCmdStanMCMC:
    """Lightweight stand-in for CmdStanMCMC that passes isinstance checks
    when we patch shared_utils.io.CmdStanMCMC with this class."""

    def __init__(self, stan_vars_cols: dict | None = None):
        self.stan_vars_cols = stan_vars_cols or {}


def _make_mock_fit(stan_vars_cols: dict | None = None) -> _MockCmdStanMCMC:
    return _MockCmdStanMCMC(stan_vars_cols)


# ---------------------------------------------------------------------------
# NumpyEncoder / write_json
# ---------------------------------------------------------------------------

class TestNumpyEncoder:
    """Tests for NumpyEncoder."""

    def test_numpy_bool(self):
        result = json.dumps({"v": np.bool_(True)}, cls=NumpyEncoder)
        assert json.loads(result) == {"v": True}

    def test_numpy_int(self):
        result = json.dumps({"v": np.int64(42)}, cls=NumpyEncoder)
        assert json.loads(result) == {"v": 42}

    def test_numpy_float(self):
        result = json.dumps({"v": np.float64(3.14)}, cls=NumpyEncoder)
        parsed = json.loads(result)
        assert abs(parsed["v"] - 3.14) < 1e-10

    def test_numpy_array(self):
        arr = np.array([1, 2, 3])
        result = json.dumps({"v": arr}, cls=NumpyEncoder)
        assert json.loads(result) == {"v": [1, 2, 3]}

    def test_non_numpy_falls_through(self):
        with pytest.raises(TypeError):
            json.dumps({"v": object()}, cls=NumpyEncoder)


class TestWriteJson:
    """Tests for write_json."""

    def test_writes_and_reads_back(self, tmp_path: Path):
        path = tmp_path / "test.json"
        payload = {"a": 1, "b": [2, 3]}
        write_json(path, payload)
        with open(path) as f:
            assert json.load(f) == payload

    def test_handles_numpy_types(self, tmp_path: Path):
        path = tmp_path / "numpy.json"
        payload = {
            "bool": np.bool_(False),
            "int": np.int64(99),
            "float": np.float64(2.718),
            "array": np.array([10, 20, 30]),
        }
        write_json(path, payload)
        with open(path) as f:
            result = json.load(f)
        assert result["bool"] is False
        assert result["int"] == 99
        assert abs(result["float"] - 2.718) < 1e-10
        assert result["array"] == [10, 20, 30]

    def test_creates_parent_dirs(self, tmp_path: Path):
        path = tmp_path / "a" / "b" / "c" / "data.json"
        write_json(path, {"x": 1})
        assert path.exists()


# ---------------------------------------------------------------------------
# _stan_var_names helper
# ---------------------------------------------------------------------------

class TestStanVarNames:
    """Tests for _stan_var_names.

    Fakes use ``spec=[...]`` so only the declared attributes exist — a bare
    MagicMock would answer every ``getattr`` with a truthy mock and hide which
    API the function actually read.
    """

    def test_from_metadata_stan_vars(self):
        """CmdStanPy >= 1.2: names live in fit.metadata.stan_vars."""
        fit = MagicMock(spec=["metadata"])
        fit.metadata = MagicMock(spec=["stan_vars"])
        fit.metadata.stan_vars = {"mu": object(), "y_rep": object()}
        assert _stan_var_names(fit) == {"mu", "y_rep"}

    def test_from_direct_attr(self):
        """Legacy: fit.stan_vars_cols."""
        fit = MagicMock(spec=["stan_vars_cols"])
        fit.stan_vars_cols = {"mu": [0], "tau": [1]}
        assert _stan_var_names(fit) == {"mu", "tau"}

    def test_from_metadata(self):
        """Legacy: fit.metadata.stan_vars_cols."""
        fit = MagicMock(spec=["metadata"])
        fit.metadata = MagicMock(spec=["stan_vars_cols"])
        fit.metadata.stan_vars_cols = {"alpha": [0], "beta": [1]}
        assert _stan_var_names(fit) == {"alpha", "beta"}

    def test_empty_when_nothing(self):
        fit = MagicMock(spec=[])
        fit.metadata = None
        assert _stan_var_names(fit) == set()


# ---------------------------------------------------------------------------
# _sanitize_coords_dims
# ---------------------------------------------------------------------------

class TestSanitizeCoordsDims:
    """Tests for _sanitize_coords_dims."""

    def test_none_returns_none(self):
        assert _sanitize_coords_dims(None) is None

    def test_numpy_array_to_list(self):
        result = _sanitize_coords_dims({"school": np.array([0, 1, 2])})
        assert result is not None
        assert result == {"school": [0, 1, 2]}
        assert isinstance(result["school"], list)

    def test_nested_dict(self):
        result = _sanitize_coords_dims({"inner": {"arr": np.array([5, 6])}})
        assert result == {"inner": {"arr": [5, 6]}}

    def test_list_with_arrays(self):
        result = _sanitize_coords_dims({"dims": [np.array([1, 2]), "x"]})
        assert result == {"dims": [[1, 2], "x"]}

    def test_plain_values_unchanged(self):
        result = _sanitize_coords_dims({"a": "hello", "b": 42})
        assert result == {"a": "hello", "b": 42}


# ---------------------------------------------------------------------------
# _filter_present
# ---------------------------------------------------------------------------

class TestFilterPresent:
    """Tests for _filter_present."""

    def test_filters_to_available(self):
        result = _filter_present(["y_rep", "log_lik", "missing"], available={"y_rep", "log_lik", "mu"})
        assert result == ["y_rep", "log_lik"]

    def test_empty_available_returns_all(self):
        result = _filter_present(["y_rep", "missing"], available=set())
        assert result == ["y_rep", "missing"]


# ---------------------------------------------------------------------------
# to_arviz
# ---------------------------------------------------------------------------

class TestToArviz:
    """Tests for to_arviz()."""

    def test_raises_for_non_cmdstan(self):
        """to_arviz() raises ValueError for non-CmdStanMCMC fit."""
        with pytest.raises(ValueError, match="fit must be CmdStanMCMC"):
            to_arviz("not a fit")  # pyright: ignore[reportArgumentType]

    @patch("shared_utils.io.az.from_cmdstanpy")
    @patch("shared_utils.io.CmdStanMCMC", _MockCmdStanMCMC)
    def test_filters_posterior_predictive(self, mock_from):
        """to_arviz() filters posterior_predictive vars against available."""
        mock_from.return_value = MagicMock(spec=az.InferenceData)
        fit = _make_mock_fit({"mu": [0], "tau": [1], "y_rep": [2]})

        to_arviz(fit, posterior_predictive=["y_rep", "nonexistent"])  # pyright: ignore[reportArgumentType]

        call_kwargs = mock_from.call_args[1]
        assert call_kwargs["posterior_predictive"] == ["y_rep"]

    @patch("shared_utils.io.az.from_cmdstanpy")
    @patch("shared_utils.io.CmdStanMCMC", _MockCmdStanMCMC)
    def test_defaults_to_y_rep_when_available(self, mock_from):
        """to_arviz() defaults to ['y_rep'] when available."""
        mock_from.return_value = MagicMock(spec=az.InferenceData)
        fit = _make_mock_fit({"mu": [0], "y_rep": [1]})

        to_arviz(fit)  # pyright: ignore[reportArgumentType]

        call_kwargs = mock_from.call_args[1]
        assert call_kwargs["posterior_predictive"] == ["y_rep"]

    @patch("shared_utils.io.az.from_cmdstanpy")
    @patch("shared_utils.io.CmdStanMCMC", _MockCmdStanMCMC)
    def test_sanitizes_coords_dims(self, mock_from):
        """to_arviz() sanitizes numpy arrays in coords/dims to lists."""
        mock_from.return_value = MagicMock(spec=az.InferenceData)
        fit = _make_mock_fit({"mu": [0]})

        to_arviz(
            fit,  # pyright: ignore[reportArgumentType]
            coords={"school": np.array([0, 1, 2])},
            dims={"mu": np.array(["school"])},
        )

        call_kwargs = mock_from.call_args[1]
        assert isinstance(call_kwargs["coords"]["school"], list)
        assert isinstance(call_kwargs["dims"]["mu"], list)

    @patch("shared_utils.io.az.from_cmdstanpy")
    @patch("shared_utils.io.CmdStanMCMC", _MockCmdStanMCMC)
    def test_no_y_rep_in_available(self, mock_from):
        """to_arviz() sets posterior_predictive=None when y_rep is not available."""
        mock_from.return_value = MagicMock(spec=az.InferenceData)
        fit = _make_mock_fit({"mu": [0], "tau": [1]})

        to_arviz(fit)  # pyright: ignore[reportArgumentType]

        call_kwargs = mock_from.call_args[1]
        assert call_kwargs["posterior_predictive"] is None


# ---------------------------------------------------------------------------
# to_arviz_prior
# ---------------------------------------------------------------------------

class TestToArvizPrior:
    """Tests for to_arviz_prior()."""

    def test_raises_for_non_cmdstan(self):
        """to_arviz_prior() raises ValueError for non-CmdStanMCMC fit."""
        with pytest.raises(ValueError, match="fit must be CmdStanMCMC"):
            to_arviz_prior("not a fit")  # pyright: ignore[reportArgumentType]

    @patch("shared_utils.io.az.from_cmdstanpy")
    @patch("shared_utils.io.CmdStanMCMC", _MockCmdStanMCMC)
    def test_calls_with_prior_kwarg(self, mock_from):
        """to_arviz_prior() calls az.from_cmdstanpy with prior=fit kwarg."""
        mock_from.return_value = MagicMock(spec=az.InferenceData)
        fit = _make_mock_fit({"mu": [0]})

        to_arviz_prior(fit)  # pyright: ignore[reportArgumentType]

        call_kwargs = mock_from.call_args[1]
        assert call_kwargs["prior"] is fit

    @patch("shared_utils.io.az.from_cmdstanpy")
    @patch("shared_utils.io.CmdStanMCMC", _MockCmdStanMCMC)
    def test_filters_prior_predictive(self, mock_from):
        """to_arviz_prior() filters prior_predictive vars."""
        mock_from.return_value = MagicMock(spec=az.InferenceData)
        fit = _make_mock_fit({"mu": [0], "y_rep": [1]})

        to_arviz_prior(fit, prior_predictive=["y_rep", "nonexistent"])  # pyright: ignore[reportArgumentType]

        call_kwargs = mock_from.call_args[1]
        assert call_kwargs["prior_predictive"] == ["y_rep"]

    @patch("shared_utils.io.az.from_cmdstanpy")
    @patch("shared_utils.io.CmdStanMCMC", _MockCmdStanMCMC)
    def test_defaults_to_y_rep_when_available(self, mock_from):
        """to_arviz_prior() defaults to ['y_rep'] when available."""
        mock_from.return_value = MagicMock(spec=az.InferenceData)
        fit = _make_mock_fit({"mu": [0], "y_rep": [1]})

        to_arviz_prior(fit)  # pyright: ignore[reportArgumentType]

        call_kwargs = mock_from.call_args[1]
        assert call_kwargs["prior_predictive"] == ["y_rep"]

    @patch("shared_utils.io.az.from_cmdstanpy")
    @patch("shared_utils.io.CmdStanMCMC", _MockCmdStanMCMC)
    def test_sanitizes_coords_dims(self, mock_from):
        """to_arviz_prior() sanitizes coords/dims."""
        mock_from.return_value = MagicMock(spec=az.InferenceData)
        fit = _make_mock_fit({"mu": [0]})

        to_arviz_prior(
            fit,  # pyright: ignore[reportArgumentType]
            coords={"idx": np.array([0, 1])},
            dims={"mu": np.array(["idx"])},
        )

        call_kwargs = mock_from.call_args[1]
        assert isinstance(call_kwargs["coords"]["idx"], list)
        assert isinstance(call_kwargs["dims"]["mu"], list)


