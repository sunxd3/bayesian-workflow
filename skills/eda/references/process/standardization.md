# Standardization

Apply these transformations to produce a canonical cleaned dataset that downstream agents can trust. Standardization is mechanical cleanup driven by the semantic audit; it does not reinterpret what columns mean. Emit in a dtype-preserving format (e.g., Parquet, not CSV) and document the final schema (column names + dtypes) on output. The canonical file is `eda/data.cleaned.parquet`, written by the analyst that owns the canonical deliverables; its schema is documented in that analyst's `findings.md` and carried into `eda_report.html` (see the eda-analyst agent's Artifacts).

## Column names

- Convert to `snake_case` (lowercase, underscores for spaces/punctuation).
- Strip leading/trailing whitespace.
- Replace non-alphanumeric characters with `_`.
- Disambiguate duplicates with a numeric suffix (`col`, `col_2`, ...).

## Missing values

- Convert sentinel strings to NaN: `"NA"`, `"N/A"`, `"NULL"`, `"null"`, `""`, `"?"`, `"-"`, `"-999"`, `-999`.
- Domain-specific sentinels (e.g., `99` in survey data) require evidence from a data dictionary or distribution shape; flag and convert with justification.

## Types

- Parse timestamp strings to datetime; preserve timezone if present, do not silently convert.
- Coerce numerics stored as strings (`"1,234"` → `1234`, `"3.14"` → `3.14`).
- Harmonize booleans (`"yes"/"no"`, `"true"/"false"`, `0/1`) to `bool`.
- Store small-cardinality categorical columns as `category` dtype.

## Categorical encoding

- Trim whitespace.
- Normalize case only when purely cosmetic (e.g., `"Yes"` vs `"yes"`); preserve semantically meaningful case.
- Merge synonyms only with evidence (`"M"` vs `"Male"` → flag, propose, justify).
- Do not impose ordinal order without evidence from a data dictionary or domain knowledge.

## What NOT to standardize here

- **Scaling / centering / log transforms.** Belong in modeling (prior setting).
- **Imputation.** Leave NaNs for the modeling phase to handle explicitly.
- **Outlier removal.** Flag, do not drop.
- **Feature engineering.** Derived columns belong in modeling.

