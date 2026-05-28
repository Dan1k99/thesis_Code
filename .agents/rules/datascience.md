---
trigger: always_on
---

# Data Science & Python Standards
- **Vectorization First**: Always prioritize NumPy/Pandas vectorized operations over explicit loops for large datasets.
- **Type Hinting**: Use Python type hints for all function signatures to ensure data integrity.
- **Memory Management**: When handling satellite rasters, always use context managers (`with rasterio.open(...)`) to prevent memory leaks.
- **PEP 8**: Adhere strictly to PEP 8. Use descriptive variable names (e.g., `ndvi_mean` instead of `m`).
- **Documentation**: Every data transformation function must have a docstring explaining the input dimensions and expected output.