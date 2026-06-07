import fiona
import sys

sys.stdout.reconfigure(encoding='utf-8')

layers = fiona.listlayers("qgis/all_layers_with_polygons.gpkg")
print(f"Total layers: {len(layers)}")
for i, l in enumerate(sorted(layers), start=1):
    print(f"{i:2d}. {l}")
