import sys

sys.stdout.reconfigure(encoding='utf-8')

# Target fields
historical_all = [
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
    "Boundary_Fields_Baseline_2011 — EHI_ablek_south",
    "Boundary_Fields_Baseline_2011 — Eden_gimel",
    "Boundary_Fields_Baseline_2011 — HavatGadash_30",
    "Boundary_Fields_Baseline_2011 — Hulata_krad_3_4",
    "Boundary_Fields_Baseline_2011 — Reem_bialik_west",
    "Boundary_Fields_Baseline_2011 — Reem_damon_5",
    "Boundary_Fields_Baseline_2011 — Yaen_kavnoa",
    "Boundary_Fields_Baseline_2011 — Yagur_buki",
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

historical_polygons = [
    "Boundary_Fields_Addition_2010-12 — EHI_tet_2012",
    "Boundary_Fields_Addition_2010-12 — Eden_d_2012",
    "Boundary_Fields_Addition_2010-12 — Eden_hei_2012",
    "Boundary_Fields_Addition_2010-12 — Geva_13_2012",
    "Boundary_Fields_Addition_2010-12 — Kfar_blum_b_2011",
    "Boundary_Fields_Addition_2010-12 — Kfar_horash_2011",
    "Boundary_Fields_Addition_2010-12 — Maale_gilboa_makruz_2011",
    "Boundary_Fields_Addition_2010-12 — Mesilot_um_savisa_2011",
    "Boundary_Fields_Addition_2010-12 — Yaen_31_2012"
]

historical_missing = [f for f in historical_all if f not in historical_polygons]

# 2025 target fields
y2025_all = [
    "Broomrape_Sampling_Gonen_2025-06-30",
    "Monitor_GDD714_Broomrape_2025-06-05",
    "Monitor_GDD562_Broomrape_2025-05-18",
    "Monitor_GDD562_Broomrape_2025-05-25",
    "gonen_maagar_220725",
    "Havat_mataim_7.7.2025",
    "Kfar_sald_shaked_east_240725",
    "Shamir_har_100725",
    "hazorea_100825",
    "manara_160725",
    "rimonim_100725",
    "Sasa_7_3.8.25"
]

y2025_polygons = [
    "Monitor_GDD714_Broomrape_2025-06-05" # Edigan field
]

y2025_missing = [f for f in y2025_all if f not in y2025_polygons]

print("=== HISTORICAL FIELDS WITHOUT POLYGONS ===")
for i, f in enumerate(sorted(historical_missing), 1):
    print(f"{i}. {f}")

print("\n=== 2025 FIELDS WITHOUT POLYGONS ===")
for i, f in enumerate(sorted(y2025_missing), 1):
    print(f"{i}. {f}")
