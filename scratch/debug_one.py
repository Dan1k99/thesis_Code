import sys
import os
import time
import re
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import rasterio.mask
import rasterio.transform
from rasterio.windows import Window
import pyproj
from shapely.geometry import box
from datetime import datetime, timedelta
from scipy.spatial import KDTree
from scipy.ndimage import uniform_filter
from skimage.feature import graycomatrix

# --- Pre-allocate GLCM weights ---
i_idx, j_idx = np.ogrid[:256, :256]
GLCM_HOMO_WEIGHTS = 1.0 / (1.0 + (i_idx - j_idx) ** 2)
GLCM_HOMO_WEIGHTS = GLCM_HOMO_WEIGHTS[:, :, np.newaxis, np.newaxis]

sample_dates = {
    "Boundary_Fields_Baseline_2011 — Eden_gimel": "03.06.11",
}

POLYGON_GPKG_PATH = "qgis/all_layers_with_polygons.gpkg"
CLEAN_TABLES_DIR = "clean_tables"
EXTRACTED_LAYERS_DIR = "extracted_layers"
OUT_HISTORICAL_DIR = "pixel_temporal_datasets_long"

def debug_process_field(csv_name):
    t0 = time.time()
    print("1. Initializing mapping...")
    short_name = "Eden_gimel"
    poly_layer_name = "Eden_gimel"
    chips_dir = "data/raw_chips"
    out_dir = OUT_HISTORICAL_DIR
    os.makedirs(out_dir, exist_ok=True)
    out_csv_path = os.path.join(out_dir, f"{short_name}_debug_features.csv")
    csv_path = os.path.join(CLEAN_TABLES_DIR, csv_name)
    pts_gpkg_path = os.path.join(EXTRACTED_LAYERS_DIR, csv_name.replace(".csv", ".gpkg"))
    
    print("2. Loading and validating CSV...")
    t_csv = time.time()
    df_table = pd.read_csv(csv_path)
    print(f"   Loaded CSV in {time.time() - t_csv:.3f}s, rows: {len(df_table)}")
    
    print("3. Loading points GPKG...")
    t_gpkg = time.time()
    gdf_pts = gpd.read_file(pts_gpkg_path)
    print(f"   Loaded GPKG in {time.time() - t_gpkg:.3f}s, rows: {len(gdf_pts)}")
    
    pt_ids = []
    for i in range(len(df_table)):
        pt_id = None
        for col_candidate in ["_ID", "id", "ID", "ObjectID", "OBJECTID", "Od", "Id", "Idpocket"]:
            if col_candidate in df_table.columns:
                pt_id = df_table[col_candidate].iloc[i]
                break
        if pt_id is None:
            pt_id = i + 1
        pt_ids.append(pt_id)
        
    gdf_pts["Aleket_cnt_clean"] = df_table["Aleket_cnt"]
    gdf_pts["Point_ID_clean"] = pt_ids
    
    print("4. Loading polygon geometry...")
    t_poly = time.time()
    gdf_poly = gpd.read_file(POLYGON_GPKG_PATH, layer=poly_layer_name)
    print(f"   Loaded Polygon in {time.time() - t_poly:.3f}s")
    
    gdf_poly_32636 = gdf_poly.to_crs("EPSG:32636")
    poly_geom_32636 = gdf_poly_32636.geometry.iloc[0]
    poly_bbox = poly_geom_32636.bounds
    poly_box = box(*poly_bbox)
    
    print("5. Searching for overlapping chips...")
    t_chips = time.time()
    csv_base = csv_name.replace(".csv", "")
    sample_date = pd.to_datetime(sample_dates[csv_base], format="%d.%m.%y")
    start_date = sample_date - timedelta(days=60)
    
    valid_chips = []
    for f in os.listdir(chips_dir):
        if not f.endswith(".tif") or "udm" in f.lower() or "sr" not in f.lower():
            continue
        chip_path = os.path.join(chips_dir, f)
        try:
            with rasterio.open(chip_path) as src:
                chip_box = box(*src.bounds)
                if poly_box.intersects(chip_box) and poly_geom_32636.intersects(chip_box):
                    match = re.search(r"(20\d{2}-?\d{2}-?\d{2})", f)
                    if match:
                        acq_date = pd.to_datetime(match.group(1))
                        if start_date <= acq_date <= sample_date:
                            valid_chips.append({"path": chip_path, "date": acq_date})
        except Exception as e:
            pass
    print(f"   Found {len(valid_chips)} chips in {time.time() - t_chips:.3f}s")
    
    print("6. Pruning dates...")
    unique_dates = sorted(list(set([c["date"] for c in valid_chips])))
    selected_dates = []
    if unique_dates:
        selected_dates.append(unique_dates[0])
        for d in unique_dates[1:]:
            if (d - selected_dates[-1]).days >= 4:
                selected_dates.append(d)
    print(f"   Selected dates: {[d.strftime('%Y-%m-%d') for d in selected_dates]}")
    
    date_to_chips = {d: [] for d in selected_dates}
    for c in valid_chips:
        if c["date"] in selected_dates:
            date_to_chips[c["date"]].append(c["path"])
            
    print("7. Selecting master chip...")
    t_master = time.time()
    best_chip_path = None
    best_pixel_count = -1
    best_out_image = None
    best_out_transform = None
    best_src_master_crs = None
    nir_idx, green_idx, red_idx, red_edge_idx = 4, 1, 2, 3
    
    for d in selected_dates:
        for chip_path in date_to_chips[d]:
            try:
                with rasterio.open(chip_path) as src:
                    out_image, out_transform = rasterio.mask.mask(src, [poly_geom_32636], crop=True, nodata=0)
                    nir_band = out_image[nir_idx]
                    valid_count = (nir_band > 0).sum()
                    if valid_count > best_pixel_count:
                        best_pixel_count = valid_count
                        best_chip_path = chip_path
                        best_out_image = out_image
                        best_out_transform = out_transform
                        best_src_master_crs = src.crs
            except Exception as e:
                pass
    print(f"   Master chip selected in {time.time() - t_master:.3f}s, pixels: {best_pixel_count}")
    
    nir_master = best_out_image[nir_idx]
    valid_rows, valid_cols = np.where(nir_master > 0)
    xs_utm36n, ys_utm36n = rasterio.transform.xy(best_out_transform, valid_rows, valid_cols, offset="center")
    xs_utm36n = np.array(xs_utm36n)
    ys_utm36n = np.array(ys_utm36n)
    
    transformer_to_wgs84 = pyproj.Transformer.from_crs(best_src_master_crs, "EPSG:4326", always_xy=True)
    lons_wgs84, lats_wgs84 = transformer_to_wgs84.transform(xs_utm36n, ys_utm36n)
    
    print("8. Point matching via KDTree...")
    t_kdtree = time.time()
    gdf_pts_proj = gdf_pts.to_crs("EPSG:32636")
    pt_coords_utm36n = np.column_stack((gdf_pts_proj.geometry.x, gdf_pts_proj.geometry.y))
    valid_pixel_coords_utm36n = np.column_stack((xs_utm36n, ys_utm36n))
    tree = KDTree(valid_pixel_coords_utm36n)
    distances, closest_indices = tree.query(pt_coords_utm36n)
    
    pixel_to_sample = {}
    for i, idx in enumerate(closest_indices):
        pt_id = gdf_pts["Point_ID_clean"].iloc[i]
        aleket_val = gdf_pts["Aleket_cnt_clean"].iloc[i]
        pixel_to_sample[idx] = (pt_id, aleket_val)
    print(f"   KDTree complete in {time.time() - t_kdtree:.3f}s")
    
    print("9. Loop over dates for pixel extraction...")
    records = []
    angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
    
    for date_seq, d in enumerate(selected_dates, start=1):
        t_date_start = time.time()
        date_str = d.strftime("%d/%m/%Y")
        days_before = (sample_date - d).days
        chip_path = date_to_chips[d][0]
        
        with rasterio.open(chip_path) as src:
            minx, miny, maxx, maxy = poly_geom_32636.bounds
            py_min, px_min = src.index(minx, maxy)
            py_max, px_max = src.index(maxx, miny)
            row_start = max(0, min(py_min, py_max) - 10)
            row_end = min(src.height, max(py_min, py_max) + 10)
            col_start = max(0, min(px_min, px_max) - 10)
            col_end = min(src.width, max(px_min, px_max) + 10)
            
            win = Window(col_start, row_start, col_end - col_start, row_end - row_start)
            win_transform = src.window_transform(win)
            data = src.read(window=win).astype(float)
            
            green_band = data[green_idx]
            red_band = data[red_idx]
            red_edge_band = data[red_edge_idx]
            nir_band = data[nir_idx]
            
            denom_ndvi = nir_band + red_band
            ndvi_full = np.divide(nir_band - red_band, denom_ndvi, out=np.full_like(nir_band, np.nan), where=denom_ndvi != 0)
            denom_gndvi = nir_band + green_band
            gndvi_full = np.divide(nir_band - green_band, denom_gndvi, out=np.full_like(nir_band, np.nan), where=denom_gndvi != 0)
            gr_ratio_full = np.divide(green_band, red_band, out=np.full_like(green_band, np.nan), where=red_band != 0)
            denom_ndre = nir_band + red_edge_band
            ndre_full = np.divide(nir_band - red_edge_band, denom_ndre, out=np.full_like(nir_band, np.nan), where=denom_ndre != 0)
            
            t_filter = time.time()
            mean_green_band = uniform_filter(green_band, size=3, mode='reflect')
            mean_ndvi_band = uniform_filter(ndvi_full, size=3, mode='reflect')
            std_ndvi_band = np.sqrt(np.maximum(0, uniform_filter(ndvi_full**2, size=3, mode='reflect') - mean_ndvi_band**2))
            mean_gndvi_band = uniform_filter(gndvi_full, size=3, mode='reflect')
            mean_gr_ratio_band = uniform_filter(gr_ratio_full, size=3, mode='reflect')
            mean_ndre_band = uniform_filter(ndre_full, size=3, mode='reflect')
            print(f"   Uniform filter applied in {time.time() - t_filter:.3f}s")
            
            py_wins, px_wins = rasterio.transform.rowcol(win_transform, xs_utm36n, ys_utm36n)
            py_wins = np.array(py_wins)
            px_wins = np.array(px_wins)
            
            t_pixels_start = time.time()
            skipped_count = 0
            glcm_count = 0
            for idx_in_valid in range(len(xs_utm36n)):
                py_win = py_wins[idx_in_valid]
                px_win = px_wins[idx_in_valid]
                pixel_id = idx_in_valid + 1
                pt_id, aleket_val = pixel_to_sample.get(idx_in_valid, (np.nan, np.nan))
                lat_val = lats_wgs84[idx_in_valid]
                lon_val = lons_wgs84[idx_in_valid]
                
                if (py_win < 7 or px_win < 7 or 
                    py_win >= data.shape[1] - 7 or px_win >= data.shape[2] - 7 or
                    np.isnan(nir_band[py_win, px_win]) or nir_band[py_win, px_win] <= 0):
                    skipped_count += 1
                    record = {
                        "image": date_seq, "Pixel_ID": pixel_id, "Point_ID": pt_id, "Aleket_cnt": aleket_val,
                        "lat": lat_val, "long": lon_val, "date": date_str, "Days_Before_Sample": days_before,
                        "ndvi": np.nan, "ndvi_std": np.nan, "gndvi": np.nan, "green_red_ratio": np.nan,
                        "ndre": np.nan, "green": np.nan,
                        "entropy_5x5": np.nan, "entropy_15x15": np.nan,
                        "homogeneity_5x5": np.nan, "homogeneity_15x15": np.nan,
                        "asm_5x5": np.nan
                    }
                    records.append(record)
                    continue
                
                mean_green = mean_green_band[py_win, px_win]
                mean_ndvi = mean_ndvi_band[py_win, px_win]
                std_ndvi = std_ndvi_band[py_win, px_win]
                mean_gndvi = mean_gndvi_band[py_win, px_win]
                mean_gr_ratio = mean_gr_ratio_band[py_win, px_win]
                mean_ndre = mean_ndre_band[py_win, px_win]
                
                nir_win_5x5 = nir_band[py_win - 2 : py_win + 3, px_win - 2 : px_win + 3]
                nir_win_15x15 = nir_band[py_win - 7 : py_win + 8, px_win - 7 : px_win + 8]
                
                glcm_count += 1
                if np.all(nir_win_5x5 == nir_win_5x5[0, 0]):
                    homo_5x5 = 1.0
                    asm_5x5 = 1.0
                    entropy_5x5 = 0.0
                else:
                    nir_8bit_5x5 = np.clip(nir_win_5x5 / 10000.0 * 255, 0, 255).astype(np.uint8)
                    glcm_5x5 = graycomatrix(nir_8bit_5x5, distances=[1], angles=angles, symmetric=True, normed=True)
                    homo_5x5 = np.mean(np.sum(glcm_5x5 * GLCM_HOMO_WEIGHTS, axis=(0, 1)))
                    asm_5x5 = np.mean(np.sum(glcm_5x5 ** 2, axis=(0, 1)))
                    glcm_avg_5x5 = np.mean(glcm_5x5, axis=3)[:, :, 0]
                    entropy_5x5 = -np.sum(glcm_avg_5x5[glcm_avg_5x5 > 0] * np.log2(glcm_avg_5x5[glcm_avg_5x5 > 0]))
                    
                if np.all(nir_win_15x15 == nir_win_15x15[0, 0]):
                    homo_15x15 = 1.0
                    entropy_15x15 = 0.0
                else:
                    nir_8bit_15x15 = np.clip(nir_win_15x15 / 10000.0 * 255, 0, 255).astype(np.uint8)
                    glcm_15x15 = graycomatrix(nir_8bit_15x15, distances=[1], angles=angles, symmetric=True, normed=True)
                    homo_15x15 = np.mean(np.sum(glcm_15x15 * GLCM_HOMO_WEIGHTS, axis=(0, 1)))
                    glcm_avg_15x15 = np.mean(glcm_15x15, axis=3)[:, :, 0]
                    entropy_15x15 = -np.sum(glcm_avg_15x15[glcm_avg_15x15 > 0] * np.log2(glcm_avg_15x15[glcm_avg_15x15 > 0]))
                    
                record = {
                    "image": date_seq, "Pixel_ID": pixel_id, "Point_ID": pt_id, "Aleket_cnt": aleket_val,
                    "lat": lat_val, "long": lon_val, "date": date_str, "Days_Before_Sample": days_before,
                    "ndvi": mean_ndvi, "ndvi_std": std_ndvi, "gndvi": mean_gndvi, "green_red_ratio": mean_gr_ratio,
                    "ndre": mean_ndre, "green": mean_green,
                    "entropy_5x5": homo_5x5, "entropy_15x15": entropy_15x15, # Wait, wait, wait! Look at this!
                    "homogeneity_5x5": homo_5x5, "homogeneity_15x15": homo_15x15,
                    "asm_5x5": asm_5x5
                }
                records.append(record)
            print(f"   Date loop {date_seq} completed in {time.time() - t_date_start:.3f}s (pixels loop: {time.time() - t_pixels_start:.3f}s, GLCMs computed: {glcm_count}, skipped: {skipped_count})")
            
    print(f"10. Saving to CSV: {out_csv_path}")
    df_out = pd.DataFrame(records)
    df_out.to_csv(out_csv_path, index=False)
    print(f"Total time taken: {time.time() - t0:.2f}s")

if __name__ == "__main__":
    debug_process_field("Boundary_Fields_Baseline_2011 — Eden_gimel.csv")
