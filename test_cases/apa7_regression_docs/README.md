# APA 7 Regression DOCX Test Cases

This folder contains Word documents for manual and automated regression testing of the dissertation review tool.

Use the files in `docs/` as upload examples in the frontend. The expected rule coverage is listed in `manifest.json`.

## Files

- `01_mechanics_numbers_punctuation.docx` - number, punctuation, ellipsis, dash, and unit rules.
- `02_citations_and_matching.docx` - in-text citation formatting plus citation/reference matching.
- `03_style_bias_language.docx` - passive voice, scholarly style, and bias-free language rules.
- `04_headings_lists_tables.docx` - headings, list formatting, table/figure references, and paragraph checks.
- `05_reference_formatting.docx` - reference-list formatting and retrieval rules.
- `06_false_positive_traps.docx` - examples that should mostly remain unflagged.

Regenerate the DOCX files with:

```powershell
python test_cases\apa7_regression_docs\generate_regression_docs.py
```

The generator overwrites files in `docs/`.

Validate the expected rule coverage with:

```powershell
python test_cases\apa7_regression_docs\validate_regression_docs.py
```
