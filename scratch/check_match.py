import os
import geopandas as gpd
import pandas as pd
import sys

# Set standard output to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Let's get the list of active fields from clean_tables
clean_tables = [f.replace('.csv', '') for f in os.listdir('clean_tables') if f.endswith('.csv')]
print(f"Target fields in clean_tables ({len(clean_tables)}):")
for ct in clean_tables[:5]:
    print("  ", ct)
print("  ... etc.")

shapefiles = []
for root, dirs, files in os.walk('.'):
    # skip virtual env and git folders
    if '.venv' in root or '.git' in root or '.idea' in root:
        continue
    for f in files:
        if f.lower().endswith('.shp'):
            shapefiles.append(os.path.join(root, f))

print(f"\nFound {len(shapefiles)} shapefiles. Checking for matches...")

for shp in shapefiles:
    try:
        gdf = gpd.read_file(shp)
        print(f"\nFile: {shp} | Rows: {len(gdf)} | Geometry types: {gdf.geometry.type.unique()}")
        print("Columns:", list(gdf.columns))
        # Let's print some unique names from likely name columns
        name_cols = [c for c in gdf.columns if any(sub in c.lower() for sub in ['name', 'field', 'shem', 'id', 'plot', 'id_plot'])]
        for nc in name_cols:
            vals = gdf[nc].dropna().unique()
            print(f"  Col '{nc}' unique values (up to 5):", [str(v) for v in vals[:5]])
    except Exception as e:
        print(f"Error reading {shp}: {e}")
