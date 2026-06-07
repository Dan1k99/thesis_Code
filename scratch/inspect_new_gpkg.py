import fiona
import geopandas as gpd
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

gpkg_path = "qgis/all_layers_with_polygons.gpkg"
if not os.path.exists(gpkg_path):
    print(f"Error: {gpkg_path} does not exist!")
    sys.exit(1)

print(f"Inspecting layers in {gpkg_path}...")
layers = fiona.listlayers(gpkg_path)
print(f"Found {len(layers)} layers in the geopackage.\n")

points_list = []
polygons_list = []
others_list = []

for l in sorted(layers):
    try:
        gdf = gpd.read_file(gpkg_path, layer=l)
        geom_types = list(gdf.geometry.type.unique()) if 'geometry' in gdf.columns else ['None']
        crs = gdf.crs
        count = len(gdf)
        
        info = {
            'layer_name': l,
            'geom_types': geom_types,
            'rows': count,
            'crs': str(crs)
        }
        
        if any(gt in ['Polygon', 'MultiPolygon'] for gt in geom_types):
            polygons_list.append(info)
        elif any(gt in ['Point', 'MultiPoint'] for gt in geom_types):
            points_list.append(info)
        else:
            others_list.append(info)
            
    except Exception as e:
        print(f"Error reading layer '{l}': {e}")

print(f"=== POLYGON LAYERS ({len(polygons_list)}) ===")
for p in polygons_list:
    print(f"Layer: {p['layer_name']} | Rows: {p['rows']} | Types: {p['geom_types']} | CRS: {p['crs']}")

print(f"\n=== POINT LAYERS ({len(points_list)}) ===")
print(f"Found {len(points_list)} point layers.")
for p in points_list[:10]:
    print(f"Layer: {p['layer_name']} | Rows: {p['rows']} | Types: {p['geom_types']} | CRS: {p['crs']}")
if len(points_list) > 10:
    print(f"... and {len(points_list) - 10} more point layers.")

if others_list:
    print(f"\n=== OTHER LAYERS ({len(others_list)}) ===")
    for o in others_list:
        print(f"Layer: {o['layer_name']} | Rows: {o['rows']} | Types: {o['geom_types']} | CRS: {o['crs']}")
