# Framework Questioning

The most important check: **is this the right modeling framework given all the available data?**

LLMs tend to commit early to a framework and optimize within it. This check forces you to step back and ask whether the framework itself is appropriate. A framework mismatch is more consequential than any within-framework refinement.

## Unused data

Read the data files. List all variables and data features that the model does NOT use. For each unused variable, assess: does this variable contain information that could support a fundamentally different (and potentially better) modeling framework? Examples:

- Response times available but model only uses accuracy → could support a drift-diffusion or accumulator framework instead of SDT.
- Censoring indicators available but model treats all observations as complete → could support a survival/hazard framework.
- Confidence ratings available but model ignores them → could support a signal-plus-noise model with criterion parameters.
- Spatial coordinates available but model is non-spatial → could support a spatial process model.

## Framework alternatives

Given the full data (including unused variables), are there standard modeling frameworks in this domain that would be more appropriate than the one the model uses? Name them and state why they fit the data-generating process better.

## Data-generating process completeness

Does the model's generative story account for how the data was actually collected? Censoring, truncation, missing-data mechanisms, and selection processes are part of the data-generating process. A model that ignores them is misspecified even if its PPCs look fine on the observed data.

## Priority

If you identify a framework concern, flag it as the highest-priority issue — above any statistical or domain refinement suggestions.
