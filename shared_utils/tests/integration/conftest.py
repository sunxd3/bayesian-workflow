"""Fixtures for the real-CmdStan integration suite.

Everything in this directory compiles a Stan program and runs NUTS. Nothing is
mocked: the point is to prove the library produces correct numbers and the
exact artifact contract the workflow agents and scripts depend on.

Without a CmdStan installation the suite is skipped — unless
SHARED_UTILS_REQUIRE_CMDSTAN=1 is set, in which case a missing installation is
an error. CI sets it, so "skipped" can never masquerade as "passed".
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

STAN_DIR = Path(__file__).parent.parent / "stan"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Ground truth for the synthetic normal data and the fake-data simulator.
TRUE_MU = 2.0
TRUE_SIGMA = 1.5
N_OBS = 200


def _cmdstan_available() -> bool:
    try:
        import cmdstanpy

        cmdstanpy.cmdstan_path()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def _require_cmdstan() -> None:
    if _cmdstan_available():
        return
    if os.environ.get("SHARED_UTILS_REQUIRE_CMDSTAN") == "1":
        pytest.fail(
            "SHARED_UTILS_REQUIRE_CMDSTAN=1 but no CmdStan installation was found",
            pytrace=False,
        )
    pytest.skip(
        "CmdStan not installed — integration suite skipped "
        "(set SHARED_UTILS_REQUIRE_CMDSTAN=1 to make this an error)"
    )


@pytest.fixture(scope="session")
def compiled() -> Callable[[str], object]:
    """Compile each test model at most once per session."""
    from shared_utils import compile_model

    cache: dict[str, object] = {}

    def get(name: str):
        if name not in cache:
            cache[name] = compile_model(STAN_DIR / f"{name}.stan")
        return cache[name]

    return get


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
def normal_fit(compiled, normal_data, tmp_path_factory):
    """One canonical fit_and_summarize run, shared by the contract tests.

    Returns (result, save_dir, stan_output_dir).
    """
    from shared_utils import fit_and_summarize

    save_dir = tmp_path_factory.mktemp("normal_fit")
    stan_out = tmp_path_factory.mktemp("normal_csv")
    result = fit_and_summarize(
        compiled("normal"),
        normal_data,
        model_name="normal",
        iter_warmup=500,
        iter_sampling=500,
        save_dir=save_dir,
        save_netcdf=True,
        output_dir=stan_out,
        seed=1,
    )
    return result, save_dir, stan_out


@pytest.fixture(scope="session")
def funnel_fit(compiled, tmp_path_factory):
    """Neal's funnel with a low adapt_delta: real divergences, no log_lik."""
    from shared_utils import fit_and_summarize

    save_dir = tmp_path_factory.mktemp("funnel_fit")
    result = fit_and_summarize(
        compiled("funnel"),
        {},
        model_name="funnel",
        iter_warmup=500,
        iter_sampling=500,
        adapt_delta=0.8,
        n_thinned_draws=0,
        save_dir=save_dir,
        output_dir=tmp_path_factory.mktemp("funnel_csv"),
        seed=3,
    )
    return result, save_dir


@pytest.fixture(scope="session")
def eight_schools_fit(compiled, eight_schools_data, tmp_path_factory):
    from shared_utils import fit_and_summarize

    save_dir = tmp_path_factory.mktemp("eight_schools_fit")
    result = fit_and_summarize(
        compiled("eight_schools_noncentered"),
        eight_schools_data,
        model_name="eight_schools",
        iter_warmup=1000,
        iter_sampling=2000,
        save_dir=save_dir,
        save_netcdf=True,
        output_dir=tmp_path_factory.mktemp("eight_schools_csv"),
        seed=8,
    )
    return result, save_dir
