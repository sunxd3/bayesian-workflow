# Simulation-Based Calibration (SBC)

Rigorous, rank-uniformity-based fake-data simulation. From Talts, Betancourt, Simpson, Vehtari, Gelman (2018), *Validating Bayesian Inference Algorithms with Simulation-Based Calibration*, arXiv:1804.06788. Builds on Cook, Gelman, Rubin (2006).

## When to use SBC

- Single-draw fake-data simulation passes but you suspect the inference algorithm is miscalibrated (subtle posterior shrinkage bias, wrong tails).
- High-stakes modeling decisions where you want algorithm-level guarantees, not just a single recovery check.
- New custom likelihoods or non-standard priors where calibration isn't established by reference.

## Idea

If the inference algorithm is correctly calibrated, then for any parameter θ:

> For each replicate, draw θ\* from the prior, simulate data y\* from p(y | θ\*), fit the model to y\*, and compute the rank of θ\* among the posterior draws of θ. Across many replicates, these ranks should be uniformly distributed on `{0, 1, ..., M}` (where M is the number of posterior draws kept per replicate).

Deviations from uniform indicate miscalibration:

- **U-shape** → posterior is *underdispersed* (overconfident)
- **Inverted-U (mound)** → posterior is *overdispersed* (underconfident)
- **Skewed** → systematic bias in one direction
- **Spikes at boundaries** → algorithm fails to explore the tails

## Procedure

1. **Choose number of replicates R** — typically 100–1000. More = sharper diagnostic, higher cost.
2. **For r = 1..R:**
   a. Draw θ\* from the prior and simulate y\* from p(y | θ\*) — both in a
      single GQ-only Stan program (see `stan > Pattern 1: Prior Simulation`).
      Extract both the parameter draw and the simulated data from the fit.
   b. Fit `model.stan` to y\* with thinned draws (typically M = 99 or 999 to
      make rank computation clean).
   c. For each parameter of interest, compute the rank of θ\* among posterior
      draws.
3. **Diagnose**: histogram of ranks for each parameter; should look uniform. Use the ECDF-difference plot from Säilynoja et al. for sharper visual diagnostics.

## Stan ecosystem support

- **`SBC` R package** (Hyunji Moon, Martin Modrák, et al.). Full SBC pipeline with rank histograms and ECDF plots.
- **Stan User's Guide.** See [Simulation-Based Calibration](https://mc-stan.org/docs/stan-users-guide/simulation-based-calibration.html).
- **CmdStanPy.** No first-class SBC harness; implement by looping the posterior fit over replicates and accumulating ranks.

## Cost note

SBC is R × the cost of a single fit. For a model that takes 10 min to fit, SBC with R=200 is ~33 hours. Reserve for cases where the cost is justified.
