# Setup: Measurement Story & Observation Unit

## Measurement story

Before choosing any distribution, commit to the measurement story. Write one sentence:

> "For each [unit], there is a latent [quantity]. The observed [variable] is [relationship] corrupted by [noise source], which [scales how]."

This forces you to separate the **process model** (noiseless latent truth) from the **observation model** (how instruments, sampling, and recording produce the data you see).

Check for observation process artifacts: censoring (measurement caps out), truncation (some values never recorded), rounding or heaping, selection bias (only certain units observed). These are likelihood features, not preprocessing details.

## Observation unit & independence

State explicitly:

- **What is one row of data?** (e.g., person-day, sensor-reading, aggregated daily count). Do not aggregate data to fit a simpler likelihood; model at the measured resolution and use hierarchy to infer at higher levels.
- **Can rows be permuted without changing meaning?** If yes, conditional independence given parameters is plausible. If no (time ordering, spatial adjacency, nesting), specify the dependence structure explicitly.

**Evaluation implications.** The data structure determines which validation tools are reliable downstream. For i.i.d. data, standard LOO and ELPD comparisons work. For temporal or spatial dependence, standard LOO overstates predictive performance — specify appropriate validation (rolling-origin, leave-future-out, leave-group-out) in your falsification criteria. This choice should already have been made in `analysis-design > Validation strategy`; see `bayesian-model-diagnostics` for the per-model preconditions.
