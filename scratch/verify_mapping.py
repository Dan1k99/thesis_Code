import os
import sys
import fiona
import geopandas as gpd

sys.stdout.reconfigure(encoding='utf-8')

gpkg_path = "qgis/all_layers_with_polygons.gpkg"
layers = fiona.listlayers(gpkg_path)

# Extract polygon layers
polygons = []
for l in layers:
    try:
        gdf = gpd.read_file(gpkg_path, layer=l)
        geom_types = gdf.geometry.type.unique() if 'geometry' in gdf.columns else []
        if len(gdf) > 0 and any(gt in ['Polygon', 'MultiPolygon'] for gt in geom_types):
            polygons.append(l)
    except:
        pass

# List clean tables
clean_tables = [f.replace('.csv', '') for f in os.listdir('clean_tables') if f.endswith('.csv')]

print(f"Polygon layers in GPKG ({len(polygons)}):")
for p in sorted(polygons):
    print("  ", p)

print(f"\nClean tables ({len(clean_tables)}):")
for c in sorted(clean_tables)[:10]:
    print("  ", c)
print("  ... etc.")
