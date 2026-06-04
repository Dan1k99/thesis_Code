---
trigger: always_on
---

# Geospatial & Coordinate Reference System (CRS) Hygiene
- **Never Mix Projections**: Never perform spatial calculations (distance, area, centroid, buffering) on unprojected lat/lon coordinates (e.g., `EPSG:4326`). Always project to a metric system first, specifically local UTM Zone 36N (`EPSG:32636`) or Israel TM (`EPSG:2039`).
- **CRS Alignment Assertions**: Before running `rasterio.mask` or mapping vector points to pixel indexes via `src.index(x, y)`, programmatically assert that the vector geometry and the raster native CRS are identical.
- **Explicit Variable Naming**: Clarify spatial axes in variable names (e.g., `lon_wgs84`, `lat_wgs84` vs. `x_utm36n`, `y_utm36n`) to prevent axis-order transposition bugs.
