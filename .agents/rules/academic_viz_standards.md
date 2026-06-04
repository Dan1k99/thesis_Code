---
trigger: always_on
---

# Academic Visualization Standards
- **Resolution**: Save all figures at a minimum of 300 DPI (`dpi=300`) using vector-friendly formats (like `.pdf` or high-resolution `.png`).
- **Color Aesthetics**: Use uniform, colorblind-friendly continuous palettes (e.g., `viridis`, `plasma`) or clean semantic transitions (e.g., soft Green for healthy/0, scaling to Dark Red for severe/3). Avoid highly saturated primary colors.
- **Statistical Annotation**: Every comparative plot (e.g., Boxplots or Spaghetti lines) must display descriptive statistical text directly on the canvas, including Spearman rank correlation coefficients ($r_s$), Mann-Whitney U p-values, or sample sizes ($n$).
- **Layout Hygiene**: Always call `plt.tight_layout()` and set explicit font sizes via `plt.rc('font', size=...)` to prevent overlapping axis labels or legends.
