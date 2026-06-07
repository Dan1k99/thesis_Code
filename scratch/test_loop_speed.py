import os
import time
import geopandas as gpd
import pandas as pd
import rasterio
import rasterio.mask
import rasterio.transform
from rasterio.windows import Window
import numpy as np
from skimage.feature import graycomatrix

# Create test data
img = np.random.randint(0, 10000, (100, 100)).astype(float)
ndvi_full = np.random.random((100, 100))
gndvi_full = np.random.random((100, 100))
gr_ratio_full = np.random.random((100, 100))
ndre_full = np.random.random((100, 100))
green_band = np.random.randint(0, 10000, (100, 100)).astype(float)
nir_band = np.random.randint(0, 10000, (100, 100)).astype(float)

# Pre-allocate weights
i_idx, j_idx = np.ogrid[:256, :256]
GLCM_HOMO_WEIGHTS = 1.0 / (1.0 + (i_idx - j_idx) ** 2)
GLCM_HOMO_WEIGHTS = GLCM_HOMO_WEIGHTS[:, :, np.newaxis, np.newaxis]

angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]

# Let's time 1000 iterations
t_start = time.time()
t_slice = 0.0
t_glcm5 = 0.0
t_glcm15 = 0.0
t_math = 0.0

for idx in range(1000):
    py_win = 50
    px_win = 50
    
    t0 = time.time()
    # 3x3 Spectral windows
    ndvi_win = ndvi_full[py_win - 1 : py_win + 2, px_win - 1 : px_win + 2]
    gndvi_win = gndvi_full[py_win - 1 : py_win + 2, px_win - 1 : px_win + 2]
    gr_win = gr_ratio_full[py_win - 1 : py_win + 2, px_win - 1 : px_win + 2]
    ndre_win = ndre_full[py_win - 1 : py_win + 2, px_win - 1 : px_win + 2]
    green_win = green_band[py_win - 1 : py_win + 2, px_win - 1 : px_win + 2]

    # Slices for texture
    nir_win_5x5 = nir_band[py_win - 2 : py_win + 3, px_win - 2 : px_win + 3]
    nir_win_15x15 = nir_band[py_win - 7 : py_win + 8, px_win - 7 : px_win + 8]
    t_slice += time.time() - t0
    
    t0 = time.time()
    # 5x5 Texture calculations
    nir_8bit_5x5 = np.clip(nir_win_5x5 / 10000.0 * 255, 0, 255).astype(np.uint8)
    glcm_5x5 = graycomatrix(nir_8bit_5x5, distances=[1], angles=angles, symmetric=True, normed=True)
    t_glcm5 += time.time() - t0
    
    t0 = time.time()
    # 15x15 Texture calculations
    nir_8bit_15x15 = np.clip(nir_win_15x15 / 10000.0 * 255, 0, 255).astype(np.uint8)
    glcm_15x15 = graycomatrix(nir_8bit_15x15, distances=[1], angles=angles, symmetric=True, normed=True)
    t_glcm15 += time.time() - t0
    
    t0 = time.time()
    # Math
    mean_green = np.nanmean(green_win)
    mean_ndvi = np.nanmean(ndvi_win)
    std_ndvi = np.nanstd(ndvi_win)
    mean_gndvi = np.nanmean(gndvi_win)
    mean_gr_ratio = np.nanmean(gr_win)
    mean_ndre = np.nanmean(ndre_win)

    homo_5x5 = np.mean(np.sum(glcm_5x5 * GLCM_HOMO_WEIGHTS, axis=(0, 1)))
    asm_5x5 = np.mean(np.sum(glcm_5x5 ** 2, axis=(0, 1)))
    glcm_avg_5x5 = np.mean(glcm_5x5, axis=3)[:, :, 0]
    entropy_5x5 = -np.sum(glcm_avg_5x5[glcm_avg_5x5 > 0] * np.log2(glcm_avg_5x5[glcm_avg_5x5 > 0]))

    homo_15x15 = np.mean(np.sum(glcm_15x15 * GLCM_HOMO_WEIGHTS, axis=(0, 1)))
    glcm_avg_15x15 = np.mean(glcm_15x15, axis=3)[:, :, 0]
    entropy_15x15 = -np.sum(glcm_avg_15x15[glcm_avg_15x15 > 0] * np.log2(glcm_avg_15x15[glcm_avg_15x15 > 0]))
    t_math += time.time() - t0

t_end = time.time()
print(f"Total time for 1000 iterations: {t_end - t_start:.4f} seconds")
print(f"  Slicing: {t_slice:.4f}s")
print(f"  GLCM 5x5: {t_glcm5:.4f}s")
print(f"  GLCM 15x15: {t_glcm15:.4f}s")
print(f"  Math & Stats: {t_math:.4f}s")
