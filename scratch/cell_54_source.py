# --- Constants & Paths ---
RAW_CHIPS_DIR = "data/raw_chips_2025" 
CLEAN_TABLES_DIR = "clean_tables"
EXTRACTED_LAYERS_DIR = "extracted_layers"
OUTPUT_DIR = "field_temporal_datasets_long_2025" 

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_valid_chips_for_field(field_gdf, chips_dir):
    valid_chips = []
    minx, miny, maxx, maxy = field_gdf.total_bounds
    
    centroid = field_gdf.geometry.unary_union.centroid
    cx, cy = centroid.x, centroid.y
    
    if not os.path.exists(chips_dir):
        return valid_chips

    for f in os.listdir(chips_dir):
        if not f.endswith('.tif') or 'udm' in f.lower() or 'sr' not in f.lower():
            continue

        chip_path = os.path.join(chips_dir, f)
        
        try:
            with rasterio.open(chip_path) as src:
                transformer = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                t_minx, t_miny = transformer.transform(minx, miny)
                t_maxx, t_maxy = transformer.transform(maxx, maxy)
                
                intersects = not (t_minx > src.bounds.right or t_maxx < src.bounds.left or
                                  t_miny > src.bounds.top or t_maxy < src.bounds.bottom)
                
                if intersects:
                    cx_proj, cy_proj = transformer.transform(cx, cy)
                    try:
                        py, px = src.index(cx_proj, cy_proj)
                        
                        val = src.read(8, window=Window(px, py, 1, 1)) 
                        
                        if val.size > 0 and val[0, 0] > 0:
                            # Using your upgraded flexible regex
                            match = re.search(r'(20\d{2}-?\d{2}-?\d{2})', f)
                            if match:
                                date_str = match.group(1)
                                acq_date = pd.to_datetime(date_str)
                                valid_chips.append({'path': chip_path, 'date': acq_date})
                    except Exception:
                        pass 
        except Exception:
            pass 
            
    return valid_chips

def extract_features_at_point(chip_path, lon, lat, use_1pixel=False):
    """
    Extracts high-resolution satellite features at a specific coordinate.
    If use_1pixel is True, spectral features are extracted strictly from the 1x1 pixel.
    GLCM texture calculations are always computed over a 3x3 surrounding window.
    """
    try:
        with rasterio.open(chip_path) as src:
            transformer = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            x_proj, y_proj = transformer.transform(lon, lat)
            
            if not ((src.bounds.left - 100) <= x_proj <= (src.bounds.right + 100) and 
                    (src.bounds.bottom - 100) <= y_proj <= (src.bounds.top + 100)):
                return None, "WRONG_FIELD"
                
            py, px = src.index(x_proj, y_proj)
            
            # Ensure safe boundary buffers for both windows
            if py < 1 or px < 1 or py >= src.height - 1 or px >= src.width - 1:
                return None, "EDGE_PROXIMITY"
            
            # --- 1. SPECTRAL FEATURE EXTRACTION ---
            if use_1pixel:
                # Extract strictly from the single 1x1 pixel containing the coordinate
                spectral_window = Window(px, py, 1, 1)
                spectral_data = src.read(window=spectral_window).astype(float)
                
                if spectral_data.shape[0] < 8:
                    return None, "SENSOR_MISMATCH"
                
                # Retrieve scalar values directly (no averaging required)
                green = spectral_data[3][0, 0]
                red = spectral_data[5][0, 0]
                red_edge = spectral_data[6][0, 0]
                nir = spectral_data[7][0, 0]
                
                if nir == 0:
                    return None, "NODATA_COLLAR"
                
                mean_green = green
                
                denom_ndvi = nir + red
                mean_ndvi = (nir - red) / denom_ndvi if denom_ndvi != 0 else np.nan

                denom_gndvi = nir + green
                mean_gndvi = (nir - green) / denom_gndvi if denom_gndvi != 0 else np.nan

                mean_gr_ratio = green / red if red != 0 else np.nan

                denom_ndre = nir + red_edge
                mean_ndre = (nir - red_edge) / denom_ndre if denom_ndre != 0 else np.nan
            else:
                # Standard 3x3 pixel window and spatial averages (original method)
                window = Window(px - 1, py - 1, 3, 3)
                data = src.read(window=window).astype(float)
                
                if data.shape[0] < 8:
                    return None, "SENSOR_MISMATCH"
                    
                green, red, red_edge, nir = data[3], data[5], data[6], data[7]
                
                if np.all(nir == 0):
                    return None, "NODATA_COLLAR"

                mean_green = np.nanmean(green)
                
                denom_ndvi = nir + red
                ndvi_arr = np.divide((nir - red), denom_ndvi, out=np.full_like(nir, np.nan), where=denom_ndvi!=0)
                mean_ndvi = np.nanmean(ndvi_arr)
                std_ndvi = np.nanstd(ndvi_arr)  # Calculates standard deviation over the 3x3 window

                denom_gndvi = nir + green
                gndvi_arr = np.divide((nir - green), denom_gndvi, out=np.full_like(nir, np.nan), where=denom_gndvi!=0)
                mean_gndvi = np.nanmean(gndvi_arr)

                gr_ratio_arr = np.divide(green, red, out=np.full_like(green, np.nan), where=red!=0)
                mean_gr_ratio = np.nanmean(gr_ratio_arr)

                denom_ndre = nir + red_edge
                ndre_arr = np.divide((nir - red_edge), denom_ndre, out=np.full_like(nir, np.nan), where=denom_ndre!=0)
                mean_ndre = np.nanmean(ndre_arr)

            # --- 2. TEXTURE FEATURE EXTRACTION (Always 3x3 window) ---
            texture_window = Window(px - 1, py - 1, 3, 3)
            texture_data = src.read(window=texture_window).astype(float)
            nir_texture = texture_data[7]
            
            nir_8bit = np.clip(nir_texture / 10000.0 * 255, 0, 255).astype(np.uint8)
            angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]
            glcm = graycomatrix(nir_8bit, distances=[1], angles=angles, symmetric=True, normed=True)
            
            homo = np.mean(graycoprops(glcm, 'homogeneity'))
            asm = np.mean(graycoprops(glcm, 'ASM'))
            
            glcm_avg = np.mean(glcm, axis=3)[:, :, 0]
            entropy = -np.sum(glcm_avg[glcm_avg > 0] * np.log2(glcm_avg[glcm_avg > 0]))

            features = {
                'green': mean_green, 
                'ndvi': mean_ndvi, 
                'ndvi_std': std_ndvi,  # Added new column here
                'gndvi': mean_gndvi, 
                'green_red_ratio': mean_gr_ratio, 
                'ndre': mean_ndre,
                'homogeneity': homo, 
                'entropy': entropy, 
                'asm': asm
            }
            return features, "SUCCESS"
            
    except Exception as e:
        return None, f"EXCEPTION: {str(e)}"
        
def build_long_format_datasets():
    target_fields = {k: v for k, v in sample_dates.items() if pd.to_datetime(v, dayfirst=True).year == 2025}
    print(f"Initiating Long Format extraction for {len(target_fields)} fields...\n")

    for field_name, s_date_str in target_fields.items():
        field_records = [] 
        sample_date = pd.to_datetime(s_date_str, dayfirst=True)
        
        # Define strict temporal boundary
        start_date = sample_date - timedelta(days=60)
        
        csv_path = os.path.join(CLEAN_TABLES_DIR, f"{field_name}.csv")
        gpkg_path = os.path.join(EXTRACTED_LAYERS_DIR, f"{field_name}.gpkg")

        if not all(os.path.exists(p) for p in [csv_path, gpkg_path]):
            print(f"[SKIP] Missing core files for {field_name}")
            continue

        df_table = pd.read_csv(csv_path)
        gdf_layer = gpd.read_file(gpkg_path).to_crs(epsg=4326)
        id_col = 'id' if 'id' in df_table.columns else df_table.columns[0]
        
        if id_col not in gdf_layer.columns:
            if len(gdf_layer) == len(df_table):
                gdf_layer[id_col] = df_table[id_col].values
            else:
                continue
                
        print(f"--- Processing Field: {field_name} ---")
        
        # Enforce 1-pixel extraction ONLY for GDD714 and GDD562 fields
        use_1pixel = field_name in [
            "Monitor_GDD714_Broomrape_2025-06-05", 
            "Monitor_GDD562_Broomrape_2025-05-25"
        ]
        
        valid_chips = get_valid_chips_for_field(gdf_layer, RAW_CHIPS_DIR)
        
        if not valid_chips:
            print(f"  -> [WARNING] No valid overlapping images found in directory. Skipping field.")
            continue
            
        unique_dates = sorted(list(set([c['date'] for c in valid_chips])))
        
        # --- NEW: STRICT TEMPORAL ENFORCEMENT ---
        # Purge any dates > 60 days before sample, or occurring after sample
        valid_temporal_dates = [d for d in unique_dates if start_date <= d <= sample_date]
        
        if not valid_temporal_dates:
            print(f"  -> [WARNING] No images fall within the 60-day pre-sample window. Skipping field.")
            continue
        
        selected_dates = []
        selected_dates.append(valid_temporal_dates[0])
        for d in valid_temporal_dates[1:]:
            if (d - selected_dates[-1]).days >= 4:
                selected_dates.append(d)
        
        if len(selected_dates) < 2:
            print(f"  -> [WARNING] Not enough temporally spaced images (< 2) in 60-day window. Skipping field.")
            continue
            
        date_to_chips = {d: [] for d in selected_dates}
        for c in valid_chips:
            if c['date'] in selected_dates:
                date_to_chips[c['date']].append(c['path'])
        
        for idx, row in df_table.iterrows():
            pt_id = row[id_col]
            aleket = row['Aleket_cnt']
            
            pt_geom_series = gdf_layer[gdf_layer[id_col] == pt_id].geometry
            if pt_geom_series.empty:
                continue
            lat, lon = pt_geom_series.iloc[0].y, pt_geom_series.iloc[0].x
            
            for i, d in enumerate(selected_dates, start=1):
                date_str = d.strftime('%d/%m/%Y')
                record = {
                    'image': i, 'Point_ID': pt_id, 'Aleket_cnt': aleket,
                    'lat': lat, 'long': lon, 'date': date_str,
                    'Days_Before_Sample': (sample_date - d).days,
                    'ndvi': np.nan, 
                    'ndvi_std': np.nan,  # Added to column order directly after 'ndvi'
                    'gndvi': np.nan, 
                    'green_red_ratio': np.nan,
                    'ndre': np.nan, 
                    'entropy': np.nan, 
                    'green': np.nan,
                    'homogeneity': np.nan, 
                    'asm': np.nan
                }
                
                chip_paths = date_to_chips[d]
                success = False
                edge_proximity = False
                nodata_count = 0
                
                for chip_path in chip_paths:
                    features, error_msg = extract_features_at_point(
                        chip_path, lon, lat, use_1pixel=use_1pixel
                    )    
                    if features:
                        record.update(features)
                        success = True
                        break 
                    else:
                        if error_msg == "EDGE_PROXIMITY": edge_proximity = True
                        elif error_msg == "NODATA_COLLAR": nodata_count += 1
                            
                if not success:
                    if edge_proximity:
                        pass # Suppressed per previous logic
                    elif nodata_count > 0:
                        pass # Suppressed per previous logic
            
                field_records.append(record)

        if field_records:
            final_df = pd.DataFrame(field_records)
            final_df = final_df.sort_values(by=['image', 'Point_ID'])
            out_path = os.path.join(OUTPUT_DIR, f"{field_name}_long_features.csv")
            final_df.to_csv(out_path, index=False)
            print(f"  -> Saved {len(final_df)} observation rows.")
        else:
            print(f"  -> No data generated.")

if __name__ == "__main__":
    build_long_format_datasets()