---
trigger: always_on
---

# Scientific Reproducibility & Portability
- **Deterministic Modeling**: Always define a fixed random seed/state (e.g., `random_state=42` or `np.random.seed(42)`) when fitting regressions, LOWESS models, or sampling points.
- **Portable Filepathing**: Never hardcode Windows-specific absolute paths or backslashes (`\`). Use Python's `pathlib.Path` or `os.path.join` to keep the codebase fully functional across Windows, Linux, and macOS.
- **Tabular Schema Assertions**: Validate column data types and mapping categories (e.g., asserting that `Aleket_cnt` is an integer type between 0 and 3) immediately upon loading CSV files from `clean_tables/`.
