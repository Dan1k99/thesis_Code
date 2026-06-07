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

# Pre-compute weights flat
i_idx, j_idx = np.ogrid[:256, :256]
GLCM_HOMO_WEIGHTS_FLAT = (1.0 / (1.0 + (i_idx - j_idx) ** 2)).ravel()

sample_dates = {
    "Boundary_Fields_Baseline_2011 — Eden_gimel": "03.06.11",
}

POLYGON_GPKG_PATH = "qgis/all_layers_with_polygons.gpkg"
CLEAN_TABLES_DIR = "clean_tables"
EXTRACTED_LAYERS_DIR = "extracted_layers"
OUT_HISTORICAL_DIR = "pixel_temporal_datasets_long"

def compute_local_glcm_features(W, compute_asm=False):
    h_A, h_B = W[:, :-1].ravel(), W[:, 1:].ravel()
    v_A, v_B = W[:-1, :].ravel(), W[1:, :].ravel()
    d1_A, d1_B = W[:-1, :-1].ravel(), W[1:, 1:].ravel()
    d2_A, d2_B = W[:-1, 1:].ravel(), W[1:, :-1].ravel()
    
    p_dirs = []
    homos = []
    asms = []
    for A_dir, B_dir in [(h_A, h_B), (d1_A, d1_B), (v_A, v_B), (d2_A, d2_B)]:
        pairs_dir = A_dir.astype(np.int32) * 256 + B_dir.astype(np.int32)
        sym_pairs_dir = B_dir.astype(np.int32) * 256 + A_dir.astype(np.int32)
        all_pairs_dir = np.concatenate([pairs_dir, sym_pairs_dir])
        
        counts_dir = np.bincount(all_pairs_dir, minlength=256*256)
        p_dir = counts_dir / len(all_pairs_dir)
        
        p_dirs.append(p_dir)
        homos.append(np.sum(p_dir * GLCM_HOMO_WEIGHTS_FLAT))
        if compute_asm:
            asms.append(np.sum(p_dir ** 2))

    homo_val = np.mean(homos)
    asm_val = np.mean(asms) if compute_asm else None
    
    p_avg = np.mean(p_dirs, axis=0)
    p_avg_nz = p_avg[p_avg > 0]
    entropy_val = -np.sum(p_avg_nz * np.log2(p_avg_nz))
    
    return homo_val, entropy_val, asm_val

def debug_process_field(csv_name):
    t0 = time.time()
    short_name = "Eden_gimel"
    poly_layer_name = "Eden_gimel"
    chips_dir = "data/raw_chips"
    out_csv_path = os.path.join(OUT_HISTORICAL_DIR, f"{short_name}_debug_features2.csv")
    csv_path = os.path.join(CLEAN_TABLES_DIR, csv_name)
    pts_gpkg_path = os.path.join(EXTRACTED_LAYERS_DIR, csv_name.replace(".csv", ".gpkg"))
    
    df_table = pd.read_csv(csv_path)
    gdf_pts = gpd.read_file(pts_gpkg_path)
    
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
    
    gdf_poly = gpd.read_file(POLYGON_GPKG_PATH, layer=poly_layer_name)
    gdf_poly_32636 = gdf_poly.to_crs("EPSG:32636")
    poly_geom_32636 = gdf_poly_32636.geometry.iloc[0]
    poly_bbox = poly_geom_32636.bounds
    poly_box = box(*poly_bbox)
    
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
            
    unique_dates = sorted(list(set([c["date"] for c in valid_chips])))
    selected_dates = []
    if unique_dates:
        selected_dates.append(unique_dates[0])
        for d in unique_dates[1:]:
            if (d - selected_dates[-1]).days >= 4:
                selected_dates.append(d)
                
    date_to_chips = {d: [] for d in selected_dates}
    for c in valid_chips:
        if c["date"] in selected_dates:
            date_to_chips[c["date"]].append(c["path"])
            
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
                
    nir_master = best_out_image[nir_idx]
    valid_rows, valid_cols = np.where(nir_master > 0)
    xs_utm36n, ys_utm36n = rasterio.transform.xy(best_out_transform, valid_rows, valid_cols, offset="center")
    xs_utm36n = np.array(xs_utm36n)
    ys_utm36n = np.array(ys_utm36n)
    
    transformer_to_wgs84 = pyproj.Transformer.from_crs(best_src_master_crs, "EPSG:4326", always_xy=True)
    lons_wgs84, lats_wgs84 = transformer_to_wgs84.transform(xs_utm36n, ys_utm36n)
    
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
        
    records = []
    
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
            
            # Pre-convert nir_band to uint8 once for the entire slice
            nir_8bit_full = np.clip(nir_band / 10000.0 * 255, 0, 255).astype(np.uint8)
            
            mean_green_band = uniform_filter(green_band, size=3, mode='reflect')
            mean_ndvi_band = uniform_filter(ndvi_full, size=3, mode='reflect')
            std_ndvi_band = np.sqrt(np.maximum(0, uniform_filter(ndvi_full**2, size=3, mode='reflect') - mean_ndvi_band**2))
            mean_gndvi_band = uniform_filter(gndvi_full, size=3, mode='reflect')
            mean_gr_ratio_band = uniform_filter(gr_ratio_full, size=3, mode='reflect')
            mean_ndre_band = uniform_filter(ndre_full, size=3, mode='reflect')
            
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
                
                # Slices of pre-converted 8-bit image
                nir_win_5x5 = nir_8bit_full[py_win - 2 : py_win + 3, px_win - 2 : px_win + 3]
                nir_win_15x15 = nir_8bit_full[py_win - 7 : py_win + 8, px_win - 7 : px_win + 8]
                
                glcm_count += 1
                
                # Compute 5x5 texture
                if np.all(nir_win_5x5 == nir_win_5x5[0, 0]):
                    homo_5x5 = 1.0
                    asm_5x5 = 1.0
                    entropy_5x5 = 0.0
                else:
                    homo_5x5, entropy_5x5, asm_5x5 = compute_local_glcm_features(nir_win_5x5, compute_asm=True)
                    
                # Compute 15x15 texture
                if np.all(nir_win_15x15 == nir_win_15x15[0, 0]):
                    homo_15x15 = 1.0
                    entropy_15x15 = 0.0
                else:
                    homo_15x15, entropy_15x15, _ = compute_local_glcm_features(nir_win_15x15, compute_asm=False)
                    
                record = {
                    "image": date_seq, "Pixel_ID": pixel_id, "Point_ID": pt_id, "Aleket_cnt": aleket_val,
                    "lat": lat_val, "long": lon_val, "date": date_str, "Days_Before_Sample": days_before,
                    "ndvi": mean_ndvi, "ndvi_std": std_ndvi, "gndvi": mean_gndvi, "green_red_ratio": mean_gr_ratio,
                    "ndre": mean_ndre, "green": mean_green,
                    "entropy_5x5": entropy_5x5, "entropy_15x15": entropy_15x15,
                    "homogeneity_5x5": homo_5x5, "homogeneity_15x15": homo_15x15,
                    "asm_5x5": asm_5x5
                }
                records.append(record)
            print(f"   Date loop {date_seq} completed in {time.time() - t_date_start:.3f}s (pixels loop: {time.time() - t_pixels_start:.3f}s, GLCMs computed: {glcm_count}, skipped: {skipped_count})")
            
    df_out = pd.DataFrame(records)
    df_out.to_csv(out_csv_path, index=False)
    print(f"Total time taken: {time.time() - t0:.2f}s")

if __name__ == "__main__":
    debug_process_field("Boundary_Fields_Baseline_2011 — Eden_gimel.csv")
