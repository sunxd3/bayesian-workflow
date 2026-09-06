# Final Report Structure

Narrative structure for the Phase 4 deliverable. For visual format (palette, typography, CSS skeleton), see `artifact-guidelines > references/html-report`; for the writing quality bar, the parent `report-writing` skill.

## Section template

Layer the report for different audiences:

### Executive Summary

Lead with what was learned about the data-generating process — the substantive insights, not the model name. State 3-5 key findings as answers to the structural questions that drove the analysis, each with uncertainty. Ground practical implications in the computed contrasts (see below). One page maximum.

### Methods

Model development process, final model specification, prior justification, computational details. Focus on the accepted model(s); briefly mention alternatives explored.

### Results

Organize by structural question, not by model. For each question the analysis investigated: what hypothesis was tested, what the evidence showed (with uncertainty), and what this tells us about the phenomenon. Models are supporting evidence for insights, not the headline. Include a **Practical Implications** subsection grounded in the computed contrasts — do not just report coefficient magnitudes.

### Discussion

What was learned, surprising findings, limitations (honest assessment), implications for the domain. Highlight negative results that were informative — a model that failed or a structure that wasn't supported by the data is an answer, not a failure.

### Supplementary

Model development journey, detailed diagnostics, all models compared, reproducibility details (code, data, environment).

## Practical Contrasts

Before writing the report, compute practical implications of the findings:

1. Load the selected model's posterior (`<selected_model_dir>/fit/posterior.nc`) and the original dataset from the dispatch's `data_path`.
2. Compute 1-3 practical contrasts: set key predictors to meaningful values (e.g., 10th vs 90th percentile of observed data) and compute the absolute difference in predicted outcome on the original scale.
3. Report these contrasts with uncertainty (posterior median ± 95% HDI of the difference).
4. Use these empirical results in the Practical Implications subsection — do not just report coefficient magnitudes.

## Substantive Writing Rules

- **Quantify uncertainty.** Never report point estimates without intervals or posterior summaries.
- **Connect to the analysis purpose.** State what decision each finding informs, and what was learned about the target quantities defined in the experiment plan.
- **Define domain terms on first use.** Non-specialist readers should be able to follow.
- **Report negative results.** A structure that the data did not support is an answer.
