import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

# The dictionary of sample dates from the project pipeline
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

# Filter to 2010-2012
fields_10_12 = []
for name, d_str in sample_dates.items():
    year = int(d_str.split('.')[-1])
    if year in [10, 11, 12] or f"20{year}" in ['2010', '2011', '2012']:
        fields_10_12.append(name)

print(f"Total 2010-2012 fields in pipeline: {len(fields_10_12)}")
for f in sorted(fields_10_12):
    print("  ", f)
