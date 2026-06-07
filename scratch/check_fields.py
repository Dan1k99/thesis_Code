import os
import re
import pandas as pd
import geopandas as gpd
import rasterio
from datetime import datetime, timedelta
from shapely.geometry import box

import sys
sys.path.append(os.getcwd())
from build_pixel_datasets import sample_dates, map_csv_to_field_info

csv_files = os.listdir("clean_tables")
valid_fields = []

for csv in csv_files:
    info = map_csv_to_field_info(csv)
    if not info:
        continue
    short_name, poly_layer_name, year_group = info
    csv_base = csv.replace(".csv", "")
    
    if csv_base not in sample_dates:
        continue
        
    s_date_str = sample_dates[csv_base]
    sample_date = pd.to_datetime(s_date_str, format="%d.%m.%y")
    start_date = sample_date - timedelta(days=60)
    
    # Check layer
    try:
        gdf_poly = gpd.read_file("qgis/all_layers_with_polygons.gpkg", layer=poly_layer_name)
    except Exception:
        continue
    if gdf_poly.empty:
        continue
        
    gdf_poly_32636 = gdf_poly.to_crs("EPSG:32636")
    poly_geom_32636 = gdf_poly_32636.geometry.iloc[0]
    poly_box = box(*poly_geom_32636.bounds)
    
    chips_dir = "data/raw_chips" if year_group == "historical" else "data/raw_chips_2025"
    
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
                            valid_chips.append(acq_date)
        except Exception:
            pass
            
    unique_dates = sorted(list(set(valid_chips)))
    selected_dates = []
    if unique_dates:
        selected_dates.append(unique_dates[0])
        for d in unique_dates[1:]:
            if (d - selected_dates[-1]).days >= 4:
                selected_dates.append(d)
                
    if len(selected_dates) >= 3:
        valid_fields.append((csv, len(selected_dates), year_group))
        
print(f"Total fields meeting 3-image threshold: {len(valid_fields)}")
for v in sorted(valid_fields, key=lambda x: (x[2], x[0])):
    print(f"  Field: {v[0]} | Images: {v[1]} | Group: {v[2]}")
