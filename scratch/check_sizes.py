import os
import re
import numpy as np
import geopandas as gpd
import pandas as pd
import rasterio
import rasterio.mask
from shapely.geometry import box
from datetime import datetime, timedelta

POLYGON_GPKG_PATH = "qgis/all_layers_with_polygons.gpkg"
CLEAN_TABLES_DIR = "clean_tables"
EXTRACTED_LAYERS_DIR = "extracted_layers"

# Definitions from build_pixel_datasets.py
sample_dates = {
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

MAPPING_2025 = {
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

def map_csv_to_field_info(csv_name: str):
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

def main():
    csv_files = [f for f in os.listdir(CLEAN_TABLES_DIR) if f.endswith(".csv")]
    results = []
    
    for csv_name in csv_files:
        mapping_info = map_csv_to_field_info(csv_name)
        if not mapping_info:
            continue
        
        short_name, poly_layer_name, year_group = mapping_info
        
        # Determine raw chips directory
        chips_dir = "data/raw_chips" if year_group == "historical" else "data/raw_chips_2025"
        
        # Load Polygon Geometries
        try:
            gdf_poly = gpd.read_file(POLYGON_GPKG_PATH, layer=poly_layer_name)
        except Exception:
            continue
            
        if gdf_poly.empty:
            continue
            
        csv_base = csv_name.replace(".csv", "")
        if csv_base not in sample_dates:
            continue
            
        s_date_str = sample_dates[csv_base]
        sample_date = pd.to_datetime(s_date_str, format="%d.%m.%y")
        start_date = sample_date - timedelta(days=60)
        
        gdf_poly_32636 = gdf_poly.to_crs("EPSG:32636")
        poly_geom_32636 = gdf_poly_32636.geometry.iloc[0]
        poly_bbox = poly_geom_32636.bounds
        poly_box = box(*poly_bbox)
        
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
                            date_str = match.group(1)
                            acq_date = pd.to_datetime(date_str)
                            if start_date <= acq_date <= sample_date:
                                valid_chips.append({"path": chip_path, "date": acq_date})
            except Exception:
                pass
                
        if not valid_chips:
            continue
            
        unique_dates = sorted(list(set([c["date"] for c in valid_chips])))
        selected_dates = []
        if unique_dates:
            selected_dates.append(unique_dates[0])
            for d in unique_dates[1:]:
                if (d - selected_dates[-1]).days >= 4:
                    selected_dates.append(d)
                    
        if len(selected_dates) < 3:
            continue
            
        master_chip_path = valid_chips[0]["path"]
        with rasterio.open(master_chip_path) as src_master:
            out_image, out_transform = rasterio.mask.mask(src_master, [poly_geom_32636], crop=True, nodata=0)
            if year_group == "historical":
                nir_idx = 4
            else:
                nir_idx = 7
            nir_master = out_image[nir_idx]
            valid_rows, valid_cols = np.where(nir_master > 0)
            pixel_count = len(valid_rows)
            
        results.append({
            "csv_name": csv_name,
            "short_name": short_name,
            "pixel_count": pixel_count,
            "dates_count": len(selected_dates)
        })
        
    df = pd.DataFrame(results)
    df = df.sort_values(by="pixel_count", ascending=False)
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
