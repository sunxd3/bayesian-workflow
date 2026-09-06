"""Fixtures for testing the fit-pipeline reference scripts.

The scripts under skills/fit-pipeline/references/ are what agents copy and
adapt; they are loaded here by path (there is no package) and exercised two
ways: pure tests on synthetic InferenceData (no CmdStan) and integration tests
that compile and sample the Stan programs under tests/stan/ for real.

Without a CmdStan installation the integration tier is skipped — unless
REQUIRE_CMDSTAN=1 is set, in which case a missing installation is
an error. CI sets it, so "skipped" can never masquerade as "passed".
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import arviz as az
import numpy as np
import pytest

TESTS_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = TESTS_DIR.parent / "skills" / "fit-pipeline" / "references"
STAN_DIR = TESTS_DIR / "stan"
FIXTURES_DIR = TESTS_DIR / "fixtures"

# Ground truth for the synthetic normal data and the fake-data simulator.
TRUE_MU = 2.0
TRUE_SIGMA = 1.5
N_OBS = 200


def load_reference(name: str) -> ModuleType:
    """Import a reference script by path, as a module."""
    spec = importlib.util.spec_from_file_location(name, REFERENCES_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def posterior_fit() -> ModuleType:
    return load_reference("posterior_fit")


@pytest.fixture(scope="session")
def prior_predictive() -> ModuleType:
    return load_reference("prior_predictive")


@pytest.fixture(scope="session")
def fake_data() -> ModuleType:
    return load_reference("fake_data")


# ---------------------------------------------------------------------------
# Synthetic InferenceData (no CmdStan)
# ---------------------------------------------------------------------------

N_CHAINS = 4
N_DRAWS = 500
N_SCHOOLS = 8
Y_OBS = np.array([28, 8, -3, 7, -1, 1, 18, 12], dtype=float)
SIGMA = np.array([15, 10, 16, 11, 9, 11, 10, 18], dtype=float)


def _eight_schools_like(rng: np.random.Generator, *, offset_chains: bool, n_div_per_chain: int):
    mu = np.zeros((N_CHAINS, N_DRAWS))
    for c in range(N_CHAINS):
        mu[c] = rng.normal(7.5 + (c * 8.0 if offset_chains else 0.0), 4.5, size=N_DRAWS)
    tau = np.abs(rng.normal(5.0, 3.5, size=(N_CHAINS, N_DRAWS)))
    theta = rng.normal(7.0, 6.0, size=(N_CHAINS, N_DRAWS, N_SCHOOLS))
    y_rep = rng.normal(theta, SIGMA)
    log_lik = -0.5 * np.log(2 * np.pi * SIGMA**2) - 0.5 * ((Y_OBS - theta) / SIGMA) ** 2
    diverging = np.zeros((N_CHAINS, N_DRAWS), dtype=bool)
    for c in range(N_CHAINS):
        if n_div_per_chain:
            diverging[c, rng.choice(N_DRAWS, size=n_div_per_chain, replace=False)] = True
    energy = rng.normal(100, 10, size=(N_CHAINS, N_DRAWS))
    return az.from_dict(
        posterior={"mu": mu, "tau": tau, "theta": theta},
        posterior_predictive={"y_rep": y_rep},
        log_likelihood={"log_lik": log_lik},
        observed_data={"y": Y_OBS},
        sample_stats={"diverging": diverging, "energy": energy},
        coords={"school": np.arange(N_SCHOOLS)},
        dims={"theta": ["school"], "y_rep": ["school"], "log_lik": ["school"]},
    )


@pytest.fixture
def well_behaved_idata() -> az.InferenceData:
    """IID draws across chains: r_hat ~ 1, ESS high, no divergences."""
    return _eight_schools_like(np.random.default_rng(123), offset_chains=False, n_div_per_chain=0)


@pytest.fixture
def divergent_idata() -> az.InferenceData:
    """Offset chains (high r_hat) and 15 divergences per chain."""
    return _eight_schools_like(np.random.default_rng(789), offset_chains=True, n_div_per_chain=15)


@pytest.fixture
def prior_idata() -> az.InferenceData:
    rng = np.random.default_rng(456)
    mu = rng.normal(0, 20, size=(1, N_DRAWS))
    y_rep = rng.normal(mu[..., None], 10.0, size=(1, N_DRAWS, N_SCHOOLS))
    return az.from_dict(prior={"mu": mu}, prior_predictive={"y_rep": y_rep})


# ---------------------------------------------------------------------------
# Real CmdStan
# ---------------------------------------------------------------------------


def _cmdstan_available() -> bool:
    try:
        import cmdstanpy

        cmdstanpy.cmdstan_path()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def require_cmdstan() -> None:
    if _cmdstan_available():
        return
    if os.environ.get("REQUIRE_CMDSTAN") == "1":
        pytest.fail(
            "REQUIRE_CMDSTAN=1 but no CmdStan installation was found",
            pytrace=False,
        )
    pytest.skip(
        "CmdStan not installed — integration tests skipped "
        "(set REQUIRE_CMDSTAN=1 to make this an error)"
    )


@pytest.fixture(scope="session")
def normal_data() -> dict:
    rng = np.random.default_rng(20260906)
    return {"N": N_OBS, "y": rng.normal(TRUE_MU, TRUE_SIGMA, size=N_OBS)}


@pytest.fixture(scope="session")
def heavy_tailed_data() -> dict:
    """Student-t(3) data: a normal likelihood is misspecified here."""
    rng = np.random.default_rng(7)
    n = 400
    return {"N": n, "y": TRUE_MU + TRUE_SIGMA * rng.standard_t(3, size=n)}


@pytest.fixture(scope="session")
def eight_schools_data() -> dict:
    return json.loads((FIXTURES_DIR / "eight_schools_data.json").read_text())


@pytest.fixture(scope="session")
def normal_fit(require_cmdstan, posterior_fit, normal_data, tmp_path_factory):
    """One canonical posterior_fit.run, shared by the contract tests.

    Returns (result, save_dir, stan_output_dir).
    """
    save_dir = tmp_path_factory.mktemp("normal_fit")
    stan_out = tmp_path_factory.mktemp("normal_csv")
    result = posterior_fit.run(
        STAN_DIR / "normal.stan", normal_data, save_dir, model_name="normal",
        iter_warmup=500, iter_sampling=500, output_dir=stan_out, seed=1,
    )
    return result, save_dir, stan_out


@pytest.fixture(scope="session")
def funnel_fit(require_cmdstan, posterior_fit, tmp_path_factory):
    """Neal's funnel with a low adapt_delta: real divergences, no log_lik."""
    save_dir = tmp_path_factory.mktemp("funnel_fit")
    result = posterior_fit.run(
        STAN_DIR / "funnel.stan", {}, save_dir, model_name="funnel",
        iter_warmup=500, iter_sampling=500, adapt_delta=0.8, n_thinned=0,
        save_netcdf=False, output_dir=tmp_path_factory.mktemp("funnel_csv"), seed=3,
    )
    return result, save_dir


@pytest.fixture(scope="session")
def eight_schools_fit(require_cmdstan, posterior_fit, eight_schools_data, tmp_path_factory):
    save_dir = tmp_path_factory.mktemp("eight_schools_fit")
    result = posterior_fit.run(
        STAN_DIR / "eight_schools_noncentered.stan", eight_schools_data, save_dir,
        model_name="eight_schools", iter_warmup=1000, iter_sampling=2000,
        output_dir=tmp_path_factory.mktemp("eight_schools_csv"), seed=8,
    )
    return result, save_dir
