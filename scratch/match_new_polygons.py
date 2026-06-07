import os
import sys
import fiona
import geopandas as gpd

sys.stdout.reconfigure(encoding='utf-8')

gpkg_path = "qgis/all_layers_with_polygons.gpkg"

# Target fields
sample_dates = {
    # 2025
    "Broomrape_Sampling_Gonen_2025-06-30": "30.06.25",
    "Monitor_GDD714_Broomrape_2025-06-05": "05.06.25",
    "Monitor_GDD562_Broomrape_2025-05-18": "18.05.25",
    "Monitor_GDD562_Broomrape_2025-05-25": "25.05.25",
    "gonen_maagar_220725": "22.07.25",
    "Havat_mataim_7.7.2025": "07.07.25",
    "Kfar_sald_shaked_east_240725": "24.07.25",
    "Shamir_har_100725": "10.07.25",
    "hazorea_100825": "10.08.25",
    "manara_160725": "16.07.25",
    "rimonim_100725": "10.07.25",
    "Sasa_7_3.8.25": "03.08.25",
    
    # 2010-2012 Addition
    "Boundary_Fields_Addition_2010-12 — EHI_tet_2012": "15.05.12",
    "Boundary_Fields_Addition_2010-12 — Eden_d_2012": "28.05.12",
    "Boundary_Fields_Addition_2010-12 — Eden_hei_2012": "22.05.12",
    "Boundary_Fields_Addition_2010-12 — Gadasj_haemek_2010": "20.04.10",
    "Boundary_Fields_Addition_2010-12 — Geva_13_2012": "27.05.12",
    "Boundary_Fields_Addition_2010-12 — Havat_Gadash_2_2012": "21.05.12",
    "Boundary_Fields_Addition_2010-12 — Kfar_blum_b_2011": "22.05.11",
    "Boundary_Fields_Addition_2010-12 — Kfar_blum_rekiak_E_2012": "14.05.12",
    "Boundary_Fields_Addition_2010-12 — Kfar_horash_2011": "01.05.11",
    "Boundary_Fields_Addition_2010-12 — Maale_gilboa_makruz_2011": "11.05.11",
    "Boundary_Fields_Addition_2010-12 — Mesilot_mafrek_E_2011": "15.05.11",
    "Boundary_Fields_Addition_2010-12 — Mesilot_um_savisa_2011": "15.05.11",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_2011_hamra_vav": "16.05.11",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_2011_shokef_alef": "16.05.11",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_Kemach_W_2012": "17.05.12",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_hamra_hey_2012": "17.05.12",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_kemach_E": "16.05.11",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_tukan_d_2012": "17.05.12",
    "Boundary_Fields_Addition_2010-12 — Sde_Nachum_2012": "16.05.12",
    "Boundary_Fields_Addition_2010-12 — Yaen_31_2012": "08.05.12",
    
    # 2011 Baseline
    "Boundary_Fields_Baseline_2011 — EHI_ablek_south": "19.05.11",
    "Boundary_Fields_Baseline_2011 — Eden_gimel": "19.05.11",
    "Boundary_Fields_Baseline_2011 — HavatGadash_30": "19.05.11",
    "Boundary_Fields_Baseline_2011 — Hulata_krad_3_4": "19.05.11",
    "Boundary_Fields_Baseline_2011 — Reem_bialik_west": "19.05.11",
    "Boundary_Fields_Baseline_2011 — Reem_damon_5": "19.05.11",
    "Boundary_Fields_Baseline_2011 — Yaen_kavnoa": "19.05.11",
    "Boundary_Fields_Baseline_2011 — Yagur_buki": "21.07.11",
    
    # 2010 Fields
    "fields_2010 — Dan_BeitHilel_east": "20.05.10",
    "fields_2010 — Dan_Namme4east_1_points": "20.05.10",
    "fields_2010 — Dan_Namme4east_2_points": "20.05.10",
    "fields_2010 — EHI_emek_d_points": "20.05.10",
    "fields_2010 — EHI_hey_points": "20.05.10",
    "fields_2010 — Geva": "20.05.10",
    "fields_2010 — HavatGadash": "20.05.10",
    "fields_2010 — Hulata_west_points": "20.05.10",
    "fields_2010 — Yagur72": "20.05.10",
    "fields_2010 — Yagur90": "20.05.10",
    "fields_2010 — Yifaat_Kishon1_points": "20.05.10",
    "fields_2010 — Yifaat_vav": "20.05.10",
    "fields_2010 — havateden_hey_points": "20.05.10",
    "fields_2010 — kfarHahoresh_37": "20.05.10"
}

# Read layers from GPKG
layers = fiona.listlayers(gpkg_path)

# Build a dictionary of active polygons in the GPKG
# Key: cleaned layer name, Value: (layer_name, rows)
active_polys = {}
for l in layers:
    try:
        gdf = gpd.read_file(gpkg_path, layer=l)
        geom_types = gdf.geometry.type.unique() if 'geometry' in gdf.columns else []
        rows = len(gdf)
        is_poly = any(gt in ['Polygon', 'MultiPolygon'] for gt in geom_types)
        if is_poly:
            cleaned = l.lower().replace(" ", "").replace("_", "")
            active_polys[cleaned] = (l, rows)
    except Exception:
        pass

def clean_target(name):
    return name.lower().replace(" ", "").replace("_", "").replace("-", "—")

print("=== CHECKING 2010-2012 FIELDS ===")
hist_matched = 0
hist_empty = []
hist_missing = []

for field in sorted(sample_dates.keys()):
    if "2025" in field or any(x in field for x in ["gonen_maagar", "Havat_mataim", "Kfar_sald", "Shamir_har", "hazorea", "manara", "rimonim", "Sasa"]):
        continue # Skip 2025 fields for now
        
    # Get the name after the "-" as specified by user
    parts = field.split("—")
    if len(parts) > 1:
        target_name = parts[1].strip()
    else:
        target_name = field
        
    # Remove suffix like "_points" or "_2012" etc., to check matching
    cleaned_target = clean_target(target_name).replace("points", "")
    
    # Try to find a match in the active polygons
    match_layer = None
    match_rows = 0
    for pk, (l_name, rows) in active_polys.items():
        # check if target name is a substring or vice versa
        if cleaned_target == pk or cleaned_target in pk or pk in cleaned_target:
            match_layer = l_name
            match_rows = rows
            break
            
    if match_layer:
        if match_rows > 0:
            hist_matched += 1
            print(f"[OK] '{field}' -> matched Polygon layer '{match_layer}' ({match_rows} features)")
        else:
            hist_empty.append((field, match_layer))
            print(f"[EMPTY] '{field}' -> matches Polygon layer '{match_layer}' BUT IT HAS 0 FEATURES!")
    else:
        hist_missing.append(field)
        print(f"[MISSING] '{field}' -> no polygon layer found! (searched for clean name: '{cleaned_target}')")

print(f"\nHistorical Summary: Matched={hist_matched}, Empty={len(hist_empty)}, Missing={len(hist_missing)}")

print("\n=== CHECKING 2025 FIELDS ===")
y25_matched = 0
y25_empty = []
y25_missing = []

for field in sorted(sample_dates.keys()):
    if not ("2025" in field or any(x in field for x in ["gonen_maagar", "Havat_mataim", "Kfar_sald", "Shamir_har", "hazorea", "manara", "rimonim", "Sasa"])):
        continue # Skip historical fields
        
    cleaned_target = clean_target(field)
    
    # Try to find a match in the active polygons
    match_layer = None
    match_rows = 0
    for pk, (l_name, rows) in active_polys.items():
        if cleaned_target == pk or cleaned_target in pk or pk in cleaned_target:
            match_layer = l_name
            match_rows = rows
            break
            
    # Also check short names for 2025 fields, e.g. "gonen" or "hazorea"
    if not match_layer:
        short_names = ["gonen", "havatmataim", "kfarsald", "shamir", "hazorea", "manara", "rimonim", "sasa", "havatgadash", "gdd"]
        for sn in short_names:
            if sn in cleaned_target:
                for pk, (l_name, rows) in active_polys.items():
                    if sn in pk:
                        match_layer = l_name
                        match_rows = rows
                        break
                if match_layer:
                    break
                    
    if match_layer:
        if match_rows > 0:
            y25_matched += 1
            print(f"[OK] '{field}' -> matched Polygon layer '{match_layer}' ({match_rows} features)")
        else:
            y25_empty.append((field, match_layer))
            print(f"[EMPTY] '{field}' -> matches Polygon layer '{match_layer}' BUT IT HAS 0 FEATURES!")
    else:
        y25_missing.append(field)
        print(f"[MISSING] '{field}' -> no polygon layer found!")

print(f"\n2025 Summary: Matched={y25_matched}, Empty={len(y25_empty)}, Missing={len(y25_missing)}")
