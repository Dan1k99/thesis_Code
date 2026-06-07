import os
import shutil

for d in ["pixel_temporal_datasets_long", "pixel_temporal_datasets_long_2025"]:
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d, exist_ok=True)
print("Cleaned output directories.")
