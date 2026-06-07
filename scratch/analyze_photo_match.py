import sys

sys.stdout.reconfigure(encoding='utf-8')

# 42 Target fields from our pipeline (2010-2012)
pipeline_fields = [
    # Boundary_Fields_Addition_2010-12
    "Boundary_Fields_Addition_2010-12 — EHI_tet_2012",
    "Boundary_Fields_Addition_2010-12 — Eden_d_2012",
    "Boundary_Fields_Addition_2010-12 — Eden_hei_2012",
    "Boundary_Fields_Addition_2010-12 — Gadasj_haemek_2010",
    "Boundary_Fields_Addition_2010-12 — Geva_13_2012",
    "Boundary_Fields_Addition_2010-12 — Havat_Gadash_2_2012",
    "Boundary_Fields_Addition_2010-12 — Kfar_blum_b_2011",
    "Boundary_Fields_Addition_2010-12 — Kfar_blum_rekiak_E_2012",
    "Boundary_Fields_Addition_2010-12 — Kfar_horash_2011",
    "Boundary_Fields_Addition_2010-12 — Maale_gilboa_makruz_2011",
    "Boundary_Fields_Addition_2010-12 — Mesilot_mafrek_E_2011",
    "Boundary_Fields_Addition_2010-12 — Mesilot_um_savisa_2011",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_2011_hamra_vav",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_2011_shokef_alef",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_Kemach_W_2012",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_hamra_hey_2012",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_kemach_E",
    "Boundary_Fields_Addition_2010-12 — Sde_Eliyahu_tukan_d_2012",
    "Boundary_Fields_Addition_2010-12 — Sde_Nachum_2012",
    "Boundary_Fields_Addition_2010-12 — Yaen_31_2012",
    
    # Boundary_Fields_Baseline_2011
    "Boundary_Fields_Baseline_2011 — EHI_ablek_south",
    "Boundary_Fields_Baseline_2011 — Eden_gimel",
    "Boundary_Fields_Baseline_2011 — HavatGadash_30",
    "Boundary_Fields_Baseline_2011 — Hulata_krad_3_4",
    "Boundary_Fields_Baseline_2011 — Reem_bialik_west",
    "Boundary_Fields_Baseline_2011 — Reem_damon_5",
    "Boundary_Fields_Baseline_2011 — Yaen_kavnoa",
    "Boundary_Fields_Baseline_2011 — Yagur_buki",
    
    # fields_2010
    "fields_2010 — Dan_BeitHilel_east",
    "fields_2010 — Dan_Namme4east_1_points",
    "fields_2010 — Dan_Namme4east_2_points",
    "fields_2010 — EHI_emek_d_points",
    "fields_2010 — EHI_hey_points",
    "fields_2010 — Geva",
    "fields_2010 — HavatGadash",
    "fields_2010 — Hulata_west_points",
    "fields_2010 — Yagur72",
    "fields_2010 — Yagur90",
    "fields_2010 — Yifaat_Kishon1_points",
    "fields_2010 — Yifaat_vav",
    "fields_2010 — havateden_hey_points",
    "fields_2010 — kfarHahoresh_37"
]

# Layers shown in the user's photo
# Format: (Visual Layer Name, Visual Icon Type)
# Icon types: 'Polygon' (colored square), 'Line' (horizontal line), 'Point' (dot)
photo_layers = [
    ("fields_2010 — Dan_BeitHilel_east", "Point"),
    ("fields_2010 — Kfar_Hahoresh_37", "Line"),
    ("fields_2010 — Havat_Gadash", "Line"),
    ("fields_2010 — EHI_hey", "Line"),
    ("fields_2010 — EHI_emek_d", "Line"),
    ("fields_2010 — Eden_hey", "Line"),
    ("fields_2010 — Dan_Namme4east_1", "Line"),
    ("fields_2010-12_addition — Eden_d_2012", "Point"),
    ("fields_2010-12_addition — Gadash_haemek_2010_line", "Line"),
    ("fields_2010-12_addition — Yaen_31_2012_line", "Polygon"),
    ("fields_2010-12_addition — Mesilot_savisa_2011_line", "Polygon"),
    ("fields_2010-12_addition — Kfar_horesh_2011_line", "Polygon"),
    ("fields_2010-12_addition — Kfar_blum_b_2011_line", "Polygon"),
    ("fields_2010-12_addition — Geva_13_2012_line", "Polygon"),
    ("fields_2010-12_addition — Maale_gilboa_makruz_2011_line", "Polygon"),
    ("fields_2010-12_addition — EHI_tet_2012_line", "Polygon"),
    ("fields_2010-12_addition — Eden_hei_2012_line", "Polygon"),
    ("fields_2010-12_addition — Eden_d_2012_line", "Polygon")
]

print("=== ANALYSIS OF FIELD GEOMETRIES IN PHOTO ===")

# Categorize pipeline fields
polygon_fields = []
line_fields = []
point_fields = []
missing_fields = []

def clean_name(n):
    return n.lower().replace(" ", "").replace("_line", "").replace("_points", "").replace("-", "—")

photo_lookup = {}
for p_name, p_type in photo_layers:
    cleaned = clean_name(p_name)
    # Handle specific renaming conventions
    cleaned = cleaned.replace("fields_2010", "")
    cleaned = cleaned.replace("fields_2010—12_addition", "")
    cleaned = cleaned.replace("havat_gadash", "havatgadash")
    cleaned = cleaned.replace("kfar_horesh_2011", "kfar_horash_2011")
    cleaned = cleaned.replace("mesilot_savisa_2011", "mesilot_um_savisa_2011")
    cleaned = cleaned.replace("gadash_haemek_2010", "gadasj_haemek_2010")
    photo_lookup[cleaned] = (p_name, p_type)

for field in pipeline_fields:
    cleaned_field = clean_name(field)
    cleaned_field = cleaned_field.replace("boundary_fields_addition_2010—12—", "")
    cleaned_field = cleaned_field.replace("boundary_fields_baseline_2011—", "")
    cleaned_field = cleaned_field.replace("fields_2010—", "")
    cleaned_field = cleaned_field.replace("havateden_hey", "eden_hey")
    
    match = None
    # Try direct and partial matches
    for pk, (p_name, p_type) in photo_lookup.items():
        if cleaned_field == pk or cleaned_field in pk or pk in cleaned_field:
            match = (p_name, p_type)
            break
            
    if match:
        p_name, p_type = match
        if p_type == 'Polygon':
            polygon_fields.append((field, p_name))
        elif p_type == 'Line':
            line_fields.append((field, p_name))
        elif p_type == 'Point':
            point_fields.append((field, p_name))
    else:
        missing_fields.append(field)

print(f"\n1. target fields with POLYGONS in photo ({len(polygon_fields)}):")
for f, p in polygon_fields:
    print(f"   * '{f}' (matches layer '{p}')")

print(f"\n2. target fields with only LINES in photo ({len(line_fields)}):")
for f, p in line_fields:
    print(f"   * '{f}' (matches layer '{p}')")

print(f"\n3. target fields with only POINTS in photo ({len(point_fields)}):")
for f, p in point_fields:
    print(f"   * '{f}' (matches layer '{p}')")

print(f"\n4. target fields MISSING ENTIRELY from photo ({len(missing_fields)}):")
for f in missing_fields:
    print(f"   * '{f}'")
