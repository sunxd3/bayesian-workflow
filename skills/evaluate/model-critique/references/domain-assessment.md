# Domain Assessment

Identify the scientific domain from the EDA report, experiment plan, and data. State it explicitly:

> **Domain identification**: [e.g., "Psychophysics — signal detection / classification under multisensory stimulation"]

If the domain is not recognizable (purely synthetic data, generic business metrics with no established domain theory), state "No strong domain conventions identified" and skip to framework questioning.

Read the Stan model file. Compare the code against both the Domain Context stated in the experiment plan AND your independent knowledge of the field. Flag discrepancies in either direction:

- The plan specified a domain component that the code omits → implementation regression.
- The plan itself missed a standard domain convention → plan blind spot.

Assess each dimension below. Be specific — cite the model's actual code and contrast it with what domain practice would dictate. Skip dimensions that are genuinely not applicable.

## Link function and response model

Is the functional form domain-standard? Examples of domain-canonical choices:

- **Psychophysics.** Probit (cumulative normal) or Weibull for psychometric functions.
- **Dose-response.** Log-logistic or Hill equation.
- **Survival analysis.** Hazard-based models (Cox, Weibull, exponential).
- **Population ecology.** Lotka-Volterra, Beverton-Holt, Ricker.
- **Pharmacokinetics.** Compartmental models with first-order kinetics.

A logistic link may work statistically but miss the theoretical foundation. State whether the model's choice is domain-standard, a defensible alternative, or a mismatch.

## Missing domain-standard model components

Most scientific domains have known structural components that competent domain modelers include as baseline expectations. Examples:

- **Psychophysics.** Lapse rates (stimulus-independent error floor/ceiling), guessing rates for forced-choice.
- **Epidemiology.** Exposure offsets, reporting delays, age-period-cohort structure.
- **Ecology.** Detection probability, abundance vs occupancy, carrying capacity.
- **Pharmacology.** Saturation kinetics (Michaelis-Menten), receptor binding curves.
- **Cognitive science.** Contaminant processes (fast guesses, attentional lapses).

Identify missing components and explain why they matter (e.g., missing lapse rate forces the sigmoid to reach 0/1 asymptotes, inflating slope estimates).

## Parameterization and mechanistic interpretability

Does the parameterization map to scientifically meaningful quantities, or does it capture the right shape for the wrong reason?

- **Domain quantities.** Are parameters interpretable as domain quantities (threshold, sensitivity, capacity, rate constant) or generic regression coefficients?
- **Alternative parameterization.** Would a different parameterization preserve statistical fit while enabling domain-meaningful inference?
- **Purpose alignment.** Does the parameterization align with the analysis purpose?

## Predictor selection and causal structure

- **Causal variable.** Does the model use the scientifically causal variable, or a correlated proxy?
- **Known confounds.** Are there known confounds in this domain that the model does not control for?
- **Direction.** Is the direction of influence correct?

## Model structure and known domain phenomena

- **Nonlinearity.** Are there nonlinearities, saturation effects, or threshold effects known in this domain that the model assumes away with linearity?
- **Known interactions.** Are there known interaction patterns?
- **Grouping respect.** Does the hierarchical structure respect the natural grouping?
