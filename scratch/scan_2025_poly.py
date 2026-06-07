import os
import sys
import geopandas as gpd

sys.stdout.reconfigure(encoding='utf-8')

print("Scanning withPoly_2025 recursively:")
found_files = []

vector_extensions = ('.shp', '.gpkg', '.geojson', '.kml')

for root, dirs, files in os.walk('withPoly_2025'):
    for f in files:
        if f.lower().endswith(vector_extensions):
            path = os.path.join(root, f)
            try:
                gdf = gpd.read_file(path)
                geom_types = gdf.geometry.type.unique() if 'geometry' in gdf.columns else []
                print(f"File: {path}")
                print(f"  Geometry Types: {list(geom_types)}")
                print(f"  Rows: {len(gdf)}")
                print(f"  Columns: {list(gdf.columns)}")
                found_files.append((path, geom_types, len(gdf)))
            except Exception as e:
                print(f"File: {path} | Error: {e}")

print("\nSummary of Scanned Files:")
for path, geom_types, count in found_files:
    print(f"  * {path} -> {list(geom_types)} ({count} features)")
