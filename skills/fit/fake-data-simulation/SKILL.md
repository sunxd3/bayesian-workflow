---
name: fake-data-simulation
description: Methodology for fake-data simulation — drawing or fixing true parameter values, simulating data from the model, refitting, and checking that inference recovers the parameters. Covers single-draw checks (cheap) and Simulation-Based Calibration (rigorous).
user-invocable: false
---

# Fake-Data Simulation

Pick known parameters, simulate data from the model, refit, and check that the inference recovers what you put in.

## Variants

- `references/single-draw.md` — one set of true parameter values, simulate once, refit, check that the posterior covers the truth. Cheap. Catches obvious model bugs and Stan-program errors.
- `references/sbc.md` — Simulation-Based Calibration (Talts, Betancourt, Simpson, Vehtari, Gelman, 2018). Many draws from the prior, refit each, check rank uniformity. Rigorous. Validates the inference algorithm's calibration, not just whether one truth can be recovered.
- `references/decision.md` — PASS / FAIL criteria and common failure modes (model misspecification, non-identifiability, computational geometry).

**Default to single-draw** for the pre-fit gate in the workflow. **Escalate to SBC** when single-draw passes but you suspect inference miscalibration, or when the modeling choice is high-stakes enough to warrant rank-based validation.

## Key Practice — Stan is the single source of truth

All data generation must happen in Stan. Python chooses parameter values, passes them to Stan as `data`, and reads back the simulated observations. **Python must NOT implement the generative model** — no `numpy.random`, no `scipy.stats` for generating synthetic observations. If the simulator is written in Python, fake-data simulation validates Python-to-Python consistency, not the Stan model itself.

The `simulator.stan` file is a generated-quantities-only Stan program (no `parameters` block, no `model` block). Its transformed-parameter computation and `_rng` calls must be a **line-by-line mirror** of the corresponding blocks in `model.stan`. See `references/single-draw.md` for the canonical pattern.
