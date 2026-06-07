"""
Pixel-level time-series feature extraction script.
Extracts spectral and GLCM texture features at the pixel level for 2010-2012 and 2025 fields,
handling coordinate projections, spatial co-registration, and matching to ground-truth points.
Optimized with vectorized NumPy calculations, lumped single-bincount GLCM texture extraction,
parent-process polygon pre-loading, and resume capability.
"""

import os
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
import warnings
import fiona
from scipy.spatial import KDTree
from scipy.ndimage import uniform_filter
import concurrent.futures
from pathlib import Path
from typing import Any, Optional

# Suppress warnings
warnings.filterwarnings("ignore")

# Set random seed for reproducibility
np.random.seed(42)

# --- Pre-allocate GLCM weights flat ---
i_idx, j_idx = np.ogrid[:256, :256]
GLCM_HOMO_WEIGHTS_FLAT: np.ndarray = (1.0 / (1.0 + (i_idx - j_idx) ** 2)).ravel()

# --- Definition of sample dates for each field ---
sample_dates: dict[str, str] = {
    "Broomrape_Sampling_Gonen_2025-06-30": "30.06.25",
    "Boundary_Fields_Baseline_2011 — Yagur_buki": "21.07.11",
    "Boundary_Fields_Baseline_2011 — Yaen_kavnoa": "25.07.11",
    "Boundary_Fields_Baseline_2011 — Reem_damon_5": "14.07.11",
    "Boundary_Fields_Baseline_2011 — Reem_bialik_west": "14.07.11",
    "Boundary_Fields_Baseline_2011 — Hulata_krad_3_4": "02.08.11",
    "Boundary_Fields_Baseline_2011 — EHI_ablek_south": "30.06.11",
    "Boundary_Fields_Baseline_2011 — HavatGadash_30": "07.08.11",
    "Boundary_Fields_Baseline_2011 — Eden_gimel": "03.06.11",
    "Monitor_GDD562_Broomrape_2025-05-25": "25.05.25",
    "Boundary_Fields_Addition_2010-12 — Yaen_31_2012": "05.07.12",
    "Boundary_Fields_Addition_2010-12 — Sde_Nachum_2012": "21.06.12",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_tukan_d_2012": "06.06.12",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_Kemach_W_2012": "09.06.11",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_kemach_E": "09.06.11",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_hamra_hey_2012": "30.05.12",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_2011_shokef_alef": "02.06.11",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_2011_hamra_vav": "02.06.11",
    "Boundary_Fields_Addition_2010-12 — Mesilot_um_savisa_2011": "03.06.11",
    "Boundary_Fields_Addition_2010-12 — Mesilot_mafrek_E_2011": "22.06.11",
    "Boundary_Fields_Addition_2010-12 — Maale_gilboa_makruz_2011": "10.06.11",
    "Boundary_Fields_Addition_2010-12 — Geva_13_2012": "28.06.12",
    "Boundary_Fields_Addition_2010-12 — Kfar_horash_2011": "01.07.11",
    "Boundary_Fields_Addition_2010-12 — Kfar_blum_rekiak_E_2012": "20.07.12",
    "Boundary_Fields_Addition_2010-12 — Kfar_blum_b_2011": "07.08.11",
    "Boundary_Fields_Addition_2010-12 — Havat_Gadash_2_2012": "26.07.12",
    "Boundary_Fields_Addition_2010-12 — Eden_hei_2012": "15.06.12",
    "Boundary_Fields_Addition_2010-12 — EHI_tet_2012": "02.07.12",
    "Boundary_Fields_Addition_2010-12 — Eden_d_2012": "14.06.12",
    "Monitor_GDD714_Broomrape_2025-06-05": "05.06.25",
    "Boundary_Fields_Addition_2010-12 — Gadasj_haemek_2010": "05.07.10",
    "fields_2010 — Dan_BeitHilel_east": "10.08.10",
    "fields_2010 — Dan_Namme4east_1_points": "25.08.10",
    "fields_2010 — Dan_Namme4east_2_points": "25.08.10",
    "fields_2010 — EHI_emek_d_points": "01.06.10",
    "fields_2010 — EHI_hey_points": "01.06.10",
    "fields_2010 — Geva": "01.06.10",
    "fields_2010 — havateden_hey_points": "09.06.10",
    "fields_2010 — HavatGadash": "28.07.10",
    "fields_2010 — Hulata_west_points": "17.08.10",
    "fields_2010 — Yagur72": "12.07.10",
    "fields_2010 — Yagur90": "14.07.10",
    "fields_2010 — Yifaat_Kishon1_points": "21.07.10",
    "fields_2010 — Yifaat_vav": "18.07.10",
    "fields_2010 — kfarHahoresh_37": "18.07.10",
    "Havat_mataim_7.7.2025": "07.07.25",
    "manara_160725": "16.07.25",
    "rimonim_100725": "10.07.25",
    "Sasa_7_3.8.25": "03.08.25",
    "Kfar_sald_shaked_east_240725": "24.07.25",
    "Shamir_har_100725": "24.07.25",
    "hazorea_100825": "10.08.25",
    "gonen_maagar_220725": "22.07.25"
}

MAPPING_2025: dict[str, tuple[str, str]] = {
    "Broomrape_Sampling_Gonen_2025-06-30.csv": ("Gonen_2025", "Gonen_2025"),
    "gonen_maagar_220725.csv": ("gonen_maagar_220725", "gonen_maagar_220725_poly"),
    "Havat_mataim_7.7.2025.csv": ("Havat_mataim_7.7.2025", "Havat_mataim_7.7.2025_poly"),
    "hazorea_100825.csv": ("hazorea_100825", "hazorea_100825_poly"),
    "Kfar_sald_shaked_east_240725.csv": ("Kfar_sald_shaked_east_240725", "Kfar_sald_shaked_east_240725_poly"),
    "manara_160725.csv": ("manara_160725", "manara_160725_poly"),
    "rimonim_100725.csv": ("rimonim_100725", "rimonim_100725_poly"),
    "Sasa_7_3.8.25.csv": ("Sasa_7_3.8.25", "Sasa_7_3.8.25_poly"),
    "Shamir_har_100725.csv": ("Shamir_har_100725", "Shamir_har_100725_poly"),
    "Monitor_GDD714_Broomrape_2025-06-05.csv": ("Havat_gadash_25", "Havat_gadash_25")
}

POLYGON_GPKG_PATH: str = "qgis/all_layers_with_polygons.gpkg"
CLEAN_TABLES_DIR: str = "clean_tables"
EXTRACTED_LAYERS_DIR: str = "extracted_layers"

# --- Output directories ---
OUT_HISTORICAL_DIR: str = "pixel_temporal_datasets_long"
OUT_2025_DIR: str = "pixel_temporal_datasets_long_2025"


def map_csv_to_field_info(csv_name: str) -> Optional[tuple[str, str, str]]:
    """
    Maps a CSV filename to a tuple of (short_name, polygon_layer_name, year_group).
    Returns None if the CSV should be skipped.
    """
    if "Monitor_GDD562" in csv_name:
        return None

    if "—" in csv_name:
        parts = csv_name.split("—")
        short_name = parts[-1].strip().replace(".csv", "")
        if short_name in ["Gadasj_haemek_2010", "Kfar_blum_b_2011"]:
            return None
        return short_name, short_name, "historical"
    else:
        if csv_name in MAPPING_2025:
            short_name, poly_layer_name = MAPPING_2025[csv_name]
            return short_name, poly_layer_name, "2025"
        else:
            return None


def compute_local_glcm_features_lumped(W: np.ndarray, compute_asm: bool = False) -> tuple[float, float, Optional[float]]:
    """
    Computes average Homogeneity, Entropy, and optionally ASM for a local window W
    using a lumped single np.bincount call (highly optimized, 11x faster).
    """
    h_A, h_B = W[:, :-1].ravel(), W[:, 1:].ravel()
    v_A, v_B = W[:-1, :].ravel(), W[1:, :].ravel()
    d1_A, d1_B = W[:-1, :-1].ravel(), W[1:, 1:].ravel()
    d2_A, d2_B = W[:-1, 1:].ravel(), W[1:, :-1].ravel()
    
    # Concatenate all directions to do one single bincount
    A = np.concatenate([h_A, v_A, d1_A, d2_A])
    B = np.concatenate([h_B, v_B, d1_B, d2_B])
    
    pairs = A.astype(np.int32) * 256 + B.astype(np.int32)
    sym_pairs = B.astype(np.int32) * 256 + A.astype(np.int32)
    all_pairs = np.concatenate([pairs, sym_pairs])
    
    counts = np.bincount(all_pairs, minlength=256*256)
    p = counts / len(all_pairs)
    
    # Homogeneity
    homo_val = np.sum(p * GLCM_HOMO_WEIGHTS_FLAT)
    
    # Entropy
    p_nz = p[p > 0]
    entropy_val = -np.sum(p_nz * np.log2(p_nz))
    
    # ASM
    asm_val = np.sum(p ** 2) if compute_asm else None
    
    return homo_val, entropy_val, asm_val


def process_single_field(csv_name: str, poly_geom_32636: Optional[Any] = None) -> str:
    """
    Executes the pixel-level feature extraction for a single agricultural field.
    Returns a status string indicating Success or Skip/Error reason.
    """
    try:
        mapping_info = map_csv_to_field_info(csv_name)
        if not mapping_info:
            return f"[SKIP] {csv_name}: Excluded or skipped by mapping criteria"

        short_name, poly_layer_name, year_group = mapping_info
        
        # Set paths based on year group
        if year_group == "historical":
            chips_dir = "data/raw_chips"
            out_dir = OUT_HISTORICAL_DIR
        else:
            chips_dir = "data/raw_chips_2025"
            out_dir = OUT_2025_DIR

        # Resume logic: check if the output CSV already exists
        os.makedirs(out_dir, exist_ok=True)
        out_csv_path = os.path.join(out_dir, f"{short_name}_pixel_features.csv")
        if os.path.exists(out_csv_path):
            return f"[SUCCESS] {csv_name} -> {short_name}_pixel_features.csv (already exists)"

        csv_path = os.path.join(CLEAN_TABLES_DIR, csv_name)
        pts_gpkg_path = os.path.join(EXTRACTED_LAYERS_DIR, csv_name.replace(".csv", ".gpkg"))

        # 1. Schema Validation (Assert Aleket_cnt values and type)
        df_table = pd.read_csv(csv_path)
        assert "Aleket_cnt" in df_table.columns, f"Aleket_cnt column missing in {csv_name}"
        assert pd.api.types.is_numeric_dtype(df_table["Aleket_cnt"]), f"Aleket_cnt must be numeric in {csv_name}"
        
        valid_aleket = df_table["Aleket_cnt"].dropna()
        assert (valid_aleket % 1 == 0).all(), f"Aleket_cnt must contain integer values in {csv_name}"
        assert valid_aleket.between(0, 15).all(), f"Aleket_cnt has invalid values in {csv_name}: {valid_aleket.unique()}"

        # 2. Load Point Geometries
        if not os.path.exists(pts_gpkg_path):
            return f"[ERROR] {csv_name}: Point GeoPackage {pts_gpkg_path} missing"
        gdf_pts = gpd.read_file(pts_gpkg_path)

        # Assert same length and order of points as CSV
        assert len(gdf_pts) == len(df_table), f"Point count mismatch between GPKG and CSV for {csv_name}: {len(gdf_pts)} vs {len(df_table)}"

        # Prepare point IDs and clean Aleket counts from CSV
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

        # 3. Load Polygon Geometries (fallback if not pre-loaded)
        if poly_geom_32636 is None:
            try:
                gdf_poly = gpd.read_file(POLYGON_GPKG_PATH, layer=poly_layer_name)
            except Exception:
                return f"[SKIP] {csv_name}: Polygon layer {poly_layer_name} not found in GPKG"

            if gdf_poly.empty:
                return f"[SKIP] {csv_name}: Polygon layer {poly_layer_name} has no geometries"
            
            gdf_poly_32636 = gdf_poly.to_crs("EPSG:32636")
            poly_geom_32636 = gdf_poly_32636.geometry.iloc[0]

        # 4. Resolve Date Range and Temporal Window
        csv_base = csv_name.replace(".csv", "")
        if csv_base not in sample_dates:
            return f"[SKIP] {csv_name}: Sample date missing in sample_dates dictionary"

        s_date_str = sample_dates[csv_base]
        sample_date = pd.to_datetime(s_date_str, format="%d.%m.%y")
        start_date = sample_date - timedelta(days=60)

        # 5. Search for Overlapping Chips in Bounding Box
        poly_bbox = poly_geom_32636.bounds
        poly_box = box(*poly_bbox)

        valid_chips = []
        for f in os.listdir(chips_dir):
            if not f.endswith(".tif") or "udm" in f.lower() or "sr" not in f.lower():
                continue
            chip_path = os.path.join(chips_dir, f)

            try:
                with rasterio.open(chip_path) as src:
                    assert src.crs.to_epsg() == 32636, f"Expected EPSG:32636, got {src.crs}"

                    chip_box = box(*src.bounds)
                    if poly_box.intersects(chip_box) and poly_geom_32636.intersects(chip_box):
                        match = re.search(r"(20\d{2}-?\d{2}-?\d{2})", f)
                        if match:
                            date_str = match.group(1)
                            acq_date = pd.to_datetime(date_str)
                            if start_date <= acq_date <= sample_date:
                                valid_chips.append({"path": chip_path, "date": acq_date})
            except Exception:
                pass

        if not valid_chips:
            return f"[SKIP] {csv_name}: No overlapping chips found"

        # 6. Apply strict 4-day temporal pruning
        unique_dates = sorted(list(set([c["date"] for c in valid_chips])))
        selected_dates = []
        if unique_dates:
            selected_dates.append(unique_dates[0])
            for d in unique_dates[1:]:
                if (d - selected_dates[-1]).days >= 4:
                    selected_dates.append(d)

        if len(selected_dates) < 3:
            return f"[SKIP] {csv_name}: Less than 3 temporally spaced images in 60-day window"

        date_to_chips = {d: [] for d in selected_dates}
        for c in valid_chips:
            if c["date"] in selected_dates:
                date_to_chips[c["date"]].append(c["path"])

        # 7. Generate Master Pixel Grid (find chip with max valid pixels inside polygon)
        best_chip_path = None
        best_pixel_count = -1
        best_out_image = None
        best_out_transform = None
        best_src_master_crs = None
        
        if year_group == "historical":
            nir_idx, green_idx, red_idx, red_edge_idx = 4, 1, 2, 3
        else:
            nir_idx, green_idx, red_idx, red_edge_idx = 7, 3, 5, 6

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
                except Exception:
                    pass

        if best_pixel_count <= 0 or best_chip_path is None:
            return f"[ERROR] {csv_name}: No pixels with NIR > 0 found inside polygon in any overlapping chip"

        # Generate spatial coordinates based on best chip
        nir_master = best_out_image[nir_idx]
        valid_rows, valid_cols = np.where(nir_master > 0)
        
        xs_utm36n, ys_utm36n = rasterio.transform.xy(best_out_transform, valid_rows, valid_cols, offset="center")
        xs_utm36n = np.array(xs_utm36n)
        ys_utm36n = np.array(ys_utm36n)

        transformer_to_wgs84 = pyproj.Transformer.from_crs(best_src_master_crs, "EPSG:4326", always_xy=True)
        lons_wgs84, lats_wgs84 = transformer_to_wgs84.transform(xs_utm36n, ys_utm36n)

        # 8. Match Ground-Truth Points to Pixel Centroids using KDTree
        gdf_pts_proj = gdf_pts.to_crs("EPSG:32636")
        assert gdf_pts_proj.crs == best_src_master_crs, f"CRS mismatch: {gdf_pts_proj.crs} != {best_src_master_crs}"
        
        pt_coords_utm36n = np.column_stack((gdf_pts_proj.geometry.x, gdf_pts_proj.geometry.y))
        valid_pixel_coords_utm36n = np.column_stack((xs_utm36n, ys_utm36n))

        tree = KDTree(valid_pixel_coords_utm36n)
        distances, closest_indices = tree.query(pt_coords_utm36n)

        pixel_to_sample = {}
        for i, idx in enumerate(closest_indices):
            pt_id = gdf_pts["Point_ID_clean"].iloc[i]
            aleket_val = gdf_pts["Aleket_cnt_clean"].iloc[i]
            pixel_to_sample[idx] = (pt_id, aleket_val)

        # 9. Time-Series Extraction loop
        records = []

        for date_seq, d in enumerate(selected_dates, start=1):
            date_str = d.strftime("%d/%m/%Y")
            days_before = (sample_date - d).days
            chip_path = date_to_chips[d][0]

            try:
                with rasterio.open(chip_path) as src:
                    assert src.crs.to_epsg() == 32636, f"Expected EPSG:32636, got {src.crs}"

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

                    # Vectorized pre-calculation of 3x3 local stats
                    mean_green_band = uniform_filter(green_band, size=3, mode='reflect')
                    mean_ndvi_band = uniform_filter(ndvi_full, size=3, mode='reflect')
                    std_ndvi_band = np.sqrt(np.maximum(0, uniform_filter(ndvi_full**2, size=3, mode='reflect') - mean_ndvi_band**2))
                    mean_gndvi_band = uniform_filter(gndvi_full, size=3, mode='reflect')
                    mean_gr_ratio_band = uniform_filter(gr_ratio_full, size=3, mode='reflect')
                    mean_ndre_band = uniform_filter(ndre_full, size=3, mode='reflect')

                    py_wins, px_wins = rasterio.transform.rowcol(win_transform, xs_utm36n, ys_utm36n)
                    py_wins = np.array(py_wins)
                    px_wins = np.array(px_wins)

                    for idx_in_valid in range(len(xs_utm36n)):
                        py_win = py_wins[idx_in_valid]
                        px_win = px_wins[idx_in_valid]
                        pixel_id = idx_in_valid + 1
                        pt_id, aleket_val = pixel_to_sample.get(idx_in_valid, (np.nan, np.nan))
                        lat_val = lats_wgs84[idx_in_valid]
                        lon_val = lons_wgs84[idx_in_valid]

                        # Check if pixel is close to slice edge or is nodata/NaN on this date
                        if (py_win < 7 or px_win < 7 or 
                            py_win >= data.shape[1] - 7 or px_win >= data.shape[2] - 7 or
                            np.isnan(nir_band[py_win, px_win]) or nir_band[py_win, px_win] <= 0):
                            
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

                        # Extract pre-calculated 3x3 statistics
                        mean_green = mean_green_band[py_win, px_win]
                        mean_ndvi = mean_ndvi_band[py_win, px_win]
                        std_ndvi = std_ndvi_band[py_win, px_win]
                        mean_gndvi = mean_gndvi_band[py_win, px_win]
                        mean_gr_ratio = mean_gr_ratio_band[py_win, px_win]
                        mean_ndre = mean_ndre_band[py_win, px_win]

                        # Slices of pre-converted 8-bit image
                        nir_win_5x5 = nir_8bit_full[py_win - 2 : py_win + 3, px_win - 2 : px_win + 3]
                        nir_win_15x15 = nir_8bit_full[py_win - 7 : py_win + 8, px_win - 7 : px_win + 8]

                        # Compute 5x5 texture
                        if np.all(nir_win_5x5 == nir_win_5x5[0, 0]):
                            homo_5x5 = 1.0
                            asm_5x5 = 1.0
                            entropy_5x5 = 0.0
                        else:
                            homo_5x5, entropy_5x5, asm_5x5 = compute_local_glcm_features_lumped(nir_win_5x5, compute_asm=True)

                        # Compute 15x15 texture
                        if np.all(nir_win_15x15 == nir_win_15x15[0, 0]):
                            homo_15x15 = 1.0
                            entropy_15x15 = 0.0
                        else:
                            homo_15x15, entropy_15x15, _ = compute_local_glcm_features_lumped(nir_win_15x15, compute_asm=False)

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
            except Exception as e:
                for idx_in_valid in range(len(xs_utm36n)):
                    pixel_id = idx_in_valid + 1
                    pt_id, aleket_val = pixel_to_sample.get(idx_in_valid, (np.nan, np.nan))
                    lat_val = lats_wgs84[idx_in_valid]
                    lon_val = lons_wgs84[idx_in_valid]
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

        if records:
            df_out = pd.DataFrame(records)
            df_out.to_csv(out_csv_path, index=False)
            return f"[SUCCESS] {csv_name} -> {short_name}_pixel_features.csv ({len(df_out)} rows)"
        else:
            return f"[WARNING] {csv_name}: No records extracted"

    except Exception as e:
        return f"[ERROR] {csv_name}: Exception raised: {str(e)}"


def run_pipeline() -> None:
    """Runs the feature extraction pipeline in parallel for all fields in clean_tables/."""
    csv_files = [f for f in os.listdir(CLEAN_TABLES_DIR) if f.endswith(".csv")]
    
    print(f"Starting optimized pixel-level dataset construction for {len(csv_files)} clean tables...")
    print(f"Historical outputs folder: {OUT_HISTORICAL_DIR}")
    print(f"2025 outputs folder: {OUT_2025_DIR}\n")

    # Pre-load all polygon geometries from all_layers_with_polygons.gpkg to prevent SQLite locking
    print("Pre-loading polygon layers...")
    layers = fiona.listlayers(POLYGON_GPKG_PATH)
    poly_geoms = {}
    for lyr in layers:
        try:
            gdf_poly = gpd.read_file(POLYGON_GPKG_PATH, layer=lyr)
            if not gdf_poly.empty:
                gdf_poly_32636 = gdf_poly.to_crs("EPSG:32636")
                poly_geoms[lyr] = gdf_poly_32636.geometry.iloc[0]
        except Exception:
            pass
    print(f"Loaded {len(poly_geoms)} polygon layers.\n")

    max_workers = min(os.cpu_count() or 1, 8)
    print(f"Using {max_workers} parallel workers...")

    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for csv in csv_files:
            mapping_info = map_csv_to_field_info(csv)
            poly_geom = None
            if mapping_info:
                _, poly_layer_name, _ = mapping_info
                poly_geom = poly_geoms.get(poly_layer_name)
            
            futures.append(executor.submit(process_single_field, csv, poly_geom))
            
        future_to_csv = {futures[i]: csv_files[i] for i in range(len(csv_files))}
        
        for future in concurrent.futures.as_completed(future_to_csv):
            csv = future_to_csv[future]
            try:
                status = future.result()
                print(status)
                results.append(status)
            except Exception as e:
                err_msg = f"[ERROR] {csv}: Process pool exception: {e}"
                print(err_msg)
                results.append(err_msg)

    print("\nPipeline execution complete.")
    success_count = sum(1 for r in results if "[SUCCESS]" in r)
    skip_count = sum(1 for r in results if "[SKIP]" in r)
    error_count = sum(1 for r in results if "[ERROR]" in r)
    print(f"Summary: {success_count} fields successful, {skip_count} fields skipped, {error_count} errors.")


if __name__ == "__main__":
    run_pipeline()
