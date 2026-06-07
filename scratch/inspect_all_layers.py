import fiona
import geopandas as gpd
import sys

sys.stdout.reconfigure(encoding='utf-8')

gpkg_path = "qgis/all_layers_with_polygons.gpkg"
layers = fiona.listlayers(gpkg_path)

polygons = []
points = []
empty_or_other = []

for l in sorted(layers):
    try:
        gdf = gpd.read_file(gpkg_path, layer=l)
        geom_types = list(gdf.geometry.type.unique()) if 'geometry' in gdf.columns else []
        rows = len(gdf)
        crs = str(gdf.crs.to_string() if gdf.crs else 'None')
        
        info = {'name': l, 'rows': rows, 'types': geom_types, 'crs': crs}
        if rows == 0:
            empty_or_other.append(info)
        elif any(gt in ['Polygon', 'MultiPolygon'] for gt in geom_types):
            polygons.append(info)
        elif any(gt in ['Point', 'MultiPoint'] for gt in geom_types):
            points.append(info)
        else:
            empty_or_other.append(info)
    except Exception as e:
        print(f"Error reading layer '{l}': {e}")

print(f"Total layers: {len(layers)}")
print(f"Polygon layers found: {len(polygons)}")
print(f"Point layers found: {len(points)}")
print(f"Empty or other layers found: {len(empty_or_other)}")

print("\n--- DETAILED POLYGON LAYERS ---")
for p in polygons:
    print(f"  * {p['name']} | rows={p['rows']} | types={p['types']} | CRS={p['crs']}")

print("\n--- DETAILED POINT LAYERS ---")
for pt in points:
    print(f"  * {pt['name']} | rows={pt['rows']} | types={pt['types']} | CRS={pt['crs']}")

if empty_or_other:
    print("\n--- EMPTY OR OTHER LAYERS ---")
    for o in empty_or_other:
         print(f"  * {o['name']} | rows={o['rows']} | types={o['types']} | CRS={o['crs']}")
