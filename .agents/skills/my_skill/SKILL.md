---
name: satellite-processing
description: Expert skill for handling Planet API orders and Rasterio manipulations.
---
# Satellite Data Skill
Use this skill when processing satellite imagery or interacting with the Planet Orders API.

## Core Logic
1. **Band Mapping**: Default to Red (Band 3) and NIR (Band 4/8) for NDVI.
2. **Coordinate Alignment**: Always verify CRS (EPSG:4326 vs EPSG:2039) before spatial operations.
3. **Local Cropping**: Use the `rasterio.mask` module for local extraction to save quota.
4. **Cloud Handling**: If a pixel is flagged as "cloud" in the UDM2 mask, convert the output to `np.nan`.