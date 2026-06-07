# --- Constants & Paths ---
RAW_CHIPS_DIR = "data/raw_chips" 
CLEAN_TABLES_DIR = "clean_tables"
EXTRACTED_LAYERS_DIR = "extracted_layers"
OUTPUT_DIR = "field_temporal_datasets_long" 

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_valid_chips_for_field(field_gdf, chips_dir, sample_date):
    """
    Scans chips to guarantee they intersect the field spatially AND 
    fall strictly within the 60 days leading up to the sample date.
    """
    valid_chips = []
    minx, miny, maxx, maxy = field_gdf.total_bounds
    
    centroid = field_gdf.geometry.unary_union.centroid
    cx, cy = centroid.x, centroid.y
    
    # Define the strict 60-day temporal window
    start_date = sample_date - timedelta(days=60)
    
    print(f"\n  [DIAGNOSTIC] Testing files for centroid (Lon: {cx:.4f}, Lat: {cy:.4f}).")
    print(f"  [DIAGNOSTIC] Valid temporal window: {start_date.strftime('%Y-%m-%d')} to {sample_date.strftime('%Y-%m-%d')}")
    files_checked = 0
    
    if not os.path.exists(chips_dir):
        print(f"  [ERROR] Directory does not exist: {chips_dir}")
        return valid_chips

    for f in os.listdir(chips_dir):
        if not f.endswith('.tif') or 'udm' in f.lower() or 'sr' not in f.lower():
            continue

        files_checked += 1
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
                        
                        val = src.read(1, window=Window(px, py, 1, 1)) 
                        
                        if val.size > 0 and val[0, 0] > 0:
                            # Your upgraded flexible date regex
                            match = re.search(r'(20\d{2}-?\d{2}-?\d{2})', f)
                            if match:
                                date_str = match.group(1)
                                acq_date = pd.to_datetime(date_str)
                                
                                # --- THE NEW TEMPORAL FILTER ---
                                if start_date <= acq_date <= sample_date:
                                    valid_chips.append({'path': chip_path, 'date': acq_date})
                                else:
                                    pass # Silently drop images outside the 60-day window to avoid spam
                            else:
                                print(f"    -> [FAIL Regex] Intersects, but can't find a valid date in filename: {f}")
                        else:
                            print(f"    -> [FAIL Pixel] Intersects, but pixel is 0 (Planet Padding): {f}")
                    except Exception as inner_e:
                        print(f"    -> [FAIL Index] Intersects, but centroid error on {f}: {inner_e}")
        except Exception as outer_e:
            print(f"    -> [FAIL Read] Could not open {f}: {outer_e}")
            
    print(f"  [DIAGNOSTIC] Checked {files_checked} files. Found {len(valid_chips)} valid chips within the 60-day window.")
    return valid_chips
    
def extract_features_at_point(chip_path: str, lon: float, lat: float) -> tuple[dict[str, float] | None, str]:
    """
    Extracts high-resolution satellite features at a specific geographic point.
    Spectral bands and indices are extracted from the EXACT 1x1 pixel.
    GLCM texture features are computed over a tight 3x3 surrounding neighborhood.
    """
    try:
        with rasterio.open(chip_path) as src:
            transformer = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            x_proj, y_proj = transformer.transform(lon, lat)
            
            # Spatial boundary check
            if not ((src.bounds.left - 100) <= x_proj <= (src.bounds.right + 100) and 
                    (src.bounds.bottom - 100) <= y_proj <= (src.bounds.top + 100)):
                return None, "WRONG_FIELD"
                
            py, px = src.index(x_proj, y_proj)
            
            # Ensure safe margins for the 3x3 texture window
            if py < 1 or px < 1 or py >= src.height - 1 or px >= src.width - 1:
                return None, "EDGE_PROXIMITY"
            
            # 1. SPECTRAL FEATURES: Extract from the exact 1x1 single pixel containing the point
            spectral_window = Window(px, py, 1, 1)
            spectral_data = src.read(window=spectral_window).astype(float)
            
            if spectral_data.shape[0] < 8:
                return None, "SENSOR_MISMATCH"
                
            # Extract scalar reflectance values from the single pixel
            green = spectral_data[3][0, 0]
            red = spectral_data[5][0, 0]
            red_edge = spectral_data[6][0, 0]
            nir = spectral_data[7][0, 0]
            
            if nir == 0:
                return None, "NODATA_COLLAR"
                
            # Perform direct scalar spectral index calculations
            mean_green = green
            
            denom_ndvi = nir + red
            mean_ndvi = (nir - red) / denom_ndvi if denom_ndvi != 0 else np.nan

            denom_gndvi = nir + green
            mean_gndvi = (nir - green) / denom_gndvi if denom_gndvi != 0 else np.nan

            mean_gr_ratio = green / red if red != 0 else np.nan

            denom_ndre = nir + red_edge
            mean_ndre = (nir - red_edge) / denom_ndre if denom_ndre != 0 else np.nan

            # 2. TEXTURE FEATURES: Read a tight 3x3 window strictly to enable GLCM math
            texture_window = Window(px - 1, py - 1, 3, 3)
            texture_data = src.read(window=texture_window).astype(float)
            nir_texture = texture_data[7]
            
            # Gray-level co-occurrence matrix math
            nir_8bit = np.clip(nir_texture / 10000.0 * 255, 0, 255).astype(np.uint8)
            angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]
            glcm = graycomatrix(nir_8bit, distances=[1], angles=angles, symmetric=True, normed=True)
            
            homo = np.mean(graycoprops(glcm, 'homogeneity'))
            asm = np.mean(graycoprops(glcm, 'ASM'))
            
            glcm_avg = np.mean(glcm, axis=3)[:, :, 0]
            entropy = -np.sum(glcm_avg[glcm_avg > 0] * np.log2(glcm_avg[glcm_avg > 0]))

            features = {
                'green': mean_green, 'ndvi': mean_ndvi, 'gndvi': mean_gndvi,
                'green_red_ratio': mean_gr_ratio, 'ndre': mean_ndre,
                'homogeneity': homo, 'entropy': entropy, 'asm': asm
            }
            return features, "SUCCESS"
            
    except Exception as e:
        return None, f"EXCEPTION: {str(e)}"

        
def build_long_format_datasets():
    historical_fields = {k: v for k, v in sample_dates.items() if pd.to_datetime(v, dayfirst=True).year < 2013}
    print(f"Initiating Long Format extraction for {len(historical_fields)} fields...\n")

    for field_name, s_date_str in historical_fields.items():
        field_records = [] 
        sample_date = pd.to_datetime(s_date_str, dayfirst=True)
        
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
        
        # Identify Valid Chips for the RapidEye Field
        valid_chips = get_valid_chips_for_field(gdf_layer, RAW_CHIPS_DIR, sample_date)
        
        if not valid_chips:
            print(f"  -> [WARNING] No valid overlapping images found in directory. Skipping field.")
            continue
            
        unique_dates = sorted(list(set([c['date'] for c in valid_chips])))
        
        # Temporal Pruning 
        selected_dates = []
        if unique_dates:
            selected_dates.append(unique_dates[0])
            for d in unique_dates[1:]:
                if (d - selected_dates[-1]).days >= 4:
                    selected_dates.append(d)
        
        if len(selected_dates) < 2:
            print(f"  -> [WARNING] Not enough temporally spaced images (< 2). Skipping field.")
            continue
            
        date_to_chips = {d: [] for d in selected_dates}
        for c in valid_chips:
            if c['date'] in selected_dates:
                date_to_chips[c['date']].append(c['path'])
        
        # Feature Extraction
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
                    'ndvi': np.nan, 'gndvi': np.nan, 'green_red_ratio': np.nan,
                    'ndre': np.nan, 'entropy': np.nan, 'green': np.nan,
                    'homogeneity': np.nan, 'asm': np.nan
                }
                
                chip_paths = date_to_chips[d]
                success = False
                edge_proximity = False
                nodata_count = 0
                
                for chip_path in chip_paths:
                    features, error_msg = extract_features_at_point(chip_path, lon, lat)
                    
                    if features:
                        record.update(features)
                        success = True
                        break 
                    else:
                        if error_msg == "EDGE_PROXIMITY": edge_proximity = True
                        elif error_msg == "NODATA_COLLAR": nodata_count += 1
                            
                if not success:
                    if edge_proximity:
                        print(f"[FAIL] Pt {pt_id} | {date_str}: Edge Proximity. Cannot extract 3x3 window.")
                    elif nodata_count > 0:
                        print(f"[FAIL] Pt {pt_id} | {date_str}: NoData Zone. Point landed on black margin.")
            
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