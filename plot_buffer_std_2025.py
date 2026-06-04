import os
import glob
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import rasterio
import pyproj
from datetime import datetime

# --- Configuration ---
INPUT_DIR = "field_temporal_datasets_long_2025"
OUTPUT_DIR = "buffer_STD_2025"
TARGET_CRS = "EPSG:32636"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set academic visualization font sizes
plt.rc('font', size=11)
plt.rc('axes', titlesize=13, labelsize=12)
plt.rc('xtick', labelsize=10)
plt.rc('ytick', labelsize=10)
plt.rc('legend', fontsize=9)

def check_and_extract_ndvi(df, field_name, chips_dir="data/raw_chips_2025"):
    """
    Checks if NDVI column contains data. If it is entirely null, extracts NDVI 
    on-the-fly from the TIFF files in the raw chips folder.
    """
    if df['ndvi'].notnull().sum() > 0:
        return df

    # Find the closest date before sampling
    df_valid = df[df['Days_Before_Sample'] > 0]
    if df_valid.empty:
        return df
    
    closest_days = df_valid['Days_Before_Sample'].min()
    df_closest = df_valid[df_valid['Days_Before_Sample'] == closest_days].copy()
    
    date_str = df_closest.iloc[0]['date']
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"    [ERROR] Cannot parse date: {date_str}")
            return df
            
    date_formatted = dt.strftime("%Y-%m-%d")
    
    # Search for matching TIFF files in chips_dir
    tifs = glob.glob(os.path.join(chips_dir, "*.tif"))
    matching_tifs = [t for t in tifs if date_formatted in t and 'sr' in t.lower() and 'udm' not in t.lower()]
    
    if not matching_tifs:
        print(f"    [WARNING] No matching TIFFs found for date {date_formatted}")
        return df
        
    ndvis = []
    for idx, row in df_closest.iterrows():
        lon, lat = row['long'], row['lat']
        ndvi_val = np.nan
        for chip_path in matching_tifs:
            try:
                with rasterio.open(chip_path) as src:
                    transformer = pyproj.Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                    x_proj, y_proj = transformer.transform(lon, lat)
                    if src.bounds.left <= x_proj <= src.bounds.right and src.bounds.bottom <= y_proj <= src.bounds.top:
                        py, px = src.index(x_proj, y_proj)
                        if 0 <= py < src.height and 0 <= px < src.width:
                            if src.count == 5:
                                # RapidEye: Band 3 is Red, Band 5 is NIR
                                red = float(src.read(3, window=rasterio.windows.Window(px, py, 1, 1))[0, 0])
                                nir = float(src.read(5, window=rasterio.windows.Window(px, py, 1, 1))[0, 0])
                            elif src.count == 8:
                                # PlanetScope: Band 6 is Red, Band 8 is NIR
                                red = float(src.read(6, window=rasterio.windows.Window(px, py, 1, 1))[0, 0])
                                nir = float(src.read(8, window=rasterio.windows.Window(px, py, 1, 1))[0, 0])
                            else:
                                continue
                            
                            if nir > 0 and (nir + red) > 0:
                                ndvi_val = (nir - red) / (nir + red)
                                break
            except Exception:
                pass
        ndvis.append(ndvi_val)
        
    df_closest['ndvi'] = ndvis
    return df_closest

def plot_field_buffer_std(csv_path):
    field_name = os.path.basename(csv_path).replace("_long_features.csv", "")
    df = pd.read_csv(csv_path)

    # 1. Ensure NDVI values are present (extract on-the-fly if missing)
    df = check_and_extract_ndvi(df, field_name)
    df = df.dropna(subset=['lat', 'long', 'ndvi', 'Aleket_cnt', 'Days_Before_Sample'])
    if df.empty:
        print(f"  [SKIP] {field_name}: No valid NDVI data.")
        return None

    # Filter to closest date before sampling (min Days_Before_Sample > 0)
    df_before = df[df['Days_Before_Sample'] > 0]
    if df_before.empty:
        print(f"  [SKIP] {field_name}: No data before sampling date.")
        return None
        
    min_days = df_before['Days_Before_Sample'].min()
    df_closest = df_before[df_before['Days_Before_Sample'] == min_days].copy()

    # Enforce strict integer types on severity and filter for 0-3
    df_closest['Aleket_cnt'] = df_closest['Aleket_cnt'].astype(int)
    df_closest = df_closest[df_closest['Aleket_cnt'].isin([0, 1, 2, 3])]
    if df_closest.empty:
        print(f"  [SKIP] {field_name}: No data in Aleket 0-3 range.")
        return None

    # 2. Project coordinates and compute signed distance to boundary (using convex hull)
    gdf = gpd.GeoDataFrame(
        df_closest, geometry=gpd.points_from_xy(df_closest['long'], df_closest['lat']), crs="EPSG:4326"
    ).to_crs(TARGET_CRS)

    convex_hull = gdf.geometry.unary_union.convex_hull
    field_boundary = convex_hull.boundary

    distances = []
    for idx, row in gdf.iterrows():
        pt = row.geometry
        dist = pt.distance(field_boundary)
        if not convex_hull.contains(pt):
            dist = -dist
        distances.append(dist)
    gdf['dist_to_border'] = distances

    # 3. Bin distances (10m intervals from -10m to 100m)
    bins = np.arange(-10, 101, 10)
    gdf['dist_bin'] = pd.cut(gdf['dist_to_border'], bins=bins)
    gdf['bin_center'] = gdf['dist_bin'].apply(lambda x: x.mid if not pd.isna(x) else np.nan)

    # 4. Group by Aleket and bin_center, compute STD of NDVI
    grouped = gdf.groupby(['Aleket_cnt', 'bin_center'], observed=False)['ndvi'].agg(['std', 'count']).reset_index()
    grouped = grouped[grouped['count'] >= 2]

    if grouped.empty:
        print(f"  [SKIP] {field_name}: Insufficient points per bin to compute STD.")
        return None

    # --- Academic Visualization ---
    plt.figure(figsize=(10, 6))

    # Standardized color palette
    palette = {
        0: '#2CA02C',  # Green (Healthy)
        1: '#FFD700',  # Gold (Light)
        2: '#FF7F0E',  # Orange (Medium)
        3: '#D62728'   # Red (Severe)
    }

    # Count sample sizes per class for annotation
    counts = gdf['Aleket_cnt'].value_counts()
    sample_sizes = {i: counts.get(i, 0) for i in [0, 1, 2, 3]}

    lines_plotted = 0
    for sev in [0, 1, 2, 3]:
        sub = grouped[grouped['Aleket_cnt'] == sev]
        if not sub.empty:
            plt.plot(
                sub['bin_center'], 
                sub['std'], 
                marker='o', 
                markersize=6, 
                linewidth=2, 
                color=palette[sev], 
                label=f"Aleket {sev} (n={sample_sizes[sev]})"
            )
            lines_plotted += 1

    if lines_plotted == 0:
        plt.close()
        return None

    # Styling and Layout Hygiene
    plt.title(f"NDVI Standard Deviation vs. Distance to Border (2025)\nField: {field_name}", 
              fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Distance from Field Border (Meters)", fontsize=12)
    plt.ylabel("NDVI Standard Deviation (STD)", fontsize=12)
    plt.xlim(-10, 100)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(title="Infestation Class", loc='upper right', frameon=True, shadow=True)

    # Statistical text annotation on the canvas
    total_n = len(gdf)
    annotation_text = f"Total Sample size (n) = {total_n}\nClosest image: {min_days} days before sampling"
    plt.text(0.02, 0.98, annotation_text, transform=plt.gca().transAxes, fontsize=9.5, va='top',
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray', boxstyle='round,pad=0.5'))

    plt.tight_layout()

    # Save figure
    file_suffix = field_name.lower().replace(" ", "_")
    out_path = os.path.join(OUTPUT_DIR, f"{file_suffix}_buffer_std.png")
    plt.savefig(out_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"  [OK] Saved plot to {out_path}")
    return out_path

# Loop over all 2025 files
print("Processing 2025 fields...")
csv_files = glob.glob(os.path.join(INPUT_DIR, "*_long_features.csv"))
for f in csv_files:
    plot_field_buffer_std(f)
print("2025 fields processing complete.")
