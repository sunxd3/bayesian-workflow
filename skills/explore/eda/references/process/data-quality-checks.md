# Data Quality Checks

Always complete these checks regardless of focus area:

- **Missingness.** Per-column and per-row rates; flag columns >30% missing.
- **Missingness mechanism.** Does missingness correlate with other variables, time, or groups? If so, report the top predictors.
- **Duplicates.** Row-level and per-identifier.
- **Invalid values.** Constant columns, impossible ranges, sentinel values (`"NA"`, `"?"`, `"-999"`).
- **Type issues.** Numerics stored as strings, mixed-type columns.
