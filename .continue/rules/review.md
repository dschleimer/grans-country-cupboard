---
invokable: true
---

Review this code for potential issues, including:

- **Jekyll configuration**: Verify `_config.yml` settings, collection definitions, and remote theme version are correct and compatible with the current Jekyll version.
- **Front‑matter consistency**: Check each markdown file under `_book_recipes`, `_book_pages`, and `_book_chapters` for required fields (`layout`, `page`, `recipe`, `page_order`, etc.) and proper YAML indentation.
- **Markdown tables**: Look for tables that may be poorly formatted. Ensure the Python formatter (`_tools/format_recipes.py`) can handle them; flag tables missing a header/separator row or with uneven columns.
- **Fraction & temperature normalization**: Confirm that ASCII fractions (e.g., `1/2`) and temperature literals (`32F`, `300 degrees`) are present where appropriate and that the formatter will replace them with Unicode characters.
- **Python script quality**: Scan `_tools/format_recipes.py` and `recipe_stats.py` for unused imports, duplicated logic, and edge‑case handling (e.g., malformed tables, unknown temperature units). Suggest adding unit tests for the helper functions.
- **Node dependencies**: Review `package.json` for unnecessary or outdated dev dependencies. Ensure Wrangler version (`^4.x`) aligns with the `wrangler.toml` output directory (`_site`).
- **Security variables**: Verify Turnstile site keys in `_config.yml` and `wrangler.toml` are not hard‑coded in public files; they should be stored as environment variables.
- **Build scripts**: Check the npm scripts (if any) and the Bundler workflow. Make sure `bundle exec jekyll serve` and `npm run publish` work without requiring extra manual steps.
- **Cross‑platform compatibility**: Look for Windows‑specific gems (`wdm`, `tzinfo-data`) and ensure they are conditionally loaded only on Windows platforms.
- **General code hygiene**: Spot duplicated code, large functions that could be split, missing docstrings, and any lint warnings from Ruby, Python, or JavaScript tooling.

Provide specific, actionable feedback for each finding, suggesting concrete fixes or improvements.
