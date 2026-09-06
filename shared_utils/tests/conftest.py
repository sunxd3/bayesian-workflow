"""Shared test fixtures for shared_utils tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import arviz as az
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Fixtures directory
# ---------------------------------------------------------------------------

@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to the tests/fixtures/ directory."""
    return Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Programmatic InferenceData fixtures (via az.from_dict)
# ---------------------------------------------------------------------------

RNG = np.random.default_rng(42)

N_CHAINS = 4
N_DRAWS = 500  # enough for ESS > 400 with IID draws
N_SCHOOLS = 8
Y_OBS = np.array([28, 8, -3, 7, -1, 1, 18, 12])
SIGMA = np.array([15, 10, 16, 11, 9, 11, 10, 18])


@pytest.fixture
def eight_schools_posterior_idata() -> az.InferenceData:
    """Well-behaved Eight Schools posterior InferenceData.

    4 chains x 250 draws, with posterior, posterior_predictive,
    log_likelihood, observed_data, and sample_stats groups.
    All chains draw from the same distribution so r_hat ~ 1.
    """
    rng = np.random.default_rng(123)

    # Use simple IID draws (no hierarchical dependence) to guarantee
    # r_hat ~ 1.0 and high ESS across all chains.
    mu = rng.normal(7.5, 4.5, size=(N_CHAINS, N_DRAWS))
    tau = np.abs(rng.normal(5.0, 3.5, size=(N_CHAINS, N_DRAWS)))

    theta = np.zeros((N_CHAINS, N_DRAWS, N_SCHOOLS))
    for j in range(N_SCHOOLS):
        theta[..., j] = rng.normal(7.0, 6.0, size=(N_CHAINS, N_DRAWS))

    y_rep = np.zeros((N_CHAINS, N_DRAWS, N_SCHOOLS))
    for j in range(N_SCHOOLS):
        y_rep[..., j] = rng.normal(theta[..., j], SIGMA[j])

    log_lik = np.zeros((N_CHAINS, N_DRAWS, N_SCHOOLS))
    for j in range(N_SCHOOLS):
        log_lik[..., j] = (
            -0.5 * np.log(2 * np.pi * SIGMA[j] ** 2)
            - 0.5 * ((Y_OBS[j] - theta[..., j]) / SIGMA[j]) ** 2
        )

    diverging = np.zeros((N_CHAINS, N_DRAWS), dtype=bool)

    return az.from_dict(
        posterior={"mu": mu, "tau": tau, "theta": theta},
        posterior_predictive={"y_rep": y_rep},
        log_likelihood={"log_lik": log_lik},
        observed_data={"y": Y_OBS},
        sample_stats={"diverging": diverging},
        coords={"school": np.arange(N_SCHOOLS)},
        dims={"theta": ["school"], "y_rep": ["school"], "log_lik": ["school"]},
    )


@pytest.fixture
def eight_schools_prior_idata() -> az.InferenceData:
    """Eight Schools prior predictive InferenceData.

    4 chains x 250 draws, with prior, prior_predictive, and observed_data groups.
    """
    rng = np.random.default_rng(456)

    mu = rng.normal(0, 20, size=(N_CHAINS, N_DRAWS))
    tau = rng.exponential(10, size=(N_CHAINS, N_DRAWS))

    theta = np.zeros((N_CHAINS, N_DRAWS, N_SCHOOLS))
    for j in range(N_SCHOOLS):
        theta[..., j] = rng.normal(mu, tau)

    y_rep = np.zeros((N_CHAINS, N_DRAWS, N_SCHOOLS))
    for j in range(N_SCHOOLS):
        y_rep[..., j] = rng.normal(theta[..., j], SIGMA[j])

    return az.from_dict(
        prior={"mu": mu, "tau": tau, "theta": theta},
        prior_predictive={"y_rep": y_rep},
        observed_data={"y": Y_OBS},
        coords={"school": np.arange(N_SCHOOLS)},
        dims={"theta": ["school"], "y_rep": ["school"]},
    )


@pytest.fixture
def divergent_idata() -> az.InferenceData:
    """Poorly-behaved InferenceData with divergences and high r_hat.

    Chains are deliberately offset to produce high r_hat.
    Some diverging=True in sample_stats.
    """
    rng = np.random.default_rng(789)

    # Offset chains to produce high r_hat
    mu = np.zeros((N_CHAINS, N_DRAWS))
    for c in range(N_CHAINS):
        mu[c] = rng.normal(7.5 + c * 8.0, 1.0, size=N_DRAWS)

    tau = np.abs(rng.normal(5, 3, size=(N_CHAINS, N_DRAWS)))
    theta = np.zeros((N_CHAINS, N_DRAWS, N_SCHOOLS))
    for j in range(N_SCHOOLS):
        theta[..., j] = rng.normal(mu, tau)

    y_rep = np.zeros((N_CHAINS, N_DRAWS, N_SCHOOLS))
    for j in range(N_SCHOOLS):
        y_rep[..., j] = rng.normal(theta[..., j], SIGMA[j])

    log_lik = np.zeros((N_CHAINS, N_DRAWS, N_SCHOOLS))
    for j in range(N_SCHOOLS):
        log_lik[..., j] = (
            -0.5 * np.log(2 * np.pi * SIGMA[j] ** 2)
            - 0.5 * ((Y_OBS[j] - theta[..., j]) / SIGMA[j]) ** 2
        )

    diverging = np.zeros((N_CHAINS, N_DRAWS), dtype=bool)
    # Set 15 divergences per chain
    for c in range(N_CHAINS):
        div_idx = rng.choice(N_DRAWS, size=15, replace=False)
        diverging[c, div_idx] = True

    return az.from_dict(
        posterior={"mu": mu, "tau": tau, "theta": theta},
        posterior_predictive={"y_rep": y_rep},
        log_likelihood={"log_lik": log_lik},
        observed_data={"y": Y_OBS},
        sample_stats={"diverging": diverging},
        coords={"school": np.arange(N_SCHOOLS)},
        dims={"theta": ["school"], "y_rep": ["school"], "log_lik": ["school"]},
    )


# ---------------------------------------------------------------------------
# Fake CmdStan objects
# ---------------------------------------------------------------------------

class FakeCmdStanMCMC:
    """Fake CmdStanMCMC for testing without actual Stan fitting.

    Attributes:
        metadata: Object with stan_vars_cols attribute
        runset: Object with csv_files attribute pointing to temp CSV files
    """

    def __init__(
        self,
        stan_vars_cols: dict[str, list[int]] | None = None,
        method_variables_data: dict[str, np.ndarray] | None = None,
        csv_file_paths: list[str] | None = None,
    ):
        # metadata.stan_vars_cols
        metadata = MagicMock()
        metadata.stan_vars_cols = stan_vars_cols or {
            "mu": [0],
            "tau": [1],
            "theta": [2, 3, 4, 5, 6, 7, 8, 9],
            "y_rep": [10, 11, 12, 13, 14, 15, 16, 17],
            "log_lik": [18, 19, 20, 21, 22, 23, 24, 25],
        }
        metadata.cmdstan_config = {"max_depth": 10}
        self.metadata = metadata

        rng = np.random.default_rng(99)
        self._method_vars = method_variables_data or {
            "divergent__": np.zeros(400),
            "treedepth__": np.full(400, 5),
            "energy__": rng.normal(100, 10, size=(100, 4)),
        }

        # runset with csv_files
        if csv_file_paths is not None:
            runset = MagicMock()
            runset.csv_files = csv_file_paths
            self.runset = runset
        else:
            self.runset = None

    def method_variables(self) -> dict[str, np.ndarray]:
        return self._method_vars


class FakeCmdStanModel:
    """Fake CmdStanModel that records sample() calls."""

    def __init__(self, return_value: FakeCmdStanMCMC | None = None):
        self._return_value = return_value or FakeCmdStanMCMC()
        self.sample_calls: list[dict] = []

    def sample(self, **kwargs) -> FakeCmdStanMCMC:
        self.sample_calls.append(kwargs)
        return self._return_value


@pytest.fixture
def csv_files(tmp_path: Path) -> list[str]:
    """Create temporary CSV files mimicking CmdStan output."""
    paths = []
    for i in range(4):
        p = tmp_path / f"output_{i}.csv"
        p.write_text(f"# CmdStan output chain {i}\nlp__,mu\n-10.0,7.5\n")
        paths.append(str(p))
    return paths


@pytest.fixture
def fake_cmdstan_fit(csv_files: list[str]) -> FakeCmdStanMCMC:
    """FakeCmdStanMCMC with real temp CSV files attached."""
    return FakeCmdStanMCMC(csv_file_paths=csv_files)
