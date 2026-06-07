import os
import geopandas as gpd
import pandas as pd
import fiona

gpkg_path = "qgis/all_layers_with_polygons.gpkg"
clean_tables_dir = "clean_tables"

# 1. Load all polygon/multipolygon layers from GPKG
layers = fiona.listlayers(gpkg_path)
poly_layers = {}
for l in layers:
    try:
        gdf = gpd.read_file(gpkg_path, layer=l)
        if not gdf.empty and gdf.geometry.iloc[0].geom_type in ['Polygon', 'MultiPolygon']:
            poly_layers[l] = gdf.to_crs(epsg=4326)
    except Exception as e:
        pass

print(f"Loaded {len(poly_layers)} polygon layers from GPKG.")

# 2. Check each clean CSV table's points
for csv_name in os.listdir(clean_tables_dir):
    if not csv_name.endswith('.csv'):
        continue
    csv_path = os.path.join(clean_tables_dir, csv_name)
    df = pd.read_csv(csv_path)
    
    # Check if we have coordinate columns
    lat_col = [c for c in df.columns if 'lat' in c.lower()]
    lon_col = [c for c in df.columns if 'lon' in c.lower() or 'lng' in c.lower()]
    
    if not lat_col or not lon_col:
        print(f"Table {csv_name} has no coordinates.")
        continue
        
    lat_col = lat_col[0]
    lon_col = lon_col[0]
    
    # Create geopandas points
    gdf_pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs="EPSG:4326")
    unary_pts = gdf_pts.geometry.unary_union
    
    matched_polys = []
    for name, gdf_poly in poly_layers.items():
        poly_geom = gdf_poly.geometry.iloc[0]
        # Check intersection or overlap
        if poly_geom.intersects(unary_pts):
            # count how many points are within the polygon
            pts_within = gdf_pts[gdf_pts.geometry.within(poly_geom)]
            matched_polys.append((name, len(pts_within)))
            
    print(f"CSV: {csv_name} | points: {len(gdf_pts)} | Matches: {matched_polys}")
